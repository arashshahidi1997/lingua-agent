"""Owner and guests over Tailscale Serve: identity, per-user data, owner-only routes, caps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from lingua_agent.api.main import build_app
from lingua_agent.config import Settings
from lingua_agent.course import store

from .test_course import COURSE, _all_correct

OWNER = {"Tailscale-User-Login": "Owner@Example.com", "Tailscale-User-Name": "Arash Shahidi"}
ANYA = {"Tailscale-User-Login": "anya@example.com", "Tailscale-User-Name": "Anya"}
OTHER = {"Tailscale-User-Login": "someone@example.com"}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    pkg = tmp_path / "courses_pkg"
    pkg.mkdir()
    (pkg / "test.yaml").write_text(yaml.safe_dump(COURSE, allow_unicode=True), "utf-8")
    monkeypatch.setattr(store, "PACKAGE_DATA", pkg)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    monkeypatch.delenv("LINGUA_OWNER_LOGINS", raising=False)
    settings = Settings.load(cwd=tmp_path)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "sharing.json").write_text(json.dumps({
        "owner_logins": ["owner@example.com"], "guest_daily_model_calls": 3, "guest_storage_mb": 1,
    }), "utf-8")
    return TestClient(build_app(settings))


def _finish_first_lesson(client: TestClient, headers: dict) -> None:
    s = client.get("/api/courses/fa-en-test/lessons/u1-l1/session", headers=headers).json()
    r = client.post("/api/courses/fa-en-test/lessons/u1-l1/complete",
                    json={"results": _all_correct(s)}, headers=headers)
    assert r.status_code == 200


def test_identity(client: TestClient):
    assert client.get("/api/me").json() == {"login": "owner@example.com", "name": "you", "owner": True}
    assert client.get("/api/me", headers=OWNER).json()["owner"] is True
    assert client.get("/api/me", headers=ANYA).json() == {"login": "anya@example.com", "name": "Anya", "owner": False}


def test_guest_progress_is_separate(client: TestClient):
    _finish_first_lesson(client, ANYA)
    anya = client.get("/api/courses/fa-en-test", headers=ANYA).json()
    mine = client.get("/api/courses/fa-en-test", headers=OWNER).json()
    laptop = client.get("/api/courses/fa-en-test").json()
    assert anya["lessons_done"] == 1
    assert mine["lessons_done"] == 0 and laptop["lessons_done"] == 0
    assert len(client.get("/api/cards/due", params={"target": "fa"}, headers=ANYA).json()) == 5
    assert client.get("/api/cards/due", params={"target": "fa"}, headers=OWNER).json() == []
    assert client.get("/api/cards/due", params={"target": "fa"}, headers=OTHER).json() == []


def test_guest_recordings_are_separate(client: TestClient, tmp_path: Path):
    r = client.post("/api/recordings", data={"ref": "salam", "language": "fa"},
                    files={"file": ("r.webm", b"x" * 100, "audio/webm")}, headers=ANYA)
    assert r.status_code == 201
    assert len(client.get("/api/recordings", headers=ANYA).json()) == 1
    assert client.get("/api/recordings", headers=OWNER).json() == []
    assert client.get(r.json()["url"], headers=OWNER).status_code == 404
    assert (tmp_path / "data" / "guests" / "anya_example.com" / "recordings").is_dir()


def test_owner_only_routes(client: TestClient):
    for method, path, body in [
        ("get", "/api/materials/sources", None),
        ("post", "/api/materials/sources", {"name": "x", "provider": "local_dir", "root": "/"}),
        ("get", "/api/materials/list?source=x", None),
        ("post", "/api/audio/from-materials", {"source": "x", "path": "a.mp3", "language": "fa"}),
    ]:
        kw = {"json": body} if body else {}
        assert getattr(client, method)(path, headers=ANYA, **kw).status_code == 403, path
    assert client.get("/api/materials/sources", headers=OWNER).status_code == 200


def test_guest_model_calls_are_capped(client: TestClient):
    sess = client.post("/api/talk/sessions", json={"target": "fa", "scenario_id": "t1"}, headers=ANYA).json()
    for _ in range(3):
        assert client.post(f"/api/talk/sessions/{sess['id']}/messages", json={"content": "salam"},
                           headers=ANYA).status_code == 200
    assert client.post(f"/api/talk/sessions/{sess['id']}/messages", json={"content": "salam"},
                       headers=ANYA).status_code == 429
    # The owner has no cap, and another guest has their own.
    own = client.post("/api/talk/sessions", json={"target": "fa", "scenario_id": "t1"}, headers=OWNER).json()
    for _ in range(5):
        assert client.post(f"/api/talk/sessions/{own['id']}/messages", json={"content": "x"},
                           headers=OWNER).status_code == 200
    other = client.post("/api/talk/sessions", json={"target": "fa"}, headers=OTHER).json()
    assert client.post(f"/api/talk/sessions/{other['id']}/messages", json={"content": "x"},
                       headers=OTHER).status_code == 200
    # Another guest can't see Anya's session.
    assert client.get(f"/api/talk/sessions/{sess['id']}", headers=OTHER).status_code == 404


def test_guest_storage_cap(client: TestClient):
    big = b"x" * (1024 * 1024 + 10)
    r = client.post("/api/audio", data={"language": "fa"}, files={"file": ("a.mp3", big, "audio/mpeg")}, headers=ANYA)
    assert r.status_code == 413
    assert client.post("/api/audio", data={"language": "fa"}, files={"file": ("a.mp3", big, "audio/mpeg")},
                       headers=OWNER).status_code == 201


def test_guests_share_voices_and_courses(client: TestClient, tmp_path: Path):
    voice = tmp_path / "data" / "voices" / "fa"
    voice.mkdir(parents=True)
    (voice / "fa_IR-test.onnx").write_bytes(b"x")
    (voice / "fa_IR-test.onnx.json").write_text("{}")
    from lingua_agent.voice import piper
    if piper._piper_backend() is not None:
        assert client.get("/api/speech", headers=ANYA).json()["server_tts"]["fa"] is True
    extra = tmp_path / "data" / "courses"
    extra.mkdir()
    (extra / "extra.yaml").write_text(yaml.safe_dump({**COURSE, "id": "fa-en-extra"}, allow_unicode=True), "utf-8")
    ids = {c["id"] for c in client.get("/api/courses", headers=ANYA).json()}
    assert ids == {"fa-en-test", "fa-en-extra"}


def test_broken_sharing_file_keeps_laptop_as_owner(client: TestClient, tmp_path: Path):
    (tmp_path / "data" / "sharing.json").write_text("{not json")
    assert client.get("/api/me").json()["owner"] is True
    assert client.get("/api/me", headers=OWNER).json()["owner"] is False  # unknown login: guest, safe default
    assert client.get("/api/materials/sources", headers=OWNER).status_code == 403


def test_guest_cannot_transcribe(client: TestClient):
    track = client.post("/api/audio", data={"language": "fa"}, files={"file": ("a.mp3", b"x", "audio/mpeg")},
                        headers=ANYA).json()
    assert client.post(f"/api/audio/{track['id']}/transcribe", headers=ANYA).status_code == 403
    assert "owner" in client.get("/api/materials/sources", headers=ANYA).json()["detail"]
