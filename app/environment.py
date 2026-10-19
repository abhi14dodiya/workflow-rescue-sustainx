"""Load project settings without retaining unrelated model credentials."""
from __future__ import annotations

import os
from pathlib import Path
import re

from dotenv import dotenv_values

APP_SETTINGS = frozenset({
    "GEMINI_API_KEY", "GEMINI_MODEL", "DEFAULT_PROVIDER", "FIRESTORE_PROJECT_ID",
    "DEMO_ACCESS_TOKEN", "MAX_MODEL_CALLS_PER_HOUR", "MAX_ACTIVE_RUNS", "PORT",
})
_SENSITIVE = re.compile(r"API_?KEY|ACCESS_?TOKEN|AUTH_?TOKEN|PASSWORD|SECRET|PRIVATE_KEY", re.I)
_MODEL_SUFFIXES = ("_BASE_URL", "_ENDPOINT", "_DEPLOYMENT", "_MODEL", "_API_VERSION")


def configure_environment(path: Path) -> None:
    # This application process only; parent shells and Google ADC stay intact.
    for name in tuple(os.environ):
        if name not in APP_SETTINGS and (_SENSITIVE.search(name) or name.endswith(_MODEL_SUFFIXES)):
            os.environ.pop(name, None)
    for name, value in dotenv_values(path).items():
        if name in APP_SETTINGS and value is not None:
            os.environ.setdefault(name, value)
