---
title: "lingua: end of day 2026-11-18 — learning modes in progress"
date: 2026-11-18
timestamp: 20261118-045028
tags: [handoff]
series: manager
branch: "main"
status: open
git_commit: "a783bfd"
refs: [docs/backlog.md, docs/audit/2026-11-17-completeness.md, content/recording/fa-en-a1/re-record.md]
---

# lingua: end of day 2026-11-18 — learning modes in progress

**How to resume:** read docs/backlog.md, section "Learning modes for analytical learners"; next is item 2,
the Grammar lab.

## What shipped (since the 2026-11-14 handoff)
- Product v2 audit fixed (docs/audit/2026-11-17-completeness.md); offline queue; owner/guest over Tailscale
  (Anya has her own data; infra opened port 443 to her).
- Built-in Talk off (local model's Persian unusable); role-plays are prompts for the learner's own chatbot.
- Look: turquoise theme, carpet margins, winding Path with tea/pomegranate/pistachio milestones.
- Native voice: tools/native_voice.py; sheet 1 recorded (Units 1 and 4: 74 texts, 144 takes); /api/tts plays
  a random take, Piper otherwise.
- Fill the gaps in stories (course/cloze.py, ClozeReader); fast track on the Path.

## Uncommitted / in flight
- Nothing. main is 27 commits ahead of origin (not pushed; push only when asked).
- Service: systemd user unit lingua-agent; tailscale serve on 443. Rebuild + restart to deploy.

## Parked / open
- Re-record list (optional): content/recording/fa-en-a1/re-record.md. Sheets 2–4 not recorded yet.
- Backup of .lingua-agent (progress, recordings, native_audio): nothing copies it — Arash to decide, infra.
- Talk's own model: OpenRouter comparison when Arash has a key.
- Offline-first app: planned after recordings (backlog).

## Decisions the user made (don't re-ask)
- "Always complete, never finished" (memory: complete-before-new).
- Talk off; role-play prompts for own chatbot instead. ChatGPT Plus can't power the app (no API).
- No GPU purchase for now (inf-manager advice).
- Learning modes order: 1 cloze ✓, 2 grammar lab, 3 decode, 4 dictation, 5 songs/film. Path keeps a fast track.
- Grammar explanations: written by Claude, reviewed by Arash before going live.
- Persian of Iran Today is CC BY-NC-ND: inspiration only.

## Prioritized next steps
1. Grammar lab (discovery → rule card → transform tasks), explanations sent to Arash for review.
2. Ask how Anya finds Fill the gaps.
3. Decode mode; dictation; songs/film.

## Kickoff prompt
> Read handoff `docs/log/handoff/handoff-arash-20261118-045028-manager.md` and docs/backlog.md; continue with the Grammar lab.
