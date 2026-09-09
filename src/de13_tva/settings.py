"""Project paths and environment loading."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "numeros-tva-6a9dbf50da6b4741045153.csv"
DEFAULT_EU_CODES_FILE = PROJECT_ROOT / "data" / "code-eu.csv"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_PHASE_1_REPORTS_DIR = DEFAULT_REPORTS_DIR / "phase_1"


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from .env without an extra dependency."""
    env_path = path or PROJECT_ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def database_config() -> dict[str, str | int]:
    """Return PostgreSQL settings from environment, .env, then project defaults."""
    dotenv = load_dotenv()

    def get(name: str, default: str) -> str:
        return os.getenv(name) or dotenv.get(name) or default

    return {
        "host": get("POSTGRES_HOST", "localhost"),
        "port": int(get("POSTGRES_PORT", "5435")),
        "dbname": get("POSTGRES_DB", "tva"),
        "user": get("POSTGRES_USER", "meridian"),
        "password": get("POSTGRES_PASSWORD", "meridian"),
    }
