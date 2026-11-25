---
title: "lingua: manager restart 2026-11-25 — for start_session; German + Russian plan waiting to start"
date: 2026-11-25
timestamp: 20261125-022632
tags: [handoff]
series: manager
branch: "main"
status: open
git_commit: "e597df2"
refs: [docs/log/handoff/handoff-arash-20261118-145152-manager.md, .scratch/lingua-manager-board.md, docs/backlog.md]
---

# lingua: manager restart 2026-11-25 — for start_session; German + Russian plan waiting to start

**How to resume (one paste):** see Kickoff prompt below.

**Restart needed (new tools)?** yes: this is the restart. The old manager (2026-11-18) predates the desktop-app
update of 2026-11-23, so it has no `mcp__ccd_session__start_session`; a fresh session has it.

## What finished (2026-11-18 → 11-25)
- Grammar review started: topic 1 feedback collected (board kickoff 3: highlight marks every occurrence, e.g.
  the م of «من»; answers in Persian script only; learner toggles for a word chooser and transliteration hints;
  topic 6 «را» title bidi). Topics 2–8 still to review.
- inf-manager: XPS moved off conda to a uv `.venv`; the live service was restarted onto it on 2026-11-18 22:57
  (checked again 2026-11-25: up since 11-23 12:18, local + tailnet /api/me 200, no errors, backup ran).
- Answered inf-manager: lingua makes no background model calls (Talk off); the 11-18 swap was most likely
  faster-whisper "medium" in tools/native_voice.py.
- Manager: core moved to the projio-workflow plugin (no repo copy, ac011d4); adapter realigned with the
  manager-setup template (989a235), core-updates pointer + start_session launching (e597df2). Plugin on the
  laptop: 0.5.0 (one-line decision format on the board).
- `/always-complete` exists as projio-workflow:always-complete (plus a hand-made user-level copy, see Open).

## Uncommitted / in flight
- Nothing uncommitted. main is 4 commits ahead of origin (manager commits b65ebe7…e597df2) plus this
  handoff: not pushed (push only when Arash asks).

## Decisions the user made (don't re-ask)
- 2026-11-18: push 7bd1380 (done); archive lingua-manager-old (done); Talk stays off, role-play prompts meanwhile.
- 2026-11-18: grammar answers in Persian script only, word-chooser and transliteration-hint toggles (kickoff 3).
- 2026-11-19: realign lingua's manager with the template (done).
- 2026-11-25: German + Russian courses: plan now, build after the Persian grammar fixes; first learner Arash,
  intermediate+; support language English. Emphasis: multi-dimensional skill profile, placement test,
  adaptive lesson choice, etymology (Greek, Latin, Germanic, Arabic, sometimes PIE), function of words and
  phrases at B1+, short stories from public-domain/open sources only.
- 2026-11-25: restart the manager in a fresh session so it can start sessions itself.
- Earlier (11-18 handoff): placeholders in the public repo; English is Anya's support language; Drive backup;
  grammar review before new features; recording format; sheets 2 and 3 next.

## Open, for the next manager
1. **Start board kickoff 4** (`lingua-docs · German + Russian plan`) with start_session on Arash's go:
   initiation `user_asked`, context fresh, cwd ~/dev/learn/lingua-agent, use_worktree false; its prompt is on
   the board under Delegate. The report-back id in it is the OLD manager's
   (local_b5550710-…): replace it with the new session's id before starting.
2. Board kickoff 3 (grammar review fixes): waits for Arash to finish reviewing topics 2–8.
3. Board kickoff 2 (voice sheets 2 and 3): waits for Arash's recordings. Kickoff 1 (Decode): after approvals.
4. Decisions on the board: offline-first plan timing (rec. after the recordings); remove the hand-made
   user-level skills `~/.claude/skills/{always-complete,project-manager,manager-setup}` that the plugin
   replaces (rec. remove); create the gitignored `inbox/` file inbox (rec. create).
5. Rename the old manager session to `lingua-manager · retired 2026-11-25` if it still shows as `lingua-manager`.

## Kickoff prompt (paste into a new session in ~/dev/learn/lingua-agent)
> Title this session `lingua-manager`. Load the `lingua-manager` skill, read handoff
> `docs/log/handoff/handoff-arash-20261125-022632-manager.md` and the board (.scratch/lingua-manager-board.md),
> turn Remote Control on, put this session's id under Sync, then run a round.
