"""Tests for the LocalDirProvider — uses a tmp filesystem, no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from lingua_agent.materials import MaterialsError
from lingua_agent.materials.local_dir import LocalDirProvider


@pytest.fixture
def fake_tree(tmp_path: Path) -> Path:
    """A small SSD-shaped tree: language folders + files."""
    (tmp_path / "de" / "pimsleur" / "l1" / "audio").mkdir(parents=True)
    (tmp_path / "de" / "pimsleur" / "l1" / "audio" / "01.mp3").write_bytes(b"\xff\xfb\x90\x00")  # fake mp3 header
    (tmp_path / "de" / "pimsleur" / "l1" / "audio" / "02.mp3").write_bytes(b"\xff\xfb\x90\x00")
    (tmp_path / "de" / "notes.md").write_text("# notes\n", encoding="utf-8")
    (tmp_path / "fa" / "novels").mkdir(parents=True)
    (tmp_path / "fa" / "novels" / "بار_هستی.txt").write_text("سلام", encoding="utf-8")
    (tmp_path / ".DS_Store").write_bytes(b"junk")
    (tmp_path / "._hidden").write_bytes(b"junk")
    return tmp_path


def test_is_available_true_when_root_exists(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    assert p.is_available()


def test_is_available_false_when_root_missing(tmp_path: Path):
    p = LocalDirProvider("ssd", str(tmp_path / "does_not_exist"))
    assert not p.is_available()


def test_list_root_hides_dotfiles(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    entries = p.list()
    names = {e.name for e in entries}
    assert names == {"de", "fa"}  # .DS_Store and ._hidden filtered out


def test_list_returns_folders_first_then_alphabetical(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    entries = p.list("de")
    # 'pimsleur' (dir) before 'notes.md' (file)
    assert entries[0].name == "pimsleur" and entries[0].is_dir
    assert entries[1].name == "notes.md" and not entries[1].is_dir


def test_list_deep_path(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    entries = p.list("de/pimsleur/l1/audio")
    assert {e.name for e in entries} == {"01.mp3", "02.mp3"}
    e = next(x for x in entries if x.name == "01.mp3")
    assert e.path == "de/pimsleur/l1/audio/01.mp3"
    assert e.size_bytes == 4
    assert e.mime_type == "audio/mpeg"


def test_metadata_for_file(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    meta = p.metadata("de/notes.md")
    assert meta.name == "notes.md"
    assert meta.is_dir is False
    assert meta.size_bytes == len("# notes\n")
    assert meta.mime_type in {"text/markdown", "text/x-markdown"}


def test_metadata_missing_raises(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    with pytest.raises(MaterialsError):
        p.metadata("de/nope.md")


def test_read_file_bytes(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    assert p.read("de/notes.md") == b"# notes\n"


def test_read_directory_raises(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    with pytest.raises(MaterialsError):
        p.read("de")


def test_path_escape_blocked(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    with pytest.raises(MaterialsError):
        p.list("../etc")
    with pytest.raises(MaterialsError):
        p.read("../../etc/passwd")


def test_persian_path_roundtrip(fake_tree: Path):
    p = LocalDirProvider("ssd", str(fake_tree))
    entries = p.list("fa/novels")
    assert entries[0].name == "بار_هستی.txt"
    assert p.read("fa/novels/بار_هستی.txt") == "سلام".encode("utf-8")


def test_unavailable_source_raises_on_list(tmp_path: Path):
    p = LocalDirProvider("ssd", str(tmp_path / "missing"))
    with pytest.raises(MaterialsError) as exc:
        p.list()
    assert "not available" in str(exc.value)
