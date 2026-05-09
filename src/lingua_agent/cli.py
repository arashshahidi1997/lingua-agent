"""Typer CLI — the proving ground for the MVP.

All subcommands operate against the in-package core; no HTTP server required.
The default AI provider is `mock`, which produces deterministic, schema-valid
content without any network call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .ai import get_provider
from .config import Settings
from .ingest import ingest_text
from .ingest.markdown import read_markdown
from .languages import list_languages
from .models import Flashcard, LearnerProfile, LessonUnit, ReviewEvent
from .models.exercises import Exercise
from .srs import SM2Scheduler, export_cards_csv
from .storage import JsonRepository
from .tutor.agent import reply as tutor_reply
from .tutor.grading import grade_attempt_deterministic
from .tutor.session import open_session

app = typer.Typer(
    name="lingua-agent",
    help="Agentic AI language-learning platform — any A → B, local-first.",
    no_args_is_help=True,
    add_completion=False,
)
languages_app = typer.Typer(help="Inspect the language registry.")
ingest_app = typer.Typer(help="Ingest custom material.")
unit_app = typer.Typer(help="Inspect generated lesson units.")
review_app = typer.Typer(help="Review SRS cards.")
export_app = typer.Typer(help="Export learning artifacts.")
tutor_app = typer.Typer(help="Tutor agent (mock in MVP).")
app.add_typer(languages_app, name="languages")
app.add_typer(ingest_app, name="ingest")
app.add_typer(unit_app, name="unit")
app.add_typer(review_app, name="review")
app.add_typer(export_app, name="export")
app.add_typer(tutor_app, name="tutor")

console = Console()


# --- shared helpers --------------------------------------------------------

def _settings() -> Settings:
    return Settings.load()


def _load_or_default_profile(s: Settings) -> LearnerProfile:
    path = s.data_dir / "learner_profile.json"
    if path.exists():
        return LearnerProfile.model_validate(json.loads(path.read_text("utf-8")))
    return LearnerProfile()


def _save_profile(s: Settings, profile: LearnerProfile) -> None:
    path = s.data_dir / "learner_profile.json"
    path.write_text(json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


# --- top-level -------------------------------------------------------------

def _print_version(value: bool) -> None:
    if value:
        console.print(f"lingua-agent {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", help="Show version and exit.",
        is_eager=True, callback=_print_version,
    ),
):
    pass


@app.command()
def init():
    """Initialise the data directory and write a default learner profile."""
    s = _settings()
    s.ensure_dirs()
    profile = _load_or_default_profile(s)
    _save_profile(s, profile)
    console.print(f"[green]Initialised[/green] data dir: {s.data_dir}")
    console.print(f"[green]Initialised[/green] content dir: {s.content_dir}")
    console.print(f"AI provider: [bold]{s.ai_provider}[/bold]")


@app.command()
def playground(
    port: int = typer.Option(8501, "--port", help="Port for the Streamlit server."),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open in browser."),
):
    """Launch the Streamlit playground UI in your browser."""
    import subprocess
    import sys
    from importlib.resources import files
    try:
        import streamlit  # noqa: F401
    except ImportError:
        console.print(
            "[red]Streamlit is not installed.[/red] Install with: "
            "[bold]pip install -e \".[playground]\"[/bold]"
        )
        raise typer.Exit(code=1)
    app_path = str(files("lingua_agent.playground").joinpath("app.py"))
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(port),
        "--server.headless", "false" if open_browser else "true",
        "--browser.gatherUsageStats", "false",
    ]
    console.print(f"[dim]→ {' '.join(cmd)}[/dim]")
    subprocess.run(cmd)


# --- languages -------------------------------------------------------------

@languages_app.command("list")
def languages_list():
    table = Table(title="Supported languages")
    for col in ("code", "name", "native", "script", "direction", "translit?"):
        table.add_column(col)
    for lang in list_languages():
        table.add_row(
            lang.code, lang.name, lang.native_name, lang.script.value,
            lang.direction.value, "yes" if lang.transliteration_supported else "—",
        )
    console.print(table)


# --- ingest ----------------------------------------------------------------

@ingest_app.command("text")
def ingest_text_cmd(
    source: str = typer.Option(..., "--source", help="Source language code."),
    target: str = typer.Option(..., "--target", help="Target language code."),
    support: Optional[str] = typer.Option(None, "--support", help="Optional support language."),
    title: str = typer.Option(..., "--title", help="Lesson title."),
    text: str = typer.Option(..., "--text", help="Material text."),
    level: Optional[str] = typer.Option(None, "--level", help="CEFR level (A1..C2)."),
):
    s = _settings()
    provider = get_provider(s.ai_provider)
    result = ingest_text(
        text=text, title=title,
        source_language=source, target_language=target, support_language=support,
        cefr_level=level, provider=provider, settings=s,
    )
    console.print(f"[green]Created[/green] lesson [bold]{result.unit.id}[/bold]")
    console.print(f"  vocabulary: {len(result.vocabulary)}")
    console.print(f"  grammar:    {len(result.grammar)}")
    console.print(f"  exercises:  {len(result.exercises)}")
    console.print(f"  flashcards: {len(result.flashcards)}")
    if result.unit_path:
        console.print(f"  markdown:   {result.unit_path}")


@ingest_app.command("file")
def ingest_file_cmd(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    source: str = typer.Option(..., "--source"),
    target: str = typer.Option(..., "--target"),
    support: Optional[str] = typer.Option(None, "--support"),
    title: Optional[str] = typer.Option(None, "--title"),
    level: Optional[str] = typer.Option(None, "--level"),
):
    if path.suffix.lower() in {".md", ".markdown"}:
        meta, body = read_markdown(path)
        text = body.strip()
        title = title or str(meta.get("title") or path.stem)
        source = str(meta.get("source_language") or source)
        target = str(meta.get("target_language") or target)
        level = level or (str(meta.get("cefr_level")) if meta.get("cefr_level") else None)
    else:
        text = path.read_text("utf-8")
        title = title or path.stem
    ingest_text_cmd(source=source, target=target, support=support, title=title, text=text, level=level)


# --- units -----------------------------------------------------------------

@unit_app.command("list")
def unit_list():
    s = _settings()
    repo = JsonRepository(s.data_dir, "lessons", LessonUnit)
    units = repo.list()
    if not units:
        console.print("[yellow]No lesson units yet.[/yellow] Try `lingua-agent ingest text ...`.")
        return
    table = Table(title="Lesson units")
    for col in ("id", "title", "source→target", "level", "cards", "exercises"):
        table.add_column(col)
    for u in units:
        table.add_row(u.id, u.title, f"{u.source_language}→{u.target_language}",
                      u.cefr_level or "—", str(len(u.flashcard_ids)), str(len(u.exercise_ids)))
    console.print(table)


@unit_app.command("show")
def unit_show(unit_id: str):
    s = _settings()
    repo = JsonRepository(s.data_dir, "lessons", LessonUnit)
    unit = repo.get(unit_id)
    if not unit:
        console.print(f"[red]No such unit:[/red] {unit_id}")
        raise typer.Exit(code=1)
    console.print_json(data=unit.model_dump(mode="json"))


# --- review ----------------------------------------------------------------

@review_app.command("due")
def review_due(
    target: Optional[str] = typer.Option(None, "--target"),
    limit: int = typer.Option(20, "--limit"),
):
    s = _settings()
    repo = JsonRepository(s.data_dir, "flashcards", Flashcard)
    cards = [c for c in repo.list() if (target is None or c.target_language == target)]
    sched = SM2Scheduler()
    due = sched.due(cards)[:limit]
    if not due:
        console.print("[green]No cards due. ✓[/green]")
        return
    table = Table(title=f"Due cards ({len(due)})")
    for col in ("id", "front", "back", "lang", "interval", "ease", "reps"):
        table.add_column(col)
    for c in due:
        table.add_row(c.id, c.front, c.back, f"{c.source_language}→{c.target_language}",
                      str(c.interval), f"{c.ease_factor:.2f}", str(c.repetitions))
    console.print(table)


@review_app.command("answer")
def review_answer(
    card_id: str = typer.Option(..., "--card-id"),
    quality: int = typer.Option(..., "--quality", min=0, max=5,
                                  help="0..5 SM-2 rating (5=perfect, 3=hard but right, 0=blackout)."),
):
    s = _settings()
    repo = JsonRepository(s.data_dir, "flashcards", Flashcard)
    review_repo = JsonRepository(s.data_dir, "reviews", ReviewEvent)
    card = repo.get(card_id)
    if not card:
        console.print(f"[red]No such card:[/red] {card_id}")
        raise typer.Exit(code=1)
    sched = SM2Scheduler()
    card, event = sched.update(card, quality)
    repo.save(card)
    review_repo.save(event)
    console.print(f"[green]Recorded[/green]: due now {card.due_at.isoformat()} "
                  f"(interval={card.interval}d, ease={card.ease_factor:.2f}, reps={card.repetitions}, lapses={card.lapses})")


# --- export ----------------------------------------------------------------

@export_app.command("anki")
def export_anki(
    target: str = typer.Option(..., "--target"),
    output: Path = typer.Option(..., "--output"),
):
    s = _settings()
    repo = JsonRepository(s.data_dir, "flashcards", Flashcard)
    cards = [c for c in repo.list() if c.target_language == target]
    if not cards:
        console.print(f"[yellow]No cards for target={target}.[/yellow]")
        raise typer.Exit(code=1)
    path = export_cards_csv(cards, output)
    console.print(f"[green]Exported[/green] {len(cards)} cards → {path}")


# --- tutor -----------------------------------------------------------------

@tutor_app.command("chat")
def tutor_chat(
    source: str = typer.Option(..., "--source"),
    target: str = typer.Option(..., "--target"),
    support: Optional[str] = typer.Option("en", "--support"),
    message: Optional[str] = typer.Option(None, "--message",
        help="Single-shot message. Omit for an interactive loop."),
):
    s = _settings()
    provider = get_provider(s.ai_provider)
    learner = _load_or_default_profile(s)
    session = open_session(source=source, target=target, support=support, settings=s)
    console.print(f"[dim]Session {session.id} (provider={provider.name})[/dim]")

    if message is not None:
        msg = tutor_reply(session=session, learner=learner, user_message=message, provider=provider)
        console.print(f"[bold]tutor:[/bold] {msg.content}")
        return

    console.print("[dim]Interactive chat. Type 'exit' to quit.[/dim]")
    while True:
        try:
            user = typer.prompt("you")
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if user.strip().lower() in {"exit", "quit", "/exit", "/quit"}:
            return
        msg = tutor_reply(session=session, learner=learner, user_message=user, provider=provider)
        console.print(f"[bold]tutor:[/bold] {msg.content}")


@tutor_app.command("grade")
def tutor_grade(
    exercise_id: str = typer.Option(..., "--exercise-id"),
    answer: str = typer.Option(..., "--answer"),
):
    """Grade a single exercise attempt deterministically."""
    s = _settings()
    repo = JsonRepository(s.data_dir, "exercises", Exercise)
    ex = repo.get(exercise_id)
    if not ex:
        console.print(f"[red]No such exercise:[/red] {exercise_id}")
        raise typer.Exit(code=1)
    result = grade_attempt_deterministic(ex, answer)
    style = "green" if result.correct else "red"
    console.print(f"[{style}]{'CORRECT' if result.correct else 'INCORRECT'}[/{style}] "
                  f"score={result.score:.2f} — {result.feedback}")


def main() -> None:  # pragma: no cover - convenience for `python -m lingua_agent.cli`
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
