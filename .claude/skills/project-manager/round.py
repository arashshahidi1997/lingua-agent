"""What changed since the last manager round (skill project-manager). Run from anywhere in the repo:

  python3 .claude/skills/project-manager/round.py                     # handoffs, since, dirty
  python3 .claude/skills/project-manager/round.py handoffs since      # chosen sections
  python3 .claude/skills/project-manager/round.py since --since <sha>
  python3 .claude/skills/project-manager/round.py board               # rewrite the manager board

All sections but `board` are read-only.

Sections:
  handoffs  newest open handoff per series in `handoffs.dir`; a series with more than one open handoff is flagged
  since     commits since the watermark, with the units each touched. The watermark is `git_commit` of the
            newest `series: manager` handoff, or two days when there is none. Sessions often wrap without
            reporting, so this is how the manager sees what finished.
  dirty     uncommitted paths grouped by unit (`units` in .projio/manager.yml): two live sessions in one unit
            is a collision; subdatasets with their own uncommitted changes or a moved pointer
  board     rewrites the board (`board.path`, default .scratch/<prefix>manager-board.md) and prints its path.
            The hand-written text of every section is kept; the blocks between `<!-- auto:… -->` markers
            (newest handoffs and dirty units under Sessions, unpushed commits under Sync) are regenerated.
            The "As of" line of What's up and the "Updated" line get the same stamp, the time of the rewrite.
            Warns when the board is not gitignored.
"""

from __future__ import annotations

import collections
import glob
import datetime as dt
import os
import re
import socket
import subprocess
import sys

sys.dont_write_bytecode = True  # the synced copy of this folder must stay byte-identical
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import age, board_path, front, git, load_adapter, stamp, to_root, unit_of  # noqa: E402


def handoff_rows(cfg: dict) -> list[dict]:
    rows = []
    for f in glob.glob(os.path.join(cfg["handoffs"]["dir"], "*.md")):
        if os.path.basename(f) == "index.md":
            continue
        with open(f, encoding="utf-8", errors="replace") as fh:
            fm, _ = front(fh.read())
        nid = os.path.basename(f)[:-3]
        ts = stamp(fm.get("timestamp", "") or nid)
        rows.append({"path": f, "id": ts.strftime("%Y%m%d-%H%M%S") if ts else nid, "ts": ts,
                     "series": fm.get("series", "") or "-", "status": fm.get("status", ""),
                     "title": fm.get("title", ""), "git_commit": fm.get("git_commit", "")})
    rows.sort(key=lambda r: r["id"], reverse=True)
    return rows


def show_handoffs(rows: list[dict]) -> None:
    open_by = collections.defaultdict(list)
    for r in rows:
        if r["status"] == "open":
            open_by[r["series"]].append(r)
    print("## handoffs: newest open per series (%d series)" % len(open_by))
    for series, rs in sorted(open_by.items(), key=lambda x: x[1][0]["id"], reverse=True):
        r = rs[0]
        more = "  (+%d older open: consume?)" % (len(rs) - 1) if len(rs) > 1 else ""
        print("  %-22s %s %4s  %s%s" % (series[:22], r["id"], age(r["ts"]), r["title"][:80], more))


def watermark(rows: list[dict], given: str) -> tuple[str, str]:
    if given:
        return given + "..HEAD", "given " + given
    for r in rows:
        sha = r["git_commit"]
        if r["series"] == "manager" and sha and git("cat-file", "-t", sha).strip() == "commit":
            return sha + "..HEAD", "manager handoff %s (%s)" % (r["id"], sha[:9])
    return "", "two days (no manager handoff with git_commit)"


def show_since(rows: list[dict], cfg: dict, given: str) -> None:
    rng, why = watermark(rows, given)
    args = ["log", "--format=\x1e%h %ad %s", "--date=short", "--name-only"]
    args += [rng] if rng else ["--since=2.days"]
    out = git(*args)
    commits = [c.strip().splitlines() for c in out.split("\x1e") if c.strip()]
    print("## since %s: %d commits" % (why, len(commits)))
    for c in commits:
        units = sorted({unit_of(p, cfg["units"]) for p in c[1:] if p.strip()})
        print("  %s  [%s]" % (c[0][:110], ",".join(units) or "-"))


def dirty_lines(cfg: dict) -> list[str]:
    by_unit = collections.defaultdict(list)
    for line in git("status", "--porcelain", "--untracked-files=all").splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        by_unit[unit_of(path, cfg["units"])].append(line[:2] + " " + path)
    out = ["dirty: %d paths in %d units" % (sum(map(len, by_unit.values())), len(by_unit))]
    for u, ps in sorted(by_unit.items(), key=lambda x: -len(x[1])):
        out.append("%-14s %3d  %s%s" % (u, len(ps), "; ".join(ps[:4]), " …" if len(ps) > 4 else ""))
    subs = [line.split() for line in git("submodule", "status").splitlines() if line.strip()]
    for s in subs:
        mark, path = s[0][0], s[1]
        own = len(git("status", "--porcelain", cwd=path).splitlines()) if os.path.isdir(path) else 0
        if mark == "+" or own:
            out.append("subdataset %-20s %s%s" % (path, "pointer moved; " if mark == "+" else "",
                                                  "%d uncommitted inside" % own if own else ""))
    return out


def show_dirty(cfg: dict) -> None:
    lines = dirty_lines(cfg)
    print("## " + lines[0])
    for line in lines[1:]:
        print("  " + line)


# The board: sections in order, with the heading and text a new board starts from. An existing section is matched
# by the start of its heading (any of BOARD_ALIASES) and keeps its heading, so a manager may rename one.
BOARD_ALIASES = {"whatsup": ("what",), "copy": ("copy", "delegate", "kickoff"), "decisions": ("decision",), "sessions": ("session",),
                 "waiting": ("waiting",), "sync": ("sync",)}
BOARD_SECTIONS = [
    ("whatsup", "What's up",
     "As of {stamp}.\n\n- Running now: nothing yet.\n- Latest: nothing yet.\n- Waiting on you: nothing yet.\n"
     "- Next to start: nothing yet."),
    ("copy", "Delegate",
     "Nothing to delegate. Kickoffs go here numbered, each with a tag line (**independent** or **depends on "
     "<what>**) and a ```text block; say \"delegated <n>\" or \"delegated all\" once one is started."),
    ("decisions", "Decisions waiting for you", "_None._"),
    ("sessions", "Sessions, by state", "| Session | State | Notes |\n|---|---|---|"),
    ("waiting", "Waiting on others", "_None._"),
    ("sync", "Sync", "This manager: {manager} · {host} · `?` (session id)\n\n"
                     "Other managers (`name · machine · session id · last contact`):\n\n- none yet"),
]
STRUCTURE = re.compile(r"^(\s*[-*|]|\s*\d+\.|```|###)", re.M)  # content beyond a placeholder sentence
# The stamp line of What's up: "As of <date time>" or a stale "As of this afternoon", optionally in *…* or _…_.
AS_OF = re.compile(r"^([*_]*\s*)As of (?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?|[^.(*_\n]*[^.(*_\n\s])", re.M)
AUTO = re.compile(r"\n*<!-- auto:(\w+) -->.*?<!-- /auto:\1 -->\n*", re.S)


def _auto(name: str, title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "(none)"
    return "<!-- auto:%s -->\n%s (from the files, rewritten by round.py board):\n\n```text\n%s\n```\n<!-- /auto:%s -->" % (
        name, title, body, name)


def unpushed_lines() -> list[str]:
    up = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").strip()
    if not up:
        return ["no upstream for %s" % (git("branch", "--show-current").strip() or "HEAD")]
    log = git("log", "--format=%h %ad %s", "--date=short", "@{u}..").splitlines()
    return ["%d commits ahead of %s" % (len(log), up)] + log[:20] + (["…"] if len(log) > 20 else [])


def handoff_lines(rows: list[dict]) -> list[str]:
    seen, out = set(), []
    for r in rows:
        if r["status"] == "open" and r["series"] not in seen:
            seen.add(r["series"])
            out.append("%-18s %s %4s  %s" % (r["series"][:18], r["id"], age(r["ts"]), r["title"][:70]))
    return out


def parse_board(text: str) -> tuple[list[str], list[tuple[str | None, str, str]]]:
    """Preamble lines, and the sections in file order as (key or None, heading, hand-written text).

    A `## ` line inside a code fence (a kickoff) is text, not a heading.
    """
    preamble, sections, fence = [], [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        elif line.strip() and not line.startswith("# ") and not line.startswith("Updated "):
            preamble.append(line)
    out = []
    for heading, lines in sections:
        key = next((k for k, al in BOARD_ALIASES.items() if heading.lower().startswith(al)), None)
        out.append((key, heading, AUTO.sub("\n\n", "\n".join(lines)).strip("\n")))
    return preamble, out


def stamp_whatsup(text: str, now: str) -> str:
    """Set the first "As of …" stamp to `now`, or put one on top; every other line stays as written."""
    if AS_OF.search(text):
        return AS_OF.sub(lambda m: m.group(1) + "As of " + now, text, count=1)
    return "As of %s.\n\n%s" % (now, text) if text.strip() else "As of %s." % now


def write_board(cfg: dict, rows: list[dict]) -> str:
    """Rewrite the board. Known sections come in BOARD_SECTIONS order, each followed by its auto blocks; a section
    the board has twice is kept once when the copies match, and copies that are only a placeholder sentence yield
    to one with content (a list, table, code block or subheading).
    Unknown sections stay after the section they followed. Hand-written text is never dropped."""
    path = board_path(cfg)
    manager = (cfg.get("prefix") or "") + "manager"
    host = socket.gethostname().split(".")[0]
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
    preamble, sections = parse_board(old)
    defaults = {k: (h, d.format(manager=manager, host=host, stamp=now)) for k, h, d in BOARD_SECTIONS}
    known: dict = {k: [] for k in defaults}
    after: dict = {None: []}  # unknown sections, by the known key they followed
    last = None
    for key, heading, text in sections:
        if key is None:
            after.setdefault(last, []).append((heading, text))
            continue
        last = key
        if all(text.strip() != t.strip() for _, t in known[key]):
            known[key].append((heading, text))
    for key, entries in known.items():
        real = [e for e in entries if STRUCTURE.search(e[1])]
        known[key] = real or entries[:1] or [defaults[key]]
    known["whatsup"] = [(h, stamp_whatsup(t, now)) for h, t in known["whatsup"]]
    auto = {
        "sessions": [_auto("handoffs", "Newest open handoff per series", handoff_lines(rows)),
                     _auto("dirty", "Uncommitted, by unit", dirty_lines(cfg))],
        "sync": [_auto("unpushed", "Unpushed commits", unpushed_lines())],
    }
    out = ["# %s board" % manager, "",
           "Updated %s on %s. Rewritten every round; gitignored. Chat replies point here." % (now, host)]
    if preamble:
        out += [""] + preamble

    def emit(heading: str, blocks: list[str]) -> None:
        out.extend(["", "## " + heading])
        for block in blocks:
            if block.strip():
                out.extend(["", block])

    for heading, text in after[None]:
        emit(heading, [text])
    for key, _, _ in BOARD_SECTIONS:
        entries = known[key]
        for i, (heading, text) in enumerate(entries):
            emit(heading, [text] + (auto.get(key, []) if i == len(entries) - 1 else []))
        for heading, text in after.get(key, []):
            emit(heading, [text])
    body = "\n".join(out).rstrip() + "\n"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def show_board(cfg: dict, rows: list[dict]) -> None:
    path = write_board(cfg, rows)
    print("## board: wrote %s" % os.path.abspath(path))
    if subprocess.run(["git", "check-ignore", "-q", path]).returncode != 0:
        print("warning: %s is not gitignored; add it (or its folder) to .gitignore" % path, file=sys.stderr)
        print("  warning: not gitignored")


def main(argv: list[str]) -> int:
    to_root()
    cfg = load_adapter()
    given = ""
    if "--since" in argv:
        i = argv.index("--since")
        given = argv[i + 1] if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2:]
    sections = [a for a in argv if not a.startswith("-")] or ["handoffs", "since", "dirty"]
    rows = handoff_rows(cfg)
    for s in sections:
        if s == "handoffs":
            show_handoffs(rows)
        elif s == "since":
            show_since(rows, cfg, given)
        elif s == "dirty":
            show_dirty(cfg)
        elif s == "board":
            show_board(cfg, rows)
        else:
            print("unknown section: " + s, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
