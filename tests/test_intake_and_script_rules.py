"""
Offline deterministic tests for Phase 3:
- `scripts/script_rules.py`
- `scripts/couple_script_generator.py`
- `scripts/api_intake.py`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import scripts.product_store as product_store
from scripts.api_intake import router as intake_router
from scripts.couple_script_generator import (
    COUPLE_CATEGORIES,
    enforce_speaker_persona,
    generate_couple_20_scripts,
    generate_single_couple_angle,
)
from scripts.script_rules import (
    RULE_NO_ELLIPSIS,
    RULE_NO_EMOJI,
    RULE_NO_PRICE,
    RULE_NO_THAI_TECH_TRANSLITERATION,
    RULE_TURN_STRUCTURE,
    lint_couple_script,
)


@pytest.fixture()
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ProductStore SQLite & JSON mirror to tmp_path."""
    fake_store_json = tmp_path / "_Docs" / "products.json"
    fake_store_json.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(product_store, "STORE_PATH", fake_store_json)
    return fake_store_json


@pytest.fixture()
def client(isolated_store: Path) -> TestClient:
    app = FastAPI()
    app.include_router(intake_router)
    return TestClient(app)


def _valid_8_turns() -> List[Dict[str, Any]]:
    return [
        {"speaker": "nui", "display": "พี่บ่าว สายชาร์จพันกันยุ่งเลย!", "spoken": "พี่บ่าว สายชาร์จในกระเป๋าน้องพันกันยุ่งไปหมดเลย!"},
        {"speaker": "bao", "display": "ใจเย็นครับน้องนุ้ย เอาตัวนี้ไป!", "spoken": "ใจเย็นๆ ครับน้องนุ้ยคนสวย เอาตัวนี้ไปใช้เลย!"},
        {"speaker": "nui", "display": "ตัวไหนเนี่ย มีสายในตัวด้วยเหรอ!", "spoken": "ตัวไหนเนี่ยพี่บ่าว มีสายติดมาในตัวด้วยเหรอ!"},
        {"speaker": "bao", "display": "ใช่แล้ว มีสาย Type-C และ Fast Charge!", "spoken": "ใช่แล้วครับ มีสาย Type-C ในตัวรองรับ Fast Charge ด้วย!"},
        {"speaker": "nui", "display": "ดีจัง ไม่ต้องพกสายแยกให้รุงรัง!", "spoken": "ดีจังเลย ไม่ต้องพกสายแยกให้รุงรังกระเป๋าอีกแล้ว!"},
        {"speaker": "bao", "display": "มีหน้าจอบอกเปอร์เซ็นต์แบตชัดเจน!", "spoken": "แถมมีหน้าจอดิจิทัลบอกเปอร์เซ็นต์แบตชัดเจนเลยครับ!"},
        {"speaker": "nui", "display": "งั้นน้องยึดอันนี้เลยนะพี่บ่าว!", "spoken": "งั้นน้องนุ้ยขอยึดอันนี้ไว้ใช้เองเลยนะพี่บ่าว!"},
        {"speaker": "bao", "display": "จัดไปครับ กดที่ตะกร้าเหลืองได้เลย!", "spoken": "จัดไปเลยครับ ใครอยากได้กดที่ตะกร้าเหลืองด้านล่างได้เลย!"},
    ]


# ---------------------------------------------------------------------------
# 1. Shared Script Rules Lint Tests
# ---------------------------------------------------------------------------

def test_lint_valid_couple_script_passes() -> None:
    res = lint_couple_script({"turns": _valid_8_turns()})
    assert res["valid"] is True
    assert res["violations"] == []


def test_lint_no_ellipsis_rule() -> None:
    turns = _valid_8_turns()
    turns[0]["display"] = "พี่บ่าว... สายชาร์จพันกัน"
    turns[2]["spoken"] = "มีสายติดมาด้วยเหรอ…"

    res = lint_couple_script({"turns": turns})
    assert res["valid"] is False
    ellipsis_violations = [v for v in res["violations"] if v["code"] == RULE_NO_ELLIPSIS]
    assert len(ellipsis_violations) == 2
    assert ellipsis_violations[0]["turn_index"] == 0
    assert ellipsis_violations[0]["field"] == "display"
    assert ellipsis_violations[1]["turn_index"] == 2
    assert ellipsis_violations[1]["field"] == "spoken"


@pytest.mark.parametrize(
    "bad_price_text",
    [
        "ตัวนี้แค่ 149 บาทเอง",
        "จ่ายเพียง ฿290 เท่านั้น",
        "ราคาคุ้มสุดๆ",
        "จัดโปรโมชั่นวันสุดท้าย",
        "ลดเหลือไม่กี่ร้อย",
        "เก็บคูปองส่วนลดได้เลย",
        "ของดีถูกมากพี่บ่าว",
        "จ่ายแค่ 99 บ. เท่านั้น",
    ],
)
def test_lint_no_price_rule(bad_price_text: str) -> None:
    turns = _valid_8_turns()
    turns[1]["display"] = bad_price_text
    res = lint_couple_script({"turns": turns})
    assert res["valid"] is False
    assert any(
        v["code"] == RULE_NO_PRICE and v["turn_index"] == 1 and v["field"] == "display"
        for v in res["violations"]
    )


def test_lint_no_emoji_rule() -> None:
    turns = _valid_8_turns()
    turns[3]["display"] = "ชาร์จไวสุดๆ 🔥😍"
    res = lint_couple_script({"turns": turns})
    assert res["valid"] is False
    assert any(v["code"] == RULE_NO_EMOJI and v["turn_index"] == 3 for v in res["violations"])


@pytest.mark.parametrize(
    "bad_tech_thai",
    [
        "เชื่อมต่อบลูทูธไวมาก",
        "มีสายไทป์ซีในตัว",
        "รองรับฟาสต์ชาร์จเต็มสปีด",
        "ชาร์จไวร์เลสได้เลย",
        "ช่องเสียบยูเอสบีคู่",
        "ระบบชาร์จพีดี",
    ],
)
def test_lint_no_thai_tech_transliteration_rule(bad_tech_thai: str) -> None:
    turns = _valid_8_turns()
    turns[4]["spoken"] = bad_tech_thai
    res = lint_couple_script({"turns": turns})
    assert res["valid"] is False
    assert any(
        v["code"] == RULE_NO_THAI_TECH_TRANSLITERATION and v["turn_index"] == 4
        for v in res["violations"]
    )


def test_lint_turn_structure_rule() -> None:
    # Fewer than 8 turns
    short_res = lint_couple_script({"turns": _valid_8_turns()[:4]})
    assert short_res["valid"] is False
    assert any(v["code"] == RULE_TURN_STRUCTURE and v["field"] == "turns" for v in short_res["violations"])

    # Invalid speaker and empty spoken
    bad_turns = _valid_8_turns()
    bad_turns[0]["speaker"] = "unknown_person"
    bad_turns[1]["spoken"] = "   "
    bad_res = lint_couple_script({"turns": bad_turns})
    assert bad_res["valid"] is False
    assert any(v["code"] == RULE_TURN_STRUCTURE and v["field"] == "speaker" for v in bad_res["violations"])
    assert any(v["code"] == RULE_TURN_STRUCTURE and v["field"] == "spoken" for v in bad_res["violations"])


# ---------------------------------------------------------------------------
# 2. Couple 20-Script Generator & Persona Self-Repair Tests
# ---------------------------------------------------------------------------

def test_generate_couple_20_scripts_offline_and_categories() -> None:
    product = {
        "name": "พาวเวอร์แบงค์ TTZ K106",
        "product_code": "TTZ01",
        "specs": [
            {"label": "สายในตัว", "value": "มีสาย Type-C ในตัว 2 เส้น"},
            {"label": "ระบบชาร์จ", "value": "รองรับ Fast Charge และ PD"},
        ],
        "images": [
            {"url": "03_Projects/assets/hero_1.webp", "starred": True},
        ],
    }
    angles = generate_couple_20_scripts(product)
    assert len(angles) == 20

    # Check 5 categories x 4 angles each
    cat_counts: Dict[str, int] = {}
    for ang in angles:
        ckey = ang["category_key"]
        cat_counts[ckey] = cat_counts.get(ckey, 0) + 1
        lint_res = lint_couple_script(ang)
        assert lint_res["valid"] is True, f"Angle {ang['id']} failed lint: {lint_res['violations']}"
        assert ang["script_review"]["state"] == "pending"
        assert ang["revision"] == 1

        # Verify Nui never uses male particles
        for turn in ang["turns"]:
            if turn["speaker"] == "nui":
                assert "ครับ" not in turn["display"]
                assert "ครับ" not in turn["spoken"]
                assert "พี่บ่าวพูดเอง" not in turn["spoken"]

    assert len(cat_counts) == len(COUPLE_CATEGORIES) == 5
    for count in cat_counts.values():
        assert count == 4


def test_generator_self_repairs_dirty_llm_output() -> None:
    def dirty_llm_fn(_prod: Dict[str, Any], _idx: int, _reason: str) -> List[Dict[str, Any]]:
        return [
            {
                "speaker": "nui",
                "display": "พี่บ่าว... ตัวนี้ 149 บาท เชื่อมบลูทูธได้ครับ 🔥",
                "spoken": "พี่บ่าวพูดเอง... ตัวนี้ราคา 149 บาท มีสายไทป์ซีนะครับ 😍",
            },
            {
                "speaker": "bao",
                "display": "ใช่แล้ว… โปรโมชั่นลดเหลือ 99 บ. ฟาสต์ชาร์จ!",
                "spoken": "ใช่แล้วครับ โปรโมชั่นลดเหลือ 99 บาท รองรับฟาสต์ชาร์จครับ!",
            },
        ]

    product = {"name": "หูฟัง Bluetooth X1", "product_code": "BTX01"}
    angle = generate_single_couple_angle(product, 0, llm_fn=dirty_llm_fn)
    lint_res = lint_couple_script(angle)
    assert lint_res["valid"] is True, f"Self-repair failed: {lint_res['violations']}"
    assert len(angle["turns"]) >= 8

    nui_turn = angle["turns"][0]
    assert nui_turn["speaker"] == "nui"
    assert "ครับ" not in nui_turn["display"]
    assert "ครับ" not in nui_turn["spoken"]
    assert "พี่บ่าวพูดเอง" not in nui_turn["spoken"]
    assert "Bluetooth" in nui_turn["display"]
    assert "Type-C" in nui_turn["spoken"]


def test_enforce_speaker_persona_never_puts_male_particles_on_nui() -> None:
    cleaned = enforce_speaker_persona("ดีมากเลยนะครับ พี่บ่าวพูดเอง", "nui")
    assert "ครับ" not in cleaned
    assert "พี่บ่าวพูดเอง" not in cleaned
    assert "นะพี่บ่าว" in cleaned


# ---------------------------------------------------------------------------
# 3. Mobile Intake & Script Review API Tests
# ---------------------------------------------------------------------------

def test_api_intake_parse_and_duplicate_check(client: TestClient) -> None:
    messy_text = "ดูสินค้านี้บน TikTok https://vt.tiktok.com/ZS9yka/item/1729384756102938475?utm_source=copy กดเลย!"
    res = client.post("/api/intake/parse", json={"text": messy_text})
    assert res.status_code == 200
    data = res.json()
    assert data["url"] == "https://vt.tiktok.com/ZS9yka/item/1729384756102938475?utm_source=copy"
    assert data["tiktok_product_id"] == "1729384756102938475"
    assert data["duplicate"] is False

    # Commit product, then parse again -> should detect duplicate
    commit_res = client.post(
        "/api/intake/commit",
        json={
            "url": data["url"],
            "name": "พัดลมพกพา Turbo Fan",
            "tiktok_product_id": data["tiktok_product_id"],
            "specs": ["ลมแรงปรับได้ 100 ระดับ", "ชาร์จผ่านพอร์ต Type-C"],
            "photos": [{"url": "https://example.com/fan1.jpg", "starred": True}],
        },
    )
    assert commit_res.status_code == 200
    assert commit_res.json()["merged"] is False

    res2 = client.post("/api/intake/parse", json={"text": messy_text})
    assert res2.status_code == 200
    assert res2.json()["duplicate"] is True
    assert res2.json()["existing_product"]["tiktok_product_id"] == "1729384756102938475"


def test_api_intake_preview_returns_needs_manual_on_waf(client: TestClient) -> None:
    res = client.post(
        "/api/intake/preview",
        json={
            "url": "https://vt.tiktok.com/ZS9yka/",
            "simulate_waf": True,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["needs_manual"] is True
    assert "Security Check" in body["warning"]


def test_api_scripts_workflow_generate_review_patch_and_409_conflict(client: TestClient) -> None:
    # 1. Commit a product
    commit_res = client.post(
        "/api/intake/commit",
        json={
            "url": "https://vt.tiktok.com/ZS9test123/",
            "name": "แท่นชาร์จไร้สาย MagSafe Stand",
            "code": "MAG01",
            "tiktok_product_id": "172999888777666555",
            "specs": ["ชาร์จ Wireless ไวมาก", "พับเก็บพกใส่กระเป๋าสะดวก"],
            "photos": [
                {"url": "https://example.com/mag1.webp", "starred": True},
                {"url": "https://example.com/mag2.webp", "starred": False},
            ],
        },
    )
    assert commit_res.status_code == 200
    product = commit_res.json()["product"]
    pid = product["id"]

    # 2. Generate 20 couple scripts
    gen_res = client.post("/api/scripts/generate-couple-20", json={"product_id": pid})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["total"] == 20
    assert gen_data["valid_count"] == 20
    angles = gen_data["angles"]
    first_angle_id = angles[0]["angle_id"]

    # 3. Approve first angle
    rev_res = client.post(
        f"/api/scripts/{pid}/angles/review",
        json={"angle_id": first_angle_id, "state": "approved"},
    )
    assert rev_res.status_code == 200
    assert first_angle_id in rev_res.json()["updated_angle_ids"]

    # 4. Re-committing or re-generating without force must preserve the approved angle
    regen_res = client.post("/api/scripts/generate-couple-20", json={"product_id": pid, "force": False})
    assert regen_res.status_code == 200
    preserved_first = regen_res.json()["angles"][0]
    assert preserved_first["script_review"]["state"] == "approved"

    # 5. Patch angle #2 with valid base_revision
    second_angle = regen_res.json()["angles"][1]
    second_id = second_angle["angle_id"]
    base_rev = second_angle["revision"]

    edited_turns = _valid_8_turns()
    edited_turns[0]["display"] = "พี่บ่าว แท่นชาร์จอันนี้พับเก็บง่ายไหม!"

    patch_ok = client.patch(
        f"/api/scripts/{pid}/angles/{second_id}",
        json={"turns": edited_turns, "base_revision": base_rev},
    )
    assert patch_ok.status_code == 200
    assert patch_ok.json()["revision"] == base_rev + 1
    assert patch_ok.json()["lint"]["valid"] is True

    # 6. Patch angle #2 with stale base_revision -> HTTP 409 Conflict
    patch_conflict = client.patch(
        f"/api/scripts/{pid}/angles/{second_id}",
        json={"turns": edited_turns, "base_revision": base_rev},
    )
    assert patch_conflict.status_code == 409

    # 7. Batch approve all valid scripts
    batch_rev = client.post(
        f"/api/scripts/{pid}/angles/review",
        json={"approve_all_valid": True, "state": "approved"},
    )
    assert batch_rev.status_code == 200
    assert len(batch_rev.json()["updated_angle_ids"]) == 20

    # 8. Test /api/scripts/lint endpoint directly
    lint_endpoint_res = client.post(
        "/api/scripts/lint",
        json={"turns": edited_turns},
    )
    assert lint_endpoint_res.status_code == 200
    assert lint_endpoint_res.json()["valid"] is True
