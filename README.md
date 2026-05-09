# lingua-agent

Agentic AI language-learning platform. Local-first. Open-source. _Any language A → any language B._

> Status: alpha (MVP). Pipeline runs end-to-end against a deterministic mock AI provider; real providers (OpenAI-compatible, Anthropic) are an optional install extra.

## Mission

`lingua-agent` is **not** a Duolingo clone with a chat box. It is:

1. **Custom material in.** Paste an article, drop a markdown file, point at a transcript.
2. **Structured learning objects out.** Bilingual reading, vocabulary with provenance, grammar notes, exercises, SRS flashcards, lesson units.
3. **A tutor agent that can actually do things.** Typed tools (`generate_exercise`, `grade_attempt`, `add_flashcard`, `update_mastery`, `switch_language_pair`, …), every call logged, every mutation auditable.
4. **Bidirectional language pairs.** English ↔ Italian, English ↔ Persian, English ↔ Russian, Italian ↔ Persian, Russian ↔ Persian, Italian ↔ Russian. The architecture does not privilege English.

## Why "any language A → B"?

Most OSS language-learning projects assume English is the source. `lingua-agent` does not. Every entity that has a language carries `source_language`, `target_language`, and an optional `support_language`. The CLI requires `--source` and `--target` explicitly.

## Initially supported languages

| Code | Name | Script | Direction |
|---|---|---|---|
| `en` | English | Latin | ltr |
| `it` | Italian | Latin | ltr |
| `ru` | Russian | Cyrillic | ltr |
| `fa` | Persian (Farsi) | Perso-Arabic | **rtl** |

Persian is a first-class citizen. Lesson exports wrap Persian blocks in `dir="rtl"` so they render correctly. Transliteration is an opt-in scaffold, never a substitute for the original script.

## Install

```bash
pip install -e ".[dev]"
# Optional providers:
pip install -e ".[openai]"
pip install -e ".[anthropic]"
```

Python 3.11+.

## Quickstart

```bash
# 1. Initialise data directory + default learner profile
lingua-agent init

# 2. List supported languages
lingua-agent languages list

# 3. Ingest some text → generates a lesson unit, vocab, exercises, and SRS cards
lingua-agent ingest text \
  --source en --target it --support en \
  --level A1 \
  --title "Coffee conversation" \
  --text "I would like a coffee and a glass of water. Where is the train station?"

# 4. View the generated lesson
lingua-agent unit list
ls content/units/

# 5. Review due cards
lingua-agent review due --target it

# 6. Grade a card
lingua-agent review answer --card-id <id> --quality 4

# 7. Export to Anki-compatible CSV
lingua-agent export anki --target it --output content/exports/italian.csv

# 8. Tutor chat (mock provider — deterministic responses for now)
lingua-agent tutor chat --source en --target it
```

## AI providers

The default provider is `mock`: it produces deterministic, schema-valid output without any network calls. Tests run against it. The ingest pipeline runs end-to-end against it.

For real content there is **one** real provider — `OpenAICompatibleProvider` — that targets any backend speaking the OpenAI `/v1/chat/completions` shape. That covers **OpenAI**, **Gemma** (via Google AI Studio or Ollama), **Qwen** (via DashScope or Ollama), plus OpenRouter, vLLM, llama.cpp, and LM Studio. Switch by setting `OPENAI_BASE_URL` and `OPENAI_MODEL`:

```bash
# OpenAI
LINGUA_AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Local Gemma via Ollama (no API key needed for localhost)
LINGUA_AI_PROVIDER=openai
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=gemma3:12b

# Local Qwen via Ollama
LINGUA_AI_PROVIDER=openai
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=qwen3:14b
```

The provider includes JSON-mode + a schema-validation repair loop so small open-weights models (Gemma 3 4B, Qwen3 1.5B) still produce valid pipeline output. Full backend list and per-language model recommendations: [`docs/providers.md`](docs/providers.md).

## Custom material workflow

1. Drop a `.md` or `.txt` file into `content/inbox/`.
2. Run `lingua-agent ingest file --source <code> --target <code> content/inbox/<file>`.
3. The pipeline normalizes text, segments it, generates bilingual reading + vocabulary + grammar + exercises + flashcards, and writes a lesson at `content/units/<id>.md`.
4. Cards land in the SRS queue; review with `lingua-agent review due --target <code>`.

PDF and EPUB ingestion are Phase 7.

## Architecture overview

See [docs/architecture.md](docs/architecture.md). In one paragraph: a CLI (Typer) drives an ingest pipeline, a tutor agent, and an SRS scheduler. All three call into typed Pydantic models persisted via a `Repository` Protocol (JSON-on-disk today, SQLite later). AI access is hidden behind an `AIProvider` Protocol whose default impl is the deterministic mock used by tests. The tutor exposes a typed tool surface and logs every call.

Other docs:
- [`docs/decisions.md`](docs/decisions.md) — design decisions and reversals.
- [`docs/references.md`](docs/references.md) — surveyed OSS projects and what we borrow.
- [`docs/language-pair-design.md`](docs/language-pair-design.md) — per-pair concerns and RTL/transliteration policy.
- [`docs/content-schema.md`](docs/content-schema.md) — entity reference.
- [`docs/agent-design.md`](docs/agent-design.md) — tutor tools and grading.
- [`docs/roadmap.md`](docs/roadmap.md) — what's MVP, what's next.

## Limitations

- Mock provider only in MVP for the actual content generation. The pipeline runs and produces valid artifacts, but the *content* is templated, not authored. Plug in a real provider for real content.
- No PDF/EPUB/audio ingestion yet.
- No frontend — CLI only.
- No voice mode.
- Single-user (one default `LearnerProfile`).
- Persian formal vs colloquial register is declared at lesson level, not learned automatically.

## Contributing

This is a personal learning project under active solo development. PRs welcome but expect rapid scope changes. License: MIT.
