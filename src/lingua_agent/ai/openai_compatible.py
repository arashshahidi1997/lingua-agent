"""OpenAI-compatible AI provider.

One implementation, many backends: any service that exposes
`POST /v1/chat/completions` with the OpenAI request/response shape works
behind this provider. Tested mental model:

    backend                         OPENAI_BASE_URL                                                  OPENAI_MODEL
    ------------------------------  --------------------------------------------------------------   --------------------------
    OpenAI                          https://api.openai.com/v1                                         gpt-4o-mini
    Google AI Studio (Gemma)        https://generativelanguage.googleapis.com/v1beta/openai          gemma-3-27b-it
    Ollama (local Gemma)            http://localhost:11434/v1                                         gemma3:12b
    Ollama (local Qwen)             http://localhost:11434/v1                                         qwen3:14b
    DashScope (Qwen cloud)          https://dashscope-intl.aliyuncs.com/compatible-mode/v1            qwen3-max
    OpenRouter                      https://openrouter.ai/api/v1                                      google/gemma-3-27b-it
    vLLM / llama.cpp / LM Studio    http://localhost:<port>/v1                                        <model name>

Local-only Ollama runs without an API key; if `OPENAI_API_KEY` is unset
**and** the base URL is localhost, we don't require it.

Two real-world adjustments for small open-weights models:

1. JSON mode — we send `response_format={"type": "json_object"}` by default.
   On a 400/422 from a backend that doesn't support it (older Ollama
   builds, certain models), we fall back to a plain prompt + JSON-parse.

2. Schema-validation repair loop — small models (Gemma/Qwen at the smaller
   sizes) sometimes emit nearly-valid JSON. On a Pydantic ValidationError
   we re-prompt with the exact validation error and the schema, up to
   `max_repair_attempts` times. Default 2 (so 3 total attempts).
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import Settings
from .base import ChatMessage, ChatResponse, GenerationError

T = TypeVar("T", bound=BaseModel)


_DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
_FENCED_JSON_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_FIRST_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_json_fences(text: str) -> str:
    m = _FENCED_JSON_RE.match(text)
    if m:
        return m.group(1)
    return text


def _extract_first_json_object(text: str) -> str | None:
    """Last-resort: pull the first balanced-looking {...} block from prose."""
    m = _FIRST_JSON_OBJECT_RE.search(text)
    return m.group(0) if m else None


def _is_local_url(url: str) -> bool:
    return any(host in url for host in ("://localhost", "://127.0.0.1", "://0.0.0.0", "://[::1]"))


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
        json_mode: bool = True,
        max_repair_attempts: int = 2,
    ):
        self.settings = settings or Settings.load()
        self.json_mode = json_mode
        self.max_repair_attempts = max(0, max_repair_attempts)

        # Local Ollama / llama.cpp servers don't require auth; only require
        # the key when talking to a remote endpoint.
        if not self.settings.openai_api_key and not _is_local_url(self.settings.openai_base_url):
            raise GenerationError(
                "OPENAI_API_KEY is not set. Set it for cloud providers, or point "
                "OPENAI_BASE_URL at a local endpoint (http://localhost:11434/v1 for Ollama)."
            )

        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=_DEFAULT_TIMEOUT)

    def __del__(self):  # pragma: no cover - best-effort cleanup
        if getattr(self, "_owns_client", False):
            try:
                self._client.close()
            except Exception:
                pass

    # -- transport helpers --------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.settings.openai_api_key:
            h["Authorization"] = f"Bearer {self.settings.openai_api_key}"
        return h

    def _endpoint(self) -> str:
        base = self.settings.openai_base_url.rstrip("/")
        return f"{base}/chat/completions"

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(self._endpoint(), headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise GenerationError(f"HTTP error talking to {self._endpoint()}: {exc}") from exc
        if response.status_code >= 400:
            # Surface the backend's error body — invaluable for debugging
            # model-name typos against Ollama / DashScope.
            raise GenerationError(
                f"{self.name} backend returned {response.status_code}: {response.text[:500]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise GenerationError(f"non-JSON response from {self._endpoint()}: {response.text[:200]}") from exc

    # -- public API ---------------------------------------------------------

    def chat(self, messages: list[ChatMessage], *, tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
        }
        if tools:
            payload["tools"] = tools
        body = self._post(payload)
        choice = body["choices"][0]
        msg = choice.get("message", {})
        return ChatResponse(
            content=msg.get("content") or "",
            tool_calls=msg.get("tool_calls") or [],
            raw=body,
        )

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

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]

        json_mode = self.json_mode
        last_error: str | None = None
        last_text: str | None = None

        for attempt in range(self.max_repair_attempts + 1):
            payload: dict[str, Any] = {
                "model": self.settings.openai_model,
                "messages": messages,
                "temperature": 0,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            try:
                body = self._post(payload)
            except GenerationError as exc:
                # If json_mode is rejected by the backend, fall back to plain text
                # mode and retry the same attempt without consuming a repair budget.
                msg = str(exc)
                if json_mode and ("response_format" in msg or " 400" in msg or " 422" in msg):
                    json_mode = False
                    continue
                raise

            text = (body.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            last_text = text
            text = _strip_json_fences(text)

            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                # Final salvage: try to locate the first {...} block in prose.
                salvage = _extract_first_json_object(text)
                if salvage is not None:
                    try:
                        parsed = json.loads(salvage)
                    except json.JSONDecodeError:
                        last_error = f"could not parse JSON: {exc}"
                        messages = self._repair_messages(system, user_prompt, text, last_error)
                        continue
                else:
                    last_error = f"could not parse JSON: {exc}"
                    messages = self._repair_messages(system, user_prompt, text, last_error)
                    continue

            try:
                return schema.model_validate(parsed)
            except ValidationError as exc:
                last_error = f"schema validation failed: {exc}"
                messages = self._repair_messages(system, user_prompt, text, last_error)
                continue

        raise GenerationError(
            f"{self.name} failed to produce schema-valid output after "
            f"{self.max_repair_attempts + 1} attempts. Last error: {last_error}. "
            f"Last response (truncated): {(last_text or '')[:200]!r}"
        )

    # -- repair loop --------------------------------------------------------

    @staticmethod
    def _repair_messages(system: str, user_prompt: str, bad_response: str, error: str) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": bad_response[:4000]},
            {
                "role": "user",
                "content": (
                    f"Your previous response failed validation:\n{error}\n\n"
                    "Return ONLY a corrected JSON object that strictly conforms to the schema. "
                    "No prose, no fences."
                ),
            },
        ]
