"""FastAPI app construction.

`build_app(settings)` returns a fresh app instance — useful for tests with
per-test settings overrides. The module-level `app` uses default settings
loaded from environment, suitable for `uvicorn lingua_agent.api.main:app`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import Settings
from .routes import get_settings, router


def build_app(settings: Settings | None = None, *, web_dir: Path | None = None,
              cors_origins: list[str] | None = None) -> FastAPI:
    settings = settings or Settings.load()
    settings.ensure_dirs()

    app = FastAPI(
        title="lingua-agent",
        description="Agentic AI language-learning platform — any language A → B.",
        version="0.1.0",
    )

    # CORS — wide open for dev (Vite dev server on :5173). Tighten when we
    # serve a built UI from the same FastAPI process in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Wire the settings dependency.
    app.dependency_overrides[get_settings] = lambda: settings
    app.state.settings = settings
    app.include_router(router)

    # If a built React app exists, mount it at the root. In dev the React
    # server runs separately on :5173, so this branch is skipped silently.
    web_dir = web_dir or (Path.cwd() / "web" / "dist")
    if web_dir.exists() and (web_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app


# Import-time module attribute for `uvicorn lingua_agent.api.main:app`.
app = build_app()
