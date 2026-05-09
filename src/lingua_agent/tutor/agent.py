"""Tutor agent loop (mock implementation).

For MVP this is a deliberately small chat loop:
- Builds the system prompt from the session and learner profile.
- Sends the user message to the AI provider via `chat()`.
- Returns the response as a `Message` and appends it to the session.

Phase 6 wires the tool surface (`tutor/tools.py`) into the loop properly: the
LLM emits tool calls, we dispatch them, and append `ToolCall` entries.
"""

from __future__ import annotations

from ..ai import AIProvider, MockProvider
from ..ai.base import ChatMessage
from ..ai.prompts import tutor_system_prompt
from ..models import LearnerProfile, Message, TutorSession
from ..models.base import utcnow


def reply(*, session: TutorSession, learner: LearnerProfile, user_message: str,
          provider: AIProvider | None = None, due_card_count: int = 0,
          current_unit_title: str | None = None) -> Message:
    provider = provider or MockProvider()
    learner_summary = (
        f"native={','.join(learner.native_languages)}; "
        f"targets={','.join(t.code for t in learner.target_languages) or 'none'}; "
        f"correction={learner.correction_style}"
    )
    sys_prompt = tutor_system_prompt(
        source_language=session.source_language,
        target_language=session.target_language,
        support_language=session.support_language,
        learner_summary=learner_summary,
        due_card_count=due_card_count,
        current_unit_title=current_unit_title,
    )
    msgs = [ChatMessage(role="system", content=sys_prompt)]
    msgs += [ChatMessage(role=m.role, content=m.content) for m in session.messages]
    msgs.append(ChatMessage(role="user", content=user_message))

    response = provider.chat(msgs)
    user_msg = Message(role="user", content=user_message)
    assistant_msg = Message(role="assistant", content=response.content)
    session.messages.append(user_msg)
    session.messages.append(assistant_msg)
    session.updated_at = utcnow()
    return assistant_msg
