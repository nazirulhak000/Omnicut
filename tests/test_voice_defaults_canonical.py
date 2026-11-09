"""One canonical voice/tone default, one BGM level (decisions D4, D5; audit
S2-07, S2-08, S2-20). Source/default inspection only -- no TTS call.
"""

import inspect
from pathlib import Path

from scripts import config
from scripts.api_schemas import RenderRequest, VoicePreviewRequest
from scripts.gemini_tts_engine import GEMINI_VOICE_PRESETS, AD_TONE_PRESETS, GeminiFlashTTSEngine
from scripts.pipeline_context import PipelineContext

ROOT = Path(__file__).resolve().parent.parent


def test_canonical_constants_are_agents_md_standard():
    assert config.DEFAULT_VOICE_PRESET == "gemini_fenrir_male_strong"
    assert config.DEFAULT_AD_TONE == "commercial_premium"
    assert GEMINI_VOICE_PRESETS[config.DEFAULT_VOICE_PRESET]["voice"] == "Fenrir"
    assert config.DEFAULT_AD_TONE in AD_TONE_PRESETS
    assert config.VOICES[config.DEFAULT_VOICE] == "th-TH-NiwatNeural"  # male Edge fallback


def test_backend_defaults_all_read_the_constants():
    ctx = PipelineContext(product_name="p", raw_video_path="x.mp4")
    assert ctx.voice_preset == config.DEFAULT_VOICE_PRESET
    assert ctx.ad_tone == config.DEFAULT_AD_TONE
    assert RenderRequest.model_fields["voice_preset"].default == config.DEFAULT_VOICE_PRESET
    assert RenderRequest.model_fields["ad_tone"].default == config.DEFAULT_AD_TONE
    assert VoicePreviewRequest.model_fields["ad_tone"].default == config.DEFAULT_AD_TONE
    sig = inspect.signature(GeminiFlashTTSEngine.generate_speech)
    assert sig.parameters["voice_preset"].default == config.DEFAULT_VOICE_PRESET
    assert sig.parameters["ad_tone"].default == config.DEFAULT_AD_TONE


def test_owned_call_sites_have_no_hype_literal_fallback():
    for rel in ("scripts/api_render.py", "scripts/api_voice.py", "scripts/stages/voice_stage.py",
                "scripts/pipeline_context.py", "scripts/api_schemas.py", "scripts/shot_list_builder.py",
                "scripts/api_shot_lists.py", "scripts/pipeline.py", "scripts/product_scraper.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert 'or "commercial_hype"' not in src, rel
        assert '= "commercial_hype"' not in src, rel
        assert '"ad_tone": "commercial_hype"' not in src, rel


def test_unknown_preset_falls_back_to_fenrir_not_kore():
    assert GeminiFlashTTSEngine.resolve_voice(preset="not_a_preset") == "Fenrir"
    src = inspect.getsource(GeminiFlashTTSEngine.generate_speech)
    assert 'target_voice = "Kore"' not in src


def test_mobile_quick_studio_uses_the_config_bgm_level():
    src = (ROOT / "scripts" / "mobile_quick_studio.py").read_text(encoding="utf-8")
    assert '"bgm_volume": BGM_VOLUME if bgm_enabled else 0.0' in src
    assert "0.14" not in src
    assert config.BGM_VOLUME == 0.12


def test_self_tests_never_write_into_the_asset_library():
    for rel in ("scripts/voice_engine.py", "scripts/gemini_tts_engine.py"):
        main_block = (ROOT / rel).read_text(encoding="utf-8").split('if __name__ == "__main__":', 1)[1]
        assert "02_Assets" not in main_block, rel
        assert ".tmp" in main_block, rel
