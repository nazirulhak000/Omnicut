"""
Smoke tests for the phase-1 pieces: manifest, AI bridge, post log, product
queue, and the re-roll endpoint's guard rails.

Every test redirects its storage into tmp_path, so running these never touches
_Docs/post_log.json, _Docs/products.json, or a real project folder.

    python -m pytest scripts/test_phase1_smoke.py -v
"""

import json
import hashlib
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import post_log, product_store, project_manifest, render_jobs
from scripts.ai_bridge import AIBridge, ManualModeRequired
from scripts.it_angles import ANGLE_LUT_HINTS, IT_ANGLE_CATALOG, LOOK_PRESETS, catalog_for_prompt, fallback_angles
from scripts.post_log import PostLog
from scripts.product_store import ProductStore
from scripts.project_manifest import REROLL_STAGE, ProjectManifest
from scripts.subtitle_engine import SubtitleEngine, _load_font_family_map
from scripts.asset_registry import AssetRegistry
from scripts.sfx_manager import SFXManager
from scripts.script_generator import ScriptGenerator
from scripts import fetch_freesound_sfx


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


def test_bgm_reroll_shares_the_voice_stage():
    """BGM has no re-roll stage of its own -- swapping it re-mixes alongside the voice."""
    assert REROLL_STAGE["bgm"] == "voice"


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
# Font selection actually changes the rendered font
#
# Every UI font_name used to collapse to "IBM Plex Sans Thai" regardless of
# which one was picked -- the picker was cosmetic. Guard against that
# regressing silently again.
# ----------------------------------------------------------------------
def test_every_legacy_font_key_still_resolves():
    """The 14 font_name values the UI has sent historically must all still map to something."""
    font_map = _load_font_family_map()
    legacy_keys = [
        "Mitr", "mitr_minimal", "IBMPlex", "ibm_tech", "IBM Plex Sans Thai",
        "ChakraPetch", "chakra_cyber", "Chakra Petch", "Prompt", "prompt_modern",
        "Kanit", "kanit_viral", "capsule_pill", "Minimal Dark Capsule Pill",
    ]
    for key in legacy_keys:
        assert key in font_map, f"'{key}' used to be selectable and must not start erroring"


def test_distinct_font_choices_are_actually_distinct():
    """The whole point of the fix: different UI choices must yield different families."""
    font_map = _load_font_family_map()
    assert font_map["Kanit"] != font_map["Mitr"] != font_map["Prompt"] != font_map["ChakraPetch"]
    assert len({font_map["Kanit"], font_map["Mitr"], font_map["Prompt"], font_map["ChakraPetch"]}) == 4


def test_font_choice_reaches_the_rendered_ass_file(tmp_path):
    cues = [{"id": 1, "start": 0.0, "end": 2.0, "text": "ทดสอบฟอนต์", "sfx": None}]
    fontnames = {}
    for font_name in ["Kanit", "Mitr"]:
        path, _ = SubtitleEngine.generate_ass(
            cues=cues, output_ass_path=str(tmp_path / f"{font_name}.ass"),
            font_name=font_name, bilingual=False,
        )
        content = Path(path).read_text(encoding="utf-8")
        style_line = next(l for l in content.splitlines() if l.startswith("Style: TikTokWhite"))
        fontnames[font_name] = style_line.split(",")[1]

    assert fontnames["Kanit"] == "Kanit"
    assert fontnames["Mitr"] == "Mitr"
    assert fontnames["Kanit"] != fontnames["Mitr"]


def test_unknown_font_name_falls_back_instead_of_erroring():
    font_map = _load_font_family_map()
    assert font_map.get("some_font_id_from_the_future", "IBM Plex Sans Thai") == "IBM Plex Sans Thai"


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
# SFX variety (from 5 hardcoded names to the real 28-file library)
# ----------------------------------------------------------------------
def test_sfxmanager_resolves_legacy_names_and_new_ones():
    """The 5 names that used to be the entire usable set must still resolve..."""
    for legacy in ("boom", "whoosh", "pop", "ding", "cash"):
        assert SFXManager.resolve(legacy) is not None, f"legacy name '{legacy}' must not stop resolving"
    # ...and so must names that were previously unreachable from any cue.
    assert SFXManager.resolve("sfx_camera_shutter") is not None
    assert SFXManager.resolve("sfx_magic_sparkle") is not None
    assert SFXManager.resolve("not_a_real_sfx_name") is None


def test_ai_bridge_sfx_prompt_lists_the_real_library_not_5_names():
    prompt = AIBridge.build_prompt("script", {
        "product_name": "หูฟัง", "angle_title": "x", "hook": "y", "specs": [], "price_deal": "z",
    })
    assert "__SFX_NAME_LIST__" not in prompt, "the sentinel must never leak into a real prompt"
    # A handful of sounds only reachable through the wider library, not the
    # old 5-name hardcoded set -- if these are missing, the schema silently
    # went back to being a hand-typed list.
    for name in ("sfx_camera_shutter", "sfx_magic_sparkle", "sfx_vine_boom"):
        assert name in prompt


def test_script_generator_fallback_uses_more_than_three_sfx_names():
    """The no-AI path used to hardcode boom/ding/cash for every script, regardless of length."""
    result = ScriptGenerator.generate("ทดสอบสินค้า")
    sfx_used = {line["sfx"] for line in result["lines"]}
    assert len(sfx_used) >= 4, f"expected real variety across 5 lines, got only: {sfx_used}"
    for name in sfx_used:
        assert AssetRegistry.resolve_sfx_path(name) is not None, f"'{name}' must resolve to a real file"


# ----------------------------------------------------------------------
# LUT color grading -- opt-in only
#
# Measured on this CPU-only machine (no CUDA) against the real Esseger
# clip: lut3d added ~90% to the ffmpeg render step (11.6s -> 22.0s on an
# 8s clip). That ruled out auto-applying one by IT angle, which the
# original plan called for -- a render must never get slower without the
# user explicitly asking for it.
# ----------------------------------------------------------------------
def test_lut_is_never_auto_applied_by_pipeline():
    """pipeline.py must not import the angle->LUT hint table -- it would only be used to auto-pick."""
    import ast
    tree = ast.parse(Path("scripts/pipeline.py").read_text(encoding="utf-8"))
    imported_names = {
        alias.asname or alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "ANGLE_LUT_HINTS" not in imported_names, (
        "pipeline.py importing this again likely means auto-pick crept back in"
    )


def test_angle_lut_hints_still_cover_every_angle():
    """Kept as a suggestion the frontend can surface -- must not silently drop an angle."""
    catalog_keys = {a["key"] for a in IT_ANGLE_CATALOG}
    assert set(ANGLE_LUT_HINTS.keys()) == catalog_keys


# ----------------------------------------------------------------------
# Per-angle punch-zoom pattern -- safe to auto-apply, unlike the LUT above
# ----------------------------------------------------------------------
def test_look_presets_cover_every_angle():
    catalog_keys = {a["key"] for a in IT_ANGLE_CATALOG}
    assert set(LOOK_PRESETS.keys()) == catalog_keys


def test_look_presets_are_actually_distinct_across_angles():
    """The whole point: different angles must not silently share one pattern."""
    patterns = {tuple(v) for v in LOOK_PRESETS.values()}
    assert len(patterns) >= 6, f"expected real per-angle variety, got only {len(patterns)} distinct patterns"


def test_angle_key_resolves_to_the_right_shot_scales_via_pipeline():
    """End-to-end through pipeline.run(), not just a dict lookup in isolation."""
    import shutil
    from unittest.mock import patch
    from scripts.pipeline import TikTokAutoCutterPipeline
    from scripts.config import PROJECTS_DIR

    raw_video = next(Path("01_Raw").rglob("*.mov"), None) or next(Path("01_Raw").rglob("*.mp4"), None)
    if raw_video is None:
        pytest.skip("no raw video available in 01_Raw to render against")

    project_name = "TEST_look_preset_resolution"
    captured = {}

    def fake_assemble(**kwargs):
        captured["shot_scales"] = kwargs.get("shot_scales")
        return "/fake/out.mp4"

    try:
        with patch("scripts.pipeline.VideoEditor.assemble_tiktok_video", side_effect=fake_assemble):
            TikTokAutoCutterPipeline.run(
                product_name="test", project_name=project_name,
                raw_video_path=str(raw_video), custom_script="ทดสอบ",
                voice_engine_type="edge_tts", export_mp4=True, use_ai_vision=False,
                angle_meta={"angle_key": "fake_vs_real"},
            )
        assert captured["shot_scales"] == LOOK_PRESETS["fake_vs_real"]
    finally:
        shutil.rmtree(PROJECTS_DIR / project_name, ignore_errors=True)


# ----------------------------------------------------------------------
# Freesound SFX acquisition (all network calls mocked -- never hits the
# real API in a test run)
# ----------------------------------------------------------------------
def test_slugify_produces_safe_filenames():
    assert fetch_freesound_sfx._slugify("Wrong Answer Buzzer #2!") == "wrong_answer_buzzer_2"
    assert fetch_freesound_sfx._slugify("") == "sound"
    assert len(fetch_freesound_sfx._slugify("x" * 200)) <= 40


def test_missing_api_key_raises_with_setup_instructions(monkeypatch):
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)
    with pytest.raises(fetch_freesound_sfx.FreesoundFetchError, match="freesound.org/apiv2/apply"):
        fetch_freesound_sfx._api_key()


def test_search_filters_to_cc0_and_short_clips_only(monkeypatch):
    """The whole point of this tool: never pull CC-BY or CC-BY-NC without the user asking for it."""
    monkeypatch.setenv("FREESOUND_API_KEY", "fake-key-for-test")
    captured = {}

    def fake_get_json(path, params):
        captured["path"] = path
        captured["params"] = params
        return {"results": []}

    monkeypatch.setattr(fetch_freesound_sfx, "_get_json", fake_get_json)
    fetch_freesound_sfx.search_cc0_sounds("cash register", limit=2)

    assert captured["path"] == "/search/text/"
    assert '"Creative Commons 0"' in captured["params"]["filter"]
    assert "duration:[0.1 TO 8.0]" in captured["params"]["filter"]
    assert captured["params"]["query"] == "cash register"


def test_download_skips_a_byte_identical_duplicate(monkeypatch, tmp_path):
    existing_file = tmp_path / "sfx_existing.mp3"
    existing_file.write_bytes(b"identical-audio-bytes")
    existing_hashes = {hashlib.md5(b"identical-audio-bytes").hexdigest(): existing_file}

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"identical-audio-bytes"

    monkeypatch.setattr(fetch_freesound_sfx.urllib.request, "urlopen", lambda *a, **k: FakeResponse())

    sound = {"name": "duplicate sound", "previews": {"preview-hq-mp3": "https://example.com/x.mp3"}}
    result = fetch_freesound_sfx.download_sound(sound, existing_hashes)
    assert result is None, "a byte-identical file must be skipped, not saved as a second copy"


def test_download_handles_a_result_with_no_preview_url():
    sound = {"name": "no preview available", "previews": {}}
    assert fetch_freesound_sfx.download_sound(sound, {}) is None


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
# PATCH /api/projects/{name}/cues -- Manual Editor caption edits
# ----------------------------------------------------------------------
def test_update_cues_404s_for_a_project_that_was_never_rendered(client, projects_dir):
    response = client.patch("/api/projects/never-rendered/cues", json={"cues": []})
    assert response.status_code == 404


def test_update_cues_requires_at_least_one_field(client, projects_dir):
    ProjectManifest.save("demo", cues=[{"start": 0, "end": 1, "text": "เดิม"}])
    response = client.patch("/api/projects/demo/cues", json={})
    assert response.status_code == 400


def test_update_cues_persists_edited_text_and_timing(client, projects_dir):
    ProjectManifest.save(
        "demo",
        cues=[{"start": 0.0, "end": 2.0, "text": "เดิม", "sfx": None}],
        micro_cues=[{"start": 0.0, "end": 1.0, "text": "เดิม"}],
    )

    new_cues = [{"start": 0.0, "end": 2.5, "text": "แก้ใหม่แล้ว", "sfx": "sfx_pop_bubble"}]
    response = client.patch("/api/projects/demo/cues", json={"cues": new_cues})

    assert response.status_code == 200
    body = response.json()
    assert body["cues"] == new_cues
    # micro_cues untouched since the request didn't include it
    assert body["micro_cues"][0]["text"] == "เดิม"

    reloaded = ProjectManifest.load("demo")
    assert reloaded["cues"] == new_cues


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


# ----------------------------------------------------------------------
# VideoEditor.assemble_tiktok_video -- clip_list (Manual Editor) path
#
# get_media_info() hits ffprobe via subprocess.run; mocking subprocess.run
# generically makes its json.loads(res.stdout) fail on the MagicMock, which
# get_media_info already catches and turns into its documented fallback
# dict -- no separate mock needed for it.
# ----------------------------------------------------------------------
def _capture_ffmpeg_cmd(monkeypatch, tmp_path, **assemble_kwargs):
    from unittest.mock import patch, MagicMock
    from scripts.video_editor import VideoEditor

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return MagicMock(returncode=0, stderr="")

    with patch("scripts.video_editor.subprocess.run", side_effect=fake_run):
        VideoEditor.assemble_tiktok_video(
            total_duration=5.0,
            mixed_audio_path=str(tmp_path / "mix.wav"),
            ass_subtitle_path=str(tmp_path / "subs.ass"),
            output_mp4_path=str(tmp_path / "out.mp4"),
            **assemble_kwargs,
        )
    return captured["cmd"]


def test_assemble_video_without_clip_list_keeps_legacy_single_source_shape(monkeypatch, tmp_path):
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[str(tmp_path / "raw.mp4")])

    assert cmd.count("-i") == 2, "legacy path: exactly 1 video input + 1 audio input"
    assert "1:a" in cmd, "audio is still input index 1 for a single-source render"
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "[base_v]" in filter_arg, "legacy path re-crops shots from one shared base stream"
    assert "shot_0" in filter_arg


def test_assemble_video_rejects_empty_raw_paths_without_clip_list(tmp_path):
    from scripts.video_editor import VideoEditor

    with pytest.raises(ValueError):
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[],
            total_duration=5.0,
            mixed_audio_path=str(tmp_path / "mix.wav"),
            ass_subtitle_path=str(tmp_path / "subs.ass"),
            output_mp4_path=str(tmp_path / "out.mp4"),
        )


def test_assemble_video_with_clip_list_opens_one_input_per_clip(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 1.5, "trim_end": 4.0},
        {"source_path": str(tmp_path / "c.mp4")},  # trim_end omitted -> falls back to full duration
    ]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)

    assert cmd.count("-i") == 4, "3 clip inputs + 1 audio input"
    assert "3:a" in cmd, "audio input index must shift to N (3 video inputs), not stay hardcoded at 1"
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "[0:v]" in filter_arg and "[1:v]" in filter_arg and "[2:v]" in filter_arg, \
        "each clip must read from its own ffmpeg input, not all from input 0"
    assert "clip_0" in filter_arg and "clip_1" in filter_arg and "clip_2" in filter_arg
    assert "[base_v]" not in filter_arg, "clip_list path must not use the single-source base stream"
    assert "concat=n=3" in filter_arg


def test_assemble_video_clip_list_with_all_cuts_keeps_single_concat(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 2.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 2.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, transitions=["cut"]
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=2" in filter_arg
    assert "xfade" not in filter_arg


def test_assemble_video_clip_list_with_fade_uses_xfade(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0},
        {"source_path": str(tmp_path / "c.mp4"), "trim_start": 0.0, "trim_end": 3.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, transitions=["fade", "cut"]
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade=transition=fade" in filter_arg, "boundary 1 (clip 0->1) should crossfade"
    assert "concat=n=2" in filter_arg, "boundary 2 (clip 1->2) stays a plain cut"
    assert "[v_concat]" in filter_arg, "final reduced node must still be named v_concat"
    # only one top-level concat=n=N (the old whole-sequence shape) must NOT appear
    assert "concat=n=3" not in filter_arg


def test_assemble_video_empty_clip_list_falls_back_to_legacy_path(monkeypatch, tmp_path):
    # `[]` is falsy like `None` -- it must fall through to the single-source
    # path (using raw_video_paths), not be treated as "0 clips to concat".
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path,
        raw_video_paths=[str(tmp_path / "raw.mp4")],
        clip_list=[],
    )
    assert cmd.count("-i") == 2
    assert "1:a" in cmd
