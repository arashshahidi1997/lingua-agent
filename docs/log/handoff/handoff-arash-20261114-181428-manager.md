---
title: "lingua-manager: first handoff (setup session)"
date: 2026-11-14
timestamp: 20261114-181428
tags: [handoff]
series: manager
branch: "claude/code-review-bhyt1c"
status: consumed
git_commit: "d22fc85"
refs: [docs/backlog.md, docs/product-v2.md, docs/roadmap.md]
---

# lingua-manager: first handoff (setup session)

**How to resume (one paste):** title this session `lingua-manager`, load the `lingua-manager` skill, read this
file, run a round.

**Restart needed (new MCP tools)?** no

## What shipped this session
- Manager files: core (projio 1ee6fe5), adapter skill, `.projio/manager.yml` (d22fc85).
- Ollama wired up end to end: Ollama 0.40.16, `qwen2.5:7b`; a Farsi A1 lesson generates in ~6 min on CPU.

## Uncommitted / in flight
- core/tests: `openai_compatible.py` sends `response_format` `json_schema` first, steps down to `json_object`,
  then plain; new `OPENAI_TIMEOUT` in `config.py`; tests updated (117 pass, ruff clean).
- docs: `docs/product-v2.md` (draft proposal), `docs/backlog.md` (new), note atop `docs/roadmap.md`,
  `mkdocs.yml` nav + `exclude_docs: log/`.
- config: `.claude/launch.json` (serve with Ollama, timeout 900); adapter now reads `docs/backlog.md`.
- The user's own: pixi sections in `pyproject.toml`, `pixi.lock`, `.gitattributes`, pixi lines in
  `.gitignore`. Not to be committed without the user saying so.

## What's parked / broken
- Lesson quality with `qwen2.5:7b` is poor for en → fa (see backlog "Phase 5b for en → fa").
- mkdocs not installed in `.venv`; docs build unchecked.

## New tooling / capabilities
- `OPENAI_TIMEOUT` env var; schema-constrained output with Ollama ≥ 0.5.

## Decisions the user made (don't re-ask)
- Manager files on branch `claude/code-review-bhyt1c`.
- Local model: `qwen2.5:7b` on Ollama (over 4B models or another machine). Ollama upgraded by the user.
- Product v2 proposal written to docs as a draft; specs are not fixed.

## Prioritized next steps
1. Ask the user to commit the in-flight work (which branch, and whether the pixi files go in).
2. Ask the open questions in `docs/product-v2.md` (cloud vs local generation first: it decides 5b's scope).
3. Start kickoffs 1–2 from the board; 3–4 once the proposal is accepted.

## Kickoff prompt (paste into the next session)
> Title this session `lingua-manager`. Load the `lingua-manager` skill, read handoff
> `docs/log/handoff/handoff-arash-20261114-181428-manager.md`, and run a round.
