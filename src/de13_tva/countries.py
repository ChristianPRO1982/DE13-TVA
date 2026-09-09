"""EU country code loading."""

from __future__ import annotations

import csv
from pathlib import Path

CODE_COLUMN = "Code (ISO 3166)"
OUT_OF_SCOPE_COUNTRIES = {"GB", "UK"}


def load_eu_country_codes(path: Path) -> set[str]:
    """Load ISO country codes from the local EU reference CSV."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = csv.DictReader(csv_file)
        if rows.fieldnames is None or CODE_COLUMN not in rows.fieldnames:
            msg = f"Missing expected column {CODE_COLUMN!r} in {path}"
            raise ValueError(msg)
        return {
            row[CODE_COLUMN].strip().upper()
            for row in rows
            if row.get(CODE_COLUMN) and row[CODE_COLUMN].strip()
        }
