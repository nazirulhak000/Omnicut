"""Audit S1-04: image quality gate where product images are downloaded.

Offline: PIL-made images, a fake opener, no network.
"""
import io

import pytest
from PIL import Image

from scripts import product_scraper as ps
from scripts.image_quality_gate import (
    ImageHashRegistry,
    evaluate_image_bytes,
    sha256_of,
)


def _img(w, h, fmt="PNG", noise=False):
    img = Image.new("RGB", (w, h), (10, 120, 200))
    if noise:
        import os as _os

        img = Image.frombytes("RGB", (w, h), _os.urandom(w * h * 3))
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def test_thumbnail_is_rejected_in_thai():
    verdict = evaluate_image_bytes(_img(100, 100))
    assert not verdict.ok
    assert "ภาพความละเอียดต่ำ" in verdict.reason and "100x100" in verdict.reason


def test_short_edge_1080_passes_even_when_the_file_is_small():
    verdict = evaluate_image_bytes(_img(1080, 1500))
    assert verdict.ok and verdict.size < 100 * 1024


def test_small_edge_but_big_file_passes():
    data = _img(600, 600, noise=True)  # incompressible -> well over 100 KB
    assert len(data) >= 100 * 1024
    assert evaluate_image_bytes(data).ok


def test_landscape_uses_the_short_edge():
    assert not evaluate_image_bytes(_img(2000, 400)).ok
    assert evaluate_image_bytes(_img(2000, 1080)).ok


def test_undecodable_bytes_are_judged_by_size_alone():
    assert not evaluate_image_bytes(b"not an image at all").ok
    assert evaluate_image_bytes(b"x" * (100 * 1024)).ok
    assert not evaluate_image_bytes(b"").ok


def test_hash_registry_dedups_identical_bytes():
    reg = ImageHashRegistry()
    a = _img(1200, 1200)
    assert reg.register(a) is True
    assert reg.register(bytes(a)) is False
    assert sha256_of(a) in reg
    assert reg.register(_img(1300, 1300)) is True


def _patch_opener(monkeypatch, payload):
    monkeypatch.setattr(
        ps.socket, "getaddrinfo", lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))]
    )

    class Headers:
        def get_content_type(self):
            return "image/png"

    class Resp:
        headers = Headers()

        def read(self, n):
            return payload[:n]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Opener:
        def open(self, req, timeout=15):
            return Resp()

    monkeypatch.setattr(ps, "_build_safe_image_opener", lambda *h: Opener())


def test_download_rejects_low_res_thumbnail_but_can_opt_out(monkeypatch):
    thumb = _img(100, 100)
    _patch_opener(monkeypatch, thumb)
    with pytest.raises(ValueError) as err:
        ps._download_image_bytes("https://cdn.example.com/100:100.png")
    assert "ภาพความละเอียดต่ำ" in str(err.value)
    data, _ = ps._download_image_bytes("https://cdn.example.com/100:100.png", enforce_quality=False)
    assert data == thumb


def test_download_accepts_full_size_image(monkeypatch):
    big = _img(1200, 1200)
    _patch_opener(monkeypatch, big)
    data, mime = ps._download_image_bytes("https://cdn.example.com/hero.png")
    assert data == big and mime == "image/png"
