"""Streamlit playground.

Run via the CLI: `lingua-agent playground` (which exec's `streamlit run` on
this file). Manually: `streamlit run -m lingua_agent.playground.app`.

This is a single-file iteration UI on top of the existing core. It is
explicitly NOT the production UI (see docs/clients.md for Phase 8).
"""

from __future__ import annotations

import json

import streamlit as st

from lingua_agent.ai import get_provider
from lingua_agent.config import Settings
from lingua_agent.ingest import ingest_text
from lingua_agent.languages import get_language, list_languages
from lingua_agent.lesson.markdown_export import read_unit
from lingua_agent.models import Flashcard, LearnerProfile, LessonUnit, ReviewEvent
from lingua_agent.srs import SM2Scheduler, export_cards_csv
from lingua_agent.storage import JsonRepository
from lingua_agent.tutor.agent import reply as tutor_reply
from lingua_agent.tutor.session import open_session


# ---- page setup -----------------------------------------------------------

st.set_page_config(
    page_title="lingua-agent playground",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource
def _settings_singleton() -> Settings:
    s = Settings.load()
    s.ensure_dirs()
    return s


SETTINGS = _settings_singleton()
LANGS = list_languages()
LANG_OPTIONS = {f"{lang.code} — {lang.name}": lang.code for lang in LANGS}


def _is_rtl(code: str) -> bool:
    try:
        return get_language(code).direction.value == "rtl"
    except KeyError:
        return False


def _rtl_md(text: str, code: str) -> str:
    if _is_rtl(code):
        # Streamlit renders unsafe_allow_html=True markdown; wrap RTL text so
        # bidi behaves and Persian punctuation renders the right way.
        return f'<div dir="rtl" style="text-align: right;">{text}</div>'
    return text


# ---- repositories ---------------------------------------------------------

def _repo(bucket: str, model):
    return JsonRepository(SETTINGS.data_dir, bucket, model)


def _profile() -> LearnerProfile:
    path = SETTINGS.data_dir / "learner_profile.json"
    if path.exists():
        return LearnerProfile.model_validate(json.loads(path.read_text("utf-8")))
    return LearnerProfile()


# ---- sidebar --------------------------------------------------------------

with st.sidebar:
    st.title("📚 lingua-agent")
    st.caption(f"v0.1.0 · provider: **{SETTINGS.ai_provider}**")
    st.markdown(
        f"**Data dir:** `{SETTINGS.data_dir}`  \n**Content dir:** `{SETTINGS.content_dir}`"
    )

    st.subheader("Active language pair")
    src_label = st.selectbox("Source", list(LANG_OPTIONS.keys()), index=0, key="src_label")
    tgt_label = st.selectbox("Target", list(LANG_OPTIONS.keys()), index=2, key="tgt_label")
    sup_label = st.selectbox("Support (optional)", ["—"] + list(LANG_OPTIONS.keys()),
                              index=1, key="sup_label")
    src_code = LANG_OPTIONS[src_label]
    tgt_code = LANG_OPTIONS[tgt_label]
    sup_code = LANG_OPTIONS[sup_label] if sup_label != "—" else None
    if src_code == tgt_code:
        st.warning("source and target must differ")

    if _is_rtl(tgt_code):
        st.info("Target is RTL — rendering will flip direction in the lesson and review panes.")

    st.markdown("---")
    st.markdown(
        "**Not the production UI.** This is a playground. The real product is the "
        "FastAPI + React PWA planned in Phase 8 — see `docs/clients.md`."
    )


tab_ingest, tab_lessons, tab_review, tab_tutor = st.tabs(
    ["📥 Ingest", "📖 Lessons", "🃏 Review", "🤖 Tutor"]
)


# ---- INGEST tab -----------------------------------------------------------

with tab_ingest:
    st.header("Ingest custom material")
    st.caption(
        "Paste any text, choose source/target, click Ingest. The pipeline "
        "produces a lesson unit, vocabulary, grammar notes, exercises, and "
        f"flashcards using the **{SETTINGS.ai_provider}** provider."
    )
    title = st.text_input("Title", value="Untitled lesson")
    level = st.selectbox("CEFR level", [None, "A1", "A2", "B1", "B2", "C1", "C2"], index=1)
    text = st.text_area(
        "Material",
        height=200,
        placeholder="I would like a coffee and a glass of water. Where is the train station?",
    )
    if st.button("Ingest", type="primary", disabled=not text.strip() or src_code == tgt_code):
        with st.spinner(f"Generating lesson via {SETTINGS.ai_provider}…"):
            try:
                provider = get_provider(SETTINGS.ai_provider)
                result = ingest_text(
                    text=text,
                    title=title,
                    source_language=src_code,
                    target_language=tgt_code,
                    support_language=sup_code,
                    cefr_level=level,
                    provider=provider,
                    settings=SETTINGS,
                )
            except Exception as exc:
                st.error(f"Ingest failed: {exc}")
            else:
                st.success(f"Created lesson `{result.unit.id}`")
                cols = st.columns(4)
                cols[0].metric("Vocabulary", len(result.vocabulary))
                cols[1].metric("Grammar", len(result.grammar))
                cols[2].metric("Exercises", len(result.exercises))
                cols[3].metric("Flashcards", len(result.flashcards))

                if result.unit.bilingual_reading:
                    st.subheader("Bilingual reading")
                    for pair in result.unit.bilingual_reading:
                        c1, c2 = st.columns(2)
                        c1.markdown(pair.source)
                        c2.markdown(_rtl_md(pair.target, tgt_code), unsafe_allow_html=True)

                if result.vocabulary:
                    st.subheader("Vocabulary")
                    for v in result.vocabulary:
                        translations = ", ".join(v.translations.get(tgt_code, [])) or "—"
                        st.markdown(_rtl_md(
                            f"- **{v.lemma}** _({v.pos or '?'})_ — {translations}",
                            tgt_code,
                        ), unsafe_allow_html=True)

                if result.unit_path:
                    st.caption(f"Markdown: `{result.unit_path}`")


# ---- LESSONS tab ----------------------------------------------------------

with tab_lessons:
    st.header("Generated lessons")
    units = _repo("lessons", LessonUnit).list()
    if not units:
        st.info("No lessons yet. Use the Ingest tab.")
    else:
        for u in sorted(units, key=lambda x: x.created_at, reverse=True):
            with st.expander(
                f"**{u.title}**  ·  {u.source_language}→{u.target_language}  ·  "
                f"{u.cefr_level or '—'}  ·  cards: {len(u.flashcard_ids)}"
            ):
                if u.summary:
                    st.markdown(_rtl_md(u.summary, u.target_language), unsafe_allow_html=True)
                if u.bilingual_reading:
                    for pair in u.bilingual_reading:
                        c1, c2 = st.columns(2)
                        c1.markdown(pair.source)
                        c2.markdown(_rtl_md(pair.target, u.target_language), unsafe_allow_html=True)
                # Show the canonical markdown file path if it exists.
                md_path = SETTINGS.content_dir / "units" / f"{u.id}.md"
                if md_path.exists():
                    st.caption(f"`{md_path}`")
                    if st.checkbox("Show raw markdown", key=f"raw_{u.id}"):
                        meta, body = read_unit(md_path)
                        st.code(body, language="markdown")


# ---- REVIEW tab -----------------------------------------------------------

with tab_review:
    st.header("Review due cards")
    target_filter = st.checkbox(f"Filter to target = `{tgt_code}`", value=True)
    cards = _repo("flashcards", Flashcard).list()
    if target_filter:
        cards = [c for c in cards if c.target_language == tgt_code]
    sched = SM2Scheduler()
    due = sched.due(cards)

    if not due:
        st.success("No cards due. ✓")
    else:
        st.caption(f"{len(due)} due. Showing one at a time.")
        idx = st.session_state.setdefault("review_idx", 0) % len(due)
        card = due[idx]

        st.markdown(f"**Card** `{card.id}`  ·  interval: {card.interval}d  ·  "
                    f"ease: {card.ease_factor:.2f}  ·  reps: {card.repetitions}  ·  lapses: {card.lapses}")

        col_front, col_back = st.columns(2)
        col_front.markdown("**Front**")
        col_front.markdown(_rtl_md(card.front, card.source_language), unsafe_allow_html=True)
        if st.session_state.get("review_show_back", False):
            col_back.markdown("**Back**")
            col_back.markdown(_rtl_md(card.back, card.target_language), unsafe_allow_html=True)
        else:
            col_back.markdown("&nbsp;")
            if col_back.button("Show back"):
                st.session_state["review_show_back"] = True
                st.rerun()

        if st.session_state.get("review_show_back", False):
            st.markdown("**Rate recall:**")
            qcols = st.columns(6)
            labels = ["0 blackout", "1 wrong", "2 hard miss", "3 hard but right", "4 right", "5 perfect"]
            for q, label in enumerate(labels):
                if qcols[q].button(label, key=f"q_{q}_{card.id}"):
                    card, event = sched.update(card, q)
                    _repo("flashcards", Flashcard).save(card)
                    _repo("reviews", ReviewEvent).save(event)
                    st.session_state["review_show_back"] = False
                    st.session_state["review_idx"] = (idx + 1) % max(1, len(due))
                    st.rerun()

    st.markdown("---")
    if st.button("Export current target to Anki CSV"):
        out = SETTINGS.content_dir / "exports" / f"{tgt_code}.csv"
        export_cards_csv([c for c in _repo("flashcards", Flashcard).list() if c.target_language == tgt_code], out)
        st.success(f"Exported → `{out}`")


# ---- TUTOR tab ------------------------------------------------------------

with tab_tutor:
    st.header("Tutor chat")
    st.caption(
        f"Talking to **{SETTINGS.ai_provider}** as the tutor. "
        f"With provider=mock you'll see canned responses; switch via env vars to reach "
        f"OpenAI / Gemma / Qwen / Ollama (see docs/providers.md)."
    )

    if "tutor_session_id" not in st.session_state:
        sess = open_session(source=src_code, target=tgt_code, support=sup_code, settings=SETTINGS)
        st.session_state["tutor_session_id"] = sess.id
        st.session_state["tutor_session"] = sess

    sess = st.session_state["tutor_session"]
    profile = _profile()

    for msg in sess.messages:
        with st.chat_message(msg.role):
            st.markdown(_rtl_md(msg.content, tgt_code if msg.role == "assistant" else src_code),
                        unsafe_allow_html=True)

    user_input = st.chat_input("Ask the tutor…")
    if user_input:
        try:
            provider = get_provider(SETTINGS.ai_provider)
            tutor_reply(session=sess, learner=profile, user_message=user_input, provider=provider)
            st.session_state["tutor_session"] = sess
            st.rerun()
        except Exception as exc:
            st.error(f"Tutor reply failed: {exc}")
