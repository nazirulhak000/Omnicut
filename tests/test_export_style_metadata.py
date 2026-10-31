"""Q6 feedback-loop metadata: style fields on exports/posts, retention
columns on stats import, and the read-only style aggregation.

Offline, tmp storage only (never the real _Docs/ stores, no renders).
"""
import datetime
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api_exports
from scripts import export_registry
from scripts import post_log as post_log_module
from scripts import tiktok_pending as pending_module
from scripts.api_server import app
from scripts.export_registry import ExportRegistry, style_metadata_from_manifest
from scripts.post_log import PostLog, parse_completion_rate, parse_watch_time_sec


STYLE_KEYS = ("style_preset", "hook_style", "story_format", "duration_sec", "hook_text")


@pytest.fixture
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(export_registry, "BASE_DIR", tmp_path)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json")
    ExportRegistry._invalidate_index()
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    exports.mkdir(parents=True)
    return exports


@pytest.fixture
def isolated_log(tmp_path, monkeypatch):
    target = tmp_path / "_Docs" / "post_log.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(post_log_module, "LOG_PATH", target)
    monkeypatch.setattr(post_log_module._TABLE, "_json_path_fn", lambda: target)
    monkeypatch.setattr(post_log_module._TABLE, "_db_path_fn", lambda: tmp_path / "store.db")
    for attr, table in (("PENDING_PATH", pending_module._TABLE), ("IGNORED_PATH", pending_module._IGNORED_TABLE)):
        path = tmp_path / f"{attr.lower()}.json"
        monkeypatch.setattr(pending_module, attr, path)
        monkeypatch.setattr(table, "_json_path_fn", lambda path=path: path)
        monkeypatch.setattr(table, "_db_path_fn", lambda: tmp_path / "store.db")
    return target


@pytest.fixture
def client():
    from scripts.channel_store import MAIN_SEED

    class AccountClient(TestClient):
        def post(self, url, **kwargs):
            if url == "/api/tiktok-stats/import" and "json" in kwargs:
                kwargs["json"] = {"source_account": MAIN_SEED["handle"], **kwargs["json"]}
            return super().post(url, **kwargs)

    return AccountClient(app)


def _manifest(export_id="exp_1"):
    return {
        "export_id": export_id,
        "style_preset": "tech_neon",
        "hook_style_id": "warning",
        # The banner template dict must never be mistaken for the hook style id.
        "hook_style": {"template": "bold_banner"},
        "total_duration": 27.456,
        "script_data": {"hook": "  หยุดก่อน ถ้าจะซื้อพัดลม  ", "lines": [{"text": "บรรทัดสอง"}]},
        "hook_title": "Banner title",
    }


# ----------------------------------------------------------------------
# export registry
# ----------------------------------------------------------------------
def test_manifest_extraction_reads_existing_fields_without_probe():
    meta = style_metadata_from_manifest(_manifest())
    assert meta == {
        "style_preset": "tech_neon",
        "hook_style": "warning",
        "story_format": "classic",
        "duration_sec": 27.46,
        "hook_text": "หยุดก่อน ถ้าจะซื้อพัดลม",
    }
    assert style_metadata_from_manifest({"hook_style": {"template": "x"}}) == {"story_format": "classic"}
    assert style_metadata_from_manifest(None) == {}


def test_finalize_stores_five_fields_and_never_blanks(isolated_registry):
    clip = isolated_registry / "clip.mp4"
    clip.write_bytes(b"x")
    meta = style_metadata_from_manifest(_manifest())
    record = ExportRegistry.ensure(clip, product_id="p1", angle_id="a1", style_metadata=meta)
    for key in STYLE_KEYS:
        assert record[key] == meta[key]

    # Later calls without metadata (or with blanks) keep the stored values.
    again = ExportRegistry.ensure(clip, style_metadata={"style_preset": "", "duration_sec": 0})
    assert again["id"] == record["id"]
    assert again["style_preset"] == "tech_neon" and again["duration_sec"] == 27.46

    # Fill-missing by default; overwrite only when asked.
    kept = ExportRegistry.set_style_metadata(record["id"], {"style_preset": "other"})
    assert kept["style_preset"] == "tech_neon"
    replaced = ExportRegistry.set_style_metadata(record["id"], {"style_preset": "other"}, overwrite=True)
    assert replaced["style_preset"] == "other"
    assert ExportRegistry.set_style_metadata("exp_missing", meta) is None


def test_old_record_without_fields_loads_unchanged(isolated_registry):
    clip = isolated_registry / "old.mp4"
    clip.write_bytes(b"x")
    record = ExportRegistry.ensure(clip, product_id="p1", angle_id="a1")
    assert not any(key in record for key in STYLE_KEYS)
    loaded = ExportRegistry.get(record["id"])
    assert loaded == record


def test_list_backfill_only_from_the_manifest_of_this_render():
    record = {"id": "exp_1", "style_preset": "kept"}
    missing = api_exports._manifest_style_for_record(_manifest("exp_1"), record)
    assert "style_preset" not in missing  # never overwrite a stored value
    assert missing["hook_style"] == "warning"
    # A newer re-render rewrote the manifest: the older export gets nothing.
    assert api_exports._manifest_style_for_record(_manifest("exp_2"), record) is None
    assert api_exports._manifest_style_for_record(None, record) is None


def test_concurrent_metadata_writes_do_not_corrupt_registry(isolated_registry):
    clips = []
    for i in range(8):
        clip = isolated_registry / f"c{i}.mp4"
        clip.write_bytes(b"x")
        clips.append(clip)
    records = ExportRegistry.ensure_many([{"path": clip} for clip in clips])
    errors = []

    def stamp(index, record):
        try:
            ExportRegistry.set_style_metadata(record["id"], {
                "style_preset": f"preset_{index}", "hook_style": "curiosity",
                "duration_sec": 10 + index, "hook_text": f"hook {index}",
            })
            ExportRegistry.ensure_many([{"path": clips[index], "style_metadata": {"story_format": "classic"}}])
        except Exception as exc:  # pragma: no cover - surfaced by the assert
            errors.append(exc)

    threads = [threading.Thread(target=stamp, args=(i, r)) for i, r in enumerate(records)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    rows = ExportRegistry.all()
    assert len(rows) == 8
    by_id = {row["id"]: row for row in rows}
    for index, record in enumerate(records):
        row = by_id[record["id"]]
        assert row["style_preset"] == f"preset_{index}"
        assert row["duration_sec"] == 10 + index
        assert row["story_format"] == "classic"


# ----------------------------------------------------------------------
# post log
# ----------------------------------------------------------------------
def test_mark_posted_copies_style_fields_to_post_log(isolated_log, tmp_path, monkeypatch):
    monkeypatch.setattr(api_exports, "BASE_DIR", tmp_path)
    export_record = {"id": "exp_9", "duration_sec": 21.5, "style_preset": "punch",
                     "hook_style": "pain_point", "hook_text": "ปวดหลังไหม"}
    result = api_exports._record_posted_in_post_log(export_record, Path("clip_v1.mp4"), None, None, None)
    post = result["post"]
    assert post["style_preset"] == "punch"
    assert post["hook_style"] == "pain_point"
    assert post["story_format"] == "classic"
    assert post["duration_sec"] == 21.5
    assert post["hook_text"] == "ปวดหลังไหม"

    # Idempotent re-mark enriches only empty fields of the same row.
    again = api_exports._record_posted_in_post_log({**export_record, "style_preset": "other"},
                                                  Path("clip_v1.mp4"), None, None, None)
    assert again["status"] == "matched_export"
    assert again["post"]["style_preset"] == "punch"


def test_old_post_rows_keep_shape(isolated_log):
    post = PostLog.add_post(product_name="Old", clip_file="old.mp4")
    assert not any(key in post for key in STYLE_KEYS)


def test_update_metrics_accepts_retention_fields(isolated_log):
    post = PostLog.add_post(product_name="P", clip_file="p.mp4")
    stored = PostLog.update_metrics(post["id"], {"views": "100", "avg_watch_time_sec": "8.5s", "completion_rate": "40%"})
    assert stored["metrics"] == {"views": 100, "avg_watch_time_sec": 8.5, "completion_rate": 0.4}
    with pytest.raises(ValueError):
        PostLog.update_metrics(post["id"], {"completion_rate": "lots"})


@pytest.mark.parametrize("raw, expected", [
    ("45.3%", 0.453), ("45,5 %", 0.455), (0.62, 0.62), (62, 0.62), ("0.5", 0.5), ("100%", 1.0),
    ("", None), ("abc", None), (150, None), ("-3%", None), (None, None), (True, None),
])
def test_completion_rate_normalization(raw, expected):
    assert parse_completion_rate(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("8.5s", 8.5), ("8.5", 8.5), (12, 12.0), ("0:12", 12.0), ("1:02:03", 3723.0),
    ("1m 5s", 65.0), ("9 วินาที", 9.0), ("", None), ("fast", None), (-1, None),
])
def test_watch_time_normalization(raw, expected):
    assert parse_watch_time_sec(raw) == expected


# ----------------------------------------------------------------------
# stats import
# ----------------------------------------------------------------------
def _seed_post(video_id, **fields):
    PostLog.add_post(product_name="Logitech Lift", clip_file=f"{video_id}.mp4", angle_title="Logitech Lift", **fields)
    posts = PostLog.list_posts()
    for post in posts:
        if post["clip_file"] == f"{video_id}.mp4":
            post["tiktok_video_id"] = video_id
    PostLog._save(posts)


def test_import_without_watch_columns_still_passes(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
    _seed_post("111")
    resp = client.post("/api/tiktok-stats/import", json={"rows": [{"video_id": "111", "title": "Logitech Lift", "views": 50}]})
    assert resp.status_code == 200 and resp.json()["updated"] == 1
    assert PostLog.list_posts()[0]["metrics"] == {"views": 50}


def test_import_with_watch_columns_and_header_variants(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
    _seed_post("222")
    _seed_post("333")
    resp = client.post("/api/tiktok-stats/import", json={"rows": [
        {"video_id": "222", "title": "Logitech Lift", "views": 80, "avg_watch_time_sec": 7.25, "completion_rate": 0.31},
        {"video_id": "333", "title": "Logitech Lift", "views": 90, "Average watch time": "9.5s", "Watched full video": "42.5%"},
    ]})
    assert resp.status_code == 200 and resp.json()["updated"] == 2
    by_vid = {p["tiktok_video_id"]: p["metrics"] for p in PostLog.list_posts()}
    assert by_vid["222"] == {"views": 80, "avg_watch_time_sec": 7.25, "completion_rate": 0.31}
    assert by_vid["333"] == {"views": 90, "avg_watch_time_sec": 9.5, "completion_rate": 0.425}


# ----------------------------------------------------------------------
# aggregation
# ----------------------------------------------------------------------
def _measured(post_id, style_preset, hook_style, views, watch=None, rate=None, age_hours=72, **extra):
    posted = datetime.datetime(2026, 10, 1, 12, 0, 0)
    metrics = {"views": views}
    if watch is not None:
        metrics["avg_watch_time_sec"] = watch
    if rate is not None:
        metrics["completion_rate"] = rate
    row = {"id": post_id, "channel_id": "main", "posted_at": posted.isoformat(), "metrics": metrics,
           "metrics_history": [{"metrics": metrics, "captured_at": "x", "age_hours": age_hours}], **extra}
    if style_preset:
        row["style_preset"] = style_preset
    if hook_style:
        row["hook_style"] = hook_style
    return row


def test_style_performance_groups_and_none_handling():
    posts = [
        _measured("a", "punch", "warning", 100, watch=8.0, rate=0.4),
        _measured("b", "punch", "curiosity", 300, watch=10.0),
        _measured("c", "punch", "warning", 200),
        _measured("d", "smooth", "warning", 50, story_format="listicle"),
        _measured("e", None, None, 10),
        _measured("young", "punch", "warning", 99999, age_hours=2),  # not mature -> ignored
        {"id": "unmeasured", "style_preset": "punch", "metrics": None},
    ]
    by_preset = {g["style_preset"]: g for g in PostLog.style_performance("style_preset", posts=posts)}
    assert by_preset["punch"] == {"style_preset": "punch", "count": 3, "median_views": 200.0,
                                  "avg_watch_time_sec": 9.0, "completion_rate": 0.4}
    assert by_preset["smooth"]["avg_watch_time_sec"] is None
    assert by_preset["smooth"]["completion_rate"] is None
    assert by_preset["unspecified"]["count"] == 1

    by_format = {g["story_format"]: g["count"] for g in PostLog.style_performance("story_format", posts=posts)}
    assert by_format == {"classic": 4, "listicle": 1}
    with pytest.raises(ValueError):
        PostLog.style_performance("caption", posts=posts)


def test_style_performance_endpoint_is_channel_scoped(isolated_log, client):
    rows = [_measured("m1", "punch", "warning", 120, watch=6.0, rate=0.5),
            _measured("o1", "other", "warning", 999, channel_id="second")]
    PostLog._save(rows)
    resp = client.get("/api/tiktok-stats/style-performance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["measured"] == 1
    assert [g["style_preset"] for g in data["by_style_preset"]] == ["punch"]
    assert data["by_hook_style"][0]["completion_rate"] == 0.5

    one = client.get("/api/tiktok-stats/style-performance", params={"group_by": "hook_style"})
    assert one.status_code == 200 and one.json()["groups"][0]["hook_style"] == "warning"
    assert client.get("/api/tiktok-stats/style-performance", params={"group_by": "nope"}).status_code == 400


# ----------------------------------------------------------------------
# hooks -> manifest
# ----------------------------------------------------------------------
def test_apply_project_persists_hook_style_id_without_touching_template():
    from scripts.project_manifest import ProjectManifest
    name = "q6_hook_style_probe"
    try:
        ProjectManifest.save(name, channel_id="main", hook_brand="B", hook_style={"template": "bold"})
        resp = TestClient(app).post("/api/hooks/apply-project", json={
            "project_name": name,
            "hook_variant": {"style_id": "warning", "hook_title": "หยุดก่อน", "hook_brand": "Logi"},
        })
        assert resp.status_code == 200
        assert resp.json()["hook_style_id"] == "warning"
        stored = ProjectManifest.load(name)
        assert stored["hook_style_id"] == "warning"
        assert stored["hook_style"] == {"template": "bold"}

        # Unknown style ids are ignored.
        TestClient(app).post("/api/hooks/apply-project", json={
            "project_name": name, "hook_variant": {"style_id": "made_up"}})
        assert ProjectManifest.load(name)["hook_style_id"] == "warning"
    finally:
        ProjectManifest.delete(name)
