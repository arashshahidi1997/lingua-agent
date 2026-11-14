# Backlog

Concrete, near-term items. The phases themselves live in [roadmap.md](roadmap.md); the direction under review
is [product-v2.md](product-v2.md). Tick items in small hunks, committed by path, in the same commit as the
work. Unit in brackets (see `.projio/manager.yml`).

## Now

- [ ] Commit the Ollama work: `json_schema` output mode with step-down fallback, `OPENAI_TIMEOUT`, tests [core, tests]
- [ ] Decide on and commit the pixi setup (`pyproject.toml` pixi sections, `pixi.lock`, `.gitattributes`, `.gitignore` pixi lines) [config]
- [ ] Review the Product v2 proposal and answer its open questions (cloud vs local generation, Persian TTS, gamification, transliteration scheme, audience) [docs] — **user**
- [ ] Phase 5b for en → fa: language-aware prompts. Observed with `qwen2.5:7b` on an A1 lesson: grammar explained English tenses instead of Persian; summary and exercise instructions in Farsi though support was `en`; ungrammatical exercise sentences; gender tag on a Persian noun; vocab lemma instead of the text's form [core]

## Next (Product v2 order, if accepted)

- [ ] UI shell: Today / Path / Library / Talk + Settings + pair chip, on the existing API [web]
- [ ] Syllabus format (`syllabi/<lang>/<level>.yaml`) and the Farsi A1 syllabus [content, core]
- [ ] Path: generate-once-and-cache per step, step state per learner [core, web]
- [ ] Quiz engine: exercise types, Review folded in [core, web]
- [ ] TTS (Piper), audio on lessons and cards [core]

## Housekeeping

- [ ] mkdocs is not in `.venv`; docs build unchecked since `product-v2.md` and `exclude_docs: log/` were added [docs, config]
- [ ] Drive subset sync from the SSD (command in the memory note `session_state_2026-05-17.md`) — needs the SSD mounted — **user**
- [ ] Ollama on the XPS is CPU-only: ~6 min per lesson with `qwen2.5:7b`; disk at 95% [infra, not lingua] — **user**

## Done

- [x] 2026-11-14 Ollama wired up: Ollama upgraded to 0.40.16, `qwen2.5:7b` pulled, `.claude/launch.json` serves with Ollama
- [x] 2026-11-14 lingua-manager set up (d22fc85)
