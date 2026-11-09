"""Scraped product images stay on the product itself (audit S1-04 / S1-18).

No network: the page HTML is served by a fake opener.
"""

import scripts.product_scraper as scraper_module
from scripts.product_scraper import ProductScraper, _deduplicate_and_filter_images

SHOPEE_URL = "https://shopee.co.th/product/111/222"
GALLERY = "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/{h}~tplv-aphluv4xwc-crop-webp:{d}:{d}.webp"
H1 = "98de2f23620d4c7ca5e1f4d1b2e9972a"
H2 = "f403e4a14d5b4eaf980650dfe9982fd7"


def test_foreign_hosts_are_dropped():
    urls = [
        GALLERY.format(h=H1, d=800),
        "https://cdn.other.com/jbl-tune.png",
        "https://ads.example.net/banner_800x800.jpg",
        "https://down-th.img.susercontent.com/file/th-11134207-7r98o-abc",
    ]
    result = _deduplicate_and_filter_images(urls)
    assert GALLERY.format(h=H1, d=800) in result
    assert "https://down-th.img.susercontent.com/file/th-11134207-7r98o-abc" in result
    assert not any("other.com" in u or "example.net" in u for u in result)


def test_thumbnail_variants_are_upgraded_or_dropped():
    urls = [
        GALLERY.format(h=H1, d=100),  # TikTok template -> asks for 800:800
        "https://p16-oec-sg.ibyteimg.com/obj/thumb_100x100.jpg",  # no template, known tiny -> dropped
        "https://down-th.img.susercontent.com/file/th-11134207-abc_tn",  # Shopee thumbnail
    ]
    result = _deduplicate_and_filter_images(urls)
    assert GALLERY.format(h=H1, d=800) in result
    assert "https://down-th.img.susercontent.com/file/th-11134207-abc" in result
    assert not any(":100:100" in u or "100x100" in u or u.endswith("_tn") for u in result)


def test_large_crop_variant_is_kept_and_deduplicated():
    # "crop-webp:1000:1000" is the gallery size, not a thumbnail.
    big = GALLERY.format(h=H2, d=1000)
    result = _deduplicate_and_filter_images([GALLERY.format(h=H2, d=260), big])
    assert result == [big]


def test_skip_words_only_match_path_tokens():
    # S1-18: "star"/"arrow"/"icon" inside a hash, a host or a longer word is fine.
    keep = [
        "https://p16-oec-sg.ibyteimg.com/obj/starlight-case/" + H1 + ".jpg",
        "https://p16-oec-sg.ibyteimg.com/obj/arrowhead_cable/" + H2 + ".jpg",
    ]
    drop = [
        "https://p16-oec-sg.ibyteimg.com/obj/ui/star.png",
        "https://p16-oec-sg.ibyteimg.com/obj/ui/arrow-right.png",
        "https://p16-oec-sg.ibyteimg.com/obj/shop/icon_cart.png",
        "https://p16-oec-sg.ibyteimg.com/obj/ui/badge.svg",
    ]
    result = _deduplicate_and_filter_images(keep + drop)
    assert sorted(result) == sorted(keep)


def test_scrape_ignores_page_img_tags_and_keeps_og_image(monkeypatch):
    og = GALLERY.format(h=H1, d=800)
    html = (
        f'<html><head><meta property="og:title" content="Anker Soundcore R50i">'
        f'<meta property="og:description" content="หูฟัง Bluetooth 5.3">'
        f'<meta property="og:image" content="{og}"></head><body>'
        f'<img src="{GALLERY.format(h=H2, d=800)}">'  # recommended-product carousel
        '<img src="https://cdn.other.com/jbl-tune.png">'
        "</body></html>"
    )

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
        def open(self, *_a, **_k):
            return FakeResponse()

    monkeypatch.setattr(scraper_module, "_validate_scrape_url", lambda *_a, **_k: None)
    monkeypatch.setattr(scraper_module, "_build_safe_opener", lambda *_a: FakeOpener())

    result = ProductScraper.scrape_url(SHOPEE_URL)

    assert result["images"] == [og]
