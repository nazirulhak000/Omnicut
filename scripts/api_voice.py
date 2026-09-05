"""
API Router for Voice, Script generation, and Speech Recognition (sub-srt).
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request

from scripts.config import (
    BASE_DIR, ASSETS_DIR, VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.script_generator import ScriptGenerator
from scripts.voice_engine import VoiceEngine
from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.tts_sanitizer import TTSSanitizer
from scripts.api_schemas import (
    ScriptGenerateRequest, VoicePreviewRequest, TranscribeRequest
)
from scripts.media_service import measure_wav_duration

PROJECT_ROOT = Path(__file__).resolve().parent.parent

router = APIRouter(tags=["Voice & Script"])

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
def preview_voice(req: VoicePreviewRequest):
    """Generates a quick voice sample for auditioning (Edge-TTS or Gemini Flash)."""
    sample_file = BASE_DIR / "test_voice.wav"
    text = req.text or "สวัสดีค่ะ นี่คือเสียงตัวอย่างสำหรับคลิปรีวิวสินค้า"
    voice_gender = req.voice_gender or "female"
    speed = req.speed or 1.15
    ad_tone = req.ad_tone or "commercial_premium"

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
                "audio_url": f"/api/media/{sample_file.name}",
                "duration": measure_wav_duration(sample_file),
                "voice_name": gemini_voice
            }
        except Exception as g_err:
            print(f"⚠️ [preview_voice] Gemini TTS failed ({g_err}) — fallback to Edge-TTS...")

    res = VoiceEngine.generate_crystal_voice(
        text_or_lines=text,
        output_audio_path=str(sample_file),
        speed=speed,
        voice_gender=voice_gender
    )
    if not res:
        raise HTTPException(status_code=500, detail="Voice generation failed")

    return {
        "audio_url": f"/api/media/{sample_file.name}",
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
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
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
                    "hashtags": ["#ของดีบอกต่อ", "#รีวิวของใช้", "#tiktokshop", f"#{req.product_name.replace(' ', '')}"]
                }
            ]
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""คุณเป็นสุดยอด Copywriter และผู้เชี่ยวชาญการทำคลิป TikTok Shop / Affiliate มือโปร
กรุณาแต่งสคริปต์วิดีโอรีวิวป้ายยา 4 มุมมอง (4 Angles) สำหรับสินค้า:
- ชื่อสินค้า: {req.product_name}
- จุดเด่น: {req.key_features}
- ปัญหาที่แก้: {req.pain_point}
- ราคา/โปร: {req.price_deal}

กฎเหล็กการเขียนบทพูด:
- ชื่อแบรนด์, ชื่อรุ่นสินค้า, และคำศัพท์เฉพาะทางที่เป็นภาษาอังกฤษ (เช่น Logitech, Wave Keys, Logi Bolt, Bluetooth, USB-C, Type-C, iPad ฯลฯ) ให้คงไว้เป็นภาษาอังกฤษตามชื่อทางการเสมอ ห้ามทับศัพท์เป็นคำไทยเพี้ยนๆ (เช่น ห้ามเขียน "โลจิเทค", "โลจิ โบลต์")
- ห้ามใช้จุดไข่ปลา "..." หรือ "…" ในทุกฟิลด์โดยเด็ดขาด (ทั้งใน script_text, hook_title, caption) ให้เว้นวรรคธรรมดาแทน
- ห้ามใช้ภาษาโฆษณาทีวีทางการ ให้ใช้ภาษาพูดเพื่อนสนิทป้ายยา
- ห้ามใส่ emoji ในบทพูด (script_text) ใส่ได้เฉพาะ angle_name และ hook_title

กรุณาแต่งสคริปต์ภาษาพูดคนรีวิวจริง (ไม่เอาภาษาโฆษณาแข็งๆ) 4 รูปแบบ:
1. เตือนภัย / จี้จุดเจ็บ (Stop Scroll / Pain Point)
2. โชว์ฟังก์ชันสุดล้ำ / ว้าว (Tech Feature Hype)
3. โปรเดือด / ความคุ้มค่า (FOMO / Price Value)
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
      "script_text": "ประโยคที่ 1\\nประโยคที่ 2\\nประโยคที่ 3\\nประโยคที่ 4\\nประโยคที่ 5 ปิดการขายจิ้มตะกร้า",
      "caption": "แคปชั่นสั้นๆ สำหรับโพสต์",
      "hashtags": ["#ของดีบอกต่อ", "#tiktokshop"]
    }}
  ]
}}
```"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )

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
                    "hashtags": ["#ของดีบอกต่อ", "#รีวิวของใช้", "#tiktokshop"]
                }
            ]
        }


@router.post("/api/sub-srt/transcribe")
def run_sub_srt_transcription(req: TranscribeRequest):
    """Runs sub-srt Speech Recognition on a video or audio file."""
    media_path = Path(req.media_path)
    if not media_path.is_absolute():
        media_path = BASE_DIR / req.media_path

    if not media_path.exists():
        raise HTTPException(status_code=404, detail=f"Media file not found: {media_path}")

    skill_script = PROJECT_ROOT / ".agents" / "skills" / "sub-srt" / "generate_srt.py"
    if not skill_script.exists():
        skill_script = Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "config" / "skills" / "sub-srt" / "generate_srt.py"

    out_dir = media_path.parent
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

        srt_content = srt_file.read_text(encoding="utf-8", errors="ignore") if srt_file.exists() else ""

        return {
            "success": True,
            "srt_path": str(srt_file) if srt_file.exists() else None,
            "srt_url": f"/api/media/{srt_file.relative_to(BASE_DIR)}" if srt_file.exists() else None,
            "vtt_url": f"/api/media/{vtt_file.relative_to(BASE_DIR)}" if vtt_file.exists() else None,
            "content": srt_content,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
