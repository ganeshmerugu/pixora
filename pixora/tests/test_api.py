from __future__ import annotations
import pytest
from httpx import AsyncClient, ASGITransport
from pixora.api.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


# --- Parse ---

@pytest.mark.asyncio
async def test_parse_create_and_get(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/parse", json={"file_id": "f1", "tier": "agentic"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        job_id = data["job_id"]

        resp2 = await c.get(f"/api/v1/parse/{job_id}")
        assert resp2.status_code == 200
        assert resp2.json()["job_id"] == job_id


@pytest.mark.asyncio
async def test_parse_list(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.post("/api/v1/parse", json={"file_id": "f2"})
        resp = await c.get("/api/v1/parse")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_parse_cancel(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create = await c.post("/api/v1/parse", json={"file_id": "f3"})
        job_id = create.json()["job_id"]
        resp = await c.post(f"/api/v1/parse/{job_id}/cancel")
        assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_parse_delete(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create = await c.post("/api/v1/parse", json={"file_id": "f4"})
        job_id = create.json()["job_id"]
        resp = await c.delete(f"/api/v1/parse/{job_id}")
        assert resp.status_code == 200
        resp2 = await c.get(f"/api/v1/parse/{job_id}")
        assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_parse_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/parse/nonexistent")
        assert resp.status_code == 404


# --- Extract ---

@pytest.mark.asyncio
async def test_extract_create(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/extract", json={"file_id": "f1", "data_schema": {"fields": ["name"]}})
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_extract_list(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/extract")
        assert resp.status_code == 200


# --- Classify ---

@pytest.mark.asyncio
async def test_classify_create(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/classify", json={
            "file_id": "f1",
            "rules": [{"type": "invoice", "description": "Has totals"}],
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"


# --- Quality (Pixora exclusive) ---

@pytest.mark.asyncio
async def test_quality_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/parse/nope/quality")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_quality_store_and_retrieve(transport):
    from pixora.api.routers.quality import store_quality
    store_quality("test_job", {
        "document_id": "doc1", "overall_score": 0.87,
        "completeness": 0.9, "grounding_score": 0.85, "recommendation": "accept",
    })
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/parse/test_job/quality")
        assert resp.status_code == 200
        assert resp.json()["overall_score"] == 0.87


@pytest.mark.asyncio
async def test_grounding_store_and_retrieve(transport):
    from pixora.api.routers.quality import store_grounding
    store_grounding("test_job2", {
        "document_id": "doc1", "grounding_rate": 0.92,
        "grounded_count": 10, "ungrounded_count": 1,
        "flagged_hallucinations": ["vendor"],
    })
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/parse/test_job2/grounding")
        assert resp.status_code == 200
        assert resp.json()["grounding_rate"] == 0.92
        assert "vendor" in resp.json()["flagged_hallucinations"]


@pytest.mark.asyncio
async def test_trace_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/parse/nope/trace")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cost_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/parse/nope/cost")
        assert resp.status_code == 404
