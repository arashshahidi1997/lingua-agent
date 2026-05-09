"""Claude Max / Claude Code provider — uses subscription quota, not API tokens.

Wraps `claude-agent-sdk`, which authenticates via the user's existing
Claude Code CLI session (OAuth). For users with a Claude Pro / Max
subscription this means programmatic access is **billed against their
subscription quota**, not against API token usage. Effective marginal
cost: zero (within quota).

Setup for the user:
    1. Install Claude Code:        npm i -g @anthropic-ai/claude-code
    2. Sign in:                    claude login
    3. Configure lingua-agent:     LINGUA_AI_PROVIDER=claude-max

Caveats:
- The SDK shells out to the `claude` CLI under the hood; if `claude` is
  not on PATH, instantiation raises a clear error.
- Subscription quotas (~225 messages / 5h on Max 5x; ~900 / 5h on Max
  20x) are real and not designed for high-throughput backend workloads.
  For ingest-pipeline batch use over many documents, prefer the API
  provider; for interactive tutor sessions, this is ideal.
- The SDK's transport is async; we run it via `asyncio.run` per call so
  the rest of the synchronous pipeline doesn't have to know.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import Settings
from .base import ChatMessage, ChatResponse, GenerationError

T = TypeVar("T", bound=BaseModel)


_FENCED_JSON_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_FIRST_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_json_fences(text: str) -> str:
    m = _FENCED_JSON_RE.match(text)
    return m.group(1) if m else text


def _extract_first_json_object(text: str) -> str | None:
    m = _FIRST_JSON_OBJECT_RE.search(text)
    return m.group(0) if m else None


def _claude_cli_available() -> bool:
    return shutil.which("claude") is not None


def _ensure_sdk():
    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError as exc:
        raise GenerationError(
            "claude-agent-sdk is not installed. Install with:  "
            "pip install -e \".[claude-max]\""
        ) from exc


class ClaudeAgentSDKProvider:
    """Use a Claude Pro/Max subscription via Claude Code's OAuth session."""

    name = "claude-max"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        model: str | None = None,
        max_repair_attempts: int = 2,
        max_turns: int = 1,
    ):
        _ensure_sdk()
        if not _claude_cli_available():
            raise GenerationError(
                "`claude` CLI not found on PATH. Install with:  "
                "npm install -g @anthropic-ai/claude-code   "
                "and sign in with:  claude login"
            )
        self.settings = settings or Settings.load()
        self.model = model or self.settings.anthropic_model
        self.max_repair_attempts = max(0, max_repair_attempts)
        self.max_turns = max_turns

    # -- internal -----------------------------------------------------------

    def _options(self, *, system_prompt: str | None = None) -> Any:
        from claude_agent_sdk import ClaudeAgentOptions
        return ClaudeAgentOptions(
            model=self.model,
            system_prompt=system_prompt,
            max_turns=self.max_turns,
            permission_mode="bypassPermissions",  # we never ask the SDK to use tools
            # We deliberately don't pass `allowed_tools` — keeping the agent in
            # plain-chat mode means it doesn't try to read files, run bash, etc.
            allowed_tools=[],
        )

    async def _collect_text(self, prompt: str, *, system_prompt: str | None) -> str:
        from claude_agent_sdk import AssistantMessage, query
        from claude_agent_sdk.types import TextBlock

        opts = self._options(system_prompt=system_prompt)
        chunks: list[str] = []
        async for msg in query(prompt=prompt, options=opts):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
        return "".join(chunks).strip()

    def _run(self, prompt: str, *, system_prompt: str | None) -> str:
        try:
            return asyncio.run(self._collect_text(prompt, system_prompt=system_prompt))
        except RuntimeError as exc:
            # Most common: "asyncio.run() cannot be called from a running event loop".
            # The fix would be to provide an async-native API; that's a future change.
            raise GenerationError(
                "ClaudeAgentSDKProvider can't be called from inside a running event "
                f"loop yet (use the API provider for async contexts). Underlying error: {exc}"
            ) from exc
        except Exception as exc:  # pragma: no cover - SDK errors are varied
            raise GenerationError(f"claude-agent-sdk call failed: {exc}") from exc

    # -- public API ---------------------------------------------------------

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        # The SDK is single-prompt; flatten the conversation into one prompt
        # and lift the system message up. Good enough for a tutor turn.
        system_prompt = next((m.content for m in messages if m.role == "system"), None)
        body_messages = [m for m in messages if m.role != "system"]
        if not body_messages:
            raise GenerationError("chat() requires at least one non-system message")

        # Render a tiny transcript so multi-turn context survives the flatten.
        if len(body_messages) == 1 and body_messages[0].role == "user":
            prompt = body_messages[0].content
        else:
            lines = [f"{m.role.upper()}: {m.content}" for m in body_messages]
            prompt = "\n\n".join(lines) + "\n\nASSISTANT:"

        text = self._run(prompt, system_prompt=system_prompt)
        return ChatResponse(content=text, tool_calls=[], raw=None)

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        context: dict[str, Any] | None = None,
    ) -> T:
        schema_json = schema.model_json_schema()
        system = (
            "You are a careful assistant that returns ONLY valid JSON conforming exactly to the "
            "user-provided JSON schema. No prose, no markdown fences, no commentary."
        )
        user_prompt = (
            f"{prompt}\n\n"
            f"Return JSON conforming to this schema:\n```json\n{json.dumps(schema_json)}\n```\n"
        )

        last_error: str | None = None
        last_text: str | None = None
        attempt_prompt = user_prompt

        for _ in range(self.max_repair_attempts + 1):
            text = self._run(attempt_prompt, system_prompt=system)
            last_text = text
            text = _strip_json_fences(text)

            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                salvage = _extract_first_json_object(text)
                if salvage is not None:
                    try:
                        parsed = json.loads(salvage)
                    except json.JSONDecodeError:
                        last_error = f"could not parse JSON: {exc}"
                        attempt_prompt = self._repair_prompt(user_prompt, text, last_error)
                        continue
                else:
                    last_error = f"could not parse JSON: {exc}"
                    attempt_prompt = self._repair_prompt(user_prompt, text, last_error)
                    continue

            try:
                return schema.model_validate(parsed)
            except ValidationError as exc:
                last_error = f"schema validation failed: {exc}"
                attempt_prompt = self._repair_prompt(user_prompt, text, last_error)
                continue

        raise GenerationError(
            f"{self.name} failed to produce schema-valid output after "
            f"{self.max_repair_attempts + 1} attempts. Last error: {last_error}. "
            f"Last response (truncated): {(last_text or '')[:200]!r}"
        )

    @staticmethod
    def _repair_prompt(original: str, bad_response: str, error: str) -> str:
        return (
            f"{original}\n\n"
            f"Your previous response failed validation:\n{error}\n\n"
            f"Previous response (truncated):\n{bad_response[:2000]}\n\n"
            "Return ONLY a corrected JSON object that strictly conforms to the schema. "
            "No prose, no fences."
        )
