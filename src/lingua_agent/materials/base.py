"""Materials provider Protocol + shared types.

Every provider (LocalDir, RcloneDrive, future Dropbox/S3) exposes the
same five operations: availability check, list a folder, read a file's
bytes, fetch metadata for one entry, and a stable root identifier.

Paths are always **forward-slash, relative to the provider's root**.
The provider handles the OS-specific separator concerns internally so
callers can treat all sources uniformly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field


ProviderKind = Literal["local_dir", "rclone_drive"]


class MaterialsError(RuntimeError):
    """Raised when a provider can't satisfy a request — unavailable
    source, missing file, permission denied, network failure, etc."""


class MaterialEntry(BaseModel):
    """One file or folder inside a materials source.

    `path` is always relative to the provider's root with forward slashes,
    e.g. `"de/pimsleur/l1/audio/01.mp3"`. The empty string represents
    the root itself.
    """
    source: str
    path: str
    name: str
    is_dir: bool
    size_bytes: int | None = None
    mime_type: str | None = None
    modified_at: datetime | None = None


class MaterialsSourceConfig(BaseModel):
    """Persisted description of a materials source.

    Stored on `LearnerProfile.materials_sources`. The matching provider
    instance is built lazily via `materials.registry.build_provider`.
    """
    name: str = Field(min_length=1, description="Human-readable label, e.g. 'Transcend SSD'.")
    provider: ProviderKind
    root: str = Field(min_length=1,
                       description="Filesystem path for local_dir, e.g. '/media/arash/Transcend-Arash/05_Language'; "
                                   "rclone remote+path for rclone_drive, e.g. 'gdrive:3-Language'.")
    read_only: bool = True
    notes: str | None = None


class MaterialsProvider(Protocol):
    """The five-operation surface every provider implements."""

    name: str
    root: str

    def is_available(self) -> bool:
        """Cheap check: is the underlying source reachable right now?
        LocalDir checks `os.path.isdir`; RcloneDrive does a fast `lsd`.
        Never raises — returns False on any failure."""

    def list(self, folder: str = "") -> list[MaterialEntry]:
        """Return entries directly inside `folder` (relative to root).
        Empty string means the root. Raises `MaterialsError` if the
        source is unavailable or the folder doesn't exist."""

    def metadata(self, path: str) -> MaterialEntry:
        """Return metadata for a single entry. Raises `MaterialsError`
        if the entry doesn't exist."""

    def read(self, path: str) -> bytes:
        """Return the file's bytes. Raises `MaterialsError` on failure
        or if `path` is a folder."""
