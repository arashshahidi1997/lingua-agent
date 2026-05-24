"""RcloneDrive materials provider — Google Drive (or any rclone remote) via subprocess.

Uses `rclone lsjson` for listing and `rclone cat` for reading. The user
must have `rclone` installed and a remote configured (see
docs/clients.md for setup); we don't ship rclone or its config.

Why subprocess and not a Google API client:
- rclone's auth is already configured on this user's machine and works
  across all their remotes (Drive, Dropbox, S3, ...); reusing it means
  one auth surface instead of N per-provider OAuth flows.
- The Drive Python SDK would add ~5 transitive deps for capability we
  already have for free.
- `rclone lsjson` returns rich, typed JSON exactly matching what we
  want to expose to the UI.
"""

from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
from datetime import datetime
from typing import Any

from .base import MaterialEntry, MaterialsError, MaterialsProvider


# Default 30 s per call — Drive can be slow on large folders.
_DEFAULT_TIMEOUT = 30.0


class RcloneDriveProvider:
    """Reads materials from an rclone remote, e.g. `gdrive:3-Language`."""

    name: str
    root: str

    def __init__(self, name: str, root: str, *, timeout: float = _DEFAULT_TIMEOUT,
                 rclone_bin: str | None = None):
        self.name = name
        self.root = root.rstrip("/")
        self._timeout = timeout
        self._rclone = rclone_bin or shutil.which("rclone")

    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        if not self._rclone:
            return False
        try:
            # Cheap probe — list the top-level of the remote root.
            result = subprocess.run(
                [self._rclone, "lsf", "--max-depth", "1", self.root],
                capture_output=True, text=True, timeout=min(self._timeout, 10.0),
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def list(self, folder: str = "") -> list[MaterialEntry]:
        body = self._lsjson(folder)
        out: list[MaterialEntry] = []
        for item in body:
            name = item.get("Name") or item.get("Path") or ""
            if name.startswith("."):
                continue  # hide dotfiles
            is_dir = bool(item.get("IsDir"))
            rel_path = (folder.rstrip("/") + "/" + name).lstrip("/") if folder else name
            mime = item.get("MimeType")
            if not mime and not is_dir:
                mime, _ = mimetypes.guess_type(name)
            mtime = _parse_iso(item.get("ModTime"))
            out.append(MaterialEntry(
                source=self.name,
                path=rel_path,
                name=name,
                is_dir=is_dir,
                size_bytes=None if is_dir else item.get("Size"),
                mime_type=mime,
                modified_at=mtime,
            ))
        out.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return out

    def metadata(self, path: str) -> MaterialEntry:
        # rclone lsjson of the parent + filter by name.
        path = (path or "").strip("/")
        if not path:
            return MaterialEntry(source=self.name, path="", name=self.root,
                                  is_dir=True)
        parent, _, leaf = path.rpartition("/")
        entries = self.list(parent)
        for e in entries:
            if e.name == leaf:
                return e
        raise MaterialsError(f"not found: {path!r}")

    def read(self, path: str) -> bytes:
        if not self._rclone:
            raise MaterialsError("rclone binary not found on PATH")
        path = (path or "").strip("/")
        if not path:
            raise MaterialsError("read() requires a file path, not the root")
        target = f"{self.root}/{path}"
        try:
            result = subprocess.run(
                [self._rclone, "cat", target],
                capture_output=True, timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise MaterialsError(f"rclone cat timed out after {self._timeout}s for {path!r}") from exc
        except OSError as exc:
            raise MaterialsError(f"rclone cat failed for {path!r}: {exc}") from exc
        if result.returncode != 0:
            raise MaterialsError(
                f"rclone cat returned {result.returncode} for {path!r}: "
                f"{result.stderr.decode('utf-8', errors='replace')[:500]}"
            )
        return result.stdout

    # ------------------------------------------------------------------

    def _lsjson(self, folder: str) -> list[dict[str, Any]]:
        if not self._rclone:
            raise MaterialsError("rclone binary not found on PATH")
        target = self.root + (("/" + folder.strip("/")) if folder else "")
        try:
            result = subprocess.run(
                [self._rclone, "lsjson", "--no-modtime", "--no-mimetype", "--fast-list", target],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise MaterialsError(f"rclone lsjson timed out after {self._timeout}s for {folder!r}") from exc
        except OSError as exc:
            raise MaterialsError(f"rclone lsjson failed for {folder!r}: {exc}") from exc
        if result.returncode != 0:
            raise MaterialsError(
                f"rclone lsjson returned {result.returncode} for {folder!r}: "
                f"{result.stderr[:500]}"
            )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MaterialsError(f"rclone lsjson returned non-JSON for {folder!r}: {exc}") from exc


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # rclone returns ISO-8601 like "2026-05-17T18:04:11.123Z"
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


_check: type[MaterialsProvider] = RcloneDriveProvider  # type: ignore[assignment]
