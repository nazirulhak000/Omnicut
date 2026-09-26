"""Project migration must be atomic and preserve an external edit."""

import json
from pathlib import Path

import pytest

from tools import reprepare_cutout_video as migration


def _fixture(tmp_path, monkeypatch):
    projects = tmp_path / "03_Projects"
    project_dir = projects / "example"
    project_dir.mkdir(parents=True)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source-must-remain-unchanged")
    clips = [
        {"source_path": str(source), "trim_start": start, "trim_end": end,
         "background_isolation": {"enabled": True, "model": "u2net", "quality": "balanced"}}
        for start, end in [(0.0, 1.0), (0.8, 1.5), (3.0, 4.0)]
    ]
    project = project_dir / "project.json"
    project.write_text(json.dumps({"clip_list": clips}), encoding="utf-8")
    monkeypatch.setattr(migration, "PROJECTS_DIR", projects)
    monkeypatch.setattr(migration, "ROOT", tmp_path)
    return project, source


def _fake_video(source, cache_root, config, **kwargs):
    artifact_id = f"bgseq1-{int(kwargs['start']):016x}"
    directory = cache_root / "background-isolation-videos" / artifact_id
    directory.mkdir(parents=True)
    manifest = {"source_fingerprint": kwargs["source_fingerprint"],
                "source_start": kwargs["start"], "source_duration": kwargs["duration"]}
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "cutout.webm").write_bytes(b"fixture")
    return {"status": "ready", "artifact_id": artifact_id, "output_directory": str(directory)}


def test_migration_reuses_overlapping_window_and_backs_up_project(tmp_path, monkeypatch):
    project, source = _fixture(tmp_path, monkeypatch)
    before = project.read_bytes()
    groups = migration.reprepare_project(project, process_video=_fake_video)
    assert len(groups) == 2
    saved = json.loads(project.read_text(encoding="utf-8"))
    ids = [clip["background_isolation"]["artifact"]["id"] for clip in saved["clip_list"]]
    assert ids[0] == ids[1] != ids[2]
    assert source.read_bytes() == b"source-must-remain-unchanged"
    backups = list((tmp_path / "06_Archive" / "cutout_project_backups").glob("*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == before


def test_migration_refuses_to_overwrite_project_changed_during_processing(tmp_path, monkeypatch):
    project, _ = _fixture(tmp_path, monkeypatch)

    def concurrent_change(*args, **kwargs):
        if project.read_text(encoding="utf-8").find('external_edit') < 0:
            data = json.loads(project.read_text(encoding="utf-8"))
            data["external_edit"] = True
            project.write_text(json.dumps(data), encoding="utf-8")
        return _fake_video(*args, **kwargs)

    with pytest.raises(RuntimeError, match="changed during"):
        migration.reprepare_project(project, process_video=concurrent_change)
    assert json.loads(project.read_text(encoding="utf-8"))["external_edit"] is True
