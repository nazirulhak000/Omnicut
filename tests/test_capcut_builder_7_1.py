"""Unit tests for CapCut Desktop 7.1 Draft Bridge compatibility (E14, §3.5)."""

import pytest
from scripts.capcut_builder import upgrade_draft_content_to_7_1, CAPCUT_7_1_MATERIAL_KEYS


def test_upgrade_draft_content_to_7_1_schema():
    draft = {
        "version": 300000,
        "tracks": [
            {
                "type": "video",
                "segments": [
                    {
                        "id": "vid-seg-001",
                        "target_timerange": {"start": 0, "duration": 5000000}
                    }
                ]
            },
            {
                "type": "text",
                "segments": [
                    {
                        "id": "txt-seg-001",
                        "target_timerange": {"start": 500000, "duration": 1500000}
                    },
                    {
                        "id": "txt-seg-002",
                        "target_timerange": {"start": 6000000, "duration": 1000000}  # Non-overlapping
                    }
                ]
            },
            {
                "type": "sticker",
                "segments": [
                    {
                        "id": "stk-seg-001",
                        "target_timerange": {"start": 2000000, "duration": 1000000}
                    }
                ]
            }
        ],
        "materials": {}
    }

    res = upgrade_draft_content_to_7_1(draft)

    # 1. Versioning
    assert res["version"] == 360000
    assert res["new_version"] == "144.0.0"

    # 2. Platform
    assert res["platform"]["app_id"] == 359289
    assert res["platform"]["app_source"] == "cc"
    assert res["platform"]["app_version"] == "7.1.0"
    assert res["platform"]["os"] == "windows"

    # 3. Canvas Config 9:16
    assert res["canvas_config"]["width"] == 1080
    assert res["canvas_config"]["height"] == 1920
    assert res["canvas_config"]["ratio"] == "9:16"

    # 4. Mode flags
    assert res["free_render_index_mode_on"] is True
    assert res["render_index_track_mode_on"] is True
    assert isinstance(res["keyframe_graph_list"], list)

    # 5. Track Linkage Relationships
    relationships = res["relationships"]
    assert len(relationships) == 2
    # txt-seg-001 (0.5s - 2.0s) overlaps vid-seg-001 (0s - 5s)
    # stk-seg-001 (2.0s - 3.0s) overlaps vid-seg-001 (0s - 5s)
    linked_targets = {r["target_id"] for r in relationships}
    assert "txt-seg-001" in linked_targets
    assert "stk-seg-001" in linked_targets
    assert "txt-seg-002" not in linked_targets

    # 6. Materials completeness
    for k in CAPCUT_7_1_MATERIAL_KEYS:
        assert k in res["materials"]
        assert isinstance(res["materials"][k], list)
