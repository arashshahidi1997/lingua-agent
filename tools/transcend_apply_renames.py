"""Execute the rename plan from transcend_rename_plan.tsv against the SSD.

Strategy: depth-first ordering by source path (deepest first). This means
all files inside a folder move out before the folder itself is touched —
so by the time we reach a folder-rename row, the source folder is empty
and we can simply rmdir it.

Per row:
- File source → mkdir parents, os.rename(src, dst). os.rename refuses to
  overwrite an existing target on Linux, which we want.
- Directory source → if empty, rmdir; if not empty, log error and skip
  (don't risk losing untracked content).
- CONTAINER row → rmdir if empty, otherwise log error.
- Special-case MERGE for non-empty target dirs: walk children of src into
  the existing target, then rmdir src.

Idempotent: if src missing and dst exists, the row is treated as already
done. Re-running picks up where it left off.

Outputs:
- rename_log.tsv      — one row per processed entry, with timestamp + status
- rename_errors.tsv   — failures (continue, don't unwind)
- rename_undo.sh      — bash inverse, append-only; run with `bash` in
                        REVERSE order to undo (use `tac rename_undo.sh | bash`)

Usage:
    python tools/transcend_apply_renames.py --dry-run            # simulate, no fs changes
    python tools/transcend_apply_renames.py --limit 50           # do first 50 only
    python tools/transcend_apply_renames.py                      # apply everything
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).parent
PLAN = TOOLS / "transcend_rename_plan.tsv"
LOG = TOOLS / "rename_log.tsv"
ERRORS = TOOLS / "rename_errors.tsv"
UNDO = TOOLS / "rename_undo.sh"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without touching the filesystem.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only the first N actionable rows (0 = all).")
    parser.add_argument("--plan", type=Path, default=PLAN, help="Path to plan TSV.")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-row progress.")
    args = parser.parse_args()

    if not args.plan.exists():
        print(f"Plan not found: {args.plan}", file=sys.stderr)
        return 2

    rows = _load_plan(args.plan)
    rows = _sort_depth_first(rows)

    counters: Counter[str] = Counter()

    log_existed = LOG.exists()
    err_existed = ERRORS.exists()
    log_f = LOG.open("a", encoding="utf-8", newline="")
    err_f = ERRORS.open("a", encoding="utf-8", newline="")
    undo_f = UNDO.open("a", encoding="utf-8")
    log_w = csv.writer(log_f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    err_w = csv.writer(err_f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

    if not log_existed:
        log_w.writerow(["timestamp", "action", "src", "dst", "status"])
    if not err_existed:
        err_w.writerow(["timestamp", "action", "src", "dst", "error"])

    if undo_f.tell() == 0:
        undo_f.write(
            "#!/usr/bin/env bash\n"
            "# Auto-generated undo log. Run in REVERSE order to roll back:\n"
            "#   tac tools/rename_undo.sh | bash -e\n"
            "set -e\n"
        )

    actionable = 0
    try:
        for row in rows:
            action = row["action"]
            if action in {"KEEP", "FLAG"}:
                counters[action] += 1
                continue

            actionable += 1
            if args.limit and actionable > args.limit:
                counters["limit_reached"] += 1
                continue

            status = _apply(row, dry_run=args.dry_run, undo_f=undo_f)
            counters[status] += 1
            log_w.writerow([now(), action, row["src"], row["dst"], status])

            if not args.quiet and actionable % 500 == 0:
                print(f"  ... {actionable} rows processed", file=sys.stderr)

            if status.startswith("error"):
                err_w.writerow([now(), action, row["src"], row["dst"], status])
    finally:
        log_f.close()
        err_f.close()
        undo_f.close()

    print()
    print("Apply summary:")
    for k, v in sorted(counters.items()):
        print(f"  {k:<20}: {v}")
    print()
    print(f"Log:    {LOG}")
    print(f"Undo:   {UNDO}  (run `tac {UNDO} | bash -e` to roll back)")
    print(f"Errors: {ERRORS}")
    return 0 if counters.get("error", 0) == 0 else 1


# ---------------------------------------------------------------------------

def _load_plan(plan_path: Path) -> list[dict]:
    out = []
    with plan_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            out.append({"action": r["action"], "src": r["current_path"],
                        "dst": r["proposed_path"], "note": r["note"]})
    return out


def _sort_depth_first(rows: list[dict]) -> list[dict]:
    """Sort by source-path depth descending (files inside a folder come
    before the folder itself). For ties, preserve insertion order."""
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (-len(Path(pair[1]["src"]).parts), pair[0]))
    return [r for _, r in indexed]


def _apply(row: dict, *, dry_run: bool, undo_f) -> str:
    action = row["action"]
    src = Path(row["src"])
    dst = Path(row["dst"]) if row["dst"] else None

    src_exists = src.exists() or src.is_symlink()
    dst_exists = dst.exists() if dst is not None else False

    # Idempotency: already done
    if not src_exists and dst_exists:
        return "already_done"
    if not src_exists and not dst_exists and action == "CONTAINER":
        return "already_done"
    if not src_exists:
        return "error_src_missing"

    if action == "CONTAINER":
        return _rmdir_if_empty(src, dry_run=dry_run, undo_f=undo_f)

    assert dst is not None

    # Files
    if src.is_file() or src.is_symlink():
        if dst_exists:
            return "error_dst_exists"
        if dry_run:
            return "dry_run_file"
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(str(src), str(dst))
            undo_f.write(f"mv {shell_quote(str(dst))} {shell_quote(str(src))}\n")
            return "ok_file"
        except OSError as exc:
            return f"error_rename: {exc}"

    # Directories
    if src.is_dir():
        # All children should have been processed already (depth-first sort).
        # If src is now empty, rmdir; if it has unexpected content, error.
        children = list(src.iterdir())
        if children:
            return f"error_dir_not_empty ({len(children)} children left)"

        if action == "MERGE":
            # Source is now empty; the merge already happened via children moves.
            if dry_run:
                return "dry_run_merge_rmdir"
            try:
                src.rmdir()
                undo_f.write(f"mkdir -p {shell_quote(str(src))}\n")
                return "ok_merge_rmdir"
            except OSError as exc:
                return f"error_rmdir: {exc}"

        # RENAME / QUARANTINE on a directory: just rmdir source. The
        # destination dir was already created by the file moves below it.
        if dst_exists and not any(dst.iterdir() if dst.is_dir() else []):
            # Nothing to do — children already populated dst, src is empty.
            pass
        if dry_run:
            return "dry_run_dir_rmdir"
        try:
            src.rmdir()
            undo_f.write(f"mkdir -p {shell_quote(str(src))}\n")
            return "ok_dir_rmdir"
        except OSError as exc:
            return f"error_rmdir: {exc}"

    return "error_unknown_src_type"


def _rmdir_if_empty(src: Path, *, dry_run: bool, undo_f) -> str:
    if not src.is_dir():
        return "error_not_dir"
    children = list(src.iterdir())
    if children:
        return f"error_container_not_empty ({len(children)} children left)"
    if dry_run:
        return "dry_run_container_rmdir"
    try:
        src.rmdir()
        undo_f.write(f"mkdir -p {shell_quote(str(src))}\n")
        return "ok_container_rmdir"
    except OSError as exc:
        return f"error_rmdir: {exc}"


if __name__ == "__main__":
    sys.exit(main())
