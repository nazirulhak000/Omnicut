"""tools/sync_channels.py: registry -> HyperFrames kit/channels.js (multi-channel P1).

Uses a tmp project root with a tmp kit dir; never touches the real studio.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import channel_store as cs
from tools import sync_channels

# Shape of the hand-written kit file before P1 (copied verbatim, not read from
# the gitignored studio folder).
LEGACY_CHANNELS_JS = """// One entry per TikTok channel. A clip picks its channel with data-channel="<id>" on #root (default "main").
// HF.applyChannel() (kit/kit.js) writes these into the watermark (#wm) and the follow outro (#fl-*).
// To add a channel: copy a block, give it a new id, drop its avatar in assets/shared/img/, then make clips with
//   python kit/new_clip.py <clip-id> --product <code> --vo <wav> --channel <id>
window.HF_CHANNELS = {
  main: {
    name: "rizannTry",
    handle: "@rizanntry",
    avatar: "assets/shared/img/channel_avatar.jpg",
    watermark: "สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง",
    followTitle: "กดติดตามด้วยนะ",
  },
};
"""

NODE = shutil.which("node")


class FakeMetrics:
    def width_px(self, text, font_file, size):
        return float(len(text) * 10)

    def unsupported_chars(self, text, font_file):
        return []


@pytest.fixture()
def project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    studio = root / "03_Projects" / "_HyperFrames_Studio"
    kit = studio / "kit"
    kit.mkdir(parents=True)
    (kit / "channels.js").write_text(LEGACY_CHANNELS_JS, encoding="utf-8", newline="\n")
    avatar = root / cs.MAIN_SEED["avatar_asset_path"]
    avatar.parent.mkdir(parents=True, exist_ok=True)
    avatar.write_bytes(b"main")
    (studio / "assets" / "shared" / "img" / "second.jpg").write_bytes(b"second")
    monkeypatch.setattr(cs, "_DEFAULT_METRICS", FakeMetrics())
    registry = root / "_Docs" / "channels.json"
    return {"root": root, "kit": kit, "registry": registry}


def _run(project, apply):
    out = io.StringIO()
    code = sync_channels.sync(
        registry_path=project["registry"],
        kit_dir=project["kit"],
        project_root=project["root"],
        apply=apply,
        out=out,
    )
    return code, out.getvalue()


def _eval_with_node(path: Path) -> dict:
    script = (
        "const vm=require('vm'),fs=require('fs');const ctx={window:{}};"
        "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),ctx);"
        "process.stdout.write(JSON.stringify(ctx.window.HF_CHANNELS));"
    )
    result = subprocess.run([NODE, "-e", script, str(path)], capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return json.loads(result.stdout.decode("utf-8"))


def test_implicit_main_matches_legacy_kit_values(project):
    code, output = _run(project, apply=False)
    assert code == 0
    # Only comment lines differ: every data line of the legacy file is reproduced.
    changed = [line for line in output.splitlines() if line[:1] in ("+", "-") and not line.startswith(("+++", "---"))]
    assert changed and all(line[1:].lstrip().startswith("//") for line in changed), changed
    assert not project["registry"].exists()  # sync never writes the registry


def test_dry_run_writes_nothing(project):
    before = (project["kit"] / "channels.js").read_bytes()
    code, output = _run(project, apply=False)
    assert code == 0 and "dry-run" in output
    assert (project["kit"] / "channels.js").read_bytes() == before
    assert not (project["kit"] / "channels.js.bak").exists()
    assert sorted(p.name for p in project["kit"].iterdir()) == ["channels.js"]


def test_apply_backs_up_writes_atomically_and_is_idempotent(project):
    store = cs.ChannelStore(project["registry"], project_root=project["root"])
    store.create(
        {
            "id": "gen-shop",
            "display_name": 'ช่อง "รอง" \\ ทดสอบ',
            "handle": "@gen_shop",
            "watermark_text": "สงวนลิขสิทธิ์ช่อง gen_shop",
            "follow_title": "กดติดตามเลย",
            "avatar_asset_path": "03_Projects/_HyperFrames_Studio/assets/shared/img/second.jpg",
        }
    )
    target = project["kit"] / "channels.js"
    code, output = _run(project, apply=True)
    assert code == 0, output
    assert (project["kit"] / "channels.js.bak").read_text(encoding="utf-8") == LEGACY_CHANNELS_JS
    text = target.read_text(encoding="utf-8")
    assert '"gen-shop": {' in text and "  main: {" in text and "// status: draft" in text
    assert not [p for p in project["kit"].iterdir() if p.name.endswith(".tmp")]

    first = target.read_bytes()
    bak_before = (project["kit"] / "channels.js.bak").read_bytes()
    code, output = _run(project, apply=True)
    assert code == 0 and "0 การเปลี่ยนแปลง" in output
    assert target.read_bytes() == first
    assert (project["kit"] / "channels.js.bak").read_bytes() == bak_before

    if NODE:
        channels = _eval_with_node(target)
        assert set(channels) == {"main", "gen-shop"}
        assert channels["main"] == {
            "name": "rizannTry",
            "handle": "@rizanntry",
            "avatar": "assets/shared/img/channel_avatar.jpg",
            "watermark": "สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง",
            "followTitle": "กดติดตามด้วยนะ",
        }
        assert channels["gen-shop"]["name"] == 'ช่อง "รอง" \\ ทดสอบ'
        assert channels["gen-shop"]["avatar"] == "assets/shared/img/second.jpg"
        for entry in channels.values():
            assert list(entry) == ["name", "handle", "avatar", "watermark", "followTitle"]


@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_legacy_and_generated_files_evaluate_to_same_main(project):
    legacy = _eval_with_node(project["kit"] / "channels.js")
    assert _run(project, apply=True)[0] == 0
    assert _eval_with_node(project["kit"] / "channels.js") == legacy


def test_crlf_files_keep_crlf(project):
    target = project["kit"] / "channels.js"
    target.write_bytes(LEGACY_CHANNELS_JS.replace("\n", "\r\n").encode("utf-8"))
    assert _run(project, apply=True)[0] == 0
    data = target.read_bytes()
    assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")
    assert "0 การเปลี่ยนแปลง" in _run(project, apply=True)[1]


def test_missing_kit_dir_exits_nonzero_without_writing(project, tmp_path):
    missing = tmp_path / "nowhere" / "kit"
    out = io.StringIO()
    code = sync_channels.sync(registry_path=project["registry"], kit_dir=missing, project_root=project["root"], apply=True, out=out)
    assert code == 2 and "ไม่พบโฟลเดอร์ kit" in out.getvalue()
    assert not missing.exists() and not missing.parent.exists()


def test_avatar_outside_studio_is_rejected(project):
    outside = project["root"] / "02_Assets" / "Branding" / "x.jpg"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"x")
    cs.ChannelStore(project["registry"], project_root=project["root"]).create(
        {"id": "second", "display_name": "x", "avatar_asset_path": "02_Assets/Branding/x.jpg"}
    )
    before = (project["kit"] / "channels.js").read_bytes()
    code, output = _run(project, apply=True)
    assert code == 2 and "นอกโฟลเดอร์ HyperFrames Studio" in output
    assert (project["kit"] / "channels.js").read_bytes() == before


def test_corrupt_registry_exits_nonzero(project):
    project["registry"].parent.mkdir(parents=True, exist_ok=True)
    project["registry"].write_text("{nope", encoding="utf-8")
    before = (project["kit"] / "channels.js").read_bytes()
    code, output = _run(project, apply=True)
    assert code == 2 and "เสียหาย" in output
    assert (project["kit"] / "channels.js").read_bytes() == before


def test_readiness_gaps_are_warnings(project):
    cs.ChannelStore(project["registry"], project_root=project["root"]).create({"id": "draft1", "display_name": "ร่าง"})
    code, output = _run(project, apply=False)
    assert code == 0 and "คำเตือน ช่อง draft1" in output


def test_cli_main_defaults_to_dry_run(project, capsys):
    before = (project["kit"] / "channels.js").read_bytes()
    code = sync_channels.main(
        ["--registry", str(project["registry"]), "--kit-dir", str(project["kit"]), "--project-root", str(project["root"])]
    )
    assert code == 0
    assert (project["kit"] / "channels.js").read_bytes() == before
    assert "dry-run" in capsys.readouterr().out


def test_non_string_fields_in_hand_edited_registry_are_rejected(project):
    project["registry"].parent.mkdir(parents=True, exist_ok=True)
    project["registry"].write_text(
        json.dumps({"schema_version": 1, "revision": 1, "channels": [{"id": "main", "status": "active", "display_name": 5}]}),
        encoding="utf-8",
    )
    before = (project["kit"] / "channels.js").read_bytes()
    code, output = _run(project, apply=True)
    assert code == 2 and "ต้องเป็นข้อความ" in output
    assert (project["kit"] / "channels.js").read_bytes() == before
