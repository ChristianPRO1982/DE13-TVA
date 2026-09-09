"""Application service used by the FastAPI endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from de13_tva.countries import load_eu_country_codes
from de13_tva.database import (
    fetch_stored_vies_verification,
    insert_vies_attempt,
    record_human_review_item,
    upsert_vies_verification,
)
from de13_tva.freshness import freshness_days, is_fresh
from de13_tva.settings import DEFAULT_EU_CODES_FILE
from de13_tva.validation import validate_structural
from de13_tva.vies import INDETERMINATE_VIES, ViesClient

VERDICT_INDETERMINATE = "indetermine"


def verify_vat_for_api(
    numero: str,
    conn,
    *,
    vies_client: ViesClient,
    force_refresh: bool,
    max_age_days: int,
    timeout: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_now = now or datetime.now(UTC)
    eu_codes = load_eu_country_codes(DEFAULT_EU_CODES_FILE)
    normalized = _normalize_api_input(numero)
    country = (
        normalized[:2] if len(normalized) >= 2 and normalized[:2].isalpha() else ""
    )
    structural = validate_structural(country, normalized, eu_codes)

    if structural.structure_verdict != "valid":
        record_human_review_item(
            conn,
            source="api",
            input_raw=numero,
            numero_tva_nettoye=normalized,
            review_reason=structural.structure_reason,
        )
        return _response(
            numero,
            normalized,
            VERDICT_INDETERMINATE,
            "structural_reject",
            checked_now,
            0,
            True,
            structural.structure_reason,
        )

    stored = fetch_stored_vies_verification(conn, normalized)
    stored_is_usable = bool(stored and stored["vies_verdict"] != INDETERMINATE_VIES)
    if (
        stored_is_usable
        and not force_refresh
        and is_fresh(stored["checked_at"], max_age_days=max_age_days, now=checked_now)
    ):
        return _response_from_stored(
            numero, normalized, stored, "stored_fresh", checked_now
        )

    result = vies_client.verify(normalized, timeout=timeout)
    if result.vies_verdict != INDETERMINATE_VIES:
        upsert_vies_verification(conn, result, origin="api")
        return _response(
            numero,
            normalized,
            result.vies_verdict,
            "vies_fresh",
            result.checked_at,
            0,
            False,
            None,
        )

    if stored_is_usable:
        insert_vies_attempt(conn, result, origin="api")
        return _response_from_stored(
            numero, normalized, stored, "stored_stale", checked_now
        )

    upsert_vies_verification(conn, result, origin="api")
    record_human_review_item(
        conn,
        source="api",
        input_raw=numero,
        numero_tva_nettoye=normalized,
        review_reason=result.error_message or "VIES indisponible",
    )
    return _response(
        numero,
        normalized,
        VERDICT_INDETERMINATE,
        "unavailable",
        result.checked_at,
        0,
        True,
        result.error_message,
    )


def _normalize_api_input(numero: str) -> str:
    from de13_tva.cleaning import normalize_vat_number

    return normalize_vat_number(numero)


def _response_from_stored(
    original: str,
    normalized: str,
    stored: dict[str, Any],
    origin: str,
    now: datetime,
) -> dict[str, Any]:
    checked_at = stored["checked_at"]
    needs_human_review = stored["vies_verdict"] == INDETERMINATE_VIES
    return _response(
        original,
        normalized,
        stored["vies_verdict"],
        origin,
        checked_at,
        freshness_days(checked_at, now),
        needs_human_review,
        stored.get("error_message") if needs_human_review else None,
    )


def _response(
    original: str,
    normalized: str,
    verdict: str,
    origin: str,
    checked_at: datetime,
    age_days: int,
    needs_human_review: bool,
    review_reason: str | None,
) -> dict[str, Any]:
    return {
        "input": original,
        "normalized": normalized,
        "verdict": verdict,
        "origin": origin,
        "checked_at": checked_at.isoformat(),
        "freshness_days": age_days,
        "needs_human_review": needs_human_review,
        "review_reason": review_reason,
    }
