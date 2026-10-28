"""Application configuration.

All tunables live here so behaviour can be changed without touching business
logic.  Most values can be overridden through environment variables, which
keeps the same code base usable on a laptop, in Docker or on a server.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Absolute path to the repository root (the folder that contains ``run.py``).
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Default configuration used by :func:`app.create_app`."""

    # ── Flask ──────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("CINEMIND_SECRET_KEY", "change-me-in-production")
    #: Hard limit for request bodies (and therefore uploads), in bytes.
    MAX_CONTENT_LENGTH = int(os.environ.get("CINEMIND_MAX_UPLOAD_MB", "10")) * 1024 * 1024
    JSON_SORT_KEYS = False

    # ── Data locations ─────────────────────────────────────────────────
    #: Bundled demo dataset, always available as a fallback.
    SAMPLE_DATASET = BASE_DIR / "data" / "sample_movies.csv"
    #: Where the active (uploaded) dataset is persisted between restarts.
    DATA_DIR = Path(os.environ.get("CINEMIND_DATA_DIR", BASE_DIR / "instance" / "data"))

    # ── Upload rules ───────────────────────────────────────────────────
    ALLOWED_EXTENSIONS = frozenset({".csv", ".tsv", ".txt", ".json", ".xlsx"})
    #: Safety valve – very large catalogues are rejected with a clear message.
    MAX_DATASET_ROWS = int(os.environ.get("CINEMIND_MAX_ROWS", "50000"))

    # ── API behaviour ──────────────────────────────────────────────────
    DEFAULT_RESULT_LIMIT = 12
    MAX_RESULT_LIMIT = 48
    MAX_LIKED_MOVIES = 25
    MAX_PAGE_SIZE = 60


class TestConfig(Config):
    """Configuration used by the automated test-suite."""

    __test__ = False  # not a pytest test class despite the name
    TESTING = True
    SECRET_KEY = "test"
    DATA_DIR = BASE_DIR / "instance" / "test-data"
