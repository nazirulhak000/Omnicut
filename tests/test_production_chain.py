"""Production chain (scripts/production_chain.py): two server-side chains per product.

Offline: TTS, the Gemini scene scan and the render pipeline are replaced by
fakes that record what they were asked to do. What is checked here is the
order of the steps, where the chain stops, what it leaves alone, and that a
chain render hands the pipeline the same arguments as the Editor's own Render.
"""
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import api_phase1, product_store, production_chain, project_manifest, render_jobs
from scripts.api_server import app
from scripts.batch_render import BatchRenderManager
from scripts.gemini_vision_matcher import GeminiVisionMatcher
from scripts.product_store import ProductStore
from scripts.project_manifest import ProjectManifest
from scripts.shot_lists_store import ShotListsStore
from scripts.task_manager import TaskManager
from scripts.video_editor import VideoEditor

client = TestClient(app)


@pytest.fixture(autouse=True)
def chain_env(tmp_path, monkeypatch):
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    projects = tmp_path / "03_Projects"
    projects.mkdir(exist_ok=True)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", projects)
    stickers = tmp_path / "stickers"
    stickers.mkdir()
    monkeypatch.setattr(api_phase1, "STICKERS_DIR", stickers)
    monkeypatch.setattr(api_phase1, "ensure_default_cover", lambda *args, **kwargs: None)
    monkeypatch.setattr(production_chain, "POLL_SECONDS", 0.01)
    monkeypatch.setattr(production_chain, "_ACTIVE", {})
    return tmp_path


def _angle(angle_id, **extra):
    return {"angle_id": angle_id, "hook_title": f"ฮุก {angle_id}", "batch": 1,
            "script_lines": ["บรรทัดหนึ่ง", "บรรทัดสอง"], **extra}


def _draft_project(product_id, angle_id, project, **render_params):
    ProjectManifest.save(
        project,
        script_data={"lines": [{"text": "a"}]},
        cues=[], micro_cues=[], total_duration=5.0,
        render_params={"raw_video_path": "nope.mp4", "product_id": product_id, "angle_id": angle_id,
                       **render_params},
    )


def _write_export(project):
    """The file and manifest entry a finished render leaves behind."""
    rel = f"04_Exports/Ready_to_post/{project}_20261112.mp4"
    target = product_store.BASE_DIR / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\x00" * 64)
    ProjectManifest.save(project, artifacts={"mp4_video": {"path": rel}})
    return rel


def _product(angles, drafts=None, **fields):
    """A product whose angles are in the given state.

    The store reconciles angles with what is on disk every time it is read: a
    draft without its project goes back to "scripted", a "rendered" clip
    without its export goes back to "in_production". So the projects (and
    exports) are written first, as they would exist in real use.
    """
    product = ProductStore.add(name="พัดลมทดสอบ", url="https://x.test/fan")
    pid = product["id"]
    for angle in angles:
        project = angle.get("project_name")
        if not project:
            continue
        _draft_project(pid, angle["angle_id"], project, **((drafts or {}).get(project) or {}))
        if angle.get("status") == "rendered":
            _write_export(project)
    ProductStore.update(pid, angles=angles, **fields)
    return ProductStore.get(pid)


def _run(product_id, kind, **kwargs):
    task = production_chain.start_chain(product_id, kind, background=False, **kwargs)
    return TaskManager.get_task(task["id"])


def _run_through_route(product_id, kind):
    """Start a chain the way the button does and wait for it to end."""
    started = client.post(f"/api/products/{product_id}/production-chain", json={"kind": kind})
    assert started.status_code == 200, started.text
    task_id = started.json()["task_id"]
    assert _wait_until(lambda: TaskManager.get_task(task_id)["status"] in ("completed", "failed", "cancelled"), 10.0)
    return TaskManager.get_task(task_id)


def _wait_until(check, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check():
            return True
        time.sleep(0.01)
    return False


# ─── Chain: draft ─────────────────────────────────────────────────────────────

@pytest.fixture
def draft_fakes(tmp_path, monkeypatch):
    """Fake voice, scan and draft workers that write to one shared event log."""
    events = []
    state = {"cached": set(), "fallback": set(), "batches": {}}

    def fake_voice(product_id, angle_id, overrides, batch=None, **kwargs):
        events.append(("voice", angle_id))
        audio = tmp_path / f"voice_{angle_id}.wav"
        audio.write_bytes(b"RIFF....WAVEfmt ")
        ShotListsStore.upsert({
            "product_id": product_id, "angle_id": angle_id, "voice_audio_path": str(audio),
            "custom_script": "บรรทัดหนึ่ง\nบรรทัดสอง",
            "voice_params": {"voice_preset": overrides["voice_preset"], "voice_engine_type": "gemini_tts"},
        }, batch=batch)
        return {"success": True}

    monkeypatch.setattr("scripts.api_shot_lists.generate_shot_list_for_angle", fake_voice)

    monkeypatch.setattr(GeminiVisionMatcher, "get_cached_catalog",
                        classmethod(lambda cls, path, *a, **k: {"scenes": [{}]} if Path(path).name in state["cached"] else None))

    def fake_index(cls, raw_video_path, raw_duration, force=False, **kwargs):
        name = Path(raw_video_path).name
        events.append(("scan", name))
        if name in state["fallback"]:
            return {"indexed_by": "heuristic_fallback", "fallback_reason": "no_response", "scenes": [{}]}
        return {"scenes": [{"label": "hero"}, {"label": "detail"}], "summary": "ok"}

    monkeypatch.setattr(GeminiVisionMatcher, "index_raw_video_catalog", classmethod(fake_index))
    monkeypatch.setattr(VideoEditor, "get_media_info", staticmethod(lambda path: {"duration": 12.0}))

    def fake_create_batch(product_id, angle_ids=None, options=None, **kwargs):
        events.append(("draft", tuple(angle_ids or [])))
        batch_id = f"batch_{len(state['batches']) + 1}"
        state["batches"][batch_id] = {
            "batch_id": batch_id, "status": "completed", "options": options,
            "items": [{"angle_id": a, "angle_name": a, "batch": options.get("batch_index"),
                       "status": "draft_ready", "project_name": f"proj_{a}"} for a in angle_ids],
        }
        return state["batches"][batch_id]

    monkeypatch.setattr(BatchRenderManager, "create_batch", classmethod(
        lambda cls, product_id, angle_ids=None, options=None, **kw: fake_create_batch(product_id, angle_ids, options, **kw)))
    monkeypatch.setattr(BatchRenderManager, "get_batch",
                        classmethod(lambda cls, batch_id, **kw: state["batches"].get(batch_id)))
    return events, state


def _clip(tmp_path, name):
    clip = tmp_path / name
    clip.write_bytes(b"\x00" * 32)
    return str(clip)


def test_draft_chain_runs_voice_then_scan_then_drafts(draft_fakes, tmp_path):
    events, state = draft_fakes
    product = _product([_angle("a1"), _angle("a2")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    task = _run(product["id"], "draft", batch_index=1, voice_preset="gemini_puck_male_hype")

    assert [e[0] for e in events] == ["voice", "voice", "scan", "draft"]
    assert events[-1] == ("draft", ("a1", "a2"))
    assert task["status"] == "completed"
    result = task["result"]
    assert result["voice"]["generated"] == 2 and result["voice"]["missing"] == []
    assert result["scan"]["scanned"] == 1
    assert [d["project_name"] for d in result["drafts"]["created"]] == ["proj_a1", "proj_a2"]
    options = state["batches"]["batch_1"]["options"]
    assert options["export_mp4"] is False
    assert options["batch_index"] == 1
    assert options["voice_preset"] == "gemini_puck_male_hype"


def test_draft_chain_stops_when_a_clip_could_not_be_analysed(draft_fakes, tmp_path):
    events, state = draft_fakes
    state["fallback"].add("raw2.mp4")
    product = _product([_angle("a1")],
                       default_videos=[_clip(tmp_path, "raw1.mp4"), _clip(tmp_path, "raw2.mp4")])

    task = _run(product["id"], "draft")

    assert [e[0] for e in events] == ["voice", "scan", "scan"], "no draft may be built after a failed scan"
    assert task["status"] == "failed"
    assert "สแกนฉาก" in task["error"] and "Gemini ไม่ตอบกลับ" in task["error"]


def test_draft_chain_leaves_existing_drafts_and_finished_clips_alone(draft_fakes, tmp_path):
    events, _ = draft_fakes
    product = _product([
        _angle("has_draft", status="in_production", project_name="proj_old"),
        _angle("posted", status="posted"),
        _angle("no_script", script_lines=[]),
        _angle("fresh"),
    ])
    task = _run(product["id"], "draft")

    assert events == [("voice", "fresh"), ("draft", ("fresh",))]
    assert task["status"] == "completed"
    assert task["result"]["scan"]["videos"] == 0, "a product without footage has nothing to scan"


def test_draft_chain_with_nothing_to_produce_completes_without_calling_a_worker(draft_fakes):
    events, _ = draft_fakes
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")])

    task = _run(product["id"], "draft")

    assert events == []
    assert task["status"] == "completed"
    assert task["result"]["drafts"]["created"] == []


def test_draft_chain_does_not_rescan_catalogued_footage(draft_fakes, tmp_path):
    events, state = draft_fakes
    state["cached"].add("raw1.mp4")
    product = _product([_angle("a1")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    task = _run(product["id"], "draft")

    assert [e[0] for e in events] == ["voice", "draft"]
    assert task["status"] == "completed"


def test_draft_chain_only_drafts_angles_that_got_a_voice(draft_fakes, monkeypatch):
    events, _ = draft_fakes
    original = sys.modules["scripts.api_shot_lists"].generate_shot_list_for_angle

    def voice_fails_for_a2(product_id, angle_id, overrides, batch=None, **kwargs):
        if angle_id == "a2":
            raise RuntimeError("TTS ล้ม")
        return original(product_id, angle_id, overrides, batch=batch, **kwargs)

    monkeypatch.setattr("scripts.api_shot_lists.generate_shot_list_for_angle", voice_fails_for_a2)
    product = _product([_angle("a1"), _angle("a2")])

    task = _run(product["id"], "draft")

    assert events[-1] == ("draft", ("a1",))
    assert task["status"] == "completed"
    assert [m["angle_id"] for m in task["result"]["voice"]["missing"]] == ["a2"]


def test_draft_chain_groups_drafts_by_lot(draft_fakes):
    events, _ = draft_fakes
    product = _product([_angle("a1"), _angle("a1", batch=2)])

    task = _run(product["id"], "draft")

    assert [e for e in events if e[0] == "draft"] == [("draft", ("a1",)), ("draft", ("a1",))]
    assert sorted(d["batch"] for d in task["result"]["drafts"]["created"]) == [1, 2]


# ─── Chain: render ────────────────────────────────────────────────────────────

@pytest.fixture
def fake_pipeline(tmp_path, monkeypatch):
    """Records every pipeline.run call; writes the export the real one would."""
    calls = []
    behaviour = {}

    def fake_run(cls, **kwargs):
        calls.append(kwargs)
        project = kwargs["project_name"]
        action = behaviour.get(project)
        if action:
            action(kwargs)
        return {"mp4_video": _write_export(project), "project_name": project, "clip_list": []}

    import scripts.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod.TikTokAutoCutterPipeline, "run", classmethod(fake_run))
    return calls, behaviour


def _status(product_id, angle_id):
    product = ProductStore.get(product_id)
    return next(a for a in product["angles"] if a["angle_id"] == angle_id)["status"]


def test_render_chain_renders_reviewed_drafts_and_reports_the_rest(fake_pipeline):
    calls, behaviour = fake_pipeline
    product = _product([
        _angle("ok", status="in_production", project_name="proj_ok"),
        _angle("cutout", status="in_production", project_name="proj_cutout"),
        _angle("broken", status="in_production", project_name="proj_broken"),
        _angle("scripted"),
        _angle("done", status="rendered", project_name="proj_done"),
    ], drafts={"proj_cutout": {"background_isolation": {"enabled": True, "scope_mode": "behind_text_windows"}}})
    pid = product["id"]

    def explode(kwargs):
        raise RuntimeError("ffmpeg ล้ม")
    behaviour["proj_broken"] = explode

    task = _run(pid, "render")

    assert sorted(c["project_name"] for c in calls) == ["proj_broken", "proj_ok"]
    assert all(c["resume_from"] == "mix" and c["export_mp4"] is True for c in calls)
    assert task["status"] == "completed"
    result = task["result"]
    assert [r["angle_id"] for r in result["rendered"]] == ["ok"]
    # The chain reports the render job's own message -- the one the Editor shows.
    assert [(f["angle_id"], f["error"]) for f in result["failed"]] == [
        ("broken", "การประมวลผลวิดีโอด้วย FFmpeg ขัดข้อง")]
    assert {s["angle_id"]: s["reason"] for s in result["skipped"]} == {
        "cutout": "ใช้ Cutout เฉพาะช่วงข้อความ — เรนเดอร์จาก Editor",
    }
    assert _status(pid, "ok") == "rendered"
    assert _status(pid, "broken") == "in_production"


def test_render_plan_reports_a_draft_whose_project_is_gone():
    # The store normally reverts such an angle before the chain sees it; this
    # is the window where the project folder vanished after that read.
    product = {"id": "p1", "angles": [_angle("gone", status="in_production", project_name="proj_gone")]}

    plan = production_chain.plan_render(product, None)

    assert plan["ready"] == []
    assert [(s["angle_id"], s["reason"]) for s in plan["skipped"]] == [("gone", "ไม่พบโปรเจกต์ดราฟต์")]


def test_render_chain_that_rendered_nothing_fails_with_the_reason(fake_pipeline):
    _, behaviour = fake_pipeline
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")])

    def explode(kwargs):
        raise RuntimeError("ดิสก์เต็ม")
    behaviour["proj_a1"] = explode

    task = _run(product["id"], "render")

    assert task["status"] == "failed"
    assert "ดิสก์เต็ม" in task["error"]


def test_render_chain_with_no_reviewed_draft_completes_empty(fake_pipeline):
    calls, _ = fake_pipeline
    product = _product([_angle("a1")])

    task = _run(product["id"], "render")

    assert calls == []
    assert task["status"] == "completed"
    assert task["result"]["rendered"] == []


def test_render_chain_skips_a_project_that_is_already_rendering(fake_pipeline):
    calls, _ = fake_pipeline
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")])
    TaskManager.create_task(task_type="render_video", title="เรนเดอร์วิดีโอ: proj_a1",
                            payload={"project_name": "proj_a1"}, target_tab="editor", target_id="proj_a1")

    task = _run(product["id"], "render")

    assert calls == []
    assert task["status"] == "failed"
    assert "กำลังเรนเดอร์อยู่แล้ว" in task["error"]


def test_render_chain_waits_while_the_shared_render_queue_is_full(fake_pipeline, monkeypatch):
    calls, _ = fake_pipeline
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")])

    looks = []

    def queued_count():
        looks.append(len(calls))
        return render_jobs.MAX_QUEUED_RENDERS if len(looks) <= 3 else 0

    monkeypatch.setattr(render_jobs, "queued_count", queued_count)

    task = _run(product["id"], "render")

    assert task["status"] == "completed"
    assert len(looks) >= 4 and looks[:4] == [0, 0, 0, 0], "the render must not start while the queue is full"
    assert len(calls) == 1


def test_cancelling_the_chain_cancels_its_renders(fake_pipeline):
    calls, behaviour = fake_pipeline
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")])
    started = threading.Event()

    def wait_for_cancel(kwargs):
        started.set()
        assert kwargs["cancel_event"].wait(5.0), "the render was never told to stop"
        raise render_jobs.RenderCancelled()

    behaviour["proj_a1"] = wait_for_cancel

    task = production_chain.start_chain(product["id"], "render")
    assert started.wait(5.0)
    TaskManager.cancel_task(task["id"])

    assert _wait_until(lambda: (product["id"] in {k[1] for k in production_chain._ACTIVE}) is False)
    assert TaskManager.get_task(task["id"])["status"] == "cancelled"
    assert _status(product["id"], "a1") == "in_production"


# ─── Same render as the Editor ────────────────────────────────────────────────

# What the Editor holds for a reviewed draft: the clip plan it loaded (one clip
# trimmed by the owner), its style panel and its layers.
EDITOR_CLIPS = [
    {"source_path": "01_Raw/p/raw1.mp4", "start": 0.0, "end": 2.5, "timeline_start": 0.0,
     "speed": 1.0, "auto_generated": True},
    {"source_path": "01_Raw/p/raw1.mp4", "start": 4.0, "end": 7.25, "timeline_start": 2.5,
     "speed": 1.25, "auto_generated": True},
]
EDITOR_TRANSITIONS = [None, {"type": "fade", "duration": 0.3}]
EDITOR_OVERLAYS = [{"id": "ov1", "type": "image", "src": "02_Assets/x.png", "start": 1.0, "end": 3.0}]
EDITOR_STICKERS = [{"id": "st1", "name": "badge_new.png", "start": 0.5, "end": 2.0, "x": 0.2, "y": 0.3}]
EDITOR_EFFECTS = [{"id": "fx1", "type": "zoom_punch", "start": 1.0, "end": 1.4}]
EDITOR_SPOTLIGHT = {"enabled": True, "x": 0.5, "y": 0.4, "radius": 0.3}


def _editor_style(badge):
    """serializeStyle() in frontend/src/lib/editorProjectState.js."""
    return {
        "caption_scale": 1.1, "caption_position": "middle", "caption_color": "#FFE600",
        "font_name": "Mali", "bgm_name": "tiktok_upbeat_bgm.wav", "bgm_volume": 0.2, "bgm_ducking": False,
        "voice_volume": 1.0, "sfx_volume": 0.28, "lut_name": "warm.cube", "lut_intensity": 0.6,
        "sticker_badge": badge or None, "sticker_position": "top_left", "sticker_scale": 0.8,
        "show_watermark": False, "ghost_reveal": False, "reveal_color_sync": False,
        "bilingual_subtitles": False,
    }


def _editor_save_payload(badge):
    """editorStateToSavePayload(): what the Editor saves just before a render."""
    return {
        "cues": [], "micro_cues": [],
        "clip_list": [dict(c) for c in EDITOR_CLIPS],
        "transitions": EDITOR_TRANSITIONS,
        "style": _editor_style(badge),
        "stickers": EDITOR_STICKERS, "effects": EDITOR_EFFECTS, "spotlight": EDITOR_SPOTLIGHT,
        "overlays": EDITOR_OVERLAYS,
        "track_mix": {"voice": 1.0, "bgm": 0.2, "sfx": 0.28},
        "audio_mutes": {"bgm": False},
        "style_preset": "clean_tech_review",
    }


def _editor_render_payload(project, badge, part):
    """The startReroll() call of EditorShell.jsx's Render button."""
    style = _editor_style(badge)
    return {
        "project_name": project, "part": part,
        "clip_list": [dict(c) for c in EDITOR_CLIPS],
        "transitions": EDITOR_TRANSITIONS, "overlays": EDITOR_OVERLAYS,
        "bilingual_subtitles": style["bilingual_subtitles"], "ghost_reveal": style["ghost_reveal"],
        "reveal_color_sync": style["reveal_color_sync"], "show_watermark": style["show_watermark"],
        "font_name": style["font_name"], "bgm_name": style["bgm_name"], "lut_name": style["lut_name"],
        "sticker_badge": badge or "",
        "lut_intensity": style["lut_intensity"], "bgm_volume": style["bgm_volume"],
        "bgm_ducking": style["bgm_ducking"], "audio_mutes": {"bgm": False},
        "export_preset": "post", "style_preset": "clean_tech_review",
        "caption_position": style["caption_position"], "caption_color": style["caption_color"],
        "caption_scale": style["caption_scale"],
        "sticker_position": style["sticker_position"], "sticker_scale": style["sticker_scale"],
        "stickers": EDITOR_STICKERS, "effects": EDITOR_EFFECTS, "spotlight": EDITOR_SPOTLIGHT,
    }


def _comparable(kwargs):
    """pipeline.run arguments without the two that belong to one job."""
    kept = {k: v for k, v in kwargs.items() if k not in ("cancel_event", "progress_callback")}
    # auto_generated is bookkeeping for script/voice rerolls (api_phase1 decides
    # there whether to drop a clip plan); the renderer never reads it. The save
    # route clears it on a clip the owner changed, while the Editor's own
    # payload still carries the value it loaded.
    if isinstance(kept.get("clip_list"), list):
        kept["clip_list"] = [{k: v for k, v in clip.items() if k != "auto_generated"} for clip in kept["clip_list"]]
    return kept


@pytest.mark.parametrize("badge", ["badge_sale.png", ""], ids=["badge chosen", "badge cleared"])
def test_chain_render_gives_the_pipeline_what_the_editor_render_gives_it(fake_pipeline, badge):
    calls, _ = fake_pipeline
    (api_phase1.STICKERS_DIR / "badge_sale.png").write_bytes(b"png")
    (api_phase1.STICKERS_DIR / "badge_draft.png").write_bytes(b"png")
    # The draft as batch_render left it: its own clip plan, style and badge.
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")], drafts={"proj_a1": dict(
        product_name="พัดลมทดสอบ", custom_script="บรรทัดหนึ่ง\nบรรทัดสอง", voice_preset="gemini_fenrir_male_strong",
        style_preset="auto", font_name="IBMPlex", bgm_volume=0.12,
        sticker_path=str(api_phase1.STICKERS_DIR / "badge_draft.png"),
        clip_list=[{**EDITOR_CLIPS[0]}, {**EDITOR_CLIPS[1], "end": 9.0, "speed": 1.0}],
        hook_brand="HATARI", hook_duration=2.5,
    )})
    pid = product["id"]

    # 1 · the owner reviews the draft and the Editor saves it.
    saved = client.patch("/api/projects/proj_a1/state", json=_editor_save_payload(badge))
    assert saved.status_code == 200, saved.text

    # 2 · the chain renders it with the Editor closed.
    task = _run_through_route(pid, "render")
    assert task["status"] == "completed", task
    assert len(calls) == 1, "the chain render did not reach the pipeline"
    from_chain = _comparable(calls[0])
    assert _status(pid, "a1") == "rendered"

    # 3 · the same saved draft, rendered by the Editor's own Render button.
    started = client.post("/api/reroll", json=_editor_render_payload("proj_a1", badge, "bgm"))
    assert started.status_code == 200, started.text
    assert len(calls) == 2, "the Editor render did not reach the pipeline"
    from_editor = _comparable(calls[1])

    assert from_chain.keys() == from_editor.keys()
    different = {k: (from_editor[k], from_chain[k]) for k in from_editor if from_editor[k] != from_chain[k]}
    assert different == {}

    # The comparison must have been about the reviewed state, not the draft's.
    expected_badge = str(api_phase1.STICKERS_DIR / "badge_sale.png") if badge else ""
    assert from_chain["sticker_path"] == expected_badge
    assert from_chain["font_name"] == "Mali" and from_chain["caption_position"] == "middle"
    assert from_chain["clip_list"][1]["end"] == 7.25
    assert from_chain["stickers"] == EDITOR_STICKERS and from_chain["spotlight"] == EDITOR_SPOTLIGHT
    assert from_chain["resume_from"] == "mix" and from_chain["export_preset"] == "post"


def test_editor_render_without_audio_changes_differs_from_the_chain_only_in_the_stage(fake_pipeline):
    calls, _ = fake_pipeline
    product = _product([_angle("a1", status="in_production", project_name="proj_a1")],
                       drafts={"proj_a1": {"product_name": "พัดลมทดสอบ"}})
    pid = product["id"]

    assert client.patch("/api/projects/proj_a1/state", json=_editor_save_payload("")).status_code == 200
    assert _run_through_route(pid, "render")["status"] == "completed"
    assert client.post("/api/reroll", json=_editor_render_payload("proj_a1", "", "subtitles")).status_code == 200

    from_chain, from_editor = _comparable(calls[0]), _comparable(calls[1])
    different = {k for k in from_editor if from_editor[k] != from_chain[k]}
    assert different == {"resume_from"}
    assert (from_editor["resume_from"], from_chain["resume_from"]) == ("subtitles", "mix")


# ─── Route ────────────────────────────────────────────────────────────────────

def test_route_refuses_a_second_chain_for_the_same_product(monkeypatch):
    product = _product([_angle("a1")])
    release = threading.Event()

    def slow_chain(task_id, product_id, **kwargs):
        release.wait(5.0)
        return {"kind": "draft", "ok": True, "message": "จบ", "stopped_at": None}

    monkeypatch.setattr(production_chain, "run_draft_chain", slow_chain)
    url = f"/api/products/{product['id']}/production-chain"

    first = client.post(url, json={"kind": "draft", "batch_index": 1})
    assert first.status_code == 200, first.text
    task_id = first.json()["task_id"]
    assert first.json()["task"]["type"] == "production_chain"

    second = client.post(url, json={"kind": "render"})
    assert second.status_code == 409
    assert second.json()["detail"]["task_id"] == task_id

    release.set()
    assert _wait_until(lambda: TaskManager.get_task(task_id)["status"] == "completed")
    third = client.post(url, json={"kind": "draft"})
    assert third.status_code == 200, third.text
    assert _wait_until(lambda: TaskManager.get_task(third.json()["task_id"])["status"] == "completed")


def test_route_rejects_an_unknown_kind_and_an_unknown_product():
    product = _product([_angle("a1")])

    assert client.post(f"/api/products/{product['id']}/production-chain", json={"kind": "post"}).status_code == 400
    assert client.post("/api/products/no-such-product/production-chain", json={"kind": "draft"}).status_code == 404


# ─── Chain: full (draft then render, no review stop) ─────────────────────────

@pytest.fixture
def full_fakes(draft_fakes, fake_pipeline, monkeypatch):
    """The draft fakes, but a built draft leaves its project and angle state
    behind the way the real batch does, so the render stage can find it."""
    events, state = draft_fakes
    calls, behaviour = fake_pipeline
    state["draft_fails"] = set()
    built = BatchRenderManager.create_batch

    def create_batch(cls, product_id, angle_ids=None, options=None, **kwargs):
        batch = built(product_id, angle_ids=angle_ids, options=options, **kwargs)
        product = ProductStore.get(product_id)
        angles = product["angles"]
        for item in batch["items"]:
            if item["angle_id"] in state["draft_fails"]:
                item.update(status="failed", error="ไม่มีฉากพอ", project_name=None)
                continue
            _draft_project(product_id, item["angle_id"], item["project_name"])
            for angle in angles:
                if angle["angle_id"] == item["angle_id"]:
                    angle.update(status="in_production", project_name=item["project_name"])
        ProductStore.update(product_id, angles=angles)
        return batch

    monkeypatch.setattr(BatchRenderManager, "create_batch", classmethod(create_batch))
    return events, state, calls, behaviour


def test_full_chain_drafts_then_renders_only_the_drafts_it_built(full_fakes, tmp_path):
    events, state, calls, behaviour = full_fakes
    product = _product([
        _angle("a1"), _angle("a2"),
        _angle("old", status="in_production", project_name="proj_old"),
        _angle("done", status="rendered", project_name="proj_done"),
    ], default_videos=[_clip(tmp_path, "raw1.mp4")])
    pid = product["id"]

    task = _run(pid, "full", batch_index=1)

    assert [e[0] for e in events] == ["voice", "voice", "scan", "draft"]
    assert sorted(c["project_name"] for c in calls) == ["proj_a1", "proj_a2"]
    assert task["status"] == "completed"
    result = task["result"]
    assert result["kind"] == "full"
    assert [d["angle_id"] for d in result["draft"]["drafts"]["created"]] == ["a1", "a2"]
    assert sorted(r["angle_id"] for r in result["render"]["rendered"]) == ["a1", "a2"]
    assert result["message"] == "สร้างดราฟต์ 2 มุม · เรนเดอร์เสร็จ 2 คลิป"
    assert _status(pid, "a1") == "rendered" and _status(pid, "a2") == "rendered"
    # a draft left from an earlier run is the render button's job
    assert _status(pid, "old") == "in_production"
    assert task["title"].startswith("ผลิตจนเรนเดอร์เสร็จ:")


def test_full_chain_renders_the_drafts_that_were_built_when_others_failed(full_fakes, tmp_path):
    events, state, calls, behaviour = full_fakes
    state["draft_fails"].add("a2")
    product = _product([_angle("a1"), _angle("a2")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    task = _run(product["id"], "full")

    assert [c["project_name"] for c in calls] == ["proj_a1"]
    assert task["status"] == "completed"
    result = task["result"]
    assert [(f["angle_id"], f["error"]) for f in result["draft"]["drafts"]["failed"]] == [("a2", "ไม่มีฉากพอ")]
    assert result["message"] == "สร้างดราฟต์ 1 มุม · ล้มเหลว 1 มุม · เรนเดอร์เสร็จ 1 คลิป"


def test_full_chain_stops_before_drafts_and_renders_when_the_scan_fails(full_fakes, tmp_path):
    events, state, calls, behaviour = full_fakes
    state["fallback"].add("raw1.mp4")
    product = _product([_angle("a1")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    task = _run(product["id"], "full")

    assert "draft" not in [e[0] for e in events]
    assert calls == []
    assert task["status"] == "failed"
    assert "หยุดที่ขั้นสแกนฉาก" in task["error"]


def test_full_chain_points_to_the_render_button_for_drafts_it_could_not_render(full_fakes, tmp_path):
    events, state, calls, behaviour = full_fakes
    product = _product([_angle("a1"), _angle("a2")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    def explode(kwargs):
        raise RuntimeError("ffmpeg ล้ม")
    behaviour["proj_a2"] = explode

    task = _run(product["id"], "full")

    assert task["status"] == "completed"
    assert task["result"]["message"].endswith("ดราฟต์ที่ยังไม่ได้เรนเดอร์ใช้ปุ่ม เรนเดอร์ดราฟต์")
    assert _status(product["id"], "a2") == "in_production"


def test_full_chain_with_nothing_to_draft_renders_nothing(full_fakes):
    events, state, calls, behaviour = full_fakes
    product = _product([_angle("old", status="in_production", project_name="proj_old")])

    task = _run(product["id"], "full")

    assert events == [] and calls == []
    assert task["status"] == "completed"
    assert task["result"]["render"] is None


def test_full_chain_progress_gives_the_first_half_to_drafts_and_the_second_to_renders(full_fakes, tmp_path,
                                                                                       monkeypatch):
    seen = []
    original = TaskManager.update_progress

    def record(task_id, value, *args, **kwargs):
        seen.append((task_id, value, kwargs.get("step_label") or ""))
        return original(task_id, value, *args, **kwargs)

    monkeypatch.setattr(TaskManager, "update_progress", staticmethod(record))
    product = _product([_angle("a1")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    task = _run(product["id"], "full")

    assert task["status"] == "completed"
    seen = [(v, label) for tid, v, label in seen if tid == task["id"]]  # not the voice task's own bar
    values = [v for v, _ in seen]
    assert values == sorted(values) and max(values) <= 1.0
    assert all(v <= 0.5 for v, label in seen if "เรนเดอร์ 1 คลิป" not in label)
    assert any(v > 0.5 for v, label in seen if "เรนเดอร์ 1 คลิป" in label)
    assert production_chain._WINDOWS == {}


def test_cancelling_the_full_chain_during_its_render_stops_it(full_fakes, tmp_path):
    events, state, calls, behaviour = full_fakes
    product = _product([_angle("a1")], default_videos=[_clip(tmp_path, "raw1.mp4")])
    started = threading.Event()

    def wait_for_cancel(kwargs):
        started.set()
        assert kwargs["cancel_event"].wait(5.0), "the render was never told to stop"
        raise render_jobs.RenderCancelled()

    behaviour["proj_a1"] = wait_for_cancel

    task = production_chain.start_chain(product["id"], "full")
    assert started.wait(5.0)
    TaskManager.cancel_task(task["id"])

    assert _wait_until(lambda: (product["id"] in {k[1] for k in production_chain._ACTIVE}) is False)
    assert TaskManager.get_task(task["id"])["status"] == "cancelled"
    assert _status(product["id"], "a1") == "in_production"


def test_route_starts_the_full_chain(full_fakes, tmp_path):
    events, state, calls, behaviour = full_fakes
    product = _product([_angle("a1")], default_videos=[_clip(tmp_path, "raw1.mp4")])

    task = _run_through_route(product["id"], "full")

    assert task["status"] == "completed", task.get("error")
    assert task["payload"]["kind"] == "full"
    assert [c["project_name"] for c in calls] == ["proj_a1"]
