"""Local text-to-speech with Piper, and optional transcription with faster-whisper.

Both are optional. Piper voices live in `${data_dir}/voices/<lang>/<voice>.onnx`
(+ `.onnx.json`); `lingua-agent voices download <lang>` fetches the default one.
Synthesised audio is cached by (voice, text) in `${data_dir}/tts_cache/`, so each
sentence is synthesised once. Without Piper the web client falls back to the
browser's speechSynthesis.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import wave
from pathlib import Path

from ..config import Settings

# Default Piper voice per language (rhasspy/piper-voices on Hugging Face).
DEFAULT_VOICES: dict[str, str] = {
    "fa": "fa/fa_IR/amir/medium/fa_IR-amir-medium",
    "en": "en/en_US/lessac/medium/en_US-lessac-medium",
    "ru": "ru/ru_RU/irina/medium/ru_RU-irina-medium",
    "de": "de/de_DE/thorsten/medium/de_DE-thorsten-medium",
    "it": "it/it_IT/paola/medium/it_IT-paola-medium",
    "nl": "nl/nl_BE/nathalie/medium/nl_BE-nathalie-medium",
}
VOICES_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


class SpeechError(RuntimeError):
    pass


def voices_dir(settings: Settings) -> Path:
    return settings.shared_data_dir / "voices"


def find_voice(settings: Settings, lang: str) -> Path | None:
    d = voices_dir(settings) / lang
    if not d.exists():
        return None
    models = sorted(p for p in d.glob("*.onnx") if p.with_suffix(".onnx.json").exists())
    return models[0] if models else None


def _piper_backend() -> str | None:
    try:
        import piper  # noqa: F401
        return "python"
    except ImportError:
        pass
    return "binary" if shutil.which("piper") else None


def tts_available(settings: Settings, lang: str) -> bool:
    return _piper_backend() is not None and find_voice(settings, lang) is not None


_loaded: dict[str, object] = {}


def _synthesize_python(model: Path, text: str, out: Path) -> None:
    from piper import PiperVoice

    voice = _loaded.get(str(model))
    if voice is None:
        voice = PiperVoice.load(str(model))
        _loaded[str(model)] = voice
    with wave.open(str(out), "wb") as wf:
        if hasattr(voice, "synthesize_wav"):  # piper-tts >= 1.3
            voice.synthesize_wav(text, wf)
        else:  # older API writes the header itself
            voice.synthesize(text, wf)


def _synthesize_binary(model: Path, text: str, out: Path) -> None:
    proc = subprocess.run(["piper", "--model", str(model), "--output_file", str(out)],
                          input=text.encode("utf-8"), capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise SpeechError(proc.stderr.decode("utf-8", "replace")[-500:])


def _cache_path(settings: Settings, text: str, model: Path) -> Path:
    key = hashlib.sha256(f"{model.name}\x1f{text}".encode("utf-8")).hexdigest()[:24]
    return settings.shared_data_dir / "tts_cache" / f"{key}.wav"


def is_cached(settings: Settings, text: str, lang: str) -> bool:
    model = find_voice(settings, lang)
    path = _cache_path(settings, " ".join(text.split()), model) if model else None
    return bool(path and path.exists() and path.stat().st_size > 44)


def synthesize(settings: Settings, text: str, lang: str) -> Path:
    """Return the path of a cached WAV for `text`; synthesise it on first request."""
    text = " ".join(text.split())
    if not text:
        raise SpeechError("empty text")
    if len(text) > 1000:
        raise SpeechError("text too long (max 1000 characters)")
    backend = _piper_backend()
    model = find_voice(settings, lang)
    if backend is None or model is None:
        raise SpeechError(f"no local voice for {lang!r}")
    out = _cache_path(settings, text, model)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 44:
        return out
    tmp = out.with_suffix(".tmp.wav")
    (_synthesize_python if backend == "python" else _synthesize_binary)(model, text, tmp)
    tmp.replace(out)
    return out


def download_voice(settings: Settings, lang: str, *, voice: str | None = None) -> Path:
    """Fetch a Piper voice (model + config) into the voices dir."""
    import httpx

    rel = voice or DEFAULT_VOICES.get(lang)
    if not rel:
        raise SpeechError(f"no default voice for {lang!r}; pass one, e.g. fa/fa_IR/gyro/medium/fa_IR-gyro-medium")
    dest = voices_dir(settings) / lang
    dest.mkdir(parents=True, exist_ok=True)
    name = rel.rsplit("/", 1)[-1]
    for suffix in (".onnx.json", ".onnx"):
        target = dest / f"{name}{suffix}"
        if target.exists():
            continue
        tmp = target.with_suffix(target.suffix + ".part")
        with httpx.stream("GET", f"{VOICES_BASE_URL}/{rel}{suffix}", follow_redirects=True, timeout=60) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
        tmp.replace(target)
    return dest / f"{name}.onnx"


# ---- transcription (optional) -----------------------------------------------------

def stt_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def transcribe_cues(path: Path, *, language: str | None = None, model_size: str = "small") -> list[dict]:
    """Sentence-level cues with timestamps. Raises SpeechError if faster-whisper is missing."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SpeechError("faster-whisper is not installed (pip install faster-whisper)") from exc
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    try:
        segments, _info = model.transcribe(str(path), language=language, vad_filter=True)
        return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    except Exception as exc:  # undecodable or corrupt audio
        raise SpeechError(f"couldn't read this audio ({type(exc).__name__})") from exc
