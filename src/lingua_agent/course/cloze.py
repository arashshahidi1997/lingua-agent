"""Fill-in-the-blanks over a whole story or dialogue, with gaps chosen by a grammar focus.

Gap choice is rule-based (no AI), from Persian morphology and the course's own words:
- verbs: the می‌/نمی‌ present prefix, forms of «هستن»/«است»/«نیست», «داشتن», past forms of common verbs;
- prepositions: a closed list (به، از، در، با، برای، تا، …);
- vocabulary: words the course teaches as single-word items.
The same story yields different gaps per seed, so it can be read many times.
"""

from __future__ import annotations

import random
import re

from pydantic import BaseModel, Field

from .models import CourseDef, StoryDef

PUNCT = "،؛؟!?.,:«»\"'()…"
_STRIP = re.compile(f"^[{re.escape(PUNCT)}]+|[{re.escape(PUNCT)}]+$")
ENDINGS = ("", "م", "ی", "یم", "ید", "ند")

COPULA = {f"{base}{e}" for base in ("هست", "نیست") for e in ENDINGS} | {"است", "هستش"}
DASHTAN = {f"{neg}دار{e}" for neg in ("", "ن") for e in ("م", "ی", "د", "یم", "ید", "ند")}
PAST_STEMS = ("رفت", "خورد", "خواند", "دید", "آمد", "اومد", "کرد", "بود", "داشت", "گفت", "نوشت", "شد",
              "گرفت", "خرید", "نشست", "زد", "دوید", "پخت", "شست", "آورد", "برد", "ساخت", "خوابید", "پرسید")
PAST = {f"{neg}{stem}{e}" for stem in PAST_STEMS for neg in ("", "ن") for e in ENDINGS}
PREPOSITIONS = {"به", "از", "در", "با", "برای", "تا", "بی", "روی", "زیر", "پیش", "بدون", "مثل", "کنار", "جلوی",
                "پشت", "بین", "توی", "سر"}

FOCUSES = ("mixed", "verbs", "prepositions", "vocab")


def bare(token: str) -> str:
    return _STRIP.sub("", token)


def norm_fa(text: str) -> str:
    """For comparing answers: no ZWNJ, diacritics, tatweel or spaces; Arabic ي/ك as Persian."""
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ـ", "")
    text = re.sub("[ً-ٰٟ‌‍‎‏]", "", text)
    return re.sub(r"\s+", "", text)


def kind_of(word: str, vocab: set[str]) -> str | None:
    w = norm_fa(word)
    if not w:
        return None
    if w.startswith(("می", "نمی")) and len(w) > 3 or w in {norm_fa(x) for x in COPULA | DASHTAN | PAST}:
        return "verb"
    if w in PREPOSITIONS:
        return "preposition"
    if w == "را":
        return "ra"
    if w in vocab:
        return "vocab"
    return None


class Gap(BaseModel):
    id: str
    answer: str            # the word as written, without punctuation
    tr: str | None = None  # its transliteration, when the line's words line up
    kind: str              # verb | preposition | ra | vocab


class Part(BaseModel):
    text: str | None = None   # plain text (with spaces and punctuation)
    gap: Gap | None = None


class ClozeLine(BaseModel):
    speaker: str | None = None
    parts: list[Part]
    tr: str | None = None
    gloss: str


class Cloze(BaseModel):
    story_id: str
    title: str
    title_gloss: str
    focus: str
    lines: list[ClozeLine]
    bank: list[str] = Field(default_factory=list)   # the answers, shuffled, plus a few distractors
    gap_count: int


def _course_vocab(course: CourseDef) -> set[str]:
    return {norm_fa(i.text) for _, lesson in course.lessons() for i in lesson.items
            if lesson.kind != "script" and len(i.text.split()) == 1 and len(norm_fa(i.text)) > 1}


RATIO = {"mixed": 0.45, "verbs": 0.75, "prepositions": 1.0, "vocab": 0.5}   # share of candidates made gaps


def build(course: CourseDef, story: StoryDef, *, focus: str = "mixed", seed: int = 0) -> Cloze:
    if focus not in FOCUSES:
        focus = "mixed"
    ratio = RATIO[focus]
    rng = random.Random(f"{story.id}:{focus}:{seed}")
    vocab = _course_vocab(course)
    wanted = {"mixed": {"verb", "preposition", "ra", "vocab"}, "verbs": {"verb"},
              "prepositions": {"preposition", "ra"}, "vocab": {"vocab"}}[focus]

    # Candidates across the whole text, then a share of them as gaps (at most two per line).
    tokens: list[list[str]] = [ln.text.split() for ln in story.lines]
    cands = [(li, ti) for li, toks in enumerate(tokens) for ti, tok in enumerate(toks)
             if kind_of(bare(tok), vocab) in wanted]
    rng.shuffle(cands)
    target = max(1, round(len(cands) * ratio)) if cands else 0
    chosen: set[tuple[int, int]] = set()
    per_line: dict[int, int] = {}
    for li, ti in cands:
        if len(chosen) >= target:
            break
        if per_line.get(li, 0) >= 2:
            continue
        chosen.add((li, ti))
        per_line[li] = per_line.get(li, 0) + 1

    lines: list[ClozeLine] = []
    answers: list[str] = []
    for li, ln in enumerate(story.lines):
        toks = tokens[li]
        trs = (ln.tr or "").split()
        aligned = len(trs) == len(toks)
        parts: list[Part] = []
        cur = ""
        for ti, tok in enumerate(toks):
            sep = " " if ti else ""
            if (li, ti) not in chosen:
                cur += sep + tok
                continue
            word = bare(tok)
            at = tok.find(word)
            cur += sep + tok[:at]                    # leading punctuation stays outside the gap
            parts.append(Part(text=cur))
            parts.append(Part(gap=Gap(id=f"{li}-{ti}", answer=word, kind=kind_of(word, vocab) or "vocab",
                                      tr=bare(trs[ti]) if aligned else None)))
            answers.append(word)
            cur = tok[at + len(word):]               # and so does trailing punctuation
        parts.append(Part(text=cur))
        speaker = story.speakers[ln.speaker].name if story.kind == "dialogue" and ln.speaker in story.speakers else None
        lines.append(ClozeLine(speaker=speaker, parts=[p for p in parts if p.gap or p.text], tr=ln.tr, gloss=ln.gloss))

    # Word bank: the answers plus a few plausible distractors of the same kinds from the course.
    pool = sorted({w for w in COPULA | PREPOSITIONS if norm_fa(w) not in {norm_fa(a) for a in answers}})
    distract = rng.sample(pool, k=min(len(pool), max(2, len(answers) // 4))) if answers else []
    bank = answers + distract
    rng.shuffle(bank)
    return Cloze(story_id=story.id, title=story.title, title_gloss=story.title_gloss, focus=focus,
                 lines=lines, bank=bank, gap_count=len(answers))


def check(answer: str, given: str, tr: str | None = None) -> bool:
    """A typed answer counts in Persian script (ZWNJ, diacritics optional) or, when known, transliteration."""
    from .exercises import normalize_tr
    if norm_fa(given) and norm_fa(given) == norm_fa(answer):
        return True
    return bool(tr) and bool(normalize_tr(given)) and normalize_tr(given) == normalize_tr(tr)
