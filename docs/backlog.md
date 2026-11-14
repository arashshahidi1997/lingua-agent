# Backlog

Concrete, near-term items. The phases themselves live in [roadmap.md](roadmap.md); the direction under review
is [product-v2.md](product-v2.md). Tick items in small hunks, committed by path, in the same commit as the
work. Unit in brackets (see `.projio/manager.yml`).

## Now

- [ ] Review the Product v2 proposal and answer its open questions (cloud vs local generation, Persian TTS, gamification, transliteration scheme, audience) [docs] — **user**
- [ ] Phase 5b for en → fa: language-aware prompts. Observed with `qwen2.5:7b` on an A1 lesson: grammar explained English tenses instead of Persian; summary and exercise instructions in Farsi though support was `en`; ungrammatical exercise sentences; gender tag on a Persian noun; vocab lemma instead of the text's form [core]

## Next

- [ ] Native-speaker review of the Farsi A1 course (`src/lingua_agent/course/data/fa-en-a1.yaml`): transliteration of ع, time phrases, the u6 café bill, words used before they're taught (list in the 2026-11-14 handoff) [content] — **user**
- [ ] Try Talk with Ollama `qwen2.5:7b`: turn latency and whether it follows the `TalkTurn` schema; tune `course/talk.py` prompts [core]
- [ ] UI for importing audio from a materials source (`POST /api/audio/from-materials` exists) [web]
- [ ] Daily goal and streak setting stored server-side (today per browser) [core, web]
- [ ] Generated courses: "generate the next unit" with an LLM, cached once, for pairs without a hand-written course [core]
- [ ] A2 course for Farsi; courses for other pairs [content]
- [ ] Install faster-whisper (`.[voice]`) and try transcribing imported audio [config] — **user**

## Housekeeping

- [ ] mkdocs is not in `.venv`; docs build unchecked since `product-v2.md` and `exclude_docs: log/` were added [docs, config]
- [ ] Drive subset sync from the SSD (command in the memory note `session_state_2026-05-17.md`) — needs the SSD mounted — **user**
- [ ] Ollama on the XPS is CPU-only: ~6 min per lesson with `qwen2.5:7b`; disk at 95% [infra, not lingua] — **user**

## Done

- [x] 2026-11-14 Product v2 first pass: Today / Path / Library / Talk + Settings redesign; Farsi A1 course (8 units, 31 lessons, 8 stories, 8 role-plays); exercise engine (choose, listen, match, order, type); practice and checkpoint quizzes with test-out; stories with play-all and shadowing; recordings and speaking diary; imported audio with synced `.srt`/`.vtt`; Talk with corrections and summary cards; Piper TTS with the `fa_IR-amir-medium` voice
- [x] 2026-11-14 Ollama work committed (`json_schema` output, `OPENAI_TIMEOUT`); pixi setup committed; branch merged into `main`

- [x] 2026-11-14 Ollama wired up: Ollama upgraded to 0.40.16, `qwen2.5:7b` pulled, `.claude/launch.json` serves with Ollama
- [x] 2026-11-14 lingua-manager set up (d22fc85)
