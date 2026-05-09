# Content schema

All entities are Pydantic v2 models defined under `src/lingua_agent/models/`. IDs are URL-safe slugs prefixed with the entity type (`doc_…`, `unit_…`, `card_…`).

## Core entities

### `Language`
| field | type | notes |
|---|---|---|
| `code` | `str` | BCP-47-ish (`en`, `fa`, `it`, `ru`). |
| `name` | `str` | English display name. |
| `native_name` | `str` | Endonym. |
| `script` | `enum` | `latin`, `cyrillic`, `arabic`, `devanagari`, `cjk`, … |
| `direction` | `enum` | `ltr` / `rtl`. |
| `transliteration_supported` | `bool` | |

### `LanguagePair`
| field | type |
|---|---|
| `source` | `Language` |
| `target` | `Language` |
| `support` | `Language \| None` |

### `Document`
The raw user-supplied material. Never overwritten.

| field | notes |
|---|---|
| `id` | `doc_<slug>` |
| `title` | |
| `source_language` | code |
| `text` | original verbatim |
| `tags` | |
| `created_at` | |

### `TextSegment`
| field | notes |
|---|---|
| `document_id` | |
| `index` | order |
| `kind` | `paragraph` / `sentence` |
| `text` | |

### `VocabularyItem`
| field | notes |
|---|---|
| `id` | `vocab_<slug>` |
| `lemma` | base form in target language |
| `surface` | as it appeared in source |
| `target_language` | code |
| `translations` | `dict[lang_code, list[str]]` (typically `{ "en": ["coffee"], "it": ["caffè"] }`) |
| `pos` | part of speech |
| `gender` | `m / f / n / null` |
| `transliteration` | optional, `approximate: true` |
| `example_sentence_id` | back-reference to a `Sentence` |
| `cefr_level` | `A1`–`C2` or `null` |
| `provenance` | `{generated: bool, model: str | null, source_doc: str | null}` |

### `GrammarPoint`
| field | notes |
|---|---|
| `id` | `grammar_<slug>` |
| `target_language` | |
| `name` | e.g. "ezafe construction" |
| `summary` | short prose |
| `evidence` | list of source sentences from the document |
| `cefr_level` | optional |
| `support_language` | language of the explanation |
| `provenance` | as above |

### `LessonUnit`
| field | notes |
|---|---|
| `id` | `unit_<slug>` |
| `title` | |
| `source_language` | |
| `target_language` | |
| `support_language` | |
| `cefr_level` | |
| `source_document_ids` | |
| `vocabulary_ids` | |
| `grammar_ids` | |
| `exercise_ids` | |
| `flashcard_ids` | |
| `bilingual_reading` | list of `(source, target)` segment pairs |
| `tags` | |
| `created_at` | |

Stored on disk as `content/units/<id>.md`:

```markdown
---
id: unit_coffee_en_it
title: Coffee conversation
source_language: en
target_language: it
support_language: en
cefr_level: A1
source_document_ids: [doc_coffee_en]
tags: [travel, food]
created_at: 2026-05-09T12:00:00Z
---

# Coffee conversation

## Source material
…

## Bilingual reading
| English | Italian |
|---|---|
| I would like a coffee | Vorrei un caffè |

## Vocabulary
- **caffè** _m._ — coffee
- **bicchiere** _m._ — glass

## Grammar focus
- **Polite conditional ("vorrei")** — used to soften requests…

## Exercises
1. Translate to Italian: "I would like a glass of water."
2. Cloze: "_____ un caffè, per favore."

## Review cards
- Front: coffee → Back: caffè
```

### `Exercise`
| field | notes |
|---|---|
| `id` | `ex_<slug>` |
| `type` | enum (see below) |
| `source_language`, `target_language` | |
| `prompt` | |
| `expected_answer` | nullable for free-write |
| `acceptable_answers` | list, used by deterministic grader |
| `hints` | |
| `explanation` | shown after grading |
| `difficulty` | `1`–`5` |
| `skill_tags` | |
| `generated_from` | `{unit_id, vocab_ids, grammar_ids, doc_id}` |
| `grading_mode` | `deterministic` / `llm_rubric` / `hybrid` |

`type ∈ { multiple_choice, cloze, translate_a_to_b, translate_b_to_a, free_write, sentence_ordering, match_pairs, morphology_parse, listening_dictation, speaking_prompt, minimal_pair }`

### `ExerciseAttempt`
| field | notes |
|---|---|
| `id` | |
| `exercise_id` | |
| `learner_id` | |
| `answer` | |
| `correct` | bool |
| `score` | 0..1 |
| `feedback` | string |
| `attempted_at` | |

### `Flashcard`
| field | notes |
|---|---|
| `id` | `card_<slug>` |
| `front`, `back` | |
| `source_language`, `target_language` | |
| `direction` | `recognition` (target → source) / `production` (source → target) / `cloze` |
| `card_type` | `vocab` / `sentence` / `grammar` / `cloze` |
| `vocabulary_item_id` | optional |
| `sentence_id` | optional |
| `mnemonic` | optional |
| `examples` | list of strings |
| `audio_ref`, `image_ref` | optional |
| `due_at` | datetime |
| `interval` | days |
| `ease_factor` | float, ≥1.3 |
| `repetitions` | int |
| `lapses` | int (added beyond upstream SM-2 to ease FSRS migration) |
| `needs_extra_review` | bool (SM-2 q==3 same-day flag) |

### `ReviewEvent`
| field | notes |
|---|---|
| `card_id` | |
| `rating` | 0..5 |
| `reviewed_at` | |
| `interval_before`, `interval_after` | |
| `ease_before`, `ease_after` | |

### `LearnerProfile`
| field | notes |
|---|---|
| `id` | typically `default` for single-user MVP |
| `display_name` | |
| `native_languages` | list of codes |
| `known_languages` | list of `(code, cefr_level)` |
| `target_languages` | list of `(code, cefr_level_goal)` |
| `preferred_support_language` | code |
| `ui_language` | code |
| `correction_style` | `gentle` / `direct` |
| `interests` | tags |
| `last_active_pair` | `(source, target)` |
| `created_at`, `updated_at` | |

### `TutorSession`
| field | notes |
|---|---|
| `id` | |
| `learner_id` | |
| `language_pair` | |
| `messages` | list of `Message` |
| `tool_calls` | append-only log: `{tool, args, result, started_at, finished_at}` |
| `current_unit_id` | optional |

## Provenance

Every model entity that can be model-generated has a `provenance` field:

```python
class Provenance(BaseModel):
    generated: bool = False
    model: str | None = None
    source_doc_id: str | None = None
    confidence: Literal["high", "medium", "low", "uncertain"] | None = None
    created_at: datetime
```

This makes it trivial to (a) display "AI-generated" tags in the UI, (b) regenerate just the low-confidence items, and (c) audit later.
