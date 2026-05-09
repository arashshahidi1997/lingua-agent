"""Language-pair value object."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .registry import Language, get_language


class LanguagePair(BaseModel):
    source: Language
    target: Language
    support: Language | None = Field(default=None, description="Optional helper language for explanations.")

    @model_validator(mode="after")
    def _distinct_source_target(self) -> "LanguagePair":
        if self.source.code == self.target.code:
            raise ValueError("source_language and target_language must differ")
        return self

    @classmethod
    def from_codes(cls, source: str, target: str, support: str | None = None) -> "LanguagePair":
        return cls(
            source=get_language(source),
            target=get_language(target),
            support=get_language(support) if support else None,
        )

    @property
    def key(self) -> str:
        return f"{self.source.code}->{self.target.code}"

    def is_rtl_target(self) -> bool:
        return self.target.direction.value == "rtl"
