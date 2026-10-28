"""Development / production entry point.

Usage
-----
    python run.py                   # dev server on http://127.0.0.1:5000
    python run.py --port 8080       # custom port
    python run.py --prod            # waitress production server
"""

from __future__ import annotations

import argparse
import os

from app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CineMind movie recommender.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--prod", action="store_true", help="Use the waitress production server")
    args = parser.parse_args()

    application = create_app()
    print(f"\n  CineMind is running -> http://{args.host}:{args.port}\n")

    if args.prod:
        from waitress import serve

        serve(application, host=args.host, port=args.port)
    else:
        # Debug mode exposes an interactive debugger – enable it explicitly only.
        debug = os.environ.get("CINEMIND_DEBUG") == "1"
        application.run(host=args.host, port=args.port, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    main()
