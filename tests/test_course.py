"""Courses, exercises, progress, Today, stories, Talk, recordings and audio (Product v2)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from lingua_agent.api.main import build_app
from lingua_agent.config import Settings
from lingua_agent.course import exercises as X
from lingua_agent.course import store
from lingua_agent.course.models import CourseDef, CourseItem
from lingua_agent.voice.subtitles import parse_transcript

COURSE = {
    "id": "fa-en-test",
    "target": "fa",
    "support": "en",
    "level": "A1",
    "title": "Test course",
    "units": [
        {
            "id": "u1", "title": "Hello", "goal": "greet",
            "story": "s1", "scenario": "t1",
            "lessons": [
                {"id": "u1-l1", "title": "Greetings", "kind": "phrases", "items": [
                    {"id": "salam", "text": "سلام", "tr": "salâm", "gloss": "hello"},
                    {"id": "khodahafez", "text": "خداحافظ", "tr": "khodâhâfez", "gloss": "goodbye"},
                    {"id": "merci", "text": "مرسی", "tr": "mersi", "gloss": "thanks"},
                    {"id": "khubam", "text": "خوبم", "tr": "khubam", "gloss": "I'm fine"},
                    {"id": "esme-man", "text": "اسم من سارا است", "tr": "esm-e man Sârâ ast", "gloss": "my name is Sara"},
                ]},
                {"id": "u1-l2", "title": "Yes and no", "kind": "words", "items": [
                    {"id": "bale", "text": "بله", "tr": "bale", "gloss": "yes"},
                    {"id": "na", "text": "نه", "tr": "na", "gloss": "no"},
                    {"id": "man", "text": "من", "tr": "man", "gloss": "I"},
                ]},
            ],
        },
        {
            "id": "u2", "title": "Letters", "goal": "read",
            "lessons": [
                {"id": "u2-l1", "title": "Alef and be", "kind": "script", "items": [
                    {"id": "alef", "text": "ا", "tr": "â", "gloss": "alef"},
                    {"id": "be", "text": "ب", "tr": "b", "gloss": "be"},
                    {"id": "pe", "text": "پ", "tr": "p", "gloss": "pe"},
                ]},
            ],
        },
    ],
    "stories": [{
        "id": "s1", "unit": "u1", "kind": "dialogue", "title": "سلام", "title_gloss": "Hi",
        "speakers": {"a": {"name": "Sara", "voice": "female"}, "b": {"name": "Ali", "voice": "male"}},
        "lines": [
            {"speaker": "a", "text": "سلام!", "tr": "salâm!", "gloss": "Hello!"},
            {"speaker": "b", "text": "خداحافظ!", "tr": "khodâhâfez!", "gloss": "Goodbye!"},
        ],
    }],
    "scenarios": [{
        "id": "t1", "unit": "u1", "title": "Neighbour", "title_target": "همسایه",
        "setting": "Stairway.", "persona": "Maryam (مریم), a teacher.", "goal": "Say hello.",
        "opener": {"text": "سلام!", "tr": "salâm!", "gloss": "Hi!"},
        "useful": [{"text": "بله", "tr": "bale", "gloss": "yes"}],
    }],
}


@pytest.fixture
def course_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "courses_pkg"
    d.mkdir()
    (d / "test.yaml").write_text(yaml.safe_dump(COURSE, allow_unicode=True), "utf-8")
    monkeypatch.setattr(store, "PACKAGE_DATA", d)
    return d


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, course_dir: Path) -> TestClient:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    monkeypatch.setenv("LINGUA_TALK", "on")
    return TestClient(build_app(Settings.load(cwd=tmp_path)))


def _all_correct(session: dict) -> list[dict]:
    out = []
    for ex in session["exercises"]:
        if ex["kind"] == "match":
            out += [{"item_id": p["id"], "correct": True} for p in ex["pairs"]]
        elif ex["kind"] != "intro":
            out.append({"item_id": ex["item"]["id"], "correct": True})
    return out


# ---- exercises -------------------------------------------------------------------

def _items() -> list[CourseItem]:
    return [CourseItem(**i) for i in COURSE["units"][0]["lessons"][0]["items"]]


def test_lesson_session_shape_and_answers():
    items = _items()
    exs = X.lesson_session("u1-l1", items, items, kind="phrases", seed="0")
    kinds = [e.kind for e in exs]
    assert kinds.count("intro") == len(items)
    assert kinds[0] == "intro"
    assert kinds[-1] == "match"
    for e in exs:
        if e.kind in ("choose_gloss", "choose_text", "listen"):
            assert e.answer in e.choices
            assert len(set(e.choices)) == len(e.choices)
        if e.kind == "order":
            assert sorted(X.words(e.answer)) == sorted(t for t in e.tiles if t in X.words(e.answer))
            assert set(X.words(e.answer)) <= set(e.tiles)
        if e.kind == "type_tr":
            assert e.answer and e.hide_tr
    assert len({e.id for e in exs}) == len(exs)


def test_sessions_are_deterministic_per_seed():
    items = _items()
    a = X.lesson_session("u1-l1", items, items, seed="0")
    b = X.lesson_session("u1-l1", items, items, seed="0")
    c = X.lesson_session("u1-l1", items, items, seed="1")
    assert [e.model_dump() for e in a] == [e.model_dump() for e in b]
    assert [e.model_dump() for e in a] != [e.model_dump() for e in c]


def test_script_lessons_hide_transliteration_when_checking():
    items = [CourseItem(**i) for i in COURSE["units"][1]["lessons"][0]["items"]]
    exs = X.lesson_session("u2-l1", items, items, kind="script")
    assert all(e.hide_tr for e in exs if e.kind == "choose_gloss")
    assert not any(e.kind in ("order", "type_tr") for e in exs)


def test_quiz_has_no_intros():
    items = _items()
    exs = X.quiz_session("u1-quiz", items, items, n=4)
    assert "intro" not in {e.kind for e in exs}
    assert sum(e.kind != "match" for e in exs) == 4


def test_normalize_tr_is_lenient():
    assert X.normalize_tr("Esm-e man Sârâ ast!") == X.normalize_tr("esme man sara ast")


# ---- subtitles -------------------------------------------------------------------

def test_parse_srt_vtt_and_text():
    srt = "1\n00:00:01,000 --> 00:00:02,500\nسلام\n\n2\n00:00:03,000 --> 00:00:04,000\n<i>خوبم</i>\n"
    assert parse_transcript(srt) == [
        {"start": 1.0, "end": 2.5, "text": "سلام"},
        {"start": 3.0, "end": 4.0, "text": "خوبم"},
    ]
    vtt = "WEBVTT\n\n00:01.000 --> 00:02.000\nhello\n"
    assert parse_transcript(vtt) == [{"start": 1.0, "end": 2.0, "text": "hello"}]
    assert [c["text"] for c in parse_transcript("one\n\ntwo\n")] == ["one", "two"]


# ---- packaged course data ------------------------------------------------------------

def test_packaged_courses_are_valid():
    for path in sorted(Path(store.__file__).parent.joinpath("data").glob("*.yaml")):
        course = CourseDef.model_validate(yaml.safe_load(path.read_text("utf-8")))
        ids = [i.id for _, lesson in course.lessons() for i in lesson.items]
        ids += [lesson.id for _, lesson in course.lessons()] + [u.id for u in course.units]
        ids += [s.id for s in course.stories] + [s.id for s in course.scenarios]
        assert len(ids) == len(set(ids)), f"duplicate ids in {path.name}"
        for unit in course.units:
            assert unit.story is None or course.story(unit.story), f"{unit.id}: missing story {unit.story}"
            assert unit.scenario is None or course.scenario(unit.scenario), f"{unit.id}: missing scenario"
        for st in course.stories:
            assert course.unit(st.unit), f"story {st.id}: unknown unit"
            assert all(line.speaker in st.speakers for line in st.lines), f"story {st.id}: unknown speaker"


# ---- API: Path ---------------------------------------------------------------------

def test_course_path_progression(client: TestClient):
    courses = client.get("/api/courses", params={"target": "fa"}).json()
    assert [c["id"] for c in courses] == ["fa-en-test"]
    course = client.get("/api/courses/fa-en-test").json()
    states = [ls["state"] for u in course["units"] for ls in u["lessons"]]
    assert states == ["current", "locked", "locked"]
    assert course["next_lesson"]["lesson_id"] == "u1-l1"

    session = client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()
    results = _all_correct(session)
    results[0]["correct"] = False
    r = client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json={"results": results, "seconds": 90})
    body = r.json()
    assert r.status_code == 200
    assert body["cards_added"] == 5
    assert body["unlocked"] == "u1-l2"
    assert 0.8 < body["score"] < 1.0

    course = client.get("/api/courses/fa-en-test").json()
    assert [ls["state"] for ls in course["units"][0]["lessons"]] == ["done", "current"]
    assert course["lessons_done"] == 1

    # Completing again doesn't duplicate cards.
    again = client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json={"results": results})
    assert again.json()["cards_added"] == 0
    cards = client.get("/api/cards/due", params={"target": "fa"}).json()
    assert len(cards) == 5
    assert any(c["front"] == "hello" and c["back"].startswith("سلام") for c in cards)


def test_unit_quiz_unlocks_after_lessons_and_tests_out(client: TestClient):
    for lid in ("u1-l1", "u1-l2"):
        s = client.get(f"/api/courses/fa-en-test/lessons/{lid}/session").json()
        last = client.post(f"/api/courses/fa-en-test/lessons/{lid}/complete", json={"results": _all_correct(s)})
    assert last.json()["unlocked"] == "u1:quiz"
    unit = client.get("/api/courses/fa-en-test").json()["units"][0]
    assert unit["quiz_state"] == "current" and unit["done"]

    quiz = client.get("/api/courses/fa-en-test/units/u1/quiz").json()
    assert quiz["id"] == "u1:quiz"
    failed = [{"item_id": r["item_id"], "correct": False} for r in _all_correct(quiz)]
    assert client.post("/api/courses/fa-en-test/units/u1/quiz/complete", json={"results": failed}).json()["passed"] is False
    ok = client.post("/api/courses/fa-en-test/units/u1/quiz/complete", json={"results": _all_correct(quiz)}).json()
    assert ok["passed"] is True
    assert client.get("/api/courses/fa-en-test").json()["units"][0]["quiz_state"] == "done"


def test_passing_a_later_unit_quiz_tests_out(client: TestClient):
    quiz = client.get("/api/courses/fa-en-test/units/u2/quiz").json()
    r = client.post("/api/courses/fa-en-test/units/u2/quiz/complete", json={"results": _all_correct(quiz)})
    assert r.json()["passed"]
    course = client.get("/api/courses/fa-en-test").json()
    assert course["units"][1]["lessons"][0]["state"] == "done"
    assert course["next_lesson"]["lesson_id"] == "u1-l1"


def test_practice_needs_a_finished_lesson(client: TestClient):
    assert client.get("/api/courses/fa-en-test/practice").status_code == 409
    s = client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()
    client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json={"results": _all_correct(s)})
    p = client.get("/api/courses/fa-en-test/practice", params={"n": 4}).json()
    assert p["id"] == "practice"
    item_ids = {e["item"]["id"] for e in p["exercises"] if e["item"]}
    assert item_ids <= {"salam", "khodahafez", "merci", "khubam", "esme-man"}
    done = client.post("/api/courses/fa-en-test/practice/complete", json={"results": _all_correct(p), "seconds": 60})
    assert done.json()["score"] == 1.0


def test_unknown_course_and_lesson_404(client: TestClient):
    assert client.get("/api/courses/nope").status_code == 404
    assert client.get("/api/courses/fa-en-test/lessons/nope/session").status_code == 404


# ---- API: Today, stories, scenarios ---------------------------------------------------------

def test_today(client: TestClient):
    t = client.get("/api/today", params={"target": "fa", "support": "en"}).json()
    assert t["course"]["id"] == "fa-en-test"
    assert t["next_lesson"]["lesson_id"] == "u1-l1"
    assert t["story"]["id"] == "s1" and t["story"]["unlocked"]
    assert t["scenario"]["id"] == "t1"
    assert t["minutes_today"] == 0 and t["streak_days"] == 0

    s = client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()
    client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json={"results": _all_correct(s), "seconds": 300})
    t = client.get("/api/today", params={"target": "fa", "support": "en"}).json()
    assert t["minutes_today"] == 5
    assert t["streak_days"] == 1
    assert t["learned_count"] == 5
    assert t["due_count"] == 5

    none = client.get("/api/today", params={"target": "it", "support": "en"}).json()
    assert none["course"] is None and none["next_lesson"] is None


def test_stories_and_scenarios(client: TestClient):
    stories = client.get("/api/stories", params={"target": "fa"}).json()
    assert [s["id"] for s in stories] == ["s1"]
    story = client.get("/api/stories/s1").json()
    assert story["speakers"]["a"]["name"] == "Sara"
    assert story["lines"][1] | {} == {**story["lines"][1], "id": "s1-1", "speaker": "b"}
    scen = client.get("/api/scenarios/t1").json()
    assert scen["opener"]["text"] == "سلام!"
    assert [u["gloss"] for u in scen["useful"]] == ["yes"]
    assert client.get("/api/stories/nope").status_code == 404


# ---- API: Talk ----------------------------------------------------------------------------

def test_talk_roleplay_with_mock(client: TestClient):
    sess = client.post("/api/talk/sessions", json={"target": "fa", "support": "en", "scenario_id": "t1"}).json()
    assert sess["scenario"]["id"] == "t1"
    assert sess["messages"][0]["role"] == "assistant"
    assert sess["messages"][0]["turn"]["text"] == "سلام!"

    reply = client.post(f"/api/talk/sessions/{sess['id']}/messages", json={"content": "salam, coffee"}).json()
    assert reply["role"] == "assistant" and reply["turn"]["text"]
    assert len(client.get(f"/api/talk/sessions/{sess['id']}").json()["messages"]) == 3

    summary = client.post(f"/api/talk/sessions/{sess['id']}/end").json()
    assert summary["mistakes"][0]["you_said"] == "salam, coffee"
    assert summary["cards_added"] == len(summary["new_words"]) > 0
    assert client.post(f"/api/talk/sessions/{sess['id']}/messages", json={"content": "x"}).status_code == 409


def test_free_talk_and_empty_summary(client: TestClient):
    sess = client.post("/api/talk/sessions", json={"target": "fa"}).json()
    assert sess["scenario"] is None and sess["messages"] == []
    summary = client.post(f"/api/talk/sessions/{sess['id']}/end").json()
    assert summary["cards_added"] == 0


# ---- API: speech, recordings, audio ---------------------------------------------------------

def test_speech_without_voices(client: TestClient):
    info = client.get("/api/speech").json()
    assert info["server_tts"]["fa"] is False
    assert client.get("/api/tts", params={"lang": "fa", "text": "سلام"}).status_code == 404
    assert client.get("/api/tts", params={"lang": "../x", "text": "a"}).status_code == 400


def test_recordings_roundtrip(client: TestClient):
    r = client.post("/api/recordings", data={"ref": "salam", "language": "fa", "seconds": "2.5"},
                    files={"file": ("rec.webm", b"\x1a\x45\xdf\xa3fake", "audio/webm")})
    assert r.status_code == 201
    rec = r.json()
    assert rec["url"] == f"/api/recordings/{rec['id']}/file"
    assert [x["id"] for x in client.get("/api/recordings", params={"ref": "salam"}).json()] == [rec["id"]]
    assert client.get("/api/recordings", params={"ref": "other"}).json() == []
    f = client.get(rec["url"])
    assert f.status_code == 200 and f.content.endswith(b"fake")
    assert client.delete(f"/api/recordings/{rec['id']}").status_code == 204
    assert client.get("/api/recordings").json() == []


def test_recording_rejects_non_audio(client: TestClient):
    r = client.post("/api/recordings", data={"ref": "x", "language": "fa"},
                    files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_audio_upload_with_transcript(client: TestClient):
    srt = "1\n00:00:00,500 --> 00:00:01,500\nسلام\n"
    r = client.post("/api/audio", data={"language": "fa", "title": "Greeting"},
                    files={"file": ("greet.mp3", b"ID3fake", "audio/mpeg"),
                           "transcript": ("greet.srt", srt.encode(), "application/x-subrip")})
    assert r.status_code == 201
    track = r.json()
    assert track["has_transcript"] and track["title"] == "Greeting"
    detail = client.get(f"/api/audio/{track['id']}").json()
    assert detail["cues"] == [{"start": 0.5, "end": 1.5, "text": "سلام", "tr": None, "gloss": None}]
    assert client.get(track["url"]).content == b"ID3fake"
    assert client.post(f"/api/audio/{track['id']}/transcribe").status_code in (200, 501)
    assert client.delete(f"/api/audio/{track['id']}").status_code == 204
    assert client.get("/api/audio").json() == []


def test_audio_from_local_materials(client: TestClient, tmp_path: Path):
    src = tmp_path / "materials" / "fa"
    src.mkdir(parents=True)
    (src / "lesson1.mp3").write_bytes(b"ID3x")
    (src / "lesson1.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nسلام\n", "utf-8")
    client.post("/api/materials/sources", json={"name": "ssd", "provider": "local_dir",
                                                "root": str(tmp_path / "materials")})
    r = client.post("/api/audio/from-materials", json={"source": "ssd", "path": "fa/lesson1.mp3", "language": "fa"})
    assert r.status_code == 201, r.text
    assert r.json()["has_transcript"] is True
    assert client.post("/api/audio/from-materials",
                       json={"source": "nope", "path": "x.mp3", "language": "fa"}).status_code == 404


def test_contract_extras(client: TestClient):
    unit = client.get("/api/courses/fa-en-test").json()["units"]
    assert unit[0]["story_unlocked"] and unit[0]["scenario_unlocked"]
    assert not unit[1]["story_unlocked"]
    assert client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()["target"] == "fa"
    assert client.get("/api/scenarios/t1").json()["persona_name"] == "Maryam"
    for ref in ("story:s1:0", "story:s1:1", "salam"):
        client.post("/api/recordings", data={"ref": ref, "language": "fa"},
                    files={"file": ("r.webm", b"x", "audio/webm")})
    refs = sorted(r["ref"] for r in client.get("/api/recordings", params={"ref_prefix": "story:s1:"}).json())
    assert refs == ["story:s1:0", "story:s1:1"]


def test_audio_supports_range_requests(client: TestClient):
    track = client.post("/api/audio", data={"language": "fa"},
                        files={"file": ("a.mp3", b"0123456789", "audio/mpeg")}).json()
    r = client.get(track["url"], headers={"Range": "bytes=2-5"})
    assert r.status_code == 206 and r.content == b"2345"


# ---- audit 2026-11-17 fixes ------------------------------------------------------------

def test_course_cards_carry_target_text(client: TestClient):
    s = client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()
    client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json={"results": _all_correct(s)})
    card = next(c for c in client.get("/api/cards/due", params={"target": "fa"}).json() if c["front"] == "hello")
    assert (card["text"], card["tr"]) == ("سلام", "salâm")


def test_review_is_idempotent_and_counts_time(client: TestClient):
    s = client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()
    client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json={"results": _all_correct(s)})
    cid = client.get("/api/cards/due", params={"target": "fa"}).json()[0]["id"]
    body = {"rating": 5, "event_id": "evt-1", "seconds": 120}
    first = client.post(f"/api/cards/{cid}/review", json=body).json()
    again = client.post(f"/api/cards/{cid}/review", json=body).json()
    assert first["repetitions_after"] == again["repetitions_after"] == 1
    assert client.get("/api/today", params={"target": "fa"}).json()["minutes_today"] == 2


def test_lesson_completion_replay_is_ignored(client: TestClient):
    s = client.get("/api/courses/fa-en-test/lessons/u1-l1/session").json()
    body = {"results": _all_correct(s), "seconds": 60, "event_id": "done-1"}
    client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json=body)
    client.post("/api/courses/fa-en-test/lessons/u1-l1/complete", json=body)
    prog = client.get("/api/courses/fa-en-test").json()
    assert prog["units"][0]["lessons"][0]["state"] == "done"
    assert client.get("/api/today", params={"target": "fa"}).json()["minutes_today"] == 1


def test_test_out_is_reachable_before_lessons(client: TestClient):
    units = client.get("/api/courses/fa-en-test").json()["units"]
    assert units[0]["quiz_state"] == "current" and not units[0]["done"]   # first unit: test-out open
    assert units[1]["quiz_state"] == "locked"


def test_today_suggests_checkpoint(client: TestClient):
    for lid in ("u1-l1", "u1-l2"):
        s = client.get(f"/api/courses/fa-en-test/lessons/{lid}/session").json()
        client.post(f"/api/courses/fa-en-test/lessons/{lid}/complete", json={"results": _all_correct(s)})
    t = client.get("/api/today", params={"target": "fa"}).json()
    assert t["checkpoint"] == {"unit_id": "u1", "unit_title": "Hello"}


def test_talk_resume_and_idempotent_end(client: TestClient):
    sess = client.post("/api/talk/sessions", json={"target": "fa", "scenario_id": "t1"}).json()
    assert client.get("/api/talk/sessions/latest", params={"target": "fa", "scenario_id": "t1"}).json()["id"] == sess["id"]
    client.post(f"/api/talk/sessions/{sess['id']}/messages", json={"content": "coffee and water"})
    first = client.post(f"/api/talk/sessions/{sess['id']}/end").json()
    second = client.post(f"/api/talk/sessions/{sess['id']}/end").json()
    assert first == second and second["cards_added"] == first["cards_added"]
    assert client.get(f"/api/talk/sessions/{sess['id']}").json()["summary"]["went_well"] == first["went_well"]
    assert client.get("/api/talk/sessions/latest", params={"target": "fa", "scenario_id": "t1"}).status_code == 404
    # The same words in another conversation don't make new cards.
    other = client.post("/api/talk/sessions", json={"target": "fa", "scenario_id": "t1"}).json()
    client.post(f"/api/talk/sessions/{other['id']}/messages", json={"content": "coffee and water"})
    assert client.post(f"/api/talk/sessions/{other['id']}/end").json()["cards_added"] == 0


def test_activity_endpoint_dedupes(client: TestClient):
    for _ in range(2):
        assert client.post("/api/activity", json={"seconds": 180, "kind": "story", "event_id": "s-1"}).status_code == 204
    assert client.get("/api/today", params={"target": "fa"}).json()["minutes_today"] == 3


def test_recordings_and_audio_filter_by_language(client: TestClient):
    for lang in ("fa", "ru"):
        client.post("/api/recordings", data={"ref": "diary", "language": lang}, files={"file": ("r.webm", b"x", "audio/webm")})
        client.post("/api/audio", data={"language": lang}, files={"file": ("a.mp3", b"x", "audio/mpeg")})
    assert [r["language"] for r in client.get("/api/recordings", params={"language": "fa"}).json()] == ["fa"]
    assert [a["language"] for a in client.get("/api/audio", params={"language": "ru"}).json()] == ["ru"]


def test_delete_generated_unit(client: TestClient):
    r = client.post("/api/ingest/text", json={"text": "Coffee and water.", "title": "Cafe", "source_language": "en",
                                              "target_language": "fa", "support_language": "en"})
    uid = r.json()["unit_id"]
    assert client.delete(f"/api/units/{uid}").status_code == 204
    assert client.get(f"/api/units/{uid}").status_code == 404
    assert client.get("/api/cards/due", params={"target": "fa"}).json() == []
    assert client.delete(f"/api/units/{uid}").status_code == 404


def test_native_text_ingest_runs(client: TestClient):
    r = client.post("/api/ingest/text", json={"text": "من قهوه و آب می‌خواهم.", "title": "Native",
                                              "source_language": "fa", "target_language": "fa", "support_language": "en"})
    assert r.status_code == 200, r.text


def test_health_label(client: TestClient):
    assert client.get("/api/health").json()["ai_label"] == "Mock replies (no AI model)"


def test_requests_without_tailscale_header_must_be_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, course_dir: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    app = build_app(Settings.load(cwd=tmp_path))
    lan = TestClient(app, client=("192.168.1.20", 50000))
    assert lan.get("/api/me").status_code == 403
    assert lan.get("/api/me", headers={"Tailscale-User-Login": "x@y.z"}).json()["owner"] is False
    assert TestClient(app, client=("127.0.0.1", 50000)).get("/api/me").json()["owner"] is True


def test_talk_switched_off_keeps_prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, course_dir: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINGUA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LINGUA_AI_PROVIDER", "mock")
    monkeypatch.delenv("LINGUA_TALK", raising=False)
    c = TestClient(build_app(Settings.load(cwd=tmp_path)))
    assert c.get("/api/health").json()["features"] == {"talk": False}
    assert c.post("/api/talk/sessions", json={"target": "fa"}).status_code == 404
    # Scenarios stay: they become prompts for the learner's own chatbot.
    assert c.get("/api/today", params={"target": "fa"}).json()["scenario"]["id"] == "t1"
    assert [x["id"] for x in c.get("/api/scenarios", params={"target": "fa"}).json()] == ["t1"]
    text = c.get("/api/scenarios/t1/prompt").json()["prompt"]
    assert "Maryam" in text and "سلام!" in text and "salâm" in text and "Better:" in text
    voice = c.get("/api/scenarios/t1/prompt", params={"voice": True}).json()["prompt"]
    assert "by voice" in voice and "Better:" not in voice
    assert c.get("/api/scenarios/nope/prompt").status_code == 404
