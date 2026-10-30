"""
API Router for Voice, Script generation, and Speech Recognition (sub-srt).
"""

import os
import sys
import json
import time
import uuid
from urllib.parse import quote
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends

from scripts.channel_scope import ChannelScope, require_active_for_new_work, get_optional_channel_scope, get_channel_scope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import get_workflow_scope, require_media_owner
from scripts.channel_artifacts import register as register_artifact
from scripts.config import (
    BASE_DIR, ASSETS_DIR, VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.script_generator import ScriptGenerator
from scripts.voice_engine import VoiceEngine
from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.quota import is_quota_error
from scripts.tts_sanitizer import TTSSanitizer
from scripts.api_schemas import (
    ScriptGenerateRequest, VoicePreviewRequest, TranscribeRequest
)
from scripts.media_service import measure_wav_duration

PROJECT_ROOT = Path(__file__).resolve().parent.parent

router = APIRouter(tags=["Voice & Script"])


def _is_contained(path: Path, root: Path) -> bool:
    """
    True if `path` is `root` or lives underneath it. Uses `Path.relative_to`
    rather than a `str.startswith()` prefix check -- a prefix check treats
    `D:\\...\\Capcut_evil\\` as "under" `D:\\...\\Capcut` because the string
    happens to start with the same characters, which is not real path
    containment. Both `path` and `root` are expected to already be resolved.
    """
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


VOICE_CACHE_DIR = PROJECT_ROOT / "frontend" / "public" / "voice_cache"
VOICE_CACHE_MANIFEST = VOICE_CACHE_DIR / "manifest.json"

_VOICE_PRESETS_META = {
    "gemini_puck_male_hype":     {"voice": "Puck",   "label": "Puck — ชายพลังสูง TikTok",       "gender": "male"},
    "gemini_charon_male_pro":    {"voice": "Charon", "label": "Charon — ชายทุ้มลึก น่าเชื่อถือ","gender": "male"},
    "gemini_kore_female_bright": {"voice": "Kore",   "label": "Kore — หญิงสดใส ป้ายยาเก่ง",     "gender": "female"},
    "gemini_aoede_female_pro":   {"voice": "Aoede",  "label": "Aoede — หญิงพรีเมียม นุ่มนวล",   "gender": "female"},
    "gemini_fenrir_male_strong": {"voice": "Fenrir", "label": "Fenrir — ชายสตรอง คมเข้ม",        "gender": "male"},
}
_AD_TONES_META = {
    "commercial_premium":   "โฆษณาพรีเมียม",
    "commercial_hype":      "ป้ายยาไวรัล",
    "commercial_aesthetic": "มินิมอล ดูแพง",
    "commercial_expert":    "ผู้เชี่ยวชาญ",
}


@router.get("/api/voice/presets")
def get_voice_presets():
    """Returns the voice cache manifest or skeleton."""
    if VOICE_CACHE_MANIFEST.exists():
        try:
            return json.loads(VOICE_CACHE_MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass

    combos = []
    for voice_id, voice_cfg in _VOICE_PRESETS_META.items():
        for tone_id, tone_label in _AD_TONES_META.items():
            fname = f"{voice_id}__{tone_id}.wav"
            combos.append({
                "voice_id": voice_id,
                "tone_id": tone_id,
                "voice_label": voice_cfg["label"],
                "tone_label": tone_label,
                "voice_gender": voice_cfg["gender"],
                "filename": fname,
                "url": f"/voice_cache/{fname}",
                "ready": (VOICE_CACHE_DIR / fname).exists(),
            })
    return {
        "generated_at": None,
        "total": len(combos),
        "ready": sum(1 for c in combos if c["ready"]),
        "combos": combos,
    }


@router.get("/api/voice/cache-status")
def get_voice_cache_status():
    """Quick per-file readiness check."""
    result = {}
    for voice_id in _VOICE_PRESETS_META:
        for tone_id in _AD_TONES_META:
            fname = f"{voice_id}__{tone_id}.wav"
            result[fname] = (VOICE_CACHE_DIR / fname).exists()
    ready = sum(1 for v in result.values() if v)
    return {"ready": ready, "total": len(result), "files": result}


@router.post("/api/voice/generate-cache")
async def trigger_voice_cache_generation(background_tasks: BackgroundTasks, force: bool = False):
    """Kicks off cache generation in the background."""
    if not GeminiFlashTTSEngine.is_available():
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not set — cannot generate voice cache.")

    def _generate():
        import subprocess as sp
        cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_voice_cache.py")]
        if force:
            cmd.append("--force")
        sp.run(cmd, capture_output=False)

    background_tasks.add_task(_generate)
    return {"status": "started", "message": "Voice cache generation started in background."}


@router.post("/api/voice/preview")
def preview_voice(req: VoicePreviewRequest, request: Request = None):
    """Generates a quick voice sample for auditioning (Edge-TTS or Gemini Flash)."""
    scope = (get_optional_channel_scope(request) or get_channel_scope(request)) if request is not None else None
    if scope is not None:
        require_active_for_new_work(scope)
    sample_file = BASE_DIR / "test_voice.wav"
    owner = scope.channel_id if scope is not None else ("main" if request is not None else None)
    if owner is not None:
        sample_file = BASE_DIR / "03_Projects" / owner / "_VoicePreviews" / (uuid.uuid4().hex + ".wav")
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        register_artifact(sample_file, owner)
    def sample_url():
        if owner is not None:
            register_artifact(sample_file, owner)
        return "/api/media/" + quote(sample_file.relative_to(BASE_DIR).as_posix(), safe="/") + ("?channel=" + owner if owner is not None else "")
    text = req.text or "สวัสดีครับ นี่คือเสียงตัวอย่างสำหรับคลิปรีวิวสินค้า"
    voice_gender = req.voice_gender or "male"
    speed = req.speed or 1.15
    ad_tone = req.ad_tone or "commercial_hype"

    if voice_gender and "gemini" in voice_gender:
        gemini_voice = GeminiFlashTTSEngine.resolve_voice(preset=voice_gender)
        try:
            GeminiFlashTTSEngine.generate_speech(
                text=text,
                output_path=str(sample_file),
                voice_name=gemini_voice,
                ad_tone=ad_tone,
                speed=speed,
            )
            return {
                "audio_url": sample_url(),
                "duration": measure_wav_duration(sample_file),
                "voice_name": gemini_voice
            }
        except (HTTPException, ChannelError):
            raise
        except Exception as g_err:
            if is_quota_error(g_err):
                raise HTTPException(status_code=429, detail=g_err.suggestion_th)
            detail_msg = getattr(g_err, "suggestion_th", None)
            if hasattr(g_err, "message_th"):
                detail_msg = f"{g_err.message_th} — {g_err.suggestion_th}" if getattr(g_err, "suggestion_th", None) else g_err.message_th
            detail_msg = detail_msg or str(g_err)
            status_code = 429 if ("429" in str(g_err) or "rate" in str(g_err).lower() or "quota" in str(g_err).lower()) else 500
            print(f"❌ [preview_voice] Gemini TTS failed ({g_err}) — halting, NO fallback to Edge-TTS.")
            raise HTTPException(status_code=status_code, detail=detail_msg)

    res = VoiceEngine.generate_crystal_voice(
        text_or_lines=text,
        output_audio_path=str(sample_file),
        speed=speed,
        voice_gender=voice_gender
    )
    if not res:
        raise HTTPException(status_code=500, detail="Voice generation failed")

    return {
        "audio_url": sample_url(),
        "duration": measure_wav_duration(sample_file),
        "voice_name": voice_gender
    }


@router.post("/api/script/generate")
def generate_script(req: ScriptGenerateRequest):
    """Generates structured high-converting TikTok product review script."""
    data = ScriptGenerator.generate(
        product_name=req.product_name,
        key_features=req.key_features,
        pain_point=req.pain_point,
        price_deal=req.price_deal,
        template_key=req.template_key
    )
    return data


@router.post("/api/script/ai-generate")
def generate_ai_scripts(req: ScriptGenerateRequest):
    """Generates 4 viral multi-angle TikTok review scripts using Google Gemini."""
    from scripts.config import get_gemini_api_keys
    api_keys = get_gemini_api_keys()
    if not api_keys:
        base = ScriptGenerator.generate(req.product_name, req.key_features, req.pain_point, req.price_deal)
        return {
            "angles": [
                {
                    "angle_id": "problem_solution",
                    "angle_name": "🚫 เปิดด้วยปัญหา / จี้จุดเจ็บ",
                    "badge_color": "red",
                    "hook_title": f"อย่าเพิ่งซื้อ {req.product_name} ถ้ายังไม่เห็นสิ่งนี้!",
                    "estimated_sec": 26,
                    "script_text": base["full_text"],
                    "caption": f"ใครเจอปัญหา {req.pain_point} ดูด่วน! {req.product_name}",
                    "hashtags": ["#ของดีบอกต่อ", "#รีวิวของใช้", "#tiktokshop", f"#{req.product_name.replace(' ', '')}"],
                    "retention_probability": 0.84,
                    "rating_score": 0.82,
                    "detected_tone": "urgency",
                }
            ]
        }

    # Pre-flight budget check. This endpoint calls Gemini directly rather than
    # through ai_bridge, so it needs its own gate -- without it the daily cap
    # cannot apply here at all, and the except below would report a cap as a
    # generic fallback anyway. Answer 429 as /api/voice/preview does; there is
    # no global AppError handler, so an uncaught one would surface as a 500.
    from scripts.quota import check_budget
    try:
        check_budget(task="ai_script")
    except Exception as q_err:
        if is_quota_error(q_err):
            raise HTTPException(status_code=429, detail=q_err.suggestion_th)
        raise

    try:
        from google import genai

        prompt = f"""คุณเป็นสุดยอด Copywriter และผู้เชี่ยวชาญการทำคลิป TikTok Shop / Affiliate มือโปร
กรุณาแต่งสคริปต์วิดีโอรีวิวป้ายยา 4 มุมมอง (4 Angles) สำหรับสินค้า:
- ชื่อสินค้า: {req.product_name}
- จุดเด่น: {req.key_features}
- ปัญหาที่แก้: {req.pain_point}

กฎเหล็กการเขียนบทพูด:
- ชื่อแบรนด์, ชื่อรุ่นสินค้า, และคำศัพท์เฉพาะทางที่เป็นภาษาอังกฤษ (เช่น Logitech, Wave Keys, Logi Bolt, Bluetooth, USB-C, Type-C, iPad ฯลฯ) ให้คงไว้เป็นภาษาอังกฤษตามชื่อทางการเสมอ ห้ามทับศัพท์เป็นคำไทยเพี้ยนๆ (เช่น ห้ามเขียน "โลจิเทค", "โลจิ โบลต์")
- ห้ามใช้จุดไข่ปลา "..." หรือ "…" ในทุกฟิลด์โดยเด็ดขาด (ทั้งใน script_text, hook_title, caption) ให้เว้นวรรคธรรมดาแทน
- ห้ามใช้ภาษาโฆษณาทีวีทางการ ให้ใช้ภาษาพูดเพื่อนสนิทป้ายยา
- ห้ามใส่ emoji ในบทพูด (script_text) ใส่ได้เฉพาะ angle_name และ hook_title
- ห้ามพูด/เขียนถึงราคา ตัวเลขเงิน ส่วนลด โปรโมชั่น Flash Sale คูปอง ส่งฟรี หรือการเดาราคา (เช่น "หลักร้อย" "หลักพัน") ในทุกช่อง (ผิดกฎ TikTok) ปิดท้ายด้วย CTA กลางๆ เช่น "กดตะกร้าดูรายละเอียดได้เลยครับ"

กรุณาแต่งสคริปต์ภาษาพูดคนรีวิวจริง (ไม่เอาภาษาโฆษณาแข็งๆ) 4 รูปแบบ:
1. เตือนภัย / จี้จุดเจ็บ (Stop Scroll / Pain Point)
2. โชว์ฟังก์ชันสุดล้ำ / ว้าว (Tech Feature Hype)
3. ห้ามพลาด / ของมันต้องมี (FOMO from real usage -- no price, no discount)
4. ชีวิตดีขึ้น / เปรียบเทียบ (Transformation / Social Proof)

ตอบกลับเป็น JSON Format เท่านั้น:
```json
{{
  "angles": [
    {{
      "angle_id": "pain_point",
      "angle_name": "🚫 เตือนห้ามซื้อ / จี้จุดเจ็บ",
      "badge_color": "red",
      "hook_title": "พาดหัวแบนเนอร์บนจอ 3 วิแรก สั้นมาก",
      "hook_brand": "ชื่อแบรนด์อย่างเดียว สั้นที่สุด 1 คำ ถ้าไม่มีแบรนด์ใส่ว่าง",
      "hook_model": "รุ่นหรือจุดเด่น 1-3 คำ",
      "hook_label": "หมวดสินค้า 1-2 คำ",
      "estimated_sec": 26,
      "script_text": "ประโยคที่ 1\\nประโยคที่ 2\\nประโยคที่ 3\\nประโยคที่ 4\\nประโยคที่ 5 CTA กลางๆ ชวนกดตะกร้าดูรายละเอียด",
      "caption": "แคปชั่นสั้นๆ สำหรับโพสต์",
      "hashtags": ["#ของดีบอกต่อ", "#tiktokshop"]
    }}
  ]
}}
```"""

        response = None
        for key_idx, cur_key in enumerate(api_keys, 1):
            key_tag = f"Key #{key_idx} (..{cur_key[-6:]})"
            client = genai.Client(api_key=cur_key)
            key_rate_limited = False
            for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response and response.text:
                        print(f"✨ [AI Script] Generated scripts with {model_name} on {key_tag}")
                        break
                except Exception as call_err:
                    print(f"[AI Script] Model {model_name} on {key_tag} note: {call_err}")
                    if "429" in str(call_err) or "RESOURCE_EXHAUSTED" in str(call_err):
                        key_rate_limited = True
                        print(f"   ⚠️ [AI Script] Rate limit (429) hit on {key_tag} — switching to next key...")
                        break
                    continue
            if response and response.text:
                break
            if key_rate_limited:
                continue

        if not response or not response.text:
            raise RuntimeError("No response received from Gemini across all API keys")

        res_text = response.text.strip()
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(res_text)

        # Validate sanitizer
        for ang in parsed.get("angles", []):
            if "script_text" in ang:
                ang["script_text"] = TTSSanitizer.clean(ang["script_text"])
            if "hook_title" in ang:
                ang["hook_title"] = TTSSanitizer.clean(ang["hook_title"])
            if "caption" in ang:
                ang["caption"] = TTSSanitizer.clean(ang["caption"])

        # Auto-enrich each angle with TypeSafe Jev hook retention scoring
        try:
            from scripts.typesafe_bridge import evaluate_hook_retention, is_typesafe_available

            if is_typesafe_available():
                for ang in parsed.get("angles", []):
                    hook_text = ang.get("hook_title") or (
                        ang.get("script_text", "").split("\n")[0] if ang.get("script_text") else ""
                    )
                    if hook_text:
                        eval_res = evaluate_hook_retention(hook_text)
                        if "error" not in eval_res:
                            ang["retention_probability"] = eval_res.get("high_retention_prob", 0.8)
                            ang["rating_score"] = eval_res.get("rating_score", 0.75)
                            ang["detected_tone"] = eval_res.get("tone", ang.get("angle_id", "curiosity"))

                # Sort angles by rating_score and retention_probability descending so strongest hook is first
                if parsed.get("angles"):
                    parsed["angles"].sort(
                        key=lambda a: (a.get("rating_score", 0), a.get("retention_probability", 0)),
                        reverse=True,
                    )
        except Exception as jev_err:
            print(f"⚠️ [ai_generate] TypeSafe Jev auto-scoring note: {jev_err}")

        return parsed

    except Exception as e:
        print(f"⚠️ [ai_generate] Error calling Gemini: {e}")
        base = ScriptGenerator.generate(req.product_name, req.key_features, req.pain_point, req.price_deal)
        return {
            "angles": [
                {
                    "angle_id": "problem_solution",
                    "angle_name": "🚫 เปิดด้วยปัญหา / จี้จุดเจ็บ",
                    "badge_color": "red",
                    "hook_title": f"อย่าเพิ่งซื้อ {req.product_name} ถ้ายังไม่เห็นสิ่งนี้!",
                    "estimated_sec": 26,
                    "script_text": base["full_text"],
                    "caption": f"ใครเจอปัญหา {req.pain_point} ดูด่วน! {req.product_name}",
                    "hashtags": ["#ของดีบอกต่อ", "#รีวิวของใช้", "#tiktokshop"],
                    "retention_probability": 0.84,
                    "rating_score": 0.82,
                    "detected_tone": "urgency",
                }
            ]
        }


@router.post("/api/sub-srt/transcribe")
def run_sub_srt_transcription(req: TranscribeRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    """Runs sub-srt Speech Recognition on a video or audio file."""
    if isinstance(scope, ChannelScope):
        require_active_for_new_work(scope)
    media_path = Path(req.media_path)
    if not media_path.is_absolute():
        media_path = BASE_DIR / req.media_path
    media_path = media_path.resolve()

    # req.media_path is client-controlled and was previously joined/read with
    # no containment check at all -- both an arbitrary-path read (whatever
    # media file is passed gets fed to the transcription subprocess) and an
    # arbitrary-path write (the -sub.srt/.vtt output lands in media_path's
    # own parent directory). Reject anything that resolves outside the
    # project tree before doing anything with it.
    if not _is_contained(media_path, BASE_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    if not media_path.exists():
        raise HTTPException(status_code=404, detail=f"Media file not found: {media_path}")

    if isinstance(scope, ChannelScope):
        require_media_owner(scope, media_path, base_dir=BASE_DIR)
    skill_script = PROJECT_ROOT / ".agents" / "skills" / "sub-srt" / "generate_srt.py"
    if not skill_script.exists():
        skill_script = Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "config" / "skills" / "sub-srt" / "generate_srt.py"

    out_dir = media_path.parent
    if isinstance(scope, ChannelScope):
        import hashlib
        key = hashlib.sha256(str(media_path).encode()).hexdigest()[:16]
        out_dir = BASE_DIR / "03_Projects" / scope.channel_id / "_Transcripts" / key
        out_dir.mkdir(parents=True, exist_ok=True)
        for suffix in ["srt", "vtt"]:
            register_artifact(out_dir / (media_path.stem + "-sub." + suffix), scope.channel_id)
    cmd = [
        sys.executable, str(skill_script),
        str(media_path),
        "--mode", req.mode,
        "--words-per-line", str(req.words_per_line),
        "--vtt",
        "--outdir", str(out_dir)
    ]
    if req.lang:
        cmd.extend(["--lang", req.lang])
    if req.fast:
        cmd.append("--fast")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {proc.stderr}")

        base_stem = media_path.stem
        srt_file = out_dir / f"{base_stem}-sub.srt"
        vtt_file = out_dir / f"{base_stem}-sub.vtt"

        if isinstance(scope, ChannelScope):
            for artifact in [srt_file, vtt_file]:
                if artifact.is_file():
                    register_artifact(artifact, scope.channel_id)
        srt_content = srt_file.read_text(encoding="utf-8", errors="ignore") if srt_file.exists() else ""

        return {
            "success": True,
            "srt_path": str(srt_file) if srt_file.exists() else None,
            "srt_url": "/api/media/" + quote(srt_file.relative_to(BASE_DIR).as_posix(), safe="/") + ("?channel=" + scope.channel_id if isinstance(scope, ChannelScope) else "") if srt_file.exists() else None,
            "vtt_url": "/api/media/" + quote(vtt_file.relative_to(BASE_DIR).as_posix(), safe="/") + ("?channel=" + scope.channel_id if isinstance(scope, ChannelScope) else "") if vtt_file.exists() else None,
            "content": srt_content,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except (HTTPException, ChannelError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
