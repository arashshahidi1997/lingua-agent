"""Shared bits of the project-manager helpers: repo root, git, the manager config, note frontmatter.

Stdlib only, so the helpers run from any Python 3.9+ and the skill folder can be copied into any project.

The manager config is the first that exists of:

1. `$MANAGER_CONFIG` (a path, absolute or relative to the repo root);
2. `.projio/manager.yml` (a projio project);
3. `.claude/manager.yml` (any other project).

It is read with PyYAML when that is importable, else with the small YAML reader below (block mappings and
lists, flow `[...]` and `{...}`, quoted strings, comments: enough for the config). A `.json` config is read as
JSON. Every key has a default. Without `.projio/` the defaults are generic: no incoming note folders, handoffs
in `docs/handoffs`, units by top-level folder. A folder the config names that does not exist is skipped.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys

CONFIG_PATHS = (".projio/manager.yml", ".claude/manager.yml")

# a projio project: notio note folders under docs/log
PROJIO_DEFAULTS: dict = {
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

# any other project: git and a handoff folder are enough
GENERIC_DEFAULTS: dict = {
    **PROJIO_DEFAULTS,
    "incoming": {**PROJIO_DEFAULTS["incoming"], "dirs": []},
    "handoffs": {"dir": "docs/handoffs"},
}
DEFAULTS = PROJIO_DEFAULTS  # kept for callers of the old name

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


def config_path() -> str:
    """The manager config in use (relative to the repo root unless given absolute), or "" when there is none."""
    env = os.environ.get("MANAGER_CONFIG", "").strip()
    if env:
        if not os.path.exists(env):
            print("warning: MANAGER_CONFIG=%s does not exist" % env, file=sys.stderr)
        return env
    return next((p for p in CONFIG_PATHS if os.path.exists(p)), "")


def layout() -> str:
    """"projio" when the repo has a `.projio/` folder, else "generic"."""
    return "projio" if os.path.isdir(".projio") else "generic"


def load_adapter(path: str | None = None) -> dict:
    """The manager config merged over the layout's defaults; `_config` and `_layout` say what was used."""
    path = config_path() if path is None else path
    defaults = PROJIO_DEFAULTS if layout() == "projio" else GENERIC_DEFAULTS
    data: dict = {}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if path.endswith(".json"):
            data = json.loads(text or "{}")
        else:
            try:
                import yaml
                data = yaml.safe_load(text)
            except ImportError:
                data = read_yaml(text)
    cfg = _merge(defaults, data or {})
    cfg["_config"], cfg["_layout"] = (path if path and os.path.exists(path) else ""), layout()
    return cfg


def existing(paths: list[str]) -> list[str]:
    return [p for p in paths or [] if os.path.isdir(p)]


# ---- a small YAML reader for the config, used when PyYAML is not importable ----

def _uncomment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if q:
            q = None if ch == q else q
        elif ch in "\"'" and (i == 0 or line[i - 1] in " \t:[{,-"):
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _scalar(s: str):
    s = s.strip()
    if len(s) > 1 and s[0] == s[-1] and s[0] in "\"'":
        inner = s[1:-1]
        return inner.replace("''", "'") if s[0] == "'" else inner.replace('\\"', '"').replace("\\\\", "\\")
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    for kind in (int, float):
        try:
            return kind(s)
        except ValueError:
            pass
    return s


def _flow(s: str, i: int, stop: str):
    """One flow value at s[i:]; a plain scalar ends at any character in `stop`."""
    while i < len(s) and s[i] == " ":
        i += 1
    if i < len(s) and s[i] in "[{":
        close, is_map = ("]", False) if s[i] == "[" else ("}", True)
        out: list | dict = {} if is_map else []
        i += 1
        while True:
            while i < len(s) and s[i] in " ,":
                i += 1
            if i >= len(s) or s[i] == close:
                return out, i + 1
            if is_map:
                key, i = _flow(s, i, ":,}")
                i += 1 if i < len(s) and s[i] == ":" else 0
                val, i = _flow(s, i, ",}")
                out[key] = val
            else:
                val, i = _flow(s, i, ",]")
                out.append(val)
    if i < len(s) and s[i] in "\"'":
        j = s.index(s[i], i + 1)
        return _scalar(s[i:j + 1]), j + 1
    j = i
    while j < len(s) and s[j] not in stop:
        j += 1
    return _scalar(s[i:j]), j


def _value(s: str):
    return _flow(s, 0, "")[0] if s[:1] in "[{" else _scalar(s)


def _split_key(text: str):
    """("key", "rest") when the line is `key: rest` or `key:`, else None."""
    m = re.match(r"""^("[^"]*"|'[^']*'|[^\s"'\[{#][^:]*?)\s*:(?:\s+(.*))?$""", text)
    return (_scalar(m.group(1)), (m.group(2) or "").strip()) if m else None


def _block(lines: list, i: int, ind: int):
    if lines[i][1] == "-" or lines[i][1].startswith("- "):
        out = []
        while i < len(lines) and lines[i][0] == ind and (lines[i][1] == "-" or lines[i][1].startswith("- ")):
            rest = lines[i][1][1:].strip()
            if not rest:
                i += 1
                val, i = _block(lines, i, lines[i][0]) if i < len(lines) and lines[i][0] > ind else (None, i)
            elif rest[0] not in "[{\"'" and _split_key(rest):
                lines[i] = (ind + 2, rest)
                val, i = _block(lines, i, ind + 2)
            else:
                val, i = _value(rest), i + 1
            out.append(val)
        return out, i
    out = {}
    while i < len(lines) and lines[i][0] == ind and not lines[i][1].startswith("- "):
        kv = _split_key(lines[i][1])
        if kv is None:
            raise ValueError("cannot read config line: %r" % lines[i][1])
        key, rest = kv
        i += 1
        if rest:
            out[key] = _value(rest)
        elif i < len(lines) and (lines[i][0] > ind or (lines[i][0] == ind and lines[i][1].startswith("- "))):
            out[key], i = _block(lines, i, lines[i][0])
        else:
            out[key] = None
    return out, i


def read_yaml(text: str):
    """The subset of YAML a manager config uses (no anchors, no multi-line scalars)."""
    lines = []
    for raw in text.splitlines():
        line = _uncomment(raw.replace("\t", "  "))
        if line.strip() and line.strip() != "---":
            lines.append((len(line) - len(line.lstrip()), line.strip()))
    return _block(lines, 0, lines[0][0])[0] if lines else {}


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
    """The unit with the longest matching path; with no units configured, the top-level folder."""
    if not units:
        return path.split("/", 1)[0] if "/" in path.rstrip("/") else "(top)"
    best, best_len = "other", -1
    for u in units:
        for p in u.get("paths", []):
            p = p.rstrip("/")
            if (path == p or path.startswith(p + "/")) and len(p) > best_len:
                best, best_len = u["name"], len(p)
    return best
