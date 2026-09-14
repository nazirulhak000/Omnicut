from __future__ import annotations

import json

import pytest

from scripts.background_isolation_compositor import (
    SEQUENCE_FRAME_PATTERN,
    CompositorValidationError,
    artifact_is_composable,
    build_alpha_composite_filter_fragment,
    build_compositing_plan,
    deserialize_compositor_config,
    map_source_time_to_frame_index,
    normalize_compositor_config,
    serialize_compositor_config,
    split_ass_layers_for_subject,
)


ARTIFACT_ID = "bgseq1-0123456789abcdef"
BASE_CONFIG = {
    "enabled": True,
    "mode": "cutout",
    "engine": "rembg",
    "model": "u2netp",
    "quality": "balanced",
    "fallback": "spotlight",
    "artifact": {"id": ARTIFACT_ID, "status": "ready"},
}
BASE_MANIFEST = {
    "schema_version": 1,
    "artifact_id": ARTIFACT_ID,
    "status": "ready",
    "source_fingerprint": "sha256:source-001",
    "algorithm": "background-isolation-v1",
    "engine": "rembg",
    "model": "u2netp",
    "quality": "balanced",
    "worker_version": "sequence-worker-v1",
    "frame_count": 4,
    "fps": 30,
    "timebase": "1/30",
    "width": 1080,
    "height": 1920,
    "rotation": 0,
    "frame_pattern": SEQUENCE_FRAME_PATTERN,
}


def test_ass_layers_put_hook_events_before_subject_and_keep_captions_foreground():
    lines = [
        "[Script Info]",
        "[Events]",
        "Dialogue: 0,0:00:00.00,0:00:03.00,HookHeader,,0,0,0,,Hook",
        "Dialogue: 1,0:00:00.00,0:00:03.00,TikTokSoftShadow,,0,0,0,,Caption",
    ]

    hook_lines, foreground_lines = split_ass_layers_for_subject(lines)

    assert hook_lines == [
        "[Script Info]",
        "[Events]",
        "Dialogue: 0,0:00:00.00,0:00:03.00,HookHeader,,0,0,0,,Hook",
    ]
    assert foreground_lines == [
        "[Script Info]",
        "[Events]",
        "Dialogue: 1,0:00:00.00,0:00:03.00,TikTokSoftShadow,,0,0,0,,Caption",
    ]


def ready_config(**changes):
    config = {**BASE_CONFIG}
    config["artifact"] = {**BASE_CONFIG["artifact"]}
    config.update(changes)
    return config


def manifest(**changes):
    return {**BASE_MANIFEST, **changes}


def test_default_and_disabled_configs_preserve_legacy_noop():
    missing = normalize_compositor_config(None)
    disabled = normalize_compositor_config({"enabled": False, "fallback": "original"})

    assert missing["enabled"] is False
    assert missing["fallback"] == "spotlight"
    assert disabled["fallback"] == "original"
    assert build_compositing_plan(None)["action"] == "fallback"
    assert build_compositing_plan(None)["stage_order"][-1] == "legacy_overlays"


def test_only_ready_matching_sequence_is_composable():
    active = normalize_compositor_config(BASE_CONFIG, BASE_MANIFEST)

    assert active["enabled"] is True
    assert active["ready"] is True
    assert active["sequence"]["artifact_id"] == ARTIFACT_ID
    assert artifact_is_composable(BASE_CONFIG, BASE_MANIFEST)


@pytest.mark.parametrize("status", ["missing", "stale", "error", "cancelled", "processing"])
def test_unavailable_artifact_uses_explicit_fallback(status):
    config = ready_config(fallback="original")
    config["artifact"] = {"id": ARTIFACT_ID, "status": status}

    normalized = normalize_compositor_config(config, manifest(status=status))
    plan = build_compositing_plan(config, manifest(status=status), 0)

    assert normalized["enabled"] is False
    assert normalized["fallback"] == "original"
    assert normalized["reason"] == f"artifact_{status}"
    assert plan["action"] == "fallback"
    assert plan["fallback"] == "original"


@pytest.mark.parametrize(
    "bad_manifest",
    [
        {"status": "ready"},
        {**BASE_MANIFEST, "frame_count": 0},
        {**BASE_MANIFEST, "fps": 0},
        {**BASE_MANIFEST, "timebase": "0/30"},
        {**BASE_MANIFEST, "width": -1},
        {**BASE_MANIFEST, "rotation": 45},
        {**BASE_MANIFEST, "frame_pattern": "../frame_%06d.png"},
        {**BASE_MANIFEST, "artifact_id": "bgseq1-bad"},
    ],
)
def test_invalid_sequence_metadata_fails_closed_to_fallback(bad_manifest):
    normalized = normalize_compositor_config(BASE_CONFIG, bad_manifest)
    plan = build_compositing_plan(BASE_CONFIG, bad_manifest, 0)

    assert normalized["enabled"] is False
    assert normalized["reason"] == "invalid_metadata"
    assert plan["action"] == "fallback"


def test_artifact_id_mismatch_cannot_composite():
    other = "bgseq1-fedcba9876543210"
    bad = {**BASE_CONFIG, "artifact": {"id": other, "status": "ready"}}
    normalized = normalize_compositor_config(bad, BASE_MANIFEST)

    assert normalized["enabled"] is False
    assert normalized["reason"] == "artifact_mismatch"


def test_ready_artifact_requires_matching_source_fingerprint():
    config = ready_config()
    config["artifact"]["source_fingerprint"] = "sha256:other-source"
    normalized = normalize_compositor_config(config, BASE_MANIFEST)

    assert normalized["enabled"] is False
    assert normalized["reason"] == "artifact_mismatch"


def test_sequence_manifest_requires_canonical_schema_and_identity_metadata():
    for key, value in (("schema_version", 99), ("worker_version", ""), ("source_fingerprint", "")):
        bad = {**BASE_MANIFEST, key: value}
        normalized = normalize_compositor_config(BASE_CONFIG, bad)
        assert normalized["enabled"] is False
        assert normalized["reason"] == "invalid_metadata"


@pytest.mark.parametrize(
    ("source_time", "expected"),
    [
        (-1, 0),
        (0, 0),
        (0.033333333, 0),
        (1 / 30, 1),
        (0.099999, 2),
        (0.1, 3),
        (10, 3),
    ],
)
def test_source_time_mapping_is_zero_based_floor_and_clamped(source_time, expected):
    assert (
        map_source_time_to_frame_index(
            source_time,
            fps=30,
            timebase="1/30",
            frame_count=4,
        )
        == expected
    )


def test_mapping_uses_timebase_and_supports_pts_ticks():
    assert map_source_time_to_frame_index(100, fps="25/1", timebase="1/1000", frame_count=10, source_time_unit="ticks") == 2
    assert map_source_time_to_frame_index(0.041, fps=25, timebase="1/1000", frame_count=10) == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fps": 0, "timebase": "1/30", "frame_count": 1},
        {"fps": 30, "timebase": "0/30", "frame_count": 1},
        {"fps": 30, "timebase": "1/30", "frame_count": 0},
        {"fps": 30, "timebase": "1/30", "frame_count": 1, "source_time_unit": "frames"},
    ],
)
def test_direct_mapping_rejects_invalid_metadata(kwargs):
    with pytest.raises(CompositorValidationError):
        map_source_time_to_frame_index(0, **kwargs)


def test_plan_exposes_frame_and_ordering_for_preview_render_parity():
    plan = build_compositing_plan(BASE_CONFIG, BASE_MANIFEST, 1 / 30)

    assert plan["enabled"] is True
    assert plan["frame_index"] == 1
    assert plan["frame_path"] == "frames/frame_000001.png"
    assert plan["stage_order"].index("alpha_composite") > plan["stage_order"].index("source_transform")
    assert plan["stage_order"].index("alpha_composite") < plan["stage_order"].index("transition")
    assert plan["stage_order"].index("alpha_composite") < plan["stage_order"].index("concat")
    assert plan["stage_order"].index("hook_overlays") < plan["stage_order"].index("subject_overlay")
    assert plan["stage_order"].index("subject_overlay") < plan["stage_order"].index("subtitle_callout_overlays")
    assert plan["alpha_applied_after"] == ["source_trim", "source_transform"]
    assert plan["alpha_applied_before"] == ["transition", "concat"]
    assert plan["operations"][0]["stage"] == "source_trim"
    assert plan["operations"][2]["stage"] == "alpha_composite"


def test_filter_fragment_has_alpha_merge_before_subject_overlay():
    fragment = build_alpha_composite_filter_fragment()

    assert fragment == (
        "[foreground_frame][alpha_frame]alphamerge[subject_rgba];"
        "[clip_transformed][subject_rgba]overlay=eof_action=pass:format=auto[clip_composited]"
    )
    assert fragment.index("alphamerge") < fragment.index("overlay")


def test_filter_labels_are_strictly_validated():
    with pytest.raises(CompositorValidationError):
        build_alpha_composite_filter_fragment(source_stream="movie=secret")


def test_contract_serialization_is_canonical_and_round_trips():
    payload = serialize_compositor_config(BASE_CONFIG, BASE_MANIFEST)
    decoded = deserialize_compositor_config(payload)

    assert payload == serialize_compositor_config(decoded)
    assert json.loads(payload)["sequence"]["fps_ratio"] == "30/1"
    assert decoded["enabled"] is True
    assert decoded["sequence"]["artifact_id"] == ARTIFACT_ID
    assert deserialize_compositor_config("not-json")["enabled"] is False


def test_module_is_pure_and_does_not_expose_execution_dependencies():
    import scripts.background_isolation_compositor as compositor

    assert not hasattr(compositor, "subprocess")
    assert not hasattr(compositor, "Path")
    assert not hasattr(compositor, "rembg")
