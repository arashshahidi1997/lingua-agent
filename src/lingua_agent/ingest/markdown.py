"""Markdown file ingestion — read frontmatter + body."""

from __future__ import annotations

from pathlib import Path

import frontmatter


def read_markdown(path: Path) -> tuple[dict, str]:
    """Return (metadata, body) from a markdown file with optional YAML frontmatter."""
    path = Path(path)
    post = frontmatter.load(path)
    return dict(post.metadata), post.content
