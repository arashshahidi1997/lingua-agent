# Language-pair design

`lingua-agent` is built on the abstraction _any source A → any target B_. English is one option, not the only source.

## Roles

| Field | Meaning |
|---|---|
| `source_language` | The language of the input material (`en`, `fa`, `it`, `ru`, …). |
| `target_language` | The language being learned. |
| `support_language` | Language used for explanations and metalinguistic notes. Often English, but configurable. May equal `source_language`. |
| `ui_language` | Language used by the CLI / UI strings. Independent of the others. |

## Initial language registry

| Code | Name | Script | Direction | Transliteration | Notes |
|---|---|---|---|---|---|
| `en` | English | Latin | ltr | n/a | Reference / common support language. |
| `it` | Italian | Latin | ltr | n/a | Romance, gendered nouns, rich verb conjugation. |
| `ru` | Russian | Cyrillic | ltr | optional | Six cases, aspect, mobile stress. |
| `fa` | Persian (Farsi) | Arabic | **rtl** | optional | Ezafe construction, light verbs, no grammatical gender, formal/colloquial diglossia. |
| `de` | German | Latin | ltr | n/a | Three genders, four cases, V2 word order, separable verbs, capitalised nouns. |
| `nl` | Dutch | Latin | ltr | n/a | Two genders (de/het), no case marking, V2 word order, separable verbs. Closely related to German with simpler morphology. |

## Per-pair concerns

### English ↔ Italian
- Cognate density: huge. Surface heavy false-friend list (`libreria` ≠ "library").
- Articles + gender agreement.
- Verb conjugation (regular -are/-ere/-ire + irregulars). Subjunctive comes early conceptually.
- Pronunciation: stress placement, double consonants.

### English ↔ Russian
- Script switch: Cyrillic. Transliteration is a temporary scaffold, not a substitute.
- Six-case system: nominative, genitive, dative, accusative, instrumental, prepositional.
- Verbal aspect (perfective ↔ imperfective) — every verb taught as a pair.
- Free-ish word order driven by case + information structure.
- Mobile stress; vowel reduction depends on stress.

### English ↔ Persian (Farsi)
- Script switch: Perso-Arabic; right-to-left.
- **Ezafe** (`-e` / `-ye`) connects nouns to modifiers; usually unwritten in informal text.
- **Light verbs** dominate the verbal system (`kar kardan` "to do work" = "to work").
- No grammatical gender. Verb agreement is by person/number only.
- Postpositional accusative marker `rā` (`را`) for definite direct objects.
- Strong **formal vs colloquial Persian** divergence — vocabulary, pronouns, verb endings shift. Lessons must declare register explicitly.
- Transliteration is opt-in; default lessons use Persian script throughout.

### Italian ↔ Persian
- Avoid routing through English where possible. The contrastive map is short:
  - Italian noun gender ↔ Persian no gender. Persian needs no agreement; Italian needs both.
  - Italian articles ↔ Persian indefinite `yek` / definite `rā`.
  - Italian preposition+article fusion ↔ Persian preposition + ezafe.
- Use English as `support_language` only when the contrast is hard to convey directly.

### Russian ↔ Persian
- Two foreign scripts in one card; render direction per-side correctly.
- Russian cases ↔ Persian word-order + adpositions. Map `genitive` to ezafe-noun chains; map `instrumental` to `bā` ("with"); `dative` to `be` ("to") + word order.
- Aspect: Russian perfective/imperfective pairs map roughly to Persian simple-past / past-progressive distinctions, but the grammatical system is different in kind, not just degree. Teach as analogy with caveats.

### Italian ↔ Russian
- Both gendered, both inflectional. Map Italian agreement chains onto Russian case+gender+number agreement; the *what to track* is similar, the *how* is different.
- Italian tense system is rich on the past axis (passato prossimo, imperfetto, trapassato, …); Russian collapses much of it into aspect on a smaller tense set.

### English ↔ German
- Three genders (`der/die/das`); learners must memorise gender with each noun.
- Four cases (nominative / accusative / dative / genitive). Articles, adjectives, and pronouns inflect.
- **V2 word order**: the finite verb is the second constituent in main clauses; subordinate clauses send the verb to the end.
- **Separable verbs** (`aufstehen` → `Ich stehe auf`). Always teach both halves and the position rule together.
- Compound nouns (`Geschwindigkeitsbegrenzung`); the gender comes from the last component.
- All nouns capitalised — purely orthographic, but easy to enforce in graders.

### English ↔ Dutch
- Two genders (`de` for common, `het` for neuter). No case marking on nouns/articles.
- V2 word order, like German. Subordinate clauses also push the verb to the end.
- Separable verbs (`opstaan` → `Ik sta op`).
- Strong cognate pull with both English and German — surface false friends (`huren` ≠ "horror"; it's "hire/rent").
- Diminutive `-je` is productive and changes nuance (`biertje` is the friendly "small beer").

### German ↔ Dutch
- Mostly close cognates; the trap is the gender system mismatch (German 3-way → Dutch 2-way) and the loss of cases in Dutch.
- Verb position is essentially identical (V2 main, verb-final subordinate).
- Useful as a contrastive pair for learners who already know one and want to bootstrap the other quickly.

## RTL policy

- Persian content is stored without bidi control characters; it is displayed RTL by adding `<div dir="rtl">…</div>` (markdown export) or `dir="rtl"` (future HTML).
- Mixed-direction lines (Persian + English in the same paragraph) are kept in two separate spans rather than relying on bidi heuristics.
- The CLI prints Persian inline; modern terminals handle bidi acceptably for short strings.

## Transliteration policy

- Optional and labelled `approximate: true`.
- Persian uses a relaxed UN/ALA-LC-flavoured romanization; Russian uses ISO 9 or BGN/PCGN as configured.
- Transliteration is a learning aid, not a storage format. Cards always include the original script.

## Direct-pair vs English-as-support

When a learner studies Italian↔Persian, the default is direct: prompts and explanations use Italian and Persian only, with English suppressed. The learner can flip a per-session setting `support_language=en` to bring English in for hard contrasts. This decision lives on `LearnerProfile` and is overridable per session.
