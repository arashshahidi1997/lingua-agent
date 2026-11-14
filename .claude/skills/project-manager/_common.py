"""Shared bits of the project-manager helpers: repo root, git, the adapter file, note frontmatter.

Stdlib only, so the helpers run from any Python 3.9+. The adapter file `.projio/manager.yml` is read with
PyYAML when it is importable; without it the defaults below are used and a warning is printed.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys

DEFAULTS: dict = {
    "prefix": "",
    "adapter_skill": "",
    "incoming": {
        "dirs": ["docs/log/issue", "docs/log/idea"],
        "title_prefix": "[from ",
        "body_markers": [],
        "open_statuses": ["open"],
        "cited_by": {"globs": [], "git_log": True},
    },
    "handoffs": {"dir": "docs/log/handoff"},
    "board": {"path": ""},  # empty: .scratch/<prefix>manager-board.md
    "units": [],
    "procs": {"protect": []},
}

# statuses that mean "closed" in the projects seen so far; anything else that is not open is flagged
CLOSED = {"done", "resolved", "answered", "consumed", "withdrawn", "cancelled", "dismissed", "hold"}


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd).stdout


def to_root() -> str:
    root = git("rev-parse", "--show-toplevel").strip() or "."
    os.chdir(root)
    return root


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load_adapter(path: str = ".projio/manager.yml") -> dict:
    if not os.path.exists(path):
        return DEFAULTS
    try:
        import yaml
    except ImportError:
        print(f"warning: PyYAML not importable, {path} ignored (run with projio's python)", file=sys.stderr)
        return DEFAULTS
    with open(path, encoding="utf-8") as fh:
        return _merge(DEFAULTS, yaml.safe_load(fh) or {})


def board_path(cfg: dict) -> str:
    """The manager board's path, relative to the repo root (`board.path`, or a bare string under `board`)."""
    b = cfg.get("board")
    path = b if isinstance(b, str) else (b or {}).get("path", "")
    return path or ".scratch/%smanager-board.md" % cfg.get("prefix", "")


def front(text: str) -> tuple[dict, str]:
    """Top-level `key: value` pairs of a frontmatter block, and the body.

    A line parser, not YAML: titles written by capture tools are often not valid YAML.
    """
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if line[:1] in (" ", "\t", "-"):
            continue
        k, _, v = line.partition(":")
        if v.strip():
            v = v.strip()
            fm[k.strip()] = v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v
    return fm, m.group(2)


def stamp(name: str) -> dt.datetime | None:
    m = re.search(r"(\d{8})-(\d{6})", name)
    try:
        return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S") if m else None
    except ValueError:
        return None


def age(ts: dt.datetime | None) -> str:
    if not ts:
        return "?"
    d = dt.datetime.now() - ts
    return f"{d.days}d" if d.days else f"{d.seconds // 3600}h"


def unit_of(path: str, units: list[dict]) -> str:
    best, best_len = "other", -1
    for u in units:
        for p in u.get("paths", []):
            p = p.rstrip("/")
            if (path == p or path.startswith(p + "/")) and len(p) > best_len:
                best, best_len = u["name"], len(p)
    return best
