from __future__ import annotations
import pytest
from httpx import AsyncClient, ASGITransport
from pixora.api.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


# --- Schemas CRUD ---

@pytest.mark.asyncio
async def test_schema_create(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/schemas", json={
            "name": "invoice_v1", "doc_type": "invoice",
            "nodes": [{"name": "total", "field_type": "NUMBER"}],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "invoice_v1"


@pytest.mark.asyncio
async def test_schema_list(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.post("/api/v1/schemas", json={"name": "test", "doc_type": "test", "nodes": []})
        resp = await c.get("/api/v1/schemas")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_schema_get_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/schemas/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_schema_delete(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create = await c.post("/api/v1/schemas", json={"name": "del", "doc_type": "t", "nodes": []})
        sid = create.json()["id"]
        resp = await c.delete(f"/api/v1/schemas/{sid}")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_schema_infer(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/schemas/infer")
        assert resp.status_code == 200
        assert resp.json()["name"] == "auto_inferred"


# --- Review Queue ---

@pytest.mark.asyncio
async def test_review_queue_empty(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/review/queue")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_review_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/review/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_review_enqueue_and_get(transport):
    from pixora.api.routers.review import enqueue_review
    rid = enqueue_review("job1", "doc1", 0.65, [{"severity": "warning", "message": "low score"}])
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get(f"/api/v1/review/{rid}")
        assert resp.status_code == 200
        assert resp.json()["quality_score"] == 0.65


@pytest.mark.asyncio
async def test_review_submit(transport):
    from pixora.api.routers.review import enqueue_review
    rid = enqueue_review("job2", "doc2", 0.5, [])
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(f"/api/v1/review/{rid}", json={"status": "approved", "reviewer": "human"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


# --- Evals ---

@pytest.mark.asyncio
async def test_evals_run(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/evals/run", json={"suite_name": "test"})
        assert resp.status_code == 200
        assert resp.json()["suite_name"] == "test"


@pytest.mark.asyncio
async def test_evals_list_reports(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/evals/reports")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_evals_drift(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/evals/drift")
        assert resp.status_code == 200


# --- Webhooks CRUD ---

@pytest.mark.asyncio
async def test_webhook_create(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/webhooks", json={"url": "https://example.com/hook", "events": ["job.completed"]})
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://example.com/hook"


@pytest.mark.asyncio
async def test_webhook_list(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/webhooks")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_delete(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create = await c.post("/api/v1/webhooks", json={"url": "https://del.com", "events": []})
        wid = create.json()["id"]
        resp = await c.delete(f"/api/v1/webhooks/{wid}")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_update(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        create = await c.post("/api/v1/webhooks", json={"url": "https://old.com", "events": ["a"]})
        wid = create.json()["id"]
        resp = await c.put(f"/api/v1/webhooks/{wid}", json={"url": "https://new.com", "events": ["b"]})
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://new.com"


@pytest.mark.asyncio
async def test_webhook_not_found(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/v1/webhooks/nope")
        assert resp.status_code == 404
