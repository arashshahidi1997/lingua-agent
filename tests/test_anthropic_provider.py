"""Tests for AnthropicProvider — fake the SDK client, no network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, Field

from lingua_agent.ai.anthropic_provider import AnthropicProvider
from lingua_agent.ai.base import ChatMessage, GenerationError
from lingua_agent.config import Settings


class Item(BaseModel):
    name: str
    score: int = Field(ge=0, le=10)


class FakeMessages:
    def __init__(self, *responses: Any):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, *responses: Any):
        self.messages = FakeMessages(*responses)


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    return Settings.load()


def _tool_use_response(tool_name: str, args: dict[str, Any]) -> SimpleNamespace:
    block = SimpleNamespace(type="tool_use", name=tool_name, input=args)
    return SimpleNamespace(content=[block])


def _text_response(text: str) -> SimpleNamespace:
    block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[block])


# ---- structured output (forced tool-use) ---------------------------------

def test_generate_structured_via_forced_tool_use(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient(_tool_use_response("emit_item", {"name": "coffee", "score": 5}))
    p = AnthropicProvider(settings, client=client)

    result = p.generate_structured("anything", Item)

    assert result == Item(name="coffee", score=5)
    call = client.messages.calls[0]
    # Forced tool choice with our tool's name.
    assert call["tool_choice"] == {"type": "tool", "name": "emit_item"}
    # Tool's input_schema is the model's JSON schema.
    assert call["tools"][0]["name"] == "emit_item"
    assert "properties" in call["tools"][0]["input_schema"]


def test_repair_loop_on_validation_failure(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient(
        _tool_use_response("emit_item", {"name": "x", "score": 99}),  # invalid
        _tool_use_response("emit_item", {"name": "x", "score": 4}),
    )
    p = AnthropicProvider(settings, client=client, max_repair_attempts=1)

    result = p.generate_structured("anything", Item)
    assert result.score == 4
    assert len(client.messages.calls) == 2
    # The repair message complains about validation.
    repair_msgs = client.messages.calls[1]["messages"]
    assert any("validation failed" in m["content"] for m in repair_msgs if isinstance(m["content"], str))


def test_gives_up_after_max_attempts(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient(
        _tool_use_response("emit_item", {"name": "x", "score": 99}),
        _tool_use_response("emit_item", {"name": "x", "score": 99}),
    )
    p = AnthropicProvider(settings, client=client, max_repair_attempts=1)
    with pytest.raises(GenerationError) as exc:
        p.generate_structured("anything", Item)
    assert "after 2 attempts" in str(exc.value)


def test_falls_back_to_text_json_if_no_tool_use(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient(_text_response('{"name": "fallback", "score": 2}'))
    p = AnthropicProvider(settings, client=client)
    result = p.generate_structured("anything", Item)
    assert result.name == "fallback"


# ---- prompt caching ------------------------------------------------------

def test_system_prompt_marked_for_caching_by_default(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient(_tool_use_response("emit_item", {"name": "x", "score": 0}))
    p = AnthropicProvider(settings, client=client)
    p.generate_structured("anything", Item)
    sys_blocks = client.messages.calls[0]["system"]
    assert isinstance(sys_blocks, list)
    assert sys_blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_caching_can_be_disabled(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient(_text_response("hi"))
    p = AnthropicProvider(settings, client=client, cache_system_prompt=False)
    p.chat([ChatMessage(role="system", content="be a tutor"),
            ChatMessage(role="user", content="hello")])
    sys_blocks = client.messages.calls[0]["system"]
    assert all("cache_control" not in b for b in sys_blocks)


# ---- chat passthrough ----------------------------------------------------

def test_chat_returns_text_and_tool_calls(monkeypatch):
    settings = _settings(monkeypatch)
    text_block = SimpleNamespace(type="text", text="ciao")
    tool_block = SimpleNamespace(type="tool_use", name="some_tool", input={"a": 1})
    response = SimpleNamespace(content=[text_block, tool_block])
    client = FakeClient(response)
    p = AnthropicProvider(settings, client=client)
    out = p.chat([ChatMessage(role="user", content="hi")])
    assert out.content == "ciao"
    assert out.tool_calls and out.tool_calls[0]["name"] == "some_tool"


def test_chat_requires_non_system_message(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient()
    p = AnthropicProvider(settings, client=client)
    with pytest.raises(GenerationError):
        p.chat([ChatMessage(role="system", content="just system")])


# ---- API key requirement ------------------------------------------------

def test_requires_api_key_when_no_client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings.load()
    with pytest.raises(GenerationError) as exc:
        AnthropicProvider(settings)
    assert "ANTHROPIC_API_KEY" in str(exc.value)
    assert "claude-max" in str(exc.value)  # mention the alternative
