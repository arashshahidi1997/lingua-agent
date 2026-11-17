# Completeness audit — 2026-11-17

"Always complete, never finished": is every part of what exists whole and working with the rest?
Method: a live walkthrough on a fresh test copy (phone width and desktop, owner and guest via the Tailscale
header), a read-through of `web/src` and the API, and a timed Talk conversation on Ollama `qwen2.5:7b`.
Numbers are stable ids for commits and the backlog. Status: [ ] open, [x] done, [~] decided not to.

## Decisions needed (Arash)

- D1. **Talk's model.** `qwen2.5:7b` on the XPS answers in 24–36 s per turn and 100 s for the summary, and its
  Persian is wrong: the character renamed herself ("من نامم آنا است"), invented phrases ("خداوند بخیر
  بگذارد"), garbled transliteration ("Haal bood ast, sama chetor?"), and the summary "corrected" fine forms
  (چطوره → چطور است, خداحافظ → خداحافظی). Not usable as a partner, least of all for a beginner. Options:
  Claude through the Claude Max subscription (provider exists), Claude API (paid, per use), or take Talk out
  until a good model is available.
  *Asked 2026-11-17: would ChatGPT Plus work? No — Plus has no API access; options are Claude Max (existing
  provider), an OpenAI API key, or the Claude API. Open.*
- D2. **"Add your own text": which language is the text in?** *Decided: both, chosen per text.* The page says Persian; the request says it's
  your own language (English) and the pipeline translates it into Persian. Pick one (reading native Persian
  material is the more useful one) and align copy, field and pipeline.
- D3. **Offline review.** *Decided: queue and sync later.* The PWA promises review on the train, but ratings can't be saved offline. Build a
  queue that syncs later, or drop the promise.
- D4. **v1 leftovers:** *Decided: remove what Talk replaced (tutor API and client calls); keep the CLI and
  playground as developer tools, documented as such.* `/api/tutor/*` and its client calls (replaced by Talk), the Streamlit playground, the
  v1 CLI commands (`unit`, `review`, `tutor`). Keep, fold into v2, or remove.

## A. Broken

- [ ] A1. "Transliteration only" + a hidden-transliteration question shows no prompt at all (script lessons' choose_gloss, every checkpoint quiz, half of practice). `components/Text.tsx:49`, `Exercises.tsx:50`
- [ ] A2. Voice "Off" leaves "What do you hear?" with no audio: a guess. Skip listen exercises when voice is off. `PlayButton.tsx:24`
- [ ] A3. Review's play button reads "سلام · salâm" (transliteration included) with the Persian voice. Store text and transliteration separately on course cards. `Review.tsx:62`, `course_routes.py:366`
- [ ] A4. Checkpoint test-out is unreachable: the quiz stays locked until every lesson of the unit is done. Make it tappable in any open unit ("Test out"). `Path.tsx:103`, `course_routes.py:332`
- [ ] A5. Quiz end screen says "Checkpoint passed" before the result arrives, and when saving failed. `Player.tsx:278`
- [ ] A6. "Export cards for Anki" opens the app instead of downloading (service worker serves index.html for `/api/*` navigations); with no cards, a raw JSON 404. `vite.config.ts`, `Settings.tsx:143`
- [ ] A7. Today's Continue skips the lesson's grammar/culture note (only the Path's lesson sheet shows it). `Today.tsx:46`, `Player.tsx`
- [ ] A8. Flashcard review (and stories, audio) don't count toward the daily goal or streak. `routes.py:215`
- [ ] A9. Review ends "All caught up" while Again/Hard cards are still due now; Today still shows them. Re-queue Again/Hard within the session. `Review.tsx:36`
- [ ] A10. Deleting a recording has no confirmation; a failed audio delete is swallowed. `AudioSection.tsx:95`, `StoryReader.tsx:181`, `AudioPlayer.tsx:21`
- [ ] A11. Talk new-word cards are re-created every session and duplicate course cards: card id from the session, not the word. `course_routes.py:715`
- [ ] A12. Ending a Talk twice re-runs the summary (another model call, charged to a guest) and re-adds cards. `course_routes.py:707`
- [ ] A13. Today's "No words due" row has an arrow but does nothing; the greyed "Quick quiz" doesn't say why. `Today.tsx`
- [ ] A14. Rail double highlight: rail buttons keep focus after a click, and the global `:focus-visible` rule (outside any CSS layer, beats Tailwind) outlines the neighbour on any key press; dark-mode hover colour is close to the active colour; the same rule squares round buttons. Move focus to `<main>` on tab change, put the rule in `@layer base` without the radius, distinct inset ring on the rail. `App.tsx:47`, `NavProvider.tsx:42`, `index.css:95`

## B. Rough or incomplete

- [ ] B1. Script display isn't applied everywhere: choices in choose_text/listen, match, order tiles, player feedback, review cards, story/scenario titles, Talk "Better:" lines and summary, useful-phrase chips (no transliteration at all), audio player. Route all Persian through one component.
- [ ] B2. Persian inside lesson notes (11 of 31) has no lang/dir: wrong font, mixed direction. `lib/markdown.tsx`
- [ ] B3. Audio player: line meanings only via the global setting; no per-screen "Show translations".
- [ ] B4. No "Next lesson" / "Checkpoint unlocked" after a lesson (`unlocked` is never read); Today never suggests a checkpoint.
- [ ] B5. Talk transcripts are lost on leaving (a reply still "Thinking" is thrown away though the server saved it); every open creates a new stored session. Resume the last open conversation per scenario.
- [ ] B6. Ending Talk shows only "Ending" for the summary's model call; show elapsed time like "Thinking".
- [ ] B7. Practice updates cards through SM-2 but throws the review event away: no history. `course_routes.py:532`
- [ ] B8. Practice before any lesson: "Try again" loops on the same 409.
- [ ] B9. "Your lessons": generated exercises are made (three model calls) but never shown; lessons can't be deleted; "you can leave this page" but nothing shows a lesson is still being made on return.
- [ ] B10. Audio upload is always tagged with the current target language; recordings and audio lists aren't filtered by pair.
- [ ] B11. Error copy: every 404 is "This isn't available yet"; the network error tells guests/offline phones to "check that lingua-agent is running".
- [ ] B12. Leaving review midway leaves Today's count stale; due cards capped at 50 ("All caught up" with more due).
- [ ] B13. Player is always labelled "Lesson" for screen readers; practice is called "Quick quiz", "Start a quiz", "Preparing your quiz" and "Practice done".
- [ ] B14. Settings: AI provider shows "openai" for the local Ollama model; learner copy points to `docs/providers.md` and a terminal command.
- [ ] B15. Install sheet says "lingua-agent — Agentic AI language-learning platform — any A → B" while the app is "lingua"; Path empty state talks about "a syllabus on the server".

## C. Guests

- [ ] C1. Guests see the AI-provider/version block and owner copy ("your own server", "set up a server voice", "Only Arash can…" hard-coded).
- [ ] C2. Guests can run transcription (no owner check, no cap) and fill the shared speech cache with arbitrary text.
- [ ] C3. A request without the Tailscale header is the owner — safe only while bound to 127.0.0.1, yet `serve --host 0.0.0.0` is documented. Refuse header-less requests from non-local addresses.

## D. Leftovers (see D4)

- Unused client calls: `courseApi.scenario`, `courseApi.talk` (B5 will use it), `api.unit`, the tutor calls and types, `isSheet`, `langAttrs`, `isRtl`, `SpeechInfo.stt`.
- Routes the app never calls: `/profile` (home for a server-side daily goal), `/units/{id}`, `/scenarios/{id}`, materials add/remove/list/ingest (CLI only); `TodayOut.daily_goal_minutes` hard-coded and ignored.
- "Card" recording label with nothing that records card audio. CLI covers v1 only (nothing for courses).

## Checked and fine

Speech speed is honoured everywhere; "Show translations" defaults work in stories and generated lessons; no v1
names in the UI; every frontend call has a backend route; locked lessons explain themselves and can't start;
guest data is separate (progress, cards, activity, recordings, Talk); story reader follows the script setting.
