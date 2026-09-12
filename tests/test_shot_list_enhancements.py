"""
Tests for ShotListsStore, invalidation on script change, and category-aware shot list directions.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from scripts.shot_lists_store import ShotListsStore
from scripts.shot_list_builder import (
    assign_beat_role,
    camera_direction_for_beat,
    build_shot_list,
)
from scripts.product_store import ProductStore


def test_assign_beat_role():
    assert assign_beat_role(0, 1) == "hook"
    assert assign_beat_role(0, 3) == "hook"
    assert assign_beat_role(1, 3) == "feature"
    assert assign_beat_role(2, 3) == "cta"


def test_camera_direction_category_aware():
    # Desk Tech Hook
    tech_hook = camera_direction_for_beat("hook", 0, "เมาส์ไร้สาย", "", "Logitech Lift", category="IT Desk Accessories")
    assert "45°" in tech_hook or "Top-Down" in tech_hook or "โต๊ะทำงาน" in tech_hook

    # Cable Hook
    cable_hook = camera_direction_for_beat("hook", 0, "สายชาร์จ", "", "Essager Cable", category="Charger and Cables")
    assert "Close-up" in cable_hook or "สาย" in cable_hook

    # Beauty Hook
    beauty_hook = camera_direction_for_beat("hook", 0, "ลิปบาล์ม", "", "Glasting Lip", category="Beauty Skincare")
    assert "Medium Close-up" in beauty_hook or "ใบหน้า" in beauty_hook

    # Generic Hook
    generic_hook = camera_direction_for_beat("hook", 0, "สินค้า", "", "Generic Product", category="Other")
    assert "Medium shot" in generic_hook


def test_build_shot_list():
    cues = [
        {"start": 0.0, "end": 2.5, "text": "เบื่อไหมกับเมาส์เดิมๆ", "on_screen": ""},
        {"start": 2.5, "end": 6.0, "text": "ตัวนี้มุม 57 องศา สบายมือสุดๆ", "on_screen": "57°"},
        {"start": 6.0, "end": 8.0, "text": "กดสั่งได้ในตะกร้าเลย", "on_screen": ""},
    ]
    shots = build_shot_list(cues, "Logitech Lift", category="IT mouse")
    assert len(shots) == 3
    assert shots[0]["role"] == "hook"
    assert shots[1]["role"] == "feature"
    assert shots[2]["role"] == "cta"
    assert shots[2]["is_separate_clip"] is True
    assert shots[0]["is_separate_clip"] is False


def test_shot_lists_store_crud_and_stale():
    test_record = {
        "id": "prod_123:angle_abc",
        "product_id": "prod_123",
        "angle_id": "angle_abc",
        "product_name": "Test Product",
        "shot_list": [],
        "custom_script": "Line 1\nLine 2",
        "total_duration": 5.0,
    }

    with patch.object(ShotListsStore, "get") as mock_get:
        mock_get.return_value = test_record

        # Not stale when script matches
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1\nLine 2") is False

        # Stale when script differs
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1\nLine 2 changed") is True
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1") is True

        # When no record exists, is_stale returns False
        mock_get.return_value = None
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1") is False

    # Test delete via mutate mock
    with patch("scripts.shot_lists_store._TABLE.mutate") as mock_mutate:
        fake_records = [
            {"id": "prod_123:angle_abc", "product_id": "prod_123", "angle_id": "angle_abc"},
            {"id": "prod_456:angle_def", "product_id": "prod_456", "angle_id": "angle_def"},
        ]
        class MockMutateContext:
            def __enter__(self):
                return fake_records
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_mutate.return_value = MockMutateContext()
        deleted = ShotListsStore.delete("prod_123", "angle_abc")
        assert deleted is True
        assert len(fake_records) == 1
        assert fake_records[0]["id"] == "prod_456:angle_def"


def test_semantic_camera_direction_for_lift():
    prod = "Logitech Lift"
    # Beat 1: Hook
    d1 = camera_direction_for_beat("hook", 0, "จ่ายแค่วันละไม่ถึง 3 บาท แต่ได้สุขภาพข้อมือ", "", prod)
    assert "45°" in d1 or "โต๊ะทำงาน" in d1

    # Beat 2: Ergonomic posture / angle
    d2 = camera_direction_for_beat("feature", 1, "ลงทุนครั้งเดียวกับ โลจิเทค Lift เมาส์สุขภาพมาตรฐานโลก", "", prod)
    assert "57°" in d2 or "ฝ่ามือ" in d2 or "ข้อมือ" in d2 or "ดีไซน์" in d2

    # Beat 3: Value / Cost
    d3 = camera_direction_for_beat("feature", 2, "เฉลี่ยแล้วตกวันละ สตางค์เท่านั้น ถูกกว่าซื้อ ยาแก้ปวดแก้เมื่อย", "", prod)
    assert "คุ้มค่า" in d3 or "360°" in d3 or "ยก" in d3 or "ข้อมือ" in d3

    # Beat 4: Clicking / SmartWheel / Silence
    d4 = camera_direction_for_beat("feature", 3, "แถมทำงานลื่นไหล ปุ่มกดนุ่มเงียบกริบ ถนอมมือของคุณ", "", prod)
    assert "คลิก" in d4 or "SmartWheel" in d4 or "เงียบกริบ" in d4

    # Beat 5: CTA
    d5 = camera_direction_for_beat("cta", 4, "กดสั่งซื้อในตะกร้าด้านล่างได้เลย", "", prod)
    assert "ตะกร้า" in d5


def test_shot_list_builder_gemini_defaults(tmp_path):
    from scripts.shot_list_builder import generate_shot_list_for_angle
    from scripts.shot_lists_store import ShotListsStore
    from scripts.pipeline_context import PipelineContext

    fake_product = {
        "id": "prod_gemini_1",
        "name": "Super Mic",
        "angles": [
            {
                "angle_id": "ang_1",
                "angle_name": "รีวิวความชัด",
                "script_lines": ["เสียงใส คมชัด ไม่ต้องจ่อปาก", "สั่งเลยวันนี้"],
            }
        ],
    }

    cues = [
        {"start": 0.0, "end": 2.0, "text": "เสียงใส คมชัด ไม่ต้องจ่อปาก"},
        {"start": 2.0, "end": 3.5, "text": "สั่งเลยวันนี้"},
    ]

    captured_ctx = []

    def mock_voice_run(ctx: PipelineContext):
        captured_ctx.append(ctx)
        audio_file = ctx.project_dir / "voiceover.wav"
        audio_file.write_bytes(b"RIFFdummywav")
        ctx.voice_audio_path = audio_file
        ctx.cues = cues
        ctx.beat_cues = cues
        ctx.total_duration = 3.5

    with patch("scripts.product_store.ProductStore.get", return_value=fake_product), \
         patch("scripts.product_store.ProductStore.update_angle_voice") as mock_update_voice, \
         patch("scripts.stages.script_stage.ScriptStage.run"), \
         patch("scripts.stages.voice_stage.VoiceStage.run", side_effect=mock_voice_run), \
         patch.object(ShotListsStore, "upsert") as mock_upsert:

        res = generate_shot_list_for_angle("prod_gemini_1", "ang_1")
        assert res["total_duration"] == 3.5
        assert len(captured_ctx) == 1
        ctx = captured_ctx[0]

        # Must default to Gemini Flash TTS and Kore
        assert ctx.voice_engine_type == "gemini_tts"
        assert ctx.voice_preset == "gemini_kore_female_bright"
        assert ctx.voice_rate == "+15%"
        assert ctx.ad_tone == "commercial_premium"

        # Check that cues and beat_cues were stored
        mock_upsert.assert_called_once()
        record = mock_upsert.call_args[0][0]
        assert record["cues"] == cues
        assert record["beat_cues"] == cues
        assert record["voice_params"]["voice_engine_type"] == "gemini_tts"

        # Check angle voice persistence
        mock_update_voice.assert_called_once_with(
            "prod_gemini_1",
            "ang_1",
            voice_preset="gemini_kore_female_bright",
            voice_engine_type="gemini_tts",
            ad_tone="commercial_premium",
        )


def test_voice_stage_reuses_shot_list_audio(tmp_path):
    from scripts.stages.voice_stage import VoiceStage
    from scripts.pipeline_context import PipelineContext
    from scripts.shot_lists_store import ShotListsStore

    # Prepare dummy shot list audio file
    shot_list_audio = tmp_path / "shot_list_voice.wav"
    shot_list_audio.write_bytes(b"RIFFwavdata12345678")

    cues = [
        {"start": 0.0, "end": 2.5, "text": "บทที่หนึ่ง"},
        {"start": 2.5, "end": 5.0, "text": "บทที่สอง"},
    ]

    record = {
        "id": "p_reuse:a_reuse",
        "product_id": "p_reuse",
        "angle_id": "a_reuse",
        "voice_audio_path": str(shot_list_audio),
        "cues": cues,
        "beat_cues": cues,
        "total_duration": 5.0,
        "voice_params": {"voice_engine_type": "gemini_tts"},
    }

    project_dir = tmp_path / "studio_project_dir"
    project_dir.mkdir()

    ctx = PipelineContext(
        product_name="Product",
        raw_video_path="",
        project_name="20260912_studio_render",
        product_id="p_reuse",
        angle_id="a_reuse",
        voice_engine_type="gemini_tts",
    )
    ctx.project_dir = project_dir
    ctx.script_data = {"lines": [{"text": "บทที่หนึ่ง"}, {"text": "บทที่สอง"}]}

    with patch.object(ShotListsStore, "get", return_value=record), \
         patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech") as mock_gemini_tts, \
         patch("scripts.voice_engine.VoiceEngine.generate_voiceover") as mock_edge_tts:

        VoiceStage.run(ctx)

        # Zero TTS API calls made!
        mock_gemini_tts.assert_not_called()
        mock_edge_tts.assert_not_called()

        # Audio file was copied to project_dir
        assert ctx.voice_audio_path.exists()
        assert ctx.voice_audio_path.name == "voiceover.wav"
        assert ctx.voice_audio_path.read_bytes() == b"RIFFwavdata12345678"

        # Cues and duration reused perfectly
        assert ctx.cues == cues
        assert ctx.beat_cues == cues
        assert ctx.total_duration == 5.0
        assert ctx.voice_engine_used == "gemini_tts"


def test_voice_stage_resynthesizes_when_voice_preset_changes(tmp_path):
    from scripts.stages.voice_stage import VoiceStage
    from scripts.pipeline_context import PipelineContext
    from scripts.shot_lists_store import ShotListsStore

    shot_list_audio = tmp_path / "shot_list_voice.wav"
    shot_list_audio.write_bytes(b"RIFFpuckaudio")

    # Shot list was generated with Puck
    record = {
        "id": "p_change:a_change",
        "product_id": "p_change",
        "angle_id": "a_change",
        "voice_audio_path": str(shot_list_audio),
        "cues": [{"start": 0.0, "end": 2.0, "text": "ทดสอบ"}],
        "beat_cues": [{"start": 0.0, "end": 2.0, "text": "ทดสอบ"}],
        "total_duration": 2.0,
        "voice_params": {"voice_preset": "gemini_puck_male_hype", "voice_engine_type": "gemini_tts"},
    }

    project_dir = tmp_path / "studio_change_dir"
    project_dir.mkdir()

    # User in Studio selected Charon instead of Puck!
    ctx = PipelineContext(
        product_name="Product",
        raw_video_path="",
        project_name="20260912_studio_change_voice",
        product_id="p_change",
        angle_id="a_change",
        voice_preset="gemini_charon_male_pro",
        voice_engine_type="gemini_tts",
    )
    ctx.project_dir = project_dir
    ctx.script_data = {"lines": [{"text": "ทดสอบ"}]}

    def mock_gemini_generate(text, output_path, **kwargs):
        Path(output_path).write_bytes(b"RIFFcharonaudio")

    with patch.object(ShotListsStore, "get", return_value=record), \
         patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.resolve_voice", return_value="Charon"), \
         patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech", side_effect=mock_gemini_generate) as mock_gen, \
         patch("scripts.stages.voice_stage._probe_audio_duration", return_value=2.0), \
         patch("scripts.stages.voice_stage._rms_aligned_cues", return_value=[{"start": 0.0, "end": 2.0, "text": "ทดสอบ"}]):

        VoiceStage.run(ctx)

        # Because voice_preset changed, it MUST synthesize the new voice!
        mock_gen.assert_called_once()
        assert ctx.voice_audio_path.read_bytes() == b"RIFFcharonaudio"


