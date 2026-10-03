from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
import scripts.api_schedule_queue as queue_api
import scripts.api_tiktok_autopost as autopost
import scripts.schedule_store as queue_store


client = TestClient(app)


@pytest.fixture
def queue_workspace(tmp_path, monkeypatch):
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    exports.mkdir(parents=True)
    posted.mkdir(parents=True)
    covers.mkdir(parents=True)
    video_a = exports / "a.mp4"
    video_b = exports / "b.mp4"
    video_a.write_bytes(b"a")
    video_b.write_bytes(b"b")
    monkeypatch.setattr(queue_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(queue_api, "EXPORTS_DIR", exports)
    monkeypatch.setattr(queue_api, "POSTED_DIR", posted)
    monkeypatch.setattr(queue_store, "SCHEDULE_QUEUE_PATH", tmp_path / "_Docs" / "schedule_queue.json")
    monkeypatch.setattr(queue_store, "SCHEDULE_TEMPLATE_PATH", tmp_path / "_Docs" / "schedule_templates.json")
    autopost._pending = None
    return video_a, video_b


def payload(video: Path, when: str):
    return {"video_path": str(video), "scheduled_at": when, "product_name": "Demo", "hook_title": video.stem}


def test_queue_persists_sorted_records_and_blocks_duplicate_video(queue_workspace):
    video_a, video_b = queue_workspace
    first = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-11T12:30:00+07:00"))
    assert first.status_code == 200
    second = client.post("/api/schedule-queue", json=payload(video_b, "2026-09-10T08:30:00+07:00"))
    assert second.status_code == 200
    listed = client.get("/api/schedule-queue").json()["items"]
    assert [row["video_path"] for row in listed] == ["04_Exports/Ready_to_post/b.mp4", "04_Exports/Ready_to_post/a.mp4"]
    duplicate = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-12T08:30:00+07:00"))
    assert duplicate.status_code == 409


def test_bulk_create_is_atomic_on_collision_and_requires_five_minutes(queue_workspace):
    video_a, video_b = queue_workspace
    bad = client.post("/api/schedule-queue", json={"items": [payload(video_a, "2026-09-10T08:31:00+07:00"), payload(video_b, "2026-09-10T08:35:00+07:00")]})
    assert bad.status_code == 422
    assert client.get("/api/schedule-queue").json()["items"] == []
    good = client.post("/api/schedule-queue", json={"items": [payload(video_a, "2026-09-10T08:30:00+07:00"), payload(video_b, "2026-09-10T08:35:00+07:00")]})
    assert good.status_code == 200
    collision = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-10T09:00:00+07:00"))
    assert collision.status_code == 409


def test_reschedule_and_lifecycle_guards(queue_workspace):
    video_a, _ = queue_workspace
    item = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-10T08:30:00+07:00")).json()["items"][0]
    moved = client.patch(f"/api/schedule-queue/{item['id']}", json={"scheduled_at": "2026-09-12T10:00:00+07:00"})
    assert moved.status_code == 200
    ready = client.patch(f"/api/schedule-queue/{item['id']}", json={"status": "ready_for_extension"})
    assert ready.status_code == 200
    blocked = client.patch(f"/api/schedule-queue/{item['id']}", json={"scheduled_at": "2026-09-13T10:00:00+07:00"})
    assert blocked.status_code == 409
    reset = client.patch(f"/api/schedule-queue/{item['id']}", json={"status": "planned"})
    assert reset.status_code == 200
    assert client.patch(f"/api/schedule-queue/{item['id']}", json={"scheduled_at": "2026-09-13T10:00:00+07:00"}).status_code == 200


def test_prepare_marks_one_item_and_sends_date_time_to_extension(queue_workspace, monkeypatch):
    video_a, _ = queue_workspace
    item = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-14T15:25:00+07:00")).json()["items"][0]
    captured = {}

    def fake_prepare(req):
        captured.update(req.model_dump())
        return {"success": True}

    monkeypatch.setattr(queue_api, "prepare", fake_prepare)
    prepared = client.post(f"/api/schedule-queue/{item['id']}/prepare")
    assert prepared.status_code == 200
    assert prepared.json()["status"] == "ready_for_extension"
    assert captured["schedule_date"] == "2026-09-14"
    assert captured["schedule_time"] == "15:25"


def test_weekly_template_upsert_copy_and_reset(queue_workspace):
    custom = {"enabled": True, "times": ["06:00", "15:00", "21:00"]}
    saved = client.put(
        "/api/schedule-queue/template",
        json={"week_start": "2030-01-07", "days": {"0": custom}},
    )
    assert saved.status_code == 200
    assert saved.json()["id"] == "week:2030-01-07"
    assert saved.json()["days"]["0"]["times"] == custom["times"]
    copied = client.post(
        "/api/schedule-queue/template/copy",
        json={"source_week_start": "2030-01-07", "target_week_start": "2030-01-14"},
    )
    assert copied.status_code == 200
    assert copied.json()["days"]["0"]["times"] == custom["times"]
    reset = client.delete("/api/schedule-queue/template/2030-01-14")
    assert reset.status_code == 200
    assert reset.json()["id"] == "default"
    assert reset.json()["days"]["0"]["times"] == ["09:00", "12:30", "16:00", "19:00", "21:30"]


def test_legacy_slot_templates_migrate_to_five_defaults(queue_workspace):
    queue_store.ScheduleTemplateStore._save([{
        "id": "default",
        "week_start": None,
        "days": {str(index): {"enabled": True, "times": ["07:00", "10:00", "12:00", "16:00", "20:00"]} for index in range(7)},
    }])
    response = client.get("/api/schedule-queue/template")
    assert response.status_code == 200
    assert response.json()["days"]["0"]["times"] == ["09:00", "12:30", "16:00", "19:00", "21:30"]


def test_template_supports_variable_slot_counts_and_rejects_duplicates(queue_workspace):
    custom = {"enabled": True, "times": ["08:00", "13:00", "18:00", "22:00"]}
    saved = client.put(
        "/api/schedule-queue/template",
        json={"week_start": "2030-01-07", "days": {"0": custom}},
    )
    assert saved.status_code == 200
    assert saved.json()["days"]["0"]["times"] == custom["times"]

    duplicate = client.put(
        "/api/schedule-queue/template",
        json={"week_start": "2030-01-07", "days": {"0": {"enabled": True, "times": ["08:00", "08:00"]}}},
    )
    assert duplicate.status_code == 422


def test_autofill_preview_rotates_products_and_commit_is_atomic(queue_workspace):
    video_a, video_b = queue_workspace
    video_c = video_a.parent / "c.mp4"
    video_d = video_a.parent / "d.mp4"
    video_c.write_bytes(b"c")
    video_d.write_bytes(b"d")
    clips = [
        {"video_path": str(video_a), "product_id": "A", "product_name": "A"},
        {"video_path": str(video_b), "product_id": "B", "product_name": "B"},
        {"video_path": str(video_c), "product_id": "A", "product_name": "A"},
        {"video_path": str(video_d), "product_id": "B", "product_name": "B"},
    ]
    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": clips, "seed": 7},
    )
    assert preview.status_code == 200
    rows = preview.json()["items"]
    assert len(rows) == 2
    assert len({row["product_id"] for row in rows}) == 2
    committed = client.post("/api/schedule-queue/auto-fill", json={"items": rows})
    assert committed.status_code == 200
    collision = client.post("/api/schedule-queue/auto-fill", json={"items": rows[:1]})
    assert collision.status_code == 409
    assert len(client.get("/api/schedule-queue").json()["items"]) == 2


def test_overdue_planned_row_is_annotated_without_changing_status(queue_workspace):
    video_a, _ = queue_workspace
    item = client.post("/api/schedule-queue", json=payload(video_a, "2020-01-06T08:00:00+07:00")).json()["items"][0]
    listed = client.get("/api/schedule-queue").json()["items"][0]
    assert listed["id"] == item["id"]
    assert listed["status"] == "planned"
    assert listed["is_overdue"] is True


def test_autofill_starts_after_latest_queue_timestamp_and_skips_past_slots(queue_workspace):
    video_a, video_b = queue_workspace
    video_c = video_a.parent / "c.mp4"
    video_c.write_bytes(b"c")
    existing = client.post("/api/schedule-queue", json=payload(video_a, "2030-01-07T10:00:00+07:00"))
    assert existing.status_code == 200
    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "clips": [
                {"video_path": str(video_b), "product_id": "B", "product_name": "B"},
                {"video_path": str(video_c), "product_id": "C", "product_name": "C"},
            ],
            "seed": 11,
        },
    )
    assert preview.status_code == 200
    assert [row["scheduled_at"] for row in preview.json()["items"]] == [
        "2030-01-07T12:30+07:00",
        "2030-01-07T16:00+07:00",
    ]


def test_autofill_never_spills_outside_requested_date_range(queue_workspace):
    video_a, video_b = queue_workspace
    extra_videos = []
    for name in ("c", "d", "e", "f"):
        path = video_a.parent / f"{name}.mp4"
        path.write_bytes(name.encode())
        extra_videos.append(path)

    existing = client.post("/api/schedule-queue", json=payload(video_a, "2030-01-07T09:00:00+07:00"))
    assert existing.status_code == 200
    clips = [
        {"video_path": str(video_b), "product_id": "B", "product_name": "B"},
        *({"video_path": str(path), "product_id": name, "product_name": name} for path, name in zip(extra_videos, ("C", "D", "E", "F"))),
    ]

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": clips, "seed": 4},
    )

    assert preview.status_code == 200
    result = preview.json()
    assert len(result["items"]) == 4
    assert result["skipped_slots"] == 1
    assert {row["scheduled_at"][:10] for row in result["items"]} == {"2030-01-07"}


def test_autofill_ignores_queue_timestamps_outside_requested_range(queue_workspace):
    video_a, video_b = queue_workspace
    future = video_a.parent / "future.mp4"
    future.write_bytes(b"future")
    existing = client.post("/api/schedule-queue", json=payload(future, "2030-01-08T21:30:00+07:00"))
    assert existing.status_code == 200

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "clips": [{"video_path": str(video_a), "product_id": "A", "product_name": "A"}, {"video_path": str(video_b), "product_id": "B", "product_name": "B"}],
            "seed": 5,
        },
    )

    assert preview.status_code == 200
    assert len(preview.json()["items"]) == 2
    assert {row["scheduled_at"][:10] for row in preview.json()["items"]} == {"2030-01-07"}


def test_autofill_avoids_adjacent_product_and_hook_color_duplicates(queue_workspace):
    video_a, video_b = queue_workspace
    extra_videos = []
    for name in ("c", "d", "e", "f"):
        path = video_a.parent / f"{name}.mp4"
        path.write_bytes(name.encode())
        extra_videos.append(path)

    previous = client.post(
        "/api/schedule-queue",
        json={**payload(video_a, "2030-01-07T09:00:00+07:00"), "product_id": "A", "style_preset": "viral_punch"},
    ).json()["items"][0]
    assert client.patch(f"/api/schedule-queue/{previous['id']}", json={"status": "posted"}).status_code == 200
    clips = [
        {"video_path": str(video_b), "product_id": "A", "product_name": "A", "style_preset": "clean_tech_review"},
        {"video_path": str(extra_videos[0]), "product_id": "B", "product_name": "B", "style_preset": "viral_punch"},
        {"video_path": str(extra_videos[1]), "product_id": "B", "product_name": "B", "style_preset": "clean_tech_review"},
        {"video_path": str(extra_videos[2]), "product_id": "C", "product_name": "C", "style_preset": "tech_product_showcase"},
        {"video_path": str(extra_videos[3]), "product_id": "D", "product_name": "D", "style_preset": "flash_deal"},
    ]

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": clips, "seed": 12},
    )

    assert preview.status_code == 200
    rows = preview.json()["items"]
    assert len(rows) >= 3
    assert rows[0]["product_id"] != "A"
    assert rows[0]["hook_color"] != "#FE2C55"
    for previous_row, row in zip(rows, rows[1:]):
        assert previous_row["product_id"] != row["product_id"]
        assert previous_row["hook_color"] != row["hook_color"]


def test_autofill_does_not_repeat_product_after_posted_previous_slot(queue_workspace):
    video_a, video_b = queue_workspace
    occupied_videos = []
    for name, when in (("c", "2030-01-07T09:00:00+07:00"), ("d", "2030-01-07T12:30:00+07:00"), ("e", "2030-01-07T16:00:00+07:00")):
        video = video_a.parent / f"{name}.mp4"
        video.write_bytes(name.encode())
        occupied_videos.append((video, when))
    for video, when in occupied_videos:
        row = client.post(
            "/api/schedule-queue",
            json={**payload(video, when), "product_id": f"OTHER-{video.stem}", "product_name": "Other product"},
        ).json()["items"][0]
        assert client.patch(f"/api/schedule-queue/{row['id']}", json={"status": "posted"}).status_code == 200
    previous = client.post(
        "/api/schedule-queue",
        json={**payload(video_a, "2030-01-07T19:00:00+07:00"), "product_id": "LOOP", "product_name": "LOOP Smartband", "style_preset": "viral_punch"},
    ).json()["items"][0]
    assert client.patch(f"/api/schedule-queue/{previous['id']}", json={"status": "posted"}).status_code == 200

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "clips": [{"video_path": str(video_b), "product_id": "LOOP", "product_name": "LOOP Smartband", "style_preset": "clean_tech_review"}],
            "limit": 1,
            "seed": 4,
        },
    )

    assert preview.status_code == 200
    result = preview.json()
    assert result["items"] == []
    assert result["skipped_repetition"] == 1


def test_autofill_skips_clip_recorded_in_post_history_when_queue_row_is_missing(queue_workspace, monkeypatch):
    video_a, _ = queue_workspace
    monkeypatch.setattr(
        queue_api.PostLog,
        "list_posts",
        classmethod(lambda cls, newest_first=True: [{"id": "old-loop", "clip_file": video_a.name, "posted_at": "2026-09-17T19:00:00+07:00", "product_name": "LOOP Smartband"}]),
    )

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": [{"video_path": str(video_a), "product_id": "LOOP", "product_name": "LOOP Smartband"}]},
    )

    assert preview.status_code == 200
    result = preview.json()
    assert result["items"] == []
    assert result["skipped_invalid"][0]["video_path"] == str(video_a)


def test_autofill_does_not_treat_unknown_product_metadata_as_duplicate(queue_workspace):
    video_a, video_b = queue_workspace
    for name, when in (("c", "2030-01-07T09:00:00+07:00"), ("d", "2030-01-07T12:30:00+07:00"), ("e", "2030-01-07T16:00:00+07:00"), ("f", "2030-01-07T19:00:00+07:00")):
        video = video_a.parent / f"{name}.mp4"
        video.write_bytes(name.encode())
        row_payload = {"video_path": str(video), "scheduled_at": when}
        if name == "f":
            row_payload["hook_color"] = "#FFE600"
        row = client.post("/api/schedule-queue", json=row_payload).json()["items"][0]
        assert client.patch(f"/api/schedule-queue/{row['id']}", json={"status": "posted"}).status_code == 200

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": [{"video_path": str(video_b), "hook_color": "#FFE600"}], "limit": 1},
    )

    assert preview.status_code == 200
    assert len(preview.json()["items"]) == 1


def test_autofill_blocks_product_used_earlier_same_day_even_after_other_product(queue_workspace):
    video_a, video_b = queue_workspace
    rows = []
    for name, when, product_id, product_name in (
        ("c", "2030-01-07T09:00:00+07:00", "A", "Other A"),
        ("d", "2030-01-07T12:30:00+07:00", "B", "Other B"),
        ("e", "2030-01-07T16:00:00+07:00", "C", "Other C"),
        ("f", "2030-01-07T19:00:00+07:00", "LOOP", "LOOP Smartband"),
        ("g", "2030-01-07T21:00:00+07:00", "D", "Other D"),
    ):
        video = video_a.parent / f"{name}.mp4"
        video.write_bytes(name.encode())
        row = client.post(
            "/api/schedule-queue",
            json={**payload(video, when), "product_id": product_id, "product_name": product_name, "style_preset": "clean_tech_review"},
        ).json()["items"][0]
        rows.append(row)
    for row in rows:
        assert client.patch(f"/api/schedule-queue/{row['id']}", json={"status": "posted"}).status_code == 200

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "clips": [{"video_path": str(video_b), "product_id": "LOOP", "product_name": "LOOP Smartband", "style_preset": "viral_punch"}],
            "limit": 1,
        },
    )

    assert preview.status_code == 200
    result = preview.json()
    assert result["items"] == []
    assert result["skipped_repetition"] == 1


def test_autofill_commit_rechecks_daily_product_constraint(queue_workspace):
    video_a, video_b = queue_workspace
    existing = client.post(
        "/api/schedule-queue",
        json={**payload(video_a, "2030-01-07T09:00:00+07:00"), "product_id": "LOOP", "product_name": "LOOP Smartband", "style_preset": "viral_punch"},
    )
    assert existing.status_code == 200

    commit = client.post(
        "/api/schedule-queue/auto-fill",
        json={
            "items": [{
                "video_path": str(video_b),
                "scheduled_at": "2030-01-07T12:30:00+07:00",
                "product_id": "LOOP",
                "product_name": "LOOP Smartband",
                "style_preset": "clean_tech_review",
            }],
        },
    )

    assert commit.status_code == 409
    listed = client.get("/api/schedule-queue").json()["items"]
    assert len(listed) == 1
    assert listed[0]["video_path"].endswith("/a.mp4")
    assert listed[0]["product_id"] == "LOOP"


def test_autofill_commit_rechecks_duplicates_inside_same_batch(queue_workspace):
    video_a, video_b = queue_workspace
    commit = client.post(
        "/api/schedule-queue/auto-fill",
        json={
            "items": [
                {"video_path": str(video_a), "scheduled_at": "2030-01-07T09:00:00+07:00", "product_id": "A", "product_name": "A", "style_preset": "viral_punch"},
                {"video_path": str(video_b), "scheduled_at": "2030-01-07T12:30:00+07:00", "product_id": "A", "product_name": "A", "style_preset": "clean_tech_review"},
            ],
        },
    )

    assert commit.status_code == 409
    assert client.get("/api/schedule-queue").json()["items"] == []


def test_autofill_preview_reports_skip_summary(queue_workspace):
    video_a, video_b = queue_workspace
    existing = client.post("/api/schedule-queue", json=payload(video_a, "2030-01-07T09:00:00+07:00"))
    assert existing.status_code == 200

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "clips": [payload(video_a, "2030-01-07T09:00:00+07:00"), payload(video_b, "2030-01-07T12:30:00+07:00")],
            "limit": 1,
        },
    )

    assert preview.status_code == 200
    summary = preview.json()["skip_summary"]
    assert summary["already_queued"] == 1


def test_autofill_reports_stats_and_prefers_evidence_backed_time(queue_workspace, monkeypatch):
    video_a, video_b = queue_workspace
    monkeypatch.setattr(
        queue_api.PostLog,
        "list_posts",
        classmethod(lambda cls, newest_first=True: [
            {"product_name": "A", "posted_at": "2026-09-10T19:00:00", "metrics": {"views": 1000, "likes": 100, "cart_clicks": 50, "orders": 10, "commission_thb": 50}},
            {"product_name": "A", "posted_at": "2026-09-11T19:00:00", "metrics": {"views": 800, "likes": 80, "cart_clicks": 40, "orders": 10, "commission_thb": 50}},
            {"product_name": "A", "posted_at": "2026-09-12T19:00:00", "metrics": {"views": 900, "likes": 90, "cart_clicks": 45, "orders": 10, "commission_thb": 50}},
            {"product_name": "B", "posted_at": "2026-09-10T12:30:00", "metrics": {"views": 100, "likes": 5}},
        ]),
    )

    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "optimize_by_stats": True,
            "clips": [
                {"video_path": str(video_a), "product_id": "A", "product_name": "A", "style_preset": "clean_tech_review"},
                {"video_path": str(video_b), "product_id": "B", "product_name": "B", "style_preset": "viral_punch"},
            ],
            "seed": 3,
        },
    )

    assert preview.status_code == 200
    result = preview.json()
    assert result["analytics"]["sample_size"] == 4
    assert result["analytics"]["top_products"][0]["product_name"] == "A"
    assert result["analytics"]["top_hours"][0]["hour"] == 19
    # 12:30 has a single measured post: below the minimum sample, never ranked.
    assert [row["hour"] for row in result["analytics"]["top_hours"]] == [19]
    assert result["analytics"]["top_products"][0]["cart_click_rate"] > 0
    assert result["analytics"]["top_products"][0]["orders_per_1000_views"] > 0
    assert result["analytics"]["top_products"][0]["commission_per_1000_views_thb"] > 0
    assert any(row["scheduled_at"].startswith("2030-01-07T19:00") for row in result["items"])


def test_autofill_distributes_multiple_products_fairly_across_days_and_slots(queue_workspace):
    video_a, _ = queue_workspace
    clips = []
    presets = ["clean_tech_review", "viral_punch", "tech_compare", "tech_product_showcase", "flash_deal", "pain_punch"]
    # Create 6 products, each having 3 clips (18 clips total)
    for p_idx, p_name in enumerate(["ProdA", "ProdB", "ProdC", "ProdD", "ProdE", "ProdF"]):
        for c_idx in range(3):
            vpath = video_a.parent / f"{p_name}_{c_idx}.mp4"
            vpath.write_bytes(f"{p_name}_{c_idx}".encode())
            clips.append({
                "video_path": str(vpath),
                "product_id": f"id_{p_name}",
                "product_name": p_name,
                "style_preset": presets[p_idx],
            })

    # Request auto-fill for 3 days (Monday to Wednesday), with default template having slots per day
    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-09",
            "clips": clips,
            "seed": 42,
        },
    )

    assert preview.status_code == 200
    items = preview.json()["items"]
    assert len(items) >= 12  # At least 4-5 slots per day

    # Check product diversity: ALL 6 products should be scheduled!
    scheduled_products = {it["product_name"] for it in items}
    assert scheduled_products == {"ProdA", "ProdB", "ProdC", "ProdD", "ProdE", "ProdF"}

    # Check time slot rotation: no single product should be scheduled at 09:00 on all 3 days
    slot_0900_products = [it["product_name"] for it in items if "09:00" in it["scheduled_at"]]
    if len(slot_0900_products) >= 2:
        # Should not be identical product for all days at 09:00
        assert len(set(slot_0900_products)) > 1

