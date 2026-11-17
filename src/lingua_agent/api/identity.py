"""Who is calling: the owner or a guest, from the header Tailscale Serve adds.

`tailscale serve` publishes the app (bound to 127.0.0.1) on the tailnet and adds
`Tailscale-User-Login` / `Tailscale-User-Name` to every proxied request. Logins
listed in `${data_dir}/sharing.json` (or `LINGUA_OWNER_LOGINS`, comma-separated)
are the owner; any other login is a guest. A request without the header comes
from the laptop itself and counts as the owner — safe only because the server
binds 127.0.0.1, so nothing else can reach it without going through Serve.

Guests get their own data dir (`${data_dir}/guests/<login>/`): progress, cards,
recordings, Talk sessions, uploads. Voices, the speech cache and extra courses
stay shared. Owner-only routes depend on `require_owner` (403 for guests), and
model calls go through `charge_model_call` (a daily cap per guest).

sharing.json:
    {"owner_logins": ["you@example.com"],
     "guest_ai_provider": null,          # e.g. "openai" pointing at local Ollama; null = same as the owner
     "guest_daily_model_calls": 80,
     "guest_storage_mb": 500}
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from fastapi import HTTPException, Request

from ..config import Settings

DEFAULTS = {"owner_logins": [], "guest_ai_provider": None, "guest_daily_model_calls": 80,
            "guest_storage_mb": 500}


@dataclass(frozen=True)
class Identity:
    login: str
    name: str
    owner: bool


def base_settings(request: Request) -> Settings:
    return request.app.state.settings


def sharing_config(base: Settings) -> dict:
    cfg = dict(DEFAULTS)
    path = base.data_dir / "sharing.json"
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text("utf-8")))
        except (OSError, ValueError):
            pass  # a broken file must not lock the owner out; defaults apply
    env = os.environ.get("LINGUA_OWNER_LOGINS", "")
    cfg["owner_logins"] = [x.strip().lower() for x in [*cfg["owner_logins"], *env.split(",")] if x.strip()]
    return cfg


def identify(request: Request) -> Identity:
    base = base_settings(request)
    login = (request.headers.get("Tailscale-User-Login") or "").strip().lower()
    if not login:
        host = request.client.host if request.client else ""
        if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
            # Only the laptop itself may skip Tailscale; e.g. `serve --host 0.0.0.0` on a LAN must not
            # make every neighbour the owner.
            raise HTTPException(403, "Open the app through Tailscale.")
        owners = sharing_config(base)["owner_logins"]
        return Identity(login=owners[0] if owners else "owner", name="you", owner=True)
    name = request.headers.get("Tailscale-User-Name") or login.split("@")[0]
    return Identity(login=login, name=name, owner=login in sharing_config(base)["owner_logins"])


def _slug(login: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", login.lower()).strip("._-")[:80] or "guest"


def settings_for(request: Request) -> Settings:
    base = base_settings(request)
    who = identify(request)
    if who.owner:
        return base
    guest_dir = base.data_dir / "guests" / _slug(who.login)
    provider = sharing_config(base)["guest_ai_provider"] or base.ai_provider
    s = replace(base, data_dir=guest_dir, content_dir=guest_dir / "content",
                shared_dir=base.shared_data_dir, ai_provider=provider)
    s.ensure_dirs()
    return s


def require_owner(request: Request) -> None:
    if not identify(request).owner:
        raise HTTPException(403, "Only the owner of this app can do that.")


def charge_model_call(request: Request, s: Settings, n: int = 1) -> None:
    """Count a model call for a guest; 429 once their daily cap is used up."""
    who = identify(request)
    if who.owner:
        return
    cap = int(sharing_config(base_settings(request))["guest_daily_model_calls"])
    path = s.data_dir / "model_usage.json"
    today = date.today().isoformat()
    try:
        usage = json.loads(path.read_text("utf-8")) if path.exists() else {}
    except ValueError:
        usage = {}
    used = int(usage.get(today, 0))
    if used + n > cap:
        raise HTTPException(429, "That's today's limit for AI replies. It resets tomorrow.")
    path.write_text(json.dumps({today: used + n}), encoding="utf-8")


def check_guest_storage(request: Request, s: Settings, incoming: int = 0) -> None:
    """Guests keep their uploads under a total size cap (owner: no cap)."""
    if identify(request).owner:
        return
    cap = int(sharing_config(base_settings(request))["guest_storage_mb"]) * 1024 * 1024
    used = sum(p.stat().st_size for p in Path(s.data_dir).rglob("*") if p.is_file())
    if used + incoming > cap:
        raise HTTPException(413, "Your storage space here is full. Delete some recordings or audio first.")
