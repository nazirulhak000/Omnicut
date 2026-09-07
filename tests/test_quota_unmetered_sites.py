"""
Three more Gemini call sites had no budget gate at all.

scripts/quota.py's check_budget() was wired into ai_bridge, the TTS engine
and the vision matcher -- but these three build `genai.Client` directly and
so could not be capped even in principle, and each folds every failure into
a plausible-looking fallback, which would have reported a spent budget as a
provider hiccup:

- scripts/api_voice.py    generate_ai_scripts()          POST /api/script/ai-generate
- scripts/product_scraper.py  generate_content_matrix()  (feeds both scrape-and-plan endpoints)
- scripts/script_tone_analyzer.py  classify_tone_shifts()  (runs in every pipeline)

Each now checks the budget before the call, and each caller reports the cap
as itself rather than as its own generic failure. The tests assert both
halves: a quota error must be visible, and a genuine provider failure must
still degrade exactly as it did.

Offline per .agents/rules/testing_standard.md -- no real network or AI calls.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.error_handler import AppError, ErrorCategory


def _quota_app_error() -> AppError:
    return AppError(
        category=ErrorCategory.AI_PROVIDER,
        code="AI_QUOTA_EXCEEDED",
        message_th="เกินโควต้าการใช้งาน AI ที่ตั้งไว้ต่อวันแล้ว",
        suggestion_th="โควต้า token ต่อวันเต็มแล้ว รอถึงวันถัดไปหรือปรับค่าใน .env",
    )


@pytest.fixture
def client():
    from scripts.api_server import app
    return TestClient(app)


_SCRIPT_REQ = {
    "product_name": "หูฟังบลูทูธ",
    "pain_point": "เสียงแตกเวลาเปิดดัง",
    "product_url": "https://shopee.co.th/x",
}


# ----------------------------------------------------------------------
# Site 1: POST /api/script/ai-generate
# ----------------------------------------------------------------------
def test_ai_generate_answers_429_when_over_budget(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    with patch("scripts.quota.check_budget", side_effect=_quota_app_error()):
        res = client.post("/api/script/ai-generate", json=_SCRIPT_REQ)

    assert res.status_code == 429, res.text
    assert "โควต้า" in res.json()["detail"]


def test_ai_generate_still_falls_back_on_a_provider_failure(client, monkeypatch):
    """A real Gemini failure keeps its graceful single-angle fallback."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")

    class _BrokenClient:
        def __init__(self, *a, **k):
            raise RuntimeError("network down")

    with patch("scripts.quota.check_budget", return_value=None), \
         patch("google.genai.Client", _BrokenClient):
        res = client.post("/api/script/ai-generate", json=_SCRIPT_REQ)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("angles"), "the fallback should still return an angle"
    # And it must not be dressed up as a quota problem.
    assert "โควต้า" not in str(body)


# ----------------------------------------------------------------------
# Site 2: product_scraper.generate_content_matrix
# ----------------------------------------------------------------------
def test_content_matrix_lets_a_quota_error_out(monkeypatch):
    """The template fallback must not absorb a spent budget."""
    from scripts.product_scraper import ProductScraper

    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    with patch("scripts.quota.check_budget", side_effect=_quota_app_error()):
        with pytest.raises(AppError) as excinfo:
            ProductScraper.generate_content_matrix(
                {"name": "หูฟัง", "specs": [], "pain_points": []}, count=2
            )

    assert excinfo.value.code == "AI_QUOTA_EXCEEDED"


def test_content_matrix_still_falls_back_on_a_provider_failure(monkeypatch):
    from scripts.product_scraper import ProductScraper

    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")

    class _BrokenClient:
        def __init__(self, *a, **k):
            raise RuntimeError("network down")

    with patch("scripts.quota.check_budget", return_value=None), \
         patch("google.genai.Client", _BrokenClient):
        angles = ProductScraper.generate_content_matrix(
            {"name": "หูฟัง", "specs": [], "pain_points": []}, count=2
        )

    assert angles, "the template fallback should still produce angles"


# ----------------------------------------------------------------------
# Site 3: script_tone_analyzer.classify_tone_shifts
# ----------------------------------------------------------------------
def _isolate_tone_cache(monkeypatch, tmp_path):
    """Point the module's own cache binding at tmp_path.

    The path is bound at import as a module-level name, so patching
    scripts.config would not reach it.
    """
    import scripts.script_tone_analyzer as sta

    cache_path = tmp_path / ".tone_cache.json"
    monkeypatch.setattr(sta, "TONE_CACHE_FILE", cache_path)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")

    # Fail loudly rather than quietly reading the real cache under
    # 02_Assets, which holds real entries: the module reads the binding and
    # the env var directly, so if either escapes the patch these tests would
    # pass or fail depending on what the machine happens to have.
    assert sta.TONE_CACHE_FILE == cache_path
    assert not sta.TONE_CACHE_FILE.exists()
    assert sta.ScriptToneAnalyzer.is_available(), "the env patch did not take"
    return sta


def test_tone_shifts_lets_a_quota_error_out(monkeypatch, tmp_path):
    """This runs in every pipeline, so it must not silently eat the cap."""
    sta = _isolate_tone_cache(monkeypatch, tmp_path)

    with patch("scripts.quota.check_budget", side_effect=_quota_app_error()):
        with pytest.raises(AppError) as excinfo:
            sta.ScriptToneAnalyzer.classify_tone_shifts(
                ["ปัญหาคือเสียงแตก", "ทางแก้คือหูฟังตัวนี้", "ซื้อเลยวันนี้ลด 50%"]
            )

    assert excinfo.value.code == "AI_QUOTA_EXCEEDED"


def test_tone_shifts_checks_the_cache_before_the_budget(monkeypatch, tmp_path):
    """A cache hit costs nothing, so it must not consume quota."""
    import hashlib

    sta = _isolate_tone_cache(monkeypatch, tmp_path)
    texts = ["ปัญหาคือเสียงแตก", "ทางแก้คือหูฟังตัวนี้"]

    # Seed the cache the way the module itself keys it.
    cache_key = hashlib.md5("|".join(texts).encode("utf-8")).hexdigest()
    sta.ScriptToneAnalyzer._save_cache({cache_key: ["major"]})

    # With the budget exhausted, the cached answer must still come back --
    # check_budget sits after the cache lookup, so it is never reached.
    with patch("scripts.quota.check_budget", side_effect=_quota_app_error()):
        result = sta.ScriptToneAnalyzer.classify_tone_shifts(texts)

    assert result == ["major"]


def test_tone_shifts_returns_empty_for_a_single_group_without_spending(monkeypatch, tmp_path):
    """Fewer than two groups has no boundary to classify, so no call is due."""
    sta = _isolate_tone_cache(monkeypatch, tmp_path)

    with patch("scripts.quota.check_budget", side_effect=_quota_app_error()):
        assert sta.ScriptToneAnalyzer.classify_tone_shifts(["เท่านั้น"]) == []
