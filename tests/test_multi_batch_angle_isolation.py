"""
Unit tests for multi-batch script angle isolation and rollback behavior.
Ensures that when multiple batches share identical angle_ids (e.g. pain_point in Batch 1 and Batch 2):
1. Status and project updates isolate cleanly per (batch, angle_id).
2. Project lookup returns the correct batch.
3. Deleting or rolling back a project for batch 2 rolls back ONLY batch 2 to scripted.
4. ShotListsStore isolates audio/beat records per batch.
"""

import pytest
from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    docs_dir = tmp_path / "_Docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.product_store.STORE_PATH", docs_dir / "products.json")
    monkeypatch.setattr("scripts.product_store.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.shot_lists_store.STORE_PATH", docs_dir / "shot_lists.json")
    monkeypatch.setattr("scripts.shot_lists_store.BASE_DIR", tmp_path)


def test_multi_batch_status_isolation_and_rollback():
    # 1. Create a product with two batches of angles sharing the same angle_id
    product = ProductStore.add(
        name="BlueWow Test Cooler",
        angles=[
            {
                "angle_id": "pain_point",
                "angle_name": "Batch 1 Pain Point",
                "status": "rendered",
                "project_name": "BLU01-ปัญหาก่อนใช้_1",
                "video_url": "exports/BLU01-ปัญหาก่อนใช้_1.mp4",
                "batch": 1,
            },
            {
                "angle_id": "pain_point",
                "angle_name": "Batch 2 Pain Point",
                "status": "scripted",
                "project_name": None,
                "video_url": None,
                "batch": 2,
            },
        ],
    )
    product_id = product["id"]

    # 2. Update Batch 2 to in_production with project_name BLU01-ปัญหาก่อนใช้_2
    ProductStore.update_angle_status(
        product_id=product_id,
        angle_id="pain_point",
        status="in_production",
        project_name="BLU01-ปัญหาก่อนใช้_2",
        batch=2,
    )

    p_after_update = ProductStore.get(product_id)
    b1_angle = next(a for a in p_after_update["angles"] if a.get("batch") == 1)
    b2_angle = next(a for a in p_after_update["angles"] if a.get("batch") == 2)

    assert b1_angle["status"] == "rendered"
    assert b1_angle["project_name"] == "BLU01-ปัญหาก่อนใช้_1"
    assert b2_angle["status"] == "in_production"
    assert b2_angle["project_name"] == "BLU01-ปัญหาก่อนใช้_2"

    # 3. Find by project should correctly distinguish between batches
    found_b1 = ProductStore.find_by_project("BLU01-ปัญหาก่อนใช้_1")
    assert found_b1 is not None
    assert found_b1[1].get("batch") == 1

    found_b2 = ProductStore.find_by_project("BLU01-ปัญหาก่อนใช้_2")
    assert found_b2 is not None
    assert found_b2[1].get("batch") == 2

    # 4. Rollback of Batch 2 project should ONLY roll back Batch 2 to scripted
    p_rolled = ProductStore.rollback_by_video_or_project("BLU01-ปัญหาก่อนใช้_2")
    assert p_rolled is not None

    p_final = ProductStore.get(product_id)
    b1_final = next(a for a in p_final["angles"] if a.get("batch") == 1)
    b2_final = next(a for a in p_final["angles"] if a.get("batch") == 2)

    # Batch 1 is completely preserved
    assert b1_final["status"] == "rendered"
    assert b1_final["project_name"] == "BLU01-ปัญหาก่อนใช้_1"

    # Batch 2 is reset cleanly
    assert b2_final["status"] == "scripted"
    assert b2_final["project_name"] is None
    assert b2_final["video_url"] is None


def test_shot_lists_store_multi_batch_isolation():
    product_id = "test_prod_123"
    angle_id = "pain_point"

    # Save shot lists for Batch 1 and Batch 2
    ShotListsStore.upsert({
        "product_id": product_id,
        "angle_id": angle_id,
        "beat_cues": ["b1_cue1"],
        "voice_preset": "voice1",
    }, batch=1)
    ShotListsStore.upsert({
        "product_id": product_id,
        "angle_id": angle_id,
        "beat_cues": ["b2_cue1", "b2_cue2"],
        "voice_preset": "voice2",
    }, batch=2)

    rec1 = ShotListsStore.get(product_id, angle_id, batch=1)
    rec2 = ShotListsStore.get(product_id, angle_id, batch=2)

    assert rec1 is not None
    assert rec1["beat_cues"] == ["b1_cue1"]
    assert rec1["voice_preset"] == "voice1"

    assert rec2 is not None
    assert rec2["beat_cues"] == ["b2_cue1", "b2_cue2"]
    assert rec2["voice_preset"] == "voice2"

    # Deleting Batch 2 shot list does not affect Batch 1
    ShotListsStore.delete(product_id, angle_id, batch=2)
    assert ShotListsStore.get(product_id, angle_id, batch=2) is None
    assert ShotListsStore.get(product_id, angle_id, batch=1) is not None


def test_update_angle_videos_and_voice_batch_isolation():
    product = ProductStore.add(
        name="Multi Batch Video Voice Test",
        angles=[
            {
                "angle_id": "pain_point",
                "angle_name": "Batch 1 Pain Point",
                "selected_videos": ["raw/b1_clip.mp4"],
                "voice_preset": "voice_1",
                "batch": 1,
            },
            {
                "angle_id": "pain_point",
                "angle_name": "Batch 2 Pain Point",
                "selected_videos": [],
                "voice_preset": "voice_default",
                "batch": 2,
            },
        ],
    )
    product_id = product["id"]

    # Update videos for batch 2
    ProductStore.update_angle_videos(product_id, "pain_point", ["raw/b2_clip.mp4"], batch=2)
    # Update voice for batch 2
    ProductStore.update_angle_voice(product_id, "pain_point", voice_preset="voice_2_pro", batch=2)

    p_updated = ProductStore.get(product_id)
    b1 = next(a for a in p_updated["angles"] if a.get("batch") == 1)
    b2 = next(a for a in p_updated["angles"] if a.get("batch") == 2)

    # Batch 1 unchanged
    assert b1["selected_videos"] == ["raw/b1_clip.mp4"]
    assert b1["voice_preset"] == "voice_1"

    # Batch 2 updated
    assert b2["selected_videos"] == ["raw/b2_clip.mp4"]
    assert b2["voice_preset"] == "voice_2_pro"


def test_remove_angle_batch_isolation():
    product = ProductStore.add(
        name="Multi Batch Remove Angle Test",
        angles=[
            {
                "angle_id": "pain_point",
                "angle_name": "Batch 1 Pain Point",
                "status": "scripted",
                "batch": 1,
            },
            {
                "angle_id": "pain_point",
                "angle_name": "Batch 2 Pain Point",
                "status": "scripted",
                "batch": 2,
            },
        ],
    )
    product_id = product["id"]

    # Remove only Batch 2
    res = ProductStore.remove_angle(product_id, "pain_point", batch=2)
    assert res["angles_left"] == 1

    p_after = ProductStore.get(product_id)
    assert len(p_after["angles"]) == 1
    remaining_angle = p_after["angles"][0]
    assert remaining_angle.get("batch") == 1
    assert remaining_angle.get("angle_id") == "pain_point"


def test_replace_angle_content_batch_isolation():
    product = ProductStore.add(
        name="Multi Batch Replace Content Test",
        angles=[
            {
                "angle_id": "pain_point",
                "hook_title": "Original B1 Hook",
                "batch": 1,
            },
            {
                "angle_id": "pain_point",
                "hook_title": "Original B2 Hook",
                "batch": 2,
            },
        ],
    )
    product_id = product["id"]

    # Seed shot lists for both batches
    ShotListsStore.upsert({"product_id": product_id, "angle_id": "pain_point", "custom_script": "b1 script"}, batch=1)
    ShotListsStore.upsert({"product_id": product_id, "angle_id": "pain_point", "custom_script": "b2 script"}, batch=2)

    # Replace content for Batch 2 only
    ProductStore.replace_angle_content(
        product_id,
        "pain_point",
        {"hook_title": "Rerolled B2 Hook"},
        batch=2,
    )

    p_after = ProductStore.get(product_id)
    b1 = next(a for a in p_after["angles"] if a.get("batch") == 1)
    b2 = next(a for a in p_after["angles"] if a.get("batch") == 2)

    assert b1["hook_title"] == "Original B1 Hook"
    assert b2["hook_title"] == "Rerolled B2 Hook"

    # Shot list for Batch 2 deleted, but Batch 1 preserved
    assert ShotListsStore.get(product_id, "pain_point", batch=2) is None
    assert ShotListsStore.get(product_id, "pain_point", batch=1) is not None


def test_update_angle_cover_batch_isolation(tmp_path, monkeypatch):
    covers_dir = tmp_path / "05_Covers_Thumbnails"
    covers_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.product_store.COVERS_DIR", covers_dir)

    cover1 = covers_dir / "cover1_cover_3x4.jpg"
    cover1.write_bytes(b"dummy1")
    cover2 = covers_dir / "cover2_cover_3x4.jpg"
    cover2.write_bytes(b"dummy2")

    product = ProductStore.add(
        name="Multi Batch Cover Test",
        angles=[
            {"angle_id": "pain_point", "batch": 1},
            {"angle_id": "pain_point", "batch": 2},
        ],
    )
    product_id = product["id"]

    ProductStore.update_angle_cover(product_id, "pain_point", cover_3x4_path=str(cover2), batch=2)

    p_after = ProductStore.get(product_id)
    b1 = next(a for a in p_after["angles"] if a.get("batch") == 1)
    b2 = next(a for a in p_after["angles"] if a.get("batch") == 2)

    assert b1.get("cover_3x4_path") is None
    assert b2.get("cover_3x4_path") is not None
    assert "cover2" in b2.get("cover_3x4_path")


