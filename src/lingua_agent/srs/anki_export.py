"""Anki-compatible CSV export.

Produces a tab-separated file with the column order Anki's "Notes in Plain
Text" import expects by default: Front, Back, Tags. Extra metadata columns
follow; users can map them in Anki's import dialog.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from ..models.srs import Flashcard


COLUMNS = [
    "Front",
    "Back",
    "Tags",
    "SourceLanguage",
    "TargetLanguage",
    "Direction",
    "CardType",
    "Mnemonic",
    "Examples",
    "Id",
]


def export_cards_csv(cards: Iterable[Flashcard], output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(COLUMNS)
        for card in cards:
            writer.writerow([
                card.front,
                card.back,
                " ".join(card.tags) if card.tags else "",
                card.source_language,
                card.target_language,
                card.direction.value,
                card.card_type.value,
                card.mnemonic or "",
                " || ".join(card.examples) if card.examples else "",
                card.id,
            ])
    return output_path
