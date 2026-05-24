"""Tests for the RcloneDriveProvider — mocks subprocess, no real rclone call."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from lingua_agent.materials import MaterialsError
from lingua_agent.materials.rclone_drive import RcloneDriveProvider


def _completed(returncode: int = 0, stdout: str | bytes = "", stderr: str = ""):
    """Build a fake subprocess.CompletedProcess."""
    class R:
        def __init__(self):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr
    return R()


def test_is_available_true_when_lsf_succeeds():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    with patch("subprocess.run", return_value=_completed(0, "foo\n", "")):
        assert p.is_available()


def test_is_available_false_when_rclone_missing():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin=None)
    assert not p.is_available()


def test_is_available_false_on_nonzero_exit():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    with patch("subprocess.run", return_value=_completed(1, "", "bad remote")):
        assert not p.is_available()


def test_list_parses_lsjson(monkeypatch):
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    sample = json.dumps([
        {"Name": "de", "IsDir": True, "Size": -1},
        {"Name": "notes.docx", "IsDir": False, "Size": 4096, "MimeType":
         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        {"Name": ".hidden", "IsDir": False, "Size": 1},  # should be filtered
    ])
    with patch("subprocess.run", return_value=_completed(0, sample, "")):
        entries = p.list("")
    names = [e.name for e in entries]
    assert names == ["de", "notes.docx"]  # dotfile hidden, folder first


def test_list_propagates_subdir_path(monkeypatch):
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    sample = json.dumps([{"Name": "01.mp3", "IsDir": False, "Size": 1000}])
    with patch("subprocess.run", return_value=_completed(0, sample, "")):
        entries = p.list("de/pimsleur/l1/audio")
    assert entries[0].path == "de/pimsleur/l1/audio/01.mp3"


def test_list_raises_on_subprocess_error():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    with patch("subprocess.run", return_value=_completed(1, "", "directory not found")):
        with pytest.raises(MaterialsError) as exc:
            p.list("does_not_exist")
    assert "directory not found" in str(exc.value)


def test_read_returns_stdout_bytes():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    with patch("subprocess.run", return_value=_completed(0, b"hello drive", "")):
        out = p.read("en/notes/vocabulary.txt")
    assert out == b"hello drive"


def test_read_root_raises():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    with pytest.raises(MaterialsError):
        p.read("")


def test_metadata_finds_entry_in_parent_listing():
    p = RcloneDriveProvider("drive", "gdrive:3-Language", rclone_bin="/bin/true")
    sample = json.dumps([
        {"Name": "foo.txt", "IsDir": False, "Size": 10},
        {"Name": "bar.txt", "IsDir": False, "Size": 20},
    ])
    with patch("subprocess.run", return_value=_completed(0, sample, "")):
        e = p.metadata("subdir/bar.txt")
    assert e.name == "bar.txt"
    assert e.size_bytes == 20
