"""Tests for OpenAICompatibleProvider using httpx.MockTransport.

We mock the HTTP layer (no network required) and assert:
- successful structured generation
- JSON-fence stripping
- repair loop on Pydantic validation failure
- give-up after max attempts
- json_mode fallback on 400 from the backend
- chat() pass-through
- missing API key error for non-local URLs
"""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest
from pydantic import BaseModel, Field

from lingua_agent.ai.base import ChatMessage, GenerationError
from lingua_agent.ai.openai_compatible import OpenAICompatibleProvider
from lingua_agent.config import Settings


class Item(BaseModel):
    name: str
    score: int = Field(ge=0, le=10)


def _make_settings(monkeypatch: pytest.MonkeyPatch, *, base_url: str = "http://localhost:11434/v1",
                    api_key: str | None = None, model: str = "gemma3:12b") -> Settings:
    monkeypatch.setenv("OPENAI_BASE_URL", base_url)
    monkeypatch.setenv("OPENAI_MODEL", model)
    if api_key:
        monkeypatch.setenv("OPENAI_API_KEY", api_key)
    else:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return Settings.load()


def _provider(handler: Callable[[httpx.Request], httpx.Response], settings: Settings,
              **kwargs) -> OpenAICompatibleProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return OpenAICompatibleProvider(settings, client=client, **kwargs)


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_generate_structured_happy_path(monkeypatch):
    settings = _make_settings(monkeypatch)
    payload_seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload_seen.update(json.loads(request.content))
        return httpx.Response(200, json=_completion('{"name": "coffee", "score": 5}'))

    p = _provider(handler, settings)
    result = p.generate_structured("anything", Item)
    assert result == Item(name="coffee", score=5)
    assert payload_seen["model"] == "gemma3:12b"
    assert payload_seen["response_format"] == {"type": "json_object"}


def test_strips_json_fences(monkeypatch):
    settings = _make_settings(monkeypatch)
    fenced = "```json\n{\"name\": \"caffè\", \"score\": 7}\n```"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion(fenced))

    p = _provider(handler, settings)
    result = p.generate_structured("anything", Item)
    assert result.name == "caffè"


def test_repair_loop_on_validation_error(monkeypatch):
    settings = _make_settings(monkeypatch)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(200, json=_completion('{"name": "x", "score": 99}'))  # score > 10
        return httpx.Response(200, json=_completion('{"name": "x", "score": 4}'))

    p = _provider(handler, settings)
    result = p.generate_structured("anything", Item)
    assert result.score == 4
    assert len(calls) == 2
    # The repair message includes the validation error.
    repair_msgs = calls[1]["messages"]
    assert any("validation failed" in (m.get("content") or "") for m in repair_msgs)


def test_gives_up_after_max_attempts(monkeypatch):
    settings = _make_settings(monkeypatch)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json=_completion("not json"))

    p = _provider(handler, settings, max_repair_attempts=2)
    with pytest.raises(GenerationError) as exc:
        p.generate_structured("anything", Item)
    assert len(calls) == 3  # initial + 2 repairs
    assert "after 3 attempts" in str(exc.value)


def test_falls_back_when_json_mode_rejected(monkeypatch):
    settings = _make_settings(monkeypatch)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        if "response_format" in body:
            return httpx.Response(400, text="response_format not supported by this model")
        return httpx.Response(200, json=_completion('{"name": "ok", "score": 1}'))

    p = _provider(handler, settings)
    result = p.generate_structured("anything", Item)
    assert result == Item(name="ok", score=1)
    # First call had json mode, second did not.
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]


def test_chat_passes_through(monkeypatch):
    settings = _make_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "ciao"}}],
        })

    p = _provider(handler, settings)
    response = p.chat([ChatMessage(role="user", content="hi")])
    assert response.content == "ciao"


def test_requires_api_key_for_remote_url(monkeypatch):
    settings = _make_settings(monkeypatch, base_url="https://api.openai.com/v1")
    with pytest.raises(GenerationError) as exc:
        OpenAICompatibleProvider(settings)
    assert "OPENAI_API_KEY" in str(exc.value)


def test_no_api_key_required_for_localhost(monkeypatch):
    settings = _make_settings(monkeypatch, base_url="http://localhost:11434/v1")

    def handler(request: httpx.Request) -> httpx.Response:
        # Authorization header should NOT be present when no key is configured.
        assert "authorization" not in {k.lower() for k in request.headers.keys()}
        return httpx.Response(200, json=_completion('{"name": "x", "score": 0}'))

    p = _provider(handler, settings)
    p.generate_structured("anything", Item)


def test_authorization_header_when_key_set(monkeypatch):
    settings = _make_settings(monkeypatch, base_url="https://api.openai.com/v1", api_key="sk-test")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(200, json=_completion('{"name": "x", "score": 0}'))

    p = _provider(handler, settings)
    p.generate_structured("anything", Item)


def test_salvages_json_from_prose(monkeypatch):
    settings = _make_settings(monkeypatch)
    prose = 'Sure thing! Here you go: {"name": "salvaged", "score": 3}. Hope this helps.'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion(prose))

    p = _provider(handler, settings)
    result = p.generate_structured("anything", Item)
    assert result.name == "salvaged"
