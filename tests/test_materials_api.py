"""HTTP API tests for the materials adapter endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lingua_agent.api.main import build_app
from lingua_agent.config import Settings


@pytest.fixture
def fake_ssd(tmp_path: Path) -> Path:
    """A small SSD-shaped tree the LocalDirProvider can read."""
    root = tmp_path / "fake_ssd"
    (root / "de" / "pimsleur").mkdir(parents=True)
    (root / "de" / "pimsleur" / "lesson1.txt").write_text(
        "Ich möchte einen Kaffee bitte.", encoding="utf-8"
    )
    (root / "en" / "notes").mkdir(parents=True)
    (root / "en" / "notes" / "vocab.txt").write_text(
        "coffee, water, train station", encoding="utf-8"
    )
    return root


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    settings = Settings.load(cwd=tmp_path)
    app = build_app(settings)
    return TestClient(app)


# ---- sources CRUD ---------------------------------------------------------

def test_sources_empty_by_default(client: TestClient):
    r = client.get("/api/materials/sources")
    assert r.status_code == 200
    assert r.json() == []


def test_add_source(client: TestClient, fake_ssd: Path):
    r = client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "ssd"
    assert body["available"] is True

    r = client.get("/api/materials/sources")
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert "ssd" in names


def test_add_source_rejects_duplicate(client: TestClient, fake_ssd: Path):
    payload = {"name": "ssd", "provider": "local_dir", "root": str(fake_ssd)}
    assert client.post("/api/materials/sources", json=payload).status_code == 201
    r = client.post("/api/materials/sources", json=payload)
    assert r.status_code == 409


def test_add_source_validates_provider(client: TestClient, fake_ssd: Path):
    r = client.post("/api/materials/sources", json={
        "name": "x", "provider": "garbage", "root": str(fake_ssd),
    })
    assert r.status_code == 422  # pydantic regex validation


def test_remove_source(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.delete("/api/materials/sources/ssd")
    assert r.status_code == 204
    assert client.get("/api/materials/sources").json() == []


def test_remove_unknown_source_404(client: TestClient):
    r = client.delete("/api/materials/sources/nope")
    assert r.status_code == 404


# ---- list -----------------------------------------------------------------

def test_list_root(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.get("/api/materials/list", params={"source": "ssd"})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    names = sorted(e["name"] for e in body["entries"])
    assert names == ["de", "en"]


def test_list_subfolder(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.get("/api/materials/list", params={"source": "ssd", "folder": "de/pimsleur"})
    body = r.json()
    assert [e["name"] for e in body["entries"]] == ["lesson1.txt"]


def test_list_unavailable_source(client: TestClient, tmp_path: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(tmp_path / "missing"),
    })
    r = client.get("/api/materials/list", params={"source": "ssd"})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert "not available" in body["error"]


def test_list_unknown_source_404(client: TestClient):
    r = client.get("/api/materials/list", params={"source": "nope"})
    assert r.status_code == 404


# ---- ingest ---------------------------------------------------------------

def test_ingest_text_file_through_materials(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.post("/api/materials/ingest", json={
        "source": "ssd",
        "path": "de/pimsleur/lesson1.txt",
        "target_language": "en",
        # source_language omitted -> should derive 'de' from path's first segment
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_language"] == "de"
    assert body["target_language"] == "en"
    assert body["title"] == "lesson1"  # derived from filename
    assert body["flashcard_count"] > 0


def test_ingest_explicit_overrides(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.post("/api/materials/ingest", json={
        "source": "ssd",
        "path": "en/notes/vocab.txt",
        "target_language": "it",
        "source_language": "en",
        "title": "Coffee shop vocab",
        "cefr_level": "A1",
    })
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Coffee shop vocab"


def test_ingest_directory_rejected(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.post("/api/materials/ingest", json={
        "source": "ssd", "path": "de/pimsleur", "target_language": "en",
    })
    assert r.status_code == 400
    assert "directory" in r.json()["detail"]


def test_ingest_too_large_rejected(client: TestClient, fake_ssd: Path):
    big = fake_ssd / "de" / "big.txt"
    big.write_text("x" * 10_000, encoding="utf-8")
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.post("/api/materials/ingest", json={
        "source": "ssd", "path": "de/big.txt", "target_language": "en",
        "max_bytes": 1000,
    })
    assert r.status_code == 413


def test_ingest_missing_path_404(client: TestClient, fake_ssd: Path):
    client.post("/api/materials/sources", json={
        "name": "ssd", "provider": "local_dir", "root": str(fake_ssd),
    })
    r = client.post("/api/materials/ingest", json={
        "source": "ssd", "path": "de/nope.txt", "target_language": "en",
    })
    assert r.status_code == 404
