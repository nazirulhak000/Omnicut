"""
Unit tests for the single-angle script reroll feature:
- ProductStore.replace_angle_content() overwrites only script-content fields,
  preserving lifecycle fields (status, project_name, video_url, qc_note).
- POST /api/products/{id}/angles/{angle_id}/reroll-script validates
  duration/extra_beats and creates a background task.
- ProductScraper.generate_content_matrix()'s duration/extra_beats/
  angle_id_override parameters actually change the generated prompt.

Follows testing_standard.md (offline, isolated with tmp_path, no side effects
on real files, no live Gemini calls).
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store as ps
from scripts.product_store import ProductStore
from scripts.api_server import app
from scripts.product_scraper import (
    ProductScraper,
    DURATION_SPECS,
    EXTRA_BEAT_BLOCKS,
    content_types_for_angle,
)


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


def test_replace_angle_content_preserves_lifecycle_fields(isolated_store):
    product = ProductStore.add(name="Widget", url="https://x.test/w")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "pain_point",
        "angle_name": "Old name",
        "hook_title": "Old hook",
        "script_lines": ["old line"],
        "status": "rendered",
        "project_name": "widget_proj_1",
        "video_url": "04_Exports/widget.mp4",
        "qc_note": "looked fine",
    }])

    updated = ProductStore.replace_angle_content(product["id"], "pain_point", {
        "angle_name": "New name",
        "hook_title": "New hook",
        "script_lines": ["new line 1", "new line 2"],
        "ad_tone": "commercial_hype",
    })

    angle = next(a for a in updated["angles"] if a["angle_id"] == "pain_point")
    assert angle["angle_name"] == "New name"
    assert angle["hook_title"] == "New hook"
    assert angle["script_lines"] == ["new line 1", "new line 2"]
    assert angle["ad_tone"] == "commercial_hype"
    # Lifecycle fields untouched by the reroll.
    assert angle["status"] == "rendered"
    assert angle["project_name"] == "widget_proj_1"
    assert angle["video_url"] == "04_Exports/widget.mp4"
    assert angle["qc_note"] == "looked fine"


def test_replace_angle_content_missing_angle_raises(isolated_store):
    product = ProductStore.add(name="Widget", url="https://x.test/w2")
    with pytest.raises(ValueError):
        ProductStore.replace_angle_content(product["id"], "no_such_angle", {"hook_title": "x"})


def test_reroll_endpoint_rejects_unknown_duration(isolated_store):
    product = ProductStore.add(name="Widget", url="https://x.test/w3")
    ProductStore.update(product["id"], angles=[{"angle_id": "pain_point", "status": "scripted"}])

    client = TestClient(app)
    res = client.post(
        f"/api/products/{product['id']}/angles/pain_point/reroll-script",
        json={"duration": "120s"},
    )
    assert res.status_code == 400
    assert "duration" in res.json()["detail"]


def test_reroll_endpoint_rejects_unknown_extra_beat(isolated_store):
    product = ProductStore.add(name="Widget", url="https://x.test/w4")
    ProductStore.update(product["id"], angles=[{"angle_id": "pain_point", "status": "scripted"}])

    client = TestClient(app)
    res = client.post(
        f"/api/products/{product['id']}/angles/pain_point/reroll-script",
        json={"extra_beats": ["not_a_real_beat"]},
    )
    assert res.status_code == 400
    assert "extra_beats" in res.json()["detail"]


def test_reroll_endpoint_404s_for_missing_product(isolated_store):
    client = TestClient(app)
    res = client.post("/api/products/no-such-id/angles/pain_point/reroll-script", json={})
    assert res.status_code == 404


def test_reroll_endpoint_404s_for_missing_angle(isolated_store):
    product = ProductStore.add(name="Widget", url="https://x.test/w5")
    ProductStore.update(product["id"], angles=[{"angle_id": "pain_point", "status": "scripted"}])

    client = TestClient(app)
    res = client.post(f"/api/products/{product['id']}/angles/no_such_angle/reroll-script", json={})
    assert res.status_code == 404


def test_reroll_endpoint_creates_task_with_valid_payload(isolated_store):
    product = ProductStore.add(name="Widget", url="https://x.test/w6")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "pain_point", "angle_name": "Old", "status": "scripted",
    }])

    client = TestClient(app)
    res = client.post(
        f"/api/products/{product['id']}/angles/pain_point/reroll-script",
        json={"duration": "60s", "extra_beats": ["spec_detail"]},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["task_id"]
    assert data["task"]["type"] == "reroll_script"


def test_reroll_task_result_angle_has_lifecycle_fields_from_saved_product(isolated_store, monkeypatch):
    """Regression test: the completed task's result.angle must be the angle
    as actually PERSISTED (status/project_name/video_url intact), not the
    raw AI-generated angle object -- which never carries those fields at all
    (the AI is never told about them), so returning it directly made a
    successful reroll look like it had wiped the angle's production state.
    """
    product = ProductStore.add(name="Widget", url="https://x.test/reroll-lifecycle")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "pain_point",
        "angle_name": "Old name",
        "status": "rendered",
        "project_name": "widget_proj_1",
        "video_url": "04_Exports/widget.mp4",
    }])

    from scripts.product_scraper import ProductScraper
    monkeypatch.setattr(
        ProductScraper,
        "generate_content_matrix",
        lambda info, count=10, **kwargs: [{
            "angle_id": "pain_point",
            "angle_name": "New name",
            "hook_title": "New hook",
            "script_lines": ["new line 1", "new line 2"],
        }],
    )

    client = TestClient(app)
    res = client.post(
        f"/api/products/{product['id']}/angles/pain_point/reroll-script",
        json={"duration": "60s"},
    )
    assert res.status_code == 200, res.text
    task_id = res.json()["task_id"]

    # TestClient runs BackgroundTasks synchronously once the response has
    # been produced, so the task is already complete by the time we ask.
    task_res = client.get(f"/api/tasks/{task_id}")
    assert task_res.status_code == 200, task_res.text
    task = task_res.json()
    assert task["status"] == "completed", task.get("error")

    result_angle = task["result"]["angle"]
    # The model is allowed to rewrite the script, but not the topic identity.
    assert result_angle["angle_name"] == "Old name"
    assert result_angle["hook_title"] == "New hook"
    assert result_angle["angle_id"] == "pain_point"
    assert result_angle["content_types"] == ["problem_solution", "specs", "comparison"]
    assert result_angle["angle_description"] == "Problem / Agitation / Solution"
    # The whole point of this test: lifecycle fields must survive.
    assert result_angle["status"] == "rendered"
    assert result_angle["project_name"] == "widget_proj_1"
    assert result_angle["video_url"] == "04_Exports/widget.mp4"


def test_content_types_support_multiple_extra_beats_without_duplicates():
    assert content_types_for_angle(
        "niche_target", ["spec_detail", "comparison", "use_cases", "faq", "comparison"]
    ) == ["target_audience", "specs", "comparison", "use_cases", "faq"]


def test_fallback_reroll_uses_the_requested_angle_template(tmp_path, monkeypatch):
    import scripts.product_scraper as scraper

    monkeypatch.setattr(scraper, "BASE_DIR", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    angles = ProductScraper.generate_content_matrix(
        {"title": "Widget", "description": "D", "price_note": "P", "raw_text": "R"},
        count=1,
        angle_id_override="comparison",
        extra_beats=[],
    )

    assert len(angles) == 1
    assert angles[0]["angle_id"] == "comparison"
    assert angles[0]["angle_name"] == "🆚 เทียบของเดิม vs ของใหม่"
    assert angles[0]["content_types"] == ["comparison"]


def test_generate_content_matrix_duration_changes_beat_count_and_word_range():
    """No live Gemini call -- forcing the fallback path (no API key) still
    lets us assert on generate_content_matrix's own duration handling logic
    that runs before any network call, via the prompt-capturing seam."""
    import os
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["contents"] = contents
            raise RuntimeError("stop -- capturing prompt only")

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

        ProductScraper.generate_content_matrix(product_data, count=1, duration="30s")
        prompt_30 = captured["contents"]
        captured.clear()

        ProductScraper.generate_content_matrix(product_data, count=1, duration="90s")
        prompt_90 = captured["contents"]
    finally:
        genai.Client = orig_client
        if orig_key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = orig_key

    assert DURATION_SPECS["30s"]["word_range"] in prompt_30
    assert DURATION_SPECS["90s"]["word_range"] in prompt_90
    # 90s pulls in extra beats by default; 30s does not.
    assert EXTRA_BEAT_BLOCKS["spec_detail"]["label"] in prompt_90
    assert EXTRA_BEAT_BLOCKS["spec_detail"]["label"] not in prompt_30


def test_generate_content_matrix_angle_override_targets_one_angle():
    import os
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["contents"] = contents
            raise RuntimeError("stop -- capturing prompt only")

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
            product_data, count=10, duration="30s", angle_id_override="unboxing"
        )
        prompt = captured["contents"]
    finally:
        genai.Client = orig_client
        if orig_key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = orig_key

    assert '"angle_id": "unboxing"' in prompt
    assert "Object เดียวเท่านั้น" in prompt
    # The full 10-angle catalog listing must NOT appear when overriding.
    assert '"pain_point": 😫' not in prompt
