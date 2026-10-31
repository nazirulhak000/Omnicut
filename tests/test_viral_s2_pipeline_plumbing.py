"""AI editor viral S2 / Agent H: pipeline plumbing.

* ``target_duration`` / ``story_format`` as real fields: request -> context ->
  script prompt context -> manifest (top level + render_params) -> export
  registry style metadata, with silent fallback on bad input and old
  manifests keeping their stage fingerprints.
* Visual cut times reach ``SFXManager.mix_audio_track`` (``cut_times=``), and
  a render whose clips are generated after the mix re-mixes only when the
  final cuts change the SFX plan.
* Export style metadata is captured at render time (pipeline + HyperFrames).

Offline and deterministic: tmp_path stores only, no ffmpeg, no network, no
paid API, nothing written to 04_Exports.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts import api_render, pipeline_context, project_manifest, render_jobs
from scripts.api_schemas import RenderRequest
from scripts.pipeline_context import (
    PipelineContext,
    _stage_payload_from_manifest,
    clip_cut_times,
    cut_bound_sfx_plan,
    normalize_story_format,
    normalize_target_duration,
)
from scripts.project_manifest import ProjectManifest
from scripts.sfx_manager import SFXManager
from scripts.stages.audio_mix_stage import AudioMixStage
from tests.test_incremental_render_reuse import _context_for, _strict_project, isolated_manifest  # noqa: F401
from tests.test_hyperframes_finalize import context as hf_context, finish as hf_finish  # noqa: F401


# ----------------------------------------------------------------------
# Normalisation
# ----------------------------------------------------------------------
@pytest.mark.parametrize("raw, expected", [
    (15, 15), (25, 25), (35, 35), (45, 45),
    ("25", 25), (" 45 ", 45), (35.0, 35), ("35.0", 35),
    (None, None), ("", None), (0, None), (30, None), (60, None), (25.5, None),
    (True, None), (False, None), ("abc", None), ([25], None), ({"s": 25}, None),
    (float("nan"), None), (float("inf"), None), (-25, None),
])
def test_target_duration_accepts_only_supported_lengths(raw, expected):
    assert normalize_target_duration(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("classic", "classic"), ("countdown", "countdown"), ("problem_reveal", "problem_reveal"),
    ("myth_buster", "myth_buster"), ("loop", "loop"), (" LOOP ", "loop"), ("Countdown", "countdown"),
    (None, "classic"), ("", "classic"), ("tutorial", "classic"), (3, "classic"), (["loop"], "classic"),
])
def test_story_format_falls_back_to_classic(raw, expected):
    assert normalize_story_format(raw) == expected


def test_context_defaults_and_silent_fallback():
    ctx = PipelineContext(product_name="P", raw_video_path="raw.mp4")
    assert ctx.target_duration is None
    assert ctx.story_format == "classic"

    good = PipelineContext(product_name="P", raw_video_path="raw.mp4", target_duration="45", story_format="Loop")
    assert (good.target_duration, good.story_format) == (45, "loop")

    bad = PipelineContext(product_name="P", raw_video_path="raw.mp4", target_duration=999, story_format="??")
    assert (bad.target_duration, bad.story_format) == (None, "classic")


# ----------------------------------------------------------------------
# Request -> pipeline -> context
# ----------------------------------------------------------------------
def _request(**extra):
    base = dict(product_name="P", raw_video_path="raw.mp4", key_features="k", pain_point="p", price_deal="")
    base.update(extra)
    return base


def test_render_request_defaults_match_todays_behaviour():
    req = RenderRequest(**_request())
    assert req.target_duration is None
    assert req.story_format == "classic"


@pytest.mark.parametrize("target, fmt, expected", [
    (25, "countdown", (25, "countdown")),
    ("35", "MYTH_BUSTER", (35, "myth_buster")),
    (31, "bogus", (None, "classic")),
    ("abc", None, (None, "classic")),
    (True, 42, (None, "classic")),
])
def test_render_request_validates_without_422(target, fmt, expected):
    req = RenderRequest(**_request(target_duration=target, story_format=fmt))
    assert (req.target_duration, req.story_format) == expected


def test_render_api_accepts_junk_values_without_422(monkeypatch):
    from fastapi.testclient import TestClient
    from scripts.api_server import app
    from scripts.auth import get_configured_api_key, API_KEY_HEADER

    captured = {}
    monkeypatch.setattr(api_render, "execute_render_job",
                        lambda job_id, req, job_scope=None: captured.setdefault("req", req))
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    monkeypatch.setattr(api_render.TaskManager, "create_task", Mock())
    key = get_configured_api_key()
    client = TestClient(app, headers={API_KEY_HEADER: key} if key else {})
    response = client.post("/api/render", json=_request(target_duration="ninety", story_format={"x": 1},
                                                        export_mp4=False))
    assert response.status_code == 200, response.text
    assert captured["req"].target_duration is None
    assert captured["req"].story_format == "classic"


def test_execute_render_job_forwards_both_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    for name in ("fail_task", "cancel_task", "complete_task"):
        monkeypatch.setattr(api_render.TaskManager, name, Mock())
    monkeypatch.setattr(api_render, "check_disk_space", lambda *_a: {"is_sufficient": True})
    run = Mock(return_value={"project_name": "p"})
    monkeypatch.setattr(api_render.TikTokAutoCutterPipeline, "run", run)
    render_jobs.create_job("h-forward")

    api_render.execute_render_job("h-forward", RenderRequest(**_request(
        raw_video_path=str(tmp_path / "raw.mp4"), target_duration=15, story_format="problem_reveal")))

    kwargs = run.call_args.kwargs
    assert kwargs["target_duration"] == 15
    assert kwargs["story_format"] == "problem_reveal"


def test_pipeline_run_puts_fields_on_the_context():
    from scripts import pipeline as pipeline_mod

    seen = {}

    def capture(ctx):
        seen["ctx"] = ctx

    stages = ("SourceResolutionStage", "ScriptStage", "VoiceStage", "SubtitleStage",
              "AudioMixStage", "ShotMatchingStage", "VideoAssemblyStage")
    with patch.multiple(pipeline_mod, **{name: SimpleNamespace(run=capture, sync_cut_bound_sfx=lambda ctx: False)
                                         for name in stages}):
        pipeline_mod.TikTokAutoCutterPipeline.run(
            product_name="P", raw_video_path="raw.mp4", target_duration=45, story_format="loop")
        assert (seen["ctx"].target_duration, seen["ctx"].story_format) == (45, "loop")

        pipeline_mod.TikTokAutoCutterPipeline.run(product_name="P", raw_video_path="raw.mp4")
        assert (seen["ctx"].target_duration, seen["ctx"].story_format) == (None, "classic")


# ----------------------------------------------------------------------
# Context -> script stage AI context
# ----------------------------------------------------------------------
def _run_script_stage(ctx):
    from scripts.stages.script_stage import ScriptStage

    generate = Mock(return_value={"lines": [{"text": "เปิดกล่องดูกัน", "sfx": None, "on_screen": ""}]})
    with patch("scripts.stages.script_stage.AIBridge.is_available", return_value=True), \
            patch("scripts.stages.script_stage.AIBridge.generate", generate):
        ScriptStage.run(ctx)
    return generate.call_args.args[1]


def test_script_stage_sends_target_and_format_from_context():
    ai_ctx = _run_script_stage(PipelineContext(product_name="P", raw_video_path="raw.mp4",
                                               target_duration=25, story_format="countdown"))
    assert ai_ctx["target_duration"] == 25
    assert ai_ctx["story_format"] == "countdown"


def test_script_stage_without_fields_keeps_todays_context():
    ai_ctx = _run_script_stage(PipelineContext(product_name="P", raw_video_path="raw.mp4"))
    assert "target_duration" not in ai_ctx
    assert ai_ctx["story_format"] == "classic"


def test_script_stage_tolerates_a_bad_value_set_after_construction():
    ctx = PipelineContext(product_name="P", raw_video_path="raw.mp4")
    ctx.target_duration, ctx.story_format = "junk", None
    ai_ctx = _run_script_stage(ctx)
    assert "target_duration" not in ai_ctx
    assert ai_ctx["story_format"] == "classic"


# ----------------------------------------------------------------------
# Fingerprints / old manifests
# ----------------------------------------------------------------------
def test_script_fingerprint_ignores_defaults_so_old_manifests_keep_reuse(isolated_manifest):
    project_name, project_dir, raw_video, manifest = _strict_project(isolated_manifest)
    assert "target_duration" not in manifest["render_params"]  # an old manifest

    inputs = _stage_payload_from_manifest(manifest, "script")["inputs"]
    assert "target_duration" not in inputs and "story_format" not in inputs

    ctx = _context_for(project_name, project_dir, raw_video, manifest)
    assert ctx.should_run("script") is False
    assert ctx.should_run("mix") is False


@pytest.mark.parametrize("override", [{"target_duration": 35}, {"story_format": "loop"}])
def test_changing_a_retention_control_makes_the_script_stale(isolated_manifest, override):
    project_name, project_dir, raw_video, manifest = _strict_project(isolated_manifest)
    ctx = _context_for(project_name, project_dir, raw_video, manifest, **override)
    assert ctx.should_run("script") is True


def test_persisted_retention_controls_are_reused_by_an_equal_reroll(isolated_manifest):
    project_name, project_dir, raw_video, manifest = _strict_project(isolated_manifest)
    params = {**manifest["render_params"], "target_duration": 35, "story_format": "loop"}
    manifest = ProjectManifest.save(project_name, render_params=params, target_duration=35, story_format="loop")
    manifest = ProjectManifest.save(project_name, incremental_render=pipeline_context.build_incremental_render_metadata(manifest))

    same = _context_for(project_name, project_dir, raw_video, manifest, target_duration=35, story_format="loop")
    assert same.should_run("script") is False
    cleared = _context_for(project_name, project_dir, raw_video, manifest)  # target cleared, format reset
    assert cleared.should_run("script") is True


# ----------------------------------------------------------------------
# Context -> manifest -> export registry metadata (render time)
# ----------------------------------------------------------------------
def _assembly_ctx(tmp_path, **extra):
    clips = [{"id": f"c{i}", "source_path": "dummy.mp4", "trim_start": 2 * i, "trim_end": 2 * i + 2,
              "duration": 2, "speed": 1, "transition_in": "cut"} for i in range(2)]
    ctx = PipelineContext(product_name="P", raw_video_path="dummy.mp4", project_name="h-plumbing",
                          export_mp4=True, style_preset="viral_punch", **extra)
    ctx.actual_clip_list = clips
    ctx.clip_list = clips
    ctx.transitions = ["cut"]
    ctx.total_duration = 4.0
    ctx.script_data = {"hook": "เปิดกล่องดูกัน", "lines": [{"text": "เปิดกล่องดูกัน"}]}
    return ctx


def _run_assembly(ctx, tmp_path):
    from scripts.stages import video_assembly_stage as vas

    ensure = Mock(return_value={"id": "exp_h"})
    with patch.object(vas, "EXPORTS_DIR", tmp_path / "exports"), \
            patch("scripts.pipeline.VideoEditor.assemble_tiktok_video"), \
            patch.object(vas.ExportRegistry, "ensure", ensure), \
            patch.object(vas.ProjectManifest, "save") as save:
        vas.VideoAssemblyStage.run(ctx)
    return ensure.call_args.kwargs, save.call_args.kwargs


def test_render_persists_fields_and_passes_style_metadata(tmp_path):
    ctx = _assembly_ctx(tmp_path, target_duration=25, story_format="countdown")
    ensure_kwargs, saved = _run_assembly(ctx, tmp_path)

    assert saved["target_duration"] == 25 and saved["story_format"] == "countdown"
    assert saved["render_params"]["target_duration"] == 25
    assert saved["render_params"]["story_format"] == "countdown"
    assert ensure_kwargs["style_metadata"] == {
        "style_preset": "viral_punch",
        "story_format": "countdown",
        "duration_sec": 4.0,
        "hook_text": "เปิดกล่องดูกัน",
    }

    # The persisted manifest feeds the registry's own extractor identically.
    from scripts.export_registry import style_metadata_from_manifest
    assert style_metadata_from_manifest(saved) == ensure_kwargs["style_metadata"]


def test_render_without_fields_writes_defaults_and_classic_metadata(tmp_path):
    ensure_kwargs, saved = _run_assembly(_assembly_ctx(tmp_path), tmp_path)
    assert saved["target_duration"] is None and saved["story_format"] == "classic"
    assert ensure_kwargs["style_metadata"]["story_format"] == "classic"


def test_render_metadata_keeps_hook_style_id_from_the_manifest(tmp_path):
    from scripts.stages.video_assembly_stage import render_style_metadata

    ctx = _assembly_ctx(tmp_path, story_format="loop")
    ctx.manifest = {"hook_style_id": "question_bold", "story_format": "classic", "duration_sec": 99,
                    "render_params": {"story_format": "classic"}}
    meta = render_style_metadata(ctx)
    assert meta["hook_style"] == "question_bold"
    assert meta["story_format"] == "loop"  # this render wins over the stored value
    assert meta["duration_sec"] == 4.0


def test_render_metadata_never_raises():
    from scripts.stages.video_assembly_stage import render_style_metadata

    assert render_style_metadata(SimpleNamespace(manifest=object())) == {}


# ----------------------------------------------------------------------
# Manifest persistence through the editor state + reroll paths
# ----------------------------------------------------------------------
@pytest.fixture
def phase1_client(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from scripts import api_phase1

    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(api_phase1, "_project_origin", lambda name: (None, None, None))
    app = FastAPI()
    app.include_router(api_phase1.router)
    return TestClient(app)


def test_project_state_persists_normalised_fields_at_both_levels(phase1_client):
    ProjectManifest.save("h-state", render_params={"style_preset": "viral_punch"})
    response = phase1_client.patch("/api/projects/h-state/state",
                                   json={"target_duration": "45", "story_format": "MYTH_BUSTER"})
    assert response.status_code == 200, response.text
    manifest = ProjectManifest.load("h-state")
    assert (manifest["target_duration"], manifest["story_format"]) == (45, "myth_buster")
    assert manifest["render_params"]["target_duration"] == 45
    assert manifest["render_params"]["story_format"] == "myth_buster"
    assert manifest["render_params"]["style_preset"] == "viral_punch"

    # Junk clears/resets silently; omitting keeps what is stored.
    phase1_client.patch("/api/projects/h-state/state", json={"target_duration": 99, "story_format": "nope"})
    manifest = ProjectManifest.load("h-state")
    assert (manifest["render_params"]["target_duration"], manifest["render_params"]["story_format"]) == (None, "classic")
    phase1_client.patch("/api/projects/h-state/state", json={"story_format": "loop"})
    phase1_client.patch("/api/projects/h-state/state", json={"hook_label": "x"})
    assert ProjectManifest.load("h-state")["render_params"]["story_format"] == "loop"


def test_project_state_normalises_fields_sent_inside_style(phase1_client):
    ProjectManifest.save("h-style", render_params={})
    phase1_client.patch("/api/projects/h-style/state", json={"style": {"story_format": "Countdown", "target_duration": 7}})
    params = ProjectManifest.load("h-style")["render_params"]
    assert (params["story_format"], params["target_duration"]) == ("countdown", None)


def test_project_state_without_fields_leaves_the_manifest_untouched(phase1_client):
    ProjectManifest.save("h-old", render_params={"style_preset": "viral_punch"})
    phase1_client.patch("/api/projects/h-old/state", json={"hook_label": "x"})
    manifest = ProjectManifest.load("h-old")
    assert "target_duration" not in manifest and "story_format" not in manifest
    assert "target_duration" not in manifest["render_params"]


@pytest.fixture
def reroll_env(tmp_path, monkeypatch):
    from scripts import product_store
    import scripts.pipeline as pipeline_mod

    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "03_Projects")
    calls = []
    monkeypatch.setattr(pipeline_mod.TikTokAutoCutterPipeline, "run",
                        classmethod(lambda cls, **kw: calls.append(kw) or {"project_name": kw["project_name"]}))
    return calls


def _reroll(project_name, overrides, render_params):
    from scripts.api_phase1 import _execute_reroll

    ProjectManifest.save(project_name, script_data={"lines": [{"text": "a"}]}, cues=[], micro_cues=[],
                         total_duration=5.0, render_params={"raw_video_path": "raw.mp4", **render_params})
    render_jobs.create_job(f"job-{project_name}")
    _execute_reroll(f"job-{project_name}", project_name, "script", overrides)


def test_reroll_reuses_persisted_fields(reroll_env):
    _reroll("h-reroll-1", {}, {"target_duration": 35, "story_format": "loop"})
    assert (reroll_env[-1]["target_duration"], reroll_env[-1]["story_format"]) == (35, "loop")


def test_reroll_of_an_old_manifest_uses_defaults(reroll_env):
    _reroll("h-reroll-2", {}, {})
    assert (reroll_env[-1]["target_duration"], reroll_env[-1]["story_format"]) == (None, "classic")


def test_reroll_override_can_clear_the_target(reroll_env):
    _reroll("h-reroll-3", {"target_duration": None, "story_format": "countdown"},
            {"target_duration": 35, "story_format": "loop"})
    assert (reroll_env[-1]["target_duration"], reroll_env[-1]["story_format"]) == (None, "countdown")


def test_trigger_reroll_normalises_sent_fields_only(monkeypatch):
    from scripts import api_phase1

    req = api_phase1.RerollRequest(project_name="p", part="script", target_duration="25", story_format="nope")
    assert api_phase1._retention_controls(req.model_fields_set, req) == {"target_duration": 25, "story_format": "classic"}
    untouched = api_phase1.RerollRequest(project_name="p", part="script")
    assert api_phase1._retention_controls(untouched.model_fields_set, untouched) == {}


# ----------------------------------------------------------------------
# Cut times -> SFX mix
# ----------------------------------------------------------------------
def test_clip_cut_times_follow_the_render_frame_grid():
    clips = [
        {"trim_start": 0.0, "trim_end": 2.0},
        {"trim_start": 5.0, "trim_end": 7.0, "speed": 2.0, "freeze_tail": 0.5},  # 1.0 + 0.5 hold
        {"duration": 1.234},
    ]
    assert clip_cut_times(clips) == [2.0, pytest.approx(3.5)]
    # A transition counts at the midpoint of its overlap.
    faded = deepcopy(clips)
    faded[1].update(transition_in="fade", transition_duration=0.4)
    assert clip_cut_times(faded) == [pytest.approx(1.8), pytest.approx(3.1)]
    # The instants sit on the 1/30 s grid.
    odd = [{"trim_start": 0, "trim_end": 1.01}, {"trim_start": 0, "trim_end": 1.0}]
    assert clip_cut_times(odd) == [pytest.approx(30 / 30)]


@pytest.mark.parametrize("clips", [None, [], [{"trim_start": 0, "trim_end": 1}], [{"trim_start": 0, "trim_end": 1}, {"source_path": "x"}]])
def test_clip_cut_times_empty_when_unknown(clips):
    assert clip_cut_times(clips) == []


@pytest.fixture
def sfx_files(tmp_path, monkeypatch):
    """whoosh / pop / boom resolve to real tmp files; ffmpeg never runs."""
    files = {}
    for name in ("whoosh", "pop", "boom"):
        path = tmp_path / "sfx" / f"{name}.wav"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"RIFF")
        files[name] = path
    monkeypatch.setattr(SFXManager, "resolve", classmethod(lambda cls, name: files.get(name)))
    return files


# A pop at 0.0 (opener, so no boom), a whoosh at 2.0 sitting right on the
# 2.0 cut but only 1.0 s after a pop at 1.0 -- the 2 s gap drops it unless it
# is bound to the cut.
CUES = [
    {"start": 0.0, "end": 1.0, "text": "a", "sfx": "pop"},
    {"start": 1.0, "end": 2.0, "text": "b", "sfx": "pop"},
    {"start": 2.0, "end": 3.0, "text": "c", "sfx": "whoosh"},
    {"start": 3.0, "end": 4.0, "text": "d"},
]
CLIPS = [{"id": "c0", "trim_start": 0.0, "trim_end": 2.0}, {"id": "c1", "trim_start": 0.0, "trim_end": 2.0}]


def test_cut_bound_plan_only_reports_a_real_difference(sfx_files):
    plan = cut_bound_sfx_plan(CUES, [], 4.0, [2.0])
    assert ["cue", 2] in plan
    assert cut_bound_sfx_plan(CUES, [], 4.0, [3.0]) is None   # no whoosh near this cut
    assert cut_bound_sfx_plan(CUES, [], 4.0, []) is None
    assert cut_bound_sfx_plan(CUES, [], 4.0, [2.0], base_cut_times=[2.0]) is None


def _mix_ctx(tmp_path, **extra):
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")
    project_dir = tmp_path / "proj"
    project_dir.mkdir(exist_ok=True)
    values = dict(product_name="P", raw_video_path="raw.mp4", project_dir=project_dir, export_mp4=True,
                  total_duration=4.0, voice_audio_path=voice, micro_cues=deepcopy(CUES))
    values.update(extra)
    return PipelineContext(**values)


def test_mix_passes_cut_times_when_clips_exist(sfx_files, tmp_path):
    ctx = _mix_ctx(tmp_path, clip_list=deepcopy(CLIPS))
    with patch("scripts.pipeline.SFXManager.mix_audio_track") as mix:
        AudioMixStage.run(ctx)
    assert mix.call_args.kwargs["cut_times"] == [2.0]
    assert ctx.mix_request["cut_times"] == [2.0]


def test_mix_without_clips_keeps_todays_call(sfx_files, tmp_path):
    ctx = _mix_ctx(tmp_path)
    with patch("scripts.pipeline.SFXManager.mix_audio_track") as mix:
        AudioMixStage.run(ctx)
    assert "cut_times" not in mix.call_args.kwargs


def test_real_mix_keeps_the_cut_bound_whoosh(sfx_files, tmp_path, monkeypatch):
    """End to end through mix_audio_track's planner (ffmpeg faked)."""
    from scripts import sfx_manager as sfx_module

    commands = []
    monkeypatch.setattr(SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    monkeypatch.setattr(sfx_module.subprocess, "run",
                        lambda command, **kw: commands.append(command) or SimpleNamespace(returncode=0, stderr=""))
    before = SFXManager.last_mix_status
    try:
        AudioMixStage.run(_mix_ctx(tmp_path))
        without = " ".join(map(str, commands[-1]))
        AudioMixStage.run(_mix_ctx(tmp_path, clip_list=deepcopy(CLIPS)))
        with_cuts = " ".join(map(str, commands[-1]))
    finally:
        SFXManager.last_mix_status = before
    assert str(sfx_files["whoosh"]) not in without
    assert str(sfx_files["whoosh"]) in with_cuts


def test_generated_clips_trigger_one_remix_only_when_the_plan_changes(sfx_files, tmp_path):
    ctx = _mix_ctx(tmp_path)  # no clips yet: a fresh render
    with patch("scripts.pipeline.SFXManager.mix_audio_track") as mix:
        AudioMixStage.run(ctx)
        assert "cut_times" not in mix.call_args.kwargs

        ctx.actual_clip_list = deepcopy(CLIPS)  # ShotMatchingStage put a cut on the whoosh
        assert AudioMixStage.sync_cut_bound_sfx(ctx) is True
        assert mix.call_count == 2
        assert mix.call_args.kwargs["cut_times"] == [2.0]
        assert mix.call_args.kwargs["output_audio_path"] == ctx.result_paths["mixed_audio"]

        # Same cuts again -> nothing to do.
        assert AudioMixStage.sync_cut_bound_sfx(ctx) is False
        assert mix.call_count == 2


def test_cuts_that_do_not_change_the_plan_never_remix(sfx_files, tmp_path):
    ctx = _mix_ctx(tmp_path)
    with patch("scripts.pipeline.SFXManager.mix_audio_track") as mix:
        AudioMixStage.run(ctx)
        ctx.actual_clip_list = [{"trim_start": 0, "trim_end": 3.0}, {"trim_start": 0, "trim_end": 1.0}]
        assert AudioMixStage.sync_cut_bound_sfx(ctx) is False
    assert mix.call_count == 1


def test_reused_mix_is_never_remixed(sfx_files, tmp_path):
    ctx = _mix_ctx(tmp_path, export_mp4=False)  # mix skipped -> no mix_request
    with patch("scripts.pipeline.SFXManager.mix_audio_track") as mix:
        AudioMixStage.run(ctx)
        ctx.actual_clip_list = deepcopy(CLIPS)
        assert AudioMixStage.sync_cut_bound_sfx(ctx) is False
    mix.assert_not_called()


def test_mix_fingerprint_gains_cut_key_only_when_it_matters(sfx_files):
    base = {"micro_cues": CUES, "total_duration": 4.0, "overlays": [], "render_params": {}}
    assert "cut_bound_sfx" not in _stage_payload_from_manifest(base, "mix")["inputs"]
    far = {**base, "clip_list": [{"trim_start": 0, "trim_end": 3.0}, {"trim_start": 0, "trim_end": 1.0}]}
    assert "cut_bound_sfx" not in _stage_payload_from_manifest(far, "mix")["inputs"]
    on_cut = {**base, "clip_list": deepcopy(CLIPS)}
    assert ["cue", 2] in _stage_payload_from_manifest(on_cut, "mix")["inputs"]["cut_bound_sfx"]


# ----------------------------------------------------------------------
# HyperFrames: style metadata at finalize / render registration
# ----------------------------------------------------------------------
def test_hyperframes_style_metadata_from_angle_inputs_and_duration():
    from scripts.hyperframes_finalize import hyperframes_style_metadata

    meta = hyperframes_style_metadata({"hook_headline": "ร้อนแค่ไหนก็ไม่กลัว", "story_format": "loop"},
                                      {"style_preset": "couple_paper_chat"}, 21.5)
    assert meta == {"style_preset": "couple_paper_chat", "story_format": "loop",
                    "duration_sec": 21.5, "hook_text": "ร้อนแค่ไหนก็ไม่กลัว"}
    assert hyperframes_style_metadata(None) == {"story_format": "classic"}
    assert hyperframes_style_metadata("junk", 5, "x") == {"story_format": "classic"}


def test_hyperframes_finalize_registers_style_metadata(hf_context):
    finalizer, jobs, _, products, registry, row, _ = hf_context
    products.product["angles"][0]["hook_headline"] = "เย็นทันทีที่เปิด"
    with jobs.table.mutate() as rows:
        rows[0]["source_angle_snapshot"]["hook_headline"] = "เย็นทันทีที่เปิด"
        rows[0]["artifact"]["specs"] = {"duration": 19.97}
        rows[0]["inputs"] = {"story_format": "countdown"}

    result = hf_finish(hf_context, caption="c", hashtags=[], tiktok_product_id="basket")

    assert result["status"] == "finalized"
    assert registry.rows[0]["style_metadata"] == {
        "story_format": "countdown", "duration_sec": 19.97, "hook_text": "เย็นทันทีที่เปิด",
    }
