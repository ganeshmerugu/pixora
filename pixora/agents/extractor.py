from __future__ import annotations
import json
import logging
import re
from pixora.agents.state import AgentState
from pixora.ocr.json_utils import extract_json_object
from pixora.providers.base import LLMProvider

logger = logging.getLogger(__name__)

CHUNK_SIZE = 6000
CHUNK_OVERLAP = 500

EXTRACTION_SYSTEM_PROMPT = """You are a document extraction agent. Extract structured data from the provided document text.
Return valid JSON matching the requested schema. For each field, extract the value from the document.
If a field is not found, use null. Be precise — do not hallucinate values not present in the text.
Preserve formatting: if a value appears bold (**text**), italic (*text*), or in a heading (# text),
keep that markdown formatting in your extracted value."""


class ExtractorAgent:
    def __init__(self, llm: LLMProvider | None = None):
        self.llm = llm

    async def run(self, state: AgentState) -> AgentState:
        doc_tree = state.get("document_tree", {})
        schema = state.get("extraction_schema", {})

        all_text = self._collect_text(doc_tree)

        if self.llm and schema.get("nodes"):
            extraction = await self._llm_extract(all_text, schema)
        else:
            extraction = self._basic_extract(all_text, schema)

        state["extraction_result"] = extraction
        state.setdefault("decision_trace", []).append({
            "agent": "extractor",
            "fields_extracted": len(extraction),
            "mode": "llm" if self.llm and schema.get("nodes") else "basic",
        })

        return state

    def _collect_text(self, doc_tree: dict) -> str:
        parts: list[str] = []
        for page in doc_tree.get("pages", []):
            regions = page.get("regions", [])
            sorted_regions = sorted(regions, key=lambda r: (
                r.get("reading_order", 0),
                r.get("bbox", {}).get("y", 0),
                r.get("bbox", {}).get("x", 0),
            ))
            for region in sorted_regions:
                content = region.get("content", "")
                if content.strip():
                    parts.append(content)
        return "\n\n".join(parts)

    async def _llm_extract(self, text: str, schema: dict) -> dict:
        nodes = schema.get("nodes", [])
        fields_desc = "\n".join(
            f'- "{n["name"]}" ({n.get("field_type", "STRING")}): {n.get("description", "")}'
            for n in nodes
        )

        chunks = self._split_into_chunks(text)
        merged: dict = {}

        for chunk_idx, chunk in enumerate(chunks):
            prompt = f"""Extract these fields from the document:
{fields_desc}

Document text (chunk {chunk_idx + 1}/{len(chunks)}):
{chunk}

Return a JSON object with field names as keys. Use null for fields not found in this chunk."""

            try:
                resp = await self.llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system=EXTRACTION_SYSTEM_PROMPT,
                    temperature=0.0,
                )
                content = resp["content"]
                parsed = extract_json_object(content)
                if parsed:
                    for key, value in parsed.items():
                        if value is not None and (key not in merged or merged[key] is None):
                            merged[key] = value
            except Exception as exc:
                logger.warning("extractor: LLM extraction failed on chunk %d: %s", chunk_idx, exc)

        return merged

    def _split_into_chunks(self, text: str) -> list[str]:
        if len(text) <= CHUNK_SIZE:
            return [text]

        pages = text.split("\n\n")
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for page in pages:
            if current_len + len(page) > CHUNK_SIZE and current:
                chunks.append("\n\n".join(current))
                overlap_text = "\n\n".join(current)[-CHUNK_OVERLAP:]
                current = [overlap_text]
                current_len = len(overlap_text)
            current.append(page)
            current_len += len(page) + 2

        if current:
            chunks.append("\n\n".join(current))

        return chunks if chunks else [text]

    def _basic_extract(self, text: str, schema: dict) -> dict:
        lines = text.split("\n")
        result: dict = {}

        for node in schema.get("nodes", []):
            name = node["name"]
            field_type = node.get("field_type", "STRING")
            aliases = [a.lower() for a in node.get("aliases", [])]
            name_label = name.lower().replace("_", " ")
            name_nospace = name.lower().replace("_", "")

            exact_variants = [name_label]
            if aliases:
                exact_variants.extend(aliases)

            best_value = None
            best_score = 0

            for idx, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue
                lower = stripped.lower()

                # Strategy 1: standard "label: value" on same line
                if ":" in stripped:
                    parts = stripped.split(":", 1)
                    label = parts[0].strip().lower()
                    value = parts[1].strip()

                    if value:
                        score = self._match_score(label, name_label, name_nospace, exact_variants)
                        if score > best_score:
                            best_value = value
                            best_score = score

                # Strategy 2: label on this line, value on next line (ID cards, forms)
                for variant in exact_variants:
                    if variant in lower and len(stripped) < 60:
                        # Check if the next non-empty line is the value
                        for next_idx in range(idx + 1, min(idx + 3, len(lines))):
                            next_line = lines[next_idx].strip()
                            if not next_line:
                                continue
                            # Next line should NOT be another label
                            is_label = any(v in next_line.lower() for v in exact_variants) or ":" in next_line[:30]
                            if not is_label and len(next_line) < 200:
                                score = self._match_score(lower, name_label, name_nospace, exact_variants)
                                adj_score = max(score - 10, 1)
                                if adj_score > best_score:
                                    best_value = next_line
                                    best_score = adj_score
                            break

                # Strategy 3: value appears right after label on same line without colon
                for variant in exact_variants:
                    if lower.startswith(variant) and len(stripped) > len(variant) + 2:
                        after = stripped[len(variant):].strip().lstrip(":").strip()
                        if after and len(after) < 200:
                            score = 50
                            if score > best_score:
                                best_value = after
                                best_score = score

            if best_value is not None:
                best_value = _clean_value(best_value, field_type)

            result[name] = best_value

        return result


    def _match_score(self, label: str, name_label: str, name_nospace: str, exact_variants: list[str]) -> int:
        if label == name_label or label in exact_variants:
            return 100
        if label == name_nospace:
            return 95
        for v in exact_variants:
            if label == v:
                return 85
        if name_label in label and _is_exact_word_match(name_label, label):
            return 70
        if any(v in label and _is_exact_word_match(v, label) for v in exact_variants):
            return 65
        if name_label in label or name_nospace in label:
            return 30
        if any(v in label for v in exact_variants):
            return 25
        return 0


def _is_exact_word_match(needle: str, haystack: str) -> bool:
    pattern = r"(?:^|[\s,;|])(" + re.escape(needle) + r")(?:[\s,;|:]|$)"
    return bool(re.search(pattern, haystack))


def _clean_value(value: str, field_type: str) -> str:
    value = value.strip()

    if field_type == "NUMBER":
        m = re.match(r"^([-+]?\d[\d,]*\.?\d*)", value)
        if m:
            return m.group(1)

    if field_type == "CURRENCY":
        m = re.match(r"^(-?\$?[\d,OoIl]+\.[\d,OoIl]{2})\s+(.*)", value)
        if m and m.group(2):
            return value
        m = re.match(r"^(-?\$?[\d,OoIl]+\.[\d,OoIl]{2})$", value)
        if m:
            return m.group(1)
        return value

    if field_type == "DATE":
        m = re.match(r"^(\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4})", value)
        if m:
            return m.group(1)
        m = re.match(r"^([A-Z][a-z]+ \d{1,2},? \d{4})", value)
        if m:
            return m.group(1)

    return value
