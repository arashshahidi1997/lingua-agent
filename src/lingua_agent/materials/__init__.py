"""Materials adapter — Phase 6c.

Abstracts over the different places a learner's source materials may live
(intermittent external SSD, Google Drive via rclone, future Dropbox / S3,
local inbox folder). The React PWA and the tutor agent can browse and
ingest from any configured source without caring about its provider type.

See docs/clients.md and docs/roadmap.md (Phase 6c) for the design
rationale.
"""

from .base import (
    MaterialEntry,
    MaterialsError,
    MaterialsProvider,
    MaterialsSourceConfig,
)
from .registry import build_provider, list_sources

__all__ = [
    "MaterialEntry",
    "MaterialsError",
    "MaterialsProvider",
    "MaterialsSourceConfig",
    "build_provider",
    "list_sources",
]
