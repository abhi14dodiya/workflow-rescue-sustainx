"""Prepare built frontend assets only; do not deploy without a working backend.

The current UI expects same-origin /api routes. Firebase Hosting on Spark cannot
proxy an external tunnel, and Cloud Run rewrites require a compatible Cloud Run
deployment. This script intentionally stops unless a backend configuration has
been reviewed; it does not disguise a temporary backend as durable hosting.
"""
from pathlib import Path
import argparse
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-configured", action="store_true",
                        help="A working durable backend and UI routing were separately verified.")
    args = parser.parse_args()
    if not args.backend_configured:
        raise SystemExit("Hosting preparation paused: verify a durable backend and configure API routing first. Static hosting alone cannot run this FastAPI application.")
    source = ROOT / "web"
    target = ROOT / "artifacts" / "firebase-public"
    if not (source / "index.html").is_file():
        raise SystemExit("Build the React frontend first.")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "index.html", target / "index.html")
    shutil.copytree(source, target / "assets", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("index.html"))
    print(json.dumps({"prepared": str(target), "deployed": False}))


if __name__ == "__main__":
    main()
