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
MIN_MATCH = 0.55        # a take must match its text at least this well (else the text keeps synthetic speech)


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


def tighten(path: Path, start: float, end: float, step: float = 0.05, *, single_word: bool = True
            ) -> tuple[float, float]:
    """Drop a breath or noise tail: after the word, if the level dips 25 dB below its peak and never comes
    back within 15 dB of it, the take ends at the dip. A pause between syllables comes back up, so stays.
    Only for single words: in a sentence a loud first word («سلام!») can be followed by quieter speech."""
    rms = rms_frames(path, start, end, step)
    if not rms:
        return start, end
    peak = max(rms)
    first = next((i for i, v in enumerate(rms) if v > peak - 30), 0)
    cut_at = len(rms)
    for i in range(first + 1, len(rms) if single_word else 0):
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


# ---- alignment by transcript (phrases, uneven takes) ------------------------------------

_DIACRITICS = re.compile("[\u064B-\u065F\u0670\u200c\u200d\u200e\u200f.,!?؟،:;«»\"'()…-]")


def fa_norm(text: str) -> str:
    """Comparable Persian: no diacritics, ZWNJ or punctuation; Arabic ي/ك/ة as Persian; no spaces."""
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه").replace("أ", "ا").replace("إ", "ا")
    return _DIACRITICS.sub("", text).replace(" ", "")


def _whisper():
    from faster_whisper import WhisperModel
    global _model
    if "_model" not in globals():
        _model = WhisperModel("medium", device="cpu", compute_type="int8")
    return _model


def units(path: Path, segs: list[tuple[float, float]], lang: str) -> list[tuple[float, float, str, int]]:
    """Spoken words with times: each pause-separated segment is transcribed on its own (Whisper drops
    repeats in long audio). Matching works on words, so a take can start or end inside a segment."""
    out: list[tuple[float, float, str, int]] = []
    for seg_no, (a, b) in enumerate(segs):
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            s0 = max(0.0, a - 0.2)
            _ffmpeg("-y", "-ss", f"{s0:.3f}", "-t", f"{b - a + 0.4:.3f}", "-i", str(path), "-ac", "1", "-ar", "16000",
                    tmp.name)
            parts, _ = _whisper().transcribe(tmp.name, language=lang, beam_size=5, word_timestamps=True,
                                             condition_on_previous_text=False)
            words = [(s0 + w.start, s0 + w.end, w.word.strip(), seg_no)
                     for p in parts for w in (p.words or []) if w.word.strip()]
        if words:
            # Keep the segment's own outer edges: Whisper's word times are loose at the ends.
            words[0] = (min(words[0][0], a), *words[0][1:])
            words[-1] = (words[-1][0], max(words[-1][1], b), *words[-1][2:])
            out.extend(words)
        else:
            out.append((a, b, "", seg_no))
    return out


def _sim(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    x, y = fa_norm(a), fa_norm(b)
    return SequenceMatcher(None, x, y).ratio() if x and y else 0.0


def align(us: list[tuple[float, float, str, int]], texts: list[str], once: bool = False
          ) -> list[list[tuple[float, float, str, float, float, float]]]:
    """Assign speech units to texts, in order: every text gets one or more takes, a take is 1..max_join
    consecutive units, units may be skipped as noise. Dynamic programming over (unit, text)."""
    n_u, n_t = len(us), len(texts)
    NEG = float("-inf")
    SKIP, NEXT_EMPTY = -0.35, -1.5           # skipping a unit; a text with no take at all
    TAKE_COST = 0.3                          # each take must be worth it: one whole word beats two halves
    # best[i][j][k]: units[:i] used, at text j, k = has text j got a take yet
    best = [[[NEG, NEG] for _ in range(n_t + 1)] for _ in range(n_u + 1)]
    back: dict = {}
    best[0][0][0] = 0.0
    for i in range(n_u + 1):
        for j in range(n_t + 1):
            for k in (0, 1):
                cur = best[i][j][k]
                if cur == NEG:
                    continue
                if j < n_t:  # move on to the next text
                    nj, val = j + 1, cur + (0 if k else NEXT_EMPTY)
                    if val > best[i][nj][0]:
                        best[i][nj][0] = val
                        back[(i, nj, 0)] = (i, j, k, None)
                if i < n_u:  # a unit is noise
                    val = cur + SKIP
                    if val > best[i + 1][j][k]:
                        best[i + 1][j][k] = val
                        back[(i + 1, j, k)] = (i, j, k, None)
                if i < n_u and j < n_t and not (once and k):  # a take of text j: about as many words as it has
                    for m in range(1, len(texts[j].split()) + 4):
                        if i + m > n_u or us[i + m - 1][1] - us[i][0] > 0.9 * len(texts[j].split()) + 1.2:
                            break
                        heard = " ".join(u[2] for u in us[i:i + m])
                        sc = _sim(texts[j], heard)
                        val = cur + (sc - 0.5) * 2 - TAKE_COST
                        if val > best[i + m][j][1]:
                            best[i + m][j][1] = val
                            back[(i + m, j, 1)] = (i, j, k, (i, i + m, heard, round(sc, 2)))
    # end: all units used, all texts visited (the last one with a take, or given up on)
    end = max(((n_u, n_t, 0), (n_u, n_t - 1, 1), (n_u, n_t - 1, 0)),
              key=lambda s: best[s[0]][s[1]][s[2]] + (NEXT_EMPTY if s == (n_u, n_t - 1, 0) else 0))
    picked: list[tuple[int, int, int, str, float]] = []   # (text, first word, end word, heard, score)
    state = end
    while state in back:
        pi, pj, pk, take = back[state]
        if take:
            a, b, heard, sc = take
            picked.insert(0, (state[1], a, b, heard, sc))
        state = (pi, pj, pk)
    # Weak matches go first: a dropped take must neither block the extension below nor be cut against.
    picked = [p for p in picked if p[4] >= MIN_MATCH]
    # A take that stops inside a spoken segment takes in the rest of it when nothing else claims those words
    # (Whisper sometimes splits one word in two, e.g. پسر → «پس» + «اف»; cutting there would clip the word).
    owner = {w: idx for idx, (_, a, b, _, _) in enumerate(picked) for w in range(a, b)}
    result: list[list[tuple[float, float, str, float, float, float]]] = [[] for _ in texts]
    for idx, (t, a, b, heard, sc) in enumerate(picked):
        # Only over words that run on without a gap, and never beyond a sensible length for the text.
        longest = 0.9 * len(texts[t].split()) + 1.2

        def fits(lo: int, hi: int) -> bool:
            return us[hi - 1][1] - us[lo][0] <= longest

        while (a > 0 and us[a - 1][3] == us[a][3] and (a - 1) not in owner
               and us[a][0] - us[a - 1][1] < 0.25 and fits(a - 1, b)):
            a -= 1
            owner[a] = idx
        while (b < n_u and us[b][3] == us[b - 1][3] and b not in owner
               and us[b][0] - us[b - 1][1] < 0.25 and fits(a, b + 1)):
            owner[b] = idx
            b += 1
        prev_end = us[a - 1][1] if a > 0 else 0.0
        next_start = us[b][0] if b < n_u else us[b - 1][1] + 5.0
        result[t].append((us[a][0], us[b - 1][1], heard, sc, prev_end, next_start))
    return result


def split_touching(path: Path, aligned: list[list[tuple]]) -> list[list[tuple]]:
    """Takes spoken without a pause between them touch; cut at the quietest moment between them (the
    breath break) instead of trusting Whisper's word times."""
    flat = sorted(((t[0], ti, ki) for ti, takes in enumerate(aligned) for ki, t in enumerate(takes)))
    out = [[list(t) for t in takes] for takes in aligned]
    for (_, ti1, ki1), (_, ti2, ki2) in zip(flat, flat[1:]):
        first, second = out[ti1][ki1], out[ti2][ki2]
        if second[0] - first[1] > 0.08:
            continue  # a real pause already separates them
        lo, hi = first[0] + 0.25, second[1] - 0.25
        if hi - lo < 0.1:
            continue
        rms = rms_frames(path, lo, hi, 0.03)
        if not rms:
            continue
        # The quietest frame, preferring the middle of the span when several are about as quiet.
        mid = len(rms) / 2
        k = min(range(len(rms)), key=lambda i: (rms[i] + abs(i - mid) * 0.05))
        cut_at = lo + (k + 0.5) * 0.03
        first[1], first[5] = cut_at, cut_at
        second[0], second[4] = cut_at, cut_at
    return [[tuple(t) for t in takes] for takes in out]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording", type=Path)
    ap.add_argument("--course", default="fa-en-a1")
    ap.add_argument("--lesson", help="course lesson id whose items were read, in order")
    ap.add_argument("--story", help="story/dialogue id whose lines were read, in order")
    ap.add_argument("--scenario", help="role-play id whose opener and useful phrases were read, in order")
    ap.add_argument("--texts", help="comma-separated texts instead of --lesson")
    ap.add_argument("--takes", type=int, default=0, help="takes per text; 0 = work it out from the count (3, 2 or 1)")
    ap.add_argument("--speaker", default="Arash")
    ap.add_argument("--dry-run", action="store_true", help="show the matching, write nothing")
    ap.add_argument("--align", action="store_true",
                    help="match by transcript even when the take count fits (sentences read once, words 3 times)")
    args = ap.parse_args()

    settings = Settings.load(cwd=ROOT)
    course = store.get_course(settings, args.course)
    if args.lesson:
        found = course.lesson(args.lesson) if course else None
        if not found:
            sys.exit(f"lesson not found: {args.lesson}")
        texts = [it.text for it in found[1].items]
    elif args.story:
        st = course.story(args.story) if course else None
        if not st:
            sys.exit(f"story not found: {args.story}")
        texts = [ln.text for ln in st.lines]
    elif args.scenario:
        sc = course.scenario(args.scenario) if course else None
        if not sc:
            sys.exit(f"scenario not found: {args.scenario}")
        texts = [p.text for p in [sc.opener, *sc.useful]]
    elif args.texts:
        texts = [t.strip() for t in args.texts.split(",") if t.strip()]
    else:
        sys.exit("give --lesson, --story, --scenario or --texts")

    segs = speech_segments(args.recording)
    speech = [(a, b) for a, b in segs if mean_volume(args.recording, a, b - a) > QUIET_MEAN_DB]
    dropped = len(segs) - len(speech)
    if not args.takes:
        args.takes = next((t for t in (3, 2, 1) if len(speech) == len(texts) * t), 3)
    want = len(texts) * args.takes
    print(f"{args.recording.name}: {len(segs)} segments, {dropped} quiet (noise) dropped, {len(speech)} takes; "
          f"expected {len(texts)} × {args.takes} = {want}")
    lang = course.target if course else "fa"
    args.lang_code = lang
    if len(speech) != want or args.align:
        print("  aligning by transcript (takes per text may differ)")
        # Dialogue lines and role-play phrases are read once; words and lesson phrases usually several times.
        aligned = align(units(args.recording, speech, lang), texts, once=bool(args.story or args.scenario))
        aligned = split_touching(args.recording, aligned)
        plan = []
        for text, takes in zip(texts, aligned):
            good = [t for t in takes if t[3] >= MIN_MATCH]
            dropped = len(takes) - len(good)
            print(f"{text:>22}  ←  " + (" | ".join(f"{t[0]:.1f}s '{t[2]}' {t[3]}" for t in good) or "NOT FOUND")
                  + (f"   ({dropped} weak match{'es' if dropped > 1 else ''} dropped)" if dropped else ""))
            # Whisper's word times are loose: widen a little, but never past halfway to the neighbouring
            # words, then let the energy trim decide the edges.
            spans = [tighten(args.recording, max(a - 0.15, (prev + a) / 2), min(b + 0.25, (b + nxt) / 2),
                             single_word=len(text.split()) == 1)
                     for a, b, _, _, prev, nxt in good]
            plan.append((text, spans))
        write(args, settings, plan)
        return

    plan = []
    for i, text in enumerate(texts):
        takes = [tighten(args.recording, a, b, single_word=len(text.split()) == 1)
                 for a, b in speech[i * args.takes:(i + 1) * args.takes]]
        heard = [transcribe(args.recording, a, b, lang) for a, b in takes]
        print(f"{text:>14}  ←  " + " | ".join(f"{a:.1f}s '{h}'" for (a, _), h in zip(takes, heard)))
        plan.append((text, takes))
    write(args, settings, plan)


def write(args, settings: Settings, plan: list[tuple[str, list[tuple[float, float]]]]) -> None:
    if args.dry_run:
        return
    out_dir = index_path(settings).parent / args.speaker.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    index = load_index(settings)
    written = 0
    for text, takes in plan:
        if not takes:
            continue
        key = norm(text)
        stem = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        # Keep takes from other recordings of the same text (another speaker, or another file of yours).
        entries = [e for e in index.get(key, [])
                   if e.get("speaker") != args.speaker or e.get("source") != args.recording.name]
        start_n = len([e for e in entries if e.get("speaker") == args.speaker]) + 1
        for n, (a, b) in enumerate(takes, start_n):
            out = out_dir / f"{stem}-{n}.m4a"
            cut(args.recording, a, b, out)
            # Check the finished clip: transcribe it again and compare with the text it should say.
            heard = " ".join(x.text.strip() for x in _whisper().transcribe(str(out), language=args.lang_code,
                                                                          beam_size=5)[0])
            score = _sim(text, heard)
            flag = "" if score >= 0.6 else "   <-- CHECK"
            print(f"    clip {out.name} {b - a:4.2f}s heard '{heard}' {score:.2f}{flag}")
            entries.append({"file": str(out.relative_to(index_path(settings).parent)), "speaker": args.speaker,
                            "source": args.recording.name, "start": round(a, 2), "end": round(b, 2)})
            written += 1
        index[key] = entries
    index_path(settings).write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
    print(f"wrote {written} clips; index: {index_path(settings)}")


if __name__ == "__main__":
    main()
