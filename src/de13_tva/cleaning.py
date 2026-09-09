"""Cleaning helpers for VAT repository imports."""

from __future__ import annotations

import re

EMPTY_MARKERS = {"", "-", "null", "n/a"}


def clean_text(value: object) -> str:
    """Return a stripped string while preserving non-empty source text."""
    if value is None:
        return ""
    return str(value).strip()


def normalize_country(value: object) -> str:
    """Normalize a declared country code."""
    return clean_text(value).upper()


def normalize_vat_number(value: object) -> str:
    """Keep only alphanumeric characters and uppercase the VAT number."""
    return re.sub(r"[^0-9A-Za-z]", "", clean_text(value)).upper()


def is_empty_like(value: object) -> bool:
    """Detect empty or placeholder values found during exploration."""
    return clean_text(value).lower() in EMPTY_MARKERS
