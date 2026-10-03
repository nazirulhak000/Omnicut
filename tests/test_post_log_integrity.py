"""Post-log data integrity: mark-posted registration, metrics history, evidence rules.

Everything runs against tmp_path stores (post log, queue, export registry);
nothing touches the real _Docs/*.json, 04_Exports or store.db.
"""
import datetime as dt
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.api_exports as exports_api
import scripts.api_schedule_queue as queue_api
import scripts.api_tiktok_autopost as autopost
import scripts.export_registry as registry
import scripts.post_log as post_log_module
import scripts.schedule_store as queue_store
from scripts.api_server import app
from scripts.post_log import PostLog

client = TestClient(app)


@pytest.fixture
def isolated_log(tmp_path, monkeypatch):
    """Post log in tmp_path/_Docs (parent.parent == tmp_path, as in production)."""
    log_path = tmp_path / "_Docs" / "post_log.json"
    monkeypatch.setattr(post_log_module, "LOG_PATH", log_path)
    monkeypatch.setattr(post_log_module._TABLE, "_json_path_fn", lambda: log_path)
    monkeypatch.setattr(post_log_module._TABLE, "_db_path_fn", lambda: tmp_path / "_Docs" / "store.db")
    return log_path


@pytest.fixture
def workspace(isolated_log, tmp_path, monkeypatch):
    ready = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    for folder in (ready, posted, covers):
        folder.mkdir(parents=True)
    video = ready / "a.mp4"
    video.write_bytes(b"a")
    for module in (queue_api, exports_api):
        monkeypatch.setattr(module, "BASE_DIR", tmp_path)
        monkeypatch.setattr(module, "EXPORTS_DIR", ready)
        monkeypatch.setattr(module, "POSTED_DIR", posted)
    monkeypatch.setattr(exports_api, "COVERS_DIR", covers)
    monkeypatch.setattr(registry, "BASE_DIR", tmp_path)
    monkeypatch.setattr(registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json")
    monkeypatch.setattr(queue_store, "SCHEDULE_QUEUE_PATH", tmp_path / "_Docs" / "schedule_queue.json")
    monkeypatch.setattr(queue_store, "SCHEDULE_TEMPLATE_PATH", tmp_path / "_Docs" / "schedule_templates.json")
    autopost._pending = None
    return video


def _queue(video: Path, when: str, **extra):
    body = {"video_path": str(video), "scheduled_at": when, "product_name": "Demo", "hook_title": video.stem}
    body.update(extra)
    resp = client.post("/api/schedule-queue", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()["items"][0]


# ---------------------------------------------------------------------------
# mark-posted -> exactly one PostLog row
# ---------------------------------------------------------------------------
def test_mark_posted_creates_exactly_one_row_with_queue_metadata(workspace):
    item = _queue(
        workspace, "2099-01-07T19:00:00+07:00",
        style_preset="viral_punch", hook_color="#FF3366",
        caption="Zorblax Quantum speaker", hashtags="#zorblax #gadget",
    )

    first = client.post("/api/exports/mark-posted", json={"file_path": str(workspace)})
    assert first.status_code == 200, first.text
    rows = PostLog.list_posts()
    assert len(rows) == 1
    row = rows[0]
    assert row["hook"] == "a"
    assert row["style_preset"] == "viral_punch"
    assert row["hook_color"] == item["hook_color"]
    assert row["scheduled_at"] == item["scheduled_at"]
    assert row["clip_file"] == "a.mp4"
    assert row["export_id"].startswith("exp_")
    assert row["hashtags"] == ["#zorblax", "#gadget"]
    assert row["caption"] == "Zorblax Quantum speaker"
    assert row["source"] == "mark_posted"
    # Scheduled in the future -> the metrics-age clock starts at the schedule time.
    assert row["posted_at"].startswith("2099-01-07")

    # Idempotent: marking the (now Posted/) file again adds no second row.
    moved = workspace.parent.parent / "Posted" / "a.mp4"
    again = client.post("/api/exports/mark-posted", json={"file_path": str(moved)})
    assert again.status_code == 200, again.text
    assert len(PostLog.list_posts()) == 1


def test_stats_sync_links_to_mark_posted_row_even_when_title_does_not_fuzzy_match(workspace):
    _queue(workspace, "2099-01-07T19:00:00+07:00", style_preset="viral_punch")
    assert client.post("/api/exports/mark-posted", json={"file_path": str(workspace)}).status_code == 200

    # The Studio title shares nothing with the stored caption/hook, so the
    # fuzzy post match fails; the candidate's clip file must still link to
    # the existing row instead of registering a duplicate.
    candidates = [{
        "clip_file": "a.mp4", "product_name": "Zorblax", "angle_title": "Quantum speaker",
        "hook_title": "Quantum speaker", "caption": "Quantum speaker review",
    }]
    result = PostLog.upsert_tiktok_stats(
        [{"title": "Quantum speaker review", "views": 120, "likes": 9, "video_id": "777"}],
        register_missing=True,
        clip_candidates=candidates,
    )
    assert result["registered"] == 0
    rows = PostLog.list_posts()
    assert len(rows) == 1
    assert rows[0]["tiktok_video_id"] == "777"
    assert rows[0]["metrics"]["views"] == 120
    assert rows[0]["style_preset"] == "viral_punch"
    assert len(rows[0]["metrics_history"]) == 1


def test_register_posted_export_enriches_existing_stats_row(isolated_log):
    PostLog.upsert_tiktok_stats(
        [{"title": "Orbit gadget quick review", "views": 5, "video_id": "42"}],
        register_missing=True,
        clip_candidates=[{"clip_file": "orbit.mp4", "product_name": "Orbit", "hook_title": "Orbit gadget quick review", "caption": "Orbit gadget quick review"}],
    )
    assert len(PostLog.list_posts()) == 1
    PostLog.register_posted_export(
        product_name="Orbit", clip_file="orbit.mp4", style_preset="clean_tech_review",
        hook_color="#00FFAA", scheduled_at="2099-01-01T09:00:00+07:00",
    )
    rows = PostLog.list_posts()
    assert len(rows) == 1
    assert rows[0]["style_preset"] == "clean_tech_review"
    assert rows[0]["tiktok_video_id"] == "42"  # existing data preserved


# ---------------------------------------------------------------------------
# metrics history / pending_metrics / legacy rows
# ---------------------------------------------------------------------------
def _rewind_posted_at(hours: float) -> None:
    posts = PostLog._load()
    posts[0]["posted_at"] = (dt.datetime.now() - dt.timedelta(hours=hours)).isoformat(timespec="seconds")
    PostLog._save(posts)


def _sync(views: int, video_id: str = "900"):
    return PostLog.upsert_tiktok_stats([{"title": "Orbit gadget quick review", "views": views, "likes": 1, "video_id": video_id}])


def test_two_syncs_append_two_snapshots_and_keep_latest_metrics(isolated_log):
    PostLog.add_post(product_name="Orbit", clip_file="orbit.mp4", angle_title="Orbit gadget quick review")
    _sync(10)
    _sync(25)
    post = PostLog.list_posts()[0]
    assert post["metrics"]["views"] == 25
    assert [snap["metrics"]["views"] for snap in post["metrics_history"]] == [10, 25]
    for snap in post["metrics_history"]:
        assert snap["captured_at"]
        assert snap["age_hours"] is not None and snap["age_hours"] < 1


def test_one_hour_snapshot_is_not_a_measured_result(isolated_log):
    PostLog.add_post(product_name="Orbit", clip_file="orbit.mp4", angle_title="Orbit gadget quick review")
    _sync(10)  # captured ~0h after posting
    _rewind_posted_at(60)  # the post is now 60h old but only has a ~0h number
    pending = PostLog.pending_metrics()
    assert [p["id"] for p in pending] == [PostLog.list_posts()[0]["id"]]
    assert post_log_module.mature_metrics(PostLog.list_posts()[0]) is None


def test_snapshot_aged_48h_counts_as_measured(isolated_log):
    PostLog.add_post(product_name="Orbit", clip_file="orbit.mp4", angle_title="Orbit gadget quick review")
    _rewind_posted_at(60)
    _sync(500)  # captured at ~60h
    assert PostLog.pending_metrics() == []
    assert post_log_module.mature_metrics(PostLog.list_posts()[0])["views"] == 500


def test_mature_metrics_uses_earliest_48h_snapshot(isolated_log):
    PostLog.add_post(product_name="Orbit", clip_file="orbit.mp4", angle_title="Orbit gadget quick review")
    _rewind_posted_at(60)
    _sync(500)
    _sync(900)
    assert post_log_module.mature_metrics(PostLog.list_posts()[0])["views"] == 500
    assert PostLog.list_posts()[0]["metrics"]["views"] == 900  # latest still current


def test_legacy_row_without_history_still_works(isolated_log):
    legacy_posted = (dt.datetime.now() - dt.timedelta(hours=100)).isoformat(timespec="seconds")
    PostLog._save([{
        "id": "legacy1", "product_name": "Old", "clip_file": "old.mp4", "angle_title": "Old gadget teardown",
        "posted_at": legacy_posted, "metrics": {"views": 1000, "likes": 50},
        "metrics_filled_at": (dt.datetime.now() - dt.timedelta(hours=1)).isoformat(timespec="seconds"),
    }, {
        "id": "legacy2", "product_name": "Old", "clip_file": "old2.mp4", "posted_at": legacy_posted, "metrics": None,
    }])
    assert [p["id"] for p in PostLog.pending_metrics()] == ["legacy2"]  # legacy1 keeps counting as measured
    assert post_log_module.mature_metrics(PostLog.list_posts()[0]) is not None
    assert PostLog.angle_performance()[0]["views"] == 1000
    assert PostLog.summary()["measured"] == 1

    # A new sync on the legacy row seeds its old numbers into the history.
    PostLog.upsert_tiktok_stats([{"title": "Old gadget teardown", "views": 1500, "video_id": "55"}])
    row = next(p for p in PostLog.list_posts() if p["id"] == "legacy1")
    assert row["metrics"]["views"] == 1500
    assert [snap["metrics"]["views"] for snap in row["metrics_history"]] == [1000, 1500]
    assert PostLog.pending_metrics()[0]["id"] == "legacy2"


def test_history_is_capped_and_keeps_earliest_mature_snapshot(isolated_log):
    PostLog.add_post(product_name="Orbit", clip_file="orbit.mp4", angle_title="Orbit gadget quick review")
    _rewind_posted_at(60)
    for views in range(1, post_log_module.METRICS_HISTORY_CAP + 6):
        _sync(views)
    post = PostLog.list_posts()[0]
    assert len(post["metrics_history"]) == post_log_module.METRICS_HISTORY_CAP
    assert post_log_module.mature_metrics(post)["views"] == 1


# ---------------------------------------------------------------------------
# analytics evidence rules (api_schedule_queue)
# ---------------------------------------------------------------------------
def _post(hour: int, day: int, views: int = 500, **extra):
    row = {"product_name": "A", "posted_at": f"2026-09-{day:02d}T{hour:02d}:00:00", "metrics": {"views": views, "likes": 50}}
    row.update(extra)
    return row


def _patch_posts(monkeypatch, posts):
    monkeypatch.setattr(queue_api.PostLog, "list_posts", classmethod(lambda cls, newest_first=True: posts))


def test_best_time_ignores_hour_buckets_under_min_sample(monkeypatch):
    posts = [_post(19, 1), _post(19, 2), _post(19, 3, views=600), _post(21, 1, views=900000)]
    _patch_posts(monkeypatch, posts)
    analytics, _, hour_scores = queue_api._build_performance_analytics([])
    assert set(hour_scores) == {19}
    assert [row["hour"] for row in analytics["top_hours"]] == [19]
    assert analytics["min_hour_samples"] == queue_api.MIN_HOUR_SAMPLES


def test_analytics_uses_48h_snapshots_and_falls_back_for_legacy_rows(monkeypatch):
    young = _post(19, 1, metrics_history=[{"metrics": {"views": 999999}, "captured_at": "2026-09-01T20:00:00", "age_hours": 1.0}])
    mature = _post(19, 2, metrics_history=[
        {"metrics": {"views": 10}, "captured_at": "2026-09-02T20:00:00", "age_hours": 1.0},
        {"metrics": {"views": 700, "likes": 70}, "captured_at": "2026-09-04T20:00:00", "age_hours": 49.0},
        {"metrics": {"views": 5000}, "captured_at": "2026-09-09T20:00:00", "age_hours": 170.0},
    ])
    legacy = _post(19, 3, views=400)  # no metrics_history at all
    _patch_posts(monkeypatch, [young, mature, legacy])
    analytics, _, hour_scores = queue_api._build_performance_analytics([])
    assert analytics["sample_size"] == 2  # the 1h-only row is excluded
    assert hour_scores == {}  # 2 samples < MIN_HOUR_SAMPLES

    _patch_posts(monkeypatch, [young, mature, legacy, _post(19, 4, views=300)])
    analytics, _, hour_scores = queue_api._build_performance_analytics([])
    assert analytics["sample_size"] == 3
    assert analytics["top_hours"][0]["hour"] == 19
    assert analytics["top_hours"][0]["avg_views"] == round((700 + 400 + 300) / 3)
    assert set(hour_scores) == {19}
