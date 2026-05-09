# AI providers

`lingua-agent` ships **one** real provider class — `OpenAICompatibleProvider` — that targets any backend speaking the OpenAI `/v1/chat/completions` shape. That covers OpenAI itself plus every major open-weights serving stack and every relevant cloud, including **Gemma** (via Google AI Studio or Ollama) and **Qwen** (via DashScope or Ollama).

The only other provider is `MockProvider`, which produces deterministic, schema-valid output without a network call. It's the default and what the test suite runs against.

## Quick recipe table

| Backend | `LINGUA_AI_PROVIDER` | `OPENAI_BASE_URL` | `OPENAI_MODEL` | API key needed? |
|---|---|---|---|---|
| OpenAI | `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` (or any) | yes |
| Google AI Studio (Gemma) | `openai` | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemma-3-27b-it` | yes |
| Ollama local (Gemma) | `openai` | `http://localhost:11434/v1` | `gemma3:12b` | **no** |
| Ollama local (Qwen) | `openai` | `http://localhost:11434/v1` | `qwen3:14b` | **no** |
| DashScope (Qwen cloud) | `openai` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `qwen3-max` | yes |
| OpenRouter | `openai` | `https://openrouter.ai/api/v1` | e.g. `google/gemma-3-27b-it` | yes |
| vLLM / llama.cpp / LM Studio | `openai` | `http://localhost:<port>/v1` | (your model name) | usually no |

`OPENAI_API_KEY` is **not required** when `OPENAI_BASE_URL` points at localhost (so your local Ollama runs without a placeholder key).

## How the provider behaves

1. **JSON mode by default.** Calls go out with `response_format={"type":"json_object"}`. If the backend returns 400/422 indicating it doesn't support that field, the provider transparently retries the same attempt without the field — no repair budget consumed.

2. **Schema-validation repair loop.** Pipelines call `generate_structured(prompt, schema)`. The provider asks for valid JSON, parses it, validates against the Pydantic schema. On failure (parse error or Pydantic `ValidationError`), it re-prompts the model with the exact error and asks for a corrected JSON object. Default budget: 2 repairs (3 attempts total). Tunable via the `max_repair_attempts` constructor argument.

3. **JSON-fence stripping and prose salvage.** Many open-weights models wrap output in ` ```json … ``` ` despite instructions; we strip that. As a last resort we extract the first `{…}` block from prose before giving up.

4. **Backend errors are surfaced.** Non-2xx responses include the body (truncated to 500 chars), so you can tell a model-name typo against Ollama from a missing API key against DashScope at a glance.

5. **Timeouts default to 120s.** Cloud chat completions for long prompts can take a while; this is roomy without being silly.

## Picking a model for the four target languages

This is rough and based on community evals + our own structure tests. The pipeline will work with any model that can reliably emit JSON; the *quality* of the language content is what varies.

| Backend / model | English | Italian | Russian | Persian | Notes |
|---|---|---|---|---|---|
| `gpt-4o-mini` (OpenAI) | A | A | A− | B+ | Strong all-rounder. Persian script handling solid. |
| `gpt-4.1-mini` / `gpt-4o` | A | A | A | A− | Worth it for Persian. |
| `gemma-3-27b-it` (Google AI Studio) | A | A− | B+ | B | Good free-tier story. |
| `gemma3:12b` (Ollama local) | A− | B+ | B | B− | Best local default if you have 16GB+ VRAM. |
| `gemma3:4b` (Ollama local) | B+ | B | C+ | C | Use only with the repair loop set to ≥2. |
| `qwen3:14b` (Ollama local) | A− | B+ | B+ | B+ | Strongest open-weights for Persian we've tried. |
| `qwen3-max` (DashScope) | A | A | A | A− | Cheapest "frontier-ish" for Persian. |

If you're targeting **Persian**, prefer Qwen 3 ≥ 14B or GPT-4o (full) over the smaller Gemmas — small Gemmas occasionally drop ZWNJ characters or transliterate when they shouldn't.

## When the repair loop matters

Big cloud models (GPT-4o, Claude, Qwen3-Max, Gemma 3 27B) almost always emit valid JSON on the first try. Small local models (Gemma 3 4B, Qwen3 1.5B/4B) frequently need the second attempt. The provider treats both identically — the only thing that changes is the latency cost.

If you're chasing throughput on cloud models, you can set `max_repair_attempts=0`. If you're running tiny local models, bump to 3 or 4.

## What's deferred

- **Anthropic native API** (`/v1/messages` with content blocks): the stub in `ai/anthropic_provider.py` raises with a hint to use OpenRouter instead in the meantime.
- **Tool use / function calling** dispatched by the provider: the chat method already returns `tool_calls`; wiring them into the tutor agent loop is Phase 6.
- **Streaming**: not needed for the structured-generation path; will be added when the tutor agent grows interactive output.
- **Embeddings** (for retrieval over previously-ingested material): planned but not in MVP.
