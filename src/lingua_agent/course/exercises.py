"""Generate exercise sessions from course items.

Deterministic for a given seed, so tests are stable and a retry (new seed) gets a
fresh order. Every exercise carries its answer; the client grades locally and
reports per-item results back.
"""

from __future__ import annotations

import random
import re
from typing import Iterable, Literal

from pydantic import BaseModel, Field

from .models import CourseItem

ExerciseKind = Literal["intro", "choose_gloss", "choose_text", "listen", "match", "order", "type_tr"]


class Exercise(BaseModel):
    id: str
    kind: ExerciseKind
    item: CourseItem | None = None
    choices: list[str] = Field(default_factory=list)
    answer: str | None = None
    pairs: list[CourseItem] = Field(default_factory=list)
    tiles: list[str] = Field(default_factory=list)
    hide_tr: bool = False


_WORD_SPLIT = re.compile(r"\s+")


def words(text: str) -> list[str]:
    return [w for w in _WORD_SPLIT.split(text.strip()) if w]


def normalize_tr(s: str) -> str:
    """Lenient transliteration compare: lowercase, â→a, drop punctuation, spaces, hyphens."""
    s = s.lower().replace("â", "a").replace("ā", "a")
    return re.sub(r"[^a-z]", "", s)


class _Builder:
    def __init__(self, session_id: str, pool: list[CourseItem], rng: random.Random):
        self.session_id = session_id
        self.pool = pool
        self.rng = rng
        self.out: list[Exercise] = []

    def _add(self, **kw) -> None:
        self.out.append(Exercise(id=f"{self.session_id}-{len(self.out)}", **kw))

    def _distractors(self, item: CourseItem, attr: str, k: int = 3) -> list[str]:
        own = getattr(item, attr)
        seen = {own}
        candidates = []
        for other in self.pool:
            value = getattr(other, attr)
            if other.id != item.id and value and value not in seen:
                seen.add(value)
                candidates.append(value)
        # Prefer distractors of similar length: they make for a fairer choice.
        candidates.sort(key=lambda v: abs(len(v) - len(own)) + self.rng.random() * 4)
        return candidates[:k]

    def _choices(self, item: CourseItem, attr: str) -> list[str]:
        choices = [getattr(item, attr), *self._distractors(item, attr)]
        self.rng.shuffle(choices)
        return choices

    def intro(self, item: CourseItem) -> None:
        self._add(kind="intro", item=item)

    def choose_gloss(self, item: CourseItem, *, hide_tr: bool = False) -> None:
        self._add(kind="choose_gloss", item=item, choices=self._choices(item, "gloss"),
                  answer=item.gloss, hide_tr=hide_tr)

    def choose_text(self, item: CourseItem) -> None:
        self._add(kind="choose_text", item=item, choices=self._choices(item, "text"), answer=item.text)

    def listen(self, item: CourseItem) -> None:
        self._add(kind="listen", item=item, choices=self._choices(item, "text"),
                  answer=item.text, hide_tr=True)

    def type_tr(self, item: CourseItem) -> None:
        self._add(kind="type_tr", item=item, answer=item.tr, hide_tr=True)

    def order(self, item: CourseItem) -> None:
        tiles = words(item.text)
        own = set(tiles)
        extra = [w for other in self.pool if other.id != item.id for w in words(other.text) if w not in own]
        extra = list(dict.fromkeys(extra))
        self.rng.shuffle(extra)
        tiles += extra[: 1 if len(tiles) < 4 else 2]
        self.rng.shuffle(tiles)
        self._add(kind="order", item=item, tiles=tiles, answer=item.text)

    def match(self, items: list[CourseItem]) -> None:
        # Glosses and texts must be unique for an unambiguous match.
        picked, glosses, texts = [], set(), set()
        for it in items:
            if it.gloss not in glosses and it.text not in texts:
                picked.append(it)
                glosses.add(it.gloss)
                texts.add(it.text)
        if len(picked) >= 3:
            self._add(kind="match", pairs=picked[:5])

    def practice(self, item: CourseItem, *, hide_tr: bool) -> None:
        """One non-intro exercise for an item, picked to suit it."""
        options = ["choose_gloss", "choose_text", "listen"]
        if len(words(item.text)) >= 2:
            options += ["order", "order"]
        elif item.tr and len(normalize_tr(item.tr)) <= 12:
            options.append("type_tr")
        kind = self.rng.choice(options)
        if kind == "choose_gloss":
            self.choose_gloss(item, hide_tr=hide_tr)
        else:
            getattr(self, kind)(item)


def lesson_session(session_id: str, items: list[CourseItem], pool: Iterable[CourseItem],
                   *, kind: str = "words", seed: str = "") -> list[Exercise]:
    """New items: introduce in pairs, check each right away, then a mixed round and a match."""
    rng = random.Random(f"{session_id}:{seed}")
    pool = _pool(items, pool)
    b = _Builder(session_id, pool, rng)
    script = kind == "script"
    for i in range(0, len(items), 2):
        chunk = items[i:i + 2]
        for it in chunk:
            b.intro(it)
        for it in chunk:
            # Letters: recognise the sound; phrases: recognise the meaning with tr as a crutch.
            b.choose_gloss(it, hide_tr=script)
    review = list(items)
    rng.shuffle(review)
    for it in review:
        if script:
            rng.choice([b.listen, b.choose_text])(it)
        else:
            b.practice(it, hide_tr=False)
    b.match(rng.sample(items, len(items)))
    return b.out


def quiz_session(session_id: str, items: list[CourseItem], pool: Iterable[CourseItem],
                 *, n: int = 15, seed: str = "") -> list[Exercise]:
    """Checkpoint: one exercise per item (no intros, no transliteration crutch), then a match."""
    rng = random.Random(f"{session_id}:{seed}")
    pool = _pool(items, pool)
    b = _Builder(session_id, pool, rng)
    chosen = rng.sample(items, min(n, len(items)))
    for it in chosen:
        b.practice(it, hide_tr=True)
    b.match(rng.sample(items, min(len(items), 5)))
    return b.out


def practice_session(session_id: str, items: list[CourseItem], pool: Iterable[CourseItem],
                     *, seed: str = "") -> list[Exercise]:
    """Items arrive pre-sorted weakest first; keep that priority but vary the kinds."""
    rng = random.Random(f"{session_id}:{seed}")
    pool = _pool(items, pool)
    b = _Builder(session_id, pool, rng)
    for it in items:
        b.practice(it, hide_tr=rng.random() < 0.5)
    if len(items) >= 4:
        b.match(items[:5])
    return b.out


def _pool(items: list[CourseItem], pool: Iterable[CourseItem]) -> list[CourseItem]:
    merged = {i.id: i for i in pool}
    merged.update({i.id: i for i in items})
    return list(merged.values())
