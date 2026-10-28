"""CineMind – an IBM-style Movie Recommendation System.

The package exposes :func:`create_app`, the Flask application factory.  Using a
factory keeps configuration explicit and makes the app trivial to test.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request

from .config import Config
from .services import DatasetStore

__version__ = "1.0.0"


def create_app(config_object: type[Config] | None = None) -> Flask:
    """Build and configure the Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_object or Config)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # The store loads the persisted upload (or the sample set) once at start-up.
    app.extensions["dataset_store"] = DatasetStore(
        sample_path=app.config["SAMPLE_DATASET"],
        data_dir=app.config["DATA_DIR"],
        max_rows=app.config["MAX_DATASET_ROWS"],
    )

    from .routes import api, pages

    app.register_blueprint(pages)
    app.register_blueprint(api, url_prefix="/api")
    _register_error_handlers(app)
    _register_security_headers(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    """Return JSON errors for API calls so the front end can display them."""

    def json_error(status: int, message: str):
        return jsonify({"error": message}), status

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return json_error(404, "The requested resource was not found.")
        return "Not found", 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return json_error(405, "This method is not allowed for the requested URL.")

    @app.errorhandler(413)
    def too_large(_error):
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return json_error(413, f"The file is too large. The maximum upload size is {limit_mb} MB.")

    @app.errorhandler(500)
    def server_error(_error):
        return json_error(500, "Something went wrong on our side. Please try again.")


def _register_security_headers(app: Flask) -> None:
    """Apply conservative browser hardening headers to every response."""

    @app.after_request
    def add_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "frame-ancestors 'none'",
        )
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response
