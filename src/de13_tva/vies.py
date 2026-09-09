"""VIES client and response mapping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import httpx

VIES_BASE_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api"
VALID_VIES = "valide"
INVALID_VIES = "invalide"
INDETERMINATE_VIES = "indetermine"


@dataclass(frozen=True)
class ViesVerification:
    numero_tva_nettoye: str
    country_code: str
    vat_number: str
    vies_verdict: str
    checked_at: datetime
    http_status: int | None
    response_time_ms: int | None
    response_payload: Any | None
    error_message: str | None


def split_vat_number(numero_tva_nettoye: str) -> tuple[str, str]:
    return numero_tva_nettoye[:2], numero_tva_nettoye[2:]


def utc_now() -> datetime:
    return datetime.now(UTC)


class ViesClient:
    def __init__(self, base_url: str = VIES_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def verify(
        self,
        numero_tva_nettoye: str,
        *,
        timeout: float,
        client: httpx.Client | None = None,
    ) -> ViesVerification:
        country_code, vat_number = split_vat_number(numero_tva_nettoye)
        url = f"{self.base_url}/ms/{country_code}/vat/{vat_number}"
        own_client = client is None
        http_client = client or httpx.Client(timeout=timeout)
        start = perf_counter()

        try:
            response = http_client.get(url)
            response_time_ms = int((perf_counter() - start) * 1000)
            if not 200 <= response.status_code < 300:
                return self._indeterminate(
                    numero_tva_nettoye,
                    country_code,
                    vat_number,
                    response.status_code,
                    response_time_ms,
                    None,
                    f"HTTP {response.status_code}",
                )

            try:
                payload = response.json()
            except ValueError as exc:
                return self._indeterminate(
                    numero_tva_nettoye,
                    country_code,
                    vat_number,
                    response.status_code,
                    response_time_ms,
                    None,
                    f"JSON invalide: {exc}",
                )

            if not isinstance(payload, dict):
                return self._indeterminate(
                    numero_tva_nettoye,
                    country_code,
                    vat_number,
                    response.status_code,
                    response_time_ms,
                    payload,
                    "JSON inattendu: objet attendu",
                )

            is_valid = payload.get("isValid")
            if is_valid is True:
                verdict = VALID_VIES
                error_message = None
            elif is_valid is False:
                verdict = INVALID_VIES
                error_message = None
            else:
                verdict = INDETERMINATE_VIES
                error_message = "Champ isValid absent ou non booleen"

            return ViesVerification(
                numero_tva_nettoye=numero_tva_nettoye,
                country_code=country_code,
                vat_number=vat_number,
                vies_verdict=verdict,
                checked_at=utc_now(),
                http_status=response.status_code,
                response_time_ms=response_time_ms,
                response_payload=payload,
                error_message=error_message,
            )
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            return self._indeterminate(
                numero_tva_nettoye,
                country_code,
                vat_number,
                None,
                int((perf_counter() - start) * 1000),
                None,
                str(exc) or exc.__class__.__name__,
            )
        finally:
            if own_client:
                http_client.close()

    def _indeterminate(
        self,
        numero_tva_nettoye: str,
        country_code: str,
        vat_number: str,
        http_status: int | None,
        response_time_ms: int | None,
        response_payload: Any | None,
        error_message: str,
    ) -> ViesVerification:
        return ViesVerification(
            numero_tva_nettoye=numero_tva_nettoye,
            country_code=country_code,
            vat_number=vat_number,
            vies_verdict=INDETERMINATE_VIES,
            checked_at=utc_now(),
            http_status=http_status,
            response_time_ms=response_time_ms,
            response_payload=response_payload,
            error_message=error_message,
        )
