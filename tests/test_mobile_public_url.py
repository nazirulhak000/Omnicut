"""Mobile / quick-post links must open on the owner's phone (Colab tunnel), not a dead LAN IP."""

from __future__ import annotations

from starlette.requests import Request

from scripts.api_render import _public_mobile_url


def _request(headers: dict, scheme: str = "http", server=("127.0.0.1", 8000)) -> Request:
    raw = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/api/status", "headers": raw,
                    "scheme": scheme, "server": server, "query_string": b""})


def test_env_public_url_wins(monkeypatch):
    monkeypatch.setenv("OMNICUT_PUBLIC_URL", "https://studio.nazirulhak.com/")
    req = _request({"host": "192.168.1.5:8000"})
    assert _public_mobile_url(req, "192.168.1.5") == "https://studio.nazirulhak.com"


def test_forwarded_tunnel_host_used(monkeypatch):
    monkeypatch.delenv("OMNICUT_PUBLIC_URL", raising=False)
    req = _request({"host": "localhost:8000", "x-forwarded-host": "studio.nazirulhak.com",
                    "x-forwarded-proto": "https"})
    assert _public_mobile_url(req, "10.0.0.2") == "https://studio.nazirulhak.com"


def test_plain_public_host_used(monkeypatch):
    monkeypatch.delenv("OMNICUT_PUBLIC_URL", raising=False)
    req = _request({"host": "studio.example.com"}, scheme="https")
    assert _public_mobile_url(req, "10.0.0.2") == "https://studio.example.com"


def test_localhost_falls_back_to_lan(monkeypatch):
    monkeypatch.delenv("OMNICUT_PUBLIC_URL", raising=False)
    for host in ("localhost:5173", "127.0.0.1:8000", "[::1]:8000"):
        assert _public_mobile_url(_request({"host": host}), "192.168.1.9") == "https://192.168.1.9:5173"
    assert _public_mobile_url(None, "192.168.1.9") == "https://192.168.1.9:5173"
