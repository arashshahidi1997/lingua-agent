"""Materials registry — turns persisted MaterialsSourceConfig into a live MaterialsProvider.

Caller pattern:
    profile = load_learner_profile()
    for cfg in profile.materials_sources:
        provider = build_provider(cfg)
        if provider.is_available():
            for entry in provider.list():
                ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import MaterialsError, MaterialsProvider, MaterialsSourceConfig

if TYPE_CHECKING:  # avoid runtime circular import: learner.py imports MaterialsSourceConfig
    from ..models.learner import LearnerProfile


def build_provider(cfg: MaterialsSourceConfig) -> MaterialsProvider:
    if cfg.provider == "local_dir":
        from .local_dir import LocalDirProvider
        return LocalDirProvider(name=cfg.name, root=cfg.root)
    if cfg.provider == "rclone_drive":
        from .rclone_drive import RcloneDriveProvider
        return RcloneDriveProvider(name=cfg.name, root=cfg.root)
    raise MaterialsError(f"unknown provider kind: {cfg.provider!r}")


def list_sources(profile: "LearnerProfile") -> list[MaterialsSourceConfig]:
    """Return the sources configured on the profile. Empty list if none."""
    return list(profile.materials_sources)


def find_source(profile: "LearnerProfile", name: str) -> MaterialsSourceConfig | None:
    for src in profile.materials_sources:
        if src.name == name:
            return src
    return None
