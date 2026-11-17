"""Reading sheets + manifests for recording a native speaker's voice for a course.

    .venv/bin/python tools/recording_scripts.py            # writes content/recording/<course>/

Each session is one continuous recording: the speaker reads the numbered lines in
order with a pause between them. The manifest lists, in the same order, which
course items / story lines each clip belongs to, so the recording can be split at
the pauses and every clip filed under its ids. Identical texts are read once and
shared by every item that uses them.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lingua_agent.config import Settings  # noqa: E402
from lingua_agent.course import store  # noqa: E402

SESSIONS = [
    ("1-hello", "Hello · who's who", ["u1", "u4"]),
    ("2-numbers-cafe", "Numbers · at the café", ["u5", "u6"]),
    ("3-verbs-around", "Everyday verbs · getting around", ["u7", "u8"]),
    ("4-letters", "The alphabet", ["u2", "u3"]),
]


def _clips(course, unit_ids: list[str]) -> list[dict]:
    clips: list[dict] = []
    by_text: dict[str, dict] = {}

    def add(text: str, tr: str | None, gloss: str, ref: str, section: str, cue: str | None = None) -> None:
        key = " ".join(text.split())
        if key in by_text:
            by_text[key]["refs"].append(ref)
            return
        clip = {"n": len(clips) + 1, "text": key, "tr": tr, "gloss": gloss, "refs": [ref],
                "section": section, "cue": cue}
        by_text[key] = clip
        clips.append(clip)

    for uid in unit_ids:
        unit = course.unit(uid)
        for lesson in unit.lessons:
            section = f"{unit.title} · {lesson.title}"
            for it in lesson.items:
                # Letters: say the letter's name (the gloss starts with it), e.g. "alef".
                cue = it.gloss.split("—")[0].strip() if lesson.kind == "script" and len(it.text) <= 2 else None
                add(it.text, it.tr, it.gloss, f"item:{it.id}", section, cue)
        if unit.story and (st := course.story(unit.story)):
            for ln in st.lines:
                speaker = st.speakers[ln.speaker].name
                add(ln.text, ln.tr, ln.gloss, f"line:{ln.id}", f"{st.title_gloss or st.title} ({st.kind})", speaker)
        if unit.scenario and (sc := course.scenario(unit.scenario)):
            for i, p in enumerate([sc.opener, *sc.useful]):
                add(p.text, p.tr, p.gloss, f"phrase:{sc.id}-{i}", f"Role-play · {sc.title}")
    return clips


CSS = """
:root{--bg:#fbf8f3;--ink:#1f1b16;--ink2:#6b6157;--line:#e7dfd3;--acc:#0f766e}
@media (prefers-color-scheme:dark){:root{--bg:#141210;--ink:#f3eee7;--ink2:#a89d90;--line:#2c2823;--acc:#5eead4}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
main{max-width:40rem;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--ink2);margin:0 0 20px}
.how{border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin-bottom:28px}
.how li{margin:4px 0}h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin:28px 0 6px}
.row{display:grid;grid-template-columns:2.5rem 1fr;gap:4px 12px;padding:14px 0;border-top:1px solid var(--line)}
.n{color:var(--ink2);font-variant-numeric:tabular-nums;padding-top:8px}
.fa{font-family:Vazirmatn,"Noto Naskh Arabic",sans-serif;font-size:28px;line-height:1.6;text-align:right}
.meta{grid-column:2;color:var(--ink2);font-size:14px}.cue{color:var(--acc);font-size:14px}
"""


def _sheet(title: str, session_id: str, clips: list[dict]) -> str:
    rows, last = [], None
    for c in clips:
        if c["section"] != last:
            rows.append(f"<h2>{html.escape(c['section'])}</h2>")
            last = c["section"]
        cue = f'<div class="meta cue">{html.escape(c["cue"])}</div>' if c["cue"] else ""
        rows.append(
            f'<div class="row"><div class="n">{c["n"]}</div>'
            f'<div class="fa" dir="rtl" lang="fa">{html.escape(c["text"])}</div>{cue}'
            f'<div class="meta">{html.escape(c["tr"] or "")} · {html.escape(c["gloss"])}</div></div>'
        )
    minutes = round(len(clips) * 4.5 / 60)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recording {session_id}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500&display=swap">
<style>{CSS}</style></head><body><main>
<h1>Recording {session_id[0]} · {html.escape(title)}</h1>
<p class="sub">{len(clips)} lines · about {minutes} minutes · one recording, file name <b>{session_id}</b></p>
<ol class="how">
<li>Read only the <b>Persian</b>, at a natural, slightly slow pace. Don't read the numbers or the English.</li>
<li>Pause about <b>2 seconds</b> after each line (count "one, two" in your head).</li>
<li>A slip? Pause, then read the <b>same line again</b>. I keep the last take.</li>
<li>Green names: for a letter, say its <b>name</b> (alef, be…); in a dialogue, it's who speaks, so you can act it out a little.</li>
<li>A quiet room, phone about a hand's width from your mouth. Any recorder app or a Telegram voice note works.</li>
</ol>
{''.join(rows)}
</main></body></html>"""


def main() -> None:
    course = store.get_course(Settings.load(cwd=ROOT), "fa-en-a1")
    out = ROOT / "content" / "recording" / course.id
    out.mkdir(parents=True, exist_ok=True)
    for session_id, title, units in SESSIONS:
        clips = _clips(course, units)
        (out / f"{session_id}.html").write_text(_sheet(title, session_id, clips), "utf-8")
        manifest = {"course": course.id, "session": session_id, "title": title, "units": units, "clips": clips}
        (out / f"{session_id}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
        print(f"{session_id}: {len(clips)} clips")


if __name__ == "__main__":
    main()
