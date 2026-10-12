import argparse
import io
import json

import pytest

from tools.hyperframes_workflow import local_api_url, request_api


@pytest.mark.parametrize("value", ["https://example.com", "http://127.0.0.1@evil.example", "http://localhost/path", "http://localhost?key=x", "file:///private", "http://192.168.1.1:8000"])
def test_client_cannot_send_configured_key_to_foreign_origin(value):
    with pytest.raises(argparse.ArgumentTypeError):
        local_api_url(value)


def test_claim_scope_and_lease_payload_are_sent_to_api_only():
    requests = []
    def opener(request, timeout):
        requests.append(request)
        return io.BytesIO(b'{"job":{"generation":2}}')
    response = request_api("http://127.0.0.1:8000", "second", "creative_id", "claim", {"executor_id": "agent", "expected_generation": 1}, key="test-key", opener=opener)
    assert response["job"]["generation"] == 2
    assert requests[0].headers["X-omnicut-channel"] == "second"
    assert requests[0].headers["X-api-key"] == "test-key"
    assert json.loads(requests[0].data)["expected_generation"] == 1
    assert requests[0].get_method() == "POST"
