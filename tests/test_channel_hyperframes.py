"""Frozen HyperFrames provenance; optional real-browser gate uses temporary HTML."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

from scripts import api_hyperframes as api, config
from scripts.channel_store import ChannelError
from scripts.channel_scope import ChannelScope
from scripts.channel_identity import project_channel_identity
from tests.test_channel_identity import profile


def setup(root, monkeypatch, channel_id="second"):
    row = profile(root, channel_id)
    row["status"] = "active"
    snapshot = project_channel_identity(row)
    scope = ChannelScope(channel_id, "header", False, channel=row)
    api.COMPOSITIONS_DIR.mkdir(parents=True, exist_ok=True)
    api.TMP_DIR.mkdir(parents=True, exist_ok=True)
    (api.ASSETS_DIR / "fixture").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api, "require_final_ready", lambda current: current)
    return scope, snapshot


def composition(snapshot, **metadata):
    owner = snapshot["channel_id"]
    return api._freeze_composition(
        f'<html><head></head><body><div id="root" data-channel="{owner}" data-duration="1"></div></body></html>',
        snapshot, {"channel_id": owner, "channel_identity_snapshot": snapshot, **metadata})


def test_kit_frozen_snapshot_wins_over_live_profile_and_missing_secondary_rejects(isolated_storage):
    import subprocess
    snapshot = project_channel_identity(profile(isolated_storage))
    snapshot["hyperframes_avatar_path"] = "assets/shared/img/avatar.png"
    kit = config.SOURCE_ROOT / "03_Projects/_HyperFrames_Studio/kit/kit.js"
    script = """
const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert/strict');
const snapshot=JSON.parse(process.argv[2]); const elements={};
let frozen={textContent:JSON.stringify(snapshot)};
const document={readyState:'loading', addEventListener(){}, getElementById(id){
 return id==='root'?{dataset:{channel:'second'}}:id==='omnicut-channel-identity'?frozen:null;
}, querySelectorAll(selector){return [elements[selector]??=( {setAttribute(k,v){this[k]=v}} )]}};
const context={window:{HF_CHANNELS:{second:{name:'WRONG',watermark:'WRONG'}}},document,console};
vm.createContext(context); vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
context.HF=context.window.HF;
vm.runInContext('HF.applyChannel()',context);
assert.equal(elements['#wm span'].textContent,snapshot.watermark_text);
assert.equal(elements['#fl-card .fl-who b'].textContent,snapshot.display_name);
assert.equal(elements['#fl-title'].textContent,snapshot.follow_title);
assert.equal(elements['#fl-card .fl-ava img'].src,snapshot.hyperframes_avatar_path);
frozen=null; assert.throws(()=>vm.runInContext('HF.applyChannel()',context), /missing frozen/);
frozen={textContent:JSON.stringify({...snapshot,channel_id:'main'})};
assert.throws(()=>vm.runInContext('HF.applyChannel()',context), /identity conflict/);
"""
    result = subprocess.run(["node", "-e", script, str(kit), json.dumps(snapshot, ensure_ascii=False)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_composition_list_filters_foreign_and_snapshot_is_frozen(monkeypatch, isolated_storage):
    current, snapshot = setup(isolated_storage, monkeypatch)
    owned = api.COMPOSITIONS_DIR / "owned.html"
    owned.write_text(composition(snapshot), encoding="utf-8")
    foreign = {**snapshot, "id": "main", "channel_id": "main"}
    (api.COMPOSITIONS_DIR / "foreign.html").write_text(composition(foreign), encoding="utf-8")
    current.channel["watermark_text"] = "live changed"
    records = api.list_compositions(current)
    assert [row["id"] for row in records] == ["owned"]
    assert records[0]["channel_identity_snapshot"]["watermark_text"] == snapshot["watermark_text"]


def test_external_avatar_freezes_studio_local_bytes_without_overwriting_source(monkeypatch, isolated_storage):
    current, _ = setup(isolated_storage, monkeypatch)
    source = isolated_storage / "02_Assets" / "avatar.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.new("RGB", (8, 8), "green").save(source)
    before = source.read_bytes()
    current.channel["avatar_asset_path"] = source.relative_to(isolated_storage).as_posix()
    snapshot = project_channel_identity(current.channel)
    html = composition(snapshot)
    frozen = api._embedded_json(html, "omnicut-channel-identity")
    cached = api.STUDIO_DIR / frozen["hyperframes_avatar_path"]
    assert cached.is_relative_to(api.STUDIO_DIR)
    assert cached.read_bytes() == before == source.read_bytes()
    assert cached.stem == snapshot["avatar_sha256"]
    assert composition(snapshot) == html  # deduplicate the immutable asset
    cached.write_bytes(b"corrupted cache")
    with pytest.raises(ChannelError) as error:
        composition(snapshot)
    assert error.value.code == "channel_identity_asset_changed"
    assert source.read_bytes() == before


@pytest.mark.skipif(os.environ.get("OMNICUT_RUN_HF_BROWSER") != "1", reason="explicit local HyperFrames browser verification")
def test_external_avatar_actual_hyperframes_browser(monkeypatch, isolated_storage):
    current, _ = setup(isolated_storage, monkeypatch)
    from PIL import Image
    source = isolated_storage / "02_Assets" / "avatar.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), "green").save(source)
    current.channel["avatar_asset_path"] = source.relative_to(isolated_storage).as_posix()
    snapshot = project_channel_identity(current.channel)
    with tempfile.TemporaryDirectory(dir=isolated_storage) as directory:
        studio = Path(directory)
        monkeypatch.setattr(api, "STUDIO_DIR", studio)
        (studio / "kit").mkdir()
        shutil.copyfile(config.SOURCE_ROOT / "03_Projects/_HyperFrames_Studio/kit/kit.js", studio / "kit/kit.js")
        markup = '<html><head></head><body style="margin:0"><div id="root" data-composition-id="avatar-contract" data-channel="second" data-duration="1" data-width="1080" data-height="1920" data-no-timeline style="position:relative;width:1080px;height:1920px;background:black"><div id="fl-card" style="position:absolute;left:100px;top:100px"><div class="fl-ava"><img width="64" height="64" alt="Frozen avatar"></div></div></div><script src="kit/kit.js"></script></body></html>'
        (studio / "index.html").write_text(api._freeze_composition(markup, snapshot, {"channel_id": "second"}), encoding="utf-8")
        command = ["npx", "--yes", "hyperframes@0.8.143", "check", str(studio), "--json", "--snapshots"]
        if os.name == "nt":
            command = ["cmd.exe", "/c", *command]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout[result.stdout.index("{"):])
        assert report["ok"] and not report.get("browserSkipped"), report
        assert source.is_file()


def test_create_passes_validated_channel_and_embeds_safe_snapshot(monkeypatch, isolated_storage):
    current, snapshot = setup(isolated_storage, monkeypatch)
    raw = isolated_storage / "01_Raw" / "vo.wav"
    raw.write_bytes(b"fixture voice")
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        owner = command[command.index("--channel") + 1]
        (api.COMPOSITIONS_DIR / "new.html").write_text(
            f'<html><head><script src="kit/kit.js"></script></head><body><div id="root" data-channel="{owner}"></div></body></html>', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(api.subprocess, "run", run)
    result = api.create_clip(api.CreateClipRequest(clip_id="new", product="fixture", vo_path=str(raw)), current)
    assert calls[0][calls[0].index("--channel") + 1] == "second"
    document = (api.COMPOSITIONS_DIR / "new.html").read_text(encoding="utf-8")
    assert document.index('id="omnicut-channel-identity"') < document.index('src="kit/kit.js"')
    assert api._composition_scope(api.COMPOSITIONS_DIR / "new.html", current)["channel_identity_snapshot"] == snapshot
    assert result["channel_id"] == "second"


@pytest.mark.parametrize("bad", ["../escape", "film/escape", "film\\escape", "film\n"])
def test_render_path_escape_never_invokes_cli(monkeypatch, isolated_storage, bad):
    current, _ = setup(isolated_storage, monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail("CLI invoked before path validation")
    monkeypatch.setattr(api.subprocess, "run", forbidden)
    with pytest.raises(ChannelError):
        asyncio.run(api.render_composition(api.RenderCompositionRequest(composition_id=bad, is_test=True), current))


def test_render_registers_frozen_scope_and_never_doublejoins_or_overwrites(monkeypatch, isolated_storage):
    current, snapshot = setup(isolated_storage, monkeypatch)
    (api.COMPOSITIONS_DIR / "owned.html").write_text(composition(snapshot), encoding="utf-8")
    prior = api.EXPORTS_DIR / "second" / "film.mp4"
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior.write_bytes(b"old export")
    def run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_bytes(b"new fixture export")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(api.subprocess, "run", run)
    monkeypatch.setattr(api, "_extract_video_thumbnail", lambda *args, **kwargs: False)
    result = asyncio.run(api.render_composition(api.RenderCompositionRequest(composition_id="owned", output_filename="film.mp4"), current))
    output = Path(result["output_path"])
    assert output == prior.with_name("film_v2.mp4")
    assert prior.read_bytes() == b"old export"
    assert output.parts.count("Ready_to_post") == 1
    record = api.ExportRegistry.get(result["export_id"], channel_id="second")
    assert record["channel_identity_snapshot"] == snapshot
    assert record["product_id"] is None  # No product guessed from filename.


def test_is_test_output_is_temporary_and_not_registered(monkeypatch, isolated_storage):
    current, snapshot = setup(isolated_storage, monkeypatch)
    (api.COMPOSITIONS_DIR / "owned.html").write_text(composition(snapshot), encoding="utf-8")
    def run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_bytes(b"fixture")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(api.subprocess, "run", run)
    monkeypatch.setattr(api, "_extract_video_thumbnail", lambda *args, **kwargs: False)
    result = asyncio.run(api.render_composition(api.RenderCompositionRequest(composition_id="owned", is_test=True), current))
    assert Path(result["output_path"]).is_relative_to(api.TMP_DIR / "second")
    assert result["export_id"] is None
    from scripts import export_registry
    assert export_registry._TABLE.load() == []
