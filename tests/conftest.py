from __future__ import annotations

import os
from pathlib import Path

import pytest

from lingua_agent.config import Settings


@pytest.fixture
def tmp_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    s = Settings.load(cwd=tmp_path)
    s.ensure_dirs()
    return s
