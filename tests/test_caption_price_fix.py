"""Captions with price wording are rewritten (AI, then the posting guard) instead of failing at posting time.

Owner decision 2026-11-13: "AI เขียนใหม่" + "แก้อัตโนมัติแล้วบอก". Offline: the AI call is replaced by a fake.
"""
import pytest

import scripts.caption_price_fix as cpf
from scripts.content_guard import content_reason
from tests.test_schedule_queue import client, payload, queue_workspace  # noqa: F401

PRICEY = "🔥 ช้าหมดอดราคาเปิดตัว! พัดลมแม่เหล็ก HOYAUP เย็นเฉียบ 👇"
CLEAN = "🔥 ช้าหมดอดของล็อตแรก! พัดลมแม่เหล็ก HOYAUP เย็นเฉียบ 👇"


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cpf, "_cache_path", lambda: tmp_path / "caption_price_fix.json")


@pytest.fixture
def fake_ai(monkeypatch):
    calls = []

    def rewrite(caption, product_name, found):
        calls.append((caption, product_name, found))
        return CLEAN
    monkeypatch.setattr(cpf, "_ai_rewrite", rewrite)
    return calls


def test_ai_rewrite_passes_the_guard_and_is_cached(fake_ai):
    first = cpf.fix_caption(PRICEY, "#พัดลม", "HOYAUP พัดลม")
    assert first == {"caption": CLEAN, "hashtags": "#พัดลม", "method": "ai", "found": ["ราคา"], "changed": True}
    assert content_reason(first["caption"], first["hashtags"]) == ""
    assert cpf.fix_caption(PRICEY, "#พัดลม", "HOYAUP พัดลม") == first          # preview and save give the same text
    assert len(fake_ai) == 1


def test_clean_caption_is_untouched(fake_ai):
    assert cpf.fix_caption(CLEAN, "#พัดลม")["changed"] is False
    assert fake_ai == []


@pytest.mark.parametrize("answer", ["ยังลดราคาอยู่นะ", "ดีมาก...", "", "#แท็กในแคปชั่น"])
def test_an_answer_the_guard_refuses_falls_back_to_the_neutral_caption(monkeypatch, answer):
    monkeypatch.setattr(cpf, "_ai_rewrite", lambda *a: answer)
    result = cpf.fix_caption(PRICEY, "", "พัดลม HOYAUP")
    assert result["method"] == "neutral"
    assert result["caption"] == "พัดลม HOYAUP ดูรายละเอียดในตะกร้าเลยครับ 👇"
    assert content_reason(result["caption"], result["hashtags"]) == ""


def test_ai_unavailable_never_blocks(monkeypatch):
    def broken(*_):
        raise RuntimeError("quota")
    monkeypatch.setattr(cpf, "_ai_rewrite", broken)
    assert cpf.fix_caption(PRICEY, "", "พัดลม")["method"] == "neutral"


def test_price_only_in_hashtags_drops_those_tags_and_keeps_the_caption(fake_ai):
    result = cpf.fix_caption(CLEAN, "#พัดลม #ลดราคา", "x")
    assert result["caption"] == CLEAN and result["hashtags"] == "#พัดลม" and result["method"] == "hashtags"
    assert fake_ai == []


def test_queue_entry_rewrites_the_caption_and_keeps_the_trail(queue_workspace, fake_ai):
    video_a, _ = queue_workspace
    res = client.post("/api/schedule-queue", json={**payload(video_a, "2026-12-01T09:00:00+07:00"), "caption": PRICEY,
                                                   "caption_fix": {"method": "spoofed"}})
    assert res.status_code == 200, res.text
    row = client.get("/api/schedule-queue").json()["items"][0]
    assert row["caption"] == CLEAN
    assert row["caption_fix"]["from_caption"] == PRICEY and row["caption_fix"]["method"] == "ai"
    assert "caption_blocked" not in row


def test_batch_fix_previews_then_saves_only_unchanged_waiting_rows(queue_workspace, monkeypatch, fake_ai):
    from scripts.schedule_store import ScheduleQueueStore
    video_a, video_b = queue_workspace
    ScheduleQueueStore._save([
        {"id": "q1", "channel_id": "main", "video_path": "04_Exports/Ready_to_post/a.mp4", "status": "planned",
         "scheduled_at": "2026-12-01T09:00+07:00", "caption": PRICEY, "hashtags": "#พัดลม"},
        {"id": "q2", "channel_id": "main", "video_path": "04_Exports/Ready_to_post/b.mp4", "status": "ready_for_extension",
         "scheduled_at": "2026-12-01T12:00+07:00", "caption": PRICEY, "hashtags": ""},
    ])
    listed = {r["id"]: r for r in client.get("/api/schedule-queue").json()["items"]}
    assert listed["q1"]["caption_blocked"] == "price_in_caption" and "caption_blocked" not in listed["q2"]
    preview = client.post("/api/schedule-queue/fix-price-captions/preview").json()
    assert [i["id"] for i in preview["items"]] == ["q1"] and preview["locked_count"] == 1
    assert ScheduleQueueStore.get_item("q1")["caption"] == PRICEY                      # a preview writes nothing
    refused = client.post("/api/schedule-queue/fix-price-captions",
                          json={"items": [{**preview["items"][0], "caption": "ยังมีราคาอยู่"}]})
    assert refused.status_code == 422
    stale = client.post("/api/schedule-queue/fix-price-captions",
                        json={"items": [{**preview["items"][0], "from_caption": "อย่างอื่น"}]})
    assert stale.status_code == 409
    saved = client.post("/api/schedule-queue/fix-price-captions", json={"items": preview["items"]})
    assert saved.status_code == 200, saved.text
    row = ScheduleQueueStore.get_item("q1")
    assert row["caption"] == CLEAN and row["caption_fix"]["from_caption"] == PRICEY
    assert ScheduleQueueStore.get_item("q2")["caption"] == PRICEY                      # the extension's frozen job is not touched
