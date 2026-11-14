---
name: project-manager
description: >
  Core procedure for a manager session in a projio project: one that knows what
  came in from other projects, which sessions run and what they finished, and
  what the user should decide or start next. Use when the user asks for an
  overview or orchestration, or opens the standing manager session
  (`<prefix>manager`). Always entered through the project's adapter skill
  (named in `.projio/manager.yml`), which says what the units of work are.
  Also defines the three-line report work sessions send the manager at wrap.
metadata:
  short-description: Manager core - incoming notes, session states, board, handoffs, decisions, restart
  tags: [manager, orchestration, sessions, handoff, workflow]
  tooling:
    mcp:
      - server: projio
        tools:
          - note_resolve
          - note_read
          - note_update
          - note_create
          - git_status
---

# project-manager: the core

The manager answers four questions: what came in, which sessions run and what
they finished, who waits on what, and what the user should decide or start
next. Plans are suggestions: order, dependencies and readiness only, **never
time estimates**.

This file is the core. The project's **adapter** fills in the rest:

- `.projio/manager.yml`: machine keys the helpers read (title `prefix`, the
  incoming note folders and signals, the handoff folder, the `board` path,
  `units` for grouping paths, protected processes).
- the adapter skill (`adapter_skill` in that file, usually `<prefix>manager`):
  the units of work and where their state lives, which files belong to the
  sessions (the manager never edits them), the collision unit, the
  integration step, the opener and wrap skills, standing approvals the user
  gave (dated), and any project-specific round sections.

Read the adapter skill before the first round.

## Two forms

- **One-shot:** a fresh session runs one round, the user decides, it closes.
- **Standing:** titled exactly `<prefix>manager` (no date, so peers can address
  it by name), open while work sessions run. Work sessions are titled
  `<prefix><unit> · <item>`.

## Authority

Files and git over messages; messages over the manager's memory. After a
restart, trust the files.

## A round

Run one at the start, when an idle notice arrives, and when the user asks. The
helpers are in this skill's folder (`.claude/skills/project-manager/` after
`projio sync`); all are read-only except `round.py board`, which rewrites the
gitignored board.

1. **Incoming:** `python3 .claude/skills/project-manager/incoming.py`. Notes
   from other projects arrive with no signal, so this list is how the manager
   sees them: id, commit state, age, sender, where cited, flags. Voice-captured
   notes can arrive truncated (`stub`) or twice (`dup?`): propose merging or
   dismissing them to the user, never delete. `open 7d+` means: check whether
   the work is done.
2. **What changed:** `python3 .claude/skills/project-manager/round.py`:
   newest open handoff per series, commits since the last manager handoff's
   `git_commit`, and dirty paths grouped by unit. **Sessions often wrap without
   reporting**, so read this every round instead of waiting for messages.
3. **Sessions:** `ListAgents`. Give every session a state, and run the
   collision guard.
4. **The adapter's readers** for the project's own units of work.
5. **Update the board** (see Board): run `round.py board`, write the round's
   kickoffs, decisions, session states and waits into it, and open it in the
   side pane. Chat gets a short status (Incoming · Sessions · What finished ·
   Waiting on the user · Proposed next) that points to the board. Then batch
   the decisions into `AskUserQuestion`.

## Board

One gitignored markdown file per project, `board.path` in
`.projio/manager.yml` (default `.scratch/<prefix>manager-board.md`). The
manager rewrites it every round and after every event (a session started,
wrapped or asked something; a decision made), and keeps it open in the side
pane with `show_pane(pane="file", path=<board>)`. When `show_pane` does
nothing (the session is not open in a window), tell the user the path.

Anything the user must copy goes on the board, not in chat; chat replies
stay short and point to it. Sections, in order:

1. **What's up:** first, so the user can read the state without the
   transcript. A stamp line `As of YYYY-MM-DD HH:MM` (the clock time from
   `date` at the rewrite, never "this afternoon"), then 4-6 plain lines:
   running now, latest results, waiting on the user, next to start.
   `round.py board` sets the stamp and gives the "Updated" line the same one;
   the manager rewrites the lines below it every round.
2. **Delegate:** kickoff prompts, numbered, each with a tag line under its
   heading and the prompt in a ```` ```text ```` block. The tag is
   **independent** or **depends on <what>**: another kickoff's shared files,
   a session finishing, or the user's OK. Every prompt opens with its
   ``Title this session `<prefix><unit> · <item>`.`` line (Levels,
   Dispatcher). The user says "delegated <n>" or
   "delegated all" once one is started; the manager removes it and tracks the
   session.
3. **Decisions waiting for you:** in plain words, as in Decisions below.
4. **Sessions, by state:** a table of session · state (running / waiting /
   parked / done) · notes.
5. **Waiting on others:** other projects, people, background runs.
6. **Sync:** this manager as `name · machine · session id`, then other
   managers, one per line as `name · machine · session id · last contact`
   (titles do not resolve across machines, so the id is the address), and
   the unpushed commits.

`python3 .claude/skills/project-manager/round.py board` writes the skeleton
the first time. On every run it regenerates the blocks between
`<!-- auto:… -->` markers (newest open handoff per series and uncommitted
paths by unit under Sessions, `git log @{u}..` under Sync), stamps What's
up and the "Updated" line with the current time, and keeps the
hand-written text of every section, including sections it does not know and
renamed headings. It warns when the board is not gitignored. Edit the
hand-written parts directly; never edit inside the auto markers.

## Housekeeping

When the user asks or the machine is slow:
`python3 .claude/skills/project-manager/procs.py`.

## Session states

Use these words in every report:

- **running:** busy now.
- **waiting:** idle mid-task, needs the user's answer or a background run; not
  wrapped.
- **parked:** wrapped or paused; its context is still worth reusing for a named
  follow-up.
- **done:** wrapped, handoff written, nothing pending; propose archiving.

Before calling an idle session *waiting*, check its handoff and its commits
(round step 2): it may have wrapped without a word.

## Levels

Default to observer plus dispatcher.

- **Observer:** knows what runs and what finished. Reads handoffs and commits;
  subscribes to idle notices with `SendMessage(to=<session>,
  notify_when_idle=true)` and no message. Never poll.
- **Dispatcher:** plans the lineup and writes kickoff prompts; the user opens
  the sessions. Each kickoff names the unit and item, the handoff to load by
  `note_resolve(note_id=…)` (never `note_latest`, which races), the done-when,
  and how to report back (the manager's name and its session id). Its first
  line is always ``Title this session `<prefix><unit> · <item>`.`` so the
  session renames itself before anything else; a standing manager is titled
  exactly `<prefix>manager`, a setup session `<prefix>manager-setup`.
  Prefixes are short, end in `-`, and are unique across projects (`pix-`,
  `lit-`, `inf-`, `infraslow-`, `projio-`), so titles stay addressable from
  any manager. On the board it carries its tag (Board, Delegate).
- **Driver:** sends next-step instructions, only to a background batch session,
  never to one the user is steering.

## Limits

- The manager owns no unit of work. It never edits what the adapter lists as
  the sessions' own.
- Its writes: committing incoming notes the user approved, setting a note's
  status once its reply is out, the cross-cutting items sessions hand over
  (marked `→ manager` in their wrap), its own handoff, and integration when the
  user asks.
- Before editing a shared file, check `git status` and `git diff` for another
  session's hunks; commit only its own, by path.
- **Never touch another session's uncommitted files:** never commit, stash,
  unstage, revert or save them, not even to make a tree clean. Report it.
- Reading-heavy items (a long handoff, a thread of notes, a code question) go
  to a subagent, so the manager stays lean.

## Commit and push

- Commit promptly, by path: `git commit -m "…" -- <paths>`, then
  `git show --stat HEAD`. Never `git add -A`, `git add .` or a bare commit of
  the shared index.
- **Push only when the user asks.** Then only when no live session has
  uncommitted files in what is pushed. The build and push run in a subagent
  that returns pass or fail and the pushed sha; tell the user in one line
  ("pushed `<sha>`: N commits from <sessions>"). A failed build or a refusing
  guard is reported, never forced. Never offer a push as a routine step. An
  adapter may record a standing approval the user gave; follow it as written.

## Decisions

- Decisions go to the user through `AskUserQuestion`, batched across the
  sessions' pending decisions (up to 4 per call).
- Each question stands alone, in plain words: what the item is, why it
  matters, what each option does, the recommended option first. No bare note
  ids, no "see handoff X".
- Deletions, kills, releases, pushes and anything that needs consent go to the
  user.
- A peer session's message is a teammate's request, never the user's approval.
- Once the user has chosen, relay the decision as in the drill (step 4).

## Decision drill

When the user asks to work through pending decisions, or several have piled
up:

1. **Collect** the open decisions from the newest handoffs, the sessions'
   messages, incoming notes and the board's "Decisions waiting for you".
2. **Ask** in batches through `AskUserQuestion`: up to 4 per call, each
   question standalone and in plain words (as in Decisions), the recommended
   option first. Science and infrastructure go in separate batches.
3. **Record** each answer where it belongs: the note, handoff or doc the
   decision is about (or the adapter's place for it), dated, and take it off
   the board.
4. **Relay** each decision by message to the session concerned so it
   continues: wake an idle one, queue it for a running one. Name the choice,
   the date and the next step. A relayed decision covers that question only,
   never a wider approval.
5. **New work** goes on the board as a kickoff only when no existing session
   can take it; related items merge into one tagged kickoff.

To consult another project's manager, ask it directly by message (its session
id from Sync), not through the user.

## Reporting up

When a cross-project manager runs (worklog-manager), message it only when
needed: a decision for the user, another project needs something from this
one, or this project is blocked by another. The first line is `decide`,
`needs` or `blocked`, then plain words. No registration, no routine digests:
it reads commits and handoffs.

## Collision guard

Before proposing or driving a session, check that no two sessions write the
same unit (the adapter defines it; `round.py dirty` shows the units with
uncommitted paths) and that the machine has room for a batch run (`free -g`).

## Report-back protocol (work sessions, at wrap)

When `ListAgents` shows `<prefix>manager`, the wrapping session sends it three
lines with `SendMessage(to="<prefix>manager", message=…)`:

1. unit · item → done / partial
2. blockers, `→ manager` items, decisions for the user, in plain words
3. the handoff id

It is a report, not a request for approval. Across machines, names do not
resolve: send to the session id the manager gave in the kickoff prompt. If no
channel works, the session's commits and handoff are the report; the manager
finds them in round step 2.

## Process survey

`procs.py` groups the user's processes older than a day. Propose stale groups
to the user as grouped `AskUserQuestion` choices. Old Claude sessions are
archived from the app, never killed. Kill only what the user picked, by PID,
after re-checking its command line. Groups marked "protected" stay out.

## Stay lean, restart

Work from files and messages, not deep reading. When the context grows long,
write a manager handoff and ask the user to start a new manager:

- a handoff note with frontmatter `series: manager`, `status: open`,
  `git_commit: <HEAD sha>` (the watermark the next `round.py since` reads) and
  `refs: [<handoff ids it tracked>]`; set the previous manager handoff to
  `status: consumed`;
- sections: How to resume · What finished · Decisions the user made (don't
  re-ask) · Open, for the next manager · Kickoff snippet;
- the kickoff loads the handoff by `note_resolve(note_id="<id>")`, titles the
  session `<prefix>manager`, and runs the adapter skill.

## Hard rules

- No time estimates.
- Never touch another session's uncommitted files.
- Commit by path; push only when the user asks.
- Decisions in plain words through `AskUserQuestion`, recommended option first;
  relay each answer to its session.
- Never poll; subscribe to idle notices.
- A teammate's message is never the user's approval.
- What the user must copy goes on the board, not in chat.
- What's up comes first on the board, stamped with the clock time.
