import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore
from scripts.task_manager import TaskManager
from scripts.gemini_tts_engine import GeminiTTSError
from scripts.api_shot_lists import _execute_batch_generate_audio_worker


@pytest.fixture
def sample_product():
    prod = ProductStore.add(
        name="ทดสอบสินค้า Batch Audio",
        angles=[
            {
                "angle_id": "ang_1",
                "hook_title": "ฮุก 1 ทดสอบ",
                "batch": 1,
                "script_lines": ["บรรทัด 1", "บรรทัด 2"],
            },
            {
                "angle_id": "ang_2",
                "hook_title": "ฮุก 2 ทดสอบ",
                "batch": 1,
                "script_lines": ["บรรทัด A", "บรรทัด B"],
            },
        ],
    )
    yield prod
    try:
        ProductStore.delete(prod["id"])
    except Exception:
        pass


def test_batch_audio_worker_skips_existing(sample_product, tmp_path):
    product_id = sample_product["id"]
    # Mock ang_1 as already having audio
    fake_audio = tmp_path / "fake_voice.wav"
    fake_audio.write_bytes(b"RIFF....WAVEfmt ")

    ShotListsStore.upsert({
        "product_id": product_id,
        "angle_id": "ang_1",
        "voice_audio_path": str(fake_audio),
        "custom_script": "บรรทัด 1\nบรรทัด 2",
        "voice_params": {"voice_preset": "gemini_puck_male_hype"},
    })

    task = TaskManager.create_task(
        task_type="batch_generate_audio",
        title="Test Batch",
        payload={"product_id": product_id},
    )

    with patch("scripts.api_shot_lists.generate_shot_list_for_angle") as mock_gen:
        mock_gen.return_value = {"success": True}
        _execute_batch_generate_audio_worker(
            task["id"],
            product_id,
            {"voice_preset": "gemini_puck_male_hype", "batch_index": 1},
        )

        # ang_1 should be skipped, only ang_2 should be generated
        assert mock_gen.call_count == 1
        call_args = mock_gen.call_args[0]
        assert call_args[0] == product_id
        assert call_args[1] == "ang_2"

    t = TaskManager.get_task(task["id"])
    assert t["status"] == "completed"
    assert t["result"]["generated"] == 1
    assert t["result"]["skipped"] == 1


def test_batch_audio_worker_handles_rate_limit_retry(sample_product):
    product_id = sample_product["id"]
    task = TaskManager.create_task(
        task_type="batch_generate_audio",
        title="Test Batch Rate Limit",
        payload={"product_id": product_id},
    )

    calls = []

    def mock_gen(p_id, a_id, overrides):
        calls.append(a_id)
        if len(calls) == 1:
            # First call on ang_1 hits 429 rate limit
            raise GeminiTTSError(
                message_th="Rate limit",
                code="GEMINI_TTS_RATE_LIMITED",
                retry_delay_seconds=1.0,
            )
        return {"success": True}

    with patch("scripts.api_shot_lists.generate_shot_list_for_angle", side_effect=mock_gen):
        with patch("time.sleep", return_value=None):
            _execute_batch_generate_audio_worker(
                task["id"],
                product_id,
                {"voice_preset": "gemini_puck_male_hype", "batch_index": 1, "force_regenerate": True},
            )

    t = TaskManager.get_task(task["id"])
    assert t["status"] == "completed"
    assert t["result"]["generated"] == 2
    # ang_1 called twice (1 failure + 1 retry success), ang_2 called once
    assert len(calls) == 3


def test_batch_audio_worker_skips_rendered_and_posted():
    prod = ProductStore.add(
        name="ทดสอบข้ามคลิปที่เสร็จและโพสต์แล้ว",
        angles=[
            {
                "angle_id": "ang_rendered",
                "hook_title": "คลิปตัดเสร็จแล้ว",
                "status": "rendered",
                "script_lines": ["บทพูด 1", "บทพูด 2"],
            },
            {
                "angle_id": "ang_posted",
                "hook_title": "คลิปโพสต์แล้ว",
                "status": "posted",
                "script_lines": ["บทพูด 1", "บทพูด 2"],
            },
            {
                "angle_id": "ang_posted_at",
                "hook_title": "คลิปมีวันโพสต์",
                "posted_at": "2026-09-15T09:00:00Z",
                "script_lines": ["บทพูด 1", "บทพูด 2"],
            },
            {
                "angle_id": "ang_pending",
                "hook_title": "คลิปที่รอทำ",
                "status": "scripted",
                "script_lines": ["บทพูด 1", "บทพูด 2"],
            },
        ],
    )
    product_id = prod["id"]
    try:
        task = TaskManager.create_task(
            task_type="batch_generate_audio",
            title="Test Batch Skip Completed",
            payload={"product_id": product_id},
        )

        with patch("scripts.api_shot_lists.generate_shot_list_for_angle") as mock_gen:
            mock_gen.return_value = {"success": True}
            _execute_batch_generate_audio_worker(
                task["id"],
                product_id,
                {"voice_preset": "gemini_puck_male_hype"},
            )

            # Only ang_pending should be generated!
            assert mock_gen.call_count == 1
            call_args = mock_gen.call_args[0]
            assert call_args[0] == product_id
            assert call_args[1] == "ang_pending"

        t = TaskManager.get_task(task["id"])
        assert t["status"] == "completed"
        assert t["result"]["total"] == 1
        assert t["result"]["generated"] == 1
        assert t["result"]["skipped"] == 0
    finally:
        try:
            with ProductStore._mutate() as prods:
                p = next((x for x in prods if x["id"] == product_id), None)
                if p:
                    for ang in p.get("angles", []):
                        ang["status"] = "scripted"
                        ang.pop("posted_at", None)
            ProductStore.delete(product_id)
        except Exception:
            pass


def test_batch_audio_worker_upgrades_legacy_edge_tts(sample_product, tmp_path):
    product_id = sample_product["id"]
    fake_audio = tmp_path / "fake_edge_voice.wav"
    fake_audio.write_bytes(b"RIFF....WAVEfmt ")

    # Mock ang_1 as having legacy edge_tts audio (without preset)
    ShotListsStore.upsert({
        "product_id": product_id,
        "angle_id": "ang_1",
        "voice_audio_path": str(fake_audio),
        "custom_script": "บรรทัด 1\nบรรทัด 2",
        "voice_params": {"voice_engine_type": "edge_tts", "voice_preset": None},
    })

    task = TaskManager.create_task(
        task_type="batch_generate_audio",
        title="Test Batch Upgrade Edge",
        payload={"product_id": product_id},
    )

    with patch("scripts.api_shot_lists.generate_shot_list_for_angle") as mock_gen:
        mock_gen.return_value = {"success": True}
        _execute_batch_generate_audio_worker(
            task["id"],
            product_id,
            {"voice_preset": "gemini_puck_male_hype", "batch_index": 1},
        )

        # ang_1 had edge_tts so it MUST NOT be skipped -- both ang_1 and ang_2 must be generated!
        assert mock_gen.call_count == 2
        calls = [c[0][1] for c in mock_gen.call_args_list]
        assert "ang_1" in calls
        assert "ang_2" in calls

    t = TaskManager.get_task(task["id"])
    assert t["status"] == "completed"
    assert t["result"]["generated"] == 2
    assert t["result"]["skipped"] == 0
