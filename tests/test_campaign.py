from dataclasses import replace
from datetime import UTC, datetime

from de13_tva import campaign
from de13_tva.campaign import run_vies_campaign
from de13_tva.vies import INDETERMINATE_VIES, INVALID_VIES, VALID_VIES, ViesVerification


def verification(number: str, verdict: str) -> ViesVerification:
    return ViesVerification(
        numero_tva_nettoye=number,
        country_code=number[:2],
        vat_number=number[2:],
        vies_verdict=verdict,
        checked_at=datetime(2026, 9, 9, tzinfo=UTC),
        http_status=200,
        response_time_ms=12,
        response_payload={"isValid": verdict == VALID_VIES},
        error_message=None,
    )


class FakeClient:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def verify(self, normalized, *, timeout):
        self.calls.append((normalized, timeout))
        result = self.results.pop(0)
        return replace(result, numero_tva_nettoye=normalized)


def test_run_vies_campaign_counts_and_sleeps(monkeypatch):
    saved = []
    sleeps = []
    monkeypatch.setattr(
        campaign,
        "fetch_vies_candidates_for_verification",
        lambda conn, **kwargs: [
            {"numero_tva_nettoye": "FR11111111111"},
            {"numero_tva_nettoye": "FR22222222222"},
            {"numero_tva_nettoye": "FR33333333333"},
        ],
    )
    monkeypatch.setattr(
        campaign,
        "upsert_vies_verification",
        lambda conn, result, origin: saved.append((result, origin)),
    )
    client = FakeClient(
        [
            verification("FR11111111111", VALID_VIES),
            verification("FR22222222222", INVALID_VIES),
            verification("FR33333333333", INDETERMINATE_VIES),
        ]
    )

    summary = run_vies_campaign(
        object(),
        client=client,
        sample_size=3,
        limit=None,
        delay=0.5,
        timeout=2.0,
        force_refresh=False,
        refresh_days=None,
        sleeper=sleeps.append,
    )

    assert summary.selected == 3
    assert summary.valid == 1
    assert summary.invalid == 1
    assert summary.indeterminate == 1
    assert sleeps == [0.5, 0.5]
    assert [origin for _, origin in saved] == ["campaign", "campaign", "campaign"]
    assert client.calls[0] == ("FR11111111111", 2.0)


def test_run_vies_campaign_with_no_candidates(monkeypatch):
    monkeypatch.setattr(
        campaign,
        "fetch_vies_candidates_for_verification",
        lambda conn, **kwargs: [],
    )

    summary = run_vies_campaign(
        object(),
        client=FakeClient([]),
        sample_size=None,
        limit=0,
        delay=0,
        timeout=1.0,
        force_refresh=True,
        refresh_days=30,
    )

    assert summary.selected == 0
    assert summary.lines == ["Debut campagne VIES"]
