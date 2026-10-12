"""Frozen visual content and cache behavior; rendering fixtures stay temporary."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest
from PIL import Image, ImageChops

from scripts import config
from scripts.channel_store import ChannelError, MAIN_SEED
from scripts.channel_identity import project_channel_identity, resolve_channel_identity, identity_fingerprint, require_identity_avatar
from scripts.pipeline_context import build_incremental_render_metadata
from scripts.subtitle_engine import SubtitleEngine


def profile(root, channel_id="second"):
    avatar = root / "03_Projects/_HyperFrames_Studio/assets/shared/img/avatar.png"
    avatar.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), "blue").save(avatar)
    return {**MAIN_SEED, "id": channel_id, "revision": 3,
            "display_name": "Second", "handle": "@second",
            "watermark_text": "ช่อง second ห้ามคัดลอก", "follow_title": "กดติดตามด้วยนะ",
            "avatar_asset_path": avatar.relative_to(root).as_posix()}


def test_projection_is_frozen_visual_only_and_avatar_changes_fail(isolated_storage):
    record = profile(isolated_storage)
    snapshot = project_channel_identity(record)
    record["watermark_text"] = "changed"
    assert snapshot["watermark_text"] == "ช่อง second ห้ามคัดลอก"
    assert snapshot["id"] == snapshot["channel_id"] == "second"
    assert snapshot["revision"] == snapshot["channel_revision"] == 3
    assert "account_binding" not in snapshot and "status" not in snapshot
    path = require_identity_avatar(snapshot)
    Image.new("RGB", (8, 8), "red").save(path)
    with pytest.raises(ChannelError) as error:
        require_identity_avatar(snapshot)
    assert error.value.code == "channel_identity_asset_changed"


def test_legacy_main_default_and_missing_secondary_snapshot():
    assert resolve_channel_identity(None)["watermark_text"] == MAIN_SEED["watermark_text"]
    with pytest.raises(ChannelError):
        resolve_channel_identity(None, channel_id="second")


def test_identity_fingerprint_changes_visuals_but_not_lifecycle(isolated_storage):
    first = project_channel_identity(profile(isolated_storage))
    lifecycle = {**first, "revision": 99, "channel_revision": 99, "status": "archived", "account_binding": {"handle": "other"}}
    assert identity_fingerprint(lifecycle) == identity_fingerprint(first)
    assert identity_fingerprint({**first, "watermark_text": "different"}) != identity_fingerprint(first)
    manifest = {"channel_id": "second", "channel_identity_snapshot": first}
    before = build_incremental_render_metadata(manifest)["stage_fingerprints"]
    after = build_incremental_render_metadata({**manifest, "channel_identity_snapshot": {**first, "watermark_text": "different"}})["stage_fingerprints"]
    assert before["subtitles"] != after["subtitles"] and before["video"] != after["video"]
    assert before["voice"] == after["voice"] and before["mix"] == after["mix"]


def render_identity_frame(folder: Path, snapshot: dict, name="identity") -> Path:
    """Actual libass fixture, invoked only after the session's FFmpeg advisory."""
    folder.mkdir(parents=True, exist_ok=True)
    ass = folder / f"{name}.ass"
    frame = folder / f"{name}.png"
    SubtitleEngine.generate_ass(cues=[{"text": "ทดสอบ", "start": 0.0, "end": 1.0}],
                                output_ass_path=str(ass), bilingual=False,
                                channel_identity_snapshot=snapshot)
    font_directory = config.FONTS_DIR.as_posix().replace(":", "\\:")
    filters = f"subtitles={ass.name}:fontsdir='{font_directory}'"
    command = [shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=1",
               "-vf", filters, "-frames:v", "1", "-threads", "1", frame.name]
    result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"ตรวจเฟรม identity ไม่สำเร็จ: {result.stderr}"
    return frame


def test_ass_identity_escaping_keeps_typography_and_actual_frame(isolated_storage):
    first = resolve_channel_identity(None)
    second = project_channel_identity(profile(isolated_storage))
    with tempfile.TemporaryDirectory(dir=isolated_storage) as directory:
        root = Path(directory)
        primary = render_identity_frame(root, first, "main")
        secondary = render_identity_frame(root, second, "second")
        main_ass = (root / "main.ass").read_text(encoding="utf-8")
        second_ass = (root / "second.ass").read_text(encoding="utf-8")
        assert MAIN_SEED["watermark_text"] in main_ass
        assert second["watermark_text"] in second_ass
        styles = lambda text: [line for line in text.splitlines() if line.startswith("Style:")]
        assert styles(main_ass) == styles(second_ass)
        with Image.open(primary) as a, Image.open(secondary) as b:
            assert a.size == b.size == (1080, 1920)
            # Identity content changes only the fixed watermark column; the
            # caption region is pixel identical under the same libass fonts.
            assert ImageChops.difference(a.crop((0, 1400, 900, 1850)), b.crop((0, 1400, 900, 1850))).getbbox() is None
            assert ImageChops.difference(a, b).getbbox() is not None
