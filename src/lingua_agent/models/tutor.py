"""Tutor session, messages, and tool-call audit log."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import utcnow


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class ToolCall(BaseModel):
    id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    error: str | None = None


class TutorSession(BaseModel):
    id: str
    learner_id: str = "default"
    source_language: str
    target_language: str
    support_language: str | None = "en"
    current_unit_id: str | None = None
    messages: list[Message] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
