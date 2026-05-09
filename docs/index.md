# lingua-agent

Agentic AI language-learning platform. Local-first. Open-source. **Any language A → any language B.**

> Status: alpha (MVP). The pipeline runs end-to-end against a deterministic mock provider, and `OpenAICompatibleProvider` connects you to OpenAI, Google AI Studio (Gemma), Ollama (Gemma / Qwen / anything), DashScope, OpenRouter, vLLM, llama.cpp, or LM Studio with one set of env vars.

## Mission

`lingua-agent` is **not** a Duolingo clone with a chat box. It is:

1. **Custom material in.** Paste an article, drop a markdown file, point at a transcript.
2. **Structured learning objects out.** Bilingual reading, vocabulary with provenance, grammar notes, exercises, SRS flashcards, lesson units.
3. **A tutor agent that can actually do things.** Typed tools, every call logged, every mutation auditable.
4. **Bidirectional language pairs.** English ↔ Italian, English ↔ Persian, English ↔ Russian, Italian ↔ Persian, Russian ↔ Persian, Italian ↔ Russian — no language is privileged as "the source".

## Initially supported languages

| Code | Name | Script | Direction |
|---|---|---|---|
| `en` | English | Latin | ltr |
| `it` | Italian | Latin | ltr |
| `ru` | Russian | Cyrillic | ltr |
| `fa` | Persian (Farsi) | Perso-Arabic | **rtl** |

Persian is a first-class citizen. Lesson exports wrap Persian blocks in `dir="rtl"` so they render correctly. Transliteration is an opt-in scaffold, never a substitute for the original script.

## Quickstart

```bash
git clone https://github.com/arashshahidi1997/lingua-agent.git
cd lingua-agent
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/lingua-agent init
.venv/bin/lingua-agent ingest text \
  --source en --target it --support en --level A1 \
  --title "Coffee conversation" \
  --text "I would like a coffee and a glass of water. Where is the train station?"
.venv/bin/lingua-agent review due --target it
```

The default AI provider is `mock` — full pipeline, no network. Switch to a real backend (OpenAI / Gemma / Qwen / …) by setting two env vars: see [AI providers](providers.md).

## Read next

- [Architecture](architecture.md) — the abstractions and the data flow.
- [Content schema](content-schema.md) — every Pydantic model, field by field.
- [Language pairs](language-pair-design.md) — per-pair concerns, RTL policy, transliteration policy.
- [AI providers](providers.md) — backend recipes for OpenAI, Gemma, Qwen, etc.
- [Tutor agent](agent-design.md) — typed tools and grading.
- [Clients (desktop & mobile)](clients.md) — Tauri 2 + Flutter plan.
- [Roadmap](roadmap.md) — what's MVP, what's next.
- [Decisions](decisions.md) — design decisions and reversals.
- [References](references.md) — surveyed OSS projects.

## License

MIT.
