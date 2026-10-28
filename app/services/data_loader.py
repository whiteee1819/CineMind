"""Dataset ingestion: reading, validating and normalising movie catalogues.

The loader is deliberately forgiving about *how* the user's file looks
(delimiter, encoding, header spelling, genre separators ...) but strict about
*what* ends up in the engine: a clean :class:`pandas.DataFrame` with the fixed
schema documented in :data:`CANONICAL_COLUMNS`.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

#: Columns of the normalised data frame handed to the recommender.
CANONICAL_COLUMNS = ("id", "title", "year", "genres", "description")

#: Accepted header spellings (after :func:`_normalise_header`) per field.
COLUMN_ALIASES: dict[str, frozenset[str]] = {
    "title": frozenset(
        {"movie name", "moviename", "name", "title", "movie", "movie title", "film", "film name", "film title"}
    ),
    "year": frozenset(
        {"movie year", "year", "release year", "released", "release date", "release", "year released"}
    ),
    "genre": frozenset({"genre", "genres", "category", "categories", "movie genre"}),
    "description": frozenset(
        {"desc", "description", "overview", "plot", "summary", "synopsis", "plot summary", "storyline", "movie description"}
    ),
}

#: Alternative genre spellings folded into one canonical label.
GENRE_SYNONYMS: dict[str, str] = {
    "sci-fi": "Science Fiction",
    "sci fi": "Science Fiction",
    "scifi": "Science Fiction",
    "science-fiction": "Science Fiction",
    "sf": "Science Fiction",
    "romcom": "Romance",
    "rom-com": "Romance",
    "docu": "Documentary",
    "doc": "Documentary",
    "bio": "Biography",
    "biopic": "Biography",
    "musical": "Musical",
    "kids": "Family",
    "children": "Family",
    "animated": "Animation",
    "cartoon": "Animation",
    "suspense": "Thriller",
    "action & adventure": "Action",
}

_GENRE_SPLIT_RE = re.compile(r"[|,/;]+")
_YEAR_RE = re.compile(r"(1[89]\d{2}|20\d{2}|21\d{2})")
_WHITESPACE_RE = re.compile(r"\s+")
_MAX_GENRE_LENGTH = 40
_MAX_TITLE_LENGTH = 200


class DatasetError(ValueError):
    """Raised when an uploaded dataset cannot be used.

    The message is written for end users – the API returns it verbatim.
    """


@dataclass
class LoadReport:
    """Human-readable summary of what happened while loading a dataset."""

    rows_read: int = 0
    rows_loaded: int = 0
    dropped_missing_title: int = 0
    duplicates_removed: int = 0
    missing_year: int = 0
    missing_genre: int = 0
    missing_description: int = 0
    genres_inferred: int = 0
    mapped_columns: dict[str, str] = field(default_factory=dict)
    ignored_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_read": self.rows_read,
            "rows_loaded": self.rows_loaded,
            "dropped_missing_title": self.dropped_missing_title,
            "duplicates_removed": self.duplicates_removed,
            "missing_year": self.missing_year,
            "missing_genre": self.missing_genre,
            "missing_description": self.missing_description,
            "genres_inferred": self.genres_inferred,
            "mapped_columns": self.mapped_columns,
            "ignored_columns": self.ignored_columns,
            "warnings": self.warnings,
        }


# ──────────────────────────────────────────────────────────────────────────
# Reading raw files
# ──────────────────────────────────────────────────────────────────────────
def read_raw_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    """Parse ``content`` (the bytes of an uploaded file) into a raw data frame.

    Supported formats: CSV / TSV / TXT (delimiter auto-detected), JSON (list of
    records or an object wrapping one) and XLSX.
    """
    if not content or not content.strip():
        raise DatasetError("The uploaded file is empty.")

    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".xlsx":
            return pd.read_excel(io.BytesIO(content), dtype=object, engine="openpyxl")
        text = _decode(content)
        if suffix == ".json":
            return _read_json(text)
        return _read_delimited(text)
    except DatasetError:
        raise
    except Exception as exc:  # pandas/openpyxl raise many unrelated types
        raise DatasetError(f"Could not parse '{filename}': {exc}") from exc


def _decode(content: bytes) -> str:
    """Decode bytes trying UTF-8 (with BOM) first and Latin-1 as a fallback."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DatasetError("Unsupported text encoding. Please save the file as UTF-8.")


def _read_delimited(text: str) -> pd.DataFrame:
    """Read CSV-like text, sniffing the delimiter among ``, ; <tab>``.

    The pipe character is intentionally *not* a candidate because it is the
    recommended separator for multiple genres inside a single cell.
    """
    sample = text[:8192]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    return pd.read_csv(
        io.StringIO(text),
        sep=delimiter,
        dtype=object,
        keep_default_na=False,
        skipinitialspace=True,
        on_bad_lines="skip",
    )


def _read_json(text: str) -> pd.DataFrame:
    payload = json.loads(text)
    if isinstance(payload, dict):
        # Accept {"movies": [...]} style wrappers.
        lists = [value for value in payload.values() if isinstance(value, list)]
        if not lists:
            raise DatasetError("JSON must be a list of movie objects.")
        payload = lists[0]
    if not isinstance(payload, list) or not payload or not all(isinstance(item, dict) for item in payload):
        raise DatasetError("JSON must be a non-empty list of movie objects.")
    return pd.DataFrame(payload)


# ──────────────────────────────────────────────────────────────────────────
# Normalisation
# ──────────────────────────────────────────────────────────────────────────
def _normalise_header(name: Any) -> str:
    """Lower-case a header and collapse separators so aliases match reliably."""
    cleaned = str(name).strip().lstrip("\ufeff").lower().replace("_", " ").replace("-", " ")
    return _WHITESPACE_RE.sub(" ", cleaned)


def _map_columns(raw: pd.DataFrame, report: LoadReport) -> dict[str, str]:
    """Return ``{field: original column name}`` for every recognised column."""
    mapping: dict[str, str] = {}
    for column in raw.columns:
        header = _normalise_header(column)
        for field_name, aliases in COLUMN_ALIASES.items():
            if header in aliases and field_name not in mapping:
                mapping[field_name] = column
                break
    report.mapped_columns = {key: str(value) for key, value in mapping.items()}
    report.ignored_columns = [str(c) for c in raw.columns if c not in mapping.values()]
    return mapping


def _clean_text(value: Any, max_length: int | None = None) -> str:
    """Convert any cell to a single-line, trimmed string ('' for missing)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = _WHITESPACE_RE.sub(" ", str(value)).strip()
    if text.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
        return ""
    return text[:max_length] if max_length else text


def parse_genres(value: Any) -> list[str]:
    """Split a raw genre cell into a de-duplicated list of canonical labels.

    Accepts ``"Drama|Crime"``, ``"drama, crime"``, ``"Sci-Fi / Thriller"`` and
    real Python lists (from JSON).
    """
    if isinstance(value, (list, tuple, set)):
        parts = [str(item) for item in value]
    else:
        parts = _GENRE_SPLIT_RE.split(_clean_text(value))

    genres: list[str] = []
    for part in parts:
        label = _clean_text(part, _MAX_GENRE_LENGTH)
        if not label:
            continue
        canonical = GENRE_SYNONYMS.get(label.lower(), _title_case_genre(label))
        if canonical not in genres:
            genres.append(canonical)
    return genres


def _title_case_genre(label: str) -> str:
    """Title-case a genre while keeping hyphenated words intact (``Film-Noir``)."""
    return "-".join(word.capitalize() for word in label.split("-")) if "-" in label else label.title()


def _parse_year(value: Any) -> float:
    """Extract a four digit year from ``1994``, ``1994.0``, ``1994-09-23`` ..."""
    match = _YEAR_RE.search(_clean_text(value))
    return float(match.group(1)) if match else float("nan")


def normalise_dataframe(raw: pd.DataFrame, max_rows: int | None = None) -> tuple[pd.DataFrame, LoadReport]:
    """Clean ``raw`` into the canonical schema and describe what was changed.

    Raises
    ------
    DatasetError
        If no movie-name column is present, the file has too many rows, or no
        usable rows remain after cleaning.
    """
    report = LoadReport(rows_read=len(raw))
    if raw.empty:
        raise DatasetError("The dataset contains no rows.")
    if max_rows and len(raw) > max_rows:
        raise DatasetError(f"The dataset has {len(raw):,} rows; the limit is {max_rows:,}.")

    mapping = _map_columns(raw, report)
    if "title" not in mapping:
        raise DatasetError(
            "No movie-name column found. Name one of your columns 'movie name' "
            "(or 'title', 'name', 'film')."
        )

    def column(field_name: str) -> list[Any]:
        source = mapping.get(field_name)
        return raw[source].tolist() if source is not None else [None] * len(raw)

    frame = pd.DataFrame(
        {
            "title": [_clean_text(v, _MAX_TITLE_LENGTH) for v in column("title")],
            "year": [_parse_year(v) for v in column("year")],
            "genres": [parse_genres(v) for v in column("genre")],
            "description": [_clean_text(v) for v in column("description")],
        }
    )

    for missing_field, label in (("year", "movie year"), ("genre", "genre"), ("description", "desc")):
        if missing_field not in mapping:
            report.warnings.append(
                f"No '{label}' column found – recommendations will rely on the remaining columns."
            )

    # Drop unusable rows -------------------------------------------------
    has_title = frame["title"].str.len() > 0
    report.dropped_missing_title = int((~has_title).sum())
    frame = frame[has_title]

    # De-duplicate on (title, year) -------------------------------------
    key = frame["title"].str.lower() + "|" + frame["year"].fillna(-1).astype(int).astype(str)
    duplicate_mask = key.duplicated(keep="first")
    report.duplicates_removed = int(duplicate_mask.sum())
    frame = frame[~duplicate_mask].reset_index(drop=True)

    if frame.empty:
        raise DatasetError("No valid rows were found – every row was missing a movie name.")

    frame.insert(0, "id", range(len(frame)))
    report.rows_loaded = len(frame)
    report.missing_year = int(frame["year"].isna().sum())
    report.missing_genre = int((frame["genres"].str.len() == 0).sum())
    report.missing_description = int((frame["description"] == "").sum())

    if report.dropped_missing_title:
        report.warnings.append(f"{report.dropped_missing_title} row(s) without a movie name were skipped.")
    if report.duplicates_removed:
        report.warnings.append(f"{report.duplicates_removed} duplicate row(s) were merged.")
    return frame[list(CANONICAL_COLUMNS)], report
