"""POST /api/products/resolve-tiktok-id is not an SSRF primitive and does
not invent product IDs from stray digits (audit S1-08). No real network."""

import socket

import pytest

import scripts.api_products as api_products
import scripts.product_scraper as scraper_module
from scripts.api_products import resolve_tiktok_product_id


def _forbid_network(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("no request may be sent for this input")

    monkeypatch.setattr(api_products, "_build_safe_opener", boom)
    monkeypatch.setattr("urllib.request.urlopen", boom)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/admin",
    "http://localhost:8000/api/products",
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "http://10.0.0.5/internal",
    "https://evil.example.com/redirect?to=shop",
])
def test_internal_and_foreign_urls_are_refused_before_any_request(monkeypatch, url):
    _forbid_network(monkeypatch)

    result = resolve_tiktok_product_id(url)

    assert result["success"] is False
    assert result["product_id"] is None


def test_allowed_host_resolving_to_private_ip_is_refused(monkeypatch):
    _forbid_network(monkeypatch)
    monkeypatch.setattr(
        scraper_module.socket,
        "getaddrinfo",
        lambda *_a, **_k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 0))],
    )

    result = resolve_tiktok_product_id("https://vt.tiktok.com/ZSabc123/")

    assert result["success"] is False


def test_digits_in_free_text_are_not_a_product_id(monkeypatch):
    _forbid_network(monkeypatch)

    result = resolve_tiktok_product_id("ออเดอร์ 202611091234567890")

    assert result == {"success": False, "product_id": None, "resolved_url": None}


def test_plain_id_and_product_url_still_resolve(monkeypatch):
    _forbid_network(monkeypatch)

    assert resolve_tiktok_product_id("1731628390379587684")["product_id"] == "1731628390379587684"
    assert (
        resolve_tiktok_product_id("https://shop.tiktok.com/th/pdp/1731628390379587684?x=1")["product_id"]
        == "1731628390379587684"
    )


def _fake_redirect(monkeypatch, final_url):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return final_url

    class FakeOpener:
        def open(self, *_a, **_k):
            return FakeResponse()

    monkeypatch.setattr(api_products, "_validate_scrape_url", lambda *_a, **_k: None)
    monkeypatch.setattr(api_products, "_build_safe_opener", lambda *_a: FakeOpener())


def test_shortlink_resolves_through_safe_opener(monkeypatch):
    _fake_redirect(monkeypatch, "https://shop.tiktok.com/view/product/1731628390379587684?region=TH")

    result = resolve_tiktok_product_id("https://vt.tiktok.com/ZSabc123/")

    assert result["success"] is True
    assert result["product_id"] == "1731628390379587684"


def test_redirect_with_only_stray_digits_is_not_a_product(monkeypatch):
    _fake_redirect(monkeypatch, "https://www.tiktok.com/@shop/video/7301234567890123456")

    result = resolve_tiktok_product_id("https://vt.tiktok.com/ZSabc123/")

    assert result["success"] is False
    assert result["product_id"] is None
