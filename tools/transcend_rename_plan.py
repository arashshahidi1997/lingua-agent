"""Generate a dry-run rename plan for /media/arash/Transcend-Arash/05_Language.

Walks the entire tree, computes a normalized target path for every entry,
and writes a TSV `tools/transcend_rename_plan.tsv` with:

    action  current_path  proposed_path  reason

Actions (NO file is ever deleted by the apply step):
- KEEP        — already in canonical place, no rename needed
- RENAME      — move/rename to the proposed path
- QUARANTINE  — junk files (.DS_Store, ._*, Desktop.ini, irlanguage.com.url, ...)
                are moved into _junk/ preserving original structure, so you
                can review and decide what to actually delete later.
- FLAG        — needs human decision; current_path stays untouched until
                you fill in the proposed_path manually

The script does NOT touch the filesystem. Run, review the TSV, edit if
desired, then a separate `transcend_apply_renames.py` (built later, only
after approval) executes the plan.

Usage:
    python tools/transcend_rename_plan.py
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path("/media/arash/Transcend-Arash/05_Language")
OUT  = Path(__file__).parent / "transcend_rename_plan.tsv"

# ---------------------------------------------------------------------------
# Top-level mapping: source folder/file at depth 1 → (target prefix | None for delete | "FLAG")
# ---------------------------------------------------------------------------

TOP_LEVEL: dict[str, str | None] = {
    # Already-language-named folders → ISO 639-1 codes
    "Deutsch":                  "de",
    "German":                   "de",
    "English":                  "en",
    # Mixed-language container; split per-file via SPECIAL_FILES below
    "06_Novels":                "__SPLIT_06_NOVELS__",
    # FME Method top-level wrapper goes away; its children fold into per-language dirs
    "FME Method":               "__FME_CHILDREN__",
    # macOS junk
    ".DS_Store":                None,
}

# FME Method children → ISO codes
FME_CHILDREN: dict[str, str] = {
    "Arabic":           "ar",
    "Danish":           "da",
    "Dutch":            "nl",
    "French":           "fr",
    "German":           "de",        # rar archives — relocate under de/_archives/
    "German_unzipped":  "de",        # actual extracted content — primary
    "Indian":           "hi",        # FLAG: confirm Hindi vs other
    "Italian":          "it",
    "Japanese":         "ja",
    "Polish":           "pl",
    "Russian":          "ru",
    "Spanish":          "es",
    "Swedish":          "sv",
    "Turkish":          "tr",
}

# When the FME folder is "German" (not _unzipped) we drop archives into _archives.
FME_GERMAN_ARCHIVE_PREFIX = "de/_archives"

# Per-file mapping for 06_Novels (multilingual)
NOVELS_06: dict[str, str] = {
    "A Song of Ice and Fire.epub":  "en/novels/a_song_of_ice_and_fire.epub",
    "A Song of Ice and Fire.pdf":   "en/novels/a_song_of_ice_and_fire.pdf",
    "GOT Season 8 Script.pdf":      "en/novels/got_s08_script.pdf",
    # Persian audiobook directory; contents get individually slugified below
    "بار هستی":                       "fa/novels/bar_e_hasti",
}

# Root-level files outside any language folder
ROOT_FILES: dict[str, str] = {
    "Ikenna D. Obi - Fluency Made Easy (2019).pdf":
        "_shared/ikenna_obi_fluency_made_easy_2019.pdf",
    "(The Farlex Grammar Book) Farlex International - Complete English Grammar Rules_ Examples, Exceptions, Exercises, and Everything You Need to Master Proper Grammar. 1-Farlex International (2016).pdf":
        "en/grammar/farlex_complete_english_grammar_2016.pdf",
    "DAF KOMPAKT A1-B1 KURSBUCH.pdf":
        "de/daf_kompakt/kursbuch_a1_b1.pdf",
}

# ---------------------------------------------------------------------------
# Slugify + filters
# ---------------------------------------------------------------------------

PIRACY_RE = re.compile(r"\s*\[\s*www\.[^\]]+\]", re.IGNORECASE)


def is_macos_junk(name: str) -> bool:
    return name == ".DS_Store" or name.startswith("._") or name == ".localized"


def is_piracy_decoration(name: str) -> bool:
    """Files left behind by piracy redistribution sites — pure noise."""
    n = name.lower()
    if n in {"desktop.ini", "thumbs.db"}:
        return True
    if n.startswith("irlanguage.com.") or n.startswith("vatandownload.com."):
        return True
    return False


def slugify(name: str, *, keep_ext: bool = True) -> str:
    """snake_case_lowercase, ASCII-friendly, preserves extension if any.
    Non-extension dots become underscores (so "D." in author names doesn't
    survive as "d.")."""
    stem, dot, ext = name.rpartition(".")
    if not dot or len(ext) > 8 or "/" in ext:  # not really an extension
        stem, ext = name, ""
    elif not keep_ext:
        ext = ""
    s = PIRACY_RE.sub("", stem)
    s = re.sub(r"[\s\-/.]+", "_", s)  # treat dots in stem as separators
    # Keep word chars + Persian (U+0600-06FF), Devanagari, Cyrillic
    s = re.sub(r"[^\w؀-ۿऀ-ॿЀ-ӿ]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s.lower() + ("." + ext.lower() if ext else "")).strip(".")


# ---------------------------------------------------------------------------
# Resource-folder normalization for FME Method / language top-level
# ---------------------------------------------------------------------------

PIMSLEUR_LEVEL_RE = re.compile(
    r"Pimsleur[\s.]+(?:[A-Za-z]+\s+)?([IV]+|\d+)\b", re.IGNORECASE
)
GLOSSIKA_VOLUME_RE = re.compile(r"glossika\s+\w+[-\s]+(\d+)", re.IGNORECASE)
ASSIMIL_RE = re.compile(r"^Assimil\b", re.IGNORECASE)


def roman_to_int(s: str) -> int:
    s = s.upper()
    if s.isdigit():
        return int(s)
    table = {"I": 1, "V": 5, "X": 10}
    out, prev = 0, 0
    for ch in reversed(s):
        v = table.get(ch, 0)
        out += -v if v < prev else v
        prev = v
    return out


def normalize_resource_folder(name: str) -> str | None:
    """Return the new folder name for a top-level resource folder, or None
    if we can't classify it (caller should keep slugified name)."""
    n = name.strip()

    # Pimsleur level (audio dirs are messy, e.g. "Pimsleur.German III [...]")
    m = PIMSLEUR_LEVEL_RE.search(n)
    if m and "pimsleur" in n.lower():
        try:
            return f"pimsleur/l{roman_to_int(m.group(1))}"
        except Exception:
            pass

    if "pimsleur" in n.lower() and ".swiss" in n.lower():
        return "pimsleur/swiss"

    if n.lower().startswith("pimsleur"):
        return "pimsleur"

    if ASSIMIL_RE.match(n):
        return "assimil"

    m = GLOSSIKA_VOLUME_RE.search(n)
    if m:
        return f"glossika/v{int(m.group(1))}"

    if "glossika" in n.lower():
        return "glossika"

    if "michel" in n.lower() and "thomas" in n.lower():
        return "michel_thomas"

    return None


# ---------------------------------------------------------------------------
# Pimsleur sub-folders inside a level dir (Audio, PDF & Word, etc.)
# ---------------------------------------------------------------------------

def normalize_pimsleur_subfolder(name: str) -> str | None:
    n = PIRACY_RE.sub("", name).strip().lower()
    if n.startswith("audio"):
        return "audio"
    if "pdf" in n or "word" in n or "booklet" in n or "transcript" in n:
        return "booklet"
    return None


# ---------------------------------------------------------------------------
# Walker
# ---------------------------------------------------------------------------

def main() -> None:
    if not ROOT.exists():
        raise SystemExit(f"ROOT not present: {ROOT}  (is the SSD mounted?)")

    rows: list[tuple[str, str, str, str]] = []
    counters: Counter[str] = Counter()

    # Walk every entry recursively; produce a row per file AND per directory
    # (we need to know the new dir paths so file rows can be relative to them).

    # First pass: build map of every old dir path → new dir path.
    dir_map: dict[Path, str] = {ROOT: ""}  # ROOT maps to empty prefix

    for path in sorted(ROOT.rglob("*")):
        if path.is_symlink():
            rows.append(("FLAG", str(path), "", "symlink — review manually"))
            counters["FLAG"] += 1
            continue
        rel = path.relative_to(ROOT)
        parts = rel.parts

        # Junk → quarantine, never delete
        if any(is_macos_junk(p) for p in parts):
            quarantine = "_junk/" + "/".join(slugify(p) for p in parts)
            rows.append(("QUARANTINE", str(path), str(ROOT / quarantine), "macOS junk"))
            counters["QUARANTINE"] += 1
            continue
        if path.is_file() and is_piracy_decoration(path.name):
            quarantine = "_junk/" + "/".join(slugify(p) for p in parts)
            rows.append(("QUARANTINE", str(path), str(ROOT / quarantine),
                         "piracy-site decoration file"))
            counters["QUARANTINE"] += 1
            continue

        new_path = compute_new_path(parts, dir_map, is_dir=path.is_dir())

        if new_path is None:
            rows.append(("FLAG", str(path), "", "needs human decision"))
            counters["FLAG"] += 1
            continue

        if new_path == "":
            # Empty-after-children container; no rename, just inform.
            rows.append(("CONTAINER", str(path), "",
                         "becomes empty after children move; can be removed manually after apply"))
            counters["CONTAINER"] += 1
            continue

        if path.is_dir():
            dir_map[path] = new_path  # cache for descendants

        old_full = str(path)
        new_full = str(ROOT / new_path)

        if old_full == new_full:
            rows.append(("KEEP", old_full, new_full, ""))
            counters["KEEP"] += 1
        else:
            rows.append(("RENAME", old_full, new_full, ""))
            counters["RENAME"] += 1

    # Collision pass: split into two cases.
    # - Directory-target collisions (multiple folders → same target dir) are
    #   intentional MERGES; emit a MERGE row instead of a duplicate.
    # - File-target collisions (a file would overwrite another file) get
    #   quarantined to _junk/duplicates/ so nothing is silently overwritten.
    seen_dirs: dict[str, int] = {}     # proposed dir target → first row idx
    seen_files: dict[str, int] = {}    # proposed file target → first row idx

    for idx, (action, old, new, _note) in enumerate(rows):
        if action != "RENAME":
            continue
        is_dir = Path(old).is_dir()
        registry = seen_dirs if is_dir else seen_files
        if new in registry:
            if is_dir:
                rows[idx] = ("MERGE", old, new,
                              f"merges into {new} (also targeted by row {registry[new] + 2})")
                counters["RENAME"] -= 1
                counters["MERGE"] += 1
            else:
                quarantine = str(ROOT / "_junk/duplicates" /
                                 "/".join(slugify(p) for p in Path(old).relative_to(ROOT).parts))
                rows[idx] = ("QUARANTINE", old, quarantine,
                              f"file would overwrite row {registry[new] + 2}: {new}")
                counters["RENAME"] -= 1
                counters["QUARANTINE"] += 1
        else:
            registry[new] = idx

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(["action", "current_path", "proposed_path", "note"])
        for row in rows:
            w.writerow(row)

    print(f"Wrote {OUT}  ({len(rows)} rows)")
    for k in ("KEEP", "RENAME", "MERGE", "QUARANTINE", "CONTAINER", "FLAG"):
        print(f"  {k:<10}: {counters[k]:5d}")
    overwrite_count = sum(1 for r in rows if r[0] == "QUARANTINE" and "overwrite" in r[3])
    print(f"  (of QUARANTINE: {overwrite_count} are file-overwrite collisions)")


# ---------------------------------------------------------------------------
# Path computation per entry
# ---------------------------------------------------------------------------

def compute_new_path(parts: tuple[str, ...], dir_map: dict[Path, str], *,
                      is_dir: bool) -> str | None:
    """Return the new path (relative to ROOT) for the entry whose old
    relative parts are `parts`. None means FLAG (can't classify)."""

    top = parts[0]

    # Special-case top-level files
    if len(parts) == 1 and top in ROOT_FILES:
        return ROOT_FILES[top]

    # 06_Novels: per-file mapping
    if top == "06_Novels":
        if len(parts) == 1:
            return ""  # container — empty after children move
        if parts[1] in NOVELS_06:
            target_root = NOVELS_06[parts[1]]
            if len(parts) == 2:
                return target_root
            inner = "/".join(slugify(p) for p in parts[2:])
            return f"{target_root}/{inner}"
        return None  # unknown novel, FLAG

    # Top-level language folders
    if top in TOP_LEVEL:
        target = TOP_LEVEL[top]
        if target is None:
            return None
        if target == "__FME_CHILDREN__":
            return _compute_fme(parts, is_dir=is_dir)
        if target == "__SPLIT_06_NOVELS__":
            return None
        return _compute_lang(parts, target, archive_prefix=None, is_dir=is_dir)

    return None


def _compute_fme(parts: tuple[str, ...], *, is_dir: bool) -> str | None:
    if len(parts) < 2:
        return ""  # FME Method itself becomes empty container
    fme_lang = parts[1]
    # Direct files under FME Method/ → _shared/
    if len(parts) == 2 and not is_dir:
        return f"_shared/{slugify(fme_lang)}"
    iso = FME_CHILDREN.get(fme_lang)
    if iso is None:
        return None
    archive_prefix = FME_GERMAN_ARCHIVE_PREFIX if fme_lang == "German" else None
    return _compute_lang(("__SHIFT__",) + parts[2:], iso,
                          archive_prefix=archive_prefix, is_dir=is_dir)


def _compute_lang(parts: tuple[str, ...], iso: str, *, archive_prefix: str | None,
                   is_dir: bool) -> str | None:
    """Map (resource_folder, ...) within a language subtree to the new path.
    First element of `parts` is a sentinel; real content starts at parts[1:].
    `is_dir` distinguishes a directory (which becomes a target dir) from a
    file (which becomes a file *inside* its target dir).
    """
    rest = parts[1:]
    if not rest:
        return iso  # the language folder itself

    res = rest[0]

    # FME German .rar archives → _archives
    if archive_prefix and res.lower().endswith(".rar"):
        return f"{archive_prefix}/{slugify(res)}"

    norm = normalize_resource_folder(res)

    if norm is None:
        # Unrecognized first-level entry. File goes to <iso>/misc/<slug>;
        # folder goes to <iso>/misc/<slug>/...
        if len(rest) == 1 and not is_dir:
            return f"{iso}/misc/{slugify(res)}"
        slug_chain = "/".join(slugify(p) for p in rest)
        return f"{iso}/misc/{slug_chain}"

    # `res` matches a known resource (pimsleur/assimil/glossika/...)
    if len(rest) == 1:
        if is_dir:
            return f"{iso}/{norm}"
        # FILE at language root that matched a resource pattern by name
        # (e.g. Pimsleur.Turkish part1.rar) → put it inside the resource dir.
        return f"{iso}/{norm.split('/')[0]}/{slugify(res)}"

    # Pimsleur level subfolders only apply to *directories*
    if norm.startswith("pimsleur/"):
        sub = rest[1]
        # Only consider Audio/PDF subfolders if the *child* is a dir
        # (otherwise files like PimsleurGermanIV.pdf get falsely classified)
        if len(rest) >= 3 or (len(rest) == 2 and is_dir):
            sub_norm = normalize_pimsleur_subfolder(sub)
            if sub_norm is not None:
                inner = sub_norm
                if len(rest) > 2:
                    inner += "/" + "/".join(slugify(p) for p in rest[2:])
                return f"{iso}/{norm}/{inner}"

    # Generic descent for files/dirs under Assimil / Glossika / Pimsleur-level
    inner = "/".join(slugify(p) for p in rest[1:])
    return f"{iso}/{norm}" + (("/" + inner) if inner else "")


if __name__ == "__main__":
    main()
