"""Thread-safe holder of the *active* dataset and its recommender.

Responsibilities
----------------
* Build a :class:`MovieRecommender` from raw bytes (CSV/JSON/XLSX).
* Validate a new upload completely **before** replacing the live model, so a
  bad file can never leave the application without data.
* Persist the active upload to disk so it survives restarts.
* Fall back to the bundled sample dataset whenever needed.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data_loader import DatasetError, LoadReport, normalise_dataframe, read_raw_dataframe
from .recommender import MovieRecommender

logger = logging.getLogger(__name__)

_META_FILE = "active_dataset.json"


class DatasetStore:
    """Owns the live recommender and the metadata describing its source."""

    def __init__(self, sample_path: Path, data_dir: Path, max_rows: int | None = None) -> None:
        self._sample_path = Path(sample_path)
        self._data_dir = Path(data_dir)
        self._max_rows = max_rows
        self._lock = threading.RLock()
        self._recommender: MovieRecommender | None = None
        self._meta: dict[str, Any] = {}
        self._load_initial()

    # ── Accessors ─────────────────────────────────────────────────────
    @property
    def recommender(self) -> MovieRecommender:
        with self._lock:
            assert self._recommender is not None  # guaranteed by _load_initial
            return self._recommender

    @property
    def meta(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._meta)

    # ── Mutations ─────────────────────────────────────────────────────
    def replace(self, content: bytes, filename: str) -> dict[str, Any]:
        """Validate, activate and persist an uploaded dataset.

        Raises :class:`DatasetError` (leaving the current dataset untouched) if
        the file is unusable.
        """
        recommender, report = self._build(content, filename)
        suffix = Path(filename).suffix.lower() or ".csv"
        stored_name = f"active_dataset{suffix}"
        meta = self._make_meta("upload", filename, report, stored_name)

        with self._lock:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._write_atomic(self._data_dir / stored_name, content)
            self._write_atomic(self._data_dir / _META_FILE, json.dumps(meta).encode("utf-8"))
            self._remove_stale_uploads(keep=stored_name)
            self._recommender, self._meta = recommender, meta
        logger.info("Activated uploaded dataset %s (%d movies)", filename, recommender.size)
        return meta

    def reset_to_sample(self) -> dict[str, Any]:
        """Discard any upload and go back to the bundled demo dataset."""
        with self._lock:
            (self._data_dir / _META_FILE).unlink(missing_ok=True)
            self._remove_stale_uploads(keep=None)
            self._load_sample()
            return dict(self._meta)

    # ── Internals ─────────────────────────────────────────────────────
    def _build(self, content: bytes, filename: str) -> tuple[MovieRecommender, LoadReport]:
        raw = read_raw_dataframe(content, filename)
        frame, report = normalise_dataframe(raw, self._max_rows)
        recommender = MovieRecommender(frame)
        report.genres_inferred = recommender.genres_inferred
        if recommender.genres_inferred:
            report.warnings.append(
                f"{recommender.genres_inferred} movie(s) had no genre – categories were inferred from their descriptions."
            )
        return recommender, report

    def _make_meta(self, source: str, filename: str, report: LoadReport, stored_name: str | None) -> dict[str, Any]:
        return {
            "source": source,
            "filename": filename,
            "stored_as": stored_name,
            "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "report": report.to_dict(),
        }

    def _load_initial(self) -> None:
        """Restore the persisted upload if it is still valid, else use the sample."""
        meta_path = self._data_dir / _META_FILE
        try:
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                stored = self._data_dir / meta["stored_as"]
                recommender, report = self._build(stored.read_bytes(), meta["filename"])
                self._recommender = recommender
                self._meta = self._make_meta("upload", meta["filename"], report, meta["stored_as"])
                self._meta["loaded_at"] = meta.get("loaded_at", self._meta["loaded_at"])
                return
        except Exception:  # corrupt/missing persisted data must never block start-up
            logger.exception("Persisted dataset could not be restored; using the sample dataset.")
        self._load_sample()

    def _load_sample(self) -> None:
        content = self._sample_path.read_bytes()
        recommender, report = self._build(content, self._sample_path.name)
        self._recommender = recommender
        self._meta = self._make_meta("sample", self._sample_path.name, report, None)

    def _remove_stale_uploads(self, keep: str | None) -> None:
        if not self._data_dir.exists():
            return
        for path in self._data_dir.glob("active_dataset.*"):
            if path.name != _META_FILE and path.name != keep:
                path.unlink(missing_ok=True)

    @staticmethod
    def _write_atomic(path: Path, payload: bytes) -> None:
        """Write via a temp file + rename so readers never see half-written data."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(payload)
        os.replace(tmp, path)


__all__ = ["DatasetStore", "DatasetError"]
