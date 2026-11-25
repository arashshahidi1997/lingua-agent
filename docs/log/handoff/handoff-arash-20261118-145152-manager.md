---
title: "lingua: wrap 2026-11-18 — grammar lab in review, native voice sheets 1+4 done"
date: 2026-11-18
timestamp: 20261118-145152
tags: [handoff]
series: manager
branch: "main"
status: consumed
git_commit: "7bd1380"
refs: [docs/backlog.md, content/recording/fa-en-a1/re-record.md, .scratch/lingua-manager-board.md]
---

# lingua: wrap 2026-11-18 — grammar lab in review, native voice sheets 1+4 done

**How to resume (one paste):** title this session `lingua-manager`, load the lingua-manager skill, read this
file and the board (.scratch/lingua-manager-board.md), run a round.

**Restart needed (new MCP tools)?** no

## What shipped this session (2026-11-18)
- Grammar lab: 8 hand-written topics (course/data/grammar/fa-en-a1.yaml): discover → rule card → practice
  (predict, transform, choose), checked server-side in script or transliteration; drafts owner-only until
  approved in the app (approvals in .lingua-agent/grammar_reviews.json). Library › Grammar; Path nodes per unit.
- Native voice: sheet 1 (74 lines) and sheet 4, the alphabet (90 lines), plus 10 re-records (5-redo); takes
  rotate at random; tools/native_voice.py aligns per segment with Whisper hotwords (tip from ohr-studio).
- Voice review in the app (Settings › Your voice): play each take, mark bad (no longer played). 18 marked so far.
- Calmer match feedback: a finished match is "All matched", not repeated (commit 7bd1380, NOT pushed).
- GitHub: private values scrubbed from unpushed history before the first push; ruff pinned (CI green).
- Nightly Drive backup of .lingua-agent (systemd user timer lingua-backup.timer, 03:30, 60-day history).

## Uncommitted / in flight
- Nothing uncommitted. main is 1 commit ahead of origin (7bd1380): Arash stopped that push — ask before pushing.

## What's parked / broken
- Talk off (local model's Persian unusable); role-plays are prompts for the learner's own chatbot.
- Offline-first app: planned, plan to be written for approval.

## Decisions the user made (don't re-ask)
- Placeholders in the public repo; English is Anya's support language; backup to Drive by lingua itself.
- Grammar: wait for Arash's review before new features (Decode is next after it).
- Recording format: words ×3, sentences once, last take on repeats; lyrics pasted by Arash himself.
- Next recordings: sheets 2 and 3 (sheet 4 done).

## Prioritized next steps
1. When Arash has reviewed/approved grammar topics: Decode mode (board kickoff 1).
2. Process sheets 2/3 when uploaded (board kickoff 2); refresh tools/voice_review.py.
3. Ask Anya's impressions of Fill the gaps and the grammar lab.

## Kickoff prompt (paste into the next session)
> Title this session `lingua-manager`. Load the `lingua-manager` skill, read handoff `docs/log/handoff/handoff-arash-20261118-145152-manager.md` and the board
> (.scratch/lingua-manager-board.md), then run a round.
