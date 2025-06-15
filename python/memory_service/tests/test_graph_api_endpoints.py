from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import pytest


@dataclass
class SimpleMemory:
    id: UUID
    content: str
    metadata: dict
    importance_score: float


class DummyGraphProvider:
    def __init__(self):
        self.enabled = True

    async def fetch_memory(self, memory_id: UUID) -> SimpleMemory | None:
        return SimpleMemory(id=memory_id, content="dummy", metadata={}, importance_score=0.5)

    async def sync_existing_memory(self, memory: SimpleMemory):
        return 1, 0

    async def find_path(self, from_entity: str, to_entity: str, max_depth: int = 3):
        return [from_entity, to_entity]

    async def memory_insights(self, memory_id: str):
        return {"memory_id": memory_id, "entities": [], "relationships": []}

    async def bulk_sync(self, memory_ids: list[UUID]):
        return len(memory_ids)


class DummyStore:
    def __init__(self):
        self.providers = {"graph": DummyGraphProvider()}


def create_app():
    store = DummyStore()

    app = FastAPI()

    def get_store():
        return store

    @app.post("/graph/sync/{memory_id}")
    async def sync_memory(memory_id: str, s: DummyStore = Depends(get_store)):
        gp = s.providers["graph"]
        mem = await gp.fetch_memory(UUID(memory_id))
        entities, rels = await gp.sync_existing_memory(mem)
        return {"memory_id": memory_id, "entities_added": entities, "relationships_added": rels}

    @app.get("/graph/path/{from_entity}/{to_entity}")
    async def path(from_entity: str, to_entity: str, s: DummyStore = Depends(get_store)):
        gp = s.providers["graph"]
        p = await gp.find_path(from_entity, to_entity)
        return {"from": from_entity, "to": to_entity, "path": p, "path_found": bool(p)}

    @app.get("/graph/insights/{memory_id}")
    async def insights(memory_id: str, s: DummyStore = Depends(get_store)):
        gp = s.providers["graph"]
        return await gp.memory_insights(memory_id)

    @app.post("/graph/bulk-sync")
    async def bulk(ids: list[str], s: DummyStore = Depends(get_store)):
        gp = s.providers["graph"]
        count = await gp.bulk_sync([UUID(i) for i in ids])
        return {"status": "success", "memories_processed": count}

    return app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_sync_memory(client: TestClient):
    mid = str(uuid4())
    r = client.post(f"/graph/sync/{mid}")
    assert r.status_code == 200
    assert r.json()["entities_added"] == 1


def test_find_path(client: TestClient):
    r = client.get("/graph/path/A/B")
    assert r.status_code == 200
    assert r.json()["path"] == ["A", "B"]


def test_insights(client: TestClient):
    mid = str(uuid4())
    r = client.get(f"/graph/insights/{mid}")
    assert r.status_code == 200
    assert r.json()["memory_id"] == mid


def test_bulk_sync(client: TestClient):
    ids = [str(uuid4()), str(uuid4())]
    r = client.post("/graph/bulk-sync", json=ids)
    assert r.status_code == 200
    assert r.json()["memories_processed"] == 2
