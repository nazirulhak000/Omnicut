"""Template fallback content never invents product claims, and scrape-and-plan
keeps deliberate 4xx statuses (audit S1 follow-up). No network, no Gemini."""

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.compliance_lint import find_claim_term, find_price_term
from scripts.product_scraper import ProductScraper

INVENTED = (
    "การันตี", "ของแท้", "แท้ 100", "รับประกัน", "ทนทาน", "พรีเมียม", "ใช้จริงมา",
    "3 เดือน", "10 เท่า", "ไม่มีพัง", "ติดใจ", "รีวิวกันเยอะ", "ของเลียนแบบ", "ของปลอม",
    "หลายปี", "รอมา", "ชีวิตเปลี่ยน", "...",
)


def _texts(angle):
    for key in ("hook_title", "pain_point", "key_features", "price_deal", "tiktok_caption", "tiktok_hashtags"):
        yield str(angle.get(key) or "")
    for line in angle.get("script_lines") or []:
        yield line if isinstance(line, str) else str(line)


def test_fallback_matrix_has_no_invented_claims(monkeypatch):
    monkeypatch.setattr("scripts.config.get_gemini_api_keys", lambda: [])

    angles = ProductScraper.generate_content_matrix({"title": "Sony WH-1000XM5"}, count=10)

    assert len(angles) == 10
    for angle in angles:
        for text in _texts(angle):
            assert find_claim_term(text) is None, text
            assert find_price_term(text) is None, text
            for phrase in INVENTED:
                assert phrase not in text, (phrase, text)


@pytest.mark.parametrize("payload", [
    {"custom_keyword": "Sony WH-1000XM5", "duration": "999s"},
    {"custom_keyword": "Sony WH-1000XM5", "extra_beats": ["not_a_beat"]},
])
def test_scrape_and_plan_keeps_4xx(monkeypatch, payload):
    monkeypatch.setattr(
        ProductScraper, "generate_content_matrix",
        staticmethod(lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not generate"))),
    )

    response = TestClient(app).post("/api/products/scrape-and-plan", json=payload)

    assert response.status_code == 400, response.text
