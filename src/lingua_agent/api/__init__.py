"""HTTP API — FastAPI server mirroring the CLI surface.

Every CLI command is reachable as an HTTP endpoint so any client (React PWA,
desktop wrapper, mobile app) can drive the same Python core. See
docs/clients.md for the multi-platform plan.

Launch:  lingua-agent serve   (or: uvicorn lingua_agent.api.main:app)
"""

from .main import app, build_app

__all__ = ["app", "build_app"]
