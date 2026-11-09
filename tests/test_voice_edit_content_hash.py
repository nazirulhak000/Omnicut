"""X-04: saved voice cuts bind to the voice file's CONTENT hash, not mtime/size.

Everything lives in tmp_path.  The pipeline-level checks reuse the fixtures of
test_voice_edit_pipeline (a reused voice file + a manifest with voice_edit).
"""

from __future__ import annotations

import os

import pytest

from scripts import voice_cut_map
from scripts.project_manifest import ProjectManifest
from scripts.stages.voice_stage import VoiceStage
from scripts.voice_cut_map import (
    VoiceEditError,
    resolve_voice_cuts,
    source_matches,
    upgrade_voice_edit_source,
    validate_voice_edit,
    voice_file_identity,
)

from tests.test_voice_edit_pipeline import (  # noqa: F401  (fixture + helpers)
    PROJECT,
    _ctx,
    _cut,
    _voice_edit,
    project,
)


def _edit(source, cuts=None, duration=10.0):
    return {
        "schema_version": 1,
        "source": {**source, "duration": duration},
        "cuts": cuts or [{"id": "c1", "start": 2.0, "end": 2.5, "reason": "manual"}],
    }


@pytest.fixture
def voice(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_cut_map, "BASE_DIR", tmp_path)
    path = tmp_path / "voiceover.wav"
    path.write_bytes(b"voice-content-A" * 100)
    return path


def _hashed_source(voice_path):
    identity = voice_file_identity(voice_path)
    return {"path": "voiceover.wav", "size": identity["size"],
            "mtime_ns": identity["mtime_ns"], "sha256": identity["sha256"]}


def test_identity_carries_the_content_hash(voice):
    identity = voice_file_identity(voice)
    assert len(identity["sha256"]) == 64
    assert identity["size"] == voice.stat().st_size


def test_touching_mtime_does_not_drop_hash_bound_cuts(voice):
    edit = _edit(_hashed_source(voice))
    os.utime(voice, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))   # touch only
    cuts, problem, duration = resolve_voice_cuts(edit, voice_file_identity(voice))
    assert problem is None and duration == 10.0
    assert cuts and cuts[0]["start"] == 2.0


def test_rewriting_identical_bytes_keeps_the_cuts(voice):
    edit = _edit(_hashed_source(voice))
    voice.write_bytes(voice.read_bytes())            # new mtime, same content
    assert resolve_voice_cuts(edit, voice_file_identity(voice))[1] is None


def test_changing_content_drops_the_cuts_even_with_same_size_and_mtime(voice):
    edit = _edit(_hashed_source(voice))
    stat = voice.stat()
    voice.write_bytes(b"voice-content-B" * 100)      # same length, different audio
    os.utime(voice, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    current = voice_file_identity(voice)
    assert current["size"] == edit["source"]["size"]
    assert current["mtime_ns"] == edit["source"]["mtime_ns"]
    assert resolve_voice_cuts(edit, current) == ([], "stale", 10.0)


def test_hash_match_survives_a_renamed_or_moved_file(voice, tmp_path):
    edit = _edit(_hashed_source(voice))
    moved = tmp_path / "renamed" / "voice_final.wav"
    moved.parent.mkdir()
    moved.write_bytes(voice.read_bytes())
    assert source_matches(edit["source"], voice_file_identity(moved)) is True


def test_pipeline_fingerprint_without_hash_is_hashed_from_the_file(voice):
    edit = _edit(_hashed_source(voice))
    identity = voice_file_identity(voice)
    bare = {"path": identity["path"], "size_bytes": identity["size"], "mtime_ns": 1}
    assert source_matches(edit["source"], bare) is True
    assert source_matches(edit["source"], {"path": str(voice.parent / "missing.wav")}) is False


def test_malformed_source_hash_is_never_trusted(voice):
    source = _hashed_source(voice)
    for bad in ("nothex", "A" * 64, "0" * 63, 12345):
        assert source_matches({**source, "sha256": bad}, voice_file_identity(voice)) is False


# ----------------------------------------------------- backward compatibility

def test_old_identity_without_hash_still_matches_then_upgrades(voice):
    identity = voice_file_identity(voice)
    legacy = _edit({"path": "voiceover.wav", "size": identity["size"], "mtime_ns": identity["mtime_ns"]})
    assert resolve_voice_cuts(legacy, identity)[1] is None          # accepted as the fallback

    upgraded = upgrade_voice_edit_source(legacy, identity)
    assert upgraded["source"]["sha256"] == identity["sha256"]
    assert upgraded["cuts"] == legacy["cuts"]
    assert "sha256" not in legacy["source"]                          # input untouched

    os.utime(voice, ns=(1_700_000_000_000_000_000,) * 2)
    touched = voice_file_identity(voice)
    assert resolve_voice_cuts(legacy, touched)[1] == "stale"         # old identity: mtime drift loses it
    assert resolve_voice_cuts(upgraded, touched)[1] is None          # re-saved with the hash: survives


def test_upgrade_refuses_stale_hashed_or_empty_edits(voice):
    identity = voice_file_identity(voice)
    legacy = _edit({"path": "voiceover.wav", "size": identity["size"], "mtime_ns": identity["mtime_ns"]})
    assert upgrade_voice_edit_source(None, identity) is None
    assert upgrade_voice_edit_source(_edit(_hashed_source(voice)), identity) is None   # already hashed
    voice.write_bytes(b"different")
    assert upgrade_voice_edit_source(legacy, voice_file_identity(voice)) is None       # stale: no new hash


# -------------------------------------------------------------- save-time stamp

def test_validate_fills_the_hash_only_when_identity_matches_the_current_file(voice):
    identity = voice_file_identity(voice)
    stamp = {"path": "voiceover.wav", "size": identity["size"], "mtime_ns": identity["mtime_ns"],
             "sha256": identity["sha256"]}
    raw = _edit({"path": "voiceover.wav", "size": identity["size"], "mtime_ns": identity["mtime_ns"]},
                duration=10.0)
    assert validate_voice_edit(raw, stamp=stamp)["source"]["sha256"] == identity["sha256"]

    omitted = _edit({}, duration=10.0)                                # client sent no identity
    assert validate_voice_edit(omitted, stamp=stamp)["source"]["sha256"] == identity["sha256"]

    other_file = _edit({"path": "voiceover.wav", "size": identity["size"], "mtime_ns": 1}, duration=10.0)
    assert "sha256" not in validate_voice_edit(other_file, stamp=stamp)["source"]   # never bind a stale file

    assert "sha256" not in validate_voice_edit(raw, stamp=None)["source"]           # legacy shape unchanged


def test_validate_rejects_a_malformed_hash(voice):
    with pytest.raises(VoiceEditError):
        validate_voice_edit(_edit({"path": "v.wav", "size": 1, "mtime_ns": 1, "sha256": "zz"}))


# ------------------------------------------------------------- VoiceStage

def test_voice_stage_resaves_a_legacy_edit_with_the_hash(project):
    ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.5)]), total_duration=5.5)
    assert "sha256" not in ProjectManifest.load(PROJECT)["voice_edit"]["source"]
    ctx = _ctx(project)

    VoiceStage.run(ctx)

    stored = ProjectManifest.load(PROJECT)["voice_edit"]
    assert stored["source"]["sha256"] == voice_file_identity(project.voice)["sha256"]
    assert ctx.voice_edit == stored
    assert ctx.voice_cuts and ctx.voice_edit_stale is False


def test_voice_stage_keeps_hash_bound_cuts_after_an_mtime_touch(project):
    identity = voice_file_identity(project.voice)
    edit = _voice_edit(project, [_cut(2.0, 2.5)])
    edit["source"]["sha256"] = identity["sha256"]
    ProjectManifest.save(PROJECT, voice_edit=edit, total_duration=5.5)
    os.utime(project.voice, ns=(1_700_000_000_000_000_000,) * 2)
    ctx = _ctx(project)

    VoiceStage._apply_voice_edit(ctx, project.voice, 6.0)

    assert ctx.voice_cuts == [_cut(2.0, 2.5)]
    assert ctx.voice_edit_stale is False


# ------------------------------------------------------------------- API

from tests.test_voice_edit_api import STATE, URL, api, cut as api_cut, edit as api_edit  # noqa: E402,F401


def test_api_save_stamps_the_hash_and_survives_an_mtime_touch(api):
    response = api.patch(STATE, json={"voice_edit": api_edit([api_cut(2.0, 2.5)])})
    assert response.status_code == 200, response.text
    stored = response.json()["voice_edit"]
    assert stored["source"]["sha256"] == voice_file_identity(api.voice)["sha256"]

    os.utime(api.voice, ns=(1_700_000_000_000_000_000,) * 2)         # e.g. a backup tool touched it
    loaded = api.get(URL).json()
    assert not loaded.get("voice_edit_stale")
    assert loaded["voice_edit"]["cuts"] == stored["cuts"]

    # an editor that echoes the old source WITHOUT the hash must not lose the binding
    echo = {k: v for k, v in stored["source"].items() if k != "sha256"}
    again = api.patch(STATE, json={"voice_edit": {"schema_version": 1, "source": echo,
                                                  "cuts": [api_cut(2.0, 2.5), api_cut(4.0, 4.5, "c2")]}})
    assert again.status_code == 200, again.text
    assert again.json()["voice_edit"]["source"]["sha256"] == stored["source"]["sha256"]
    assert again.json()["voice_edit_stale"] is False


def test_api_replaced_audio_marks_hash_bound_cuts_stale(api):
    api.patch(STATE, json={"voice_edit": api_edit([api_cut(2.0, 2.5)])})
    stat = api.voice.stat()
    data = bytearray(api.voice.read_bytes())
    data[-1] ^= 0x01                                                  # same size, different audio
    api.voice.write_bytes(bytes(data))
    os.utime(api.voice, ns=(stat.st_atime_ns, stat.st_mtime_ns))      # even with the old mtime
    assert api.get(URL).json()["voice_edit_stale"] is True
