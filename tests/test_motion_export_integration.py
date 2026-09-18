"""Regression coverage for the opt-in motion-contract export seam."""

from copy import deepcopy

from scripts.subtitle.overlay_events import overlay_events


def _text_overlay(**extra):
    value = {
        "id": "text-contract-test",
        "kind": "text",
        "start": 0,
        "end": 2,
        "text": "Export motion",
        "look": {"font": "Kanit", "size_pct": 100},
        "anim": {"in": "snap", "loop": "none", "out": "fade"},
    }
    value.update(extra)
    return value


def _ctx():
    return {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 50,
        "resolved_font": "Kanit",
        "font_map": {},
        "style_preset": "premium_minimal",
    }


def test_unknown_contract_id_keeps_byte_identical_legacy_output():
    legacy = _text_overlay()
    migrated_but_unknown = _text_overlay(anim={
        "in": "snap",
        "loop": "none",
        "out": "fade",
        "contract_id": "text.in.not_yet_migrated",
    })

    assert overlay_events(legacy, _ctx()) == overlay_events(migrated_but_unknown, _ctx())


def test_text_contract_id_controls_export_timing_and_scale():
    overlay = _text_overlay(
        motion_contracts={
            "in": {
                "version": 1,
                "id": "text.test.in",
                "role": "text",
                "phase": "in",
                "duration_ms": 40,
                "tracks": {
                    "scale": {
                        "unit": "ratio",
                        "keyframes": [
                            {"t": 0, "value": 0.8},
                            {"t": 1, "value": 1},
                        ],
                    }
                },
            }
        }
    )

    events = overlay_events(deepcopy(overlay), _ctx())
    main = [event for event in events if "TextOverlayMain" in event]
    assert main
    assert any(r"\fscx80\fscy80\t(0,40,\fscx100\fscy100)" in event for event in main)


def test_hook_contract_id_uses_adapter_and_preserves_phase_boundaries():
    overlay = {
        "id": "hook-contract-test",
        "kind": "hook",
        "start": 0,
        "end": 2,
        "tiers": [
            {"text": "Brand", "look": {"size_pct": 100}},
            {"text": "Model", "look": {"size_pct": 100}},
            {"text": "Label", "look": {"size_pct": 100}},
        ],
        "anim": {"in": "bounce", "loop": "none", "out": "fade"},
        "motion_contracts": {
            "in": {
                "version": 1,
                "id": "hook.test.in",
                "role": "hook",
                "phase": "in",
                "duration_ms": 40,
                "tracks": {
                    "scale": {
                        "unit": "ratio",
                        "keyframes": [
                            {"t": 0, "value": 0.5},
                            {"t": 1, "value": 1},
                        ],
                    }
                },
            },
            "out": {
                "version": 1,
                "id": "hook.test.out",
                "role": "hook",
                "phase": "out",
                "duration_ms": 60,
                "tracks": {
                    "alpha": {
                        "unit": "opacity",
                        "keyframes": [
                            {"t": 0, "value": 1},
                            {"t": 1, "value": 0},
                        ],
                    }
                },
            },
        },
    }

    events = overlay_events(overlay, {"video_width": 1080, "video_height": 1920, "hook_fs": 75, "hook_font": "Kanit"})
    main = [event for event in events if event.startswith("Dialogue: 2,")]
    assert main
    assert any(r"\fscx50\fscy50\t(0,40,\fscx100\fscy100)" in event for event in main)
    assert any(r"\t(1940,2000,\alpha&HFF&)" in event for event in main)


def test_unsupported_contract_track_reports_without_breaking_export():
    overlay = _text_overlay(
        motion_contracts={
            "in": {
                "version": 1,
                "id": "text.test.reveal",
                "role": "text",
                "phase": "in",
                "duration_ms": 40,
                "tracks": {
                    "reveal": {
                        "unit": "ratio",
                        "keyframes": [{"t": 0, "value": 0}, {"t": 1, "value": 1}],
                    }
                },
            }
        }
    )

    events = overlay_events(overlay, _ctx())
    assert any("TextOverlayMain" in event for event in events)
