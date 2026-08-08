---
id: showcase-fa-diglot-04
title: Diglot-weave preview — The old man and the river
kind: diglot_weave
phase: 6e
source_language: en
target_language: fa
support_language: en
cefr_level: A2
tags: [diglot-weave, comprehensible-input, substitution, preview]
book_id: the_old_man_and_the_river
saturation_curve: [0.10, 0.35, 0.60]
---

# Diglot-weave preview — The old man and the river

## Summary

A preview of the **Phase 6e diglot-weave reader** (idea credit: Maria Molina).
The reader starts in English and **progressively substitutes** Persian words as
you advance — forcing context-based guessing rather than click-to-translate.
Below, the same original passage is shown at three saturation levels from the
`saturation_curve`. Concrete, high-context nouns are substituted first; verbs
and abstractions last. Every substitution shows its gloss on first appearance
(the reader does this on hover).

> This is an illustrative hand-weave. The real pipeline is
> `ingest_book_for_diglot(source_text, target_language, profile, saturation_curve)`,
> which chooses substitutions from the learner's SRS history and CEFR frequency
> lists, and logs them per book so a word stays consistent across chapters.

## Wave 0 — original source (0%)

> The old man lived in a small house near the river. Every morning he walked to
> the market to buy bread and tea. His friend, the baker, always gave him a warm
> smile.

## Wave 1 — ~10% (concrete nouns)

> The old man lived in a small **خانه** _(house)_ near the river. Every morning
> he walked to the market to buy **نان** _(bread)_ and **چای** _(tea)_. His
> friend, the baker, always gave him a warm smile.

## Wave 2 — ~35% (more nouns)

> The old **مرد** _(man)_ lived in a small **خانه** near the **رودخانه**
> _(river)_. Every **صبح** _(morning)_ he walked to the **بازار** _(market)_ to
> buy **نان** and **چای**. His **دوست** _(friend)_, the baker, always gave him a
> warm **لبخند** _(smile)_.

## Wave 3 — ~60% (adjectives + verbs, as phrases)

> The **پیرمرد** _(old man)_ lived in a **کوچک** _(small)_ **خانه** near the
> **رودخانه**. Every **صبح** he **پیاده می‌رفت** _(walked)_ to the **بازار** to
> buy **نان** and **چای**. His **دوست**, the **نانوا** _(baker)_, **همیشه**
> _(always)_ gave him a **گرم** _(warm)_ **لبخند**.

## Why phrases, not bare words

Note that "old man" becomes the compound **پیرمرد** _(pirmard)_ — one word — and
"walked" becomes **پیاده می‌رفت** _(piyâde miraft)_ — a phrase. Substituting bare
tokens would produce ungrammatical Persian; the weaver substitutes **whole
phrases** so ezafe, compounds, and verb structure stay correct (see
`03_grammar_ezafe_a2_en_fa.md`). Per-language validators reject a substitution
that would break agreement.

## Substitution log (excerpt)

Persisted at `data/diglot_books/the_old_man_and_the_river/log.json` so "house →
خانه" in chapter 1 is still "house → خانه" in chapter 12:

```json
{
  "book_id": "the_old_man_and_the_river",
  "target_language": "fa",
  "saturation_curve": [0.10, 0.35, 0.60],
  "substitutions": {
    "house":   { "target": "خانه",  "translit": "khâne",  "first_wave": 1, "pos": "noun" },
    "bread":   { "target": "نان",   "translit": "nân",    "first_wave": 1, "pos": "noun" },
    "tea":     { "target": "چای",   "translit": "chây",   "first_wave": 1, "pos": "noun" },
    "man":     { "target": "مرد",   "translit": "mard",   "first_wave": 2, "pos": "noun" },
    "river":   { "target": "رودخانه","translit": "rudkhâne","first_wave": 2, "pos": "noun" },
    "morning": { "target": "صبح",   "translit": "sobh",   "first_wave": 2, "pos": "noun" },
    "market":  { "target": "بازار", "translit": "bâzâr",  "first_wave": 2, "pos": "noun" },
    "old man": { "target": "پیرمرد","translit": "pirmard","first_wave": 3, "pos": "compound_noun" },
    "walked":  { "target": "پیاده می‌رفت","translit": "piyâde miraft","first_wave": 3, "pos": "verb_phrase" }
  }
}
```

## Vocabulary (harvested from the weave)

<div dir="rtl">

- **خانه** _(khâne)_ — house
- **نان** _(nân)_ — bread
- **رودخانه** _(rudkhâne)_ — river
- **بازار** _(bâzâr)_ — market, bazaar
- **پیرمرد** _(pirmard)_ — old man _(compound: پیر "old" + مرد "man")_
- **نانوا** _(nânvâ)_ — baker _(نان "bread" + وا)_
- **لبخند** _(labkhand)_ — smile
- **همیشه** _(hamishe)_ — always

</div>

## Exercises

1. **[free_write]** After Wave 3, retell the passage in English — how much did
   the Persian carry without a lookup?
2. **[multiple_choice]** In Wave 2, you meet **بازار** without a gloss the second
   time. It means:
    - _choices:_ market, morning, river, smile
    - _expected:_ market
3. **[cloze]** From the log, chapter 12 must still render "bread" as ____.
    - _expected:_ <span dir="rtl">نان</span>

## Review cards

- house → <span dir="rtl">خانه (khâne)</span>
- old man → <span dir="rtl">پیرمرد (pirmard)</span>
- always → <span dir="rtl">همیشه (hamishe)</span>
- baker → <span dir="rtl">نانوا (nânvâ)</span>
