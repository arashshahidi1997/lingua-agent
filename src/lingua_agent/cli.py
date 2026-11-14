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
materials_app = typer.Typer(help="Manage and browse materials sources (SSD, Drive, ...).")
voices_app = typer.Typer(help="Local text-to-speech voices (Piper).")
app.add_typer(languages_app, name="languages")
app.add_typer(ingest_app, name="ingest")
app.add_typer(unit_app, name="unit")
app.add_typer(review_app, name="review")
app.add_typer(export_app, name="export")
app.add_typer(tutor_app, name="tutor")
app.add_typer(materials_app, name="materials")
app.add_typer(voices_app, name="voices")

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


def _build_web(web_dir: Path) -> None:
    """Build the React PWA into ``web_dir/dist`` so FastAPI can serve it.

    Runs ``npm install`` (only when ``node_modules`` is missing) then
    ``npm run build``. Raises ``typer.Exit`` with a clear message when the
    toolchain or the ``web/`` directory is missing, or the build fails.
    """
    import shutil
    import subprocess

    if not (web_dir / "package.json").exists():
        console.print(
            f"[red]No web app found at {web_dir}[/red] "
            "(expected a package.json). Run from the repo root."
        )
        raise typer.Exit(code=1)
    if shutil.which("npm") is None:
        console.print(
            "[red]npm not found on PATH.[/red] Install Node.js (>=18) to build "
            "the PWA, or serve the API alone without [bold]--build[/bold]."
        )
        raise typer.Exit(code=1)

    if not (web_dir / "node_modules").exists():
        console.print("[cyan]→[/cyan] installing web dependencies (first run)…")
        if subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"], cwd=web_dir
        ).returncode != 0:
            console.print("[red]npm install failed.[/red]")
            raise typer.Exit(code=1)

    console.print("[cyan]→[/cyan] building the PWA (npm run build)…")
    if subprocess.run(["npm", "run", "build"], cwd=web_dir).returncode != 0:
        console.print("[red]web build failed.[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]✓[/green] built {web_dir / 'dist'}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host. Use 0.0.0.0 for LAN."),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev)."),
    build: bool = typer.Option(
        False, "--build",
        help="Build the React PWA into web/dist first, then serve it from this process.",
    ),
):
    """Start the FastAPI HTTP server (Phase 8 backend for the React PWA).

    With [bold]--build[/bold] this is the one-command way to run the installable
    app: it compiles the PWA into web/dist and serves both the API and the UI
    from a single origin. For "Install to Home Screen" on Android/iOS the origin
    must be HTTPS — see docs/mobile-https.md.
    """
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]uvicorn not installed.[/red] Install with: "
            "[bold]pip install -e \".[api]\"[/bold]"
        )
        raise typer.Exit(code=1)

    web_dir = Path.cwd() / "web"
    if build:
        _build_web(web_dir)

    dist = web_dir / "dist"
    if (dist / "index.html").exists():
        console.print(f"[green]✓[/green] serving PWA from {dist}")
    else:
        console.print(
            "[yellow]![/yellow] no built UI at web/dist — serving the API only. "
            "Add [bold]--build[/bold] to compile and serve the installable app."
        )
    if host == "0.0.0.0":
        console.print(
            "[yellow]![/yellow] bound to 0.0.0.0 (LAN). Plain HTTP works in a "
            "phone browser, but 'Install to Home Screen' needs HTTPS — "
            "see [bold]docs/mobile-https.md[/bold]."
        )

    console.print(f"[green]→[/green] http://{host}:{port}/api/health")
    uvicorn.run("lingua_agent.api.main:app", host=host, port=port, reload=reload)


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


# --- voices ---------------------------------------------------------------

@voices_app.command("list")
def voices_list():
    """Show which languages have a local Piper voice."""
    from .voice import piper
    s = _settings()
    table = Table(title="Local voices (Piper)")
    for col in ("language", "voice", "ready"):
        table.add_column(col)
    for lang in sorted(piper.DEFAULT_VOICES):
        model = piper.find_voice(s, lang)
        table.add_row(lang, model.stem if model else "—",
                      "[green]yes[/green]" if piper.tts_available(s, lang) else "[red]no[/red]")
    console.print(table)
    if not piper.tts_available(s, "fa") and piper.find_voice(s, "fa"):
        console.print("[yellow]Voice files found but Piper isn't installed:[/yellow] pip install piper-tts")


@voices_app.command("download")
def voices_download(
    lang: str = typer.Argument(..., help="Language code, e.g. fa."),
    voice: Optional[str] = typer.Option(None, help="Voice path in rhasspy/piper-voices, e.g. fa/fa_IR/gyro/medium/fa_IR-gyro-medium."),
):
    """Download a Piper voice (about 60 MB) from rhasspy/piper-voices on Hugging Face."""
    from .voice import piper
    s = _settings()
    path = piper.download_voice(s, lang, voice=voice)
    console.print(f"[green]Voice ready:[/green] {path}")


# --- materials ------------------------------------------------------------

@materials_app.command("list")
def materials_list_sources():
    """List configured materials sources and their availability."""
    from .materials import build_provider
    s = _settings()
    profile = _load_or_default_profile(s)
    if not profile.materials_sources:
        console.print("[yellow]No materials sources configured.[/yellow] "
                       "Add one with: [bold]lingua-agent materials add[/bold]")
        return
    table = Table(title="Materials sources")
    for col in ("name", "provider", "root", "available", "notes"):
        table.add_column(col)
    for cfg in profile.materials_sources:
        try:
            avail = build_provider(cfg).is_available()
        except Exception:
            avail = False
        table.add_row(cfg.name, cfg.provider, cfg.root,
                       "[green]yes[/green]" if avail else "[red]no[/red]",
                       cfg.notes or "")
    console.print(table)


@materials_app.command("add")
def materials_add(
    name: str = typer.Option(..., "--name", help="Human-readable label, e.g. 'Transcend SSD'."),
    provider: str = typer.Option(..., "--provider", help="local_dir | rclone_drive"),
    root: str = typer.Option(..., "--root",
                              help="Filesystem path or rclone remote+path, e.g. 'gdrive:3-Language'."),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    """Add a materials source to the learner profile."""
    from .materials.base import MaterialsSourceConfig
    if provider not in ("local_dir", "rclone_drive"):
        console.print(f"[red]Unknown provider:[/red] {provider}")
        raise typer.Exit(code=1)
    s = _settings()
    profile = _load_or_default_profile(s)
    if any(src.name == name for src in profile.materials_sources):
        console.print(f"[red]Source {name!r} already exists.[/red]")
        raise typer.Exit(code=1)
    profile.materials_sources.append(MaterialsSourceConfig(
        name=name, provider=provider, root=root, notes=notes,  # type: ignore[arg-type]
    ))
    _save_profile(s, profile)
    console.print(f"[green]Added[/green] source [bold]{name}[/bold] "
                   f"({provider}: {root})")


@materials_app.command("remove")
def materials_remove(name: str):
    """Remove a materials source from the learner profile."""
    s = _settings()
    profile = _load_or_default_profile(s)
    before = len(profile.materials_sources)
    profile.materials_sources = [src for src in profile.materials_sources if src.name != name]
    if len(profile.materials_sources) == before:
        console.print(f"[red]No such source:[/red] {name}")
        raise typer.Exit(code=1)
    _save_profile(s, profile)
    console.print(f"[green]Removed[/green] source [bold]{name}[/bold]")


@materials_app.command("browse")
def materials_browse(
    source: str = typer.Argument(..., help="Name of the source to browse."),
    folder: str = typer.Option("", "--folder",
                                help="Sub-folder path (relative to source root)."),
):
    """List entries in a materials folder."""
    from .materials import MaterialsError, build_provider
    from .materials.registry import find_source
    s = _settings()
    profile = _load_or_default_profile(s)
    cfg = find_source(profile, source)
    if cfg is None:
        console.print(f"[red]No such source:[/red] {source}")
        raise typer.Exit(code=1)
    provider = build_provider(cfg)
    if not provider.is_available():
        console.print(f"[yellow]Source {source!r} is not available right now.[/yellow]")
        raise typer.Exit(code=1)
    try:
        entries = provider.list(folder)
    except MaterialsError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    table = Table(title=f"{source} : /{folder}".rstrip("/"))
    for col in ("name", "kind", "size", "mime"):
        table.add_column(col)
    for e in entries:
        kind = "📁 dir" if e.is_dir else "📄 file"
        size = "—" if e.size_bytes is None else _human_size(e.size_bytes)
        table.add_row(e.name, kind, size, e.mime_type or "—")
    console.print(table)


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def main() -> None:  # pragma: no cover - convenience for `python -m lingua_agent.cli`
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
