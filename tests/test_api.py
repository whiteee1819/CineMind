"""End-to-end tests of the JSON API through Flask's test client."""

from __future__ import annotations

import io


def test_index_page_and_static_assets(client):
    page = client.get("/")
    assert page.status_code == 200 and b"CineMind" in page.data
    for asset in ("/static/css/style.css", "/static/js/app.js"):
        assert client.get(asset).status_code == 200


def test_security_headers_present(client):
    headers = client.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "script-src 'self'" in headers["Content-Security-Policy"]


def test_health_and_dataset_summary(client):
    assert client.get("/api/health").json["status"] == "ok"
    summary = client.get("/api/dataset").json
    assert summary["meta"]["source"] == "sample"
    assert summary["stats"]["total"] >= 50
    assert summary["stats"]["genres_inferred"] >= 1  # sample ships with unlabeled rows


def test_search_and_detail(client):
    hit = client.get("/api/movies/search?q=incep").json["results"][0]
    assert hit["title"] == "Inception"
    assert client.get(f"/api/movies/{hit['id']}").json["title"] == "Inception"
    assert client.get("/api/movies/99999").status_code == 404
    assert client.get("/api/nope").json["error"]


def test_library_endpoint_validates_paging(client):
    data = client.get("/api/movies?page=abc&per_page=9999&genre=Comedy").json
    assert data["page"] == 1 and data["per_page"] <= 60
    assert all("Comedy" in m["genres"] for m in data["items"])


def test_recommend_from_liked_movie(client):
    liked = client.get("/api/movies/search?q=the matrix").json["results"][0]["id"]
    data = client.post("/api/recommend", json={"liked": [liked], "limit": 6}).json
    assert 1 <= len(data["results"]) <= 6
    assert all(item["id"] != liked for item in data["results"])


def test_recommend_validation(client):
    assert client.post("/api/recommend", json={}).status_code == 400
    assert client.post("/api/recommend", data="nope").status_code == 400
    assert client.post("/api/recommend", json={"liked": "x"}).status_code == 400
    bad_range = client.post("/api/recommend", json={"genres": ["Drama"], "year_min": 2020, "year_max": 1990})
    assert bad_range.status_code == 400
    odd = client.post("/api/recommend", json={"mood": "space", "limit": "many", "year_min": "x"})
    assert odd.status_code == 200


def test_upload_replaces_dataset_and_persists(app, client, small_csv_bytes):
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(small_csv_bytes), "my movies.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert response.json["stats"]["total"] == 6
    assert response.json["meta"]["source"] == "upload"

    # A "restart" (new app on the same data dir) restores the upload.
    from app import create_app

    restarted = create_app(_same_config(app))
    assert restarted.test_client().get("/api/dataset").json["stats"]["total"] == 6

    reset = client.post("/api/dataset/reset").json
    assert reset["meta"]["source"] == "sample"


def _same_config(app):
    from app.config import TestConfig

    class Same(TestConfig):
        DATA_DIR = app.config["DATA_DIR"]

    return Same


def test_bad_uploads_are_rejected_and_do_not_replace_data(client):
    before = client.get("/api/dataset").json["stats"]["total"]

    def post(data, name):
        return client.post(
            "/api/upload", data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data"
        )

    assert post(b"title\nA", "movies.exe").status_code == 400
    assert post(b"", "movies.csv").status_code == 400
    assert post(b"year,genre\n2000,Drama\n", "movies.csv").status_code == 400
    assert client.post("/api/upload", data={}, content_type="multipart/form-data").status_code == 400
    assert client.get("/api/dataset").json["stats"]["total"] == before


def test_oversized_upload_returns_json_413(app, client):
    app.config["MAX_CONTENT_LENGTH"] = 1024
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"title\n" + b"x" * 5000), "big.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413 and "too large" in response.json["error"]


def test_template_download(client):
    response = client.get("/api/template.csv")
    assert response.mimetype == "text/csv" and b"movie name" in response.data
