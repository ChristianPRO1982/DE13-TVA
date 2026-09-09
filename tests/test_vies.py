import httpx

from de13_tva import vies
from de13_tva.vies import (
    INDETERMINATE_VIES,
    INVALID_VIES,
    VALID_VIES,
    ViesClient,
    split_vat_number,
)


def test_split_vat_number():
    assert split_vat_number("FR27552032534") == ("FR", "27552032534")


def test_vies_valid_response_with_injected_client():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/ms/FR/vat/27552032534")
        return httpx.Response(200, json={"isValid": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == VALID_VIES
    assert result.country_code == "FR"
    assert result.vat_number == "27552032534"
    assert result.http_status == 200
    assert result.error_message is None


def test_vies_invalid_response():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"isValid": False})
        )
    )

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == INVALID_VIES
    assert result.response_payload == {"isValid": False}


def test_vies_missing_is_valid_is_indeterminate():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"status": "OK"})
        )
    )

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == INDETERMINATE_VIES
    assert result.error_message == "Champ isValid absent ou non booléen"


def test_vies_non_object_json_is_indeterminate():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=["unexpected"])
        )
    )

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == INDETERMINATE_VIES
    assert result.response_payload == ["unexpected"]
    assert result.error_message == "JSON inattendu: objet attendu"


def test_vies_http_error_is_indeterminate():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    )

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == INDETERMINATE_VIES
    assert result.http_status == 503
    assert result.error_message == "HTTP 503"


def test_vies_invalid_json_is_indeterminate():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"{"))
    )

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == INDETERMINATE_VIES
    assert result.http_status == 200
    assert result.error_message.startswith("JSON invalide:")


def test_vies_timeout_is_indeterminate():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = ViesClient().verify("FR27552032534", timeout=1.0, client=client)

    assert result.vies_verdict == INDETERMINATE_VIES
    assert result.http_status is None
    assert result.error_message == "timeout"


def test_vies_owns_and_closes_default_client(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.closed = False

        def get(self, url):
            assert url.endswith("/ms/FR/vat/27552032534")
            return httpx.Response(200, json={"isValid": True})

        def close(self):
            self.closed = True

    fake_client = FakeClient()
    monkeypatch.setattr(vies.httpx, "Client", lambda timeout: fake_client)

    result = ViesClient().verify("FR27552032534", timeout=1.0)

    assert result.vies_verdict == VALID_VIES
    assert fake_client.closed
