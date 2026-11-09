"""Scraper failure modes (audit S1-05 / S1-06 / S1-07).

All network access is faked: `_build_safe_opener` returns an in-memory opener
and `_validate_scrape_url` is a no-op (its own SSRF tests live elsewhere).
"""

import socket

import pytest

import scripts.product_scraper as scraper_module
from scripts.api_intake import _looks_like_waf_challenge
from scripts.product_scraper import ProductScraper, _extract_specs_from_text

SHOPEE_URL = "https://shopee.co.th/product/111/222"


def _fake_network(monkeypatch, html: str = "", *, error: Exception = None):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return SHOPEE_URL

        def read(self, *_):
            return html.encode("utf-8")

    class FakeOpener:
        def open(self, *_args, **_kwargs):
            if error is not None:
                raise error
            return FakeResponse()

    monkeypatch.setattr(scraper_module, "_validate_scrape_url", lambda *_a, **_k: None)
    monkeypatch.setattr(scraper_module, "_build_safe_opener", lambda *_a: FakeOpener())
    monkeypatch.setattr(
        scraper_module,
        "_scrape_rendered_page",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Shopee must not open a browser")),
    )


def test_extract_specs_from_text_accepts_none():
    assert _extract_specs_from_text(None) == []
    assert _extract_specs_from_text("") == []


def test_page_without_any_description_does_not_crash(monkeypatch):
    # S1-07: no og:description / description meta and no body text used to
    # make description None -> AttributeError in _extract_specs_from_text.
    _fake_network(
        monkeypatch,
        '<html><head><meta property="og:title" content="Anker Soundcore R50i"></head><body></body></html>',
    )

    result = ProductScraper.scrape_url(SHOPEE_URL)

    assert result["title"] == "Anker Soundcore R50i"
    assert result["description"] == ""
    assert result["source_missing"] is True
    assert result["needs_manual"] is True
    assert result["source_warning"]


def test_missing_description_is_never_replaced_by_an_invented_claim(monkeypatch):
    # S1-06: the placeholder "สินค้าคุณภาพยอดนิยม การันตีของแท้" used to become
    # the AI's only source text.
    _fake_network(monkeypatch, "<html><head><title>x</title></head><body></body></html>")

    result = ProductScraper.scrape_url(SHOPEE_URL)

    assert "การันตี" not in result["description"]
    assert "การันตี" not in result["raw_text"]
    assert result["source_missing"] is True


def test_shopee_captcha_page_is_flagged_not_scraped(monkeypatch):
    # S1-05: the captcha <title> used to become the product name and the
    # result passed _looks_like_waf_challenge as a normal product.
    _fake_network(
        monkeypatch,
        "<html><head><title>Shopee Security Verification Page Please Wait</title></head>"
        "<body><div>Please wait while we verify your browser</div></body></html>",
    )

    result = ProductScraper.scrape_url(SHOPEE_URL)

    assert result["challenge"] is True
    assert result["needs_manual"] is True
    assert "Security" not in result["title"]
    assert "Verification" not in result["title"]
    assert "Captcha" in result["source_warning"]
    assert _looks_like_waf_challenge(result) is True


def test_timeout_falls_back_with_needs_manual(monkeypatch):
    _fake_network(monkeypatch, error=socket.timeout("timed out"))

    result = ProductScraper.scrape_url(SHOPEE_URL)

    assert result["metadata_source"] == "slug_fallback"
    assert result["description"] == ""
    assert result["needs_manual"] is True
    assert result["source_warning"]
    assert _looks_like_waf_challenge(result) is True


def test_real_product_page_is_not_flagged(monkeypatch):
    _fake_network(
        monkeypatch,
        '<html><head><meta property="og:title" content="Anker Soundcore R50i">'
        '<meta property="og:description" content="หูฟัง Bluetooth 5.3 แบต 10 ชั่วโมง"></head>'
        "<body></body></html>",
    )

    result = ProductScraper.scrape_url(SHOPEE_URL)

    assert result["needs_manual"] is False
    assert result["source_missing"] is False
    assert "challenge" not in result
    assert "Bluetooth 5.3" in result["description"]
