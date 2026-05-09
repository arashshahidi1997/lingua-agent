from pathlib import Path

from typer.testing import CliRunner

from lingua_agent.cli import app

runner = CliRunner()


def test_languages_list_includes_persian():
    result = runner.invoke(app, ["languages", "list"])
    assert result.exit_code == 0, result.stdout
    assert "fa" in result.stdout
    assert "Persian" in result.stdout


def test_init_creates_data_dir(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "data").exists()
    assert (tmp_path / "data" / "learner_profile.json").exists()


def test_ingest_then_review_then_export(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    runner.invoke(app, ["init"])
    r = runner.invoke(app, [
        "ingest", "text",
        "--source", "en", "--target", "it", "--support", "en",
        "--title", "Coffee", "--text", "I would like a coffee. Where is the train station?",
        "--level", "A1",
    ])
    assert r.exit_code == 0, r.stdout

    r = runner.invoke(app, ["unit", "list"])
    assert r.exit_code == 0
    assert "Coffee" in r.stdout

    r = runner.invoke(app, ["review", "due", "--target", "it"])
    assert r.exit_code == 0
    # New cards are due immediately by default.
    assert "Due cards" in r.stdout or "No cards due" in r.stdout

    out = tmp_path / "italian.csv"
    r = runner.invoke(app, ["export", "anki", "--target", "it", "--output", str(out)])
    assert r.exit_code == 0, r.stdout
    assert out.exists()
