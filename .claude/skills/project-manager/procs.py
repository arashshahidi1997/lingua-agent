"""Process survey for the manager's housekeeping (skill project-manager). Read-only: it never kills anything.

  python3 .claude/skills/project-manager/procs.py              # your processes older than a day, by kind
  python3 .claude/skills/project-manager/procs.py --hours 6

Groups show count, RAM, age range and orphans (parent pid 1), with up to 10 rows each. Groups matching
`procs.protect` in .projio/manager.yml are marked "protected": never propose them for a kill. Old Claude
sessions are archived from the app, never killed here.
"""

from __future__ import annotations

import collections
import getpass
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # the synced copy of this folder must stay byte-identical
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_adapter, to_root  # noqa: E402

KINDS = [
    ("screen/tmux", r"^(SCREEN|screen|tmux)"), ("dbus", r"dbus-daemon"), ("watcher", r"^(tail|grep|watch) "),
    ("site server", r"mkdocs serve|site serve|http\.server|quarto preview"), ("snakemake", r"snakemake"),
    ("marimo", r"marimo"), ("jupyter", r"jupyter|ipykernel"), ("claude", r"(^|/)(claude|ccd-cli)\b"),
    ("mcp server", r"\bmcp\b|mcp[._-]server|-m \S+\.mcp"), ("java", r"\bjava\b"),
    ("mp spawn worker", r"multiprocessing"), ("ssh", r"\bssh"), ("shell", r"^(\S*/)?-?(ba|z)?sh\b"),
    ("python", r"python"),
]


def kind(args: str) -> str:
    for k, p in KINDS:
        if re.search(p, args):
            return k
    return "other"


def main(argv: list[str]) -> int:
    to_root()
    protect = load_adapter()["procs"].get("protect") or []
    hours = float(argv[argv.index("--hours") + 1]) if "--hours" in argv else 24.0
    out = subprocess.run(["ps", "-u", getpass.getuser(), "-o", "pid=,ppid=,etimes=,rss=,args="],
                         capture_output=True, text=True).stdout
    groups = collections.defaultdict(list)
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5 or int(parts[2]) < hours * 3600:
            continue
        pid, ppid, et, rss, args = parts
        k = kind(args)
        if any(re.search(p, args) for p in protect):
            k += " (protected)"
        groups[k].append((pid, ppid, int(et) / 86400, int(rss) // 1024, args[:110]))
    print("## processes of %s older than %gh: %d" % (getpass.getuser(), hours, sum(map(len, groups.values()))))
    for k, v in sorted(groups.items(), key=lambda x: -len(x[1])):
        mb = sum(x[3] for x in v)
        orph = sum(1 for x in v if x[1] == "1")
        print("## %s: %d procs, %d MB, age %.1f-%.1f d, orphans %d" % (
            k, len(v), mb, min(x[2] for x in v), max(x[2] for x in v), orph))
        for x in v[:10]:
            print("   %s ppid %s %.1fd %dMB %s" % x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
