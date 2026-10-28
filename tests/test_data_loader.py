"""Tests for dataset parsing and normalisation."""

from __future__ import annotations

import json

import pytest

from app.services.data_loader import (
    DatasetError,
    normalise_dataframe,
    parse_genres,
    read_raw_dataframe,
)


def load(content: str | bytes, filename: str = "movies.csv"):
    data = content.encode("utf-8") if isinstance(content, str) else content
    return normalise_dataframe(read_raw_dataframe(data, filename))


def test_aliases_are_mapped_case_insensitively(small_csv_bytes):
    frame, report = normalise_dataframe(read_raw_dataframe(small_csv_bytes, "small.csv"))
    assert report.mapped_columns == {
        "title": "Movie Name",
        "year": "Movie Year",
        "genre": "Genre",
        "description": "Desc",
    }
    assert list(frame.columns) == ["id", "title", "year", "genres", "description"]
    assert report.rows_loaded == 6
    assert report.missing_genre == 1


def test_genre_parsing_handles_separators_and_synonyms():
    assert parse_genres("Sci-Fi | thriller, Drama / drama") == ["Science Fiction", "Thriller", "Drama"]
    assert parse_genres(["romcom", "Film-noir"]) == ["Romance", "Film-Noir"]
    assert parse_genres("") == []
    assert parse_genres(float("nan")) == []


def test_year_extraction_and_missing_values():
    frame, report = load("title,year\nA,1994-09-23\nB,1999.0\nC,unknown\nD,\n")
    assert frame["year"].iloc[0] == 1994 and frame["year"].iloc[1] == 1999
    assert report.missing_year == 2


def test_duplicates_and_blank_titles_are_removed():
    frame, report = load("name,year\nHeat,1995\nheat,1995\n,2000\nHeat,2001\n")
    assert len(frame) == 2
    assert report.duplicates_removed == 1
    assert report.dropped_missing_title == 1


def test_semicolon_and_tab_delimiters_are_detected():
    assert len(load("title;year;genre\nA;2000;Drama\nB;2001;Comedy\n")[0]) == 2
    assert len(load("title\tyear\tgenre\nA\t2000\tDrama\nB\t2001\tComedy\n")[0]) == 2


def test_pipe_separated_genres_are_not_mistaken_for_a_delimiter():
    frame, _ = load('title,year,genre\nA,2000,"Drama|Comedy"\nB,2001,"Action|Crime"\n')
    assert frame["genres"].iloc[0] == ["Drama", "Comedy"]


def test_json_records_and_wrapped_objects():
    records = [{"movie name": "A", "movie year": 2000, "genre": ["Drama", "Comedy"], "desc": "Plot"}]
    for payload in (records, {"movies": records}):
        frame, _ = load(json.dumps(payload), "movies.json")
        assert frame["genres"].iloc[0] == ["Drama", "Comedy"]


def test_latin1_encoded_files_are_supported():
    frame, _ = load("title,year\nAmélie,2001\n".encode("latin-1"))
    assert frame["title"].iloc[0] == "Amélie"


@pytest.mark.parametrize(
    "content, filename",
    [
        ("", "movies.csv"),
        ("year,genre\n2000,Drama\n", "movies.csv"),  # no title column
        ("title\n\n\n", "movies.csv"),  # only blank rows
        ("not json", "movies.json"),
        ("[1, 2, 3]", "movies.json"),
    ],
)
def test_unusable_files_raise_dataset_error(content, filename):
    with pytest.raises(DatasetError):
        load(content, filename)


def test_row_limit_is_enforced():
    raw = read_raw_dataframe(b"title\nA\nB\nC\n", "movies.csv")
    with pytest.raises(DatasetError):
        normalise_dataframe(raw, max_rows=2)
