"""
Unit tests for Custom Hook Templates: persistence, CRUD API, and style resolution parity.
"""
import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from scripts.api_server import app
from scripts.hook_styles import (
    HOOK_TEMPLATES,
    DEFAULT_HOOK_TEMPLATE,
    load_custom_hook_templates,
    get_all_hook_templates,
    save_custom_hook_template,
    delete_custom_hook_template,
    resolve_hook_style,
    CUSTOM_HOOK_TEMPLATES_FILE,
)


@pytest.fixture
def clean_custom_templates(tmp_path, monkeypatch):
    """Isolates custom templates file to a temporary path for deterministic testing."""
    test_file = tmp_path / "custom_hook_templates.json"
    monkeypatch.setattr("scripts.hook_styles.CUSTOM_HOOK_TEMPLATES_FILE", test_file)
    return test_file


def test_custom_hook_templates_crud_and_resolve(clean_custom_templates):
    # 1. Initial state is empty
    assert load_custom_hook_templates() == {}
    all_tpls = get_all_hook_templates()
    assert len(all_tpls) == len(HOOK_TEMPLATES)

    # 2. Save a new custom template
    sample_data = {
        "name": "เทมเพลตสีนีออนของฉัน",
        "font": "Kanit",
        "tiers": {
            "brand": {"size_pct": 140, "color": "#00FFCC", "outline_color": "#000000", "outline_px": 8.0, "upper": True},
            "model": {"size_pct": 115, "color": "#FF00FF", "outline_color": "#FFFFFF", "outline_px": 6.0},
            "label": {"size_pct": 70, "color": "#FFFF00", "pill": "#FF0055"},
        },
        "motion": {"in": "pop", "loop": "pulse", "out": "zoom", "accent": "badge"},
    }

    saved = save_custom_hook_template("my_neon_special", sample_data)
    assert saved["id"] == "custom_my_neon_special"
    assert saved["label_th"] == "เทมเพลตสีนีออนของฉัน"
    assert saved["font"] == "Kanit"
    assert saved["tiers"]["brand"]["color"] == "#00FFCC"
    assert saved["tiers"]["model"]["outline_px"] == 6.0

    # 3. Verify persistence
    loaded = load_custom_hook_templates()
    assert "custom_my_neon_special" in loaded
    assert get_all_hook_templates()["custom_my_neon_special"]["font"] == "Kanit"

    # 4. Resolve hook style with custom template
    resolved = resolve_hook_style("custom_my_neon_special")
    assert resolved["template"] == "custom_my_neon_special"
    assert resolved["font"] == "Kanit"
    assert resolved["tiers"]["brand"]["color"] == "#00FFCC"
    assert resolved["tiers"]["brand"]["size_pct"] == 140
    assert resolved["tiers"]["model"]["color"] == "#FF00FF"

    # 5. Overrides still work on top of custom template
    resolved_over = resolve_hook_style("custom_my_neon_special", overrides={"font": "Prompt"})
    assert resolved_over["font"] == "Prompt"
    assert resolved_over["tiers"]["brand"]["color"] == "#00FFCC"

    # 6. Cannot delete built-in template
    assert delete_custom_hook_template("tech") is False

    # 7. Delete custom template
    assert delete_custom_hook_template("custom_my_neon_special") is True
    assert "custom_my_neon_special" not in load_custom_hook_templates()


def test_api_hook_templates_endpoints(clean_custom_templates):
    client = TestClient(app)

    # GET /api/editor/hook-templates
    res = client.get("/api/editor/hook-templates")
    assert res.status_code == 200
    body = res.json()
    assert "builtin" in body
    assert "tech" in body["builtin"]
    assert "custom" in body

    # POST /api/editor/hook-templates
    post_data = {
        "id": "vip_gold",
        "label_th": "โกลด์ลักชัวรี VIP",
        "font": "Prompt",
        "tiers": {
            "brand": {"color": "#FFD700", "outline_color": "#111111", "outline_px": 5.0},
        },
        "motion": {"in": "slide_up", "loop": "lightsweep"},
    }
    res_post = client.post("/api/editor/hook-templates", json=post_data)
    assert res_post.status_code == 200
    saved = res_post.json()["template"]
    assert saved["id"] == "custom_vip_gold"
    assert saved["label_th"] == "โกลด์ลักชัวรี VIP"

    # Verify present in list
    res_list = client.get("/api/editor/hook-templates")
    assert "custom_vip_gold" in res_list.json()["custom"]

    # DELETE /api/editor/hook-templates/tech (Built-in protected)
    res_del_bad = client.delete("/api/editor/hook-templates/tech")
    assert res_del_bad.status_code == 400

    # DELETE /api/editor/hook-templates/custom_vip_gold
    res_del_ok = client.delete("/api/editor/hook-templates/custom_vip_gold")
    assert res_del_ok.status_code == 200

    # Verify deleted
    res_list2 = client.get("/api/editor/hook-templates")
    assert "custom_vip_gold" not in res_list2.json()["custom"]
