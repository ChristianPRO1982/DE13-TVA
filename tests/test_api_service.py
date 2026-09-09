from datetime import UTC, datetime, timedelta

from de13_tva import api_service
from de13_tva.vies import INDETERMINATE_VIES, VALID_VIES, ViesVerification

EU_CODES = {"BE", "DK", "FI", "FR", "IT", "LU", "NL", "PL", "PT", "SE"}
NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


class FakeClient:
    def __init__(self, result: ViesVerification):
        self.result = result
        self.calls = []

    def verify(self, normalized, *, timeout):
        self.calls.append((normalized, timeout))
        return self.result


def result(number: str, verdict: str, error: str | None = None) -> ViesVerification:
    return ViesVerification(
        numero_tva_nettoye=number,
        country_code=number[:2],
        vat_number=number[2:],
        vies_verdict=verdict,
        checked_at=NOW,
        http_status=200 if error is None else None,
        response_time_ms=10,
        response_payload={"isValid": verdict == VALID_VIES} if error is None else None,
        error_message=error,
    )


def setup_api_service(monkeypatch, stored=None):
    reviews = []
    saved = []
    monkeypatch.setattr(api_service, "load_eu_country_codes", lambda path: EU_CODES)
    monkeypatch.setattr(
        api_service,
        "fetch_stored_vies_verification",
        lambda conn, normalized: stored,
    )
    monkeypatch.setattr(
        api_service,
        "record_human_review_item",
        lambda conn, **kwargs: reviews.append(kwargs),
    )
    monkeypatch.setattr(
        api_service,
        "upsert_vies_verification",
        lambda conn, verification, origin: saved.append((verification, origin)),
    )
    return reviews, saved


def stored_verification(checked_at: datetime) -> dict[str, object]:
    return {
        "numero_tva_nettoye": "FR27552032534",
        "vies_verdict": "valide",
        "checked_at": checked_at,
    }


def test_api_structural_reject_records_human_review(monkeypatch):
    reviews, _ = setup_api_service(monkeypatch)
    client = FakeClient(result("", VALID_VIES))

    response = api_service.verify_vat_for_api(
        "---",
        object(),
        vies_client=client,
        force_refresh=False,
        max_age_days=30,
        timeout=1.0,
        now=NOW,
    )

    assert response["origin"] == "structural_reject"
    assert response["verdict"] == "indetermine"
    assert response["needs_human_review"]
    assert reviews[0]["review_reason"] == "pays_absent"
    assert client.calls == []


def test_api_returns_stored_fresh_without_calling_vies(monkeypatch):
    setup_api_service(monkeypatch, stored_verification(NOW - timedelta(days=2)))
    client = FakeClient(result("FR27552032534", VALID_VIES))

    response = api_service.verify_vat_for_api(
        "FR 27 552 032 534",
        object(),
        vies_client=client,
        force_refresh=False,
        max_age_days=30,
        timeout=1.0,
        now=NOW,
    )

    assert response["origin"] == "stored_fresh"
    assert response["freshness_days"] == 2
    assert client.calls == []


def test_api_calls_vies_for_missing_stored_value(monkeypatch):
    _, saved = setup_api_service(monkeypatch)
    client = FakeClient(result("FR27552032534", VALID_VIES))

    response = api_service.verify_vat_for_api(
        "FR/27_552_032_534",
        object(),
        vies_client=client,
        force_refresh=False,
        max_age_days=30,
        timeout=1.0,
        now=NOW,
    )

    assert response["normalized"] == "FR27552032534"
    assert response["origin"] == "vies_fresh"
    assert saved[0][1] == "api"


def test_api_force_refresh_ignores_fresh_stored_value(monkeypatch):
    setup_api_service(monkeypatch, stored_verification(NOW))
    client = FakeClient(result("FR27552032534", VALID_VIES))

    response = api_service.verify_vat_for_api(
        "FR27552032534",
        object(),
        vies_client=client,
        force_refresh=True,
        max_age_days=30,
        timeout=2.0,
        now=NOW,
    )

    assert response["origin"] == "vies_fresh"
    assert client.calls == [("FR27552032534", 2.0)]


def test_api_returns_stale_stored_when_refresh_is_indeterminate(monkeypatch):
    setup_api_service(monkeypatch, stored_verification(NOW - timedelta(days=40)))
    client = FakeClient(result("FR27552032534", INDETERMINATE_VIES, "timeout"))

    response = api_service.verify_vat_for_api(
        "FR27552032534",
        object(),
        vies_client=client,
        force_refresh=False,
        max_age_days=30,
        timeout=1.0,
        now=NOW,
    )

    assert response["origin"] == "stored_stale"
    assert response["freshness_days"] == 40


def test_api_unavailable_without_stored_value_records_review(monkeypatch):
    reviews, _ = setup_api_service(monkeypatch)
    client = FakeClient(result("FR27552032534", INDETERMINATE_VIES, "timeout"))

    response = api_service.verify_vat_for_api(
        "FR27552032534",
        object(),
        vies_client=client,
        force_refresh=False,
        max_age_days=30,
        timeout=1.0,
        now=NOW,
    )

    assert response["origin"] == "unavailable"
    assert response["needs_human_review"]
    assert reviews[0]["review_reason"] == "timeout"
