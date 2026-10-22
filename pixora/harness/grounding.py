from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from Levenshtein import ratio as levenshtein_ratio


class GroundingEvidence(TypedDict, total=False):
    field: Required[str]
    extracted_value: Required[str]
    source_region_id: str
    source_text: str
    source_snippet: str
    match_type: str
    similarity_score: float
    parsing_confidence: float
    extraction_confidence: float
    page: int
    bbox: dict


class Citation(TypedDict, total=False):
    field: Required[str]
    value: Required[str]
    page: int
    text: str
    bbox: dict
    parsing_confidence: float
    extraction_confidence: float
    overall_confidence: float


class GroundingReport(TypedDict, total=False):
    document_id: Required[str]
    total_fields: int
    grounded_count: int
    inferred_count: int
    ungrounded_count: int
    grounding_rate: float
    evidence: list[GroundingEvidence]
    citations: list[Citation]
    field_confidences: list[dict]
    flagged_hallucinations: list[str]


FUZZY_THRESHOLD = 0.85


class GroundingVerifier:
    def verify(
        self,
        extraction: dict[str, Any],
        document_tree: dict[str, Any],
        document_id: str = "",
    ) -> GroundingReport:
        regions = self._collect_regions(document_tree)
        evidence: list[GroundingEvidence] = []
        citations: list[Citation] = []
        field_confidences: list[dict] = []
        grounded = 0
        inferred = 0
        ungrounded = 0
        hallucinations: list[str] = []

        for field, value in extraction.items():
            if field.startswith("_") or value is None:
                continue

            val_str = str(value).strip()
            if not val_str:
                continue

            match = self._find_match(val_str, regions)
            parsing_conf = match.get("parsing_confidence", 0.0)
            sim_score = match["evidence"].get("similarity_score", 0.0)
            extraction_conf = sim_score

            ev = match["evidence"] | {
                "field": field,
                "extracted_value": val_str,
                "parsing_confidence": parsing_conf,
                "extraction_confidence": extraction_conf,
                "source_snippet": match["evidence"].get("source_text", "")[:200],
            }
            evidence.append(ev)

            overall_conf = round((parsing_conf + extraction_conf) / 2, 4) if parsing_conf > 0 else extraction_conf
            field_confidences.append({
                "field": field,
                "parsing_confidence": round(parsing_conf, 4),
                "extraction_confidence": round(extraction_conf, 4),
                "overall": round(overall_conf, 4),
            })

            citation = Citation(
                field=field,
                value=val_str,
                page=ev.get("page", 0),
                text=ev.get("source_snippet", ""),
                bbox=ev.get("bbox", {}),
                parsing_confidence=round(parsing_conf, 4),
                extraction_confidence=round(extraction_conf, 4),
                overall_confidence=round(overall_conf, 4),
            )
            citations.append(citation)

            if match["type"] in ("exact", "normalized"):
                grounded += 1
            elif match["type"] == "fuzzy":
                grounded += 1
            elif match["type"] == "inferred":
                inferred += 1
            else:
                ungrounded += 1
                hallucinations.append(field)

        total = grounded + inferred + ungrounded
        rate = grounded / total if total > 0 else 1.0

        return GroundingReport(
            document_id=document_id,
            total_fields=total,
            grounded_count=grounded,
            inferred_count=inferred,
            ungrounded_count=ungrounded,
            grounding_rate=round(rate, 4),
            evidence=evidence,
            citations=citations,
            field_confidences=field_confidences,
            flagged_hallucinations=hallucinations,
        )

    def _collect_regions(self, doc_tree: dict) -> list[dict]:
        regions = []
        for page in doc_tree.get("pages", []):
            page_num = page.get("page_number", 0)
            for region in page.get("regions", []):
                regions.append({
                    "id": region.get("id", ""),
                    "content": region.get("content", ""),
                    "page": page_num,
                    "bbox": region.get("bbox", {}),
                    "confidence": region.get("confidence", 0.0),
                })
        return regions

    def _find_match(self, value: str, regions: list[dict]) -> dict:
        val_lower = value.lower().strip()
        val_norm = self._normalize(value)

        for region in regions:
            content = region["content"]
            pc = region.get("confidence", 0.0)

            if value in content:
                return {"type": "exact", "parsing_confidence": pc, "evidence": GroundingEvidence(
                    source_region_id=region["id"], source_text=value,
                    match_type="exact", similarity_score=1.0,
                    page=region["page"], bbox=region["bbox"],
                )}

            if val_lower in content.lower():
                return {"type": "normalized", "parsing_confidence": pc, "evidence": GroundingEvidence(
                    source_region_id=region["id"], source_text=value,
                    match_type="normalized", similarity_score=1.0,
                    page=region["page"], bbox=region["bbox"],
                )}

            content_norm = self._normalize(content)
            if val_norm in content_norm:
                return {"type": "normalized", "parsing_confidence": pc, "evidence": GroundingEvidence(
                    source_region_id=region["id"], source_text=value,
                    match_type="normalized", similarity_score=0.95,
                    page=region["page"], bbox=region["bbox"],
                )}

        best_ratio = 0.0
        best_region = None
        for region in regions:
            for word in region["content"].split():
                r = levenshtein_ratio(val_lower, word.lower())
                if r > best_ratio:
                    best_ratio = r
                    best_region = region

        if best_ratio >= FUZZY_THRESHOLD and best_region:
            return {"type": "fuzzy", "parsing_confidence": best_region.get("confidence", 0.0), "evidence": GroundingEvidence(
                source_region_id=best_region["id"], source_text=value,
                match_type="fuzzy", similarity_score=round(best_ratio, 4),
                page=best_region["page"], bbox=best_region["bbox"],
            )}

        if self._is_numeric(value):
            for region in regions:
                if any(self._normalize_number(value) == self._normalize_number(w) for w in region["content"].split()):
                    return {"type": "inferred", "parsing_confidence": region.get("confidence", 0.0), "evidence": GroundingEvidence(
                        source_region_id=region["id"], source_text=value,
                        match_type="inferred", similarity_score=0.8,
                        page=region["page"], bbox=region["bbox"],
                    )}

        return {"type": "ungrounded", "parsing_confidence": 0.0, "evidence": GroundingEvidence(
            match_type="ungrounded", similarity_score=0.0,
        )}

    def _normalize(self, text: str) -> str:
        return text.lower().replace(",", "").replace("$", "").replace(" ", "").strip()

    def _is_numeric(self, value: str) -> bool:
        try:
            float(value.replace(",", "").replace("$", "").replace("%", ""))
            return True
        except ValueError:
            return False

    def _normalize_number(self, value: str) -> str:
        try:
            return str(float(value.replace(",", "").replace("$", "").replace("%", "")))
        except ValueError:
            return value
