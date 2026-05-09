"""Repository protocol + JSON-on-disk implementation.

One file per entity under `${data_dir}/<bucket>/<id>.json`. Atomic writes via
write-then-rename. SQLite implementation is a future swap behind the same
Protocol — see `docs/decisions.md` D3.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generic, Iterable, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Repository(Protocol[T]):
    def save(self, entity: T) -> T: ...
    def get(self, entity_id: str) -> T | None: ...
    def list(self) -> list[T]: ...
    def delete(self, entity_id: str) -> bool: ...


class JsonRepository(Generic[T]):
    def __init__(self, root: Path, bucket: str, model: type[T], *, id_field: str = "id"):
        self.dir = root / bucket
        self.dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.id_field = id_field

    def _path(self, entity_id: str) -> Path:
        # Keep IDs flat; slashes are not expected but rejected just in case.
        if "/" in entity_id or ".." in entity_id:
            raise ValueError(f"unsafe id: {entity_id!r}")
        return self.dir / f"{entity_id}.json"

    def save(self, entity: T) -> T:
        entity_id = getattr(entity, self.id_field)
        path = self._path(entity_id)
        payload = entity.model_dump(mode="json")
        # Atomic write: tmpfile then rename, both inside the same directory.
        fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=self.dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise
        return entity

    def get(self, entity_id: str) -> T | None:
        path = self._path(entity_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return self.model.model_validate(data)

    def list(self) -> list[T]:
        out: list[T] = []
        for p in sorted(self.dir.glob("*.json")):
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            out.append(self.model.model_validate(data))
        return out

    def delete(self, entity_id: str) -> bool:
        path = self._path(entity_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def filter(self, **predicates: Any) -> Iterable[T]:
        for entity in self.list():
            if all(getattr(entity, k, None) == v for k, v in predicates.items()):
                yield entity
