"""
Smoke tests for the phase-1 pieces: manifest, AI bridge, post log, product
queue, and the re-roll endpoint's guard rails.

Every test redirects its storage into tmp_path, so running these never touches
_Docs/post_log.json, _Docs/products.json, or a real project folder.

    python -m pytest scripts/test_phase1_smoke.py -v
"""

import json
import hashlib
import os
import re
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
from tools import fetch_freesound_sfx


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
    from scripts.auth import get_configured_api_key, API_KEY_HEADER
    key = get_configured_api_key()
    headers = {API_KEY_HEADER: key} if key else {}
    return TestClient(app, headers=headers)


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


def test_delete_removes_the_project_folder(projects_dir):
    ProjectManifest.save("doomed", total_duration=3.0)
    (projects_dir / "doomed" / "voiceover.wav").write_bytes(b"x" * 2048)
    ProjectManifest.save("keeper", total_duration=3.0)

    result = ProjectManifest.delete("doomed")

    assert not (projects_dir / "doomed").exists()
    assert (projects_dir / "keeper").exists(), "deleting one project must not touch another"
    assert result["project_name"] == "doomed"
    assert result["files_removed"] >= 2, "manifest + the wav"


def test_delete_refuses_to_escape_the_projects_folder(projects_dir, tmp_path):
    outsider = tmp_path / "03_Projects" / ".." / "precious"
    (tmp_path / "precious").mkdir()

    # a name is a folder name, never a path: "../precious" resolves outside
    with pytest.raises(ValueError):
        ProjectManifest.delete("../precious")
    assert (tmp_path / "precious").exists()


def test_update_project_state_persists_every_hook_field(client, projects_dir):
    """
    Regression test for a bug where PATCH /projects/{name}/state silently
    dropped every hook-banner edit: UpdateProjectStateRequest didn't declare
    hook_brand/model/label/duration/motion, and Pydantic drops unknown
    fields with no error at all, so the Editor's save button looked like it
    worked while nothing actually persisted. Covers hook_motion specifically
    since it's the newest field, added alongside the same fields that were
    already fixed once.
    """
    ProjectManifest.save("demo", total_duration=5.0)

    resp = client.patch(
        "/api/projects/demo/state",
        json={
            "hook_brand": "Logitech",
            "hook_model": "Wave Keys",
            "hook_label": "Wireless Keyboard",
            "hook_duration": 2.4,
            "hook_motion": {"bounce": True, "stagger": True, "pulse": False, "underline": True},
        },
    )
    assert resp.status_code == 200, resp.text

    reloaded = client.get("/api/projects/demo").json()
    assert reloaded["hook_brand"] == "Logitech"
    assert reloaded["hook_model"] == "Wave Keys"
    assert reloaded["hook_label"] == "Wireless Keyboard"
    assert reloaded["hook_duration"] == 2.4
    assert reloaded["hook_motion"] == {"bounce": True, "stagger": True, "pulse": False, "underline": True}
    # Written to render_params too -- _execute_reroll's fallback and a future
    # reroll both read hook_* from there, not just the top-level manifest key.
    assert reloaded["render_params"]["hook_motion"] == {"bounce": True, "stagger": True, "pulse": False, "underline": True}


def test_delete_refuses_system_folders(projects_dir):
    (projects_dir / "_template").mkdir()
    with pytest.raises(ValueError):
        ProjectManifest.delete("_template")
    assert (projects_dir / "_template").exists(), "the template every project starts from"


def test_delete_missing_project_says_so(projects_dir):
    with pytest.raises(FileNotFoundError):
        ProjectManifest.delete("never-existed")


def test_project_list_carries_size_so_the_ui_can_warn(projects_dir):
    ProjectManifest.save("sized", total_duration=1.0)
    (projects_dir / "sized" / "big.wav").write_bytes(b"x" * (1024 * 1024))

    entry = next(p for p in ProjectManifest.list_projects() if p["project_name"] == "sized")
    assert entry["size_mb"] >= 1.0


def test_remove_angle_keeps_the_other_angles(product_file):
    product = ProductStore.add(url="https://x.test/1", name="หูฟัง", platform="tiktok")
    ProductStore.update(product["id"], angles=[
        {"angle_id": "pain_point", "hook_title": "A"},
        {"angle_id": "viral_hype", "hook_title": "B"},
    ])

    result = ProductStore.remove_angle(product["id"], "pain_point")

    assert result["angles_left"] == 1
    assert result["product_removed"] is None
    left = ProductStore.get(product["id"])["angles"]
    assert [a["angle_id"] for a in left] == ["viral_hype"]


def test_removing_the_last_angle_removes_the_product(product_file):
    product = ProductStore.add(url="https://x.test/2", name="ลำโพง", platform="tiktok")
    ProductStore.update(product["id"], angles=[{"angle_id": "only", "hook_title": "A"}])

    result = ProductStore.remove_angle(product["id"], "only")

    assert result["product_removed"] == product["id"]
    assert ProductStore.get(product["id"]) is None, "a product with no angles is an empty tracker card"


def test_find_by_project_prefers_the_recorded_link(product_file):
    linked = ProductStore.add(url="https://x.test/3", name="ชื่อซ้ำ", platform="tiktok")
    ProductStore.update(linked["id"], angles=[{"angle_id": "a1", "hook_title": "hook"}])
    ProductStore.attach_project(linked["id"], "TikTok_clip")

    other = ProductStore.add(url="https://x.test/4", name="ชื่อซ้ำ", platform="tiktok")

    product, angle = ProductStore.find_by_project("TikTok_clip", product_id=linked["id"], angle_id="a1")
    assert product["id"] == linked["id"], "the explicit link wins over a same-named product"
    assert angle["angle_id"] == "a1"

    # product_id alone (no angle_id) still resolves the product without
    # guessing which angle -- it's on the caller to know the angle too.
    product_only, angle_only = ProductStore.find_by_project("TikTok_clip", product_id=linked["id"])
    assert product_only["id"] == linked["id"]
    assert angle_only is None

    # a project with no recorded link and no stable id at all must not guess
    # by name -- two products share this display name, and guessing here is
    # exactly the bug that let a delete cascade onto the wrong product.
    product2, angle2 = ProductStore.find_by_project("TikTok_unlinked")
    assert product2 is None
    assert angle2 is None


def test_delete_with_angle_scope_refuses_when_nothing_matches(client, projects_dir, product_file):
    ProjectManifest.save("orphan", total_duration=1.0, render_params={"product_name": "ไม่มีในระบบ"})

    res = client.delete("/api/projects/orphan?scope=angle")

    assert res.status_code == 409, "never guess which script to delete"
    assert (projects_dir / "orphan").exists(), "and do not delete the project either"


def test_delete_endpoint_refuses_while_a_render_holds_the_slot(client, projects_dir, monkeypatch):
    from scripts import render_jobs

    ProjectManifest.save("busy-project", total_duration=1.0)
    monkeypatch.setattr(render_jobs, "is_busy", lambda: True)

    res = client.delete("/api/projects/busy-project")
    assert res.status_code == 409, "deleting under a running render leaves half-written files"
    assert (projects_dir / "busy-project").exists()


def test_bgm_reroll_remixes_without_resynthesizing_the_voice():
    """
    Music (track, level, ducking) lives in the mix. Swapping it must rebuild
    the mix and everything after it, and must NOT re-run the voice -- that was
    minutes of TTS for a change the voiceover never hears.
    """
    stage = REROLL_STAGE["bgm"]
    assert stage == "mix"
    assert ProjectManifest.should_run("voice", stage) is False
    assert ProjectManifest.should_run("mix", stage) is True
    assert ProjectManifest.should_run("subtitles", stage) is True
    assert ProjectManifest.should_run("video", stage) is True


def test_video_reroll_reuses_the_mix():
    """A clip-only change must not re-mix -- which is exactly why the editor
    has to ask for the "bgm" part when the music settings changed."""
    assert ProjectManifest.should_run("mix", REROLL_STAGE["video"]) is False


def test_ducking_is_off_by_default_and_wires_a_sidechain_when_on():
    import inspect
    from scripts.sfx_manager import SFXManager

    sig = inspect.signature(SFXManager.mix_audio_track)
    assert sig.parameters["bgm_ducking"].default is False, "ducking must be opt-in"
    src = inspect.getsource(SFXManager.mix_audio_track)
    assert "sidechaincompress" in src
    assert "anullsink" in src, "the split key must be terminated when there is no music"


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
    monkeypatch.setenv("DISABLE_ANTIGRAVITY", "1")
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: []))

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
# Hook banner motion presets (In / Loop / Out / Accent, CapCut-style)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "th, en",
    [
        # Thai matches a dictionary keyword, English matches nothing
        ("ดูนี่ด่วนเลย!", "at this quickly!"),
        ("มือเราจะวางสบายมาก", "Our hands will rest very comfortably."),
        # English matches, Thai does not
        ("❌ ทุกคน!", "everyone! Who has wrist pain?"),
        ("หลังก็ตึง", "My back is tight."),
    ],
)
def test_bilingual_highlight_never_leaves_one_line_plain(th, en):
    """
    Matching the colour is not the same as both lines having one. Re-running
    the other side with a colour hint only reorders which dictionary is tried
    -- a line with no listed keyword still came out plain, leaving a coloured
    Thai line above an all-white English one. Measured on a real 28-cue
    project, 10 cues were lopsided this way.
    """
    th_res, en_res = SubtitleEngine.apply_bilingual_kinetic_highlighting(
        th_text=th, en_text=en, primary_th="&H00FFFFFF&", primary_en="&H00EAEAEA&",
    )
    th_colors = re.findall(r"\{\\c(&H[0-9A-Fa-f]+&)\}", th_res)
    en_colors = re.findall(r"\{\\c(&H[0-9A-Fa-f]+&)\}", en_res)
    assert th_colors, f"Thai line left plain: {th_res!r}"
    assert en_colors, f"English line left plain: {en_res!r}"
    assert th_colors[0] == en_colors[0], "both lines must use the same highlight colour"


def test_missing_translations_are_retried_not_frozen(tmp_path, monkeypatch):
    """
    Cues that came back without an English line used to stay that way for
    good: generate_ass reused the stored translations whenever ANY cue had
    one, so a batch with gaps kept those gaps through every later render and
    re-roll. One project folder was missing English on 16 of its 25 cues.
    """
    import scripts.translator as translator_mod

    asked = []

    def fake_batch(phrases, custom_dict=None):
        asked.extend(phrases)
        return [f"EN::{p}" for p in phrases]

    monkeypatch.setattr(translator_mod.SubtitleTranslator, "translate_batch", staticmethod(fake_batch))

    cues = [
        {"id": 1, "start": 0.0, "end": 1.0, "text": "หนึ่ง", "translation": "one", "sfx": None},
        {"id": 2, "start": 1.0, "end": 2.0, "text": "สอง", "translation": "", "sfx": None},
        {"id": 3, "start": 2.0, "end": 3.0, "text": "สาม", "sfx": None},
    ]
    SubtitleEngine.generate_ass(
        cues=cues, output_ass_path=str(tmp_path / "retry.ass"), bilingual=True,
    )

    # only the gaps are re-sent, and the one that already had English is kept
    assert "หนึ่ง" not in asked, "a cue that already had English must not be re-translated"
    assert asked, "cues missing English must be sent for translation"


def test_bilingual_highlight_stays_in_one_meaning_group():
    """
    The keyword dictionaries are three parallel meaning groups (pain point /
    product / warning) in both languages. A colour hint used to only reorder
    which group was tried first, so when the hinted group had no match the
    line fell through to another group and took ITS colour: Thai lit
    "ด่วนเลย" yellow from the pain-point list while English lit
    "look at this" red from the warning list, on the same cue.
    """
    th_res, en_res = SubtitleEngine.apply_bilingual_kinetic_highlighting(
        th_text="ดูนี่ด่วนเลย!", en_text="Look at this quickly!",
        primary_th="&H00FFFFFF&", primary_en="&H00EAEAEA&",
    )
    th_colors = re.findall(r"\{\\c(&H[0-9A-Fa-f]+&)\}", th_res)
    en_colors = re.findall(r"\{\\c(&H[0-9A-Fa-f]+&)\}", en_res)
    assert th_colors and en_colors, "both lines must be highlighted"
    assert th_colors[0] == en_colors[0], (
        f"highlight switched meaning group: th={th_colors[0]} en={en_colors[0]}"
    )
    # and it must land on the counterpart word, not an unrelated phrase
    assert "quickly" in en_res.split("}")[1] or "quickly" in en_res


def test_bilingual_highlight_leaves_both_plain_when_neither_matches():
    """The consistent outcome for a pair with nothing worth emphasising is
    BOTH plain -- the fallback must not invent a highlight on one side."""
    th_res, en_res = SubtitleEngine.apply_bilingual_kinetic_highlighting(
        th_text="อืม", en_text="Um", primary_th="&H00FFFFFF&", primary_en="&H00EAEAEA&",
    )
    assert "{\\c" not in th_res and "{\\c" not in en_res


def _brand_pct(base=None, template=None):
    """
    What the brand tier's \\fscx actually ends up as. Sizes in subtitle_engine
    are em intents; the HookHeader Style's Fontsize now carries this face's
    1/ass_glyph_scale boost directly (rather than leaving Fontsize unboosted
    and pushing the boost onto \\fscx/\\fscy, which used to break the GPOS
    mark-to-mark anchor ั+่ ("นั่ง") at scale -- see font_size_boosted's
    comment in subtitle_engine.py), so \\fscx/\\fscy now carry the plain
    (unboosted) percent -- Fontsize alone accounts for the boost. Derived
    here rather than hardcoded, so changing a template's font or its tier
    size cannot turn these into magic numbers that quietly stop describing
    the code.
    """
    from scripts.hook_styles import resolve_hook_style

    style = resolve_hook_style(template)
    size_pct = style["tiers"]["brand"]["size_pct"] if base is None else base
    return round(size_pct)


def _hook_events(content: str) -> str:
    return "\n".join(l for l in content.splitlines() if l.startswith("Dialogue:") and "HookHeader" in l)


def _gen_hook_ass(tmp_path, name, hook_motion=None, hook_duration=3.0):
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=[{"id": 1, "start": 0.0, "end": 1.0, "text": "ทดสอบ", "sfx": None}],
        output_ass_path=str(tmp_path / f"{name}.ass"),
        hook_brand="Logitech",
        hook_model="Wave Keys",
        hook_label="Wireless Keyboard",
        hook_duration=hook_duration,
        hook_motion=hook_motion,
        bilingual=False,
    )
    return Path(ass_path).read_text(encoding="utf-8")


def test_hook_motion_default_preset_is_bounce_stagger_pulse_bar(tmp_path):
    combined = _hook_events(_gen_hook_ass(tmp_path, "default"))
    assert f"\\fscx{round(_brand_pct() * 1.25)}" in combined, "bounce overshoot keyframe missing"
    assert "&H25&" in combined, "pulse dim alpha missing"
    assert "\\p1" in combined, "accent bar drawing missing"
    assert "\\t(150," in combined, "model-tier stagger offset (150ms) missing"


def test_hook_motion_legacy_boolean_dict_falls_back_to_the_default_preset(tmp_path):
    """
    The pre-preset schema was 4 booleans (bounce/stagger/pulse/underline).
    None of those keys exist now, so an old saved manifest must land on the
    default preset rather than erroring or rendering an empty banner --
    that's what makes a migration step unnecessary.
    """
    legacy = _hook_events(_gen_hook_ass(
        tmp_path, "legacy", hook_motion={"bounce": True, "stagger": True, "pulse": True, "underline": True},
    ))
    assert legacy == _hook_events(_gen_hook_ass(tmp_path, "legacy_ref", hook_motion=None))


@pytest.mark.parametrize(
    "preset, marker",
    [
        ("bounce", lambda: f"\\fscx{round(_brand_pct() * 1.25)}"),   # overshoot
        ("pop", lambda: f"\\fscx{round(_brand_pct() * 1.18)}"),      # overshoot
        ("slam", lambda: f"\\fscx{round(_brand_pct() * 2.2)}"),      # slam impact start
        ("elastic_bounce", lambda: f"\\fscx{round(_brand_pct() * 1.28)}"),  # elastic overshoot
        ("fade", "\\alpha&HFF&\\t(0,250,\\alpha&H00&)"),
        ("zoom", lambda: f"\\fscx{round(_brand_pct() * 1.8)}"),      # zoom-in start
        ("slide_up", "\\move(540,341,540,221,0,300)"),
        ("blur", "\\blur12"),
        ("typewriter", "\\clip("),
        ("none", lambda: f"\\pos(540,221)\\fscx{_brand_pct()}\\fscy{_brand_pct()}\\t(2850"),
    ],
)
def test_each_in_preset_emits_its_own_technique(tmp_path, preset, marker):
    combined = _hook_events(_gen_hook_ass(
        tmp_path, f"in_{preset}", hook_motion={"in": preset, "loop": "none", "out": "fade", "accent": "none"},
    ))
    expected = marker() if callable(marker) else marker
    assert expected in combined, f"In preset '{preset}' did not emit {expected!r}"


@pytest.mark.parametrize(
    "preset, marker",
    [
        ("pulse", "\\alpha&H25&"),
        ("wave", "\\frz-3"),
        ("shake", "\\frz-2"),             # shake's 5-step cycle has an angle wave never uses
        ("flicker", "\\alpha&H30&"),
        ("none", None),
    ],
)
def test_each_loop_preset_emits_its_own_technique(tmp_path, preset, marker):
    combined = _hook_events(_gen_hook_ass(
        tmp_path, f"loop_{preset}", hook_motion={"in": "none", "loop": preset, "out": "fade", "accent": "none"},
    ))
    if marker is None:
        # "none" must leave only the entry/exit tags behind
        assert "\\frz" not in combined and "\\alpha&H25&" not in combined
    else:
        assert marker in combined, f"Loop preset '{preset}' did not emit {marker!r}"


def test_lightsweep_adds_an_overlay_event_per_line_not_a_tag(tmp_path):
    """
    The sweep can't ride on the base line: \\clip is single-state per event
    and the typewriter In preset already animates it. It must arrive as its
    own higher-layer duplicate of each line instead.
    """
    base = _hook_events(_gen_hook_ass(
        tmp_path, "sweep_off", hook_motion={"in": "none", "loop": "none", "out": "fade", "accent": "none"},
    )).splitlines()
    swept = _hook_events(_gen_hook_ass(
        tmp_path, "sweep_on", hook_motion={"in": "none", "loop": "lightsweep", "out": "fade", "accent": "none"},
    )).splitlines()
    overlays = [l for l in swept if l.startswith("Dialogue: 3,")]
    assert len(swept) == len(base) + len(overlays)
    assert overlays, "lightsweep emitted no overlay events"
    assert all("\\clip(" in l for l in overlays)


@pytest.mark.parametrize(
    "preset, marker",
    [
        ("fade", "\\t(2850,3000,\\alpha&HFF&)"),
        ("slide", "\\move(540,221,540,341,2850,3000)"),
        ("zoom", lambda: f"\\fscx{round(_brand_pct() * 1.4)}"),      # grow-out
        ("glitch", "\\t(2850,2890,\\frz-3)"),
        ("none", "\\t(2999,3000,\\alpha&HFF&)"),
    ],
)
def test_each_out_preset_emits_its_own_technique(tmp_path, preset, marker):
    combined = _hook_events(_gen_hook_ass(
        tmp_path, f"out_{preset}", hook_motion={"in": "none", "loop": "none", "out": preset, "accent": "none"},
    ))
    expected = marker() if callable(marker) else marker
    assert expected in combined, f"Out preset '{preset}' did not emit {expected!r}"


@pytest.mark.parametrize("preset, drawings", [("underline", 2), ("badge", 1), ("none", 0)])
def test_each_accent_preset_draws_the_right_number_of_shapes(tmp_path, preset, drawings):
    combined = _hook_events(_gen_hook_ass(
        tmp_path, f"acc_{preset}", hook_motion={"in": "none", "loop": "none", "out": "fade", "accent": preset},
    ))
    assert len([l for l in combined.splitlines() if "\\p1" in l]) == drawings


def test_accent_drawings_use_positive_path_coordinates(tmp_path):
    """
    libass mis-anchors a \\p drawing whose path uses negative coordinates --
    it lands with its right edge on \\pos instead of centred, which is what
    made the first accent bar sit visibly off to the left. Every shape must
    therefore be drawn from an all-positive path placed at its own left edge.
    """
    for preset in ("underline", "badge"):
        combined = _hook_events(_gen_hook_ass(
            tmp_path, f"pos_{preset}", hook_motion={"accent": preset},
        ))
        for line in combined.splitlines():
            if "\\p1" not in line:
                continue
            path = line.split("}")[-1]
            assert "-" not in path, f"{preset} drew a negative-coordinate path: {path!r}"
            assert "\\an7" in line, f"{preset} must anchor its drawing top-left"


def test_accent_reserves_layout_space_so_it_never_overlaps_the_label(tmp_path):
    """
    Consecutive tiers touch exactly (line-height factor 1.0), so an accent
    shape has no natural gap to sit in -- the label below has to be pushed
    down or the bar renders straight through it.
    """
    def label_y(motion):
        combined = _hook_events(_gen_hook_ass(tmp_path, f"space_{motion['accent']}", hook_motion=motion))
        label_line = [l for l in combined.splitlines() if "Wireless Keyboard" in l and "Dialogue: 2," in l][0]
        return int(label_line.split("\\pos(540,")[1].split(")")[0])

    without = label_y({"in": "none", "loop": "none", "out": "fade", "accent": "none"})
    with_bar = label_y({"in": "none", "loop": "none", "out": "fade", "accent": "underline"})
    assert with_bar > without, "accent bar must push the label tier down, not draw over it"


def test_hook_colors_override_each_tier_independently(tmp_path):
    """
    A brand with its own colour equity must be able to recolour just its own
    tier; tiers left unset keep the poster defaults (white / accent / muted).
    """
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=[{"id": 1, "start": 0.0, "end": 1.0, "text": "ทดสอบ", "sfx": None}],
        output_ass_path=str(tmp_path / "colors.ass"),
        hook_brand="Logitech", hook_model="Wave Keys", hook_label="Wireless Keyboard",
        hook_duration=3.0, hook_colors={"brand": "#00FF66"}, bilingual=False,
    )
    combined = _hook_events(Path(ass_path).read_text(encoding="utf-8"))
    brand_line = [l for l in combined.splitlines() if "LOGITECH" in l and "Dialogue: 2," in l][0]
    label_line = [l for l in combined.splitlines() if "Wireless Keyboard" in l and "Dialogue: 2," in l][0]
    assert "\\c&H0066FF00&" in brand_line, "brand tier must take the override (ASS is &HBBGGRR)"
    assert "\\c&H00E0E0E0&" in label_line, "an unset tier must keep its default colour"


def test_lightsweep_overlay_matches_the_scale_of_the_line_it_shadows(tmp_path):
    """
    The sweep copy has to carry the same \\fscx/\\fscy as its base line. At
    the style's default 100% it rendered as a visibly different-sized ghost
    of the 130% brand and 58% label tiers instead of a shimmer over them.
    """
    combined = _hook_events(_gen_hook_ass(
        tmp_path, "sweep_scale", hook_motion={"in": "none", "loop": "lightsweep", "out": "fade", "accent": "none"},
    ))
    base = {}
    for line in combined.splitlines():
        if line.startswith("Dialogue: 2,"):
            base[line.split("}")[-1]] = line.split("\\fscx")[1].split("\\")[0]
    for line in combined.splitlines():
        if not line.startswith("Dialogue: 3,"):
            continue
        text = line.split("}")[-1]
        assert f"\\fscx{base[text]}" in line, f"sweep for {text!r} does not match its line's scale"


@pytest.mark.parametrize("preset_kind, preset", [("loop", "wave"), ("loop", "shake"), ("out", "glitch")])
def test_rotation_presets_use_signed_angles_not_wrapped_ones(tmp_path, preset_kind, preset):
    """
    \\t interpolates linearly toward its target, so a -3 degree tilt written
    as 357 sweeps the long way round through 180 and flips the line on its
    head mid-step -- which is exactly what the glitch exit did before.
    """
    motion = {"in": "none", "loop": "none", "out": "fade", "accent": "none"}
    motion[preset_kind] = preset
    combined = _hook_events(_gen_hook_ass(tmp_path, f"rot_{preset}", hook_motion=motion))
    assert "\\frz" in combined, f"{preset} emitted no rotation at all"
    for angle in re.findall(r"\\frz(-?\d+)", combined):
        assert abs(int(angle)) <= 45, f"{preset} used a wrapped angle {angle} that will spin the line"


def test_preset_catalog_matches_the_builder_registries(client):
    """
    The catalog is only labels; the animations live in subtitle_engine's
    registries. A preset listed in one but missing from the other would show
    up as a picker option that silently renders as something else (or an
    animation nobody can select), so the two must stay in lockstep.
    """
    from scripts.subtitle_engine import (
        HOOK_IN_BUILDERS, HOOK_LOOP_BUILDERS, HOOK_OUT_BUILDERS, DEFAULT_HOOK_MOTION,
    )
    from scripts.hook_motion_presets import HOOK_ACCENT_PRESETS

    catalog = client.get("/api/hook-motion-presets").json()["catalog"]
    # typewriter is built inline (it needs resolved line geometry), so it is
    # catalogued without a registry entry -- every other In preset pairs up.
    assert set(catalog["in"]) == set(HOOK_IN_BUILDERS) | {"typewriter"}
    assert set(catalog["loop"]) == set(HOOK_LOOP_BUILDERS)
    assert set(catalog["out"]) == set(HOOK_OUT_BUILDERS)
    assert set(catalog["accent"]) == set(HOOK_ACCENT_PRESETS)

    for category, chosen in DEFAULT_HOOK_MOTION.items():
        if category == "stagger":
            continue
        assert chosen in catalog[category], f"default {category}={chosen!r} isn't in its own catalog"


def test_hook_motion_loop_skips_cleanly_when_duration_too_short(tmp_path):
    """A short hook_duration leaves no room for even one pulse half-cycle --
    it must degrade to no pulse, not emit a broken/negative-range \\t tag."""
    combined = _hook_events(_gen_hook_ass(tmp_path, "short", hook_duration=1.2))
    assert "&H25&" not in combined
    assert "\\p1" in combined, "the accent (independent of loop) must still render"


def test_measure_text_width_px_uses_real_font_metrics():
    from scripts.subtitle_engine import _measure_text_width_px

    font_map = _load_font_family_map()
    resolved = font_map.get("IBMPlex", "IBM Plex Sans Thai")
    w_short = _measure_text_width_px("AB", resolved, 60)
    w_long = _measure_text_width_px("ABCDEFGH", resolved, 60)
    assert w_short is not None and w_long is not None, "font file must resolve to a real path, not fall back silently"
    assert w_long > w_short, "more characters must measure wider than a flat per-tier fallback would give"


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
        hook_brand="ทดสอบ",
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


def test_angle_key_resolves_to_the_right_shot_scales_via_pipeline(tmp_path, monkeypatch):
    """End-to-end through pipeline.run(), not just a dict lookup in isolation."""
    from unittest.mock import patch
    from scripts.pipeline import TikTokAutoCutterPipeline
    from scripts.stages import source_resolution

    raw_video = next(Path("01_Raw").rglob("*.mov"), None) or next(Path("01_Raw").rglob("*.mp4"), None)
    if raw_video is None:
        pytest.skip("no raw video available in 01_Raw to render against")

    # Redirect every module that has its own bound PROJECTS_DIR name -- per
    # .agents/rules/testing_standard.md rule 3, this must never touch the
    # real 03_Projects/. source_resolution is what actually mkdir()s the
    # project folder; project_manifest is what reads/writes project.json.
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(source_resolution, "PROJECTS_DIR", target)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)

    project_name = "TEST_look_preset_resolution"
    captured = {}

    def fake_assemble(**kwargs):
        captured["shot_scales"] = kwargs.get("shot_scales")
        return "/fake/out.mp4"

    with patch("scripts.pipeline.VideoEditor.assemble_tiktok_video", side_effect=fake_assemble):
        TikTokAutoCutterPipeline.run(
            product_name="test", project_name=project_name,
            raw_video_path=str(raw_video), custom_script="ทดสอบ",
            voice_engine_type="edge_tts", export_mp4=True, use_ai_vision=False,
            angle_meta={"angle_key": "fake_vs_real"},
        )
    assert captured["shot_scales"] == LOOK_PRESETS["fake_vs_real"]


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
            total_duration=assemble_kwargs.pop("total_duration", 5.0),
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


def test_assemble_video_probes_a_shared_source_once(monkeypatch, tmp_path):
    from scripts.video_editor import VideoEditor

    source = tmp_path / "shared.mp4"
    clip_list = [
        {"source_path": str(source), "trim_start": float(index), "trim_end": float(index + 1)}
        for index in range(4)
    ]
    probes = []
    monkeypatch.setattr(
        VideoEditor,
        "get_media_info",
        staticmethod(lambda path: probes.append(path) or {"duration": 9.0, "width": 1080, "height": 1920, "has_audio": False}),
    )

    _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)

    assert probes == [os.path.normcase(str(source.resolve()))]


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


def test_assemble_video_clip_list_named_transition_reaches_the_filter(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list,
        transitions=[{"type": "wipeleft", "duration": 0.8}],
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade=transition=wipeleft:duration=0.8" in filter_arg
    assert "offset=2.2" in filter_arg, "3s clip minus a 0.8s overlap starts the wipe at 2.2s"


def test_assemble_video_unknown_transition_falls_back_to_fade(monkeypatch, tmp_path):
    # The name comes from the UI; an unknown one must never reach ffmpeg,
    # where it would kill the whole render.
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list,
        transitions=[{"type": "not-a-real-transition", "duration": 0.5}],
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade=transition=fade" in filter_arg
    assert "not-a-real-transition" not in filter_arg


def test_transition_duration_is_clamped_to_what_the_clips_can_give(monkeypatch, tmp_path):
    # A 2s transition across a 1s clip would make xfade's offset negative.
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 1.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 1.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list,
        transitions=[{"type": "circleopen", "duration": 2.0}],
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "duration=0.95" in filter_arg, "capped at min(clip)-0.05, not the requested 2.0"
    assert "offset=-" not in filter_arg


def test_clip_colour_only_reaches_ffmpeg_when_changed(monkeypatch, tmp_path):
    from scripts.video_editor import build_eq_filter

    assert build_eq_filter({}) == ""
    assert build_eq_filter({"brightness": 0.0, "contrast": 1.0, "saturation": 1.0}) == "",         "default values must not add a filter (and its render cost) to the chain"
    assert build_eq_filter({"contrast": 99}) == "eq=contrast=2.0,", "clamped to EQ_LIMITS"
    assert build_eq_filter({"saturation": "junk"}) == "", "garbage is ignored, not raised"

    clip_list = [{
        "source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0,
        "saturation": 0.0, "brightness": 0.12,
    }]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "eq=" in filter_arg and "saturation=0.0" in filter_arg and "brightness=0.12" in filter_arg


def test_lut_intensity_below_full_blends_instead_of_grading_outright(monkeypatch, tmp_path):
    lut = tmp_path / "grade.cube"
    lut.write_text("LUT_3D_SIZE 2\n" + "0 0 0\n" * 8, encoding="utf-8")
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0}]

    full = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, lut_path=str(lut),
    )
    full_filter = full[full.index("-filter_complex") + 1]
    assert "lut3d=" in full_filter
    assert "blend=" not in full_filter, "full strength must stay on the cheap single-pass path"

    half = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list,
        lut_path=str(lut), lut_intensity=0.4,
    )
    half_filter = half[half.index("-filter_complex") + 1]
    assert "blend=all_mode=normal:all_opacity=0.4" in half_filter
    assert "split=2[lut_src][lut_in]" in half_filter


def test_frame_geometry_clamps_zoom_and_keeps_the_crop_inside_the_frame():
    from scripts.video_editor import frame_geometry
    from scripts.config import VIDEO_WIDTH, VIDEO_HEIGHT

    scale, cx, cy, w, h = frame_geometry({}, 1.08)
    assert scale == 1.08, "no per-clip zoom keeps the alternating punch-zoom"

    # pan hard to both extremes: ffmpeg errors on a crop starting outside the
    # scaled image, so both ends must stay in range
    for pan in (-1, 1, -5, 5):
        scale, cx, cy, w, h = frame_geometry({"zoom": 2.0, "pan_x": pan, "pan_y": pan}, 1.08)
        assert 0 <= cx <= w - VIDEO_WIDTH
        assert 0 <= cy <= h - VIDEO_HEIGHT

    assert frame_geometry({"zoom": 99}, 1.08)[0] == 3.0, "zoom clamped to ZOOM_LIMITS"
    assert frame_geometry({"zoom": "junk"}, 1.08)[0] == 1.08, "garbage falls back"


def test_freeze_tail_extends_the_clip_and_its_timeline_slot(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0, "freeze_tail": 1.5},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list,
        transitions=[{"type": "fade", "duration": 0.4}], total_duration=99.0,
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=1.5" in filter_arg
    # the frozen 1.5s has to count towards the clip's slot, or the xfade after
    # it starts in the wrong place -- 3.0 + 1.5 - 0.4 = 4.1
    assert "offset=4.1" in filter_arg


def test_short_video_holds_its_last_frame_instead_of_ending_early(monkeypatch, tmp_path):
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 4.0}]

    short = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, total_duration=12.0,
    )
    short_filter = short[short.index("-filter_complex") + 1]
    assert "[v_filled]" in short_filter, "4s of clips under 12s of audio must be padded"

    plenty = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, total_duration=3.0,
    )
    plenty_filter = plenty[plenty.index("-filter_complex") + 1]
    assert "[v_filled]" not in plenty_filter, "video longer than the audio needs no padding"


def _quality_setting(cmd):
    """
    The encode-effort knob in use, whichever encoder ran. Asserting on x264's
    `-crf`/`-preset` alone broke the moment a machine with a usable hardware
    encoder was the one running the tests.
    """
    for flag in ("-crf", "-qp_i", "-global_quality", "-qp"):
        if flag in cmd:
            return flag, cmd[cmd.index(flag) + 1]
    raise AssertionError(f"no quality setting in {cmd}")


def test_draft_export_scales_down_and_lowers_encode_effort(monkeypatch, tmp_path):
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0}]

    post = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    post_flag, post_quality = _quality_setting(post)
    post_filter = post[post.index("-filter_complex") + 1]
    assert "[v_subbed]" not in post_filter, "post quality must not add a scale pass"

    draft = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, export_preset="draft",
    )
    draft_flag, draft_quality = _quality_setting(draft)
    assert draft_flag == post_flag, "both presets should drive the same encoder"
    # Draft asks for less: a higher crf, or a higher qp, is coarser and faster.
    assert int(draft_quality) > int(post_quality)
    draft_filter = draft[draft.index("-filter_complex") + 1]
    assert "scale=720:1280" in draft_filter
    # subtitles burn before the downscale -- the .ass coordinates assume 1080
    assert draft_filter.index("subtitles=") < draft_filter.index("scale=720:1280")


def test_unknown_export_preset_falls_back_to_post(monkeypatch, tmp_path):
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0}]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, export_preset="nonsense",
    )
    _, quality = _quality_setting(cmd)
    post = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    assert quality == _quality_setting(post)[1], "an unknown preset must render like post"
    assert "scale=720:1280" not in cmd[cmd.index("-filter_complex") + 1]


def test_caption_style_lands_in_the_ass_header(tmp_path):
    from scripts.subtitle_engine import SubtitleEngine, ass_colour

    assert ass_colour("#FFE600") == "&H0000E6FF", "ASS is &HAABBGGRR, not RGB"
    assert ass_colour("nope") == "", "unparseable colour falls back, never crashes the render"

    cues = [{"id": 1, "start": 0.0, "end": 2.0, "text": "ทดสอบ"}]
    out = tmp_path / "subs.ass"
    SubtitleEngine.generate_ass(
        cues=cues, output_ass_path=str(out), font_name="IBMPlex", bilingual=False,
        caption_position="top", caption_color="#FFE600", caption_scale=1.5,
    )
    header = out.read_text(encoding="utf-8")
    white = next(l for l in header.splitlines() if l.startswith("Style: TikTokWhite"))
    fields = white.split(",")
    assert fields[3] == "&H0000E6FF", "primary colour"
    assert fields[18] == "8", "alignment 8 = top centre"
    assert fields[21] == "260", "top margin"
    # Derived from the one tuned constant rather than a list of magic numbers:
    # base_fs = round(video_width * 0.0463) in subtitle_engine.py, times the
    # 1.5 caption_scale above, times the resolved font's own em-vs-line-box
    # boost (Style Fontsize now carries that boost directly -- see
    # font_size_boosted's comment in subtitle_engine.py -- rather than
    # leaving Fontsize unboosted and pushing it onto \fscx/\fscy, which used
    # to break the GPOS mark-to-mark anchor ั+่ ("นั่ง") at scale). Retuning
    # the 0.0463 ratio must be a deliberate act that updates this line AND
    # the canvas side (guarded by tests/test_preview_render_parity.py),
    # never a silent drift.
    from scripts.subtitle.font_metrics import ass_glyph_scale
    ibm_plex_boost = 1.0 / ass_glyph_scale("IBM Plex Sans Thai")
    unboosted = max(24, round(round(1080 * 0.0463) * 1.5))
    assert int(fields[2]) == round(unboosted * ibm_plex_boost), "scaled font size"


def test_sticker_geometry_corners_and_clamped_size():
    from scripts.video_editor import sticker_geometry

    w, x, y = sticker_geometry("top_right", 1.0)
    assert (w, x, y) == (320, "(W-w-80)", "280")
    assert sticker_geometry("bottom_left", 1.0)[1:] == ("80", "(H-h-840)")
    assert sticker_geometry("junk", 1.0)[1:] == ("(W-w-80)", "280"), "unknown corner falls back"
    assert sticker_geometry("top_left", 99)[0] == 1120, "scale clamped to 3.5x"
    assert sticker_geometry("top_left", 1.0)[0] % 2 == 0, "even width or libx264 complains"


def test_sticker_position_reaches_the_overlay(monkeypatch, tmp_path):
    badge = tmp_path / "badge.png"
    badge.write_bytes(bytes([0x89, 0x50, 0x4E, 0x47]))   # only has to exist
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0}]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list,
        sticker_path=str(badge), sticker_position="bottom_left", sticker_scale=1.5,
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "scale=480:-1" in filter_arg
    assert "overlay=x=80:y=(H-h-840)" in filter_arg


def test_normalize_transitions_shapes():
    from scripts.video_editor import normalize_transitions, DEFAULT_TRANSITION_DURATION

    out = normalize_transitions(["fade", "cut", {"type": "slideup", "duration": 0.6}])
    assert out[0] == {"type": "fade", "duration": DEFAULT_TRANSITION_DURATION}
    assert out[1]["type"] == "cut"
    assert out[2] == {"type": "slideup", "duration": 0.6}

    # garbage duration falls back instead of raising
    assert normalize_transitions([{"type": "fade", "duration": "abc"}])[0]["duration"] == DEFAULT_TRANSITION_DURATION
    # and durations stay inside the supported window
    assert normalize_transitions([{"type": "fade", "duration": 99}])[0]["duration"] == 2.0
    assert normalize_transitions([{"type": "fade", "duration": 0}])[0]["duration"] == 0.1


def test_reroll_sticker_badge_resolves_to_a_real_path(tmp_path):
    from scripts.api_phase1 import RerollRequest
    from scripts.config import STICKERS_DIR

    badges = sorted(STICKERS_DIR.glob("*.png"))
    assert badges, "no sticker assets on disk to test with"

    def overrides_for(badge):
        req = RerollRequest(project_name="p", part="video", sticker_badge=badge)
        o = req.model_dump(exclude={"project_name", "part"}, exclude_none=True)
        # mirrors trigger_reroll's resolution block
        if "sticker_badge" in o:
            name = o.pop("sticker_badge")
            resolved = ""
            if name:
                cand = STICKERS_DIR / name
                if cand.exists():
                    resolved = str(cand)
            o["sticker_path"] = resolved
        return o

    picked = overrides_for(badges[0].name)
    assert picked["sticker_path"] == str(badges[0])

    # "" means "no badge" -- and it must survive _execute_reroll's
    # `if v is not None` merge, or the badge already on the project would stay.
    cleared = overrides_for("")
    assert cleared["sticker_path"] == ""
    assert cleared["sticker_path"] is not None


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


# ----------------------------------------------------------------------
# GET /api/editor/filmstrip -- timeline thumbnails
#
# ffmpeg itself is mocked here (the real two-clip render was verified live);
# these lock in the caching, clamping and path-guard behavior.
# ----------------------------------------------------------------------
@pytest.fixture
def filmstrip_dir(tmp_path, monkeypatch):
    from scripts import api_editor
    target = tmp_path / "filmstrips"
    monkeypatch.setattr(api_editor, "FILMSTRIP_DIR", target)
    return target


def _fake_ffmpeg(out_index):
    """Stand-in for subprocess.run that just writes the output file it's told to."""
    from unittest.mock import MagicMock

    def run(cmd, **kwargs):
        Path(cmd[out_index[0] if isinstance(out_index, tuple) else -1]).write_bytes(b"\xff\xd8jpg")
        return MagicMock(returncode=0, stderr="")
    return run


def test_filmstrip_renders_then_serves_from_cache(client, filmstrip_dir, tmp_path, monkeypatch):
    from unittest.mock import patch
    from scripts import api_editor

    source = tmp_path / "clip.mp4"
    source.write_bytes(b"x" * 2048)
    monkeypatch.setattr(api_editor, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_editor.VideoEditor, "get_media_info",
                        classmethod(lambda cls, p: {"duration": 20.0}))

    calls = []

    def fake_run(cmd, **kwargs):
        from unittest.mock import MagicMock
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"\xff\xd8jpg")
        return MagicMock(returncode=0, stderr="")

    with patch("scripts.api_editor.subprocess.run", side_effect=fake_run):
        first = client.get("/api/editor/filmstrip", params={"path": "clip.mp4", "count": 4})
        assert first.status_code == 200
        assert first.headers["content-type"] == "image/jpeg"
        # 4 input-seek grabs + 1 hstack -- not one whole-file decode
        assert len(calls) == 5
        assert any("-ss" in c for c in calls[:4])

        calls.clear()
        second = client.get("/api/editor/filmstrip", params={"path": "clip.mp4", "count": 4})
        assert second.status_code == 200
        assert calls == [], "second request must hit the cached sprite, not ffmpeg"


def test_filmstrip_clamps_absurd_frame_counts(client, filmstrip_dir, tmp_path, monkeypatch):
    from unittest.mock import patch
    from scripts import api_editor

    source = tmp_path / "clip.mp4"
    source.write_bytes(b"x" * 2048)
    monkeypatch.setattr(api_editor, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_editor.VideoEditor, "get_media_info",
                        classmethod(lambda cls, p: {"duration": 20.0}))

    grabs = []

    def fake_run(cmd, **kwargs):
        from unittest.mock import MagicMock
        if "-ss" in cmd:
            grabs.append(cmd)
        Path(cmd[-1]).write_bytes(b"\xff\xd8jpg")
        return MagicMock(returncode=0, stderr="")

    with patch("scripts.api_editor.subprocess.run", side_effect=fake_run):
        assert client.get("/api/editor/filmstrip", params={"path": "clip.mp4", "count": 9999}).status_code == 200
    assert len(grabs) == api_editor.MAX_FRAMES, "must cap frames, not spawn 9999 ffmpeg calls"


def test_filmstrip_refuses_paths_outside_the_project(client, filmstrip_dir):
    response = client.get("/api/editor/filmstrip", params={"path": "C:/Windows/win.ini"})
    assert response.status_code == 403


def test_filmstrip_404s_for_a_missing_clip(client, filmstrip_dir, tmp_path, monkeypatch):
    from scripts import api_editor
    monkeypatch.setattr(api_editor, "BASE_DIR", tmp_path)
    assert client.get("/api/editor/filmstrip", params={"path": "nope.mp4"}).status_code == 404


def test_clip_speed_shrinks_its_slot_and_emits_setpts(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 4.0},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 4.0, "speed": 2.0},
    ]
    cmd = _capture_ffmpeg_cmd(
        monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list, transitions=["fade"]
    )
    filter_arg = cmd[cmd.index("-filter_complex") + 1]

    assert "setpts=PTS/2.0" in filter_arg, "2x clip must scale presentation timestamps"
    # trim still pulls the full 4s span from the source; speed is what halves it
    assert "duration=4.0" in filter_arg
    # xfade offset proves clip_durations used the post-speed 2.0s, not 4.0s:
    # clip A (4.0s) minus the 0.4s overlap => 3.6
    assert "offset=3.5999999999999996" in filter_arg or "offset=3.6" in filter_arg


def test_clip_mirror_flips_only_the_marked_clip(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0, "mirror": True},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0},
    ]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    filter_arg = cmd[cmd.index("-filter_complex") + 1]

    # Check the per-clip segments, not the whole graph: the subtitle path in
    # the final segment carries pytest's tmp dir name, which would otherwise
    # match whatever this test is called.
    segments = {
        f"clip_{i}": part
        for part in filter_arg.split(";")
        for i in (0, 1)
        if part.endswith(f"[clip_{i}]")
    }
    assert "hflip" in segments["clip_0"], "the mirrored clip must be flipped"
    assert "hflip" not in segments["clip_1"], "its neighbour must not be"


def test_clip_speed_is_clamped_to_a_sane_range(monkeypatch, tmp_path):
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 4.0, "speed": 99}]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "setpts=PTS/4.0" in filter_arg, "absurd speeds clamp to 4x instead of producing a 0-frame clip"


def test_clip_without_speed_or_mirror_is_byte_identical_to_before(monkeypatch, tmp_path):
    """The plain path must not gain a stray setpts/hflip -- 1-Click Studio uses it."""
    clip_list = [{"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0}]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "hflip" not in filter_arg
    assert "setpts=PTS/" not in filter_arg
    assert "setpts=PTS-STARTPTS" in filter_arg


def test_clip_rotation_emits_transpose_and_flips(monkeypatch, tmp_path):
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0, "rotation": 90},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0, "rotation": 180},
        {"source_path": str(tmp_path / "c.mp4"), "trim_start": 0.0, "trim_end": 3.0, "rotation": 270},
    ]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "transpose=1" in filter_arg, "90 deg CW uses transpose=1"
    assert "hflip,vflip" in filter_arg, "180 deg uses hflip,vflip"
    assert "transpose=2" in filter_arg, "270 deg uses transpose=2"


def test_clip_audio_volume_blends_into_master(monkeypatch, tmp_path):
    from scripts.video_editor import VideoEditor
    monkeypatch.setattr(VideoEditor, "get_media_info", lambda p: {"duration": 5.0, "width": 1080, "height": 1920, "rotation": 0, "has_audio": True})
    clip_list = [
        {"source_path": str(tmp_path / "a.mp4"), "trim_start": 0.0, "trim_end": 3.0, "volume": 0.6},
        {"source_path": str(tmp_path / "b.mp4"), "trim_start": 0.0, "trim_end": 3.0, "volume": 0.0},
    ]
    cmd = _capture_ffmpeg_cmd(monkeypatch, tmp_path, raw_video_paths=[], clip_list=clip_list)
    filter_arg = cmd[cmd.index("-filter_complex") + 1]
    assert "volume=0.6" in filter_arg
    assert "amix=inputs=2" in filter_arg
    assert "-map" in cmd and "[a_final]" in cmd


def test_j_cut_rules_and_timing():
    from scripts.config import J_CUT_OFFSET_SECONDS
    from pathlib import Path

    assert 0.10 <= J_CUT_OFFSET_SECONDS <= 0.30, "J-Cut offset must be between 100ms and 300ms for TikTok pacing"

    # Verify J-Cut rule documentation exists and is linked in AGENTS.md
    rule_file = Path(".agents/rules/j_cut_rules.md")
    assert rule_file.exists(), "j_cut_rules.md must exist in .agents/rules/"
    agents_md = Path("AGENTS.md").read_text(encoding="utf-8")
    assert "j_cut_rules.md" in agents_md, "AGENTS.md must reference j_cut_rules.md"


def test_kinetic_subtitles_and_rules():
    from scripts.subtitle_engine import SubtitleEngine
    from pathlib import Path

    # Verify kinetic highlighting applies inline color tags
    raw_sample = "ทุกคน! ใครปวดข้อมือ ดูคลิปนี้เลย"
    highlighted = SubtitleEngine.apply_kinetic_highlighting(raw_sample, "&H00FFFFFF&")
    assert "{\\c&H0000E6FF&}ปวดข้อมือ{\\c&H00FFFFFF&}" in highlighted, "Pain point keyword must be highlighted in neon yellow"

    # Verify feature keyword highlighting
    raw_feature = "อันนี้คือคีย์บอร์ด Logitech สรีรศาสตร์"
    highlighted_feat = SubtitleEngine.apply_kinetic_highlighting(raw_feature, "&H00FFFFFF&")
    assert "{\\c&H00FFE600&}" in highlighted_feat, "Feature/tech keyword must be highlighted in electric cyan"

    # Verify rule documentation exists and is linked in AGENTS.md
    rule_file = Path(".agents/rules/subtitle_kinetic_rules.md")
    assert rule_file.exists(), "subtitle_kinetic_rules.md must exist in .agents/rules/"
    agents_md = Path("AGENTS.md").read_text(encoding="utf-8")
    assert "subtitle_kinetic_rules.md" in agents_md, "AGENTS.md must reference subtitle_kinetic_rules.md"





def _pipeline_run_kwargs(raw_video, project_name):
    return dict(
        product_name="test", project_name=project_name,
        raw_video_path=str(raw_video), custom_script="ทดสอบเสียง",
        voice_engine_type="edge_tts", use_ai_vision=False,
    )


def test_one_click_does_not_bake_the_audio_mix(tmp_path, monkeypatch):
    """
    The mix exists for the ffmpeg render alone -- the editor previews the
    stems. Baking it during a 1-Click that stops at the timeline only froze
    the BGM and SFX picks before the user had seen them, so no mix should be
    written and no mixed_audio artifact recorded.
    """
    from unittest.mock import patch
    from scripts.pipeline import TikTokAutoCutterPipeline
    from scripts.stages import source_resolution

    raw_video = next(Path("01_Raw").rglob("*.mov"), None) or next(Path("01_Raw").rglob("*.mp4"), None)
    if raw_video is None:
        pytest.skip("no raw video available in 01_Raw")

    # Per .agents/rules/testing_standard.md rule 3 -- never the real
    # 03_Projects/. source_resolution mkdir()s the project folder;
    # project_manifest reads/writes project.json.
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(source_resolution, "PROJECTS_DIR", target)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)

    project_name = "TEST_no_mix_on_create"
    with patch("scripts.pipeline.SFXManager.mix_audio_track") as mixer:
        TikTokAutoCutterPipeline.run(export_mp4=False, **_pipeline_run_kwargs(raw_video, project_name))
    assert not mixer.called, "1-Click must not mix audio"

    manifest = ProjectManifest.load(project_name)
    assert "mixed_audio" not in (manifest.get("artifacts") or {}), (
        "recording a mix that was never written is what made the reuse path "
        "trust a missing file"
    )
    assert (manifest.get("artifacts") or {}).get("voice_audio"), "the voice stem is still needed"


def test_render_mixes_on_demand_when_no_mix_exists_yet(tmp_path, monkeypatch):
    """
    The editor's Render button resumes from "subtitles", which reports the mix
    stage as already done. After a 1-Click that skipped mixing there is no file
    to reuse, and the old code raised FileNotFoundError instead of just mixing.
    """
    from unittest.mock import patch
    from scripts.pipeline import TikTokAutoCutterPipeline
    from scripts.stages import source_resolution

    raw_video = next(Path("01_Raw").rglob("*.mov"), None) or next(Path("01_Raw").rglob("*.mp4"), None)
    if raw_video is None:
        pytest.skip("no raw video available in 01_Raw")

    # Per .agents/rules/testing_standard.md rule 3 -- never the real
    # 03_Projects/. source_resolution mkdir()s the project folder;
    # project_manifest reads/writes project.json.
    target = tmp_path / "03_Projects"
    target.mkdir()
    monkeypatch.setattr(source_resolution, "PROJECTS_DIR", target)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)

    project_name = "TEST_mix_on_demand"
    with patch("scripts.pipeline.SFXManager.mix_audio_track"):
        TikTokAutoCutterPipeline.run(export_mp4=False, **_pipeline_run_kwargs(raw_video, project_name))

    def fake_mix(**kwargs):
        Path(kwargs["output_audio_path"]).write_bytes(b"RIFF fake wav")
        return kwargs["output_audio_path"]

    with patch("scripts.pipeline.SFXManager.mix_audio_track", side_effect=fake_mix) as mixer, \
         patch("scripts.pipeline.VideoEditor.assemble_tiktok_video", return_value="/fake/out.mp4"):
        TikTokAutoCutterPipeline.run(
            export_mp4=True, resume_from="subtitles",
            **_pipeline_run_kwargs(raw_video, project_name),
        )
    assert mixer.called, "a render with no mix on disk has to make one"

    manifest = ProjectManifest.load(project_name)
    assert (manifest.get("artifacts") or {}).get("mixed_audio"), "now it exists, so record it"
