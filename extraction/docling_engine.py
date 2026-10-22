"""Docling integration — IBM's open-source document understanding engine.
Handles PDF, DOCX, images with ML-based layout analysis, table extraction,
and structured output. No API key needed."""
from __future__ import annotations
import io
import os
import re
import tempfile
from typing import Any


def extract_with_docling(file_bytes: bytes, filename: str) -> dict[str, Any]:
    from docling.document_converter import DocumentConverter

    ext = os.path.splitext(filename)[1].lower()

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        doc = result.document

        markdown = doc.export_to_markdown()

        tables: list[dict[str, Any]] = []
        tables_markdown: list[str] = []
        for table in doc.tables:
            try:
                table_data = table.export_to_dataframe()
                table_md = table.export_to_markdown()
                tables.append({
                    "headers": list(table_data.columns),
                    "rows": table_data.values.tolist(),
                    "markdown": table_md,
                })
                tables_markdown.append(table_md)
            except Exception:
                fallback = str(table)
                tables.append({"markdown": fallback})
                tables_markdown.append(fallback)

        fields = _extract_fields_from_markdown(markdown)

        return {
            "markdown": markdown,
            "text": _markdown_to_plain(markdown),
            "tables": tables,
            "tables_markdown": tables_markdown,
            "fields": fields,
            "page_count": len(doc.pages) if hasattr(doc, "pages") else 0,
            "engine": "docling",
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _extract_fields_from_markdown(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        clean = stripped.lstrip("#").lstrip("-").lstrip("*").strip()

        if ":" in clean and len(clean) < 300:
            colon_pos = clean.index(":")
            label = clean[:colon_pos].strip()
            value = clean[colon_pos + 1:].strip()

            if not label or not value or len(label) > 80 or len(label) < 2:
                continue
            if re.search(r"https?://", label):
                continue

            alpha = sum(1 for c in label if c.isalpha() or c in " .-_#/()") / max(len(label), 1)
            if alpha < 0.5:
                continue

            field_name = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
            if field_name and field_name not in fields:
                fields[field_name] = value

    return fields


def _markdown_to_plain(md: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", md)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text
