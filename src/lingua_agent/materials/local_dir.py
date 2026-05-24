"""LocalDir materials provider — filesystem-backed.

Handles the intermittently-mounted-SSD case gracefully: `is_available()`
checks whether the root exists right now, and `list()`/`read()` raise
`MaterialsError` with a clear message when the source has gone away.
"""

from __future__ import annotations

import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import MaterialEntry, MaterialsError, MaterialsProvider


class LocalDirProvider:
    """Reads materials directly from a filesystem path."""

    name: str
    root: str

    def __init__(self, name: str, root: str):
        self.name = name
        self.root = root
        self._root_path = Path(root)

    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            return self._root_path.is_dir()
        except OSError:
            return False

    def list(self, folder: str = "") -> list[MaterialEntry]:
        target = self._resolve(folder)
        if not target.is_dir():
            raise MaterialsError(f"not a directory: {folder!r}")
        out: list[MaterialEntry] = []
        try:
            with os.scandir(target) as it:
                for entry in it:
                    if entry.name.startswith("."):
                        # Hide dotfiles (.DS_Store, ._*, etc.) at the
                        # provider level so the UI stays clean.
                        continue
                    rel = self._relativize(Path(entry.path))
                    out.append(self._make_entry(entry, rel))
        except OSError as exc:
            raise MaterialsError(f"failed to list {folder!r}: {exc}") from exc
        # Folders first, then alphabetical
        out.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return out

    def metadata(self, path: str) -> MaterialEntry:
        target = self._resolve(path)
        if not target.exists():
            raise MaterialsError(f"not found: {path!r}")
        try:
            stat = target.stat()
        except OSError as exc:
            raise MaterialsError(f"stat failed for {path!r}: {exc}") from exc
        is_dir = target.is_dir()
        mime, _ = mimetypes.guess_type(target.name) if not is_dir else (None, None)
        return MaterialEntry(
            source=self.name,
            path=self._relativize(target),
            name=target.name,
            is_dir=is_dir,
            size_bytes=None if is_dir else stat.st_size,
            mime_type=mime,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

    def read(self, path: str) -> bytes:
        target = self._resolve(path)
        if target.is_dir():
            raise MaterialsError(f"is a directory, not a file: {path!r}")
        try:
            return target.read_bytes()
        except OSError as exc:
            raise MaterialsError(f"read failed for {path!r}: {exc}") from exc

    # ------------------------------------------------------------------
    # Path safety: every input path must resolve inside the root.

    def _resolve(self, rel: str) -> Path:
        if not self.is_available():
            raise MaterialsError(
                f"source {self.name!r} (root {self.root!r}) is not available "
                "right now — is the drive mounted?"
            )
        rel = (rel or "").strip().strip("/")
        if not rel:
            return self._root_path
        candidate = (self._root_path / rel).resolve()
        # Defense-in-depth: refuse paths that escape the root via `..`.
        try:
            candidate.relative_to(self._root_path.resolve())
        except ValueError:
            raise MaterialsError(f"path escapes root: {rel!r}")
        return candidate

    def _relativize(self, abs_path: Path) -> str:
        rel = abs_path.relative_to(self._root_path.resolve()) \
            if abs_path.is_absolute() else abs_path
        # Always forward-slash, even on Windows.
        return rel.as_posix() if str(rel) != "." else ""

    def _make_entry(self, dir_entry: os.DirEntry, rel: str) -> MaterialEntry:
        try:
            stat = dir_entry.stat(follow_symlinks=True)
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            size = stat.st_size if not dir_entry.is_dir() else None
        except OSError:
            mtime, size = None, None
        mime, _ = mimetypes.guess_type(dir_entry.name) if not dir_entry.is_dir() else (None, None)
        return MaterialEntry(
            source=self.name,
            path=rel,
            name=dir_entry.name,
            is_dir=dir_entry.is_dir(),
            size_bytes=size,
            mime_type=mime,
            modified_at=mtime,
        )


# Static type sanity: LocalDirProvider satisfies the Protocol.
_check: type[MaterialsProvider] = LocalDirProvider  # type: ignore[assignment]
