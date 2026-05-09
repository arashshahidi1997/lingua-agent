"""Runtime configuration loaded from environment variables.

Kept deliberately small: the working tree owns its data dir, AI provider
selection is a single env var, and each provider reads its own keys lazily.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    content_dir: Path
    ai_provider: str
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    ollama_base_url: str

    @classmethod
    def load(cls, *, cwd: Path | None = None) -> "Settings":
        cwd = cwd or Path.cwd()
        data_dir_env = os.environ.get("LINGUA_DATA_DIR", "").strip()
        data_dir = Path(data_dir_env) if data_dir_env else cwd / ".lingua-agent"
        return cls(
            data_dir=data_dir,
            content_dir=cwd / "content",
            ai_provider=os.environ.get("LINGUA_AI_PROVIDER", "mock").strip().lower(),
            openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
            openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    def ensure_dirs(self) -> None:
        for sub in ("documents", "lessons", "flashcards", "exercises", "attempts", "reviews", "sessions"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)
        for sub in ("inbox", "units", "cards", "exports"):
            (self.content_dir / sub).mkdir(parents=True, exist_ok=True)
