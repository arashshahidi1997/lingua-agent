"""Prompt templates.

Each prompt is a callable rendering a string. They are deliberately verbose:
real providers want explicit JSON schemas, anti-hallucination caveats, and
language-pair context. The mock provider ignores them.
"""

from __future__ import annotations

from textwrap import dedent


def material_analysis_prompt(*, source_language: str, target_language: str, support_language: str | None,
                              level: str | None, text: str) -> str:
    return dedent(f"""
        You are analysing a piece of source-language material so a learner can study it.

        source_language: {source_language}
        target_language: {target_language}
        support_language: {support_language or 'none'}
        target CEFR level: {level or 'unspecified'}

        Material (do not modify; do not invent additional content):
        ---
        {text}
        ---

        Return JSON with: summary, themes (list), suitable_for_levels (list).
    """).strip()


def vocabulary_extraction_prompt(*, source_language: str, target_language: str, level: str | None, text: str) -> str:
    return dedent(f"""
        Extract vocabulary the learner of {target_language} (level: {level or 'unspecified'}) should learn from the
        following {source_language} text. For each item include lemma, surface, translations into {target_language},
        part of speech, gender if applicable, an example sentence quoting from the text, and CEFR level if known.

        Mark uncertainty with confidence: "uncertain". Do not invent definitions.

        Text:
        ---
        {text}
        ---

        Return JSON: {{"items": [...]}}
    """).strip()


def grammar_extraction_prompt(*, source_language: str, target_language: str, level: str | None, text: str) -> str:
    return dedent(f"""
        Identify the most useful grammar points exemplified in this {source_language} text for a learner of
        {target_language} at level {level or 'unspecified'}. Cite the exact sentence(s) as evidence; do not invent.

        Text:
        ---
        {text}
        ---

        Return JSON: {{"points": [{{"name": "...", "summary": "...", "evidence": ["...","..."]}}]}}
    """).strip()


def lesson_generation_prompt(*, source_language: str, target_language: str, support_language: str | None,
                              level: str | None, title: str, text: str) -> str:
    return dedent(f"""
        Build a self-contained lesson titled {title!r} for a learner whose target language is {target_language},
        explained in {support_language or target_language}, at CEFR level {level or 'A1'}.

        Source material ({source_language}):
        ---
        {text}
        ---

        Return JSON with: bilingual_reading (list of source/target pairs), summary.
        Translate naturally; mark provenance.generated=true on every translation.
        For Persian content, preserve original script. Transliteration is optional.
    """).strip()


def exercise_generation_prompt(*, source_language: str, target_language: str, vocab_items: list[str],
                                grammar_points: list[str], type: str, difficulty: int) -> str:
    return dedent(f"""
        Generate a {type} exercise (difficulty {difficulty}/5) for a learner moving from {source_language}
        to {target_language}. Use these vocabulary items: {vocab_items}. Use these grammar points: {grammar_points}.

        Return JSON: {{"prompt": "...", "expected_answer": "...", "acceptable_answers": [...], "choices": [...],
        "hints": [...], "explanation": "..."}}.
    """).strip()


def answer_grading_prompt(*, source_language: str, target_language: str, prompt: str, expected: str | None,
                           answer: str) -> str:
    return dedent(f"""
        Grade this learner answer for a {source_language}→{target_language} exercise.

        Exercise prompt: {prompt}
        Expected answer: {expected or '(none — judge by rubric)'}
        Learner answer: {answer}

        Return JSON: {{"correct": bool, "score": float (0..1), "feedback": "..."}}.
    """).strip()


def mistake_explanation_prompt(*, source_language: str, target_language: str, support_language: str | None,
                                answer: str, expected: str) -> str:
    return dedent(f"""
        Explain in {support_language or source_language} why "{answer}" is incorrect for the {target_language}
        translation/answer "{expected}". Be brief, concrete, pedagogical. Cite the relevant grammar rule by name
        if applicable. Do not invent rules.
    """).strip()


def mnemonic_generation_prompt(*, target_word: str, target_language: str, native_language: str, meaning: str) -> str:
    return dedent(f"""
        Build a keyword mnemonic for the {target_language} word "{target_word}" (meaning: "{meaning}") for a
        speaker of {native_language}. Method (after Ellis & Beaton 1993; see also arXiv:2305.10436):
        1) Find a {native_language} word that sounds like "{target_word}".
        2) Write one vivid sentence in {native_language} that links that word to "{meaning}".

        Return JSON: {{"keyword": "...", "linking_sentence": "..."}}.
    """).strip()


def tutor_system_prompt(*, source_language: str, target_language: str, support_language: str | None,
                         learner_summary: str, due_card_count: int, current_unit_title: str | None) -> str:
    return dedent(f"""
        You are a language tutor working with a learner studying {target_language} from {source_language}.
        Use {support_language or source_language} for explanations; use {target_language} for examples and
        practice. For Persian, prefer original script; transliteration only on request. Mark uncertainty.
        Prefer calling a tool (generate_exercise, grade_exercise_attempt, list_due_cards, add_flashcard, ...)
        over a long monologue.

        Learner: {learner_summary}
        Due cards: {due_card_count}
        Current unit: {current_unit_title or 'none'}
    """).strip()
