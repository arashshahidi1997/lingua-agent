# Architecture

lingua-agent is a FastAPI server with a React PWA on top, served from one laptop to phones over Tailscale.
Learners use the web app; the CLI and the Streamlit playground are developer tools on the same core.

```
 phones / laptop browser ──HTTPS──▶ tailscale serve ──▶ 127.0.0.1:8000  FastAPI (lingua-agent serve)
                                    adds Tailscale-User-Login            │
                                                                         ├── web/dist   React PWA (Today · Path · Library · Talk · Settings)
                                                                         ├── /api/*     api/routes.py         profile, own-text lessons (ingest), cards, export, materials
                                                                         │              api/course_routes.py  courses, sessions, practice, Today, stories, Talk, speech, recordings, audio
                                                                         └── api/identity.py  owner or guest → which data dir
```

## Who is calling

`api/identity.py` reads the header Tailscale Serve adds. Logins in `.lingua-agent/sharing.json` are the owner;
any other login is a guest with their own data dir, `.lingua-agent/guests/<login>/`. Voices, the speech cache
and extra courses are shared. Without the header a request must come from the machine itself (the server
binds 127.0.0.1). Guests get 403 on the owner's material sources and transcription, 429 past a daily cap of
model calls, 413 past a storage cap. See [mobile-https.md](mobile-https.md).

## Courses (the Path)

- **Content** is hand-written YAML: `src/lingua_agent/course/data/<course>.yaml` (Farsi A1 for English
  speakers today). Units → lessons → items (`text`, `tr`, `gloss`), plus one story or dialogue and one
  role-play scenario per unit. `course/models.py`, loaded and cached by `course/store.py`.
- **Exercises** are generated from items (`course/exercises.py`): intro, choose the meaning, choose the
  text, listen, match, word order, type the transliteration. Deterministic per seed; the client grades.
- **Progress** per learner: `course_progress/<course>.json` (lessons, quizzes, per-item stats, applied event
  ids) and `activity.json` (seconds per day → daily goal and streak). Completions and reviews carry an
  `event_id`, so the app's offline queue can replay them safely.
- **Cards**: finishing a lesson adds one flashcard per item (meaning → Persian, with the Persian kept apart in
  `target_text`/`target_tr`); review runs SM-2 (`srs/`). Practice draws on due and weak items.
- **Checkpoint quizzes** open once a unit is reached; passing one before the lessons marks them done.

## Talk

`course/talk.py`: each turn is a structured `TalkTurn` (reply, transliteration, meaning, and a correction of the
learner's last message only when needed). Ending a conversation writes a stored summary; its new words become
cards (one per word, none for words the course teaches). The model comes from the AI provider setting.

## Own texts ("Your lessons")

`ingest/pipeline.py` turns a pasted text into a lesson: analysis, bilingual reading, vocabulary, grammar,
exercises and cards, with five or so model calls. The text may be in the learner's own language (translated
into the target) or in the target language itself (meanings and explanations in the support language).

## Speech and audio

`voice/piper.py`: Piper voices in `.lingua-agent/voices/<lang>/`, synthesised once and cached by text;
without one, the app falls back to the browser's voices. Recordings (shadowing, the speaking diary) and
imported audio with `.srt`/`.vtt` cues live in the learner's data dir; faster-whisper transcription is
optional. `tools/recording_scripts.py` makes reading sheets for recording a native voice for the course.

## AI providers

`ai/`: an `AIProvider` protocol with `generate_structured` (schema-validated, repaired) and `chat`.
Implementations: mock (tests, no network), OpenAI-compatible (OpenAI, Ollama, OpenRouter, vLLM, …, with
`json_schema` output), Anthropic API, Claude Max. Chosen with `LINGUA_AI_PROVIDER`; see
[providers.md](providers.md).

## Storage

JSON files under `.lingua-agent/` (`storage.py`: one file per entity, atomic writes). Course content is in the
package; everything a learner makes is in their data dir.

## Developer tools

- `lingua-agent` CLI: ingest, units, review, export, materials, voices, and a terminal tutor chat
  (`tutor/`, the v1 agent).
- `lingua-agent playground`: a Streamlit UI on the v1 core, for trying the pipeline. Neither is the learner
  interface.
