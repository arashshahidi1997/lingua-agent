"""Loading courses and reading/writing learner progress and daily activity.

Courses ship with the package (`course/data/*.yaml`); a learner can drop extra
course files into `${data_dir}/courses/`. Progress lives in
`${data_dir}/course_progress/<course_id>.json`, activity in `${data_dir}/activity.json`.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from ..config import Settings
from .models import ActivityDay, CourseDef, CourseProgress, LessonRecord

PACKAGE_DATA = Path(__file__).parent / "data"


def _load_file(path: Path) -> CourseDef:
    data = yaml.safe_load(path.read_text("utf-8"))
    course = CourseDef.model_validate(data)
    for story in course.stories:
        for i, line in enumerate(story.lines):
            line.id = f"{story.id}-{i}"
    return course


@lru_cache(maxsize=32)
def _load_cached(path: str, mtime: float) -> CourseDef:
    return _load_file(Path(path))


def course_files(settings: Settings) -> list[Path]:
    files = sorted(PACKAGE_DATA.glob("*.yaml"))
    user_dir = settings.shared_data_dir / "courses"
    if user_dir.exists():
        files += sorted(user_dir.glob("*.yaml"))
    return files


def load_courses(settings: Settings) -> list[CourseDef]:
    courses: dict[str, CourseDef] = {}
    for path in course_files(settings):
        course = _load_cached(str(path), path.stat().st_mtime)
        courses[course.id] = course  # user files override packaged ones by id
    return list(courses.values())


def get_course(settings: Settings, course_id: str) -> CourseDef | None:
    return next((c for c in load_courses(settings) if c.id == course_id), None)


def find_story(settings: Settings, story_id: str):
    for c in load_courses(settings):
        if (s := c.story(story_id)) is not None:
            return c, s
    return None


def find_scenario(settings: Settings, scenario_id: str):
    for c in load_courses(settings):
        if (s := c.scenario(scenario_id)) is not None:
            return c, s
    return None


# ---- progress -----------------------------------------------------------------

def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _progress_path(settings: Settings, course_id: str) -> Path:
    if "/" in course_id or ".." in course_id:
        raise ValueError(f"unsafe id: {course_id!r}")
    return settings.data_dir / "course_progress" / f"{course_id}.json"


def load_progress(settings: Settings, course_id: str) -> CourseProgress:
    path = _progress_path(settings, course_id)
    if path.exists():
        return CourseProgress.model_validate_json(path.read_text("utf-8"))
    return CourseProgress(course_id=course_id)


def save_progress(settings: Settings, progress: CourseProgress) -> None:
    _write_json(_progress_path(settings, progress.course_id), progress.model_dump(mode="json"))


def record(records: dict[str, LessonRecord], key: str, score: float) -> None:
    prev = records.get(key)
    if prev is None:
        records[key] = LessonRecord(best_score=score)
    else:
        prev.best_score = max(prev.best_score, score)
        prev.attempts += 1


# ---- activity -----------------------------------------------------------------

def _activity_path(settings: Settings) -> Path:
    return settings.data_dir / "activity.json"


def load_activity(settings: Settings) -> list[ActivityDay]:
    path = _activity_path(settings)
    if not path.exists():
        return []
    return [ActivityDay.model_validate(d) for d in json.loads(path.read_text("utf-8"))]


def log_activity(settings: Settings, seconds: int, *, today: date | None = None) -> None:
    today = today or date.today()
    days = load_activity(settings)
    if days and days[-1].day == today:
        days[-1].seconds += max(0, seconds)
        days[-1].sessions += 1
    else:
        days.append(ActivityDay(day=today, seconds=max(0, seconds), sessions=1))
    _write_json(_activity_path(settings), [d.model_dump(mode="json") for d in days[-400:]])


def minutes_today(days: list[ActivityDay], *, today: date | None = None) -> int:
    today = today or date.today()
    return next((round(d.seconds / 60) for d in reversed(days) if d.day == today), 0)


def streak(days: list[ActivityDay], *, today: date | None = None) -> int:
    """Consecutive active days ending today (or yesterday, so the streak survives until tonight)."""
    today = today or date.today()
    active = {d.day for d in days if d.sessions > 0}
    day = today if today in active else today - timedelta(days=1)
    n = 0
    while day in active:
        n += 1
        day -= timedelta(days=1)
    return n
