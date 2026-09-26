"""Tests for the stale-cutout render guard in scripts/api_phase1.py.

The editor sends the cutout config it held when Render was pressed. If that
tab was showing an older state -- artifact still preparing, or prepared in
another tab -- the payload can say "cutout off" while the saved project has
every clip ready. Rendering anyway succeeds and silently produces a video
with the hook text over the product instead of behind it, which reads as a
broken feature rather than a stale browser tab.

The guard has to be narrow: refusing too eagerly would block a deliberate
"render without cutout", which is a real workflow.
"""
from __future__ import annotations

import pytest

from scripts.api_phase1 import _guard_stale_cutout_payload


def _ready_clip():
    return {
        "source_path": "01_Raw/a.mp4",
        "background_isolation": {
            "enabled": True,
            "artifact": {"id": "bgseq1-" + "a" * 16, "status": "ready"},
        },
    }


def _manifest(clips=None, enabled=True):
    return {
        "background_isolation": {"enabled": enabled, "artifact": {"id": None, "status": "missing"}},
        "clip_list": clips if clips is not None else [_ready_clip()],
    }


# ---------------------------------------------------------------------------
# The case this exists for
# ---------------------------------------------------------------------------

def test_refuses_when_payload_is_older_than_the_saved_project():
    """Saved project has a ready artifact; the payload says cutout is off."""
    params = {"background_isolation": {"enabled": False}}
    with pytest.raises(ValueError, match="Cutout"):
        _guard_stale_cutout_payload(params, _manifest())


def test_refuses_when_payload_omits_cutout_entirely():
    """A payload with no cutout key at all is the same staleness."""
    with pytest.raises(ValueError, match="Cutout"):
        _guard_stale_cutout_payload({}, _manifest())


def test_message_names_how_many_clips_are_ready():
    """The user needs to know the project really does have prepared work."""
    manifest = _manifest([_ready_clip(), _ready_clip(), _ready_clip()])
    with pytest.raises(ValueError, match="3"):
        _guard_stale_cutout_payload({"background_isolation": {"enabled": False}}, manifest)


def test_message_tells_the_user_what_to_do():
    with pytest.raises(ValueError, match="รีเฟรช"):
        _guard_stale_cutout_payload({}, _manifest())


# ---------------------------------------------------------------------------
# Renders that must NOT be blocked
# ---------------------------------------------------------------------------

def test_allows_a_matching_enabled_payload():
    params = {"background_isolation": {"enabled": True, "artifact": {"status": "ready", "id": "x"}}}
    _guard_stale_cutout_payload(params, _manifest())


def test_allows_when_the_project_switch_is_off():
    """Deliberately rendering without cutout: the project itself says off."""
    _guard_stale_cutout_payload({"background_isolation": {"enabled": False}},
                                _manifest(enabled=False))


def test_allows_when_no_clip_has_a_ready_artifact():
    """The switch is on but nothing is prepared yet -- there is nothing the
    render could have used, so this is not staleness."""
    pending = {
        "source_path": "01_Raw/a.mp4",
        "background_isolation": {"enabled": True,
                                 "artifact": {"id": None, "status": "processing"}},
    }
    _guard_stale_cutout_payload({"background_isolation": {"enabled": False}},
                                _manifest([pending]))


def test_allows_when_the_project_has_no_cutout_config():
    _guard_stale_cutout_payload({}, {"clip_list": [_ready_clip()]})


def test_allows_an_empty_project():
    _guard_stale_cutout_payload({}, _manifest([]))


# ---------------------------------------------------------------------------
# Malformed input must not crash a render
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("manifest", [
    {},
    {"background_isolation": None},
    {"background_isolation": "enabled"},
    {"background_isolation": {"enabled": True}},
    {"background_isolation": {"enabled": True}, "clip_list": None},
    {"background_isolation": {"enabled": True}, "clip_list": ["not-a-dict"]},
    {"background_isolation": {"enabled": True}, "clip_list": [{"background_isolation": None}]},
    {"background_isolation": {"enabled": True},
     "clip_list": [{"background_isolation": {"artifact": "ready"}}]},
])
def test_malformed_manifests_are_tolerated(manifest):
    """A guard that throws on odd input is a guard that gets removed."""
    _guard_stale_cutout_payload({}, manifest)


def test_malformed_payload_is_tolerated():
    _guard_stale_cutout_payload({"background_isolation": "yes"}, _manifest(enabled=False))


def test_guard_runs_after_the_failure_handler_is_defined():
    """The guard must raise somewhere the except block can actually handle.

    It was first placed near the top of _execute_reroll, before the local
    _restore_pre_reroll_snapshot was defined. Raising there made the except
    block itself die with UnboundLocalError, so fail_task never ran: the job
    sat at "queued" forever and the user saw a render that simply never
    started, with no error anywhere. This pins the ordering.
    """
    import inspect

    from scripts import api_phase1

    source = inspect.getsource(api_phase1._execute_reroll)
    guard_at = source.index("_guard_stale_cutout_payload(params, manifest)")
    helper_at = source.index("def _restore_pre_reroll_snapshot()")

    assert helper_at < guard_at, (
        "_guard_stale_cutout_payload must be called after "
        "_restore_pre_reroll_snapshot is defined, or the except block that "
        "reports the failure cannot run"
    )
