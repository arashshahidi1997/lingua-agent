# lingua-agent

Agentic AI language-learning platform. Local-first. Open-source. _Any language A → any language B._

> Status: in daily use on two phones. A web app (Today · Path · Library · Talk) with a hand-written Farsi A1
> course, served from a laptop over Tailscale; owner and guest each have their own progress. Work in progress
> is tracked in [`docs/backlog.md`](docs/backlog.md); the latest review in [`docs/audit/`](docs/audit/).

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

## What's in the app

The web app (`lingua-agent serve --build`) has four tabs:

- **Today** — continue your course, review due cards, a quick quiz, a story, and a conversation to try.
- **Path** — a structured course, unit by unit: lessons as Duolingo-style exercises (choose, listen, match,
  word order, type the transliteration), a story and a role-play per unit, and a checkpoint quiz that also
  lets you test out. The first course is **Farsi A1 for English speakers** (8 units, hand-written, with
  transliteration throughout: `src/lingua_agent/course/data/fa-en-a1.yaml`).
- **Library** — stories and dialogues to read and listen to (play all, per line, and shadowing: record yourself
  right after the model line), your own recordings and speaking diary, imported audio with synced `.srt`/`.vtt`
  transcripts, and lessons generated from your own texts.
- **Talk** — role-play the unit's scenario (or talk freely) with the AI, by text or voice, with gentle
  corrections and a summary at the end that turns mistakes and new words into flashcards.

Settings hold the language pair, script display (Persian script / transliteration / both), speech, daily goal,
and the AI provider. The direction and its open questions are in [`docs/product-v2.md`](docs/product-v2.md).

### Speech

Audio comes from a local [Piper](https://github.com/rhasspy/piper) voice when one is installed, else from the
browser's voices (most devices have none for Persian):

```bash
pip install -e ".[voice]"            # piper-tts (+ faster-whisper for transcribing your audio)
lingua-agent voices download fa      # ~63 MB, from rhasspy/piper-voices
lingua-agent voices list
```

## Install

```bash
pip install -e ".[dev]"
# Optional providers:
pip install -e ".[openai]"
pip install -e ".[anthropic]"
```

Python 3.11+.

## Try it without typing CLI commands

```bash
pip install -e ".[playground]"
lingua-agent playground   # → http://localhost:8501
```

A Streamlit UI on the v1 core (ingest, lessons, review, the terminal-era tutor). **A developer tool, not the
learner interface** — that's the web app above. See [`docs/playground.md`](docs/playground.md).

## Use it on your phone (Android PWA)

The React front end is an installable **PWA** — no app store, no native build.
One command compiles it and serves both the API and the UI from a single origin:

```bash
pip install -e ".[api]"                 # one-time: installs uvicorn + FastAPI
lingua-agent serve --build --host 0.0.0.0   # build the PWA, then serve on your LAN
```

`--build` runs `npm install` (first time) + `npm run build` into `web/dist`, so
you need Node.js ≥ 18 on the machine. Then, from your phone on the same Wi-Fi:

1. **Browse it now** — open `http://<your-computer-ip>:8000` in Android Chrome.
   Reading, ingest, review, and tutor all work over plain HTTP.
2. **Install to Home Screen** — this needs **HTTPS** (Android won't register a
   service worker over `http://192.168.x.x`). The fastest path is a tunnel:

   ```bash
   # in a second terminal, with the server already running
   cloudflared tunnel --url http://localhost:8000   # or: ngrok http 8000
   ```

   Open the printed `https://…` URL on the phone → Chrome menu → **Install app**.
   You'll get a home-screen icon, a standalone window, and offline SRS review
   (the service worker caches `/api/*` network-first).

For a stable LAN cert (`mkcert`) or an off-Wi-Fi setup (`tailscale serve`), see
[`docs/mobile-https.md`](docs/mobile-https.md). Everything is **self-hosted** —
your lessons and API keys live on your machine, not a third-party server.

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

# 8. Tutor chat in the terminal (developer tool; learners use Talk in the web app)
lingua-agent tutor chat --source en --target it
```

## AI providers

Four providers, all behind the same Protocol — switch with one env var:

| Provider | When | Cost |
|---|---|---|
| `mock` (default) | Tests, no network | Free |
| `openai` | OpenAI / Gemma / Qwen / Ollama / OpenRouter / vLLM / llama.cpp / LM Studio | API or free local |
| `anthropic` | Claude API with **prompt caching** (~90% off cached tokens) | API |
| **`claude-max`** | You have a **Claude Pro/Max subscription** — **no API key needed** | Subscription quota |

For example, OpenAI-compatible (covers Gemma, Qwen, Ollama, ...):

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

For Anthropic with prompt caching:
```bash
pip install -e ".[anthropic]"
LINGUA_AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

For Claude Max users (no API key — uses your subscription):
```bash
npm install -g @anthropic-ai/claude-code && claude login
pip install -e ".[claude-max]"
LINGUA_AI_PROVIDER=claude-max
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Full backend list, per-language model recommendations, and prompt-caching details: [`docs/providers.md`](docs/providers.md).

## Custom material workflow

1. Drop a `.md` or `.txt` file into `content/inbox/`.
2. Run `lingua-agent ingest file --source <code> --target <code> content/inbox/<file>`.
3. The pipeline normalizes text, segments it, generates bilingual reading + vocabulary + grammar + exercises + flashcards, and writes a lesson at `content/units/<id>.md`.
4. Cards land in the SRS queue; review with `lingua-agent review due --target <code>`.

PDF and EPUB ingestion are Phase 7.

## Architecture overview

See [docs/architecture.md](docs/architecture.md). In one paragraph: a FastAPI server serves the React PWA and
the API; courses are hand-written YAML turned into generated exercises, with per-learner progress, SM-2
flashcards, stories, Talk role-plays and Piper speech; owner and guests are told apart by the Tailscale login.
Everything is typed Pydantic, stored as JSON on disk, and AI access goes through an `AIProvider` protocol
(mock for tests; OpenAI-compatible incl. Ollama; Anthropic; Claude Max). The CLI and playground are developer
tools on the same core.

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
