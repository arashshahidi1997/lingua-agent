"""Anthropic API provider with prompt caching.

Two reasons this is its own provider rather than the OpenAI-compatible one:

1. **Anthropic's API is content-block oriented**, not OpenAI-shaped. The
   SDK gives us cleaner access to message/tool blocks than wrestling raw
   JSON over the OpenAI compat layer some proxies expose.
2. **Prompt caching** — mark the system prompt (and reusable context
   like learner profile + due-card summary) with `cache_control:
   {"type": "ephemeral"}`. After the first turn, cached input tokens
   are billed at ~10% of normal — material savings on chat-heavy tutor
   sessions where the system prompt easily reaches 2–4k tokens.

For **structured output** we use **forced tool-use**: define a tool whose
input schema is the Pydantic schema we want, then ask the model with
`tool_choice={"type": "tool", "name": "..."}`. The model's response
contains a tool_use block whose `input` is already the parsed schema —
no JSON parsing or fence stripping needed.

Falls back to the same repair-loop pattern as the OpenAI provider on
validation errors (rare with tool-use forcing, but possible).
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import Settings
from .base import ChatMessage, ChatResponse, GenerationError

T = TypeVar("T", bound=BaseModel)


def _ensure_sdk():
    try:
        import anthropic  # noqa: F401
    except ImportError as exc:
        raise GenerationError(
            "anthropic SDK is not installed. Install with:  pip install -e \".[anthropic]\""
        ) from exc


# Sentinel used by tests to inject a fake client without going to network.
_TestClientSentinel = object()


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: Any = None,
        cache_system_prompt: bool = True,
        max_repair_attempts: int = 1,
        max_tokens: int = 4096,
    ):
        _ensure_sdk()
        self.settings = settings or Settings.load()
        if client is None and not self.settings.anthropic_api_key:
            raise GenerationError(
                "ANTHROPIC_API_KEY is not set. Set it for the API provider, or use "
                "LINGUA_AI_PROVIDER=claude-max for a Claude Pro/Max subscription "
                "(no API key needed)."
            )
        if client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        else:
            self._client = client
        self.cache_system_prompt = cache_system_prompt
        self.max_repair_attempts = max(0, max_repair_attempts)
        self.max_tokens = max_tokens

    # -- helpers ------------------------------------------------------------

    def _system_blocks(self, system_text: str | None) -> list[dict[str, Any]] | None:
        """Return system as a list of content blocks, the first marked for caching.

        Anthropic's SDK accepts `system=` as either a string or a list of
        text blocks; the block form is the only way to attach
        `cache_control`. We always send a block list when caching is on.
        """
        if not system_text:
            return None
        if not self.cache_system_prompt:
            return [{"type": "text", "text": system_text}]
        return [{
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }]

    @staticmethod
    def _split_system(messages: list[ChatMessage]) -> tuple[str | None, list[ChatMessage]]:
        sys_msgs = [m for m in messages if m.role == "system"]
        body = [m for m in messages if m.role != "system"]
        sys_text = "\n\n".join(m.content for m in sys_msgs) if sys_msgs else None
        return sys_text, body

    @staticmethod
    def _to_anthropic_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            role = "assistant" if m.role == "assistant" else "user"
            out.append({"role": role, "content": m.content})
        return out

    @staticmethod
    def _extract_text(response: Any) -> str:
        # Walk content blocks; concatenate text blocks.
        parts: list[str] = []
        for block in getattr(response, "content", []) or []:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "text":
                text = getattr(block, "text", None) or block.get("text", "")
                parts.append(text)
        return "".join(parts).strip()

    @staticmethod
    def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any] | None:
        for block in getattr(response, "content", []) or []:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype != "tool_use":
                continue
            name = getattr(block, "name", None) or block.get("name")
            if name != tool_name:
                continue
            inp = getattr(block, "input", None) or block.get("input")
            if isinstance(inp, dict):
                return inp
        return None

    # -- public API ---------------------------------------------------------

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        sys_text, body = self._split_system(messages)
        if not body:
            raise GenerationError("chat() requires at least one non-system message")

        kwargs: dict[str, Any] = {
            "model": self.settings.anthropic_model,
            "max_tokens": self.max_tokens,
            "messages": self._to_anthropic_messages(body),
        }
        sys_blocks = self._system_blocks(sys_text)
        if sys_blocks is not None:
            kwargs["system"] = sys_blocks
        if tools:
            kwargs["tools"] = tools

        try:
            response = self._client.messages.create(**kwargs)
        except Exception as exc:  # pragma: no cover - SDK errors are varied
            raise GenerationError(f"Anthropic API call failed: {exc}") from exc

        return ChatResponse(
            content=self._extract_text(response),
            tool_calls=[
                {"name": getattr(b, "name", None), "input": getattr(b, "input", None)}
                for b in getattr(response, "content", []) or []
                if (getattr(b, "type", None) == "tool_use")
            ],
            raw=None,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        context: dict[str, Any] | None = None,
    ) -> T:
        # Forced tool-use pattern: register a single tool whose input_schema
        # is the target Pydantic schema, then force the model to call it.
        schema_json = schema.model_json_schema()
        tool_name = "emit_" + schema.__name__.lower()
        tool = {
            "name": tool_name,
            "description": (
                f"Emit a {schema.__name__} value matching the provided schema. "
                "Always call this tool. Do not add prose."
            ),
            "input_schema": schema_json,
        }

        sys_blocks = self._system_blocks(
            "You return structured data by calling the provided tool. "
            "Never reply in prose. Match the schema exactly."
        )

        attempt_messages: list[dict[str, Any]] = [
            {"role": "user", "content": prompt},
        ]
        last_error: str | None = None

        for _ in range(self.max_repair_attempts + 1):
            kwargs: dict[str, Any] = {
                "model": self.settings.anthropic_model,
                "max_tokens": self.max_tokens,
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": tool_name},
                "messages": attempt_messages,
            }
            if sys_blocks is not None:
                kwargs["system"] = sys_blocks

            try:
                response = self._client.messages.create(**kwargs)
            except Exception as exc:  # pragma: no cover
                raise GenerationError(f"Anthropic API call failed: {exc}") from exc

            tool_input = self._extract_tool_input(response, tool_name)
            if tool_input is None:
                # Fall back to scanning text for JSON, just in case.
                text = self._extract_text(response)
                try:
                    tool_input = json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    last_error = "model did not call the structured-output tool"
                    attempt_messages = self._repair_messages(prompt, repr(response)[:1000], last_error)
                    continue

            try:
                return schema.model_validate(tool_input)
            except ValidationError as exc:
                last_error = f"schema validation failed: {exc}"
                attempt_messages = self._repair_messages(prompt, json.dumps(tool_input), last_error)
                continue

        raise GenerationError(
            f"{self.name} failed to produce schema-valid output after "
            f"{self.max_repair_attempts + 1} attempts. Last error: {last_error}"
        )

    @staticmethod
    def _repair_messages(original_prompt: str, bad_response: str, error: str) -> list[dict[str, Any]]:
        return [
            {"role": "user", "content": original_prompt},
            {"role": "assistant", "content": bad_response[:4000]},
            {
                "role": "user",
                "content": (
                    f"Your previous response failed validation:\n{error}\n\n"
                    "Call the tool again with corrected arguments matching the schema."
                ),
            },
        ]
