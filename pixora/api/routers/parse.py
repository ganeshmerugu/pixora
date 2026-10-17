from __future__ import annotations
import io
import logging
import re
import uuid
import os
import time

logger = logging.getLogger(__name__)
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any
from urllib.parse import urlparse

from pixora.storage import save_file, get_file, save_job, get_job, list_jobs, update_job, delete_job as db_delete_job
from pixora.agents.state import AgentState
from pixora.agents.classifier import ClassifierAgent
from pixora.agents.router import RouterAgent
from pixora.agents.extractor import ExtractorAgent
from pixora.agents.validator import ValidatorAgent
from pixora.agents.scorer import ScorerAgent
from pixora.harness.grounding import GroundingVerifier
from pixora.models.document import DocumentTree, Page, Region
from pixora.api.routers.audit import PipelineAuditor
from pixora.ocr.easyocr_engine import EasyOCREngine
from pixora.extraction.docling_engine import extract_with_docling
from pixora.extraction.llm_engine import extract_with_llm, is_available as llm_available, vision_to_markdown, vision_to_items
from pixora.ocr.paddle_engine import PaddleOCREngine, paddle_to_markdown
from pixora.parsing.reader import ReaderRegistry
from pixora.parsing.pdf_reader import PDFReader
from pixora.parsing.image_reader import ImageReader
from pixora.parsing.docx_reader import DocxReader
from pixora.parsing.spreadsheet import SpreadsheetReader, CSVReader
from pixora.parsing.html_reader import HTMLReader
from pixora.parsing.text_reader import TextReader
from pixora.rendering.page_renderer import render_pages, compute_field_bboxes

router = APIRouter(prefix="/parse", tags=["parse"])

_reader_registry = ReaderRegistry()
_reader_registry.register(PDFReader())
_reader_registry.register(ImageReader())
_reader_registry.register(DocxReader())
_reader_registry.register(SpreadsheetReader())
_reader_registry.register(CSVReader())
_reader_registry.register(HTMLReader())
_reader_registry.register(TextReader())

# Keep in-memory dict for backward compat with tests + dashboard
_jobs: dict[str, dict] = {}


@router.post("/upload")
async def parse_with_upload(
    file: UploadFile = File(...),
    tier: str = Form("agentic"),
    extraction_target: str = Form("per_doc"),
    webhook_url: str = Form(""),
):
    data = await file.read()
    filename = file.filename or "unknown"
    file_id = save_file(filename, data, file.content_type or "")

    job_id = uuid.uuid4().hex
    doc_id = uuid.uuid4().hex

    save_job({
        "id": job_id, "file_id": file_id, "document_id": doc_id,
        "job_type": "parse", "tier": tier, "status": "processing",
        "filename": filename, "doc_type": "",
        "created_at": datetime.now().isoformat(),
    })

    try:
        if extraction_target == "per_page":
            result = await _run_pipeline_per_page(data, filename, doc_id, tier)
        else:
            result = await _run_pipeline(data, filename, doc_id, tier)

        update_job(job_id,
            status="completed",
            doc_type=result["doc_type"],
            result=result["extraction"],
            quality_report=result["quality_report"],
            grounding_report=result["grounding_report"],
            trace=result["trace"],
            completed_at=datetime.now().isoformat(),
        )

        # Also store in memory for dashboard stats
        _jobs[job_id] = {
            "job_id": job_id, "status": "completed", "document_id": doc_id,
            "result": result["extraction"],
        }

        response_data = {
            "job_id": job_id,
            "status": "completed",
            "document_id": doc_id,
            "filename": filename,
            "doc_type": result["doc_type"],
            "extraction": result["extraction"],
            "markdown": result["markdown"],
            "text": result.get("text", result.get("source_text", "")),
            "items": result.get("items", []),
            "quality_report": result["quality_report"],
            "grounding_report": result["grounding_report"],
            "citations": result.get("citations", []),
            "field_confidences": result.get("field_confidences", []),
            "correction_rounds": result["correction_rounds"],
            "processing_time_ms": result["processing_time_ms"],
            "audit": result.get("audit", {}),
            "source_text": result.get("source_text", ""),
            "highlights": result.get("highlights", []),
            "pages": [{k: v for k, v in p.items() if k != "text_spans"} for p in result.get("pages", [])],
            "field_bboxes": result.get("field_bboxes", []),
        }

        if webhook_url:
            _fire_webhook(webhook_url, {
                "event": "job.completed", "job_id": job_id,
                "document_id": doc_id, "doc_type": result["doc_type"],
                "field_count": len([k for k in result["extraction"] if not k.startswith("_")]),
                "processing_time_ms": result["processing_time_ms"],
            })

        return response_data

    except Exception as e:
        update_job(job_id, status="failed", error=str(e), completed_at=datetime.now().isoformat())
        _jobs[job_id] = {"job_id": job_id, "status": "failed", "document_id": doc_id, "result": None}
        return {
            "job_id": job_id,
            "status": "failed",
            "document_id": doc_id,
            "error": str(e),
        }


@router.post("")
async def create_parse_job(request: dict[str, Any] = {}):
    job_id = uuid.uuid4().hex
    doc_id = uuid.uuid4().hex
    file_id = request.get("file_id", "")
    tier = request.get("tier", "agentic")

    job = {
        "id": job_id, "file_id": file_id, "document_id": doc_id,
        "job_type": "parse", "tier": tier, "status": "queued",
        "created_at": datetime.now().isoformat(),
    }
    save_job(job)

    # If file_id is in storage, process it
    stored = get_file(file_id)
    if stored and stored.get("data"):
        update_job(job_id, status="processing")
        try:
            result = await _run_pipeline(stored["data"], stored["filename"], doc_id, tier)
            update_job(job_id,
                status="completed", result=result["extraction"],
                quality_report=result["quality_report"],
                grounding_report=result["grounding_report"],
                trace=result["trace"],
                completed_at=datetime.now().isoformat(),
            )
            _jobs[job_id] = {"job_id": job_id, "status": "completed", "document_id": doc_id, "result": result["extraction"]}
            return {"job_id": job_id, "status": "completed", "document_id": doc_id, "result": result["extraction"]}
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
            _jobs[job_id] = {"job_id": job_id, "status": "failed", "document_id": doc_id, "result": None}

    _jobs[job_id] = {"job_id": job_id, "status": job.get("status", "queued"), "document_id": doc_id, "result": None}
    return {"job_id": job_id, "status": "queued", "document_id": doc_id, "result": None}


def _format_job(job: dict) -> dict:
    qr = job.get("quality_report") or {}
    return {
        "job_id": job.get("id", job.get("job_id")),
        "status": job.get("status"),
        "document_id": job.get("document_id"),
        "file_id": job.get("file_id", ""),
        "filename": job.get("filename", ""),
        "doc_type": job.get("doc_type", ""),
        "tier": job.get("tier", ""),
        "parent_job_id": job.get("parent_job_id", ""),
        "quality_score": qr.get("overall_score", 0) if qr else 0,
        "recommendation": qr.get("recommendation", "") if qr else "",
        "field_count": len(job.get("result") or {}) if isinstance(job.get("result"), dict) else 0,
        "error": job.get("error", ""),
        "created_at": job.get("created_at", ""),
        "completed_at": job.get("completed_at", ""),
        "extraction": job.get("result"),
    }


@router.get("/{job_id}")
async def get_parse_job(job_id: str):
    job = get_job(job_id)
    if not job:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out = _format_job(job)
    out["quality_report"] = job.get("quality_report")
    out["grounding_report"] = job.get("grounding_report")
    out["trace"] = job.get("trace")
    return out



@router.get("")
async def list_parse_jobs():
    db_jobs = list_jobs(100)
    results = []
    for j in db_jobs:
        results.append(_format_job(j))
    for jid, j in _jobs.items():
        if not any(r["job_id"] == jid for r in results):
            results.append(_format_job(j))
    return results


@router.post("/{job_id}/cancel")
async def cancel_parse_job(job_id: str):
    update_job(job_id, status="cancelled")
    if job_id in _jobs:
        _jobs[job_id]["status"] = "cancelled"
    return {"job_id": job_id, "status": "cancelled"}


@router.delete("/{job_id}")
async def delete_parse_job(job_id: str):
    db_delete_job(job_id)
    _jobs.pop(job_id, None)
    return {"deleted": True}


@router.get("/{job_id}/file")
async def get_job_file(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    file_id = job.get("file_id", "")
    if not file_id:
        raise HTTPException(status_code=404, detail="No file attached to this job")
    stored = get_file(file_id)
    if not stored or not stored.get("data"):
        raise HTTPException(status_code=404, detail="File not found in storage")

    filename = stored.get("filename", "file")
    mime = stored.get("mime_type", "application/octet-stream")
    if not mime or mime == "":
        ext = os.path.splitext(filename)[1].lower()
        mime = {
            ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
            ".tiff": "image/tiff", ".tif": "image/tiff", ".bmp": "image/bmp",
            ".svg": "image/svg+xml", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".csv": "text/csv", ".txt": "text/plain", ".html": "text/html", ".json": "application/json",
        }.get(ext, "application/octet-stream")

    return Response(
        content=stored["data"],
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{job_id}/rerun")
async def rerun_parse_job(job_id: str, tier: str = Form("")):
    original = get_job(job_id)
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")

    file_id = original.get("file_id", "")
    stored = get_file(file_id) if file_id else None
    if not stored or not stored.get("data"):
        raise HTTPException(status_code=400, detail="Original file no longer available")

    use_tier = tier if tier else original.get("tier", "agentic")
    filename = stored.get("filename", original.get("filename", "rerun"))
    data = stored["data"]

    new_job_id = uuid.uuid4().hex
    new_doc_id = uuid.uuid4().hex

    save_job({
        "id": new_job_id, "file_id": file_id, "document_id": new_doc_id,
        "job_type": "parse", "tier": use_tier, "status": "processing",
        "filename": filename, "doc_type": "",
        "parent_job_id": job_id,
        "created_at": datetime.now().isoformat(),
    })

    try:
        result = await _run_pipeline(data, filename, new_doc_id, use_tier)

        update_job(new_job_id,
            status="completed", doc_type=result["doc_type"],
            result=result["extraction"],
            quality_report=result["quality_report"],
            grounding_report=result["grounding_report"],
            trace=result["trace"],
            completed_at=datetime.now().isoformat(),
        )

        _jobs[new_job_id] = {"job_id": new_job_id, "status": "completed", "document_id": new_doc_id, "result": result["extraction"]}

        return {
            "job_id": new_job_id,
            "parent_job_id": job_id,
            "status": "completed",
            "document_id": new_doc_id,
            "filename": filename,
            "tier": use_tier,
            "doc_type": result["doc_type"],
            "extraction": result["extraction"],
            "markdown": result["markdown"],
            "quality_report": result["quality_report"],
            "grounding_report": result["grounding_report"],
            "citations": result.get("citations", []),
            "field_confidences": result.get("field_confidences", []),
            "processing_time_ms": result["processing_time_ms"],
            "source_text": result.get("source_text", ""),
            "highlights": result.get("highlights", []),
            "pages": [{k: v for k, v in p.items() if k != "text_spans"} for p in result.get("pages", [])],
            "field_bboxes": result.get("field_bboxes", []),
        }
    except Exception as e:
        update_job(new_job_id, status="failed", error=str(e), completed_at=datetime.now().isoformat())
        return {"job_id": new_job_id, "parent_job_id": job_id, "status": "failed", "error": str(e)}


@router.post("/url")
async def parse_from_url(
    url: str = Form(...),
    tier: str = Form("agentic"),
    extraction_target: str = Form("per_doc"),
    webhook_url: str = Form(""),
):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs supported")

    import httpx
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.content
            content_type = resp.headers.get("content-type", "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    filename = os.path.basename(parsed.path) or "download"
    if "." not in filename:
        ext_map = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg",
                    "text/html": ".html", "text/plain": ".txt", "text/csv": ".csv"}
        for ct, ext in ext_map.items():
            if ct in content_type:
                filename += ext
                break

    file_id = save_file(filename, data, content_type)
    job_id = uuid.uuid4().hex
    doc_id = uuid.uuid4().hex

    save_job({
        "id": job_id, "file_id": file_id, "document_id": doc_id,
        "job_type": "parse", "tier": tier, "status": "processing",
        "filename": filename, "doc_type": "", "source_url": url,
        "created_at": datetime.now().isoformat(),
    })

    try:
        if extraction_target == "per_page":
            result = await _run_pipeline_per_page(data, filename, doc_id, tier)
        else:
            result = await _run_pipeline(data, filename, doc_id, tier)

        update_job(job_id, status="completed", doc_type=result["doc_type"],
                   result=result["extraction"], completed_at=datetime.now().isoformat())

        response = {
            "job_id": job_id, "status": "completed", "document_id": doc_id,
            "source_url": url, "filename": filename,
            "doc_type": result["doc_type"], "extraction": result["extraction"],
            "quality_report": result["quality_report"],
            "grounding_report": result["grounding_report"],
            "citations": result.get("citations", []),
            "field_confidences": result.get("field_confidences", []),
            "processing_time_ms": result["processing_time_ms"],
        }

        if webhook_url:
            _fire_webhook(webhook_url, response)

        return response
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
        return {"job_id": job_id, "status": "failed", "error": str(e)}


@router.post("/split")
async def parse_split_document(
    file: UploadFile = File(...),
    tier: str = Form("agentic"),
):
    data = await file.read()
    filename = file.filename or "unknown"
    from pixora.parsing.splitter import DocumentSplitter
    splitter = DocumentSplitter()
    sub_docs = splitter.split(data, filename)

    results = []
    for i, sub in enumerate(sub_docs):
        doc_id = uuid.uuid4().hex
        try:
            result = await _run_pipeline(sub["bytes"], sub["filename"], doc_id, tier)
            results.append({
                "sub_document": i + 1,
                "pages": sub.get("page_range", ""),
                "doc_type": result["doc_type"],
                "extraction": result["extraction"],
                "quality_report": result["quality_report"],
                "citations": result.get("citations", []),
                "field_confidences": result.get("field_confidences", []),
            })
        except Exception as e:
            results.append({"sub_document": i + 1, "error": str(e)})

    return {"total_sub_documents": len(sub_docs), "results": results}


def _fire_webhook(url: str, payload: dict):
    import threading
    import httpx
    import hashlib
    import json as _json

    def _send():
        try:
            body = _json.dumps(payload, default=str)
            sig = hashlib.sha256(body.encode()).hexdigest()
            httpx.post(url, content=body, headers={
                "Content-Type": "application/json",
                "X-Pixora-Signature": sig,
            }, timeout=10.0)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


async def _run_pipeline(file_bytes: bytes, filename: str, doc_id: str, tier: str) -> dict:
    start = time.monotonic()

    # Read document — try format-specific reader, fall back to raw text on any failure
    doc_tree = None
    try:
        reader = _reader_registry.get_reader(filename)
        doc_tree = await reader.read(file_bytes, filename)
    except Exception:
        pass

    # Check if reader produced any actual text
    has_text = doc_tree is not None and doc_tree.get("pages") and any(
        r.get("content", "").strip() for p in doc_tree.get("pages", []) for r in p.get("regions", [])
    )

    # Additional check: even if we got "text", verify it's not binary garbage
    if has_text:
        all_content = " ".join(
            r.get("content", "") for p in doc_tree.get("pages", []) for r in p.get("regions", [])
        )[:3000]
        printable = sum(1 for c in all_content if c.isprintable() or c in "\n\r\t")
        if printable / max(len(all_content), 1) < 0.6:
            has_text = False

    # If no text layer — use VLM-first architecture (don't waste time on OCR)
    is_image_format = doc_tree is not None and (
        doc_tree.get("text_layer_present") is False
        or any(r.get("metadata", {}).get("needs_ocr") for p in doc_tree.get("pages", []) for r in p.get("regions", []))
    )

    vlm_result = None
    vlm_error = ""
    doc_type = ""
    if not has_text and is_image_format:
        # Strategy 1: VLM-first (Gemini free, best quality for images)
        try:
            from pixora.ocr.vlm_harness import vlm_extract as vlm_harness_extract, is_vlm_available
            if is_vlm_available():
                t0 = time.monotonic()
                vlm_result = await vlm_harness_extract(file_bytes, filename, doc_type=doc_type)
                vlm_md = vlm_result.get("markdown", "")
                vlm_ext = vlm_result.get("extraction", {})
                vlm_text = vlm_md or " ".join(str(v) for v in vlm_ext.values() if v)

                if vlm_text and vlm_text.strip():
                    doc_tree = DocumentTree(
                        document_id=doc_id,
                        pages=[Page(page_number=1, regions=[
                            Region(id="r_vlm_0", type="TEXT", content=vlm_text, confidence=vlm_result.get("confidence", 0.85)),
                        ])],
                        source_format="vlm",
                        text_layer_present=True,
                    )
                    has_text = True
                    auditor.log_stage("vlm_primary", detail=(
                        f"provider={vlm_result.get('provider', '?')}, "
                        f"fields={len(vlm_ext)}, "
                        f"confidence={vlm_result.get('confidence', 0):.2f}, "
                        f"cost=${vlm_result.get('cost_usd', 0):.4f}, "
                        f"cached={vlm_result.get('cached', False)}"
                    ), duration_ms=int((time.monotonic() - t0) * 1000))
        except Exception as exc:
            logger.warning("parse: VLM primary failed: %s", exc, exc_info=True)
            vlm_error = str(exc)

        # Strategy 2: OCR fallback (free, for when VLM is unavailable)
        if not has_text:
            ocr_text = await _run_ocr(file_bytes, filename)
            if ocr_text and ocr_text.strip():
                doc_tree = DocumentTree(
                    document_id=doc_id,
                    pages=[Page(page_number=1, regions=[
                        Region(id="r_ocr_0", type="TEXT", content=ocr_text, confidence=0.75),
                    ])],
                    source_format="ocr",
                    text_layer_present=True,
                )
                has_text = True
                auditor.log_stage("ocr_fallback", detail=f"len={len(ocr_text)}")

        if not has_text:
            ext = os.path.splitext(filename)[1].lower()
            from pixora.ocr.vlm_harness import is_vlm_available
            vlm_status = is_vlm_available()
            from pixora.config.settings import settings
            has_key = bool(settings.gemini_api_key)
            error_detail = (
                f"Could not extract text from this {ext.upper().lstrip('.')} file. "
                f"VLM available: {vlm_status}, Gemini key set: {has_key}, "
                f"Key prefix: {settings.gemini_api_key[:8]}... "
            )
            if vlm_error:
                error_detail += f"VLM error: {vlm_error[:200]}"
            if not has_key:
                error_detail += "Set PIXORA_GEMINI_API_KEY (free) for VLM-based extraction."
            raise ValueError(error_detail)

    if not has_text:
        text = file_bytes.decode("utf-8", errors="replace")[:50000]

        # Detect binary garbage — if >40% non-printable, this is not readable text
        printable_ratio = sum(1 for c in text[:2000] if c.isprintable() or c in "\n\r\t") / max(len(text[:2000]), 1)

        if printable_ratio < 0.6:
            ext = os.path.splitext(filename)[1].lower()
            if ext in (".pdf",):
                raise ValueError(
                    f"PDF text extraction failed — this appears to be a scanned/image-only PDF. "
                    f"Connect an OCR provider (Tesseract or Claude Vision) to process scanned documents."
                )
            else:
                raise ValueError(
                    f"File contains binary or unreadable content (readable: {printable_ratio:.0%}). "
                    f"Supported text formats: PDF, DOCX, XLSX, CSV, HTML, TXT, JSON, XML, Markdown."
                )

        doc_tree = DocumentTree(
            document_id=doc_id,
            pages=[Page(page_number=1, regions=[
                Region(id="r_raw_0", type="TEXT", content=text, confidence=0.8),
            ])],
            source_format="raw_fallback",
            text_layer_present=True,
        )

    state = AgentState(
        document_id=doc_id,
        job_id=f"parse_{doc_id[:12]}",
        source_filename=filename,
        raw_bytes=file_bytes,
        document_tree=dict(doc_tree),
        extraction_schema={"schema_id": "auto", "doc_type": "auto", "version": "1.0", "nodes": []},
    )

    # Run agents with audit logging
    auditor = PipelineAuditor(job_id=f"parse_{doc_id[:12]}", document_id=doc_id)

    classifier = ClassifierAgent()
    router_agent = RouterAgent()
    extractor = ExtractorAgent()
    validator = ValidatorAgent()
    scorer = ScorerAgent()

    t0 = time.monotonic()
    state = await classifier.run(state)
    auditor.log_stage("classifier", detail=f"type={state.get('profile',{}).get('doc_type','?')}", duration_ms=int((time.monotonic()-t0)*1000))

    t0 = time.monotonic()
    state = await router_agent.run(state)
    auditor.log_stage("router", detail=f"strategy={state.get('processing_plan',{}).get('ocr_strategy','?')}", duration_ms=int((time.monotonic()-t0)*1000))

    # Tier-based extraction with self-healing loop
    doc_type = state.get("profile", {}).get("doc_type", "document")
    all_text = _collect_text(state.get("document_tree", {}))

    MAX_HEAL_ROUNDS = 3
    heal_round = 0
    engine_used = "regex"

    # If VLM already extracted structured data, use it directly (skip redundant re-extraction)
    if vlm_result and vlm_result.get("extraction") and any(k for k in vlm_result["extraction"] if not k.startswith("_")):
        extraction_result = vlm_result["extraction"]
        extraction_result = _post_process_extraction(extraction_result)
        engine_used = f"vlm_{vlm_result.get('provider', 'unknown')}"
        if vlm_result.get("markdown"):
            extraction_result["_markdown"] = vlm_result["markdown"]
        if vlm_result.get("tables"):
            extraction_result["_tables"] = vlm_result["tables"]
        auditor.log_stage("extractor_round_0", detail=f"tier={tier}, engine={engine_used}, fields={len(extraction_result)}, vlm_passthrough=true", duration_ms=0)
        state["extraction_result"] = extraction_result
        state["extraction_schema"] = {
            "schema_id": "dynamic", "doc_type": doc_type, "version": "1.0",
            "nodes": [{"name": k, "field_type": "STRING"} for k in extraction_result if not k.startswith("_")],
        }
    else:

      for heal_round in range(MAX_HEAL_ROUNDS):
        t0 = time.monotonic()
        extraction_result, engine_used = await _smart_tier_extract(file_bytes, filename, all_text, tier)
        extraction_result = _post_process_extraction(extraction_result)
        auditor.log_stage(
            f"extractor_round_{heal_round}",
            detail=f"tier={tier}, engine={engine_used}, fields={len(extraction_result)}",
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

        state["extraction_result"] = extraction_result
        state["extraction_schema"] = {
            "schema_id": "dynamic", "doc_type": doc_type,
            "version": "1.0",
            "nodes": [{"name": k, "field_type": "STRING"} for k in extraction_result if not k.startswith("_")],
        }

        t0 = time.monotonic()
        state = await validator.run(state)
        auditor.log_stage("validator", detail=f"issues={len(state.get('validator_issues', []))}", duration_ms=int((time.monotonic() - t0) * 1000))

        t0 = time.monotonic()
        state = await scorer.run(state)
        auditor.log_stage("scorer", detail=f"score={state.get('quality_score', 0):.2f}, rec={state.get('recommendation', '?')}", duration_ms=int((time.monotonic() - t0) * 1000))

        quality = state.get("quality_score", 0)
        issues = state.get("validator_issues", [])

        # Self-healing: if quality is acceptable or we've exhausted strategies, stop
        if quality >= 0.7 or heal_round == MAX_HEAL_ROUNDS - 1:
            break

        # Heal strategy 1: if zero fields, try lower tier
        if not any(k for k in extraction_result if not k.startswith("_")):
            if tier != "fast":
                tier = "fast"
                auditor.log_stage("self_heal", detail=f"round={heal_round}, action=fallback_to_fast_tier")
                continue

        # Heal strategy 2: if low quality from regex, try agentic if available
        if engine_used == "regex" and quality < 0.5 and llm_available() and tier == "fast":
            tier = "agentic"
            auditor.log_stage("self_heal", detail=f"round={heal_round}, action=escalate_to_agentic")
            continue

        break

    state["correction_round"] = heal_round

    extraction = state.get("extraction_result", {})

    t0 = time.monotonic()
    grounding = GroundingVerifier().verify(extraction, state.get("document_tree", {}), doc_id)
    auditor.log_stage("grounding_verifier", detail=f"rate={grounding.get('grounding_rate',0):.2f}, hallucinations={len(grounding.get('flagged_hallucinations',[]))}", duration_ms=int((time.monotonic()-t0)*1000))

    auditor.finish(
        status="completed",
        recommendation=state.get("recommendation", ""),
        quality_score=state.get("quality_score", 0),
    )
    audit_summary = auditor.get_summary()

    # Build markdown output, source highlights, and page images
    all_text = _collect_text(state.get("document_tree", {}))

    # For images/PDFs, use PP-StructureV3 (free, local) then fall back to Claude Vision (paid)
    vision_markdown = ""
    vision_items = []
    ext = os.path.splitext(filename)[1].lower()
    is_image = ext in (".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif", ".avif", ".tiff", ".tif", ".bmp", ".gif")
    is_pdf = ext == ".pdf"

    if (is_image or is_pdf) and tier in ("agentic", "agentic_plus"):
        # Strategy 1: PP-StructureV3 (free, local, best layout detection)
        try:
            t0 = time.monotonic()
            paddle_result = await paddle_to_markdown(file_bytes)
            if paddle_result.get("markdown") and len(paddle_result["markdown"].strip()) > 20:
                vision_markdown = paddle_result["markdown"]
                vision_items = paddle_result.get("items", [])
                auditor.log_stage("paddle_structure", detail=f"items={len(vision_items)}, md_len={len(vision_markdown)}", duration_ms=int((time.monotonic()-t0)*1000))
        except Exception:
            pass

        # Strategy 2: Claude Vision (paid, best for bilingual/visual descriptions)
        if not vision_markdown and is_image and llm_available():
            try:
                vm_result = vision_to_markdown(file_bytes)
                if vm_result.get("markdown"):
                    vision_markdown = vm_result["markdown"]
                    audit_summary["vision_tokens"] = vm_result.get("tokens_in", 0) + vm_result.get("tokens_out", 0)
                    audit_summary["vision_cost_usd"] = vm_result.get("cost_usd", 0)
            except Exception:
                pass
            if not vision_items:
                try:
                    vision_items = vision_to_items(file_bytes)
                except Exception:
                    pass

    markdown = vision_markdown if vision_markdown else _build_markdown(filename, doc_type, extraction, state.get("quality_report", {}), dict(grounding))
    highlights = _build_highlights(all_text, extraction, grounding)

    # Render document pages as images with real text positions
    try:
        pages = render_pages(file_bytes, filename, dpi=150)
    except Exception:
        pages = []

    # Compute bounding boxes using real text spans from PDF or OCR words
    ocr_words = None
    for p in state.get("document_tree", {}).get("pages", []):
        for r in p.get("regions", []):
            if r.get("words"):
                ocr_words = [dict(w) for w in r["words"]]
                break

    # For images without text_spans, run EasyOCR to get word-level bboxes for highlighting
    if not ocr_words and pages:
        try:
            from PIL import Image as _PILImage
            _img = _PILImage.open(io.BytesIO(file_bytes))
            if _img.mode not in ("RGB", "L"):
                _img = _img.convert("RGB")
            _buf = io.BytesIO()
            _img.save(_buf, format="PNG")
            _png = _buf.getvalue()

            _ocr_engine = EasyOCREngine()
            _ocr_regions = await _ocr_engine.recognize(_png, languages=["en"], page_number=1)
            ocr_words = []
            for r in _ocr_regions:
                for w in r.get("words", []):
                    wb = w.get("bbox", {})
                    if wb and w.get("text", "").strip() and w.get("confidence", 0) >= 0.3:
                        ocr_words.append({"text": w["text"], "bbox": dict(wb)})
            logger.info("parse: OCR for bboxes got %d words", len(ocr_words))
        except Exception as exc:
            logger.warning("parse: OCR for bboxes failed: %s", exc)
            ocr_words = []

    # If still no ocr_words, create approximate bboxes from extraction values
    if not ocr_words and extraction and pages:
        ocr_words = []
        page_h = pages[0].get("height", 800) if pages else 800
        page_w = pages[0].get("width", 600) if pages else 600
        field_count = len([k for k in extraction if not k.startswith("_")])
        y_step = page_h / max(field_count + 2, 5)
        y_pos = 40
        for key, value in extraction.items():
            if key.startswith("_") or value is None:
                continue
            val_str = str(value)[:80]
            ocr_words.append({
                "text": val_str,
                "bbox": {"x": 50, "y": y_pos, "width": min(len(val_str) * 8, page_w - 100), "height": 20, "page": 1},
            })
            y_pos += y_step

    # Also build text_spans from ocr_words so document viewer can render them
    if ocr_words and pages and all(len(p.get("text_spans", [])) == 0 for p in pages):
        for p in pages:
            spans = []
            for w in ocr_words:
                wb = w.get("bbox", {})
                if wb:
                    spans.append({
                        "text": w["text"],
                        "x": wb.get("x", 0),
                        "y": wb.get("y", 0),
                        "width": wb.get("width", 0),
                        "height": wb.get("height", 0),
                    })
            p["text_spans"] = spans

    field_bboxes = compute_field_bboxes(extraction, pages, ocr_words)

    elapsed = int((time.monotonic() - start) * 1000)

    if not vision_items and extraction:
        vision_items = _build_items_from_extraction(extraction, field_bboxes)

    return {
        "doc_type": doc_type,
        "extraction": extraction,
        "markdown": markdown,
        "text": all_text[:50000],
        "items": vision_items,
        "quality_report": state.get("quality_report", {}),
        "grounding_report": dict(grounding),
        "citations": grounding.get("citations", []),
        "field_confidences": grounding.get("field_confidences", []),
        "trace": state.get("decision_trace", []),
        "correction_rounds": state.get("correction_round", 0) + 1,
        "processing_time_ms": elapsed,
        "audit": audit_summary,
        "source_text": all_text[:50000],
        "highlights": highlights,
        "pages": pages,
        "field_bboxes": field_bboxes,
    }


def _reconstruct_lines(regions: list) -> str:
    """Reconstruct text with line breaks from PaddleOCR word-level bboxes."""
    words = []
    for r in regions:
        for w in r.get("words", []):
            if w.get("text", "").strip() and w.get("confidence", 0) >= 0.3:
                words.append(w)
    if not words:
        return " ".join(r.get("text", "") for r in regions)

    words.sort(key=lambda w: (w["bbox"]["y"], w["bbox"]["x"]))
    lines: list[str] = []
    current_line: list[str] = []
    last_y = words[0]["bbox"]["y"]

    for w in words:
        y = w["bbox"]["y"]
        h = w["bbox"].get("height", 20)
        if abs(y - last_y) > max(h * 0.5, 8) and current_line:
            lines.append(" ".join(current_line))
            current_line = []
        current_line.append(w["text"])
        last_y = y
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)


def _detect_languages(file_bytes: bytes) -> list[str]:
    """Detect likely languages from image using a quick EasyOCR pass."""
    from PIL import Image
    import io

    LANG_SCRIPTS = {
        "hi": r"[ऀ-ॿ]",
        "ar": r"[؀-ۿ]",
        "zh": r"[一-鿿]",
        "ja": r"[぀-ゟ゠-ヿ]",
        "ko": r"[가-힯]",
        "th": r"[฀-๿]",
        "ta": r"[஀-௿]",
        "te": r"[ఀ-౿]",
        "bn": r"[ঀ-৿]",
        "ru": r"[Ѐ-ӿ]",
        "de": r"[äöüßÄÖÜ]",
        "fr": r"[àâéèêëîïôùûüçÀÂÉÈÊËÎÏÔÙÛÜÇ]",
        "es": r"[áéíóúñüÁÉÍÓÚÑÜ¿¡]",
    }

    try:
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        engine = EasyOCREngine()
        regions = engine._get_reader_sync(["en"])
        import numpy as np
        arr = np.array(img)
        results = regions.readtext(arr)
        all_text = " ".join(t for _, t, _ in results if t.strip())

        detected = ["en"]
        for lang, pattern in LANG_SCRIPTS.items():
            if re.search(pattern, all_text):
                detected.append(lang)
        return detected[:3]
    except Exception:
        return ["en"]


async def _run_ocr(file_bytes: bytes, filename: str) -> str:
    """Run PaddleOCR (primary) or EasyOCR (fallback) on image bytes.
    Converts any image format (WEBP, HEIC, AVIF, etc.) to PNG first."""
    from PIL import Image
    import io

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    except Exception as exc:
        logger.warning("_run_ocr: image conversion failed: %s", exc)
        png_bytes = file_bytes

    languages = _detect_languages(file_bytes)

    # Try PaddleOCR first — better multi-language support
    try:
        paddle = PaddleOCREngine()
        regions = await paddle.recognize(png_bytes, languages=languages, page_number=1)
        text = " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
        if text.strip() and len(text.strip()) > 10:
            return _reconstruct_lines(regions)
    except Exception:
        pass

    # Fallback to EasyOCR
    engine = EasyOCREngine()
    regions = await engine.recognize(png_bytes, languages=languages, page_number=1)

    words = []
    for r in regions:
        for w in r.get("words", []):
            conf = w.get("confidence", 0)
            text = w.get("text", "").strip()
            if not text:
                continue
            if conf < 0.4:
                continue
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
            if conf < 0.55 and ascii_ratio < 0.3 and len(languages) <= 1:
                continue
            words.append(w)

    if not words:
        return " ".join(r["text"] for r in regions if r.get("text", "").strip())

    words.sort(key=lambda w: (w["bbox"]["y"], w["bbox"]["x"]))

    lines: list[str] = []
    current_line: list[str] = []
    last_y = words[0]["bbox"]["y"] if words else 0

    for w in words:
        y = w["bbox"]["y"]
        h = w["bbox"].get("height", 20)
        if abs(y - last_y) > h * 0.6 and current_line:
            lines.append(" ".join(current_line))
            current_line = []
        current_line.append(w["text"])
        last_y = y

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


_DOCLING_SUPPORTED_EXTS = {".pdf", ".docx", ".pptx", ".html", ".htm", ".png", ".jpg", ".jpeg",
                            ".tiff", ".tif", ".bmp", ".csv", ".xlsx", ".md"}


def _build_items_from_extraction(extraction: dict, field_bboxes: list) -> list[dict]:
    items = []
    bbox_map = {b["field"]: b for b in field_bboxes} if field_bboxes else {}
    for key, value in extraction.items():
        if key.startswith("_") or value is None:
            continue
        label = key.replace("_", " ").title()
        item_type = "field"
        if any(kw in key for kw in ("date", "dob", "birth")):
            item_type = "date"
        elif any(kw in key for kw in ("name", "father", "mother", "husband")):
            item_type = "name"
        elif any(kw in key for kw in ("number", "account", "pan", "id", "vin", "mrn")):
            item_type = "id"
        elif any(kw in key for kw in ("total", "amount", "price", "fee", "cost", "tax", "subtotal")):
            item_type = "amount"
        item = {"type": item_type, "field": key, "label": label, "value": str(value)}
        if key in bbox_map:
            item["bbox"] = bbox_map[key]
        items.append(item)
    return items


def _tier_extract(file_bytes: bytes, filename: str, text: str, tier: str) -> tuple[dict, str]:
    """Route extraction to the right engine based on tier.
    Returns (extraction_dict, engine_name)."""
    ext = os.path.splitext(filename)[1].lower()

    if tier in ("agentic", "agentic_plus") and llm_available():
        result = extract_with_llm(text)
        if result and any(k for k in result if not k.startswith("_")):
            return result, "claude"

    if tier in ("agentic", "agentic_plus", "cost_effective") and ext in _DOCLING_SUPPORTED_EXTS:
        try:
            docling_result = extract_with_docling(file_bytes, filename)
            fields = docling_result.get("fields", {})
            if fields:
                fields["_markdown"] = docling_result.get("markdown", "")
                fields["_tables"] = docling_result.get("tables", [])
                fields["_meta"] = {"engine": "docling", "page_count": docling_result.get("page_count", 0)}
                return fields, "docling"
        except Exception:
            pass

    result = _dynamic_extract(text)
    return result, "regex"


async def _smart_tier_extract(file_bytes: bytes, filename: str, text: str, tier: str) -> tuple[dict, str]:
    """Smart extraction — uses LLM/VLM when available, falls back to regex.
    This is the generic solution: no hardcoded rules, the AI understands context."""
    import asyncio

    try:
        from pixora.extraction.smart_extractor import smart_extract
        result, engine = await smart_extract(text=text, image_bytes=file_bytes)
        if result and any(k for k in result if not k.startswith("_")):
            return result, engine
    except Exception:
        pass

    return _tier_extract(file_bytes, filename, text, tier)


_SECTION_HEADER_RE = re.compile(
    r"^(section\s*\d|part\s*\d|chapter\s*\d|appendix|table\s*of\s*contents|"
    r"notes?$|disclaimer$|instructions?$|vitals?$|lab\s*results?|"
    r"current\s*medications?$|references?$|items?$)",
    re.IGNORECASE,
)


def _dynamic_extract(text: str) -> dict:
    """Dynamically discover and extract ALL key-value pairs, tables, and structured
    data from any document — no predefined schema required."""

    if not text or not text.strip():
        return {}

    sample = text[:2000]
    if sum(1 for c in sample if c.isprintable() or c in "\n\r\t") / max(len(sample), 1) < 0.5:
        return {}

    result: dict = {}
    lines = text.split("\n")

    known_labels = {
        "name", "full name", "first name", "last name",
        "father s name", "fathers name", "father name", "father's name",
        "mother s name", "mother name", "mother's name",
        "date of birth", "dob", "husband s name", "husband name",
        "address", "gender", "sex", "phone", "email", "mobile",
        "permanent account number", "account number", "pan", "pan number",
        "aadhaar", "aadhaar number", "uid", "vid",
        "voter id", "voter id number", "election commission",
        "driving licence", "licence number", "license number",
        "passport number", "passport no",
        "policy number", "tracking number", "order number",
        "invoice number", "invoice date", "due date", "bill to",
        "vendor name", "total", "subtotal", "tax", "amount",
        "title", "authors", "journal", "doi", "abstract",
    }

    stop_words = {
        "signature", "sign", "photo", "photograph", "thumb",
        "seal", "stamp", "logo", "barcode", "qr", "qr code",
    }

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 500:
            continue

        if sum(1 for c in stripped if ord(c) > 127) / max(len(stripped), 1) > 0.5:
            continue

        # Pattern 1: "Label: Value" on same line
        if ":" in stripped:
            colon_pos = stripped.index(":")
            label = stripped[:colon_pos].strip()
            value = stripped[colon_pos + 1:].strip()

            if not label or len(label) > 80 or len(label) < 2:
                continue
            if re.search(r"https?://|www\.", label):
                continue
            alpha_ratio = sum(1 for c in label if c.isalpha() or c in " .-_#/()") / max(len(label), 1)
            if alpha_ratio < 0.5:
                continue

            field_name = _to_field_name(label)
            if not field_name:
                continue

            if _SECTION_HEADER_RE.search(label):
                continue

            if value:
                for sw in stop_words:
                    if value.lower().endswith(" " + sw):
                        value = value[:-(len(sw) + 1)].strip()
                    if value.lower().endswith("/" + sw):
                        value = value[:-(len(sw) + 1)].strip()

                value = _clean_extracted_value(value)
                if field_name not in result:
                    result[field_name] = value

        # Pattern 2: Label line followed by value on next line (ID cards, forms)
        elif stripped[0].isalpha() and ":" not in stripped:
            lower_stripped = stripped.lower().strip()

            if lower_stripped in stop_words or any(lower_stripped.startswith(sw) for sw in stop_words):
                continue

            is_known = any(lower_stripped == lbl or lower_stripped.startswith(lbl) for lbl in known_labels)

            is_all_caps_value = (
                stripped == stripped.upper()
                and len(stripped) > 3
                and any(c.isalpha() for c in stripped)
                and not is_known
            )
            if is_all_caps_value:
                continue

            is_label_like = (
                len(stripped) < 40
                and sum(1 for c in stripped if c.isalpha() or c in " '.-/") / max(len(stripped), 1) > 0.8
                and not stripped[0].isdigit()
                and not _SECTION_HEADER_RE.search(stripped)
                and stripped != stripped.upper()
            )

            if is_known or is_label_like:
                for next_idx in range(idx + 1, min(idx + 3, len(lines))):
                    next_line = lines[next_idx].strip()
                    if not next_line:
                        continue
                    next_lower = next_line.lower().strip()
                    if any(next_lower == lbl or next_lower.startswith(lbl) for lbl in known_labels):
                        break
                    if ":" in next_line and next_line.index(":") < 40:
                        break
                    if next_lower in stop_words:
                        break

                    for sw in stop_words:
                        if next_line.lower().endswith(" " + sw):
                            next_line = next_line[:-(len(sw) + 1)].strip()

                    field_name = _to_field_name(stripped)
                    if field_name and field_name not in result:
                        result[field_name] = _clean_extracted_value(next_line)
                    break

        # Pattern 3: "label value" without colon (e.g. "date 2024-01-15", "total $42.99")
        # Runs independently — check every non-colon line
        if ":" not in stripped:
            m = re.match(r"^([a-zA-Z][\w\s]{1,25}?)\s+([$\d][\d,.$/%\-]+.*)$", stripped)
            if m:
                label = m.group(1).strip()
                value = m.group(2).strip()
                if len(label) >= 2 and not _SECTION_HEADER_RE.search(label):
                    field_name = _to_field_name(label)
                    if field_name and field_name not in result:
                        result[field_name] = _clean_extracted_value(value)

    # Pattern 4: Table rows (pipe-separated)
    table_rows = [l.strip() for l in lines if "|" in l and l.count("|") >= 2]
    if len(table_rows) >= 2:
        result["_tables"] = table_rows

    return result


def _clean_extracted_value(value: str) -> str:
    """Clean JSON artifacts, extra quotes, and trailing noise from extracted values."""
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    value = value.rstrip(",").strip()
    return value


def _post_process_extraction(extraction: dict) -> dict:
    """Self-healing post-processor: clean values, remove junk fields, deduplicate."""
    cleaned: dict = {}
    for k, v in extraction.items():
        if k.startswith("_"):
            cleaned[k] = v
            continue
        if not isinstance(v, str):
            cleaned[k] = v
            continue
        # Skip section-header-as-field
        if _SECTION_HEADER_RE.search(k.replace("_", " ")):
            continue
        # Skip fields whose value is just another label:value (misparse)
        if v.count(":") > 2 and len(v) > 150:
            continue
        # Clean JSON artifacts from values
        v = _clean_extracted_value(v)
        if v:
            cleaned[k] = v
    return cleaned


def _to_field_name(label: str) -> str | None:
    """Convert a label like 'Invoice Number' to 'invoice_number'."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", label).strip()
    if not cleaned or len(cleaned) < 2:
        return None
    field = re.sub(r"\s+", "_", cleaned.lower())
    if len(field) > 60:
        return None
    return field


def _build_highlights(source_text: str, extraction: dict, grounding: dict) -> list[dict]:
    """Build character-offset highlights with multi-strategy matching."""
    highlights = []
    text_lower = source_text.lower()
    used_ranges: list[tuple[int, int]] = []

    evidence_map = {}
    for ev in grounding.get("evidence", []):
        evidence_map[ev.get("field", "")] = ev

    def _overlaps(start: int, end: int) -> bool:
        return any(s < end and start < e for s, e in used_ranges)

    def _normalize_ws(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    for field, value in extraction.items():
        if field.startswith("_") or value is None:
            continue
        val_str = str(value).strip()
        if not val_str or len(val_str) < 2:
            continue

        ev = evidence_map.get(field, {})
        match_type = ev.get("match_type", "none")
        found = False

        # Strategy 1: exact match
        idx = source_text.find(val_str)
        if idx >= 0 and not _overlaps(idx, idx + len(val_str)):
            highlights.append({"field": field, "value": val_str, "start": idx, "end": idx + len(val_str), "match_type": "exact", "grounded": True})
            used_ranges.append((idx, idx + len(val_str)))
            found = True

        # Strategy 2: case-insensitive
        if not found:
            idx = text_lower.find(val_str.lower())
            if idx >= 0 and not _overlaps(idx, idx + len(val_str)):
                highlights.append({"field": field, "value": val_str, "start": idx, "end": idx + len(val_str), "match_type": "normalized", "grounded": True})
                used_ranges.append((idx, idx + len(val_str)))
                found = True

        # Strategy 3: whitespace-normalized match
        if not found:
            val_norm = _normalize_ws(val_str).lower()
            text_norm = _normalize_ws(source_text).lower()
            norm_idx = text_norm.find(val_norm)
            if norm_idx >= 0:
                real_start = _map_normalized_offset(source_text, norm_idx)
                real_end = min(real_start + len(val_str) + 20, len(source_text))
                if not _overlaps(real_start, real_end):
                    highlights.append({"field": field, "value": val_str, "start": real_start, "end": real_end, "match_type": "normalized", "grounded": True})
                    used_ranges.append((real_start, real_end))
                    found = True

        # Strategy 4: word-token overlap — find best window
        if not found and len(val_str) > 5:
            val_words = val_str.lower().split()
            if len(val_words) >= 2:
                best_idx, best_end, best_score = -1, -1, 0
                for i in range(len(source_text) - 10):
                    if source_text[i] not in (" ", "\n", "\t") and i > 0:
                        continue
                    window = source_text[i:i + len(val_str) + 50].lower()
                    window_words = window.split()
                    overlap = sum(1 for w in val_words if w in window_words)
                    score = overlap / len(val_words)
                    if score > best_score and score >= 0.5:
                        best_score = score
                        best_idx = i
                        best_end = min(i + len(val_str) + 10, len(source_text))
                if best_idx >= 0 and not _overlaps(best_idx, best_end):
                    highlights.append({"field": field, "value": val_str, "start": best_idx, "end": best_end, "match_type": "fuzzy", "grounded": best_score >= 0.7})
                    used_ranges.append((best_idx, best_end))
                    found = True

        # Strategy 5: partial (first significant chunk)
        if not found:
            partial = val_str[:min(30, len(val_str))]
            idx = text_lower.find(partial.lower())
            if idx >= 0:
                end_idx = min(idx + len(val_str), len(source_text))
                if not _overlaps(idx, end_idx):
                    highlights.append({"field": field, "value": val_str, "start": idx, "end": end_idx, "match_type": "partial", "grounded": match_type in ("exact", "fuzzy", "normalized")})
                    used_ranges.append((idx, end_idx))
                    found = True

        if not found:
            highlights.append({"field": field, "value": val_str, "start": -1, "end": -1, "match_type": "not_found", "grounded": False})

    highlights.sort(key=lambda h: h["start"] if h["start"] >= 0 else 999999)
    return highlights


def _map_normalized_offset(original: str, norm_offset: int) -> int:
    """Map an offset in whitespace-normalized text back to the original."""
    norm_pos = 0
    in_ws = False
    for i, ch in enumerate(original):
        if ch in (" ", "\n", "\t", "\r"):
            if not in_ws:
                norm_pos += 1
                in_ws = True
        else:
            norm_pos += 1
            in_ws = False
        if norm_pos >= norm_offset:
            return i
    return len(original)


def _collect_text(doc_tree: dict) -> str:
    parts = []
    for page in doc_tree.get("pages", []):
        for region in page.get("regions", []):
            parts.append(region.get("content", ""))
    return "\n\n".join(parts)


async def _run_pipeline_per_page(file_bytes: bytes, filename: str, doc_id: str, tier: str) -> dict:
    start = time.monotonic()

    doc_tree = None
    try:
        reader = _reader_registry.get_reader(filename)
        doc_tree = await reader.read(file_bytes, filename)
    except Exception:
        pass

    if not doc_tree or not doc_tree.get("pages"):
        return await _run_pipeline(file_bytes, filename, doc_id, tier)

    page_extractions = {}
    all_citations = []
    all_confidences = []

    for page in doc_tree["pages"]:
        page_num = page.get("page_number", 1)
        page_text = "\n".join(r.get("content", "") for r in page.get("regions", []))
        if not page_text.strip():
            continue

        page_extraction, engine = _tier_extract(file_bytes, filename, page_text, tier)
        page_extraction = _post_process_extraction(page_extraction)

        page_tree = DocumentTree(
            document_id=doc_id,
            pages=[page],
            source_format=doc_tree.get("source_format", "unknown"),
            text_layer_present=True,
        )
        page_grounding = GroundingVerifier().verify(page_extraction, dict(page_tree), doc_id)

        for c in page_grounding.get("citations", []):
            c["page"] = page_num
            all_citations.append(c)
        all_confidences.extend(page_grounding.get("field_confidences", []))

        page_extractions[f"page_{page_num}"] = page_extraction

    elapsed = int((time.monotonic() - start) * 1000)

    return {
        "doc_type": "multi_page",
        "extraction": page_extractions,
        "markdown": "",
        "quality_report": {},
        "grounding_report": {},
        "citations": all_citations,
        "field_confidences": all_confidences,
        "trace": [],
        "correction_rounds": 1,
        "processing_time_ms": elapsed,
        "audit": {},
        "source_text": "",
        "highlights": [],
        "pages": [],
        "field_bboxes": [],
    }


def _build_markdown(filename: str, doc_type: str, extraction: dict, quality: dict, grounding: dict) -> str:
    lines = [f"# {filename}", ""]
    lines.append(f"**Document Type:** {doc_type}")
    lines.append(f"**Quality Score:** {quality.get('overall_score', 0)*100:.1f}%")
    lines.append(f"**Grounding Rate:** {grounding.get('grounding_rate', 0)*100:.1f}%")
    lines.append(f"**Recommendation:** {quality.get('recommendation', 'unknown')}")
    lines.append("")

    if extraction:
        lines.append("## Extracted Fields")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("| --- | --- |")
        for k, v in extraction.items():
            val = str(v) if v is not None else "*not found*"
            lines.append(f"| {k.replace('_', ' ').title()} | {val} |")
        lines.append("")

    halls = grounding.get("flagged_hallucinations", [])
    if halls:
        lines.append("## Hallucination Warnings")
        lines.append("")
        for h in halls:
            lines.append(f"- **{h}**: Value not found in source document")
        lines.append("")

    issues = quality.get("issues", [])
    if issues:
        lines.append("## Quality Issues")
        lines.append("")
        for issue in issues:
            sev = issue.get("severity", "info")
            msg = issue.get("message", "")
            lines.append(f"- [{sev.upper()}] {msg}")

    return "\n".join(lines)


def _get_auto_schema(doc_type: str) -> list[dict] | None:
    from pixora.evals.benchmarks.schemas import (
        INVOICE_SCHEMA, RECEIPT_SCHEMA, CONTRACT_SCHEMA, MEDICAL_SCHEMA,
        FORM_SCHEMA, SCIENTIFIC_SCHEMA, BANK_STATEMENT_SCHEMA,
        INSURANCE_SCHEMA, SHIPPING_SCHEMA, GOVERNMENT_SCHEMA,
    )
    ID_CARD_SCHEMA = [
        {"name": "card_type", "field_type": "STRING", "description": "Type of ID card", "aliases": ["permanent account number", "pan", "aadhaar", "voter id", "driving licence", "passport"]},
        {"name": "id_number", "field_type": "STRING", "description": "ID/PAN/Aadhaar number", "required": True, "aliases": ["pan", "permanent account number", "aadhaar", "uid", "dl no", "passport no"]},
        {"name": "full_name", "field_type": "STRING", "description": "Name on ID", "required": True, "aliases": ["name"]},
        {"name": "father_name", "field_type": "STRING", "description": "Father's name", "aliases": ["father s name", "fathers name", "father name", "s/o", "d/o"]},
        {"name": "date_of_birth", "field_type": "DATE", "description": "Date of birth", "aliases": ["dob", "date of birth", "birth date"]},
        {"name": "gender", "field_type": "STRING", "description": "Gender", "aliases": ["sex"]},
        {"name": "address", "field_type": "STRING", "description": "Address on ID"},
        {"name": "issue_date", "field_type": "DATE", "description": "Date of issue"},
        {"name": "issuing_authority", "field_type": "STRING", "description": "Issuing authority", "aliases": ["income tax department", "uidai", "govt of india"]},
    ]

    return {
        "invoice": INVOICE_SCHEMA,
        "receipt": RECEIPT_SCHEMA,
        "contract": CONTRACT_SCHEMA,
        "medical": MEDICAL_SCHEMA,
        "form": FORM_SCHEMA,
        "scientific_paper": SCIENTIFIC_SCHEMA,
        "bank_statement": BANK_STATEMENT_SCHEMA,
        "insurance": INSURANCE_SCHEMA,
        "shipping": SHIPPING_SCHEMA,
        "government": GOVERNMENT_SCHEMA,
        "id_card": ID_CARD_SCHEMA,
        "pan_card": ID_CARD_SCHEMA,
    }.get(doc_type)


def _infer_schema_from_text(text: str) -> list[dict] | None:
    """Auto-detect field: value patterns in text and create schema nodes."""

    # Reject binary garbage
    sample = text[:2000]
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\r\t")
    if printable / max(len(sample), 1) < 0.7:
        return None

    nodes = []
    seen = set()
    for line in text.split("\n"):
        line = line.strip()
        if ":" not in line or len(line) > 200:
            continue
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        label = parts[0].strip()
        value = parts[1].strip()
        if not label or not value or len(label) > 60 or len(label) < 2:
            continue
        if re.search(r"https?://|www\.", label, re.IGNORECASE):
            continue
        field_name = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        if not field_name or field_name in seen:
            continue
        seen.add(field_name)

        field_type = "STRING"
        if re.match(r"^\$?[\d,]+\.?\d*$", value.replace(",", "").replace("$", "")):
            field_type = "CURRENCY" if "$" in value else "NUMBER"
        elif re.match(r"\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4}", value):
            field_type = "DATE"

        nodes.append({
            "name": field_name,
            "field_type": field_type,
            "description": label,
            "aliases": [label.lower()],
        })

    return nodes if nodes else None
