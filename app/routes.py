"""HTTP layer: one page route plus a small, documented JSON API.

Endpoint overview (all under ``/api``):

====================  ======  ==============================================
Path                  Method  Purpose
====================  ======  ==============================================
/health               GET     Liveness probe
/dataset              GET     Active dataset metadata + analytics
/upload               POST    Upload a new dataset (multipart field ``file``)
/dataset/reset        POST    Go back to the bundled sample dataset
/template.csv         GET     Download a ready-to-fill CSV template
/movies               GET     Paginated library (``q``, ``genre``, ``sort``...)
/movies/search        GET     Title auto-complete (``q``)
/movies/<id>          GET     One movie
/recommend            POST    Personalised recommendations
====================  ======  ==============================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from . import __version__
from .services import DatasetError, DatasetStore

pages = Blueprint("pages", __name__)
api = Blueprint("api", __name__)

_TEMPLATE_CSV = (
    '"movie name","movie year","genre","desc"\r\n'
    '"Example Movie One",2001,"Drama|Romance","A short plot summary of the movie."\r\n'
    '"Example Movie Two",1999,"Action|Science Fiction","Another plot summary. Separate multiple genres with |"\r\n'
)


# ── Helpers ───────────────────────────────────────────────────────────────
def _store() -> DatasetStore:
    return current_app.extensions["dataset_store"]


def _bad_request(message: str):
    return jsonify({"error": message}), 400


def _to_int(value: Any, default: int | None = None) -> int | None:
    """Best-effort integer conversion (``None``/blank/invalid → ``default``)."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _dataset_summary() -> dict[str, Any]:
    store = _store()
    return {"meta": store.meta, "stats": store.recommender.stats(), "version": __version__}


# ── Pages ─────────────────────────────────────────────────────────────────
@pages.route("/")
def index():
    return render_template("index.html", version=__version__)


# ── API ───────────────────────────────────────────────────────────────────
@api.get("/health")
def health():
    return jsonify({"status": "ok", "version": __version__, "movies": _store().recommender.size})


@api.get("/dataset")
def dataset():
    return jsonify(_dataset_summary())


@api.post("/upload")
def upload():
    file = request.files.get("file")
    if file is None or not file.filename:
        return _bad_request("No file received. Choose a CSV, TSV, JSON or XLSX file.")

    extension = Path(file.filename).suffix.lower()
    if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        allowed = ", ".join(sorted(current_app.config["ALLOWED_EXTENSIONS"]))
        return _bad_request(f"Unsupported file type '{extension or 'none'}'. Allowed types: {allowed}.")

    try:
        _store().replace(file.read(), Path(file.filename).name)
    except DatasetError as exc:
        return _bad_request(str(exc))
    return jsonify(_dataset_summary()), 201


@api.post("/dataset/reset")
def reset_dataset():
    _store().reset_to_sample()
    return jsonify(_dataset_summary())


@api.get("/template.csv")
def template():
    return Response(
        _TEMPLATE_CSV,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cinemind_template.csv"},
    )


@api.get("/movies")
def movies():
    config = current_app.config
    result = _store().recommender.list_movies(
        query=request.args.get("q", "")[:100],
        genre=request.args.get("genre", "")[:40],
        sort=request.args.get("sort", "title"),
        page=_to_int(request.args.get("page"), 1) or 1,
        per_page=_clamp(_to_int(request.args.get("per_page"), 24) or 24, 1, config["MAX_PAGE_SIZE"]),
    )
    return jsonify(result)


@api.get("/movies/search")
def search_movies():
    query = request.args.get("q", "")[:100]
    limit = _clamp(_to_int(request.args.get("limit"), 8) or 8, 1, 20)
    return jsonify({"results": _store().recommender.search(query, limit)})


@api.get("/movies/<int:movie_id>")
def movie_detail(movie_id: int):
    movie = _store().recommender.movie(movie_id)
    if movie is None:
        return jsonify({"error": "Movie not found."}), 404
    return jsonify(movie)


@api.post("/recommend")
def recommend():
    config = current_app.config
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _bad_request("Send a JSON object as the request body.")

    raw_liked = payload.get("liked") or []
    raw_genres = payload.get("genres") or []
    if not isinstance(raw_liked, list) or not isinstance(raw_genres, list):
        return _bad_request("'liked' and 'genres' must be lists.")

    liked = [i for i in (_to_int(v) for v in raw_liked) if i is not None][: config["MAX_LIKED_MOVIES"]]
    genres = [str(g)[:40] for g in raw_genres if isinstance(g, str) and g.strip()][:20]
    mood = str(payload.get("mood") or "")[:300]
    year_min, year_max = _to_int(payload.get("year_min")), _to_int(payload.get("year_max"))
    if year_min is not None and year_max is not None and year_min > year_max:
        return _bad_request("'From' year must not be later than 'To' year.")
    limit = _clamp(
        _to_int(payload.get("limit"), config["DEFAULT_RESULT_LIMIT"]) or config["DEFAULT_RESULT_LIMIT"],
        1,
        config["MAX_RESULT_LIMIT"],
    )

    try:
        result = _store().recommender.recommend(
            liked_ids=liked, genres=genres, mood=mood, year_min=year_min, year_max=year_max, limit=limit
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result)
