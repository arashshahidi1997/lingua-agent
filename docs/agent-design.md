# Tutor agent design

## Why an agent and not a chat loop

A chat loop produces plausible language conversation but cannot mutate learner state, schedule reviews, generate exercises tied to weak skills, or audit its own behaviour. We want all four. The tutor is therefore an **agent that calls typed tools**, and every tool call is logged.

This shape is explicit even before a real LLM is wired up: the mock provider returns hard-coded "the next thing I would do is call tool X with args Y" plans, and the dispatcher runs them. Phase 6 swaps in a real provider; the tools and dispatcher do not change.

## Tool surface

Defined in `src/lingua_agent/tutor/tools.py` as Pydantic call objects. Each tool has:
- a name (snake_case)
- a typed `Args` model
- a typed `Result` model
- a docstring (used as the tool description for the LLM)
- a side-effect classification: `read | write | external`

| Tool | Class | Purpose |
|---|---|---|
| `get_learner_profile` | read | Return the current learner profile. |
| `update_learner_profile(patch)` | write | Apply a partial update; logged. |
| `list_due_cards(language_pair?, limit?)` | read | Return SRS cards due now. |
| `add_flashcard(card)` | write | Insert a new card with provenance. |
| `grade_exercise_attempt(exercise_id, answer)` | write | Score against `expected_answer` / `acceptable_answers`; return feedback. |
| `record_exercise_attempt(...)` | write | Persist `ExerciseAttempt`. |
| `generate_exercise(unit_id, type, difficulty)` | external | Prompt the AI provider, validate against `Exercise` schema, persist. |
| `generate_micro_lesson(document_id, target_language, level)` | external | Convenience wrapper over the ingest pipeline for a sub-section. |
| `extract_vocabulary(document_id, target_language)` | external | Re-run vocab extraction on a document. |
| `explain_mistake(answer, expected, source_language, target_language)` | external | Pedagogical explanation; cites the relevant grammar point if known. |
| `compare_languages(source_language, target_language, item)` | external | Contrastive note. |
| `switch_language_pair(source, target, support)` | write | Update session and learner profile. |
| `recommend_next_activity()` | read | Suggest next thing: due review, new exercise on weak skill, or fresh material. |

## Tool-call log

Each `TutorSession` has an append-only list of:

```python
class ToolCall(BaseModel):
    id: str
    tool: str
    args: dict[str, Any]
    result: dict[str, Any]
    started_at: datetime
    finished_at: datetime
    error: str | None = None
```

The CLI command `lingua-agent tutor inspect <session_id>` pretty-prints this log. The log is the audit trail.

## Memory

We borrow OpenLingo's **memory tool trio** (`read_memory`, `add_memory`, `rewrite_all_memory`) but back it by free-text fields on `LearnerProfile.memory: list[MemoryEntry]` rather than a separate table. Each entry carries `kind: "fact" | "preference" | "weakness"`, `text`, `created_at`. Rewrite operations log a diff to the tool-call log.

## System prompt template

`tutor/agent.py` builds the system prompt from:
- learner profile summary (target language, level, weaknesses, preferences)
- current language pair and support language
- current unit (if any)
- list of due cards (count and a few examples)
- relevant memory entries

The prompt explicitly instructs:
- Always reply in `support_language` for explanations and `target_language` for examples.
- For Persian content, prefer the original script; transliteration only on request.
- Mark uncertainty; do not invent etymology.
- Prefer calling a tool over a long monologue.

## Grading

`tutor/grading.py` implements three grading modes:
- **deterministic**: exact-match against `expected_answer` after normalization (lower-case, strip punctuation, configurable Persian zero-width-non-joiner handling); also accepts entries in `acceptable_answers`.
- **llm_rubric**: hands the answer + rubric to the AI provider; expects a `{score: 0..1, correct: bool, feedback: str}` JSON.
- **hybrid**: deterministic first; if not exact-correct, fall back to `llm_rubric`. Used for translation exercises where many phrasings are valid.

## Failure modes the agent is designed to avoid

- **Silent state mutation**: every write tool logs.
- **Hallucinated translations becoming canonical**: `provenance.generated=true` on every model-generated field; the UI treats them as drafts.
- **Forgetting which language is which**: tools take explicit `source_language` / `target_language` arguments. The agent does not infer them from the conversation.
- **Drift away from learner level**: `recommend_next_activity` reads CEFR goal and weak skills before suggesting.
