"""Voice ripple cuts through the pipeline contracts (round EDITOR-CUT-QUALITY-R3, lane RB).

* the mix fingerprint sees the cuts (changing them invalidates the cached mix) and
  stays exactly what it was for a project that never cut;
* VoiceStage applies saved cuts only to a REUSED voice file whose fingerprint still
  matches, flags stale ones, and clears them whenever a new voice file is produced;
* AudioMixStage hands the cuts to the mixer (and nothing extra when there are none).

No real TTS/ffmpeg mix: stubs + tmp_path manifests. (ffprobe is used only to read the
length of a tiny synthetic wav in the stale-file case.)
"""

import wave
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts import pipeline_context, project_manifest, voice_cut_map
from scripts.pipeline_context import (
    INCREMENTAL_RENDER_SCHEMA_VERSION,
    PipelineContext,
    _artifact_fingerprints_from_manifest,
    _payload_fingerprint,
    _stage_payload_from_manifest,
    build_incremental_render_metadata,
)
from scripts.project_manifest import ProjectManifest
from scripts.sfx_manager import SFXManager
from scripts.stages.audio_mix_stage import AudioMixStage
from scripts.stages.voice_stage import VoiceStage
from scripts.voice_cut_map import voice_file_identity

PROJECT = "voice-edit-demo"

# The saved render's inputs and the context's inputs must agree, or the strict reuse
# contract (rightly) refuses to reuse anything and the tests would measure that instead.
RENDER_PARAMS = {
    "product_name": "Product", "key_features": "feature", "pain_point": "pain", "price_deal": "deal",
    "custom_script": "hello", "script_overlays": [""], "voice": "female", "voice_rate": "+15%",
    "voice_engine_type": "edge_tts", "voice_engine_used": "edge_tts", "voice_preset": "gemini_puck_male_hype",
    "ad_tone": "commercial_premium", "font_name": "IBMPlex", "bilingual_subtitles": True,
    "bgm_name": None, "bgm_volume": None, "bgm_ducking": True, "audio_mutes": {}, "lut_name": None,
    "lut_intensity": 1.0, "caption_position": "bottom", "caption_color": None, "caption_scale": 1.0,
    "sticker_position": "top_right", "sticker_scale": 1.0, "overlays": [], "text_overlays": None,
    "stickers": None, "effects": None, "sticker_path": None, "human_voice_audio_path": None,
}
VOICE_SECONDS = 6.0
RATE = 16000


def _write_wav(path, seconds):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\x00\x00" * int(RATE * seconds))


def _cut(start, end, cid="c1"):
    return {"id": cid, "start": start, "end": end, "reason": "manual"}


@pytest.fixture
def project(tmp_path, monkeypatch):
    projects_dir = tmp_path / "03_Projects"
    projects_dir.mkdir()
    for module in (project_manifest, pipeline_context, voice_cut_map):
        monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", projects_dir)

    project_dir = projects_dir / PROJECT
    project_dir.mkdir()
    raw = tmp_path / "01_Raw" / "source.mp4"
    raw.parent.mkdir()
    raw.write_bytes(b"source-v1")
    voice = project_dir / "voiceover.wav"
    _write_wav(voice, VOICE_SECONDS)
    mixed = project_dir / "mixed_audio.wav"
    mixed.write_bytes(b"mix-v1")
    subtitles = project_dir / "subtitles.ass"
    subtitles.write_text("[Script Info]\n", encoding="utf-8")
    mp4 = tmp_path / "04_Exports" / "final.mp4"
    mp4.parent.mkdir()
    mp4.write_bytes(b"mp4-v1")

    cues = [{"start": 0.0, "end": 1.0, "text": "hello", "sfx": None}]
    manifest = ProjectManifest.save(
        PROJECT,
        script_data={"lines": [{"text": "hello", "sfx": None, "on_screen": ""}], "full_text": "hello"},
        cues=cues, micro_cues=cues, beat_cues=cues,
        total_duration=VOICE_SECONDS,
        clip_list=[], transitions=[], overlays=[],
        render_params={**RENDER_PARAMS, "raw_video_path": str(raw), "clip_list": [], "transitions": []},
        artifacts={
            "voice_audio": {"path": str(voice)},
            "mixed_audio": {"path": str(mixed)},
            "subtitles_ass": {"path": str(subtitles)},
            "mp4_video": {"path": str(mp4)},
        },
    )
    manifest = ProjectManifest.save(PROJECT, incremental_render=build_incremental_render_metadata(manifest))
    return SimpleNamespace(base=tmp_path, dir=project_dir, voice=voice, raw=raw, manifest=manifest)


def _voice_edit(project, cuts, duration=VOICE_SECONDS):
    """A voice_edit exactly as the save endpoint stores it for the CURRENT voice file."""
    entry = ProjectManifest.load(PROJECT)["artifacts"]["voice_audio"]
    identity = voice_file_identity(project.voice)
    return {
        "schema_version": 1,
        "source": {"path": entry["path"], "size": identity["size"],
                   "mtime_ns": identity["mtime_ns"], "duration": duration},
        "cuts": cuts,
    }


def _ctx(project, manifest=None, **overrides):
    values = dict(
        product_name="Product", raw_video_path=str(project.raw), project_name=PROJECT,
        key_features="feature", pain_point="pain", price_deal="deal", custom_script="hello",
        script_overlays=[""], voice="female", voice_rate="+15%", voice_engine_type="edge_tts",
        voice_preset="gemini_puck_male_hype", ad_tone="commercial_premium", font_name="IBMPlex",
        bilingual_subtitles=True, bgm_ducking=True, caption_position="bottom", caption_scale=1.0,
        sticker_position="top_right", sticker_scale=1.0, lut_intensity=1.0, resume_from="subtitles",
        manifest=manifest if manifest is not None else ProjectManifest.load(PROJECT),
        project_dir=project.dir, export_mp4=True,
    )
    values.update(overrides)
    return PipelineContext(**values)


# ---------------------------------------------------------------------------
# mix fingerprint
# ---------------------------------------------------------------------------

def _mix_inputs(manifest):
    fingerprints = _artifact_fingerprints_from_manifest(manifest)
    return _stage_payload_from_manifest(manifest, "mix", fingerprints)["inputs"], fingerprints


def test_mix_payload_without_cuts_has_exactly_the_pre_feature_keys_and_fingerprint(project):
    manifest = ProjectManifest.load(PROJECT)
    inputs, fingerprints = _mix_inputs(manifest)

    assert set(inputs) == {
        "voice_audio", "micro_cues", "total_duration", "overlays", "bgm_name", "bgm_file",
        "bgm_volume", "bgm_ducking", "audio_mutes", "sfx_files",
    }
    expected = {
        "schema_version": INCREMENTAL_RENDER_SCHEMA_VERSION, "stage": "mix",
        "inputs": {
            "voice_audio": fingerprints["voice_audio"], "micro_cues": manifest["micro_cues"],
            "total_duration": manifest["total_duration"], "overlays": manifest["overlays"],
            "bgm_name": None, "bgm_file": None, "bgm_volume": None, "bgm_ducking": True,
            "audio_mutes": {}, "sfx_files": [],
        },
    }
    assert _payload_fingerprint(_stage_payload_from_manifest(manifest, "mix", fingerprints)) == _payload_fingerprint(expected)


def test_mix_payload_carries_only_the_cuts_that_will_really_apply(project):
    base = _payload_fingerprint(_stage_payload_from_manifest(
        ProjectManifest.load(PROJECT), "mix", _artifact_fingerprints_from_manifest(ProjectManifest.load(PROJECT))))

    manifest = ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.5)]))
    inputs, fingerprints = _mix_inputs(manifest)
    assert inputs["voice_cuts"] == [[2.0, 2.5]]
    with_cut = _payload_fingerprint(_stage_payload_from_manifest(manifest, "mix", fingerprints))
    assert with_cut != base

    # another range -> another fingerprint; only ids/reasons changing -> the same one
    other = ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.6)]))
    assert _payload_fingerprint(_stage_payload_from_manifest(
        other, "mix", _artifact_fingerprints_from_manifest(other))) not in (base, with_cut)
    renamed = ProjectManifest.save(PROJECT, voice_edit=_voice_edit(
        project, [{"id": "other-id", "start": 2.0, "end": 2.6, "reason": "silence"}]))
    assert _payload_fingerprint(_stage_payload_from_manifest(
        renamed, "mix", _artifact_fingerprints_from_manifest(renamed))) == _payload_fingerprint(_stage_payload_from_manifest(
            other, "mix", _artifact_fingerprints_from_manifest(other)))

    # stale (file changed since the cut) or malformed voice_edit is ignored like the stage ignores it
    stale = _voice_edit(project, [_cut(2.0, 2.5)])
    stale["source"]["size"] += 1
    stale_manifest = ProjectManifest.save(PROJECT, voice_edit=stale)
    stale_inputs, stale_fp = _mix_inputs(stale_manifest)
    assert "voice_cuts" not in stale_inputs
    assert _payload_fingerprint(_stage_payload_from_manifest(stale_manifest, "mix", stale_fp)) == base
    broken = ProjectManifest.save(PROJECT, voice_edit={"source": "x", "cuts": [_cut(1, 2)]})
    assert "voice_cuts" not in _mix_inputs(broken)[0]


def test_changing_the_cuts_invalidates_the_cached_mix_but_not_the_voice(project):
    ctx = _ctx(project)
    assert ctx.should_run("mix") is False and ctx.should_run("voice") is False

    ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.5)]))
    ctx = _ctx(project)
    assert ctx.should_run("voice") is False                  # the voice file itself is untouched
    assert ctx.should_run("mix") is True                      # the cuts changed the mix inputs
    first = ctx.expected_stage_fingerprint("mix")

    # a finished render stamps the new fingerprint: the mix is reusable again ...
    manifest = ProjectManifest.load(PROJECT)
    ProjectManifest.save(PROJECT, incremental_render=build_incremental_render_metadata(manifest))
    assert _ctx(project).should_run("mix") is False
    assert _ctx(project).expected_stage_fingerprint("mix") == first

    # ... until the cuts change once more
    ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.5), _cut(4.0, 4.2, "c2")]))
    changed = _ctx(project)
    assert changed.should_run("mix") is True
    assert changed.expected_stage_fingerprint("mix") != first


def test_the_context_snapshot_carries_the_voice_edit_the_stage_accepted(project):
    edit = _voice_edit(project, [_cut(2.0, 2.5)])
    ctx = _ctx(project)
    assert "voice_edit" not in ctx._manifest_snapshot_from_context()
    ctx.voice_edit = edit
    assert ctx._manifest_snapshot_from_context()["voice_edit"] == edit


# ---------------------------------------------------------------------------
# VoiceStage
# ---------------------------------------------------------------------------

def test_reused_voice_with_matching_cuts_uses_the_post_cut_duration(project, capsys):
    ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.01, 2.49), _cut(4.0, 4.2, "c2")]),
                         total_duration=999.0)               # whatever the manifest says, the cuts decide
    ctx = _ctx(project)

    VoiceStage.run(ctx)

    assert ctx.voice_cuts == [_cut(2.0, 2.5), _cut(4.0, 4.2, "c2")]
    assert ctx.voice_source_duration == VOICE_SECONDS
    assert ctx.total_duration == pytest.approx(VOICE_SECONDS - 0.5 - 0.2)
    assert ctx.voice_edit == ProjectManifest.load(PROJECT)["voice_edit"]
    assert ctx.voice_edit_stale is False and ctx.voice_edit_notice is None
    assert ctx.voice_audio_path == project.voice
    assert "✂️" in capsys.readouterr().out
    # nothing about the cuts is rewritten on disk by the stage
    assert ProjectManifest.load(PROJECT)["voice_edit"]["cuts"][0]["start"] == 2.01


def test_reused_voice_without_voice_edit_is_unchanged(project):
    before = ProjectManifest.load(PROJECT)
    ctx = _ctx(project)

    VoiceStage.run(ctx)

    assert ctx.voice_cuts == [] and ctx.voice_edit is None and ctx.voice_edit_stale is False
    assert ctx.total_duration == VOICE_SECONDS
    assert ProjectManifest.load(PROJECT) == before            # no bookkeeping written


def test_saved_cuts_that_do_not_match_the_file_are_never_applied_and_flagged(project):
    ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.5)]), total_duration=5.5)
    # The voice file is replaced by a longer take, and a later render re-stamped the
    # fingerprints around it (so the voice is "reusable") -- the saved cuts belong to the OLD file.
    _write_wav(project.voice, 7.0)
    manifest = ProjectManifest.load(PROJECT)
    ProjectManifest.save(PROJECT, incremental_render=build_incremental_render_metadata(manifest))
    ctx = _ctx(project)
    assert ctx.should_run("voice") is False

    VoiceStage.run(ctx)

    assert ctx.voice_cuts == [] and ctx.voice_edit is None
    assert ctx.voice_edit_stale is True
    assert "ไม่ตรงกับตอนที่ตัด" in ctx.voice_edit_notice
    assert ctx.total_duration == pytest.approx(7.0, abs=0.01)  # the file's real length, not the cut one
    saved = ProjectManifest.load(PROJECT)
    assert saved["voice_edit_stale"] is True
    assert saved["voice_edit_notice"]["kind"] == "stale"
    assert saved["voice_edit"]["cuts"]                         # kept so the editor can still show it


@pytest.mark.parametrize("engine", ["edge_tts", "gemini_tts"])
def test_generating_a_new_voice_clears_the_saved_cuts_with_a_thai_reason(project, engine, capsys):
    ProjectManifest.save(PROJECT, voice_edit=_voice_edit(project, [_cut(2.0, 2.5)]), voice_edit_stale=True)
    ctx = _ctx(project, resume_from="voice", voice_engine_type=engine)
    assert ctx.manifest["voice_edit"]

    edge_result = {"cues": [{"start": 0.0, "end": 1.0, "text": "hello", "line_idx": 0}], "duration": 4.0}
    with patch("scripts.voice_engine.VoiceEngine.generate_voiceover", return_value=edge_result), \
            patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.resolve_voice", return_value="Fenrir"), \
            patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech",
                  side_effect=lambda **kw: _write_wav(kw["output_path"], 4.0)), \
            patch("scripts.stages.voice_stage._probe_audio_duration", return_value=4.0), \
            patch("scripts.stages.voice_stage._rms_aligned_cues",
                  return_value=[{"start": 0.0, "end": 1.0, "text": "hello"}]):
        VoiceStage.run(ctx)

    assert ctx.total_duration == 4.0
    assert ctx.voice_cuts == [] and ctx.voice_edit is None and ctx.voice_edit_stale is False
    assert "ล้างการตัดเสียงเดิม (1 ช่วง)" in ctx.voice_edit_notice
    assert "voice_edit" not in ctx.manifest                    # the in-memory manifest the snapshot reads
    saved = ProjectManifest.load(PROJECT)
    assert saved["voice_edit"] is None
    assert saved["voice_edit_stale"] is False
    assert saved["voice_edit_notice"] == {"kind": "dropped", "reason": ctx.voice_edit_notice}
    assert "ล้างการตัดเสียงเดิม" in capsys.readouterr().out


def test_generating_a_voice_for_a_project_without_cuts_writes_no_bookkeeping(project):
    before = ProjectManifest.load(PROJECT)
    ctx = _ctx(project, resume_from="voice")
    edge_result = {"cues": [{"start": 0.0, "end": 1.0, "text": "hello", "line_idx": 0}], "duration": 4.0}
    with patch("scripts.voice_engine.VoiceEngine.generate_voiceover", return_value=edge_result):
        VoiceStage.run(ctx)
    assert ctx.voice_edit_notice is None
    assert ProjectManifest.load(PROJECT) == before


def test_a_project_that_has_no_manifest_on_disk_is_not_created_by_the_bookkeeping(tmp_path, monkeypatch):
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "03_Projects")
    ctx = PipelineContext(product_name="G", raw_video_path="x.mp4", project_name="ghost",
                          voice_engine_type="edge_tts", voice_rate=None)
    ctx.manifest = {"voice_edit": {"cuts": [{"id": "a", "start": 1, "end": 2}]}}
    VoiceStage._drop_voice_edit(ctx)
    assert not (tmp_path / "03_Projects" / "ghost").exists()
    assert "voice_edit" not in ctx.manifest


# ---------------------------------------------------------------------------
# AudioMixStage
# ---------------------------------------------------------------------------

@pytest.fixture
def mix_calls(monkeypatch):
    calls = []

    def fake_mix(cls, **kwargs):
        calls.append(kwargs)
        return kwargs["output_audio_path"]

    monkeypatch.setattr(SFXManager, "mix_audio_track", classmethod(fake_mix))
    return calls


def _mix_ctx(project, **overrides):
    values = dict(
        product_name="G", raw_video_path="x.mp4", project_name=PROJECT, project_dir=project.dir,
        export_mp4=True, total_duration=5.5, voice_audio_path=project.voice, micro_cues=[],
        resume_from="mix", manifest=None,
    )
    values.update(overrides)
    return PipelineContext(**values)


def test_mix_stage_hands_the_cuts_to_the_mixer(project, mix_calls):
    cuts = [_cut(2.0, 2.5)]
    ctx = _mix_ctx(project, voice_cuts=cuts, voice_source_duration=6.0)

    AudioMixStage.run(ctx)

    assert len(mix_calls) == 1
    assert mix_calls[0]["voice_cuts"] == cuts
    assert mix_calls[0]["voice_source_duration"] == 6.0
    assert mix_calls[0]["total_duration"] == 5.5               # the post-cut length drives SFX/BGM bounds


def test_mix_stage_without_cuts_calls_the_mixer_exactly_as_before(project, mix_calls):
    AudioMixStage.run(_mix_ctx(project))

    assert len(mix_calls) == 1
    assert "voice_cuts" not in mix_calls[0] and "voice_source_duration" not in mix_calls[0]
