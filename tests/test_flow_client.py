"""
Tests for scripts/flow_client.py
"""

import io
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
import pytest

from scripts.flow_client import FlowClient, FlowClientError


def test_get_token(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("secret_test_token_123\n", encoding="utf-8")
    client = FlowClient(token_file=token_file)
    assert client.get_token() == "secret_test_token_123"


def _make_mock_response(status_code: int, body_dict: dict):
    resp = MagicMock()
    resp.status = status_code
    resp.read.return_value = json.dumps(body_dict).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    return resp


def test_is_healthy_success():
    client = FlowClient()
    mock_resp = _make_mock_response(200, {"name": "flow-mcp"})

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.is_healthy() is True


def test_is_healthy_failure():
    client = FlowClient()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        assert client.is_healthy() is False


def test_get_status_call():
    client = FlowClient(token_file=Path("/nonexistent/token"))
    mock_resp = _make_mock_response(200, {
        "url": "https://flow.google.com/project/123",
        "signedIn": True,
        "inProject": True,
        "credits_remaining": 45,
    })

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.get_status(detailed=True)
        assert res["signedIn"] is True
        assert res["credits_remaining"] == 45


def test_generate_call():
    client = FlowClient(token_file=Path("/nonexistent/token"))
    mock_resp = _make_mock_response(200, {
        "job_ids": ["job_abc_123"],
        "task_id": "task_xyz",
    })

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.generate(
            project="TestProject",
            scenes=[{"prompt": "A test scene", "type": "video", "aspect_ratio": "9:16"}],
        )
        assert res["job_ids"] == ["job_abc_123"]


def test_flow_client_error_handling():
    client = FlowClient(token_file=Path("/nonexistent/token"))
    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:8787/api/generate",
        code=400,
        msg="Bad Request",
        hdrs={},
        fp=io.BytesIO(json.dumps({"error": "Scene prompt required"}).encode("utf-8")),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(FlowClientError, match="Scene prompt required"):
            client.generate(project="Err", scenes=[])
