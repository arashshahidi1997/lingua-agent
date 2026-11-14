"""Incoming notes for the manager (skill project-manager). Read-only. Run from anywhere in the repo:

  python3 .claude/skills/project-manager/incoming.py           # open notes from other projects, newest first
  python3 .claude/skills/project-manager/incoming.py --all     # also open notes with no "from" signal
  python3 .claude/skills/project-manager/incoming.py --json

A note counts as incoming when its status is open (`incoming.open_statuses`) or unknown, and its title starts
with `incoming.title_prefix` ("[from <project>] …") or its body has an `incoming.body_markers` line naming the
sender. Per note: id, commit state (UNCOMMITTED / modified / committed), age, sender, where it is cited (docs
matching `incoming.cited_by.globs`, and commit messages when `cited_by.git_log`), and flags:
  stub        no status, or a body under 200 characters (voice captures can arrive truncated)
  dup?        same sender within a day and near-identical text (captures can arrive twice)
  status?     a status outside the open and closed vocabularies
  open 7d+    still open after a week: check whether the work is done
Editor backups (*.md~) in the note folders are counted at the end.
"""

from __future__ import annotations

import difflib
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # the synced copy of this folder must stay byte-identical
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import CLOSED, age, front, git, load_adapter, stamp, to_root  # noqa: E402


def sender_of(title: str, body: str, prefix: str, markers: list[str]) -> str:
    if prefix and title.startswith(prefix):
        return re.split(r"[\],]", title[len(prefix):], maxsplit=1)[0].strip()
    for mk in markers:
        m = re.search(r"^" + re.escape(mk) + r"\s*(.+)$", body, re.M)
        if m:
            return m.group(1).strip()
    return ""


def collect(cfg: dict, show_all: bool) -> tuple[list[dict], list[str]]:
    inc = cfg["incoming"]
    dirs = inc["dirs"]
    open_st = set(inc["open_statuses"])
    untracked = set(git("ls-files", "--others", "--exclude-standard", "--", *dirs).split())
    modified = set(git("diff", "--name-only", "HEAD", "--", *dirs).split())
    cite = {}
    for g in inc["cited_by"].get("globs") or []:
        for c in sorted(glob.glob(g, recursive=True)):
            with open(c, encoding="utf-8", errors="replace") as fh:
                cite[c] = fh.read()
    log = git("log", "-n", "3000", "--format=%h %s") if inc["cited_by"].get("git_log") else ""
    rows, backups = [], []
    for d in dirs:
        backups += glob.glob(os.path.join(d, "*.md~"))
        for f in sorted(glob.glob(os.path.join(d, "*.md"))):
            if os.path.basename(f) == "index.md":
                continue
            with open(f, encoding="utf-8", errors="replace") as fh:
                fm, body = front(fh.read())
            status = fm.get("status", "")
            if status in CLOSED:
                continue
            title = fm.get("title", "").strip("\"' #")
            sender = sender_of(title, body, inc["title_prefix"], inc["body_markers"])
            if not sender and not show_all:
                continue
            nid = os.path.basename(f)[:-3]
            ts = stamp(nid)
            short = ts.strftime("%Y%m%d-%H%M%S") if ts else nid
            cited = [os.path.basename(c)[:-3] for c, t in cite.items() if short in t]
            cited += ["commit " + line.split()[0] for line in log.splitlines() if short in line]
            rows.append({
                "path": f, "id": short, "ts": ts, "title": title, "sender": sender, "status": status,
                "body": body.strip(), "open": status in open_st,
                "state": "UNCOMMITTED" if f in untracked else "modified" if f in modified else "committed",
                "cited": cited,
            })
    rows.sort(key=lambda r: r["id"], reverse=True)
    return rows, backups


def flag(rows: list[dict]) -> None:
    import datetime as dt
    now = dt.datetime.now()
    for r in rows:
        fl = []
        if not r["status"] or len(r["body"]) < 200:
            fl.append("stub")
        elif not r["open"]:
            fl.append("status?")
        if r["ts"] and r["open"] and (now - r["ts"]).days >= 7:
            fl.append("open 7d+")
        for o in rows:
            if o is r or not r["sender"] or o["sender"] != r["sender"] or not (r["ts"] and o["ts"]):
                continue
            if abs((r["ts"] - o["ts"]).total_seconds()) > 86400:
                continue
            a, b = r["title"] + " " + r["body"][:600], o["title"] + " " + o["body"][:600]
            if difflib.SequenceMatcher(None, a, b).ratio() > 0.85:
                fl.append("dup? " + o["id"])
                break
        r["flags"] = fl


def main(argv: list[str]) -> int:
    to_root()
    cfg = load_adapter()
    show_all = "--all" in argv
    rows, backups = collect(cfg, show_all)
    flag(rows)
    if "--json" in argv:
        for r in rows:
            r["ts"] = r["ts"].isoformat() if r["ts"] else None
            r.pop("body")
        print(json.dumps({"notes": rows, "backups": backups}, indent=1))
        return 0
    print("%d open %snotes, newest first" % (len(rows), "" if show_all else "incoming "))
    for r in rows:
        cited = ",".join(r["cited"][:3]) + ("…" if len(r["cited"]) > 3 else "") or "-"
        print("%s  %-11s %4s  %-12s cited:%-16s %-14s %s" % (
            r["id"], r["state"], age(r["ts"]), (r["sender"] or "-")[:12], cited, " ".join(r["flags"]),
            r["title"][:90]))
    if backups:
        print("editor backups: " + " ".join(backups))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
