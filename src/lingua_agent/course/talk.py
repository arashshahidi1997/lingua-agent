"""Talk: role-play conversations with an AI character, with gentle corrections.

Each assistant turn is structured (`TalkTurn`): what the character says, its
transliteration and meaning, and — only when needed — a correction of the
learner's last message. Ending a session produces a `TalkSummaryDraft` whose
mistakes and new words become flashcards.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..ai.base import AIProvider
from ..languages import get_language
from ..models.base import utcnow
from .models import CourseDef, ScenarioDef


class TalkTurn(BaseModel):
    text: str = Field(description="What the character says, in the target language. 1–2 short sentences.")
    tr: str | None = Field(None, description="Transliteration of `text` (Latin script), if the target uses another script.")
    gloss: str | None = Field(None, description="Meaning of `text` in the support language.")
    correction: str | None = Field(None, description="One short sentence in the support language, only if the learner's last message had a real mistake; otherwise null.")
    better: str | None = Field(None, description="A corrected, natural version of the learner's last message in the target language; null if it was fine.")


class TalkMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    turn: TalkTurn | None = None
    created_at: datetime = Field(default_factory=utcnow)


class TalkSession(BaseModel):
    id: str
    course_id: str | None = None
    scenario_id: str | None = None
    target: str
    support: str
    messages: list[TalkMessage] = Field(default_factory=list)
    ended: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TalkMistake(BaseModel):
    you_said: str
    better: str
    note: str


class TalkWord(BaseModel):
    text: str
    tr: str | None = None
    gloss: str


class TalkSummaryDraft(BaseModel):
    went_well: str = Field(description="One or two encouraging sentences in the support language.")
    mistakes: list[TalkMistake] = Field(default_factory=list, description="Up to 5 real mistakes from the learner's messages.")
    new_words: list[TalkWord] = Field(default_factory=list, description="Up to 6 useful target-language words or phrases from the conversation the learner should learn.")


def _lang_name(code: str) -> str:
    try:
        return get_language(code).name
    except Exception:  # unknown code: fall back to the code itself
        return code


TRANSLIT_HINT = {
    "fa": "Transliterate Persian with: â = long a, a/e/o short vowels, i = ee, u = oo, kh, gh, sh, zh, ch; ezafe as -e / -ye.",
    "ru": "Transliterate Russian with simple English-style romanisation (zh, kh, ts, ch, sh, shch, y).",
}


def persona_name(scenario: ScenarioDef) -> str:
    """Short display name from the persona text: "Maryam (مریم), around 30, …" → "Maryam"."""
    return scenario.persona.strip().split("(")[0].split(",")[0].strip() or "Partner"


def _transcript(session: TalkSession, persona_name: str) -> str:
    lines = []
    for m in session.messages:
        who = "Learner" if m.role == "user" else persona_name
        lines.append(f"{who}: {m.content}")
    return "\n".join(lines) or "(no messages yet)"


def turn_prompt(session: TalkSession, scenario: ScenarioDef | None, course: CourseDef | None,
                user_message: str) -> str:
    target, support = _lang_name(session.target), _lang_name(session.support)
    level = course.level if course else "A1"
    if scenario:
        role = (f"Role-play scenario.\nSetting: {scenario.setting.strip()}\nYou play: {scenario.persona.strip()}\n"
                f"The learner's goal: {scenario.goal}\n")
        name = persona_name(scenario)
    else:
        role = "Free conversation. You are a friendly conversation partner from a country where the language is spoken.\n"
        name = "Partner"
    return (
        f"You are helping a {level} learner practise speaking {target}. Their support language is {support}.\n"
        f"{role}\n"
        "Rules:\n"
        f"- Stay in character and reply ONLY in simple, natural, everyday {target} at {level} level: 1–2 short sentences, "
        "and usually end with a simple question so the conversation keeps going.\n"
        "- Recast gently: never lecture inside the conversation. If the learner's last message has a real mistake, "
        f"put a one-sentence explanation in `correction` (in {support}) and a corrected version in `better` (in {target}). "
        "If it was fine or only informal, set both to null.\n"
        f"- If the learner writes in {support} or seems stuck, answer in very simple {target} and include in `gloss` what they could say.\n"
        f"- `gloss` is the meaning of your reply in {support}. {TRANSLIT_HINT.get(session.target, '')}\n\n"
        f"Conversation so far:\n{_transcript(session, name)}\n\n"
        f"Learner's new message: {user_message}\n"
    )


def summary_prompt(session: TalkSession, scenario: ScenarioDef | None) -> str:
    target, support = _lang_name(session.target), _lang_name(session.support)
    goal = f"The learner's goal was: {scenario.goal}\n" if scenario else ""
    return (
        f"Review this {target} conversation practice by a beginner (support language {support}).\n{goal}"
        f"Write `went_well` in {support}; list up to 5 real mistakes from the Learner lines only "
        f"(`you_said` verbatim, `better` in {target}, `note` in {support}); and up to 6 useful {target} words or "
        f"phrases from the conversation as `new_words` with `tr` and `gloss` in {support}. "
        f"{TRANSLIT_HINT.get(session.target, '')}\n\n"
        f"Conversation:\n{_transcript(session, 'Partner')}\n"
    )


def opener_turn(scenario: ScenarioDef) -> TalkTurn:
    o = scenario.opener
    return TalkTurn(text=o.text, tr=o.tr, gloss=o.gloss)


def take_turn(provider: AIProvider, session: TalkSession, scenario: ScenarioDef | None,
              course: CourseDef | None, user_message: str) -> TalkMessage:
    prompt = turn_prompt(session, scenario, course, user_message)
    turn = provider.generate_structured(
        prompt, TalkTurn,
        context={"target_language": session.target, "source_language": session.support,
                 "text": user_message, "scenario": scenario.model_dump() if scenario else None},
    )
    session.messages.append(TalkMessage(role="user", content=user_message))
    reply = TalkMessage(role="assistant", content=turn.text, turn=turn)
    session.messages.append(reply)
    session.updated_at = utcnow()
    return reply


def summarize(provider: AIProvider, session: TalkSession, scenario: ScenarioDef | None) -> TalkSummaryDraft:
    if not any(m.role == "user" for m in session.messages):
        return TalkSummaryDraft(went_well="You opened the conversation. Say a few things next time and you'll get feedback here.")
    return provider.generate_structured(
        summary_prompt(session, scenario), TalkSummaryDraft,
        context={"target_language": session.target, "source_language": session.support,
                 "messages": [m.model_dump(mode="json") for m in session.messages]},
    )
