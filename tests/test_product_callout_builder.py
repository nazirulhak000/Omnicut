from copy import deepcopy
import re

from scripts.product_callout_builder import build_product_callouts


def _cues(with_on_screen=False):
    cues = [
        {"id": "beat-1", "start": 0.1254, "end": 1.8766, "text": "เปิดกล่อง"},
        {"id": "beat-2", "start": 1.8766, "end": 4.2019, "text": "จุดเด่น"},
    ]
    if with_on_screen:
        cues[1]["on_screen"] = "20W PD"
    return cues


def test_builds_brand_and_model_with_existing_overlay_shape_and_english_names():
    overlays = build_product_callouts(
        _cues(),
        {"brand": "Anker", "model": "Soundcore Boom Go 3i"},
    )

    assert [item["callout_type"] for item in overlays] == ["brand", "model"]
    assert [item["tiers"][0]["text"] for item in overlays] == ["Anker", "Soundcore Boom Go 3i"]
    assert all(item["kind"] == "text" for item in overlays)
    assert all(item["role"] == "product_callout" for item in overlays)
    assert all(item["origin"] == "auto" for item in overlays)


def test_empty_inputs_return_empty_without_requiring_timing():
    assert build_product_callouts() == []
    assert build_product_callouts([], {"brand": "Anker"}) == []
    assert build_product_callouts(_cues(), {}) == []


def test_on_screen_candidate_uses_beat_timing_and_classifies_spec():
    overlays = build_product_callouts(_cues(with_on_screen=True), {})

    assert len(overlays) == 1
    assert overlays[0]["callout_type"] == "spec"
    assert overlays[0]["tiers"][0]["text"] == "20W PD"
    assert overlays[0]["start"] == 1.877
    assert overlays[0]["end"] == 4.202
    assert overlays[0]["source"]["beat_id"] == "beat-2"


def test_duplicate_auto_candidates_are_emitted_once():
    overlays = build_product_callouts(
        _cues(),
        {
            "features": ["กันน้ำ IPX7", "กันน้ำ  IPX7"],
            "callouts": [{"callout_type": "feature", "text": "กันน้ำ IPX7"}],
        },
    )

    assert len(overlays) == 1
    assert overlays[0]["tiers"][0]["text"] == "กันน้ำ IPX7"


def test_manual_overlay_wins_over_auto_and_preserves_manual_fields():
    manual = {
        "id": "manual-model-1",
        "kind": "text",
        "role": "product_callout",
        "callout_type": "model",
        "origin": "manual",
        "start": 2.25,
        "end": 3.75,
        "tiers": [{"text": "Soundcore Boom Go 3i", "look": {"color": "#00FF99"}}],
        "look": {"font": "Kanit"},
    }
    overlays = build_product_callouts(
        _cues(),
        {"model": "Soundcore Boom Go 3i"},
        [manual],
    )

    assert len(overlays) == 1
    assert overlays[0]["id"] == "manual-model-1"
    assert overlays[0]["origin"] == "manual"
    assert overlays[0]["start"] == 2.25
    assert overlays[0]["look"] == {"font": "Kanit"}


def test_manual_overlay_with_generated_id_can_replace_edited_auto_text():
    automatic = build_product_callouts(_cues(), {"model": "Soundcore Boom Go 3i"})[0]
    manual = {
        "id": automatic["id"],
        "role": "product_callout",
        "callout_type": "model",
        "start": 0.5,
        "end": 2.0,
        "text": "Soundcore Boom Go 3i Pro",
    }

    overlays = build_product_callouts(
        _cues(),
        {"model": "Soundcore Boom Go 3i"},
        [manual],
    )

    assert len(overlays) == 1
    assert overlays[0]["id"] == automatic["id"]
    assert overlays[0]["tiers"][0]["text"] == "Soundcore Boom Go 3i Pro"


def test_generated_id_and_output_are_deterministic():
    cues = _cues()
    metadata = {"brand": "Anker", "model": "Soundcore Boom Go 3i", "features": ["Bluetooth 5.3"]}

    first = build_product_callouts(cues, metadata)
    second = build_product_callouts(deepcopy(cues), deepcopy(metadata))

    assert first == second
    assert all(re.fullmatch(r"callout-(brand|model|feature)-[0-9a-f]{12}", item["id"]) for item in first)


def test_builder_does_not_mutate_cues_metadata_or_manual_overlay():
    cues = _cues()
    metadata = {"brand": "Anker", "features": [{"text": "กันน้ำ", "beat_id": "beat-2"}]}
    manual = [{"role": "product_callout", "callout_type": "brand", "text": "Anker", "start": 0, "end": 1}]
    before = deepcopy((cues, metadata, manual))

    build_product_callouts(cues, metadata, manual)

    assert (cues, metadata, manual) == before


def test_manual_without_id_gets_stable_id_and_non_callout_overlay_is_ignored():
    overlays = build_product_callouts(
        _cues(),
        {"brand": "Anker"},
        [
            {"kind": "text", "role": "caption", "text": "ไม่ใช่ callout", "start": 0, "end": 1},
            {"role": "product_callout", "callout_type": "proof", "text": "ทดสอบกันน้ำ IPX5", "start": 1, "end": 2},
            # "price" is no longer a callout type (TikTok no-price rule).
            {"role": "product_callout", "callout_type": "price", "text": "฿1,990", "start": 1, "end": 2},
        ],
    )

    assert [item["callout_type"] for item in overlays] == ["brand", "proof"]
    assert overlays[1]["id"].startswith("callout-proof-")


def test_builder_keeps_text_raw_for_render_boundary_escaping():
    text = r"C:\Product\{20W}"
    overlays = build_product_callouts(_cues(), {"features": [text]})

    assert overlays[0]["tiers"][0]["text"] == text
