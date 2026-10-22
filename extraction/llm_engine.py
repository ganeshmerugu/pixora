"""LLM extraction engine — optional Claude integration.
Resolution order: ANTHROPIC_API_KEY env → Claude Code API key helper → cached credentials.
If no API key is found, all functions gracefully return empty results."""
from __future__ import annotations
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    HAS_ANTHROPIC = False


_CLIENT_LOCK = threading.Lock()
_CLIENT = None


def _read_cached_credentials(min_ttl_seconds: int = 60) -> str:
    from datetime import datetime, timezone
    dirs = [Path.home() / ".claude" / "fico", Path("/run/fico")]
    for d in dirs:
        try:
            data = json.loads((d / "credentials.json").read_text())
            key = data.get("temporary_api_key", "").strip()
            if not key:
                continue
            expiry = data.get("temporary_key_expiry", "")
            if expiry:
                dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if (dt - datetime.now(timezone.utc)).total_seconds() < min_ttl_seconds:
                    continue
            return key
        except Exception:
            continue
    return ""


def _make_client():
    if not HAS_ANTHROPIC:
        return None
    import httpx
    kwargs: dict = {}

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if base_url:
        kwargs["base_url"] = base_url

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        helper = os.environ.get("CLAUDE_CODE_API_KEY_HELPER_COMMAND", "")
        if helper and os.path.isfile(helper) and os.access(helper, os.X_OK):
            try:
                api_key = subprocess.check_output([helper], timeout=30).decode().strip()
            except Exception:
                pass

    if not api_key:
        api_key = _read_cached_credentials()

    if not api_key:
        return None

    kwargs["api_key"] = api_key
    kwargs["max_retries"] = 2
    kwargs["timeout"] = anthropic.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)

    try:
        kwargs["http_client"] = httpx.Client(
            verify=os.getenv("PIXORA_TLS_VERIFY", "true").lower() not in ("0", "false", "no"),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    except Exception:
        pass

    return anthropic.Anthropic(**kwargs)


def get_client():
    global _CLIENT
    if _CLIENT is None:
        with _CLIENT_LOCK:
            if _CLIENT is None:
                _CLIENT = _make_client()
    return _CLIENT


def is_available() -> bool:
    return get_client() is not None


VISION_MARKDOWN_PROMPT = """You are a document intelligence system. Analyze this document image and produce a rich structured markdown representation.

Rules:
- Preserve ALL text in ALL languages exactly as it appears (Hindi, English, Arabic, etc.)
- Use ## for major section headings, ### for sub-headings
- Bold important values with **value**
- Describe visual elements inline: "logo: [description]", "photo: [description]", "signature: [description]", "QR Code"
- Pair bilingual labels: Hindi heading on one line, English translation on next
- Preserve the exact reading order (top to bottom, left to right)
- For ID cards, forms, certificates: extract every label/value pair as **Label**\\n**Value**
- Do NOT explain or summarize — reproduce the document structure faithfully

Return ONLY the markdown content, no JSON wrapper."""


VISION_ITEMS_PROMPT = """Analyze this document image and return a JSON array of structured items.

Each item must have:
- "type": one of "heading", "text", "image", "table", "form_field"
- "md": the markdown representation of this item
- "value": the plain text value
- "level": heading level (2 or 3) if type is "heading", null otherwise
- "bbox": {{"x": float, "y": float, "w": float, "h": float, "confidence": float, "label": string}}
  where x,y,w,h are percentages of page dimensions (0-100)
- "label": one of "paragraph_title", "text", "caption", "image", "table"

Rules:
- Include ALL text in ALL languages (Hindi, English, etc.)
- Describe images/photos/logos/signatures/QR codes as text items with descriptive values
- Preserve reading order
- Every visible element gets its own item

Return ONLY a valid JSON array, no explanation."""


def vision_to_markdown(image_bytes: bytes, model: str | None = None) -> dict[str, Any]:
    import base64
    client = get_client()
    if not client:
        return {"markdown": "", "error": "LLM not available"}

    model = model or os.environ.get("PIXORA_DEFAULT_MODEL", "gemini-2.0-flash-001")
    b64 = base64.b64encode(image_bytes).decode()

    media_type = "image/png"
    if image_bytes[:3] == b'\xff\xd8\xff':
        media_type = "image/jpeg"
    elif image_bytes[:4] == b'RIFF':
        media_type = "image/webp"

    start = time.monotonic()
    try:
        resp = client.messages.create(
            model=model, max_tokens=4096, temperature=0.0,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": VISION_MARKDOWN_PROMPT},
            ]}],
        )
        markdown = resp.content[0].text if resp.content else ""
        elapsed_ms = int((time.monotonic() - start) * 1000)
        tokens_in = resp.usage.input_tokens or 0
        tokens_out = resp.usage.output_tokens or 0

        return {
            "markdown": markdown,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": _estimate_cost(tokens_in, tokens_out, model),
            "latency_ms": elapsed_ms,
        }
    except Exception as e:
        return {"markdown": "", "error": str(e)}


def vision_to_items(image_bytes: bytes, page_width: float = 100, page_height: float = 100, model: str | None = None) -> list[dict]:
    import base64
    client = get_client()
    if not client:
        return []

    model = model or os.environ.get("PIXORA_DEFAULT_MODEL", "gemini-2.0-flash-001")
    b64 = base64.b64encode(image_bytes).decode()

    media_type = "image/png"
    if image_bytes[:3] == b'\xff\xd8\xff':
        media_type = "image/jpeg"
    elif image_bytes[:4] == b'RIFF':
        media_type = "image/webp"

    try:
        resp = client.messages.create(
            model=model, max_tokens=4096, temperature=0.0,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": VISION_ITEMS_PROMPT},
            ]}],
        )
        content = resp.content[0].text if resp.content else "[]"
        start_idx = content.find("[")
        end_idx = content.rfind("]") + 1
        if start_idx >= 0 and end_idx > start_idx:
            return json.loads(content[start_idx:end_idx])
        return []
    except Exception:
        return []


EXTRACTION_PROMPT = """You are a document intelligence system. Analyze this document and extract ALL structured data.

Return a JSON object where:
- Keys are descriptive field names in snake_case (e.g., "invoice_number", "patient_name", "total_amount")
- Values are the extracted text exactly as it appears in the document
- Include EVERY piece of structured information you can find
- For tables, include a "_tables" key with an array of table objects
- For each table object, include "headers" (array) and "rows" (array of arrays)
- If a field has no value, omit it entirely (don't use null)
- Extract dates, amounts, names, IDs, addresses — anything that looks like a data field

Document text:
{text}

Return ONLY valid JSON, no explanation."""


def extract_with_llm(text: str, model: str | None = None) -> dict[str, Any]:
    """Extract structured data from text using Claude."""
    client = get_client()
    if not client:
        return {}

    model = model or os.environ.get("PIXORA_DEFAULT_MODEL", "gemini-2.0-flash-001")
    prompt = EXTRACTION_PROMPT.format(text=text[:15000])

    start = time.monotonic()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.content[0].text if resp.content else ""
        elapsed_ms = int((time.monotonic() - start) * 1000)
        tokens_in = resp.usage.input_tokens or 0
        tokens_out = resp.usage.output_tokens or 0

        # Parse JSON from response
        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            extracted = json.loads(content[start_idx:end_idx])
        else:
            extracted = {}

        extracted["_meta"] = {
            "engine": "claude",
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": _estimate_cost(tokens_in, tokens_out, model),
            "latency_ms": elapsed_ms,
        }
        return extracted

    except Exception as e:
        return {"_meta": {"engine": "claude", "error": str(e)}}


SCHEMA_GEN_PROMPT = """You are a document intelligence schema designer. Given the description below, generate an extraction schema as a JSON object.

The schema must have:
- "schema_id": a short snake_case identifier
- "doc_type": the document type
- "version": "1.0"
- "nodes": array of field definitions, each with:
  - "name": snake_case field name
  - "field_type": one of STRING, NUMBER, DATE, CURRENCY, BOOLEAN, ENUM, EMAIL, PHONE, URL, ADDRESS, LIST, TABLE
  - "description": human-readable description
  - "required": true/false
  - "aliases": array of alternative names for this field

{context}

Description: {prompt}

Return ONLY valid JSON, no explanation."""


def generate_schema_with_llm(prompt: str, sample_text: str | None = None, model: str | None = None) -> dict[str, Any]:
    client = get_client()
    if not client:
        return {"error": "LLM not available"}

    model = model or os.environ.get("PIXORA_DEFAULT_MODEL", "gemini-2.0-flash-001")
    context = ""
    if sample_text:
        context = f"Here is a sample document to analyze:\n---\n{sample_text[:8000]}\n---\n"

    full_prompt = SCHEMA_GEN_PROMPT.format(prompt=prompt, context=context)

    try:
        resp = client.messages.create(
            model=model, max_tokens=4096, temperature=0.0,
            messages=[{"role": "user", "content": full_prompt}],
        )
        content = resp.content[0].text if resp.content else ""
        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            return json.loads(content[start_idx:end_idx])
        return {"error": "Could not parse schema from LLM response"}
    except Exception as e:
        return {"error": str(e)}


def _estimate_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    if "opus" in model:
        return (tokens_in * 15 + tokens_out * 75) / 1_000_000
    elif "haiku" in model:
        return (tokens_in * 0.25 + tokens_out * 1.25) / 1_000_000
    else:  # sonnet
        return (tokens_in * 3 + tokens_out * 15) / 1_000_000
