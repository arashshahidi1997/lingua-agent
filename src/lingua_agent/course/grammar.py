"""Grammar lab: discover a pattern from examples, then the rule, then practice.

Topics are hand-written YAML (`course/data/grammar/<course>.yaml`). A topic is `draft` until the owner has
reviewed it; drafts are shown to the owner only. Answers are checked here, in script (ZWNJ and diacritics
optional) or transliteration, so the client never needs its own Persian normalisation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .cloze import norm_fa
from .exercises import normalize_tr

DATA = Path(__file__).parent / "data" / "grammar"


class Example(BaseModel):
    text: str
    tr: str | None = None
    gloss: str
    hl: list[str] = Field(default_factory=list)   # parts of `text` to highlight


class Sentence(BaseModel):
    text: str
    tr: str | None = None
    gloss: str | None = None


class Task(BaseModel):
    kind: Literal["predict", "transform", "choose"]
    prompt: str
    given: str | None = None          # a frame with ___ for the answer (predict / choose)
    from_: Sentence | None = Field(None, alias="from")   # the sentence to change (transform)
    answer: str
    answer_tr: str | None = None
    accept: list[str] = Field(default_factory=list)
    choices: list[str] = Field(default_factory=list)
    mode: Literal["any", "tr"] = "any"   # tr: answer in transliteration (e.g. ezafe, invisible in script)

    model_config = {"populate_by_name": True}


class Topic(BaseModel):
    id: str
    title: str
    title_fa: str = ""
    unit: str | None = None
    status: Literal["draft", "reviewed"] = "draft"
    intro: str = ""
    examples: list[Example]
    question: str
    choices: list[str]
    correct: int
    why: str = ""
    rule: str
    tasks: list[Task]


class GrammarDef(BaseModel):
    course: str
    topics: list[Topic]


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> GrammarDef:
    return GrammarDef.model_validate(yaml.safe_load(Path(path).read_text("utf-8")))


def load(course_id: str) -> GrammarDef | None:
    path = DATA / f"{course_id}.yaml"
    if not path.exists():
        return None
    return _load(str(path), path.stat().st_mtime)


def approvals_path(shared_dir: Path) -> Path:
    return shared_dir / "grammar_reviews.json"


def approvals(shared_dir: Path) -> dict[str, str]:
    """Topic id → status set by the owner in the app ("reviewed" / "draft"), overriding the YAML."""
    import json
    path = approvals_path(shared_dir)
    try:
        return json.loads(path.read_text("utf-8")) if path.exists() else {}
    except ValueError:
        return {}


def set_approval(shared_dir: Path, topic_id: str, status: str) -> None:
    import json
    data = approvals(shared_dir)
    data[topic_id] = status
    approvals_path(shared_dir).parent.mkdir(parents=True, exist_ok=True)
    approvals_path(shared_dir).write_text(json.dumps(data, indent=1), "utf-8")


def check(task: Task, given: str) -> bool:
    """Right if it matches the answer (or an accepted one) in script or transliteration."""
    given = given.strip()
    if not given:
        return False
    if task.kind == "choose":
        return given == task.answer
    script = [task.answer, *[a for a in task.accept if not a.isascii()]]
    translit = [t for t in [task.answer_tr, *[a for a in task.accept if a.isascii()]] if t]
    if task.mode != "tr" and any(norm_fa(given) == norm_fa(s) for s in script):
        return True
    return any(normalize_tr(given) == normalize_tr(t) for t in translit)
