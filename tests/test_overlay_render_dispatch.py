from scripts.overlay_model import overlay_kind
from scripts.subtitle.overlay_events import overlay_events


def test_overlay_kind_normalizes_canonical_and_legacy_spellings():
    assert overlay_kind({"kind": "hook"}) == "hook"
    assert overlay_kind({"type": "hook_header"}) == "hook"
    assert overlay_kind({"kind": "text"}) == "text"
    assert overlay_kind({"type": "text_overlay"}) == "text"


def test_overlay_dispatch_rejects_unknown_kind_without_emitting_events():
    assert overlay_kind({"kind": "future_overlay"}) is None
    assert overlay_events({"kind": "future_overlay"}, {}) == []
    assert overlay_events(None, {}) == []
