"""A page to listen to every recorded take, sheet by sheet, next to its text.

    .venv/bin/python tools/voice_review.py      # writes .lingua-agent/native_audio/review.html

One row per sheet line: number, Persian, transliteration, meaning, and a player per take (with the
recording it was cut from). Lines on the re-record list are marked; lines without a take say so. The page
sits next to the clips, so the players use relative paths: open it in a browser from that folder.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lingua_agent.config import Settings  # noqa: E402
from lingua_agent.voice.native import index_path, load_index, norm  # noqa: E402

SHEETS = ROOT / "content" / "recording" / "fa-en-a1"

CSS = """
:root{--bg:#c9ece6;--card:#fbfefd;--ink:#1c1917;--ink2:#4f5b59;--line:#b3dcd5;--acc:#0f766e;--warn:#9a3412;--warnbg:#fff1e6}
@media (prefers-color-scheme:dark){:root{--bg:#0b2b2a;--card:#103735;--ink:#f2f0ee;--ink2:#9fb6b2;--line:#1f504c;--acc:#3cc7b4;--warn:#fdba74;--warnbg:#3a2516}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{max-width:52rem;margin:0 auto;padding:24px 16px 80px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:36px 0 4px}.sub{color:var(--ink2);margin:0 0 8px}
h3{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin:20px 0 6px}
.row{display:grid;grid-template-columns:2.2rem 1fr;gap:2px 12px;background:var(--card);border:1px solid var(--line);
 border-radius:12px;padding:10px 14px;margin:6px 0}
.row.redo{border-color:var(--warn);background:var(--warnbg)}
.n{color:var(--ink2);font-variant-numeric:tabular-nums;padding-top:6px}
.fa{font-family:Vazirmatn,"Noto Naskh Arabic",sans-serif;font-size:24px;text-align:right}
.meta{color:var(--ink2);font-size:13px}.flag{color:var(--warn);font-size:13px;font-weight:600}
.takes{display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:4px}.take{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--ink2)}
audio{height:32px;width:220px}.none{color:var(--warn);font-size:13px}
"""


def redo_lines() -> dict[str, set[int]]:
    """Sheet number → line numbers on the re-record list ("| … | 4 · line 34 | …")."""
    out: dict[str, set[int]] = {}
    path = SHEETS / "re-record.md"
    if path.exists():
        for m in re.finditer(r"\|\s*(\d)\s*·\s*line\s*(\d+)", path.read_text("utf-8")):
            out.setdefault(m.group(1), set()).add(int(m.group(2)))
    return out


def main() -> None:
    settings = Settings.load(cwd=ROOT)
    index = load_index(settings)
    root = index_path(settings).parent
    redo = redo_lines()
    parts = ['<h1>Your voice: review</h1><p class="sub">Every take the app plays, in sheet order. '
             'Orange rows are on the re-record list.</p>']
    for manifest in sorted(SHEETS.glob("*.json")):
        sheet = json.loads(manifest.read_text("utf-8"))
        sheet_no = sheet["session"].split("-")[0]
        clips = sheet["clips"]
        recorded = sum(1 for c in clips if index.get(norm(c["text"])))
        parts.append(f'<h2>Sheet {sheet_no} · {html.escape(sheet["title"])}</h2>'
                     f'<p class="sub">{recorded} of {len(clips)} lines have your voice</p>')
        section = None
        for c in clips:
            if c["section"] != section:
                section = c["section"]
                parts.append(f"<h3>{html.escape(section)}</h3>")
            takes = [t for t in index.get(norm(c["text"]), []) if (root / t["file"]).exists()]
            is_redo = c["n"] in redo.get(sheet_no, set())
            players = "".join(
                f'<span class="take">{i}<audio controls preload="none" src="{html.escape(t["file"])}"></audio>'
                f'<span title="{html.escape(t.get("source", ""))}">{html.escape(t.get("source", "")[:22])}</span></span>'
                for i, t in enumerate(takes, 1)) or '<span class="none">no take yet</span>'
            cue = f' · say: {html.escape(c["cue"])}' if c.get("cue") else ""
            parts.append(
                f'<div class="row{" redo" if is_redo else ""}"><div class="n">{c["n"]}</div><div>'
                f'<div class="fa" dir="rtl" lang="fa">{html.escape(c["text"])}</div>'
                f'<div class="meta">{html.escape(c.get("tr") or "")} · {html.escape(c["gloss"])}{cue}</div>'
                + ('<div class="flag">on the re-record list</div>' if is_redo else "")
                + f'<div class="takes">{players}</div></div></div>')
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>Voice review</title>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn&display=swap">'
            f'<style>{CSS}</style></head><body><main>{"".join(parts)}</main></body></html>')
    out = root / "review.html"
    out.write_text(page, "utf-8")
    print(out)


if __name__ == "__main__":
    main()
