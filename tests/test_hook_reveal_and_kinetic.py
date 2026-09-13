"""
Tests for Hook Banner Kinetic Motion Extensions & Cumulative Reveal Mode:
1. slam entrance keyframes & duration
2. elastic_bounce entrance keyframes & duration
3. cumulative reveal mode step delays & pre-t0 opacity tags
4. simultaneous reveal mode
5. Preview = Render parity constants
"""
import re
from pathlib import Path
import pytest

from scripts.hook_motion_presets import (
    HOOK_IN_PRESETS,
    HOOK_REVEAL_PRESETS,
    hook_motion_catalog,
)
from scripts.subtitle.motion_effects import (
    _in_slam,
    _in_elastic_bounce,
    DEFAULT_HOOK_MOTION,
    DEFAULT_HOOK_STEP_DELAY_MS,
)
from scripts.subtitle.overlay_events import overlay_events


ROOT = Path(__file__).resolve().parent.parent


def test_slam_and_elastic_bounce_presets_registered():
    catalog = hook_motion_catalog()
    assert "slam" in catalog["in"]
    assert "elastic_bounce" in catalog["in"]
    assert catalog["in"]["slam"]["label_th"] == "กระแทกจอ"
    assert catalog["in"]["elastic_bounce"]["label_th"] == "เด้งดึ๋ง"


def test_reveal_presets_registered():
    catalog = hook_motion_catalog()
    assert "reveal" in catalog
    assert "simultaneous" in catalog["reveal"]
    assert "cumulative" in catalog["reveal"]
    assert "tier_step" in catalog["reveal"]
    assert catalog["reveal"]["cumulative"]["label_th"] == "สะสมทีละบรรทัด"


def test_slam_keyframes_and_timing():
    tag, end_ms, loop_start = _in_slam(100.0, 0)
    assert end_ms == 180
    assert loop_start is None
    # Entry from 220% to 100%
    assert r"\fscx220\fscy220" in tag
    assert r"\alpha&HFF&" in tag
    assert r"\t(0,50,\alpha&H00&)" in tag
    assert r"\t(0,180,2.2,\fscx100\fscy100)" in tag


def test_elastic_bounce_keyframes_and_timing():
    tag, end_ms, loop_start = _in_elastic_bounce(100.0, 0)
    assert end_ms == 520
    assert loop_start is None
    assert r"\fscx40\fscy40" in tag
    assert r"\t(0,40,\alpha&H00&)" in tag
    assert r"\fscx128\fscy128" in tag
    assert r"\fscx88\fscy88" in tag
    assert r"\fscx108\fscy108" in tag
    assert r"\fscx98\fscy98" in tag
    assert r"\fscx100\fscy100" in tag


def test_cumulative_reveal_emits_delayed_tiers_and_pre_t0_alpha():
    overlay = {
        "id": "hook_test",
        "type": "hook",
        "start": 0.0,
        "end": 3.0,
        "anchor": "top",
        "tiers": [
            {"text": "LOGITECH", "look": {"size_pct": 130, "color": "#FFFFFF", "outline_px": 6}},
            {"text": "WAVE KEYS", "look": {"size_pct": 100, "color": "#FFE600", "outline_px": 6}},
            {"text": "KEYBOARD", "look": {"size_pct": 60, "color": "#FFFFFF", "outline_px": 0, "pill": "#FE2C55"}},
        ],
        "anim": {
            "in": "slam",
            "reveal": "cumulative",
            "step_delay_ms": 400,
            "loop": "none",
            "out": "fade",
            "accent": "badge",
        },
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "hook_fs": 70,
        "hook_font": "Kanit",
    }

    events = overlay_events(overlay, ctx)
    assert len(events) >= 3

    # Tier 0 (LOGITECH): t0 = 0 -> starts immediately
    tier0_event = [t for t in events if "HookHeader," in t and "LOGITECH" in t][0]
    assert r"\alpha&HFF&\t(0,0,\alpha&H00&)" not in tier0_event

    # Tier 1 (WAVE KEYS): t0 = 400ms -> pre-t0 invisible via slam's alpha&HFF&, transitions from 400 to 450
    tier1_event = [t for t in events if "HookHeader," in t and "WAVE KEYS" in t][0]
    assert r"\alpha&HFF&" in tier1_event
    assert r"\t(400,450,\alpha&H00&)" in tier1_event  # slam alpha fade

    # Tier 2 (KEYBOARD): t0 = 800ms -> pre-t0 invisible via slam's alpha&HFF&, transitions from 800 to 850
    tier2_event = [t for t in events if "HookHeader," in t and "KEYBOARD" in t][0]
    assert r"\alpha&HFF&" in tier2_event
    assert r"\t(800,850,\alpha&H00&)" in tier2_event

    # Pill for tier 2 (HookHeaderPill): should have pre-t0 invisible tag
    pill_events = [t for t in events if "HookHeaderPill" in t]
    assert len(pill_events) >= 1
    assert any(r"\alpha&HFF&" in p and r"\t(800,850,\alpha&H00&)" in p for p in pill_events)

    # Now test with bounce (which has no intrinsic alpha, so it gets \alpha&HFF&\t(t0,t0,\alpha&H00&))
    overlay_bounce = dict(overlay)
    overlay_bounce["anim"] = dict(overlay["anim"])
    overlay_bounce["anim"]["in"] = "bounce"
    events_bounce = overlay_events(overlay_bounce, ctx)
    b_tier1 = [t for t in events_bounce if "HookHeader," in t and "WAVE KEYS" in t][0]
    assert r"\alpha&HFF&\t(400,400,\alpha&H00&)" in b_tier1
    b_pill = [t for t in events_bounce if "HookHeaderPill" in t]
    assert any(r"\alpha&HFF&\t(800,800,\alpha&H00&)" in p for p in b_pill)


def test_preview_render_parity_for_slam_and_elastic_bounce():
    sp_js = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
    # slam exists in OVERLAY_IN_TRANSFORMS with 0.18s durSec
    assert "slam: {" in sp_js
    assert "durSec: 0.18" in sp_js
    assert "[0, 2.2]" in sp_js
    assert "[180, 1.0, ACCEL_SNAP_IN]" in sp_js

    # elastic_bounce exists in OVERLAY_IN_TRANSFORMS with 0.52s durSec
    assert "elastic_bounce: {" in sp_js
    assert "durSec: 0.52" in sp_js
    assert "[0, 0.4]" in sp_js
    assert "[520, 1.0, ACCEL_SOFT_OUT]" in sp_js

    # cumulative reveal handling exists in SequencePlayer.jsx
    assert "isCumulative = revealMode === 'cumulative' || revealMode === 'tier_step'" in sp_js
    assert "if (isCumulative && tRel < t0)" in sp_js
    assert "if (isCumulative && tRel < boxT0) continue;" in sp_js
