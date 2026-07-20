from __future__ import annotations

import json
from pathlib import Path


_PACKAGE_JSON = Path(__file__).resolve().parents[1] / "frontend" / "package.json"


def load_app_version() -> str:
    """Return the version baked into this checkout or container image."""
    try:
        payload = json.loads(_PACKAGE_JSON.read_text(encoding="utf-8"))
        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except (OSError, json.JSONDecodeError):
        pass
    return "unknown"


APP_VERSION = load_app_version()
