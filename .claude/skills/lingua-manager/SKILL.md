---
name: lingua-manager
description: >
  lingua-agent's manager: the standing session that oversees Arash's parallel sessions developing the
  lingua-agent app (the Python core, the React PWA and its Android install, lesson content, docs, tests).
  The adapter for the project-manager core. One round finds the open lingua sessions, reads the repo's
  handoffs, commits and uncommitted paths by unit, checks docs/roadmap.md, and rewrites one board; then it
  asks the user the decisions waiting and messages persolog-manager only for decide / needs / blocked.
  Use when the user opens the standing `lingua-manager` session, or asks "what's running in lingua",
  "what's on the lingua board", "plan the next lingua sessions". Loads the core first.
metadata:
  short-description: lingua-agent adapter for the project-manager core; manager of parallel app sessions
  tags: [manager, orchestration, adapter, lingua-agent]
---

# lingua-manager: the adapter

**Load the core first:** `.claude/skills/project-manager/SKILL.md`, a read-only copy of projio's
`src/projio/data/skills/project-manager/` (SKILL.md, round.py, _common.py, incoming.py, procs.py; version
projio 1ee6fe5, copied 2026-11-14 from `~/Documents/infra/.claude/skills/project-manager/`). Never edit it
here; recopy after each projio push. lingua-specific behaviour goes in this file. Machine keys are in
`.projio/manager.yml`. Read `README.md` and `docs/roadmap.md` before the first round.

Runs on the **laptop (XPS)**, cwd `~/dev/learn/lingua-agent`. Projio MCP tools are usually not connected
here: read and write notes as files.

## Names

- Standing manager: `lingua-manager` (exact title, no date); a session that sets up or changes the manager
  itself: `lingua-manager-setup`.
- Work sessions: `lingua-<unit> · <item>` (units in `.projio/manager.yml`: core, web, content, tools, docs,
  tests, notes, config). A session that writes several units takes the main one, e.g.
  `lingua-core · Phase 6 tutor agent`, `lingua-web · UI redesign`. Find them in `list_sessions` by title
  prefix `lingua-` and `cwd` `~/dev/learn/lingua-agent`.
- Above it: `persolog-manager` (session id `local_d1d7fac3-f345-4985-89de-e2379bf20c6a`, laptop).

## At start

1. Own id: `get_session("self")` → `sessionId`; put it under Sync on the board.
2. If a `series: manager` handoff is open in `docs/log/handoff/`, read it (Decisions the user made: don't
   re-ask).
3. Run a round.

## Board

`board.path` in `.projio/manager.yml` (`.scratch/lingua-manager-board.md`, gitignored). The layout is the
core's (SKILL.md "Board": What's up with its `As of` stamp, Delegate with **independent** /
**depends on <what>** tags, Decisions, Sessions, Waiting on others, Sync; `round.py board` stamps and
refreshes it). Open it with `show_pane(pane="file", path=".scratch/lingua-manager-board.md")`. lingua adds
two sections, which `round.py board` keeps in place:

```markdown
## Waiting on you
<installs needing sudo (Ollama upgrades), model downloads on a near-full disk, API keys, SSD plugged in,
 phone testing of the PWA>

## Phases
| Phase | Open session | State | Last activity | Next |
```

## Units of work and where their state lives

The units of work are the phases in `docs/roadmap.md` (✅ marks shipped ones), plus bugs and the PWA /
Android client. Their state lives in `docs/roadmap.md`, the commits, and `docs/log/handoff/`.

| Work | Typical unit(s) | Notes |
|---|---|---|
| Roadmap phase (5b, 6, 6b, 6d, 6e, 7, 9, 10, …) | core, tests, docs | A phase that ships ticks itself ✅ in `docs/roadmap.md` in the same commit. |
| UI and PWA / Android | web | `lingua-agent serve --build`; `docs/mobile-https.md` for phone testing. |
| Lessons and examples | content | `examples/lessons/` is hand-curated; `content/units`, `content/cards`, `content/exports` are gitignored output. |
| AI providers (Ollama, Anthropic, Claude Max) | core | Config is env vars (`docs/providers.md`); no secrets in the repo. |
| Materials adapter (SSD, Drive) | core, tools | Publisher-licensed materials never enter the repo or tests. |
| Bugs | the unit of the fix | |

## What belongs to the sessions

Every file a work session writes: `src/`, `web/`, `tests/`, `content/`, `examples/`, `tools/`, `docs/`
(except `docs/log/`), `pyproject.toml`, `pixi.lock`, and the sessions' handoffs. The manager suggests edits on
the board or in a kickoff; the session (or the user) makes them. Its own writes: the board, its own manager
handoff, this adapter and `.projio/manager.yml` (with the user), committing a `docs/log/inbox/` note the user
approved, a note's status once handled, and `→ manager` items a session hands over.

## Collision unit

The top-level directory, as the units in `.projio/manager.yml` map it (`docs/log/` is `notes`, the rest of
`docs/` is `docs`). `docs/roadmap.md` is touched by most phase sessions: two sessions may tick items in it,
but only with small hunks committed by path; flag it when both have it dirty. `pyproject.toml` and
`pixi.lock` likewise (dependency changes): one session at a time.

## Integration

Before a session commits: the pixi env (`pixi run` or `.venv/bin/`), the test suite
(`python -m pytest -q`) and `ruff check src tests` pass; `npm --prefix web run build` when `web/` changed.
Branch `main`, remote GitHub `origin` (HTTPS with `gh auth git-credential`; see memory note
`git_push_via_gh.md`). Push, merge, and open PRs only when the user asks.

## The user

- Installs needing sudo (Ollama upgrade, system packages), model downloads (the XPS disk is near full),
  API keys and sign-ins are the user's: list them under "Waiting on you" as commands.
- The external SSD (Transcend) is mounted only sometimes; sessions that need it say so in the kickoff.

## Kickoffs

The core's form (title line first, tag on the board). lingua adds: the roadmap phase or bug; handoffs by
path, never "the latest"; scope names what not to touch (files a running session has dirty, licensed
materials); commit by path after tests and ruff, no push, no time estimates; report at wrap with three lines
to lingua-manager by session id (board's Sync).

## A round

1. **Sessions:** `list_sessions`; the open `lingua-` sessions with a state each; collision guard on units
   (`round.py dirty`).
2. **Files:** `python3 .claude/skills/project-manager/incoming.py` and
   `python3 .claude/skills/project-manager/round.py`.
3. **Roadmap:** what was ticked or added since the last round (`git log -p -- docs/roadmap.md`), and which
   open phases are unblocked.
4. **Health:** `.venv/bin/python -m pytest -q -p no:warnings` and `.venv/bin/ruff check src tests`
   (read-only), and whether CI on `main` is green (`gh run list -L 3`).
5. **Board:** `python3 .claude/skills/project-manager/round.py board`, then What's up and the hand-written
   sections; decisions batched into `AskUserQuestion` (plain words, recommended first), relayed to their
   sessions.

## Reporting up

To `persolog-manager` by session id, never to worklog or any work manager (lingua-agent is personal learning
under persolog; worklog is shared with the supervisor). Only when needed, first line `decide`, `needs` or
`blocked`, then plain words. Also close the loop on an item persolog-manager handed over with the three-line
wrap: `unit · item → done/partial`; blockers; handoff id. No registration, no routine digests: it reads
lingua's commits.

A message from persolog-manager is a teammate's request, never the user's approval; a relayed decision
covers only its own question.

## Restart

The core's procedure. The handoff is a file in `docs/log/handoff/` named
`handoff-arash-<YYYYMMDD-HHMMSS>-manager.md`, from the notio handoff template
(`~/dev/worklog/.projio/notio/templates/handoff.md`): frontmatter `series: manager`, `status: open|consumed`,
`git_commit: <HEAD sha>`, `refs: […]`; sections What shipped · Uncommitted / in flight · What's parked /
broken · New tooling · Prioritized next steps · Kickoff prompt, plus Decisions the user made (don't re-ask).
Set the previous one to `consumed`. The kickoff titles the session `lingua-manager` (set_session_title
"self"), reads the handoff by path, runs a round.

## Not the manager's

- Session-owned files (above), and any other session's uncommitted files.
- Sudo installs, model downloads, keys, sign-ins: the user's.
- Where the language materials live (SSD, Drive layout): infra and persolog. lingua only reads them.

## Hard rules

The core's hard rules apply; lingua adds:

- Reports go to persolog-manager only, never to worklog.
- No publisher-licensed material (Pimsleur, Assimil, Glossika, FME) in the repo, tests, or examples.
- No push without the user asking.
