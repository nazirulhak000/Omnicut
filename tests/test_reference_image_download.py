"""
Unit tests for reference-image handling in ProductScraper.generate_content_matrix():
scraped product images arrive as remote http(s) URLs (no local file), and
generate_content_matrix must download them for Gemini vision input rather
than silently dropping every URL-shaped entry -- which used to make AI
scripts/rerolls write generic, unspecific copy despite having real product
photos available (see api_products.py's image_paths filters).

Follows testing_standard.md (offline, isolated with tmp_path/monkeypatch, no
live network or Gemini calls).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_scraper as ps
from scripts.product_scraper import ProductScraper, _validate_image_url, _download_image_bytes


def test_validate_image_url_rejects_private_ip(monkeypatch):
    """CDN image URLs don't need the page-domain allowlist, but still must
    not be usable as an SSRF vector against internal addresses."""
    monkeypatch.setattr(
        ps.socket, "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("127.0.0.1", 0))]
    )
    with pytest.raises(ValueError):
        _validate_image_url("http://internal.example.com/secret.jpg")


def test_validate_image_url_allows_non_allowlisted_public_cdn_host(monkeypatch):
    """Unlike _validate_scrape_url, image URLs are not restricted to
    shopee/tiktok domains -- product photos live on separate CDN hosts."""
    monkeypatch.setattr(
        ps.socket, "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))]
    )
    _validate_image_url("https://p16-oec-sg.ibyteimg.com/tos-alisg/example.webp")  # must not raise


def test_download_image_bytes_returns_data_and_mime(monkeypatch):
    monkeypatch.setattr(
        ps.socket, "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))]
    )

    class FakeHeaders:
        def get_content_type(self):
            return "image/webp"

    class FakeResp:
        headers = FakeHeaders()

        def read(self, n):
            return b"fake-image-bytes"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def geturl(self):
            return "https://p16-oec-sg.ibyteimg.com/tos-alisg/example.webp"

    class FakeOpener:
        def open(self, req, timeout=15):
            return FakeResp()

    monkeypatch.setattr(ps, "_build_safe_image_opener", lambda *h: FakeOpener())

    data, mime = _download_image_bytes("https://p16-oec-sg.ibyteimg.com/tos-alisg/example.webp")
    assert data == b"fake-image-bytes"
    assert mime == "image/webp"


def test_download_image_bytes_enforces_size_cap(monkeypatch):
    monkeypatch.setattr(
        ps.socket, "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))]
    )

    class FakeHeaders:
        def get_content_type(self):
            return "image/jpeg"

    oversized = b"x" * (ps.MAX_REFERENCE_IMAGE_BYTES + 100)

    class FakeResp:
        headers = FakeHeaders()

        def read(self, n):
            return oversized[:n]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeOpener:
        def open(self, req, timeout=15):
            return FakeResp()

    monkeypatch.setattr(ps, "_build_safe_image_opener", lambda *h: FakeOpener())

    with pytest.raises(ValueError):
        _download_image_bytes("https://cdn.example.com/huge.jpg")


def test_generate_content_matrix_downloads_url_image_paths(monkeypatch):
    """The image-reading loop must route http(s) image_paths entries through
    the downloader instead of treating them as local Path()s (which used to
    either crash or, after being filtered out upstream, never arrive here
    at all)."""
    import os

    downloaded = []

    def fake_download(url):
        downloaded.append(url)
        return b"bytes-for-" + url.encode(), "image/webp"

    monkeypatch.setattr(ps, "_download_image_bytes", fake_download)

    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["contents"] = contents
            raise RuntimeError("stop -- capturing contents only")

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    import google.genai as genai
    orig_client = genai.Client
    orig_key = os.environ.get("GEMINI_API_KEY")
    genai.Client = FakeClient
    os.environ["GEMINI_API_KEY"] = "fake-key-for-test"
    try:
        product_data = {"title": "T", "description": "D", "price_note": "P", "raw_text": "R"}
        ProductScraper.generate_content_matrix(
            product_data, count=1,
            image_paths=["https://p16-oec-sg.ibyteimg.com/tos-alisg/example.webp"],
        )
    finally:
        genai.Client = orig_client
        if orig_key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = orig_key

    assert downloaded == ["https://p16-oec-sg.ibyteimg.com/tos-alisg/example.webp"]
    contents = captured["contents"]
    assert isinstance(contents, list) and len(contents) == 2  # [prompt, image_part]
