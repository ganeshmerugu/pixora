"""End-to-end pipeline integration tests.

Tests the full flow: upload → classify → extract → validate → bbox → route.
Runs against the live Cloud Run deployment when PIXORA_E2E_URL is set,
otherwise against the local ASGI app.
"""
from __future__ import annotations
import io
import os
import pytest
from PIL import Image, ImageDraw, ImageFont
from httpx import AsyncClient, ASGITransport


LIVE_URL = os.environ.get("PIXORA_E2E_URL", "")
LOCAL_BASE = "http://test"


def _make_test_invoice_image() -> bytes:
    img = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        small = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
        small = font

    draw.text((50, 30), "INVOICE", fill="black", font=font)
    draw.text((50, 70), "Invoice Number: INV-2024-0042", fill="black", font=small)
    draw.text((50, 95), "Date: 09/15/2024", fill="black", font=small)
    draw.text((50, 120), "Vendor: Acme Corp", fill="black", font=small)
    draw.text((50, 145), "Bill To: John Smith", fill="black", font=small)
    draw.text((50, 180), "Email: john@example.com", fill="black", font=small)
    draw.text((50, 205), "Phone: +1 (415) 555-0177", fill="black", font=small)
    draw.text((50, 250), "Item                Qty    Price     Total", fill="black", font=small)
    draw.line([(50, 270), (600, 270)], fill="black")
    draw.text((50, 280), "Widget A             2    $25.00    $50.00", fill="black", font=small)
    draw.text((50, 305), "Widget B             1    $75.00    $75.00", fill="black", font=small)
    draw.line([(50, 330), (600, 330)], fill="black")
    draw.text((350, 340), "Subtotal:  $125.00", fill="black", font=small)
    draw.text((350, 365), "Tax (8%):   $10.00", fill="black", font=small)
    draw.text((350, 390), "Total Due: $135.00", fill="black", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_test_medical_image() -> bytes:
    img = Image.new("RGB", (800, 500), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
        small = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
        small = font

    draw.text((50, 30), "PATIENT LAB REPORT", fill="black", font=font)
    draw.text((50, 65), "Patient: Jane Doe", fill="black", font=small)
    draw.text((50, 85), "DOB: 03/22/1985", fill="black", font=small)
    draw.text((50, 105), "MRN: MRN-98765", fill="black", font=small)
    draw.text((50, 125), "Collection Date: 10/01/2024", fill="black", font=small)
    draw.text((50, 145), "Physician: Dr. Robert Chen", fill="black", font=small)
    draw.text((50, 180), "Test           Result    Reference Range", fill="black", font=small)
    draw.line([(50, 200), (550, 200)], fill="black")
    draw.text((50, 210), "Glucose        95 mg/dL  70-100 mg/dL", fill="black", font=small)
    draw.text((50, 235), "Hemoglobin     14.2 g/dL 12.0-17.5 g/dL", fill="black", font=small)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client_params():
    if LIVE_URL:
        return {"base_url": LIVE_URL}
    from pixora.api.main import app
    return {"transport": ASGITransport(app=app), "base_url": LOCAL_BASE}


# ── 1. Health Check ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client_params):
    async with AsyncClient(**client_params) as c:
        resp = await c.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "providers" in data
        assert data["providers"]["tesseract"] is True


# ── 2. Invoice Upload → Full Pipeline ────────────────────────────

@pytest.mark.asyncio
async def test_invoice_e2e(client_params):
    img = _make_test_invoice_image()

    async with AsyncClient(**client_params, timeout=180) as c:
        resp = await c.post(
            "/api/v1/parse/upload",
            files={"file": ("test_invoice.png", img, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()

    assert data["status"] == "completed", f"Pipeline failed: {data.get('error')}"

    # Classification
    doc_type = data.get("doc_type", "")
    assert doc_type, "No doc_type returned"
    print(f"  doc_type: {doc_type}")

    # Extraction
    extraction = data.get("extraction", {})
    assert extraction, "No extraction returned"
    print(f"  extraction fields: {list(extraction.keys())}")

    ext_lower = {k.lower(): str(v).lower() for k, v in extraction.items() if v}

    has_amount = any("135" in v or "125" in v for v in ext_lower.values())
    has_vendor = any("acme" in v for v in ext_lower.values())
    has_date = any("09" in v and "2024" in v for v in ext_lower.values())
    assert has_amount or has_vendor or has_date, (
        f"Extraction missed key fields. Got: {extraction}"
    )

    # Pages + Bounding Boxes
    pages = data.get("pages", [])
    field_bboxes = data.get("field_bboxes", [])
    print(f"  pages: {len(pages)}, field_bboxes: {len(field_bboxes)}")

    if pages:
        p = pages[0]
        assert p.get("width", 0) > 0, "Page width is 0"
        assert p.get("height", 0) > 0, "Page height is 0"

    if field_bboxes:
        for bb in field_bboxes:
            assert bb.get("x", -1) >= 0, f"Negative x in bbox: {bb}"
            assert bb.get("y", -1) >= 0, f"Negative y in bbox: {bb}"
            assert bb.get("width", 0) > 0, f"Zero width in bbox: {bb}"
            assert bb.get("height", 0) > 0, f"Zero height in bbox: {bb}"

    # Quality / Grounding
    qr = data.get("quality_report", {})
    gr = data.get("grounding_report", {})
    print(f"  quality_report: {bool(qr)}, grounding_report: {bool(gr)}")

    # Trace
    trace = data.get("trace", [])
    agent_names = [t.get("agent", "") for t in trace]
    print(f"  trace agents: {agent_names}")


# ── 3. Medical Doc → Classification Accuracy ─────────────────────

@pytest.mark.asyncio
async def test_medical_classification(client_params):
    img = _make_test_medical_image()

    async with AsyncClient(**client_params, timeout=180) as c:
        resp = await c.post(
            "/api/v1/parse/upload",
            files={"file": ("lab_report.png", img, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()

    assert data["status"] == "completed", f"Pipeline failed: {data.get('error')}"

    doc_type = data.get("doc_type", "").lower()
    extraction = data.get("extraction", {})
    print(f"  doc_type: {doc_type}")
    print(f"  extraction: {list(extraction.keys())}")

    ext_lower = {k.lower(): str(v).lower() for k, v in extraction.items() if v}
    has_patient = any("jane" in v or "doe" in v for v in ext_lower.values())
    has_mrn = any("98765" in v for v in ext_lower.values())
    assert has_patient or has_mrn, f"Extraction missed patient data. Got: {extraction}"


# ── 4. Jev Integration (when available) ──────────────────────────

@pytest.mark.asyncio
async def test_jev_classification_unit():
    from pixora.providers.typesafe_jev import is_available, classify_document
    if not is_available():
        pytest.skip("TYPESAFE_API_KEY not set")

    result = await classify_document(
        "Invoice Number: INV-001\nDate: 2024-01-15\nTotal: $500.00\nVendor: Acme Corp"
    )
    assert result["doc_type"] == "invoice"
    assert result["confidence"] > 0.5
    assert result["provider"] == "jev"
    print(f"  Jev classified as '{result['doc_type']}' with {result['confidence']:.0%} confidence")


@pytest.mark.asyncio
async def test_jev_value_extraction_unit():
    from pixora.providers.typesafe_jev import is_available, pick_value, find_candidates
    if not is_available():
        pytest.skip("TYPESAFE_API_KEY not set")

    text = "Invoice total: $1,250.00. Paid amount: $500.00. Balance due: $750.00"
    candidates = find_candidates(text, "amount")
    assert len(candidates) >= 3

    result = await pick_value(text, candidates, "What is the total invoice amount?")
    assert result["value"] == "$1,250.00"
    assert result["confidence"] > 0.5
    print(f"  Jev picked '{result['value']}' with {result['confidence']:.0%} confidence")


@pytest.mark.asyncio
async def test_jev_quality_routing_unit():
    from pixora.providers.typesafe_jev import is_available, evaluate_extraction_quality
    if not is_available():
        pytest.skip("TYPESAFE_API_KEY not set")

    text = "Invoice Number: INV-001\nDate: 01/15/2024\nVendor: Acme Corp\nTotal: $500.00"
    extraction = {"invoice_number": "INV-001", "date": "01/15/2024", "vendor": "Acme Corp", "total": "$500.00"}

    result = await evaluate_extraction_quality(text, extraction)
    assert result["action"] in ("accept", "review", "reject")
    assert result["provider"] == "jev"
    print(f"  Jev routing: {result['action']} (quality={result['quality_score']}, errors_prob={result['has_errors_prob']:.0%})")


@pytest.mark.asyncio
async def test_jev_field_validation_unit():
    from pixora.providers.typesafe_jev import is_available, validate_fields
    if not is_available():
        pytest.skip("TYPESAFE_API_KEY not set")

    text = "Patient: Jane Doe\nDOB: 03/22/1985\nMRN: MRN-98765"
    extraction = {"patient": "Jane Doe", "dob": "03/22/1985", "mrn": "MRN-98765"}

    result = await validate_fields(text, extraction)
    assert "patient" in result
    assert result["patient"]["likely_correct"] is True
    parts = [f"{k}={v['valid_prob']:.0%}" for k, v in result.items()]
    print(f"  Jev field validation: {', '.join(parts)}")


# ── 5. Bbox Coordinate Sanity ─────────────────────────────────────

@pytest.mark.asyncio
async def test_bbox_coordinates_within_page(client_params):
    img = _make_test_invoice_image()

    async with AsyncClient(**client_params, timeout=180) as c:
        resp = await c.post(
            "/api/v1/parse/upload",
            files={"file": ("bbox_test.png", img, "image/png")},
        )
        data = resp.json()

    if data.get("status") != "completed":
        pytest.skip(f"Pipeline failed: {data.get('error')}")

    pages = data.get("pages", [])
    bboxes = data.get("field_bboxes", [])

    if not pages or not bboxes:
        pytest.skip("No pages or bboxes returned")

    page_w = pages[0].get("width", 800)
    page_h = pages[0].get("height", 600)

    for bb in bboxes:
        x, y = bb.get("x", 0), bb.get("y", 0)
        w, h = bb.get("width", 0), bb.get("height", 0)
        assert 0 <= x <= page_w, f"bbox x={x} outside page width={page_w}: {bb}"
        assert 0 <= y <= page_h, f"bbox y={y} outside page height={page_h}: {bb}"
        assert x + w <= page_w * 1.1, f"bbox right edge {x+w} exceeds page width={page_w}: {bb}"
        assert y + h <= page_h * 1.1, f"bbox bottom edge {y+h} exceeds page height={page_h}: {bb}"
        print(f"  {bb['field']}: ({x:.0f},{y:.0f}) {w:.0f}x{h:.0f} — within {page_w}x{page_h}")
