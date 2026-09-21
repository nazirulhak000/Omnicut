import json
from pathlib import Path

import pytest

from scripts import gadget_media_narration, gadget_media_renderer, render_jobs
from scripts.gadget_media_paths import (
    GadgetMediaPathError,
    GadgetMediaRoots,
    contained_path,
)
from scripts.gadget_media_project import (
    ProductVideoProject,
    ProductVideoValidationError,
)
from scripts.gadget_media_quality import validate_product_video
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.gadget_media_timeline_adapter import GadgetMediaTimelineAdapter


def _complete_project(project_id="gadget-project-001"):
    project = ProductVideoProject(
        project_id=project_id,
        product_identity={"brand": "Xiaomi", "model": "Test Phone", "category": "Smartphone"},
        audience="คนที่กำลังเลือกมือถือ",
        editorial_promise="สรุปจุดเด่นและข้อจำกัดก่อนซื้อ",
        status="review_required",
        presentation={"mode": "product_only", "voice": ""},
        source_assets=[{
            "source_id": "source-001",
            "local_path": "01_Raw/GadgetMedia/test/source.mp4",
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "duration": 90,
            "rights_reviewed": True,
            "rights_basis": "licensed_press_kit",
            "upscaled": False,
            "product_key": "xiaomi test phone",
        }],
        facts=[
            {"fact_id": "fact-001", "type": "brand_claim", "text": "จอ 120 Hz", "evidence_refs": ["source-001"]},
            {"fact_id": "fact-002", "type": "caveat", "text": "ไม่มีช่องหูฟัง", "evidence_refs": ["source-001"]},
        ],
        story={"blocks": [
            {"block_id": "block-hook", "role": "hook", "text": "มือถือรุ่นนี้เหมาะกับใคร", "claim_ids": ["fact-001"], "evidence_ids": ["source-001"]},
            {"block_id": "block-reveal", "role": "product_reveal", "text": "นี่คือ Test Phone", "claim_ids": [], "evidence_ids": ["source-001"]},
            {"block_id": "block-benefit", "role": "hero_benefit", "text": "จอลื่น", "claim_ids": ["fact-001"], "evidence_ids": ["source-001"]},
            {"block_id": "block-proof", "role": "proof", "text": "ดูการเลื่อนหน้าจอ", "claim_ids": ["fact-001"], "evidence_ids": ["source-001"]},
            {"block_id": "block-caveat", "role": "caveat", "text": "ต้องใช้หูฟัง USB-C", "claim_ids": ["fact-002"], "evidence_ids": ["source-001"]},
            {"block_id": "block-verdict", "role": "verdict", "text": "เหมาะกับคนชอบจอลื่น", "claim_ids": [], "evidence_ids": ["source-001"]},
        ]},
        edit={
            "parity_verified": True,
            "edl": {"shots": [
                {"shot_id": "shot-001", "source_id": "source-001", "story_block_id": "block-hook", "source_start": 0, "source_end": 10},
                {"shot_id": "shot-002", "source_id": "source-001", "story_block_id": "block-benefit", "source_start": 10, "source_end": 20},
                {"shot_id": "shot-003", "source_id": "source-001", "story_block_id": "block-proof", "source_start": 20, "source_end": 30},
                {"shot_id": "shot-004", "source_id": "source-001", "story_block_id": "block-caveat", "source_start": 30, "source_end": 40},
                {"shot_id": "shot-005", "source_id": "source-001", "story_block_id": "block-verdict", "source_start": 40, "source_end": 50},
            ]},
        },
    )
    project.validate()
    return project


def test_paths_reject_absolute_and_traversal(tmp_path):
    roots = GadgetMediaRoots.under(tmp_path)
    with pytest.raises(GadgetMediaPathError):
        contained_path(roots.projects, "..", "escape")
    with pytest.raises(GadgetMediaPathError):
        roots.project_dir("../escape")
    assert roots.project_dir("valid-project") == (roots.projects / "valid-project").resolve()


def test_repository_creates_only_the_gadget_media_namespace(tmp_path):
    roots = GadgetMediaRoots.under(tmp_path)
    repository = GadgetMediaRepository(roots)
    project = repository.create(
        {"brand": "Xiaomi", "model": "14T", "category": "Smartphone", "variant": ""},
        project_id="xiaomi-14t-project",
    )

    project_dir = roots.projects / project.project_id
    assert (project_dir / "project.json").is_file()
    assert (project_dir / "sources.json").is_file()
    assert (project_dir / "media" / "proxy").is_dir()
    assert (roots.exports / project.project_id).is_dir()
    assert not (tmp_path / "03_Projects" / project.project_id).exists()
    index = json.loads((roots.docs / "project_index.json").read_text(encoding="utf-8"))
    assert [item["project_id"] for item in index["projects"]] == [project.project_id]


def test_state_machine_rejects_skipping_required_states():
    project = ProductVideoProject(
        project_id="state-project",
        product_identity={"brand": "Xiaomi", "model": "14T"},
    )
    with pytest.raises(ProductVideoValidationError, match="invalid status transition"):
        project.transition_to("approved")
    project.transition_to("sourcing")
    assert project.status == "sourcing"


def test_timeline_adapter_keeps_source_story_and_evidence_traceability():
    project = _complete_project()
    timeline = GadgetMediaTimelineAdapter.build(project)

    assert timeline["workspace_scope"] == "gadget_media"
    assert timeline["project_id"] == project.project_id
    assert timeline["duration"] == 50
    assert timeline["clips"][0]["source_id"] == "source-001"
    assert timeline["clips"][0]["story_block_id"] == "block-hook"
    assert timeline["clips"][0]["evidence_ids"] == ["source-001"]


def test_quality_gate_requires_native_rights_evidence_duration_and_parity():
    project = _complete_project()
    timeline = GadgetMediaTimelineAdapter.build(project)
    report = validate_product_video(project, timeline)
    assert report["passed"] is True
    assert report["duration"] == 50

    project.source_assets[0]["width"] = 640
    project.source_assets[0]["height"] = 360
    failed = validate_product_video(project, timeline)
    assert failed["passed"] is False
    assert "native_source" in {item["id"] for item in failed["blockers"]}


def test_quality_gate_requires_project_audio_for_voice_modes(tmp_path):
    project = _complete_project()
    timeline = GadgetMediaTimelineAdapter.build(project)
    project.presentation = {"mode": "gemini_tts", "voice": "gemini_puck_male_hype"}
    failed = validate_product_video(project, timeline, project_root=tmp_path)
    assert "audio" in {item["id"] for item in failed["blockers"]}

    voice = tmp_path / "audio" / "voice" / "narration.wav"
    voice.parent.mkdir(parents=True)
    voice.write_bytes(b"wav")
    project.presentation["audio_path"] = str(voice)
    passed = validate_product_video(project, timeline, project_root=tmp_path)
    assert "audio" not in {item["id"] for item in passed["blockers"]}


def test_repository_allows_many_renders_but_only_one_approved_master(tmp_path):
    repository = GadgetMediaRepository(GadgetMediaRoots.under(tmp_path))
    project = repository.create(
        {"brand": "Xiaomi", "model": "14T"},
        project_id="approval-project",
    )
    project.status = "ready_to_render"
    repository.save(project)
    first = repository.add_render_artifact(project.project_id, {
        "artifact_id": "render-one", "kind": "render", "path": "one.mp4", "approved": False,
    })
    second = repository.add_render_artifact(project.project_id, {
        "artifact_id": "render-two", "kind": "render", "path": "two.mp4", "approved": False,
    })
    assert len(second.artifacts) == 2

    approved = repository.approve_render(project.project_id, "render-two")
    assert approved.approved_master_id == "render-two"
    assert sum(bool(item.get("approved")) for item in approved.artifacts) == 1
    reapproved = repository.approve_render(project.project_id, "render-one")
    assert reapproved.approved_master_id == "render-one"
    assert sum(bool(item.get("approved")) for item in reapproved.artifacts) == 1


def test_gemini_narration_is_versioned_and_attached_to_project(tmp_path, monkeypatch):
    repository = GadgetMediaRepository(GadgetMediaRoots.under(tmp_path))
    project = repository.create(
        {"brand": "Xiaomi", "model": "14T"},
        presentation={"mode": "gemini_tts", "voice": "gemini_puck_male_hype"},
        project_id="narration-project",
    )
    project.story = {"blocks": [{"block_id": "hook", "role": "hook", "text": "มือถือรุ่นนี้...น่าสนใจ"}]}
    repository.save(project)

    def fake_generate(**kwargs):
        Path(kwargs["output_path"]).write_bytes(b"fake-wave")
        return kwargs["output_path"]

    monkeypatch.setattr(gadget_media_narration.GeminiFlashTTSEngine, "generate_speech", fake_generate)
    monkeypatch.setattr(gadget_media_narration, "measure_wav_duration", lambda _path: 48.5)
    job_id = "narration-job"
    render_jobs.create_job(job_id)
    gadget_media_narration.execute_gadget_media_narration(job_id, project.project_id, repository)

    job = render_jobs.get_job(job_id)
    saved = repository.get(project.project_id)
    assert job["status"] == "completed"
    assert Path(saved.presentation["audio_path"]).name == "gemini_narration_v01.wav"
    assert saved.presentation["audio_duration"] == 48.5
    assert "..." not in gadget_media_narration.project_narration_text(saved)


def test_renderer_registers_scoped_master_after_success(tmp_path, monkeypatch):
    repository = GadgetMediaRepository(GadgetMediaRoots.under(tmp_path))
    project = _complete_project("render-project")
    source = repository.roots.raw_dir(project.project_id) / "original" / "source.mp4"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake-video")
    project.source_assets[0]["local_path"] = str(source)
    project.status = "ready_to_render"
    project.quality_report = {"passed": True}
    repository.save(project)
    timeline = GadgetMediaTimelineAdapter.build(project)
    repository.save_timeline(project.project_id, timeline)

    fake_audio = repository.roots.project_layout(project.project_id)["mix"] / "fake.wav"
    fake_audio.write_bytes(b"fake-audio")
    monkeypatch.setattr(gadget_media_renderer, "_prepare_audio", lambda *_args, **_kwargs: fake_audio)

    def fake_assemble(**kwargs):
        Path(kwargs["output_mp4_path"]).write_bytes(b"fake-mp4")

    monkeypatch.setattr(gadget_media_renderer.VideoEditor, "assemble_tiktok_video", fake_assemble)
    job_id = "render-job"
    render_jobs.create_job(job_id)
    gadget_media_renderer.execute_gadget_media_render(job_id, project.project_id, repository)

    job = render_jobs.get_job(job_id)
    saved = repository.get(project.project_id)
    artifact = saved.artifacts[0]
    assert job["status"] == "completed"
    assert saved.status == "rendered"
    assert Path(artifact["path"]).parent == repository.roots.export_dir(project.project_id)
    assert Path(artifact["path"]).is_file()
