"""FastAPI application for VAT verification."""

from __future__ import annotations

from fastapi import FastAPI, Query

from de13_tva.api_service import verify_vat_for_api
from de13_tva.database import connect, ensure_schema
from de13_tva.settings import DEFAULT_FRESHNESS_DAYS, DEFAULT_VIES_TIMEOUT_SECONDS
from de13_tva.vies import ViesClient

app = FastAPI(title="DE13 TVA", version="0.1.0")


@app.get("/vat")
def verify_vat(
    numero: str = Query(..., description="Numero de TVA brut ou deja normalise"),
    force_refresh: bool = False,
    max_age_days: int = DEFAULT_FRESHNESS_DAYS,
):
    with connect() as conn:
        ensure_schema(conn)
        return verify_vat_for_api(
            numero,
            conn,
            vies_client=ViesClient(),
            force_refresh=force_refresh,
            max_age_days=max_age_days,
            timeout=DEFAULT_VIES_TIMEOUT_SECONDS,
        )
