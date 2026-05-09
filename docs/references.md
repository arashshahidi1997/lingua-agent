# Reference projects

Summaries from a Phase 0 survey (May 2026). All projects listed are MIT, Apache-2.0, or CC0 unless noted, so patterns and (where useful) clean-room re-implementations are safe to use under our own MIT license. We do not vendor any source verbatim.

## Architectural reference

### pretzelai/openlingo — MIT
- https://github.com/pretzelai/openlingo
- TypeScript / Next.js / Drizzle / Postgres. Web-first, not local-first.
- Real **agent with typed tools** (Vercel AI SDK + Zod). Notable tools: `readMemory` / `addMemory` / `rewriteAllMemory` (the memory trio), `srs` (constrained SQL against the SRS table only), `presentExercise`, `createUnit`, `addWordsToSrs`, `switchLanguage`, `readArticle`.
- **SM-2** in `lib/srs.ts` (~70 LOC). Card schema: `easeFactor`, `interval`, `repetitions`, `status` (`new|learning|review`), `nextReviewAt`, plus pedagogical fields (`cefrLevel`, `pos`, `gender`, `exampleNative`, `exampleEnglish`).
- Lessons are a **markdown-with-frontmatter DSL** parsed into 9 exercise types (translation, multiple-choice, fill-in-blank, matching, listening/TTS, word-bank, speaking/STT, free-text).
- Word-cache: memoize LLM word analyses keyed by `(word, lang)`.
- **Borrow** (as patterns, re-implemented in Python): agent + tool surface, memory-trio tool shape, SM-2, markdown-unit DSL, prompt registry with `{var}` interpolation, word cache.
- **Skip**: stack (Next.js/Drizzle/Postgres), web-only renderers, server-side TTS+R2.
- **Notable gap**: no Persian dictionary seed, no RTL handling. We have to build both.

### CAHLR/OATutor-LLM-Learner — MIT
- https://github.com/CAHLR/OATutor-LLM-Learner
- Source for the **Bayesian Knowledge Tracing** module. Per-skill 4-parameter model (`probSlip`, `probGuess`, `probTransit`, `probMastery`); item picker = lowest-mastery-above-threshold-not-yet-completed.
- ~30 LOC clean-room Python port planned for Phase 6. Reference path: `src/models/BKT/BKT-brain.js`.

### 5uru/Discute — Apache-2.0
- https://github.com/5uru/Discute
- Streamlit + Whisper + Groq + Kokoro voice pipeline. The valuable shape is the **3-function STT → LLM → TTS seam**, easy to mock and swap. We mirror this with `voice/{stt,tts}.py` Protocols from day one even though voice is post-MVP.
- For Farsi/Russian voices we will favour Piper over Kokoro (better coverage); faster-whisper handles all four target languages for STT.

## UX / pattern references

### sjoerdvanderhoorn/babbelaar — MIT
- https://github.com/sjoerdvanderhoorn/babbelaar
- Single-file vanilla browser app. No SRS, no schema, no agent. Useful only as a UX sketch: tutor persona prompt shape, click-any-word inline translation with a per-session cache, profile-driven personalization.

### raine/anki-llm — MIT
- https://github.com/raine/anki-llm
- Rust CLI. We borrow the **AnkiConnect** request shapes (`addNote`, `findNotes`, `notesInfo`, `updateNoteFields`, `storeMediaFile`) and the CSV/YAML round-trip workflow (Anki can be closed during processing). MVP exports CSV; AnkiConnect later.

### StephanAkkerman/mnemorai (a.k.a. FluentAI) — MIT
- https://github.com/StephanAkkerman/mnemorai
- Implements the **SmartPhone keyword-mnemonic** method (arXiv 2305.10436). Pipeline: translate + transliterate → phonetic-keyword search in L1 → vivid linking sentence → image render → TTS. We adopt the prompt shape and pipeline ordering for our `mnemonic_generation_prompt`. Image+TTS deferred.

## Spaced repetition primitives

### open-spaced-repetition/sm-2 — MIT
- https://github.com/open-spaced-repetition/sm-2
- Reference algorithm; we re-implement in pure Python. Note the **q==3 same-day re-review** branch (sets `needs_extra_review=True`, due now), EF floor 1.3, intervals `1 → 6 → ceil(I × EF)`, lapse on `q<3` resets `n=0, I=0` and leaves EF unchanged. We add an explicit `lapses` counter to ease the future FSRS migration.

### open-spaced-repetition/awesome-fsrs — CC0
- https://github.com/open-spaced-repetition/awesome-fsrs
- For a Phase-N FSRS migration we will use **`open-spaced-repetition/py-fsrs`** (pure-Python, FSRS-6, has the optimizer). Identical `Card`/`Scheduler`/`ReviewLog` API shape to the SM-2 repo, so the swap is mechanical.

## Surveyed (skipped or borrowed lightly)

| Repo | License | Verdict |
|---|---|---|
| ArtCC/freelingo | AGPL-3.0 | Inspiration only (placement assessment, curriculum bounding). **No code copying** — AGPL is incompatible with our MIT release. |
| Dev-Adnani/deutsch-ai-tutor | none | Has SM-2 + mistake tracking but **no license** = legally untouchable. Skip. |
| codeafridi/LoopLingo | MIT | Wrong stack (Express/Kestra). Skip. |
| brylie/language-lesson-chat | EUPL-1.2 | Optional skim of scenario/persona library. Don't import code. |
| Nidhal-Abidi/languageWhisperer | none | Discute already covers this shape under Apache-2.0. Skip. |

## Attribution policy

- Re-implemented algorithms (SM-2, BKT) carry an attribution comment in the module header pointing at the upstream MIT source.
- We do not vendor JSON dictionaries from upstream without per-file license review.
- `docs/references.md` (this file) is the canonical place to credit prior art.
