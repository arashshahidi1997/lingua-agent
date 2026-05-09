# AI providers

`lingua-agent` ships **four** providers, all behind the same `AIProvider` Protocol so the rest of the code doesn't change when you switch.

| Provider | `LINGUA_AI_PROVIDER` | Use when… | Cost model |
|---|---|---|---|
| Mock | `mock` | Tests, no network, default | Free |
| OpenAI-compatible | `openai` | OpenAI / Gemma (Google AI Studio or Ollama) / Qwen (DashScope or Ollama) / OpenRouter / vLLM / llama.cpp / LM Studio | API tokens (or free if local) |
| **Anthropic API** | `anthropic` | Real Claude with **prompt caching** (~90% off cached tokens) | API tokens |
| **Claude Max** | `claude-max` | You have a **Claude Pro / Max subscription** and don't want to pay for API tokens | **Subscription quota** (no API billing) |

## Mock (default)
Deterministic, schema-valid output, no network call. The whole pipeline runs against it.

```bash
LINGUA_AI_PROVIDER=mock
```

## OpenAI-compatible — covers OpenAI, Gemma, Qwen, ...

| Backend | `OPENAI_BASE_URL` | `OPENAI_MODEL` | API key needed? |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | yes |
| Google AI Studio (Gemma) | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemma-3-27b-it` | yes |
| Ollama (local Gemma) | `http://localhost:11434/v1` | `gemma3:12b` | **no** |
| Ollama (local Qwen) | `http://localhost:11434/v1` | `qwen3:14b` | **no** |
| DashScope (Qwen cloud) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `qwen3-max` | yes |
| OpenRouter | `https://openrouter.ai/api/v1` | e.g. `google/gemma-3-27b-it` | yes |
| vLLM / llama.cpp / LM Studio | `http://localhost:<port>/v1` | (your model name) | usually no |

JSON-mode by default with transparent fallback when the backend rejects it. Schema-validation repair loop (default 2 retries). Fence stripping + first-`{...}`-block prose salvage. Backend errors are surfaced verbatim.

## Anthropic API — Claude with prompt caching

```bash
pip install -e ".[anthropic]"

LINGUA_AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6   # or claude-opus-4-7, claude-haiku-4-5
```

Implementation notes:
- **Prompt caching** — the system prompt (and any reusable context we pass as a system block) is marked `cache_control: {"type": "ephemeral"}`. After the first turn within ~5 minutes, cached input tokens are billed at ~10% of normal — material savings for chat-heavy tutor sessions where the system prompt + learner state easily reaches 2–4k tokens.
- **Structured output** uses **forced tool-use**: a tool whose `input_schema` is the target Pydantic schema, with `tool_choice={"type": "tool", "name": "..."}`. The model returns a `tool_use` block whose `input` is already the parsed schema. No JSON parsing of free text needed; rare validation failures fall back to a single repair attempt.
- Fallback to text-JSON parsing if the model somehow returns text instead of calling the tool.

You can disable caching with `AnthropicProvider(cache_system_prompt=False)` if you're seeing weird behaviour from the cache (e.g. testing prompt changes mid-session).

## Claude Max — use your Claude Pro/Max subscription, no API key

```bash
# 1. Install Claude Code (provides the `claude` CLI + OAuth)
npm install -g @anthropic-ai/claude-code
claude login

# 2. Install our optional extra
pip install -e ".[claude-max]"

# 3. Configure
LINGUA_AI_PROVIDER=claude-max
ANTHROPIC_MODEL=claude-sonnet-4-6   # picked up here too
```

This wraps **`claude-agent-sdk`**, which authenticates via the existing Claude Code CLI session. For Claude Pro / Max subscribers, programmatic calls are **billed against your subscription quota**, not against API token usage. Effective marginal cost: **zero** (within quota).

**Caveats**:
- The SDK shells out to the `claude` CLI under the hood — if `claude` isn't on `PATH`, instantiation raises a clear error pointing you at `npm install -g @anthropic-ai/claude-code` and `claude login`.
- Subscription quotas (~225 messages / 5h on Max 5x; ~900 / 5h on Max 20x) are real and not designed for high-throughput backend workloads.
- Best fit: **interactive tutor sessions and one-off ingest from the React PWA**.
- For ingesting many documents in batch, switch to `LINGUA_AI_PROVIDER=anthropic` (or `openai`) so you don't burn through your subscription quota in five minutes.
- Currently runs the SDK via `asyncio.run` per call — calling from inside an existing event loop raises a clear `GenerationError` pointing you at the API provider for async contexts.

## Picking a model for the four target languages

Rough quality estimates (your mileage will vary per task; this is the deciding factor for **Persian** especially).

| Backend / model | English | Italian | Russian | Persian | German | Dutch | Notes |
|---|---|---|---|---|---|---|---|
| `gpt-4o-mini` (OpenAI) | A | A | A− | B+ | A | A− | Solid all-rounder. |
| `gpt-4.1-mini` / `gpt-4o` | A | A | A | A− | A | A | Worth it for Persian. |
| **`claude-sonnet-4-6` (anthropic / claude-max)** | A | A | A | A | A | A | Strongest single recommendation across all six. Prompt caching tilts cost in your favour. |
| `claude-opus-4-7` | A+ | A | A | A | A | A | When you want max quality for a big lesson generation; otherwise Sonnet. |
| `gemma-3-27b-it` (Google AI Studio) | A | A− | B+ | B | A− | A− | Free tier, good Italian/German/Dutch. |
| `gemma3:12b` (Ollama local) | A− | B+ | B | B− | B+ | B+ | Best local default with 16GB+ VRAM. |
| `qwen3:14b` (Ollama local) | A− | B+ | B+ | B+ | B+ | B | Strongest open-weights for Persian. |
| `qwen3-max` (DashScope) | A | A | A | A− | A | A− | Cheapest "frontier-ish" for Persian. |

For **Persian** specifically: Sonnet 4.6, Opus 4.7, GPT-4o, Qwen3 Max, or Qwen3 ≥14B. Avoid the small Gemmas — they occasionally drop ZWNJ characters or transliterate when they shouldn't.

## When the repair loop matters
Big cloud models (GPT-4o, Claude Sonnet/Opus, Qwen3-Max, Gemma 3 27B) almost always emit valid JSON on the first try. Small local models (Gemma 3 4B, Qwen3 1.5B/4B) frequently need the second attempt. The provider treats both identically — only the latency cost changes.

## What's deferred
- **Streaming**: not needed for structured-generation; will be added when the tutor agent grows token-by-token output in the chat UI.
- **Embeddings** (for retrieval over previously-ingested material): planned but not in MVP.
- **Tool dispatch**: the chat method already returns `tool_calls`; wiring those into the tutor agent loop is Phase 6.
