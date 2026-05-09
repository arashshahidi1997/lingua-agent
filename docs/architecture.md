# Architecture

```
                     ┌─────────────────────────────────┐
                     │              CLI                │  Typer
                     │  (lingua-agent ingest / review  │
                     │   / unit / tutor / export)      │
                     └──────────────┬──────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
   ┌────▼─────┐              ┌──────▼───────┐            ┌──────▼────────┐
   │  ingest  │  pipeline    │    tutor     │ session +  │     srs       │
   │  text /  │ ───────────▶ │  agent +     │ tool log   │   sm2 /       │
   │ markdown │              │  typed tools │            │   scheduler   │
   └────┬─────┘              └──────┬───────┘            └──────┬────────┘
        │                           │                           │
        │     ┌─────────────────────┼─────────────────────┐     │
        │     │                     │                     │     │
        │  ┌──▼────┐            ┌───▼────┐            ┌───▼─────┴─┐
        └─▶│lesson │            │   ai   │            │  models   │
           │ gen + │            │provider│            │ (Pydantic │
           │ md    │            │ proto  │            │   v2)     │
           │export │            │        │            │           │
           └──┬────┘            └───┬────┘            └─────┬─────┘
              │                     │                       │
              │    ┌────────────────┼───────────────────┐   │
              │    │                │                   │   │
              ▼    ▼                ▼                   ▼   ▼
           content/units/      mock | openai           Repository
           content/cards/      | anthropic             (json-on-disk
           content/exports/                            today, sqlite
                                                      tomorrow)
```

## Key abstractions

### `AIProvider` (Protocol)
- `generate_structured(prompt: str, schema: type[BaseModel]) -> BaseModel`
- `chat(messages: list[Message], tools: list[Tool] | None) -> ChatResponse`

The mock provider returns deterministic Pydantic-valid output. Switching providers does not touch any pipeline code.

### `Scheduler` (Protocol)
- `update(card: Flashcard, rating: int, reviewed_at: datetime) -> Flashcard`
- `due(cards, *, now) -> list[Flashcard]`

SM-2 is the only implementation today; `py-fsrs` is the planned second.

### `Repository[Entity]` (Protocol)
- `save(entity)`, `get(id)`, `list(**filters)`, `delete(id)`

`JsonRepository` writes one file per entity-type under `${LINGUA_DATA_DIR}/<entity>/<id>.json`. SQLite implementation is a future swap.

### `LessonUnit`
The canonical lesson is a markdown file with YAML frontmatter under `content/units/<unit_id>.md`. The frontmatter is the schema; the body is for humans. Round-trips through `lesson.markdown_export.read_unit` / `write_unit`.

### Tutor agent
`TutorSession` carries learner state, current language pair, conversation history, and an append-only `tool_calls` log. `tutor/tools.py` defines every tool as a Pydantic call object; `tutor/agent.py` is a thin loop that asks the provider for the next action and dispatches.

## Data flow: ingest

```
text / markdown
  │
  ▼
normalize  ──▶  detect_language (or validate --source)
  │
  ▼
segment paragraphs / sentences
  │
  ▼
generate_lesson_unit  ──▶  AIProvider.generate_structured(LessonDraft)
  │
  ├──▶ extract_vocabulary
  ├──▶ extract_grammar_points
  ├──▶ generate_exercises
  └──▶ generate_flashcards
  │
  ▼
persist all artifacts (Repository)
write content/units/<id>.md
return UnitSummary
```

## Data flow: review

```
list_due_cards(target_language, now)
  │
  ▼
present card to user (CLI prompt)
  │
  ▼
collect rating 0..5
  │
  ▼
Scheduler.update(card, rating, now)
  │
  ▼
Repository.save(card); append ReviewEvent
```

## Storage layout

```
${LINGUA_DATA_DIR}/                # default: ./.lingua-agent
├── learner_profile.json
├── documents/<id>.json
├── lessons/<id>.json              # mirror of content/units/<id>.md
├── flashcards/<id>.json
├── exercises/<id>.json
├── attempts/<id>.json
├── reviews/<id>.json
└── sessions/<id>.json
content/
├── inbox/                         # user drops files here
├── units/<id>.md                  # human-readable lessons (canonical)
├── cards/                         # optional flashcard exports
└── exports/                       # CSV / future apkg
```
