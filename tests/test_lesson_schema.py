from pathlib import Path

import frontmatter

from lingua_agent.lesson.markdown_export import render_unit_markdown, write_unit
from lingua_agent.lesson.validators import LessonValidationError, validate_unit
from lingua_agent.models import LessonUnit, ReadingPair


def _unit(target: str = "it", **overrides) -> LessonUnit:
    base = dict(
        id="unit_test",
        title="Test unit",
        source_language="en",
        target_language=target,
        support_language="en",
        cefr_level="A1",
        bilingual_reading=[ReadingPair(source="I would like a coffee.", target="Vorrei un caffè.")],
        summary="A small test.",
    )
    base.update(overrides)
    return LessonUnit(**base)


def test_render_includes_title_and_summary():
    md = render_unit_markdown(_unit())
    assert "# Test unit" in md
    assert "A small test." in md
    assert "## Bilingual reading" in md


def test_render_wraps_rtl_target():
    unit = _unit(target="fa", bilingual_reading=[
        ReadingPair(source="My friend goes to the university.", target="دوست من به دانشگاه می‌رود."),
    ])
    md = render_unit_markdown(unit)
    assert 'dir="rtl"' in md
    # The Persian text is preserved verbatim, not transliterated.
    assert "دوست من به دانشگاه" in md


def test_render_no_rtl_for_italian():
    md = render_unit_markdown(_unit(target="it"))
    assert "dir=\"rtl\"" not in md


def test_write_unit_roundtrip(tmp_path: Path):
    unit = _unit()
    path = write_unit(unit, content_dir=tmp_path)
    assert path.exists()
    post = frontmatter.load(path)
    assert post.metadata["id"] == unit.id
    assert post.metadata["target_language"] == "it"
    assert "# Test unit" in post.content


def test_validator_rejects_same_source_and_target():
    unit = _unit()
    unit.target_language = "en"
    import pytest
    with pytest.raises(LessonValidationError):
        validate_unit(unit)
