"""A native speaker's recorded takes, preferred over synthetic speech.

`tools/native_voice.py` cuts a recording into takes and writes them, with an index keyed by the
(normalised) text, under `${shared_data_dir}/native_audio/`. Several takes per text are kept on purpose:
`pick_take` returns one at random each time, so a learner hears natural variation instead of getting used
to one exact recording of a word.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ..config import Settings


def norm(text: str) -> str:
    return " ".join(text.split())


def index_path(settings: Settings) -> Path:
    return settings.shared_data_dir / "native_audio" / "index.json"


def load_index(settings: Settings) -> dict[str, list[dict]]:
    path = index_path(settings)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text("utf-8"))
    except ValueError:
        return {}


def takes_for(settings: Settings, text: str, *, include_bad: bool = False) -> list[dict]:
    """The text's takes on disk; takes marked bad in the voice review are left out unless asked for."""
    root = index_path(settings).parent
    return [t for t in load_index(settings).get(norm(text), [])
            if (root / t["file"]).exists() and (include_bad or not t.get("bad"))]


def set_bad(settings: Settings, file: str, bad: bool) -> bool:
    """Mark a take bad (it stops being played) or good again. False if no such take."""
    index = load_index(settings)
    found = False
    for takes in index.values():
        for t in takes:
            if t["file"] == file:
                t["bad"] = bad
                found = True
    if found:
        path = index_path(settings)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(path)
    return found


def pick_take(settings: Settings, text: str) -> tuple[Path, dict] | None:
    takes = takes_for(settings, text)
    if not takes:
        return None
    take = random.choice(takes)
    return index_path(settings).parent / take["file"], take


def native_count(settings: Settings) -> int:
    return len(load_index(settings))
