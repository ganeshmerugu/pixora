from __future__ import annotations
import json
import uuid
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.models.document import BoundingBox
from pixora.providers.base import VisionProvider


class FormField(TypedDict, total=False):
    field_id: Required[str]
    label: str
    field_type: str
    value: Any
    bbox: BoundingBox
    confidence: float


OMR_PROMPT = """Analyze this image for form fields: checkboxes, radio buttons, text inputs, and signatures.
Return JSON array:
[{"label": "field label", "field_type": "checkbox|radio|text_input|signature", "value": true/false/"text", "confidence": 0.95}]
Only return the JSON array."""


class OMREngine:
    engine_name = "omr_forms"

    def __init__(self, provider: VisionProvider):
        self.provider = provider

    async def recognize_marks(
        self,
        image_bytes: bytes,
        page_number: int = 1,
    ) -> list[FormField]:
        resp = await self.provider.analyze_image(image_bytes, OMR_PROMPT)

        try:
            fields_data = json.loads(resp["content"])
            if not isinstance(fields_data, list):
                fields_data = [fields_data]
        except (json.JSONDecodeError, KeyError):
            return []

        fields: list[FormField] = []
        for i, f in enumerate(fields_data):
            fields.append(FormField(
                field_id=f"omr_{page_number}_{i}_{uuid.uuid4().hex[:8]}",
                label=str(f.get("label", "")),
                field_type=str(f.get("field_type", "unknown")),
                value=f.get("value"),
                confidence=float(f.get("confidence", 0.8)),
            ))

        return fields
