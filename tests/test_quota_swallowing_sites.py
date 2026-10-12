"""
Regression tests for the follow-up to the quota gate (scripts/quota.py,
check_budget()): three call sites wrapped their paid AI/TTS/vision call in a
broad `except Exception` that gracefully degrades on ANY failure, including a
quota hit. That fallback is correct and desirable for a genuine provider
failure (network down, API error, model unavailable) -- but a quota error
means the user's own daily spending cap stopped the call, and silently
degrading hides that reason from the user. Fixed sites:

- scripts/api_phase1.py  ai_prompt()      -- POST /api/ai/prompt
- scripts/api_voice.py   preview_voice()  -- POST /api/voice/preview
- scripts/stages/shot_matching_stage.py   -- AI Vision scene matching
- scripts/stages/script_stage.py          -- AIBridge script generation
- scripts/stages/voice_stage.py           -- Gemini Flash TTS synthesis

scripts/quota.py gained a small predicate, is_quota_error(exc), so each site
can distinguish "AppError(AI_QUOTA_EXCEEDED)" from every other exception
shape without re-deriving the code string everywhere.

Each site gets two tests: a quota AppError must surface as a real,
user-visible error (HTTPException 429 for the two API endpoints; a loud
ctx.notify() warning distinct from the generic one for the three pipeline
stages, since those degrade-with-a-loud-warning rather than fail the whole
render -- see the code comments at each site for why), AND a genuine
provider failure (plain RuntimeError, standing in for network/SDK/model
errors) must still degrade gracefully exactly as before.

Isolated / offline per .agents/rules/testing_standard.md: no real network or
AI calls are made anywhere in this file.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.error_handler import AppError, ErrorCategory
from scripts.quota import is_quota_error


def _quota_app_error() -> AppError:
    return AppError(
        category=ErrorCategory.AI_PROVIDER,
        code="AI_QUOTA_EXCEEDED",
        message_th="เกินโควต้าการใช้งาน AI ที่ตั้งไว้ต่อวันแล้ว",
        suggestion_th="โควต้า token ต่อวันเต็มแล้ว รอถึงวันถัดไปหรือปรับค่าใน .env",
    )


# ----------------------------------------------------------------------
# is_quota_error() predicate itself
# ----------------------------------------------------------------------
def test_is_quota_error_true_only_for_the_quota_appError():
    assert is_quota_error(_quota_app_error()) is True


def test_is_quota_error_false_for_other_appError_categories():
    other = AppError(
        category=ErrorCategory.AI_PROVIDER,
        code="TTS_NETWORK_ERROR",
        message_th="x",
        suggestion_th="y",
    )
    assert is_quota_error(other) is False


def test_is_quota_error_false_for_a_plain_exception():
    assert is_quota_error(RuntimeError("network down")) is False


# ----------------------------------------------------------------------
# Site 1: scripts/api_phase1.py -- POST /api/ai/prompt
# ----------------------------------------------------------------------
@pytest.fixture
def client():
    from scripts.api_server import app
    return TestClient(app)


_SCRIPT_CTX = {
    "product_name": "หูฟังบลูทูธ",
    "angle_title": "เทียบราคา",
    "hook": "199 กับ 899 ต่างกันยังไง",
    "specs": [{"label": "จุดเด่น", "value": "เบสหนัก"}],
    "price_deal": "ลด 50%",
}


def test_ai_prompt_quota_error_surfaces_as_http_429(client):
    """A quota hit must be a real, visible HTTP error -- not a silent
    'mode: manual' response indistinguishable from a genuine SDK failure."""
    with patch("scripts.api_phase1.AIBridge.generate", side_effect=_quota_app_error()):
        resp = client.post("/api/ai/prompt", json={"task": "script", "context": _SCRIPT_CTX})

    assert resp.status_code == 429, resp.text
    assert "โควต้า" in resp.json()["detail"]


def test_ai_prompt_genuine_provider_failure_still_degrades_to_manual_mode(client):
    """A real SDK/network failure must keep behaving exactly as before:
    200 OK with mode=manual and the prompt for the user to paste."""
    with patch("scripts.api_phase1.AIBridge.generate", side_effect=RuntimeError("network down")):
        resp = client.post("/api/ai/prompt", json={"task": "script", "context": _SCRIPT_CTX})

    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "manual"
    assert "prompt" in body and body["prompt"]
    assert "network down" in body["warning"]


# ----------------------------------------------------------------------
# Site 2: scripts/api_voice.py -- POST /api/voice/preview
# ----------------------------------------------------------------------
def test_voice_preview_quota_error_surfaces_as_http_429(client, isolated_storage, monkeypatch):
    from scripts import api_voice
    monkeypatch.setattr(api_voice, "BASE_DIR", isolated_storage)

    with patch("scripts.api_voice.GeminiFlashTTSEngine.generate_speech", side_effect=_quota_app_error()):
        resp = client.post("/api/voice/preview", json={"voice_gender": "gemini_puck_male_hype"})

    assert resp.status_code == 429, resp.text
    assert "โควต้า" in resp.json()["detail"]


def test_voice_preview_provider_failure_halts_without_fallback(client, isolated_storage, monkeypatch):
    """When Gemini TTS fails in preview, it must NOT degrade to Edge-TTS.
    It returns an error response indicating the failure."""
    from scripts import api_voice
    monkeypatch.setattr(api_voice, "BASE_DIR", isolated_storage)

    with patch("scripts.api_voice.GeminiFlashTTSEngine.generate_speech", side_effect=RuntimeError("network down")), \
         patch("scripts.api_voice.VoiceEngine.generate_crystal_voice") as mock_edge:
        resp = client.post("/api/voice/preview", json={"voice_gender": "gemini_puck_male_hype"})

    assert resp.status_code in (429, 500), resp.text
    mock_edge.assert_not_called()


# ----------------------------------------------------------------------
# Site 3: scripts/stages/shot_matching_stage.py -- AI Vision scene matching
# ----------------------------------------------------------------------
def _vision_matching_ctx(monkeypatch, tmp_path):
    """Minimal PipelineContext that reaches the AI Vision matching branch:
    use_ai_vision=True, a GEMINI_API_KEY set, no manual clip_list, and a
    cache miss (get_cached_matches returns falsy) so match_script_to_video
    is actually invoked."""
    from scripts.pipeline_context import PipelineContext
    from scripts import gemini_vision_matcher as gvm

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, path, cues: None))

    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"not a real video")

    ctx = PipelineContext(
        product_name="Gadget",
        raw_video_path=str(raw_video),
        project_name="test_quota_shot_matching",
    )
    ctx.raw_video = raw_video
    ctx.use_ai_vision = True
    ctx.clip_list = None
    ctx.is_image_source = False
    ctx.image_files = None
    ctx.project_dir = None
    ctx.total_duration = 6.0
    ctx.cues = [{"start": 0.0, "end": 3.0, "text": "หนึ่ง"}, {"start": 3.0, "end": 6.0, "text": "สอง"}]
    ctx.micro_cues = ctx.cues
    ctx.angle_meta = None
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    return ctx


def test_shot_matching_quota_error_notifies_loudly_and_still_degrades(monkeypatch, tmp_path):
    """AI Vision matching is a quality enhancement, not a hard dependency --
    the code already tolerates ai_matched_shots staying None and falls back
    to rhythmic cuts. A quota hit must NOT fail the whole render (that would
    be disproportionate for a non-essential feature), but it must notify the
    user loudly and distinctly from a generic provider-failure message, so
    they know it was their own budget cap."""
    from scripts.stages.shot_matching_stage import ShotMatchingStage
    from scripts import gemini_vision_matcher as gvm

    ctx = _vision_matching_ctx(monkeypatch, tmp_path)
    notifications = []
    ctx.progress_callback = lambda msg, progress: notifications.append(msg)

    with patch.object(gvm.GeminiVisionMatcher, "match_script_to_video", side_effect=_quota_app_error()), \
         patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 6.0}):
        ShotMatchingStage.run(ctx)

    assert ctx.ai_matched_shots is None, "must still degrade to rhythmic cuts, not raise"
    assert ctx.actual_clip_list, "the render must still get a usable clip list"
    quota_msgs = [m for m in notifications if "โควต้า" in m]
    assert quota_msgs, f"expected a loud quota-specific notification, got: {notifications}"


def test_shot_matching_genuine_provider_failure_still_degrades_quietly(monkeypatch, tmp_path):
    """A real Gemini Vision failure (network/SDK/model) must keep degrading
    to rhythmic cuts exactly as before, without the quota-specific wording."""
    from scripts.stages.shot_matching_stage import ShotMatchingStage
    from scripts import gemini_vision_matcher as gvm

    ctx = _vision_matching_ctx(monkeypatch, tmp_path)
    notifications = []
    ctx.progress_callback = lambda msg, progress: notifications.append(msg)

    with patch.object(gvm.GeminiVisionMatcher, "match_script_to_video", side_effect=RuntimeError("network down")), \
         patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 6.0}):
        ShotMatchingStage.run(ctx)

    assert ctx.ai_matched_shots is None
    assert ctx.actual_clip_list, "the render must still get a usable clip list"
    assert not any("โควต้า" in m for m in notifications), "a generic failure must not claim it was a quota hit"


# ----------------------------------------------------------------------
# Site 4 (found via grep, same shape): scripts/stages/script_stage.py
# ----------------------------------------------------------------------
def test_script_stage_quota_error_notifies_loudly_and_still_degrades(monkeypatch):
    from scripts.stages.script_stage import ScriptStage
    from scripts.pipeline_context import PipelineContext
    from scripts.ai_bridge import AIBridge

    ctx = PipelineContext(product_name="Gadget", raw_video_path="dummy.mp4", project_name="p")
    ctx.custom_script = None
    ctx.script_overlays = None
    ctx.angle_meta = None
    ctx.key_features = "เบสหนัก"
    ctx.price_deal = "ลด 50%"
    notifications = []
    ctx.progress_callback = lambda msg, progress: notifications.append(msg)

    with patch.object(AIBridge, "is_available", classmethod(lambda cls: True)), \
         patch.object(AIBridge, "generate", side_effect=_quota_app_error()):
        ScriptStage.run(ctx)

    assert ctx.script_data is not None, "must still degrade to ScriptGenerator, not raise"
    assert ctx.script_data["lines"], "a real fallback script must be produced"
    assert any("โควต้า" in m for m in notifications), f"expected a loud quota notification, got: {notifications}"


def test_script_stage_genuine_provider_failure_still_degrades_quietly(monkeypatch):
    from scripts.stages.script_stage import ScriptStage
    from scripts.pipeline_context import PipelineContext
    from scripts.ai_bridge import AIBridge

    ctx = PipelineContext(product_name="Gadget", raw_video_path="dummy.mp4", project_name="p")
    ctx.custom_script = None
    ctx.script_overlays = None
    ctx.angle_meta = None
    ctx.key_features = "เบสหนัก"
    ctx.price_deal = "ลด 50%"
    notifications = []
    ctx.progress_callback = lambda msg, progress: notifications.append(msg)

    with patch.object(AIBridge, "is_available", classmethod(lambda cls: True)), \
         patch.object(AIBridge, "generate", side_effect=RuntimeError("network down")):
        ScriptStage.run(ctx)

    assert ctx.script_data is not None
    assert ctx.script_data["lines"]
    assert not any("โควต้า" in m for m in notifications)


# ----------------------------------------------------------------------
# Site 5 (found via grep, same shape): scripts/stages/voice_stage.py
# ----------------------------------------------------------------------
def _voice_stage_ctx(tmp_path):
    from scripts.pipeline_context import PipelineContext

    ctx = PipelineContext(product_name="Gadget", raw_video_path="dummy.mp4", project_name="p")
    ctx.voice_engine_type = "gemini_tts"
    ctx.voice_preset = "gemini_puck_male_hype"
    ctx.voice = "male"
    ctx.voice_rate = None
    ctx.ad_tone = "commercial_premium"
    ctx.is_reroll = False
    ctx.human_voice_audio_path = None
    ctx.project_dir = tmp_path
    ctx.script_data = {"hook": "หนึ่ง", "lines": [{"text": "หนึ่ง", "sfx": None}], "full_text": "หนึ่ง"}
    return ctx


def test_voice_stage_quota_error_notifies_loudly_and_halts_without_fallback(tmp_path, monkeypatch):
    from scripts.stages.voice_stage import VoiceStage
    from scripts.voice_engine import VoiceEngine
    from scripts.error_handler import AppError

    ctx = _voice_stage_ctx(tmp_path)
    notifications = []
    ctx.progress_callback = lambda msg, progress: notifications.append(msg)

    with patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.resolve_voice", return_value="Puck"), \
         patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech", side_effect=_quota_app_error()), \
         patch.object(VoiceEngine, "generate_voiceover") as mock_edge:
        with pytest.raises(AppError):
            VoiceStage.run(ctx)

    mock_edge.assert_not_called()
    assert any("โควต้า" in m for m in notifications), f"expected a loud quota notification, got: {notifications}"


def test_voice_stage_genuine_provider_failure_halts_without_fallback(tmp_path, monkeypatch):
    from scripts.stages.voice_stage import VoiceStage
    from scripts.voice_engine import VoiceEngine

    ctx = _voice_stage_ctx(tmp_path)
    notifications = []
    ctx.progress_callback = lambda msg, progress: notifications.append(msg)

    with patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.resolve_voice", return_value="Puck"), \
         patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech", side_effect=RuntimeError("network down")), \
         patch.object(VoiceEngine, "generate_voiceover") as mock_edge, \
         patch("scripts.stages.voice_stage.time.sleep", return_value=None):
        with pytest.raises(Exception):
            VoiceStage.run(ctx)

    mock_edge.assert_not_called()
