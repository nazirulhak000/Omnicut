# -*- coding: utf-8 -*-
"""Automatic in-place TikTok sharpness after a render (plan item C2).

Offline: temp storage and a fake encoder, except the last test, which runs the
real enhancer on a generated clip inside the temp storage root.
"""
import shutil
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_exports
from scripts import api_phase1
from scripts import api_render
from scripts import auto_sharpen
from scripts import batch_render
from scripts import media_validation
from scripts import product_store as ps
from scripts import render_jobs
from scripts import tiktok_enhancer
from scripts.db import DocumentTable
from scripts.export_registry import TIKTOK_SHARP_FIELD, ExportRegistry
from tests.test_auto_cover import _batch_render, _editor_render, _first_render

CHANNEL = "main"
EXPORT_ID = "export_clip"
RENDERED = b"rendered clip"


@pytest.fixture
def studio(isolated_storage, monkeypatch):
    """One registered export and an encoder that only rewrites bytes."""
    root = isolated_storage
    monkeypatch.delenv(auto_sharpen.ENV_SWITCH, raising=False)
    video = root / "04_Exports" / CHANNEL / "20261112_clip_hook_v1.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(RENDERED)
    docs = root / "_Docs"
    DocumentTable("export_registry", lambda: docs / "store.db", lambda: docs / "export_registry.json").save([
        {"id": EXPORT_ID, "channel_id": CHANNEL, "path": video.relative_to(root).as_posix()},
        {"id": "export_other", "channel_id": "other", "path": "04_Exports/other/20261112_other_hook_v1.mp4"},
    ])
    product = ps.ProductStore.add(
        name="Auto Sharp Product",
        angles=[{"angle_id": "a1", "project_name": "clip_project", "status": "rendered"}],
    )

    calls = []

    def fake_enhance(input_path, output_path=None, **kwargs):
        calls.append((input_path, output_path))
        output_path.write_bytes(b"sharp:" + input_path.read_bytes())
        return output_path

    monkeypatch.setattr(tiktok_enhancer, "enhance_video_for_tiktok", fake_enhance)

    class Studio:
        pass

    s = Studio()
    s.root, s.video, s.product_id, s.calls = root, video, product["id"], calls
    s.record = lambda: ExportRegistry.get(EXPORT_ID, channel_id=CHANNEL)
    s.run = lambda: auto_sharpen.ensure_tiktok_sharp(EXPORT_ID, channel_id=CHANNEL)
    return s


# --- the step itself ---------------------------------------------------------

def test_render_is_sharpened_in_place_and_marked(studio):
    outcome = studio.run()

    assert outcome["status"] == "sharpened", outcome
    assert studio.calls == [(studio.video, studio.video)]  # same file in and out
    assert studio.video.read_bytes() == b"sharp:" + RENDERED
    assert [p.name for p in studio.video.parent.iterdir()] == [studio.video.name]
    record = studio.record()
    assert record["path"] == studio.video.relative_to(studio.root).as_posix()
    assert record[TIKTOK_SHARP_FIELD]["size"] == studio.video.stat().st_size
    assert auto_sharpen.is_sharpened(record, studio.video)


def test_sharpened_clip_is_not_sharpened_twice(studio):
    studio.run()

    outcome = studio.run()

    assert outcome == {"status": "kept", "reason": "already_sharp"}
    assert len(studio.calls) == 1
    assert studio.video.read_bytes() == b"sharp:" + RENDERED


def test_re_render_to_the_same_path_is_sharpened_again(studio):
    studio.run()
    studio.video.write_bytes(b"second render, different length")  # what a re-render does
    assert not auto_sharpen.is_sharpened(studio.record(), studio.video)

    outcome = studio.run()

    assert outcome["status"] == "sharpened"
    assert studio.video.read_bytes() == b"sharp:second render, different length"
    assert auto_sharpen.is_sharpened(studio.record(), studio.video)


def test_encoder_failure_keeps_the_render_and_is_not_raised(studio, monkeypatch):
    def broken(input_path, output_path=None, **kwargs):
        raise RuntimeError("encoder exploded")

    monkeypatch.setattr(tiktok_enhancer, "enhance_video_for_tiktok", broken)

    outcome = studio.run()

    assert outcome["status"] == "failed" and "encoder exploded" in outcome["reason"]
    assert studio.video.read_bytes() == RENDERED
    assert TIKTOK_SHARP_FIELD not in studio.record()
    assert not auto_sharpen.is_sharpened(studio.record(), studio.video)


def test_failed_pass_after_a_re_render_does_not_leave_the_clip_marked(studio, monkeypatch):
    studio.run()
    studio.video.write_bytes(b"second render, different length")
    monkeypatch.setattr(tiktok_enhancer, "enhance_video_for_tiktok",
                        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no encoder")))

    outcome = studio.run()

    assert outcome["status"] == "failed"
    assert studio.video.read_bytes() == b"second render, different length"
    assert not auto_sharpen.is_sharpened(studio.record(), studio.video)


@pytest.mark.parametrize("value", ["0", "false", "OFF", "no"])
def test_switch_off_skips_the_step(studio, monkeypatch, value):
    monkeypatch.setenv(auto_sharpen.ENV_SWITCH, value)

    assert studio.run() == {"status": "skipped", "reason": "disabled"}
    assert studio.calls == [] and studio.video.read_bytes() == RENDERED


def test_nothing_to_sharpen_is_skipped(studio):
    assert auto_sharpen.ensure_tiktok_sharp(None)["reason"] == "no_export_id"
    assert auto_sharpen.ensure_tiktok_sharp("missing", channel_id=CHANNEL)["reason"] == "export_not_found"
    # another channel's export looks absent from this channel
    assert auto_sharpen.ensure_tiktok_sharp("export_other", channel_id=CHANNEL)["reason"] == "export_not_found"
    studio.video.unlink()
    assert studio.run() == {"status": "skipped", "reason": "video_missing"}
    assert studio.calls == []


def test_copy_written_by_the_manual_button_is_left_alone(studio):
    copy = studio.video.with_name("20261112_clip_hook_v1_tiktok_sharp.mp4")
    copy.write_bytes(b"already sharp copy")
    export_id = ExportRegistry.ensure(str(copy), status="rendered", channel_id=CHANNEL)["id"]

    outcome = auto_sharpen.ensure_tiktok_sharp(export_id, channel_id=CHANNEL)

    assert outcome == {"status": "kept", "reason": "manual_sharp_copy"}
    assert studio.calls == [] and copy.read_bytes() == b"already sharp copy"


# --- the marker in the registry ---------------------------------------------

def test_marker_survives_identity_hydration_and_can_be_cleared(studio):
    studio.run()
    marker = studio.record()[TIKTOK_SHARP_FIELD]

    # what every gallery listing does for the files it finds
    again = ExportRegistry.ensure(str(studio.video), status="rendered", channel_id=CHANNEL)
    assert again["id"] == EXPORT_ID and again[TIKTOK_SHARP_FIELD] == marker

    cleared = ExportRegistry.set_tiktok_sharp(EXPORT_ID, None, channel_id=CHANNEL)
    assert TIKTOK_SHARP_FIELD not in cleared and TIKTOK_SHARP_FIELD not in studio.record()
    assert ExportRegistry.set_tiktok_sharp("missing", {"size": 1, "mtime_ns": 1}, channel_id=CHANNEL) is None
    assert ExportRegistry.set_tiktok_sharp("export_other", {"size": 1, "mtime_ns": 1}, channel_id=CHANNEL) is None


@pytest.mark.parametrize("marker", [None, "yes", {}, {"size": "x", "mtime_ns": 1}, {"size": 13}])
def test_malformed_marker_never_counts_as_sharpened(studio, marker):
    assert not auto_sharpen.is_sharpened({TIKTOK_SHARP_FIELD: marker}, studio.video)
    assert not auto_sharpen.is_sharpened(None, studio.video)


# --- the three places a render completes -----------------------------------

@pytest.fixture
def completion_steps(monkeypatch):
    """Record, in order, what each render completion site runs for the finished clip."""
    steps = []
    for module in (api_render, api_phase1, batch_render):
        monkeypatch.setattr(module, "ensure_tiktok_sharp",
                            lambda export_id, **kwargs: steps.append(("sharp", export_id, kwargs)))
        monkeypatch.setattr(module, "ensure_default_cover",
                            lambda export_id, **kwargs: steps.append(("cover", export_id, kwargs)))
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    return steps


def _order(steps):
    return [(name, export_id) for name, export_id, _ in steps]


SHARP_THEN_COVER = [("sharp", EXPORT_ID), ("cover", EXPORT_ID)]


def test_first_render_sharpens_before_the_default_cover(studio, completion_steps, monkeypatch):
    job = _first_render(monkeypatch, studio.product_id, result={
        "mp4": studio.video.relative_to(studio.root).as_posix(),
        "project_name": "clip_project", "export_id": EXPORT_ID})

    assert job["status"] == "completed"
    assert _order(completion_steps) == SHARP_THEN_COVER


def test_draft_only_first_render_sharpens_nothing(studio, completion_steps, monkeypatch):
    _first_render(monkeypatch, studio.product_id, export_mp4=False,
                  result={"mp4": "", "project_name": "clip_project", "export_id": ""})

    assert completion_steps == []


def test_editor_render_sharpens_before_the_default_cover(studio, completion_steps, monkeypatch):
    job = _editor_render(monkeypatch, studio, mp4=studio.video.relative_to(studio.root).as_posix())

    assert job["status"] == "completed"
    assert _order(completion_steps) == SHARP_THEN_COVER
    assert completion_steps[0][2] == {"channel_id": CHANNEL}


def test_editor_render_without_output_sharpens_nothing(studio, completion_steps, monkeypatch):
    _editor_render(monkeypatch, studio, mp4="")

    assert completion_steps == []


@pytest.mark.parametrize("export_mp4, expected", [(True, SHARP_THEN_COVER), (False, [])])
def test_batch_render_sharpens_before_the_default_cover_only_for_rendered_clips(
        studio, completion_steps, monkeypatch, tmp_path, export_mp4, expected):
    _batch_render(monkeypatch, studio, tmp_path, export_mp4=export_mp4)

    assert _order(completion_steps) == expected


def test_render_still_completes_when_sharpening_fails(studio, monkeypatch):
    """The real step with a broken encoder: the job finishes and the clip is untouched."""
    monkeypatch.setattr(tiktok_enhancer, "enhance_video_for_tiktok",
                        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no encoder")))
    covers = []
    monkeypatch.setattr(api_render, "ensure_default_cover",
                        lambda export_id, **kwargs: covers.append(export_id))
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})

    job = _first_render(monkeypatch, studio.product_id, result={
        "mp4": studio.video.relative_to(studio.root).as_posix(),
        "project_name": "clip_project", "export_id": EXPORT_ID})

    assert job["status"] == "completed"
    assert covers == [EXPORT_ID]
    assert studio.video.read_bytes() == RENDERED


# --- the real encoder, the listing and the manual button ---------------------

def _real_clip(path, seconds=1.0):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=30:duration={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(path),
    ], check=True, capture_output=True, timeout=120)
    return path


def _listed(name):
    return next(item for item in api_exports.list_exports()["exports"] if item["name"] == name)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg/ffprobe required")
def test_real_clip_is_sharpened_in_place_listed_as_done_and_refused_by_the_manual_button(
        isolated_storage, monkeypatch):
    """No mocks: the real enhancer, the real gallery listing and the real endpoint."""
    monkeypatch.delenv(auto_sharpen.ENV_SWITCH, raising=False)
    exports_dir = api_exports.EXPORTS_DIR
    assert isolated_storage in exports_dir.parents  # never the real exports folder
    exports_dir.mkdir(parents=True, exist_ok=True)
    name = "20261112_sharp_hook_v1.mp4"
    clip = _real_clip(exports_dir / name)
    rendered = clip.read_bytes()
    before = media_validation.validate_mp4(clip, use_cache=False)
    assert before.ok, before.reason
    export_id = ExportRegistry.ensure(str(clip), status="rendered", channel_id=CHANNEL)["id"]
    assert _listed(name)["tiktok_enhanced"] is False

    outcome = auto_sharpen.ensure_tiktok_sharp(export_id, channel_id=CHANNEL)

    assert outcome["status"] == "sharpened", outcome
    assert sorted(p.name for p in exports_dir.iterdir() if p.suffix == ".mp4") == [name]  # no copy, no partial
    assert clip.read_bytes() != rendered
    after = media_validation.validate_mp4(clip, use_cache=False)
    assert after.ok, after.reason
    assert abs(after.details["duration"] - before.details["duration"]) <= 0.1
    item = _listed(name)
    assert item["export_id"] == export_id and item["tiktok_enhanced"] is True

    # the manual button's endpoint refuses a second pass and writes nothing
    app = FastAPI()
    app.include_router(api_exports.router)
    response = TestClient(app).post("/api/exports/enhance-tiktok", json={"export_id": export_id})
    assert response.status_code == 409, response.text
    by_path = TestClient(app).post(
        "/api/exports/enhance-tiktok", json={"path": str(clip.relative_to(api_exports.BASE_DIR)).replace("\\", "/")})
    assert by_path.status_code == 409, by_path.text
    assert sorted(p.name for p in exports_dir.iterdir() if p.suffix == ".mp4") == [name]

    # a second run leaves the sharpened file alone
    sharpened = clip.read_bytes()
    assert auto_sharpen.ensure_tiktok_sharp(export_id, channel_id=CHANNEL)["reason"] == "already_sharp"
    assert clip.read_bytes() == sharpened

    # a re-render to the same path is no longer shown as done
    _real_clip(clip, seconds=1.5)
    assert _listed(name)["tiktok_enhanced"] is False


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg/ffprobe required")
def test_real_clip_sharpened_then_covered_keeps_one_file_a_current_cover_and_the_flag(
        isolated_storage, monkeypatch):
    """No mocks: the two steps a finished render runs, in their real order."""
    from PIL import Image
    from scripts import api_covers, auto_cover

    monkeypatch.delenv(auto_sharpen.ENV_SWITCH, raising=False)
    exports_dir = api_exports.EXPORTS_DIR
    assert isolated_storage in exports_dir.parents  # never the real exports folder
    exports_dir.mkdir(parents=True, exist_ok=True)
    name = "20261112_chain_hook_v1.mp4"
    clip = _real_clip(exports_dir / name, seconds=2.0)
    rendered = clip.read_bytes()
    product = ps.ProductStore.add(
        name="Sharp Cover Product",
        angles=[{"angle_id": "a1", "project_name": "chain_project", "status": "rendered"}])
    export_id = ExportRegistry.ensure(
        str(clip), product_id=product["id"], angle_id="a1", project_name="chain_project",
        status="rendered", channel_id=CHANNEL)["id"]

    sharp = auto_sharpen.ensure_tiktok_sharp(export_id, channel_id=CHANNEL)
    cover = auto_cover.ensure_default_cover(export_id, channel_id=CHANNEL, product_id=product["id"], angle_id="a1")

    assert sharp["status"] == "sharpened", sharp
    assert cover["status"] == "created" and cover["bound"] and cover["angle_updated"], cover
    assert clip.read_bytes() != rendered
    assert sorted(p.name for p in exports_dir.iterdir()) == [name]  # one clip, nothing beside it
    with Image.open(isolated_storage / cover["cover_path"]) as image:
        assert image.size == (api_covers.COVER_W, api_covers.COVER_H)
    # the cover was cut from the final file, so it is not stale: a second cover call makes nothing new
    again = auto_cover.ensure_default_cover(export_id, channel_id=CHANNEL, product_id=product["id"], angle_id="a1")
    assert again["status"] != "created", again
    # the cover step's own registry writes keep the sharpness marker
    item = _listed(name)
    assert item["export_id"] == export_id and item["tiktok_enhanced"] is True
    assert auto_sharpen.ensure_tiktok_sharp(export_id, channel_id=CHANNEL)["reason"] == "already_sharp"
