# Example lessons — inspiration gallery

Hand-authored, fully-worked lesson units for **Farsi** and **Russian**, one per
_kind_ of lesson the project builds toward. These are design targets and
inspiration pieces — what a finished lesson should feel like — not pipeline
output. They mirror the export format in
[`lesson/markdown_export.py`](../../src/lingua_agent/lesson/markdown_export.py):
YAML frontmatter is the schema, the body is human-readable, and RTL
(target-language) sections are wrapped in `<div dir="rtl">` / `<span dir="rtl">`
so they render correctly in any markdown viewer.

Each file carries two extra frontmatter keys beyond the `LessonUnit` schema:

- `kind:` — the pedagogical shape (see the table).
- `phase:` — `shipped` if the current ingest pipeline can already produce this
  shape, or the roadmap phase that introduces it.

## The five kinds

| # | `kind` | What it showcases | Phase |
|---|--------|-------------------|-------|
| 1 | `bilingual_narrative` | A short A1 text with parallel source/target reading, mined vocab, one grammar focus, a few exercises, and review cards — the core ingest output. | shipped |
| 2 | `dialogue` | An Assimil-style conversation, a **register** contrast (Persian کتابی↔محاوره‌ای; Russian ты↔вы), and a **second-wave review** hook (`next_revisit_at`). | 6d |
| 3 | `grammar_focus` | A whole unit built around one signature feature — the Persian **ezafe**, Russian **verbal aspect**. | shipped |
| 4 | `diglot_weave` / `sentence_rep` | Forward-looking previews: progressive target-word **substitution** across saturation waves (Farsi, Phase 6e), and a **Glossika-style rep batch** that reuses known vocab + 1–2 new items (Russian, Phase 6d). | 6e / 6d |
| 5 | `authentic_text` | A real, public-domain cultural text — Saʿdi, Pushkin — with literal + literary translation for advanced comprehensible input. | shipped |

## Contents

```
farsi/
  01_narrative_a1_fa_en.md        bilingual_narrative — first day at university
  02_dialogue_a2_fa_en.md         dialogue           — café; formal ↔ colloquial register
  03_grammar_ezafe_a2_en_fa.md    grammar_focus      — the ezafe linker
  04_diglot_weave_preview_en_fa.md diglot_weave      — progressive substitution (Phase 6e)
  05_poetry_c1_fa_en.md           authentic_text     — Saʿdi, Bani Adam
russian/
  01_narrative_a1_ru_en.md        bilingual_narrative — yesterday & today
  02_dialogue_a2_ru_en.md         dialogue           — café; ты ↔ вы
  03_grammar_aspect_b1_ru_en.md   grammar_focus      — imperfective ↔ perfective
  04_sentence_rep_preview_ru_en.md sentence_rep      — Glossika-style rep batch (Phase 6d)
  05_poetry_b2_ru_en.md           authentic_text     — Pushkin, Я вас любил
```

## Copyright

Every authentic text here is public domain: Saʿdi's *Golestan* (13th c.) and
Pushkin's *Я вас любил* (1829). Translations are original. The diglot-weave
preview uses an original English passage. Nothing here reproduces
copyrighted teaching material — consistent with the roadmap's copyright posture
for Phases 6c–6e (derivative work from the learner's own legitimately-owned
sources, never redistributed).
