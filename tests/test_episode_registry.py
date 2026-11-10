"""EP numbers: permanent, per lineage, atomic, carried in the caption as a hashtag."""
import threading

import pytest
from fastapi.testclient import TestClient

from scripts import api_episodes, config
from scripts.channel_store import ChannelError
from scripts.content_guard import content_reason
from scripts.episode_registry import DEFAULT_FIRST_NUMBER, EpisodeRegistry, compose_hashtags, lineage_key, tag_numbers
from scripts.posting_jobs import PostingJobStore


@pytest.fixture
def reg(tmp_path):
    return EpisodeRegistry(tmp_path)


def test_numbers_start_at_the_default_and_a_lineage_keeps_its_number_across_exports(reg):
    first = reg.ensure("main", product_id="p1", angle_id="a1", export_id="exp-1")
    assert first["episode_no"] == DEFAULT_FIRST_NUMBER == 1
    again = reg.ensure("main", product_id="p1", angle_id="a1", export_id="exp-1")
    assert again["episode_no"] == 1 and reg.next_number("main") == 2                 # idempotent, nothing consumed
    rerender = reg.ensure("main", product_id="p1", angle_id="a1", export_id="exp-2")        # a re-render of the same angle
    assert rerender["episode_no"] == 1 and sorted(rerender["export_ids"]) == ["exp-1", "exp-2"]
    other = reg.ensure("main", product_id="p1", angle_id="a2", export_id="exp-3")
    assert other["episode_no"] == 2
    assert reg.by_export("main") == {"exp-1": 1, "exp-2": 1, "exp-3": 2}


def test_a_clip_without_product_or_angle_is_its_own_lineage_and_a_clip_with_nothing_is_refused(reg):
    assert reg.ensure("main", export_id="exp-solo")["lineage_key"] == "export:exp-solo"
    with pytest.raises(ChannelError) as err:
        reg.ensure("main")
    assert err.value.code == "episode_lineage_missing"
    assert lineage_key("p", "a", "e") == "angle:p:a"


def test_channels_count_separately(reg):
    assert reg.ensure("main", export_id="e1")["episode_no"] == 1
    assert reg.ensure("second", export_id="e1")["episode_no"] == 1
    assert reg.ensure("main", export_id="e2")["episode_no"] == 2


def test_parallel_issuing_never_duplicates_or_skips_a_number(tmp_path):
    results, errors = [], []

    def worker(index):
        try:
            results.append(EpisodeRegistry(tmp_path).ensure("main", export_id=f"exp-{index}")["episode_no"])
        except Exception as exc:                     # pragma: no cover - the assertion below reports it
            errors.append(exc)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    assert sorted(results) == list(range(1, 13))


def test_the_counter_can_be_raised_but_never_onto_an_issued_number(reg):
    reg.ensure("main", export_id="e1")
    reg.ensure("main", export_id="e2")                                                         # 1, 2
    with pytest.raises(ChannelError) as err:
        reg.set_next("main", 2)
    assert err.value.code == "episode_next_taken"
    assert reg.set_next("main", 2000) == 2000
    assert reg.ensure("main", export_id="e3")["episode_no"] == 2000
    with pytest.raises(ChannelError):
        reg.set_next("main", 0)


def test_backfill_numbers_are_explicit_and_unused_and_the_counter_follows_them(reg):
    reg.ensure("main", export_id="old-1", number=1, source="backfill")
    reg.ensure("main", export_id="old-2", number=2, source="backfill")
    assert reg.next_number("main") == 3                                                         # the counter moves past the backfilled numbers
    with pytest.raises(ChannelError) as err:
        reg.ensure("main", export_id="old-3", number=2, source="backfill")
    assert err.value.code == "episode_number_taken"
    assert reg.ensure("main", export_id="new-1")["episode_no"] == 3
    reg.ensure("main", export_id="far", number=500, source="backfill")                          # an explicit higher number never lowers it
    assert reg.next_number("main") == 501


def test_hashtag_form_is_idempotent_and_refuses_another_clips_number():
    assert compose_hashtags("#a #b", 1731) == "#a #b #EP1731"
    assert compose_hashtags("#a #b #EP1731", 1731) == "#a #b #EP1731"
    assert compose_hashtags("", 1731) == "#EP1731"
    assert compose_hashtags("#a", None) == "#a"
    assert compose_hashtags("#a #ep01731", 1731) == "#a #ep01731"                              # zero padding / case = the same tag
    with pytest.raises(ChannelError) as err:
        compose_hashtags("#a #EP1700", 1731)
    assert err.value.code == "episode_tag_conflict"
    assert tag_numbers("x #EP1731 y #ep5 #EPX #EP12345678901") == [1731, 5]


def test_the_content_guard_accepts_the_tag_and_still_blocks_prices():
    assert content_reason("สรุปจุดเด่นพัดลม ดูก่อนตัดสินใจ", "#รีวิวของดี #EP1731") == ""
    assert content_reason("สรุปจุดเด่นพัดลม", "#EP1731 #EP1732") == ""
    assert content_reason("พัดลมราคา 199", "#EP1731") == "price_in_caption"


def test_listing_counts_what_really_left_through_the_app(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    registry = EpisodeRegistry(tmp_path)
    registry.ensure("main", export_id="e1")
    registry.ensure("main", export_id="e2")
    registry.ensure("main", export_id="e3")
    store = PostingJobStore(tmp_path)
    store.table.save([
        {"id": "j1", "job_id": "j1", "channel_id": "main", "export_id": "e1", "status": "published", "updated_at": 5},
        {"id": "j2", "job_id": "j2", "channel_id": "main", "export_id": "e2", "status": "prepared", "updated_at": 6},
        {"id": "j3", "job_id": "j3", "channel_id": "main", "export_id": "e3", "status": "scheduled_on_platform", "updated_at": 7},
        {"id": "j4", "job_id": "j4", "channel_id": "main", "export_id": "e3", "status": "cancelled", "updated_at": 9},
    ])
    listing = api_episodes.build_listing("main")
    assert listing["next"] == 4
    assert listing["summary"] == {"assigned": 3, "sent_via_app": 2, "first": 1, "last": 3}
    by = {row["episode_no"]: row["sent_via_app"] for row in listing["items"]}
    assert by[1]["status"] == "published" and by[2] is None and by[3]["status"] == "scheduled_on_platform"
