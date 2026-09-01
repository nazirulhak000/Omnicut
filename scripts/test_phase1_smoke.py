"""
Smoke tests for the phase-1 pieces: manifest, AI bridge, post log, product
queue, and the re-roll endpoint's guard rails.

Every test redirects its storage into tmp_path, so running these never touches
_Docs/post_log.json, _Docs/products.json, or a real project folder.

    python -m pytest scripts/test_phase1_smoke.py -v
"""

import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import post_log, product_store, project_manifest, render_jobs
from scripts.ai_bridge import AIBridge, ManualModeRequired
from scripts.it_angles import catalog_for_prompt, fallback_angles
from scripts.post_log import PostLog
from scripts.product_store import ProductStore
from scripts.project_manifest import REROLL_STAGE, ProjectManifest
from scripts.subtitle_engine import SubtitleEngine


# ----------------------------------------------------------------------
# Fixtures — keep every test off the real data files
# ----------------------------------------------------------------------
@pytest.fixture
def projects_dir(tmp_path, monkeypatch):
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    return target


@pytest.fixture
def post_log_file(tmp_path, monkeypatch):
    target = tmp_path / "post_log.json"
    monkeypatch.setattr(post_log, "LOG_PATH", target)
    return target


@pytest.fixture
def product_file(tmp_path, monkeypatch):
    target = tmp_path / "products.json"
    monkeypatch.setattr(product_store, "STORE_PATH", target)
    return target


@pytest.fixture
def client():
    from scripts.api_server import app
    return TestClient(app)


# ----------------------------------------------------------------------
# Project manifest
# ----------------------------------------------------------------------
def test_manifest_roundtrip(projects_dir):
    ProjectManifest.save(
        "demo",
        script_data={"lines": [{"text": "หนึ่ง"}, {"text": "สอง"}]},
        cues=[{"id": 1, "start": 0.0, "end": 1.5, "text": "หนึ่ง"}],
        micro_cues=[{"id": 1, "start": 0.0, "end": 0.8, "text": "หนึ่ง"}],
        total_duration=12.5,
        artifacts={"voice_audio": {"path": str(projects_dir / "demo" / "voiceover.wav")}},
    )

    loaded = ProjectManifest.load("demo")
    assert loaded["total_duration"] == 12.5
    assert loaded["cues"][0]["text"] == "หนึ่ง"
    assert loaded["artifacts"]["voice_audio"]["path"].endswith("voiceover.wav")
    assert loaded["created_at"] and loaded["updated_at"]


def test_manifest_save_merges_instead_of_replacing(projects_dir):
    ProjectManifest.save("demo", total_duration=10.0, artifacts={"voice_audio": {"path": "a.wav"}})
    ProjectManifest.save("demo", artifacts={"subtitles_ass": {"path": "b.ass"}})

    artifacts = ProjectManifest.load("demo")["artifacts"]
    assert set(artifacts) == {"voice_audio", "subtitles_ass"}, "a later save must not drop earlier artifacts"
    assert ProjectManifest.load("demo")["total_duration"] == 10.0


def test_require_explains_itself_when_missing(projects_dir):
    with pytest.raises(ValueError, match="render"):
        ProjectManifest.require("never-rendered")


def test_versioned_path_never_overwrites(projects_dir):
    first = ProjectManifest.versioned_path("demo", "voiceover", ".wav")
    first.write_text("take 1", encoding="utf-8")
    second = ProjectManifest.versioned_path("demo", "voiceover", ".wav")

    assert first.name == "voiceover_v1.wav"
    assert second.name == "voiceover_v2.wav"
    assert first.read_text(encoding="utf-8") == "take 1", "the earlier take must survive"


def test_artifact_path_ignores_deleted_files(projects_dir):
    manifest = {"artifacts": {"voice_audio": {"path": str(projects_dir / "gone.wav")}}}
    assert ProjectManifest.artifact_path(manifest, "voice_audio") is None


@pytest.mark.parametrize(
    "resume_from, expected",
    [
        (None, {"script": True, "voice": True, "subtitles": True, "video": True}),
        ("script", {"script": True, "voice": True, "subtitles": True, "video": True}),
        ("voice", {"script": False, "voice": True, "subtitles": True, "video": True}),
        ("subtitles", {"script": False, "voice": False, "subtitles": True, "video": True}),
        ("video", {"script": False, "voice": False, "subtitles": False, "video": True}),
    ],
)
def test_resume_reruns_only_the_tail(resume_from, expected):
    for stage, should in expected.items():
        assert ProjectManifest.should_run(stage, resume_from) is should


def test_cheap_rerolls_keep_the_voice():
    """A hook or subtitle re-roll must not touch the voice — that is the whole point."""
    for part in ("hook", "subtitles"):
        stage = REROLL_STAGE[part]
        assert ProjectManifest.should_run("voice", stage) is False
        assert ProjectManifest.should_run("subtitles", stage) is True

    assert ProjectManifest.should_run("voice", REROLL_STAGE["voice"]) is True
    assert ProjectManifest.should_run("script", REROLL_STAGE["script"]) is True


# ----------------------------------------------------------------------
# AI bridge
# ----------------------------------------------------------------------
def test_parses_answer_wrapped_in_fences_and_prose():
    messy = (
        "นี่คือผลลัพธ์ครับ\n"
        "```json\n"
        '{"caption":"สายชาร์จ 20W จิ้มตะกร้าเลย","hashtags":["#สายชาร์จ"],"cover_text":"99 vs 399"}\n'
        "```"
    )
    data = AIBridge.parse_response("caption", messy)
    assert data["caption"].startswith("สายชาร์จ")
    assert data["hashtags"] == ["#สายชาร์จ"]


def test_parses_bare_json_with_trailing_prose():
    raw = '{"product_name":"หูฟังบลูทูธ"} หวังว่าจะช่วยได้นะครับ'
    assert AIBridge.parse_response("product_enrich", raw)["product_name"] == "หูฟังบลูทูธ"


@pytest.mark.parametrize(
    "task, raw",
    [
        ("angles", "{}"),
        ("angles", '{"angles":[{"title":"ไม่มี hook"}]}'),
        ("script", '{"lines":[]}'),
        ("caption", '{"caption":"มี caption แต่ hashtags ไม่ใช่ list","hashtags":"x"}'),
        ("caption", "ไม่มี JSON เลยสักตัว"),
    ],
)
def test_rejects_answers_downstream_code_cannot_use(task, raw):
    with pytest.raises(ValueError):
        AIBridge.parse_response(task, raw)


def test_manual_mode_hands_back_the_prompt(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ManualModeRequired) as excinfo:
        AIBridge.generate("caption", {
            "product_name": "หูฟัง",
            "angle_title": "เทียบราคา",
            "hook": "199 กับ 899 ต่างกันยังไง",
            "price_deal": "ลด 50%",
        })

    assert "หูฟัง" in excinfo.value.prompt, "the prompt must be usable as-is in a chat window"
    assert excinfo.value.task == "caption"


def test_prompt_refuses_to_build_without_required_context():
    with pytest.raises(ValueError, match="missing context"):
        AIBridge.build_prompt("script", {"product_name": "หูฟัง"})


# ----------------------------------------------------------------------
# IT angle catalog
# ----------------------------------------------------------------------
def test_seller_asset_filter_drops_angles_needing_the_product():
    everything = catalog_for_prompt()
    sellers_only = catalog_for_prompt(seller_assets_only=True)

    assert len(sellers_only) < len(everything)
    keys = {a["key"] for a in sellers_only}
    assert "real_test" not in keys, "you cannot film a hands-on test before the product arrives"
    assert "spec_compare" in keys


def test_fallback_angles_are_ready_to_put_on_screen():
    angles = fallback_angles("หูฟังบลูทูธ", seller_assets_only=True)
    assert angles, "there must be angles even with no LLM available"
    assert all(a["angle_key"] and a["hook"] for a in angles)
    assert all("หูฟังบลูทูธ" in a["hook"] for a in angles)

    # A half-filled pattern would put literal braces on the video.
    leftovers = [a["hook"] for a in angles if "{" in a["hook"] or "}" in a["hook"]]
    assert not leftovers, f"unfilled placeholders would be burned into the clip: {leftovers}"


# ----------------------------------------------------------------------
# Post log
# ----------------------------------------------------------------------
def test_post_log_cycle(post_log_file):
    post = PostLog.add_post(
        product_name="สายชาร์จแม่เหล็ก",
        clip_file="clip.mp4",
        angle_key="spec_compare",
        angle_title="เทียบราคา",
        hook="99 กับ 399 ต่างกันยังไง",
    )
    PostLog.update_metrics(post["id"], {"views": 10000, "cart_clicks": 250, "orders": 5, "commission_thb": 180.5})

    summary = PostLog.summary()
    assert summary == {
        "total_posted": 1,
        "measured": 1,
        "pending_metrics": 0,
        "total_views": 10000,
        "total_orders": 5,
        "total_commission_thb": 180.5,
    }

    by_angle = PostLog.angle_performance()
    assert by_angle[0]["angle_key"] == "spec_compare"
    assert by_angle[0]["cart_click_rate"] == 2.5


def test_metrics_reject_non_numbers(post_log_file):
    post = PostLog.add_post(product_name="x", clip_file="c.mp4")
    with pytest.raises(ValueError, match="views"):
        PostLog.update_metrics(post["id"], {"views": "เยอะมาก"})


def test_unmeasured_posts_stay_out_of_performance(post_log_file):
    PostLog.add_post(product_name="x", clip_file="c.mp4", angle_key="fake_vs_real")
    assert PostLog.angle_performance() == []
    assert PostLog.summary()["measured"] == 0


# ----------------------------------------------------------------------
# Product queue
# ----------------------------------------------------------------------
def test_product_cycle(product_file):
    product = ProductStore.add(name="หูฟัง TWS", url="https://shopee.co.th/x")
    assert product["platform"] == "shopee"
    assert product["status"] == "candidate"

    ProductStore.update(product["id"], status="scripted", pain_points=["เสียงแตก"])
    updated = ProductStore.get(product["id"])
    assert updated["status"] == "scripted"
    assert updated["pain_points"] == ["เสียงแตก"]


def test_same_url_is_not_queued_twice(product_file):
    first = ProductStore.add(name="หูฟัง", url="https://shopee.co.th/same")
    second = ProductStore.add(name="หูฟัง (พิมพ์ซ้ำ)", url="https://shopee.co.th/same")
    assert first["id"] == second["id"]
    assert len(ProductStore.list()) == 1


def test_unknown_status_is_refused(product_file):
    product = ProductStore.add(name="หูฟัง")
    with pytest.raises(ValueError, match="status"):
        ProductStore.update(product["id"], status="ยิงแอดแล้ว")


def test_attaching_a_project_marks_it_rendered(product_file):
    product = ProductStore.add(name="หูฟัง")
    ProductStore.attach_project(product["id"], "TikTok_headphones")
    ProductStore.attach_project(product["id"], "TikTok_headphones")

    stored = ProductStore.get(product["id"])
    assert stored["projects"] == ["TikTok_headphones"], "linking twice must not duplicate"
    assert stored["status"] == "rendered"


# ----------------------------------------------------------------------
# Spec-bar overlay (IT vertical: numbers on screen, not just spoken)
# ----------------------------------------------------------------------
def _cue(start, end, text, on_screen=""):
    return {"id": 1, "start": start, "end": end, "text": text, "sfx": None, "on_screen": on_screen}


def test_spec_bar_only_appears_for_cues_with_something_to_show(tmp_path):
    cues = [
        _cue(0.0, 2.0, "สายชาร์จแม่เหล็กตัวนี้ชาร์จไวมาก", on_screen="20W PD"),
        _cue(2.0, 4.0, "ไม่ทำร้ายแบตเลย"),  # nothing to show -- no bar expected
        _cue(4.0, 6.0, "กดตะกร้าซ้ายล่างเลย", on_screen="ลด 50%"),
    ]

    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(tmp_path / "out.ass"),
        font_name="IBMPlex",
        hook_title="ทดสอบ",
        hook_duration=2.0,
        bilingual=False,
    )
    content = Path(ass_path).read_text(encoding="utf-8")

    assert "Style: SpecBar" in content, "the SpecBar style must be declared even if unused elsewhere"
    spec_events = [l for l in content.splitlines() if l.startswith("Dialogue:") and ",SpecBar," in l]
    assert len(spec_events) == 2, f"expected one bar per non-empty on_screen cue, got: {spec_events}"
    assert "20W PD" in spec_events[0] and "0:00:00.00,0:00:02.00" in spec_events[0]
    assert "ลด 50%" in spec_events[1] and "0:00:04.00,0:00:06.00" in spec_events[1]


def test_spec_bar_survives_a_cue_with_no_on_screen_key_at_all(tmp_path):
    """Cues from voice engines that predate this feature won't have the key."""
    cues = [{"id": 1, "start": 0.0, "end": 2.0, "text": "ทดสอบ", "sfx": None}]  # no "on_screen" key
    ass_path, _ = SubtitleEngine.generate_ass(cues=cues, output_ass_path=str(tmp_path / "out.ass"))
    content = Path(ass_path).read_text(encoding="utf-8")
    assert not any(l.startswith("Dialogue:") and ",SpecBar," in l for l in content.splitlines())


# ----------------------------------------------------------------------
# Render concurrency guard
#
# This machine has no CUDA and 13.7GB RAM (see _Docs/PRD_phase1.md section 3)
# -- two ffmpeg encodes or two TTS calls at once is a real OOM/thrash risk.
# ----------------------------------------------------------------------
def test_render_slot_serializes_two_jobs():
    job_a, job_b = render_jobs.create_job("job-a"), render_jobs.create_job("job-b")
    order = []
    b_saw_queued_while_waiting = threading.Event()

    def run_a():
        with render_jobs.render_slot("job-a"):
            order.append("a-start")
            time.sleep(0.2)
            order.append("a-end")

    def run_b():
        time.sleep(0.05)  # let job A grab the slot first
        # Poll briefly for the "queued" status the lock sets while job A holds it.
        for _ in range(20):
            if render_jobs.ACTIVE_JOBS["job-b"]["status"] == "queued" and "a-start" in order:
                b_saw_queued_while_waiting.set()
                break
            time.sleep(0.01)
        with render_jobs.render_slot("job-b"):
            order.append("b-start")

    t_a, t_b = threading.Thread(target=run_a), threading.Thread(target=run_b)
    t_a.start(); t_b.start()
    t_a.join(timeout=5); t_b.join(timeout=5)

    assert order == ["a-start", "a-end", "b-start"], "job B must not start until job A releases the slot"
    assert b_saw_queued_while_waiting.is_set(), "the waiting job must be visibly 'queued', not silently stuck"


def test_render_slot_releases_on_exception():
    render_jobs.create_job("job-fails")
    with pytest.raises(ValueError):
        with render_jobs.render_slot("job-fails"):
            raise ValueError("render blew up")

    # A lock left held after a crash would freeze every render after it.
    with render_jobs.render_slot("job-after-crash"):
        pass  # acquiring at all proves the previous slot was released


# ----------------------------------------------------------------------
# Re-roll guard rails (HTTP level)
# ----------------------------------------------------------------------
def test_reroll_rejects_an_unknown_part(client):
    response = client.post("/api/reroll", json={"project_name": "whatever", "part": "ทั้งคลิป"})
    assert response.status_code == 400
    assert "part" in response.json()["detail"]


def test_reroll_refuses_a_project_that_was_never_rendered(client, projects_dir):
    response = client.post("/api/reroll", json={"project_name": "never-rendered", "part": "hook"})
    assert response.status_code == 404
    assert "render" in response.json()["detail"]


def test_reroll_reports_its_cost_up_front(client, projects_dir):
    ProjectManifest.save(
        "demo",
        script_data={"lines": [{"text": "หนึ่ง"}]},
        cues=[], micro_cues=[], total_duration=8.0,
        render_params={"raw_video_path": str(projects_dir / "nope.mp4")},
    )
    response = client.post("/api/reroll", json={"project_name": "demo", "part": "hook"})

    body = response.json()
    assert response.status_code == 200
    assert body["job_id"] and body["status"] == "queued"
    assert "เร็ว" in body["cost"], "the user should see what a button costs before pressing it"


def test_angles_endpoint_serves_the_catalog(client):
    body = client.get("/api/angles", params={"seller_assets_only": True, "product_name": "หูฟัง"}).json()
    assert body["catalog"] and body["fallback"]
    assert all(not a["needs_own_footage"] for a in body["fallback"])


def test_product_fetch_rejects_a_non_url(client):
    assert client.post("/api/product/fetch", json={"url": "หูฟังบลูทูธ"}).status_code == 400
