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
    summary: dict | None = None  # stored when ended; ending again returns it
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


# ---- prompts for the learner's own chatbot ---------------------------------------------

def chatbot_prompt(course: CourseDef, scenario: ScenarioDef, *, voice: bool = False) -> str:
    """A role-play prompt to paste into any AI chatbot (ChatGPT, Claude, Gemini, …).

    Written in the support language so every chatbot follows it; built from the scenario and the words of
    its unit and the units before it, so the conversation stays at the learner's level. `voice` drops the
    transliteration and translation lines, which a voice mode would otherwise read aloud.
    """
    target, support = _lang_name(course.target), _lang_name(course.support)
    order = [u.id for u in course.units]
    upto = order[: order.index(scenario.unit) + 1] if scenario.unit in order else order
    words: list[str] = []
    for unit in course.units:
        if unit.id not in upto:
            continue
        for lesson in unit.lessons:
            if lesson.kind == "script":
                continue
            for it in lesson.items:
                words.append(f"{it.text} ({it.tr}) = {it.gloss}" if it.tr else f"{it.text} = {it.gloss}")
    for p in scenario.useful:
        line = f"{p.text} ({p.tr}) = {p.gloss}" if p.tr else f"{p.text} = {p.gloss}"
        if line not in words:
            words.append(line)
    # The scenario's own unit matters most: keep its words, then the most recent earlier ones.
    words = words[-40:]
    hint = TRANSLIT_HINT.get(course.target, "")
    if voice:
        format_rules = (f"- We're talking by voice: speak only {target}, slowly and clearly. No transliteration, "
                        f"no translations, unless I ask \"what does that mean?\".\n"
                        f"- If I make a mistake, answer in character first, then say the better version once, "
                        f"briefly, in {support}.")
        opener = scenario.opener.text
    else:
        format_rules = (f"- Write each of your turns as three lines: the {target} sentence, its transliteration in "
                        f"Latin letters, and the {support} meaning in brackets. {hint}\n"
                        f"- If my message has a real mistake, reply in character first, then add one short line "
                        f"starting with \"Better:\" giving the corrected {target}, with a few words of "
                        f"explanation in {support}. Don't correct informal spoken forms that are fine.")
        opener = f"{scenario.opener.text}\n{scenario.opener.tr or ''}\n({scenario.opener.gloss})".strip()
    return (
        f"Let's practise {target} conversation. I'm a beginner ({course.level}); my own language is {support}.\n\n"
        f"Role-play\n"
        f"- Setting: {scenario.setting.strip()}\n"
        f"- You play: {scenario.persona.strip()}\n"
        f"- My goal: {scenario.goal.strip()}\n\n"
        f"How to talk with me\n"
        f"- Stay in character. Use simple, natural, everyday spoken {target}: one or two short sentences per "
        f"turn, and usually end with a simple question so I can answer.\n"
        f"{format_rules}\n"
        f"- Mostly use words I already know (list below). Bring in at most one new word per turn.\n"
        f"- If I write in {support} or seem stuck, give me the {target} sentence I could say.\n"
        f"- When I say \"end\", step out of the role and give me: what went well, up to five mistakes with "
        f"better versions, and five useful new words with their meanings.\n\n"
        f"Words I know\n" + "\n".join(f"- {w}" for w in words) + "\n\n"
        f"Start now, in character, with this line:\n{opener}"
    )
