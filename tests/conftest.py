"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture()
def app(tmp_path):
    """A fresh app whose persisted data lives in a throw-away directory."""

    class IsolatedConfig(TestConfig):
        DATA_DIR = tmp_path / "data"

    return create_app(IsolatedConfig)


@pytest.fixture()
def client(app):
    return app.test_client()


SMALL_CSV = (
    '"Movie Name","Movie Year","Genre","Desc"\n'
    '"Star Voyage",2015,"Sci-Fi|Adventure","Astronauts explore a distant galaxy aboard a starship."\n'
    '"Galaxy Wars",2017,"Science Fiction|Adventure","A rebel pilot fights an empire across the galaxy and its starships."\n'
    '"Love in Paris",2010,"Romance|Drama","Two strangers fall in love on a rainy evening in Paris."\n'
    '"Paris Nights",2012,"Romance","A young painter falls in love with a mysterious stranger in Paris."\n'
    '"Dark Alley",1998,"Crime|Thriller","A detective hunts a killer through the dark streets of the city."\n'
    '"Mystery Pilot",2016,"","A space pilot on an uncharted journey across deep space, science fiction."\n'
)


@pytest.fixture()
def small_csv_bytes() -> bytes:
    return SMALL_CSV.encode("utf-8")
