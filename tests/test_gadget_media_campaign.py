import json

import pytest

from scripts.gadget_media_campaign import (
    CAMPAIGN_TYPE,
    SERIES,
    CampaignStore,
    CampaignValidationError,
    ContentMetrics,
    SourceRef,
    create_starter_campaign,
)


def test_starter_campaign_has_the_21_slot_series_mix():
    campaign = create_starter_campaign(campaign_id="campaign-1")

    assert campaign.campaign_type == CAMPAIGN_TYPE
    assert len(campaign.slots) == 21
    assert [len([slot for slot in campaign.slots if slot.series == series]) for series in SERIES] == [9, 6, 6]
    assert all(slot.status == "planned" for slot in campaign.slots)


def test_publish_readiness_blocks_unreviewed_external_source():
    campaign = create_starter_campaign(campaign_id="campaign-2")
    slot = campaign.slots[0]
    slot.status = "edited"
    slot.script = "สรุปผลการใช้งานจริง"
    slot.source_refs = [
        SourceRef(
            source_url="https://example.com/official.mp4",
            rights_basis="commentary_excerpt",
            creator_or_brand="Example Brand",
            usage_note="ใช้เฉพาะช่วงสาธิตเพื่อวิเคราะห์ข้อจำกัด",
        )
    ]

    assert slot.ready_to_publish is False
    assert any("rights review is required" in error for error in slot.publish_readiness_errors())


def test_reviewed_commentary_source_can_pass_the_gate():
    campaign = create_starter_campaign(campaign_id="campaign-3")
    slot = campaign.slots[0]
    slot.status = "edited"
    slot.script = "สรุปผลการใช้งานจริง"
    slot.source_refs = [
        SourceRef(
            source_url="https://example.com/official.mp4",
            rights_basis="commentary_excerpt",
            creator_or_brand="Example Brand",
            usage_note="ใช้เฉพาะช่วงสาธิตเพื่อวิเคราะห์ข้อจำกัด",
            rights_reviewed=True,
        )
    ]

    assert slot.ready_to_publish is True
    assert campaign.readiness_summary()["ready_slots"] == 1


def test_metrics_calculate_follow_conversion():
    metrics = ContentMetrics(views=2500, follows=25, comments=9, completion_rate=42.5)

    assert metrics.follows_per_1000_views == 10.0
    assert metrics.to_dict()["completion_rate"] == 42.5


def test_store_round_trips_campaign_atomically(tmp_path):
    path = tmp_path / "campaigns.json"
    store = CampaignStore(path)
    campaign = create_starter_campaign(campaign_id="campaign-4")

    store.create(campaign)
    loaded = store.get("campaign-4")

    assert loaded.to_dict() == campaign.to_dict()
    assert json.loads(path.read_text(encoding="utf-8"))[0]["campaign_id"] == "campaign-4"
    assert not list(tmp_path.glob("*.tmp"))


def test_store_rejects_duplicate_campaign_id(tmp_path):
    store = CampaignStore(tmp_path / "campaigns.json")
    store.create(create_starter_campaign(campaign_id="duplicate"))

    with pytest.raises(CampaignValidationError, match="already exists"):
        store.create(create_starter_campaign(campaign_id="duplicate"))


def test_slot_update_preserves_other_slots_and_recalculates_readiness(tmp_path):
    store = CampaignStore(tmp_path / "campaigns.json")
    store.create(create_starter_campaign(campaign_id="campaign-5"))

    updated = store.update_slot(
        "campaign-5",
        "gadget-01",
        {
            "status": "scripted",
            "script": "สคริปต์ทดลอง",
        },
    )

    assert updated.status == "scripted"
    assert store.get("campaign-5").slots[1].slot_id == "gadget-02"
    assert store.get("campaign-5").slots[0].ready_to_publish is False
