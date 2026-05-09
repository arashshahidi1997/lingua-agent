import csv
from pathlib import Path

from lingua_agent.ai import MockProvider
from lingua_agent.config import Settings
from lingua_agent.ingest import ingest_text
from lingua_agent.lesson.markdown_export import read_unit
from lingua_agent.models import Flashcard, LessonUnit
from lingua_agent.srs import export_cards_csv
from lingua_agent.storage import JsonRepository


def test_pipeline_creates_all_artifacts(tmp_settings: Settings):
    result = ingest_text(
        text="I would like a coffee and a glass of water. Where is the train station?",
        title="Coffee conversation",
        source_language="en",
        target_language="it",
        support_language="en",
        cefr_level="A1",
        provider=MockProvider(),
        settings=tmp_settings,
    )
    assert result.document.id.startswith("doc_")
    assert result.unit.id.startswith("unit_")
    assert len(result.vocabulary) > 0
    assert len(result.exercises) >= 3
    assert len(result.flashcards) > 0
    assert result.unit.bilingual_reading
    # All flashcards have provenance marked as model-generated.
    assert all(c.provenance.generated for c in result.flashcards)


def test_pipeline_persists_lesson_to_markdown(tmp_settings: Settings):
    result = ingest_text(
        text="My friend is going to the university today. She studies biology.",
        title="University day",
        source_language="en",
        target_language="fa",
        support_language="en",
        cefr_level="A1",
        provider=MockProvider(),
        settings=tmp_settings,
    )
    assert result.unit_path is not None
    md_path = Path(result.unit_path)
    assert md_path.exists()
    meta, body = read_unit(md_path)
    assert meta["target_language"] == "fa"
    assert "## Bilingual reading" in body
    # RTL marker is present for Persian target.
    assert 'dir="rtl"' in body


def test_pipeline_persian_text_not_corrupted(tmp_settings: Settings):
    persian_input = "دوست من امروز به دانشگاه می‌رود."
    result = ingest_text(
        text=persian_input, title="Persian source",
        source_language="fa", target_language="en", support_language="en",
        provider=MockProvider(), settings=tmp_settings,
    )
    # The original Persian text must round-trip exactly through the Document.
    assert result.document.text == persian_input
    # And should be present verbatim in the bilingual reading.
    sources = [pair.source for pair in result.unit.bilingual_reading]
    assert any("دوست من" in s for s in sources)


def test_ingest_is_idempotent_on_same_input(tmp_settings: Settings):
    kwargs = dict(
        text="Yesterday I read a book.", title="Past tense",
        source_language="en", target_language="ru", support_language="en",
        provider=MockProvider(), settings=tmp_settings,
    )
    a = ingest_text(**kwargs)
    b = ingest_text(**kwargs)
    assert a.unit.id == b.unit.id  # hash-based IDs
    assert a.document.id == b.document.id


def test_repositories_persist_pipeline_artifacts(tmp_settings: Settings):
    ingest_text(
        text="Vorrei un caffè e un bicchiere d'acqua.",
        title="Italian café",
        source_language="it", target_language="en", support_language="en",
        provider=MockProvider(), settings=tmp_settings,
    )
    units = JsonRepository(tmp_settings.data_dir, "lessons", LessonUnit).list()
    cards = JsonRepository(tmp_settings.data_dir, "flashcards", Flashcard).list()
    assert units, "expected at least one persisted lesson"
    assert cards, "expected at least one persisted flashcard"


def test_anki_csv_export_has_expected_columns(tmp_settings: Settings):
    result = ingest_text(
        text="I would like a coffee.",
        title="Tiny",
        source_language="en", target_language="it", support_language="en",
        provider=MockProvider(), settings=tmp_settings,
    )
    out = tmp_settings.content_dir / "exports" / "italian.csv"
    export_cards_csv(result.flashcards, out)
    assert out.exists()
    with out.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        rows = list(reader)
    assert "Front" in header and "Back" in header and "TargetLanguage" in header
    assert len(rows) == len(result.flashcards)
