from __future__ import annotations

from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_review


@pytest.fixture()
def review_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    projects_dir = tmp_path / "03_Projects"
    cache_dir = projects_dir / ".cache" / "review"
    state_file = cache_dir / "review_state.json"

    monkeypatch.setattr(api_review.config, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(api_review, "REVIEW_CACHE_DIR", cache_dir)
    monkeypatch.setattr(api_review, "REVIEW_STATE_FILE", state_file)
    monkeypatch.setattr(api_review.ProductStore, "get_all", classmethod(lambda cls: []))

    # Create a composition HTML with #b-cta[data-start="27.8"] for clip_01
    clip1_dir = projects_dir / "TTZ01_clip_01"
    clip1_dir.mkdir(parents=True, exist_ok=True)
    (clip1_dir / "index.html").write_text(
        """<!DOCTYPE html>
<html>
<body>
  <div id="chat-track" data-start="0.0" data-duration="27.8"></div>
  <div class="cta-card" id="b-cta" data-start="27.8" data-duration="3.2">สั่งซื้อที่ตะกร้าซ้ายล่าง</div>
</body>
</html>
""",
        encoding="utf-8",
    )

    api_review.seed_review_clips(
        [
            {
                "clip_id": "TTZ01_clip_01",
                "product_code": "TTZ01",
                "angle_id": "angle_01",
                "title": "พัดลมพกพา ลมแรงไม่กลัวร้อน",
                "qc_status": "pending",
                "turns": [
                    {
                        "speaker": "น้องนุ้ย",
                        "display": "พี่บ่าว ร้อนขนาดนี้เอาไรมาเป่า",
                        "spoken": "พี่บ่าว ร้อนพันนี้เอาไอไหรมาเป่าเนี่ย",
                        "photo": "photo_1.jpg",
                    },
                    {
                        "speaker": "พี่บ่าว",
                        "display": "ตัวนี้เลยพัดลมเทอร์โบพกพา ลมแรงจริง",
                        "spoken": "ตัวนี้เลยน้องนุ้ย พัดลมเทอร์โบพกพา ลมแรงจริงนิ",
                        "photo": None,
                    },
                ],
                "available_photos": ["photo_1.jpg", "photo_2.jpg", "photo_3.jpg"],
                "revision": 1,
            },
            {
                "clip_id": "TTZ01_clip_02",
                "product_code": "TTZ01",
                "angle_id": "angle_02",
                "title": "แบตอึดพกไปแคมป์ปิ้ง",
                "qc_status": "pending",
                "turns": [
                    {
                        "speaker": "น้องนุ้ย",
                        "display": "แบตอยู่ได้นานไหมพี่บ่าว",
                        "spoken": "แบตอยู่ได้นานหม้ายพี่บ่าว",
                        "photo": None,
                    }
                ],
                "available_photos": ["photo_1.jpg", "photo_2.jpg"],
                "revision": 1,
            },
            {
                "clip_id": "HAT01_clip_01",
                "product_code": "HAT01",
                "angle_id": "angle_01",
                "title": "พัดลมตั้งโต๊ะเสียงเงียบ",
                "qc_status": "passed",
                "turns": [],
                "available_photos": [],
                "revision": 2,
            },
        ]
    )

    app = FastAPI()
    app.include_router(api_review.router)
    return TestClient(app)


def test_get_review_queue_and_filtering(review_env: TestClient):
    resp = review_env.get("/api/review/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3

    # Filter by product_code
    resp_ttz = review_env.get("/api/review/queue", params={"product_code": "TTZ01"})
    assert resp_ttz.status_code == 200
    assert [c["clip_id"] for c in resp_ttz.json()] == ["TTZ01_clip_01", "TTZ01_clip_02"]

    # Filter by status=pending
    resp_pending = review_env.get("/api/review/queue", params={"status": "pending"})
    assert resp_pending.status_code == 200
    assert [c["clip_id"] for c in resp_pending.json()] == ["TTZ01_clip_01", "TTZ01_clip_02"]


def test_snapshots_extract_cta_t_from_b_cta_and_serve_webp(review_env: TestClient):
    resp = review_env.post("/api/review/TTZ01_clip_01/snapshots")
    assert resp.status_code == 200
    info = resp.json()
    assert info["cta_t"] == pytest.approx(27.8)
    assert info["cta_t"] > 0.0
    assert Path(info["chat_webp_path"]).is_file()
    assert Path(info["cta_webp_path"]).is_file()

    # Fetch chat & cta WebP snapshots via GET endpoint
    chat_res = review_env.get("/api/review/TTZ01_clip_01/snapshots/chat")
    assert chat_res.status_code == 200
    assert chat_res.headers["content-type"] == "image/webp"
    assert "Cache-Control" in chat_res.headers
    assert "ETag" in chat_res.headers
    assert chat_res.content[:4] == b"RIFF"
    assert chat_res.content[8:12] == b"WEBP"

    # Conditional GET with If-None-Match returns 304
    etag = chat_res.headers["ETag"]
    cached_res = review_env.get(
        "/api/review/TTZ01_clip_01/snapshots/chat",
        headers={"If-None-Match": etag},
    )
    assert cached_res.status_code == 304


def test_decision_requires_seen_and_reject_note(review_env: TestClient):
    # Cannot approve when seen=False
    unseen_res = review_env.post(
        "/api/review/TTZ01_clip_01/decision",
        json={"decision": "pass", "note": "", "seen": False},
    )
    assert unseen_res.status_code == 422
    assert unseen_res.json()["detail"] == "seen_required_before_decision"

    # Cannot reject without a note
    empty_note_res = review_env.post(
        "/api/review/TTZ01_clip_01/decision",
        json={"decision": "reject", "note": "   ", "seen": True},
    )
    assert empty_note_res.status_code == 422
    assert empty_note_res.json()["detail"] == "reject_note_required"

    # Valid reject with note
    reject_res = review_env.post(
        "/api/review/TTZ01_clip_01/decision",
        json={"decision": "reject", "note": "คำผิดบรรทัดแรก", "seen": True},
    )
    assert reject_res.status_code == 200
    rejected_clip = reject_res.json()
    assert rejected_clip["qc_status"] == "rejected"
    assert rejected_clip["qc_note"] == "คำผิดบรรทัดแรก"

    # Valid pass when seen=True
    pass_res = review_env.post(
        "/api/review/TTZ01_clip_02/decision",
        json={"decision": "pass", "note": "", "seen": True},
    )
    assert pass_res.status_code == 200
    assert pass_res.json()["qc_status"] == "passed"


def test_batch_approve_only_seen_clips(review_env: TestClient):
    # Only mark TTZ01_clip_01 as seen; TTZ01_clip_02 remains unseen
    batch_res = review_env.post(
        "/api/review/batch-approve-seen",
        json={"seen_clip_ids": ["TTZ01_clip_01"]},
    )
    assert batch_res.status_code == 200
    body = batch_res.json()
    assert body["approved_clip_ids"] == ["TTZ01_clip_01"]
    assert body["approved_count"] == 1
    assert body["skipped_unseen_count"] >= 1

    # Verify TTZ01_clip_02 is still pending
    queue = review_env.get("/api/review/queue", params={"product_code": "TTZ01"}).json()
    by_id = {c["clip_id"]: c for c in queue}
    assert by_id["TTZ01_clip_01"]["qc_status"] == "passed"
    assert by_id["TTZ01_clip_02"]["qc_status"] == "pending"


def test_light_edit_updates_display_locks_spoken_and_steps_timing(review_env: TestClient):
    # 1. Attempt to mutate spoken text -> 400 spoken_locked_in_light_edit
    locked_res = review_env.patch(
        "/api/review/TTZ01_clip_01/script",
        json={
            "turns": [
                {
                    "index": 0,
                    "display": "พี่บ่าว ร้อนมากเอาไรมาเป่า",
                    "spoken": "พยายามแก้บทพากย์ใหม่",
                }
            ]
        },
    )
    assert locked_res.status_code == 400
    assert locked_res.json()["detail"] == "spoken_locked_in_light_edit"

    # 2. Attempt to put forbidden price or ellipsis in display -> 422
    price_res = review_env.patch(
        "/api/review/TTZ01_clip_01/script",
        json={"turns": [{"index": 0, "display": "ตัวนี้แค่ 199 บาท"}]},
    )
    assert price_res.status_code == 422
    assert price_res.json()["detail"] == "display_contains_forbidden_price"

    ellipsis_res = review_env.patch(
        "/api/review/TTZ01_clip_01/script",
        json={"turns": [{"index": 0, "display": "พี่บ่าว... ร้อนจัง"}]},
    )
    assert ellipsis_res.status_code == 422
    assert ellipsis_res.json()["detail"] == "display_contains_ellipsis"

    # 3. Valid light edit: update display, change photo, adjust timing_offset_sec by +0.3s
    ok_res = review_env.patch(
        "/api/review/TTZ01_clip_01/script",
        json={
            "turns": [
                {
                    "index": 0,
                    "display": "พี่บ่าว ร้อนขนาดนี้เอาตัวไหนมาเป่าดี",
                    "photo": "photo_2.jpg",
                }
            ],
            "timing_offset_sec": 0.3,
            "base_revision": 1,
        },
    )
    assert ok_res.status_code == 200
    updated = ok_res.json()
    assert updated["revision"] == 2
    assert updated["timing_offset_sec"] == pytest.approx(0.3)
    assert updated["turns"][0]["display"] == "พี่บ่าว ร้อนขนาดนี้เอาตัวไหนมาเป่าดี"
    assert updated["turns"][0]["spoken"] == "พี่บ่าว ร้อนพันนี้เอาไอไหรมาเป่าเนี่ย"
    assert updated["turns"][0]["photo"] == "photo_2.jpg"
    assert updated["rerender_job_id"].startswith("rerender_TTZ01_clip_01_v2_")
