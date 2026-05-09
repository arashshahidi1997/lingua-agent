"""Tests for ClaudeAgentSDKProvider — fake the SDK + the `claude` CLI check."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel, Field

from lingua_agent.ai import claude_agent_sdk_provider as mod
from lingua_agent.ai.base import ChatMessage, GenerationError


class Item(BaseModel):
    name: str
    score: int = Field(ge=0, le=10)


def _patch_sdk(monkeypatch: pytest.MonkeyPatch, *texts: str) -> list[str]:
    """Replace claude_agent_sdk.query with a fake that yields one
    AssistantMessage(text=...) per call. Returns a list recording every
    prompt sent to the fake.

    Uses the real AssistantMessage / TextBlock classes so the provider's
    isinstance() checks pass.
    """
    import claude_agent_sdk
    from claude_agent_sdk import AssistantMessage
    from claude_agent_sdk.types import TextBlock

    iter_texts = iter(texts)
    seen: list[str] = []

    async def fake_query(*, prompt: str, options=None, transport=None):
        seen.append(prompt)
        try:
            text = next(iter_texts)
        except StopIteration:
            raise AssertionError("fake_query ran out of canned responses")
        yield AssistantMessage(content=[TextBlock(text=text)], model="fake")

    monkeypatch.setattr(claude_agent_sdk, "query", fake_query, raising=True)
    return seen


@pytest.fixture
def cli_present(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "_claude_cli_available", lambda: True)


# ---- chat ----------------------------------------------------------------

def test_chat_returns_assembled_text(monkeypatch, cli_present):
    seen = _patch_sdk(monkeypatch, "ciao!")
    p = mod.ClaudeAgentSDKProvider()
    out = p.chat([ChatMessage(role="user", content="say hi in italian")])
    assert out.content == "ciao!"
    assert seen == ["say hi in italian"]


def test_chat_lifts_system_message(monkeypatch, cli_present):
    seen = _patch_sdk(monkeypatch, "hello")
    p = mod.ClaudeAgentSDKProvider()
    p.chat([
        ChatMessage(role="system", content="be a tutor"),
        ChatMessage(role="user", content="hi"),
    ])
    # Single user message → prompt is just that user content (no transcript).
    assert seen == ["hi"]
    # The system message went into options.system_prompt — we trust the SDK
    # call, not the recorded prompt.


def test_chat_flattens_multi_turn_into_transcript(monkeypatch, cli_present):
    seen = _patch_sdk(monkeypatch, "ok")
    p = mod.ClaudeAgentSDKProvider()
    p.chat([
        ChatMessage(role="system", content="be a tutor"),
        ChatMessage(role="user", content="ciao"),
        ChatMessage(role="assistant", content="ciao!"),
        ChatMessage(role="user", content="how are you"),
    ])
    assert "USER: ciao" in seen[0]
    assert "ASSISTANT: ciao!" in seen[0]
    assert seen[0].endswith("ASSISTANT:")


def test_chat_requires_non_system_message(monkeypatch, cli_present):
    _patch_sdk(monkeypatch)
    p = mod.ClaudeAgentSDKProvider()
    with pytest.raises(GenerationError):
        p.chat([ChatMessage(role="system", content="just system")])


# ---- structured generation -----------------------------------------------

def test_generate_structured_happy_path(monkeypatch, cli_present):
    _patch_sdk(monkeypatch, '{"name": "coffee", "score": 5}')
    p = mod.ClaudeAgentSDKProvider()
    result = p.generate_structured("anything", Item)
    assert result == Item(name="coffee", score=5)


def test_generate_structured_strips_fences(monkeypatch, cli_present):
    _patch_sdk(monkeypatch, '```json\n{"name": "x", "score": 0}\n```')
    p = mod.ClaudeAgentSDKProvider()
    result = p.generate_structured("anything", Item)
    assert result.name == "x"


def test_repair_on_validation_error(monkeypatch, cli_present):
    seen = _patch_sdk(
        monkeypatch,
        '{"name": "x", "score": 99}',  # invalid: out of range
        '{"name": "x", "score": 4}',
    )
    p = mod.ClaudeAgentSDKProvider(max_repair_attempts=1)
    result = p.generate_structured("anything", Item)
    assert result.score == 4
    assert len(seen) == 2
    # Repair prompt mentions validation failure.
    assert "validation failed" in seen[1]


def test_gives_up_after_max_attempts(monkeypatch, cli_present):
    _patch_sdk(monkeypatch, "not json", "still not json")
    p = mod.ClaudeAgentSDKProvider(max_repair_attempts=1)
    with pytest.raises(GenerationError) as exc:
        p.generate_structured("anything", Item)
    assert "after 2 attempts" in str(exc.value)


def test_salvages_json_from_prose(monkeypatch, cli_present):
    _patch_sdk(monkeypatch, 'Sure! Here you go: {"name": "salvaged", "score": 1}.')
    p = mod.ClaudeAgentSDKProvider()
    result = p.generate_structured("anything", Item)
    assert result.name == "salvaged"


# ---- environment guard ---------------------------------------------------

def test_missing_claude_cli_raises(monkeypatch):
    monkeypatch.setattr(mod, "_claude_cli_available", lambda: False)
    with pytest.raises(GenerationError) as exc:
        mod.ClaudeAgentSDKProvider()
    msg = str(exc.value)
    assert "claude" in msg
    assert "claude login" in msg


def test_async_context_error_is_caught(monkeypatch, cli_present):
    """When invoked from inside a running event loop, raise a clear error."""
    _patch_sdk(monkeypatch, '{"name": "x", "score": 0}')
    p = mod.ClaudeAgentSDKProvider()

    async def inner():
        # Calling from inside an event loop should fail with a GenerationError
        # carrying the "running event loop" hint.
        return p.generate_structured("anything", Item)

    with pytest.raises(GenerationError) as exc:
        asyncio.run(inner())
    assert "event loop" in str(exc.value)
