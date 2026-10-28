"""Tests for the recommendation engine and genre categoriser."""

from __future__ import annotations

import pytest

from app.services.data_loader import normalise_dataframe, read_raw_dataframe
from app.services.recommender import MovieRecommender


@pytest.fixture()
def engine(small_csv_bytes) -> MovieRecommender:
    frame, _ = normalise_dataframe(read_raw_dataframe(small_csv_bytes, "small.csv"))
    return MovieRecommender(frame)


def id_of(engine: MovieRecommender, title: str) -> int:
    return engine.search(title)[0]["id"]


def titles(result) -> list[str]:
    return [item["title"] for item in result["results"]]


def test_similar_movie_ranks_first_and_input_is_excluded(engine):
    result = engine.recommend(liked_ids=[id_of(engine, "Star Voyage")])
    assert "Star Voyage" not in titles(result)
    assert titles(result)[0] == "Galaxy Wars"
    assert result["results"][0]["because"] == "Star Voyage"
    assert "Science Fiction" in result["results"][0]["shared_genres"]


def test_scores_are_sorted_and_bounded(engine):
    result = engine.recommend(liked_ids=[id_of(engine, "Love in Paris")])
    scores = [item["score"] for item in result["results"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 1 for s in scores)
    assert all(0 <= item["match"] <= 99 for item in result["results"])


def test_genre_filter_is_strict_and_accepts_synonyms(engine):
    result = engine.recommend(genres=["sci-fi"])
    assert result["results"], "expected sci-fi movies"
    assert all("Science Fiction" in item["genres"] for item in result["results"])


def test_unknown_genre_yields_no_results(engine):
    assert engine.recommend(genres=["Western"])["results"] == []


def test_year_window_filters_results(engine):
    result = engine.recommend(genres=["Romance"], year_min=2011, year_max=2020)
    assert titles(result) == ["Paris Nights"]


def test_mood_text_drives_results(engine):
    result = engine.recommend(mood="detective hunting a killer")
    assert titles(result)[0] == "Dark Alley"
    assert result["results"][0]["keywords"]


def test_mood_with_no_vocabulary_overlap_returns_empty(engine):
    assert engine.recommend(mood="xyzzy plugh")["results"] == []


def test_empty_request_is_rejected(engine):
    with pytest.raises(ValueError):
        engine.recommend()


def test_invalid_liked_ids_are_ignored(engine):
    result = engine.recommend(liked_ids=[9999, -3], genres=["Romance"])
    assert result["results"]


def test_missing_genre_is_inferred_from_description(engine):
    movie = engine.movie(id_of(engine, "Mystery Pilot"))
    assert movie["genre_inferred"] is True
    assert "Science Fiction" in movie["genres"]


def test_search_prefers_prefix_matches(engine):
    assert [m["title"] for m in engine.search("paris")][:1] == ["Paris Nights"]
    assert engine.search("   ") == []


def test_library_listing_paginates_and_filters(engine):
    page = engine.list_movies(genre="romance", per_page=1, page=2)
    assert page["total"] == 2 and page["pages"] == 2 and len(page["items"]) == 1
    assert engine.list_movies(query="galaxy")["total"] == 2
    newest = engine.list_movies(sort="year_desc")["items"][0]
    assert newest["year"] == 2017


def test_stats_describe_the_catalogue(engine):
    stats = engine.stats()
    assert stats["total"] == 6
    assert stats["year_min"] == 1998 and stats["year_max"] == 2017
    assert {g["name"] for g in stats["genres"]} >= {"Romance", "Science Fiction"}


def test_catalogue_without_descriptions_still_works():
    raw = read_raw_dataframe(b"title,genre\nA,Drama\nB,Drama\nC,Comedy\n", "x.csv")
    frame, _ = normalise_dataframe(raw)
    engine = MovieRecommender(frame)
    assert titles(engine.recommend(liked_ids=[0])) [0] == "B"


def test_single_movie_catalogue():
    raw = read_raw_dataframe(b"title\nOnly One\n", "x.csv")
    frame, _ = normalise_dataframe(raw)
    engine = MovieRecommender(frame)
    assert engine.recommend(liked_ids=[0])["results"] == []
