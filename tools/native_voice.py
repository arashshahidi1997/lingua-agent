"""Cut a native speaker's recording into clips, one or more takes per word, for the app's speech.

    .venv/bin/python tools/native_voice.py RECORDING --lesson u1-l1 [--takes 3] [--speaker Arash] [--dry-run]
    .venv/bin/python tools/native_voice.py RECORDING --texts "سلام,خداحافظ" --takes 3

The speaker reads each word or line `--takes` times, in course order, with a pause after each take.
Speech is found from the pauses (ffmpeg silencedetect); quiet segments (breaths, handling noise) are
dropped by loudness. The remaining segments must number exactly items × takes; they are matched by
order, and Whisper (if installed) transcribes each one as a sanity check, printed next to its word.
Each take is trimmed, peak-normalised, faded and saved as AAC under the shared data dir:

    .lingua-agent/native_audio/<speaker>/<hash>-<n>.m4a   +   .lingua-agent/native_audio/index.json

The server's /api/tts serves one of these takes, at random, for any text that has them, and falls back to
Piper otherwise — so the voice changes everywhere the text is spoken, in lessons, review and stories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lingua_agent.config import Settings  # noqa: E402
from lingua_agent.course import store  # noqa: E402
from lingua_agent.voice.native import index_path, load_index, norm  # noqa: E402

NOISE_DB = -38.0        # silencedetect threshold
MIN_PAUSE = 0.35        # seconds of silence between takes
QUIET_MEAN_DB = -40.0   # segments quieter than this on average are breaths or noise


def _ffmpeg(*args: str) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", *args], capture_output=True, text=True).stderr


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    return float(out.strip())


def speech_segments(path: Path) -> list[tuple[float, float]]:
    log = _ffmpeg("-i", str(path), "-af", f"silencedetect=noise={NOISE_DB}dB:d={MIN_PAUSE}", "-f", "null", "-")
    events = [(m.group(1), float(m.group(2))) for m in re.finditer(r"silence_(start|end): ([\d.]+)", log)]
    segs, last = [], 0.0
    for kind, t in events:
        if kind == "start":
            if t - last > 0.15:
                segs.append((last, t))
        else:
            last = t
    end = duration(path)
    if end - last > 0.3:
        segs.append((last, end))
    return segs


def mean_volume(path: Path, start: float, length: float) -> float:
    log = _ffmpeg("-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(path), "-af", "volumedetect", "-f", "null", "-")
    m = re.search(r"mean_volume: ([-\d.]+)", log)
    return float(m.group(1)) if m else -99.0


def rms_frames(path: Path, start: float, end: float, step: float = 0.05) -> list[float]:
    """RMS level (dB) of consecutive `step`-second frames between start and end."""
    log = _ffmpeg("-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(path), "-af",
                  f"aresample=44100,asetnsamples={int(44100 * step)},astats=metadata=1:reset=1,"
                  "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-")
    vals = []
    for m in re.finditer(r"RMS_level=([-\w.]+)", log):
        try:
            vals.append(float(m.group(1)))
        except ValueError:  # -inf
            vals.append(-120.0)
    return vals


def tighten(path: Path, start: float, end: float, step: float = 0.05) -> tuple[float, float]:
    """Drop a breath or noise tail: after the word, if the level dips 25 dB below its peak and never comes
    back within 15 dB of it, the take ends at the dip. A pause between syllables comes back up, so stays."""
    rms = rms_frames(path, start, end, step)
    if not rms:
        return start, end
    peak = max(rms)
    first = next((i for i, v in enumerate(rms) if v > peak - 30), 0)
    cut_at = len(rms)
    for i in range(first + 1, len(rms)):
        if rms[i] < peak - 25 and all(v < peak - 15 for v in rms[i:]):
            cut_at = i
            break
    return start + first * step, min(end, start + cut_at * step + step)


def cut(path: Path, start: float, end: float, out: Path) -> None:
    """Trim to the take with a little air, even out the level, fade the edges, encode AAC."""
    a, b = max(0.0, start - 0.12), end + 0.18
    chain = (
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse,"
        "loudnorm=I=-18:TP=-1.5:LRA=11,"
        "afade=t=in:d=0.02,areverse,afade=t=in:d=0.04,areverse"
    )
    _ffmpeg("-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(path), "-af", chain,
            "-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", "96k", str(out))


def transcribe(path: Path, start: float, end: float, lang: str) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return ""
    global _model
    if "_model" not in globals():
        _model = WhisperModel("medium", device="cpu", compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        _ffmpeg("-y", "-ss", f"{max(0, start - 0.25):.3f}", "-t", f"{end - start + 0.5:.3f}", "-i", str(path),
                "-ac", "1", "-ar", "16000", tmp.name)
        segs, _ = _model.transcribe(tmp.name, language=lang, beam_size=5)
        return " ".join(s.text.strip() for s in segs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording", type=Path)
    ap.add_argument("--course", default="fa-en-a1")
    ap.add_argument("--lesson", help="course lesson id whose items were read, in order")
    ap.add_argument("--texts", help="comma-separated texts instead of --lesson")
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--speaker", default="Arash")
    ap.add_argument("--dry-run", action="store_true", help="show the matching, write nothing")
    args = ap.parse_args()

    settings = Settings.load(cwd=ROOT)
    course = store.get_course(settings, args.course)
    if args.lesson:
        found = course.lesson(args.lesson) if course else None
        if not found:
            sys.exit(f"lesson not found: {args.lesson}")
        texts = [it.text for it in found[1].items]
    elif args.texts:
        texts = [t.strip() for t in args.texts.split(",") if t.strip()]
    else:
        sys.exit("give --lesson or --texts")

    segs = speech_segments(args.recording)
    speech = [(a, b) for a, b in segs if mean_volume(args.recording, a, b - a) > QUIET_MEAN_DB]
    dropped = len(segs) - len(speech)
    want = len(texts) * args.takes
    print(f"{args.recording.name}: {len(segs)} segments, {dropped} quiet (noise) dropped, {len(speech)} takes; "
          f"expected {len(texts)} × {args.takes} = {want}")
    if len(speech) != want:
        for a, b in speech:
            print(f"  {a:6.2f}-{b:6.2f}  {transcribe(args.recording, a, b, course.target if course else 'fa')}")
        sys.exit("count mismatch: check the recording (a missing or extra take) and re-run")

    out_dir = index_path(settings).parent / args.speaker.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    index = load_index(settings)
    for i, text in enumerate(texts):
        key = norm(text)
        stem = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        takes = [tighten(args.recording, a, b) for a, b in speech[i * args.takes:(i + 1) * args.takes]]
        heard = [transcribe(args.recording, a, b, course.target if course else "fa") for a, b in takes]
        print(f"{text:>14}  ←  " + " | ".join(f"{a:.1f}s '{h}'" for (a, _), h in zip(takes, heard)))
        if args.dry_run:
            continue
        entries = [e for e in index.get(key, []) if e.get("speaker") != args.speaker]
        for n, (a, b) in enumerate(takes, 1):
            out = out_dir / f"{stem}-{n}.m4a"
            cut(args.recording, a, b, out)
            entries.append({"file": str(out.relative_to(index_path(settings).parent)), "speaker": args.speaker,
                            "source": args.recording.name, "start": round(a, 2), "end": round(b, 2)})
        index[key] = entries
    if not args.dry_run:
        index_path(settings).write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
        print(f"wrote {len(texts) * args.takes} clips; index: {index_path(settings)}")


if __name__ == "__main__":
    main()
