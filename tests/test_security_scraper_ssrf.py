"""
Regression tests for the P0.5 4b security fix: scripts/product_scraper.py
only checked the URL scheme before fetching -- no host/IP validation, and
urllib followed redirects automatically then re-fetched `resp.geturl()`
without re-validating the new host.

Because CORS is `allow_origins=["*"]` and no endpoint has authentication,
any web page the user has open could POST a URL to /api/products/scrape
and use this backend as an SSRF proxy: cloud metadata endpoint
(169.254.169.254 -- IAM credential theft once deployed), the app's own API
(127.0.0.1:8000), or internal network scanning (10.x/172.16-31.x/192.168.x,
with scraped title/price echoed back as a hit/miss oracle) -- plus a
redirect-based bypass where an attacker-controlled URL 302s to an internal
target that urllib would follow unchecked.

Fix: `_validate_scrape_url()` enforces a domain allowlist (Shopee/TikTok +
their short-link domains) AND resolves the hostname via
`socket.getaddrinfo`, rejecting loopback/private/link-local/reserved/
multicast ranges via the stdlib `ipaddress` module. `_SafeRedirectHandler`
re-validates every redirect hop instead of following blindly, and
`resolved_url` is re-validated again before the second (content) fetch.

Isolated / offline per .agents/rules/testing_standard.md rule 2 -- no real
network fetches are made; `socket.getaddrinfo` is monkeypatched so tests
work without a live network connection, and no test relies on actually
reaching shopee.co.th or tiktok.com.
"""
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.product_scraper import (
    ProductScraper,
    _validate_scrape_url,
    _hostname_allowed,
    _SafeRedirectHandler,
)


def _fake_getaddrinfo(ip_by_host):
    """Builds a socket.getaddrinfo replacement mapping hostname -> IP string,
    in the same shape socket.getaddrinfo returns, so tests never depend on a
    live DNS resolver or network connection."""

    def _fn(host, *args, **kwargs):
        if host not in ip_by_host:
            raise socket.gaierror(f"no mock entry for host {host}")
        ip = ip_by_host[host]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _fn


# ---------------------------------------------------------------------------
# Domain allowlist
# ---------------------------------------------------------------------------

def test_hostname_allowed_for_shopee_and_subdomains():
    assert _hostname_allowed("shopee.co.th")
    assert _hostname_allowed("s.shopee.co.th")
    assert _hostname_allowed("www.shopee.co.th")


def test_hostname_allowed_for_tiktok_and_short_links():
    assert _hostname_allowed("tiktok.com")
    assert _hostname_allowed("www.tiktok.com")
    assert _hostname_allowed("vt.tiktok.com")
    assert _hostname_allowed("vm.tiktok.com")
    assert _hostname_allowed("shp.ee")


def test_hostname_rejected_for_arbitrary_and_lookalike_domains():
    assert not _hostname_allowed("evil.com")
    assert not _hostname_allowed("169.254.169.254")
    assert not _hostname_allowed("127.0.0.1")
    # lookalike / suffix-confusion attempts must not pass a naive "in" check
    assert not _hostname_allowed("shopee.co.th.evil.com")
    assert not _hostname_allowed("notshopee.co.th")
    assert not _hostname_allowed("evilshopee.co.th")


# ---------------------------------------------------------------------------
# _validate_scrape_url -- the exploit inputs named in the audit doc
# ---------------------------------------------------------------------------

def test_blocks_cloud_metadata_ip():
    with pytest.raises(ValueError):
        _validate_scrape_url("http://169.254.169.254/latest/meta-data/iam/security-credentials/")


def test_blocks_own_api_loopback():
    with pytest.raises(ValueError):
        _validate_scrape_url("http://127.0.0.1:8000/")
    with pytest.raises(ValueError):
        _validate_scrape_url("http://localhost:8000/")


def test_blocks_rfc1918_private_ranges():
    for bad in [
        "http://192.168.1.1/",
        "http://10.0.0.5/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
    ]:
        with pytest.raises(ValueError):
            _validate_scrape_url(bad)


def test_blocks_non_http_schemes():
    with pytest.raises(ValueError):
        _validate_scrape_url("ftp://shopee.co.th/x")
    with pytest.raises(ValueError):
        _validate_scrape_url("file:///etc/passwd")


def test_blocks_domain_not_on_allowlist(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"evil.com": "93.184.216.34"}))
    with pytest.raises(ValueError):
        _validate_scrape_url("http://evil.com/product/123")


def test_allows_legit_shopee_and_tiktok_domains(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        _fake_getaddrinfo({
            "shopee.co.th": "8.8.8.8",
            "shp.ee": "8.8.8.8",
            "vt.tiktok.com": "8.8.8.8",
        }),
    )
    _validate_scrape_url("https://shopee.co.th/product/123/456")
    _validate_scrape_url("https://shp.ee/abc123")
    _validate_scrape_url("https://vt.tiktok.com/xyz")


def test_allowed_domain_that_resolves_to_private_ip_is_still_blocked(monkeypatch):
    """DNS-rebinding-style defense in depth: even a domain on the allowlist
    must be refused if it resolves to a non-public address."""
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo({"shopee.co.th": "127.0.0.1"}))
    with pytest.raises(ValueError):
        _validate_scrape_url("https://shopee.co.th/product/123")


# ---------------------------------------------------------------------------
# Redirect-hop validation -- urllib follows redirects automatically by
# default; _SafeRedirectHandler must re-validate every hop.
# ---------------------------------------------------------------------------

def test_redirect_handler_blocks_hop_to_internal_target(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        _fake_getaddrinfo({"shp.ee": "8.8.8.8"}),
    )
    handler = _SafeRedirectHandler()
    import urllib.request as ur
    req = ur.Request("https://shp.ee/abc123")
    with pytest.raises(ValueError):
        handler.redirect_request(
            req, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/"
        )


def test_redirect_handler_allows_hop_to_another_allowed_domain(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        _fake_getaddrinfo({"shp.ee": "8.8.8.8", "shopee.co.th": "8.8.8.8"}),
    )
    handler = _SafeRedirectHandler()
    import urllib.request as ur
    req = ur.Request("https://shp.ee/abc123")
    # Should not raise; falls through to the real HTTPRedirectHandler logic
    # which needs a fully-formed fp/headers to build the follow-up request,
    # so we only assert validation itself doesn't reject it.
    try:
        handler.redirect_request(
            req, None, 302, "Found", {}, "https://shopee.co.th/product/123"
        )
    except ValueError:
        pytest.fail("legit redirect hop to an allowed domain must not be rejected")
    except Exception:
        # Any failure past validation (e.g. missing fp for the base class
        # machinery) is not what this test is about.
        pass


# ---------------------------------------------------------------------------
# End-to-end: ProductScraper.scrape_url must still raise ValueError (not
# silently proceed) for a malicious URL, and legitimate URLs must still be
# scrapeable (network calls mocked so this stays offline).
# ---------------------------------------------------------------------------

def test_scrape_url_raises_valueerror_for_ssrf_attempt():
    with pytest.raises(ValueError):
        ProductScraper.scrape_url("http://169.254.169.254/latest/meta-data/iam/security-credentials/")


def test_scrape_url_raises_valueerror_for_internal_network_scan():
    with pytest.raises(ValueError):
        ProductScraper.scrape_url("http://192.168.1.1/admin")


def test_scrape_url_still_works_for_legit_domain_end_to_end(monkeypatch):
    """Exercises the full scrape_url path (redirect resolution + content
    fetch) against a mocked opener, confirming legitimate scraping behavior
    survives the SSRF fix."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        _fake_getaddrinfo({"shopee.co.th": "8.8.8.8"}),
    )

    class _FakeResp:
        def __init__(self, url, body=b""):
            self._url = url
            self._body = body

        def geturl(self):
            return self._url

        def read(self, n=-1):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _FakeOpener:
        def __init__(self, *a, **kw):
            pass

        def open(self, req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if "shopee.co.th" not in url:
                raise AssertionError(f"unexpected fetch target: {url}")
            html = (
                b'<html><head>'
                b'<meta property="og:title" content="Mock Product Title">'
                b'<meta property="og:description" content="A great mock product.">'
                b'</head></html>'
            )
            return _FakeResp(url, html)

    import scripts.product_scraper as ps_mod
    monkeypatch.setattr(ps_mod, "_build_safe_opener", lambda *h: _FakeOpener())

    result = ProductScraper.scrape_url("https://shopee.co.th/product/123/456")
    assert result["platform"] == "shopee"
    assert "Mock Product Title" in result["title"]
