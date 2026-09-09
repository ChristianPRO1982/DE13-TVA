from de13_tva import api


def test_openapi_is_available():
    schema = api.app.openapi()

    assert schema["info"]["title"] == "DE13 TVA"
    assert "/vat" in schema["paths"]


def test_vat_endpoint_uses_service(monkeypatch):
    calls = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(api, "connect", lambda: FakeConnection())
    monkeypatch.setattr(
        api, "ensure_schema", lambda conn: calls.append(("schema", conn))
    )
    monkeypatch.setattr(
        api,
        "verify_vat_for_api",
        lambda numero, conn, **kwargs: {
            "input": numero,
            "normalized": "FR27552032534",
            "verdict": "valide",
            "origin": "stored_fresh",
            "checked_at": "2026-09-09T12:00:00+00:00",
            "freshness_days": 0,
            "needs_human_review": False,
            "review_reason": None,
        },
    )
    response = api.verify_vat(
        numero="FR 27/552_032_534",
        force_refresh=True,
        max_age_days=30,
    )

    assert response["input"] == "FR 27/552_032_534"
    assert calls[0][0] == "schema"
