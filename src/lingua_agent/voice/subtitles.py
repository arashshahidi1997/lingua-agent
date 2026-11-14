"""Parse .srt / .vtt / plain-text transcripts into timed cues."""

from __future__ import annotations

import re

_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_ARROW = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)")
_TAG = re.compile(r"<[^>]+>")


def _seconds(stamp: str) -> float:
    m = _TIME.fullmatch(stamp.strip())
    if not m:
        raise ValueError(f"bad timestamp: {stamp!r}")
    h, mnt, s, ms = m.groups()
    return int(h or 0) * 3600 + int(mnt) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_transcript(content: str, filename: str = "") -> list[dict]:
    """Return cues `{start, end, text}`. Plain text gives one untimed cue per non-empty line."""
    content = content.replace("\r\n", "\n").replace("﻿", "")
    if "-->" not in content:
        return [{"start": 0.0, "end": 0.0, "text": line.strip()}
                for line in content.split("\n") if line.strip()]
    cues: list[dict] = []
    for block in re.split(r"\n\s*\n", content):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            m = _ARROW.match(line)
            if not m:
                continue
            try:
                start, end = _seconds(m.group(1)), _seconds(m.group(2))
            except ValueError:
                break
            text = " ".join(_TAG.sub("", t).strip() for t in lines[i + 1:]).strip()
            if text:
                cues.append({"start": start, "end": end, "text": text})
            break
    return cues
