---
name: lingua-manager
description: >
  lingua-agent's manager: the adapter for the project-manager core. Use when the user opens the standing
  `lingua-manager` session, or asks for an overview of lingua-agent work ("what's running in lingua", "what's
  on the lingua board", "plan the next lingua sessions"): Arash's parallel sessions on the Python core, the
  React PWA and its Android install, lesson content and native voice, docs and tests, plus the roadmap
  phases and bugs. Loads the core first.
metadata:
  short-description: lingua-agent adapter for the project-manager core
  tags: [manager, orchestration, adapter]
---

# lingua-manager: the adapter

**Load the core first:** the `projio-workflow:project-manager` skill, from the projio-workflow plugin
(marketplace `arashshahidi1997/projio-plugins`, installed on the XPS 2026-11-19; update with
`/plugin marketplace update projio`). There is no repo copy. Run its helpers from the plugin's folder:

```bash
PM=$(ls -d ~/.claude/plugins/cache/projio/projio-workflow/*/skills/project-manager | sort -V | tail -1)
python3 $PM/incoming.py; python3 $PM/round.py; python3 $PM/round.py board
```

Wherever the core says `.claude/skills/project-manager/<helper>`, read `$PM/<helper>`. This file only fills
in what is specific to lingua-agent; the core's rules are not repeated here. Machine keys are in
`.projio/manager.yml` (lingua is not a projio project otherwise: no `projio` command, no notio; notes and
handoffs are plain files). Read `README.md` and `docs/roadmap.md` before the first round.

**Core updates:** follow the core's section (one `core update · <ver> · …` message per manager; reload the
skill after the user updates the plugin).

## Names

- Standing manager: `lingua-manager`; a session that sets up or changes the manager itself:
  `lingua-manager-setup`.
- Work sessions: `lingua-<unit> · <item>`, for example `lingua-web · Decode mode`. Units are those in
  `.projio/manager.yml` (core, web, content, tools, docs, tests, notes, config); a session writing several
  takes the main one. Find them in `list_sessions` by title prefix `lingua-` and cwd
  `~/dev/learn/lingua-agent`.
- Opener: the handoff named by path in the kickoff (never "the latest"). Wrap: a handoff in
  `docs/log/handoff/`, ending with the three-line report to `lingua-manager` by session id (board's Sync).
- Working copy: `~/dev/learn/lingua-agent` on the laptop (XPS), branch `main`. The manager runs there too.

## Board

`.scratch/lingua-manager-board.md` (gitignored). Refresh with `round.py board`, open it with
`show_pane(pane="file", path=".scratch/lingua-manager-board.md")`. lingua adds two sections, which
`round.py board` keeps in place:

```markdown
## Waiting on you
<installs needing sudo (Ollama upgrades), model downloads on a near-full disk, API keys, SSD plugged in,
 recordings, phone testing of the PWA, restarts of the live service>

## Phases
| Phase | Open session | State | Last activity | Next |
```

Other managers in Sync:

- `persolog-manager` · XPS · `local_d1d7fac3-f345-4985-89de-e2379bf20c6a`: the one above lingua (lingua is
  personal learning under persolog). Report up only to it, never to worklog or a work manager.
- `inf-manager` · XPS · `local_6078ca0c-d5be-469e-9d3e-ca41d867df74`: the machine, Ollama, tailscale, Python
  envs.

**Decisions (drill).** Record each answer, dated, in the manager handoff's "Decisions the user made (don't
re-ask)", and in `docs/backlog.md` when it changes a backlog item. Relay it to the session concerned.

## Units of work and where their state lives

| Work | Unit(s) | State lives in |
|---|---|---|
| Roadmap phase (5b, 6, 6b, 6d, 6e, 7, 9, 10, …) | core, tests, docs | `docs/roadmap.md` (✅ = shipped; a phase that ships ticks itself in the same commit) |
| Backlog items, learning modes | the unit of the change | `docs/backlog.md` (Now / Next / Housekeeping / Ideas (parked) / Done; `**user**` = Arash's items) |
| UI and PWA / Android | web | commits; `docs/mobile-https.md` for phone testing |
| Lessons, grammar topics, native voice | content, core | `src/lingua_agent/course/data/`, `content/recording/`; approvals in the app's data dir |
| AI providers (Ollama, Anthropic, Claude Max) | core | env vars (`docs/providers.md`, the systemd unit); no secrets in the repo |
| Materials adapter (SSD, Drive) | core, tools | publisher-licensed materials never enter the repo or tests |
| Bugs | the unit of the fix | commits, handoffs |

The direction under review is `docs/product-v2.md`; the completeness audit is `docs/audit/`. Next-work
proposals follow "always complete, never finished" (`projio-workflow:always-complete`): complete what exists before new
modes or content.

**Incoming.** Notes routed from persolog or another workspace land in `docs/log/inbox/` (title
`[from <project>] …` or a `### Source context:` line). Rare; most requests arrive as session messages.

## What belongs to the sessions (the manager never edits)

- Every file a work session writes: `src/`, `web/`, `tests/`, `content/`, `examples/`, `tools/`, `docs/`
  (except `docs/log/`), `pyproject.toml`, `pixi.lock`, `uv.lock`, and the sessions' handoffs.
- The app's data dir `.lingua-agent/` (Arash's and Anya's progress, recordings, approvals): read-only for
  the manager.
- The manager's own writes: the board, its handoffs, this adapter, `.projio/manager.yml` (with the user),
  inbox notes' status, and `→ manager` items a session hands over.

## Collision unit

The top-level directory, as the units in `.projio/manager.yml` map it (`docs/log/` is `notes`, the rest of
`docs/` is `docs`). `docs/backlog.md` and `docs/roadmap.md` are touched by most sessions: two may tick items,
only in small hunks committed by path; flag it when both have it dirty. `pyproject.toml`, `pixi.lock` and
`uv.lock` (dependency changes): one session at a time.

## Integration (only when the user asks)

1. Before a session commits: the uv `.venv` (`.venv/bin/python` or `uv run`; never conda or ~/anaconda3,
   and plain `python3` on PATH has only PyYAML), `.venv/bin/python -m pytest -q` and
   `.venv/bin/ruff check src tests` pass; `npm --prefix web run build` when `web/` changed.
2. The live app is the systemd user unit `lingua-agent.service` (served on the tailnet by tailscale serve,
   port 443 → 127.0.0.1:8000); it picks up backend changes only after
   `systemctl --user restart lingua-agent` (Arash runs it; check `/api/me` → 200 a few seconds later).
   Nightly backup: `lingua-backup.timer` (03:30, Drive).

Push: only when the user asks (no standing approval). Remote GitHub `origin` over HTTPS with
`git -c credential.helper='!gh auth git-credential' push origin main` (memory note `git_push_via_gh.md`).

## lingua-specific round sections

- **Backlog:** what was ticked or added since the last round (`git log -p -- docs/backlog.md docs/roadmap.md`),
  which open items are unblocked; `**user**` items go under "Waiting on you".
- **Health:** `.venv/bin/python -m pytest -q -p no:warnings`, `.venv/bin/ruff check src tests` (read-only), CI on
  `main` (`gh run list -L 3`), and whether the live service runs the repo's `.venv`
  (`readlink /proc/$(systemctl --user show lingua-agent -p MainPID --value)/exe`).
- **Reviews in the app:** grammar approvals (`.lingua-agent/grammar_reviews.json`) and voice marks
  (Settings › Your voice) gate the next kickoffs; read them, don't write them.
- **Kickoffs** add: the roadmap phase or backlog item; handoffs by path; what not to touch (files a running
  session has dirty, licensed materials, `.lingua-agent/`); test on a scratch data dir; commit by path after
  tests and ruff, no push.
- **Launching:** on the user's go, start a kickoff with `start_session` (initiation `user_asked`, its title,
  cwd `~/dev/learn/lingua-agent`, the file boundaries in the prompt); the deep link is only a fallback. All
  lingua sessions run on the laptop.

## Not the manager's

- Session-owned files (above), and any other session's uncommitted files.
- Sudo installs, model downloads (the XPS disk is near full), API keys, sign-ins, restarting the live
  service: the user's; list them under "Waiting on you" as commands.
- Where the language materials live (SSD, Drive layout): infra and persolog; lingua only reads them. The
  external SSD (Transcend) is mounted only sometimes; sessions that need it say so in the kickoff.
- No publisher-licensed material (Pimsleur, Assimil, Glossika, FME) in the repo, tests or examples.
