import os
import sys
import json
import wave
import base64
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if present
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_VOICE_PRESETS = {
    "gemini_puck_male_hype": {"voice": "Puck", "gender": "male", "name": "⚡ Puck (ชายพลังสูง สไตล์ TikTok)"},
    "gemini_charon_male_pro": {"voice": "Charon", "gender": "male", "name": "🎙️ Charon (ชายทุ้มลึก น่าเชื่อถือ)"},
    "gemini_kore_female_bright": {"voice": "Kore", "gender": "female", "name": "✨ Kore (หญิงสดใส ป้ายยาเก่ง)"},
    "gemini_aoede_female_pro": {"voice": "Aoede", "gender": "female", "name": "👑 Aoede (หญิงพรีเมียม นุ่มนวล)"},
    "gemini_fenrir_male_strong": {"voice": "Fenrir", "gender": "male", "name": "🔥 Fenrir (ชายสตรอง คมเข้ม)"},
}

AD_TONE_PRESETS = {
    "commercial_premium": {
        "name": "📢 โฆษณาพรีเมียม (Premium Commercial - เริ่มน่าค้นหา จบชวนซื้อ)",
        "prompt": "Scene: The Sound Stage Booth.\nSample Context: Premium commercial. Dynamic pacing—starts intrigued, ends punchy. Tone is polished, persuasive, and inviting."
    },
    "commercial_hype": {
        "name": "🔥 ป้ายยาตัวแม่ TikTok ไวรัล (Viral Hype - ตื่นเต้น เร่งด่วน)",
        "prompt": "Scene: Viral TikTok Live Stage.\nSample Context: High-energy viral TikTok product review. Dynamic, enthusiastic, fast-paced, excited, and highly persuasive."
    },
    "commercial_aesthetic": {
        "name": "✨ มินิมอล นุ่มนวล ดูแพง (Aesthetic Beauty & Lifestyle)",
        "prompt": "Scene: Cozy Modern Studio.\nSample Context: Warm, soothing, aesthetic lifestyle commercial. Relaxed, intimate, friendly, and authentic tone."
    },
    "commercial_expert": {
        "name": "🎙️ ผู้เชี่ยวชาญ คมชัด น่าเชื่อถือ (Tech & Pro Authority)",
        "prompt": "Scene: Tech Broadcast Studio.\nSample Context: Confident, crisp, authoritative reviewer. Clear articulation, professional, and convincing."
    }
}

class GeminiFlashTTSEngine:
    """Google Gemini 3.1 Flash Speech Generation Engine."""

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY)

    @classmethod
    def generate_speech(
        cls,
        text: str,
        output_path: str,
        voice_preset: str = "gemini_kore_female_bright",
        voice_name: Optional[str] = None,
        ad_tone: str = "commercial_premium",
        speed: float = 1.15
    ) -> str:
        """
        Generates crystal-clear Thai speech using Gemini 3.1 Flash TTS with Commercial Ad Direction.
        """
        api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Please set it in .env or environment.")

        # Determine Gemini Voice Name
        target_voice = "Kore"
        if voice_name:
            target_voice = voice_name
        elif voice_preset in GEMINI_VOICE_PRESETS:
            target_voice = GEMINI_VOICE_PRESETS[voice_preset]["voice"]
        elif voice_preset in ["Puck", "Charon", "Kore", "Aoede", "Fenrir"]:
            target_voice = voice_preset

        out_wav = Path(output_path).resolve()
        out_wav.parent.mkdir(parents=True, exist_ok=True)

        clean_text = text.strip()

        # Build Acting Direction Prompt
        tone_cfg = AD_TONE_PRESETS.get(ad_tone, AD_TONE_PRESETS["commercial_premium"])
        formatted_prompt = f"[{tone_cfg['prompt']}]\n\nRead the following Thai transcript using the commercial acting direction above:\n{clean_text}"

        payload = {
            "contents": [{
                "parts": [{"text": formatted_prompt}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": target_voice
                        }
                    }
                }
            }
        }

        # Try gemini-3.1-flash-tts-preview first, fallback to 2.5 if needed
        model_candidates = [
            "gemini-3.1-flash-tts-preview",
            "gemini-2.5-flash-preview-tts"
        ]
        
        last_error = None
        data = None

        for model_name in model_candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    print(f"✨ [Gemini Flash TTS] Used model '{model_name}' with voice '{target_voice}'")
                    break
            except Exception as e:
                last_error = e
                print(f"⚠️ [Gemini Flash TTS] Model '{model_name}' error: {e}, trying fallback...")

        if not data:
            raise RuntimeError(f"All Gemini Flash TTS models failed. Last error: {last_error}")

        try:
                
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                if not parts or "inlineData" not in parts[0]:
                    raise RuntimeError("Gemini Flash TTS returned no audio inline data.")

                raw_b64 = parts[0]["inlineData"]["data"]
                pcm_bytes = base64.b64decode(raw_b64)

                # Write standard WAV header (16-bit 24kHz mono PCM)
                temp_raw_wav = out_wav.with_suffix(".raw.wav")
                with wave.open(str(temp_raw_wav), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2) # 16-bit
                    wf.setframerate(24000)
                    wf.writeframes(pcm_bytes)

                # If speed adjustment requested, run ffmpeg atempo
                if abs(speed - 1.0) > 0.02:
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", str(temp_raw_wav),
                        "-filter:a", f"atempo={speed}",
                        "-ar", "24000",
                        str(out_wav)
                    ]
                    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
                    if temp_raw_wav.exists():
                        try:
                            temp_raw_wav.unlink()
                        except Exception:
                            pass
                else:
                    if out_wav.exists():
                        out_wav.unlink()
                    temp_raw_wav.rename(out_wav)

                print(f"✨ [Gemini Flash TTS] Generated successfully with voice '{target_voice}' -> {out_wav}")
                return str(out_wav)

        except Exception as e:
            print(f"❌ [Gemini Flash TTS] Generation failed: {e}")
            raise

if __name__ == "__main__":
    if GeminiFlashTTSEngine.is_available():
        test_out = PROJECT_ROOT / "02_Assets" / "Voiceover" / "test_gemini_cli.wav"
        res = GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ สายชาร์จแม่เหล็กตัวนี้แรงดูดดีมาก ชาร์จไวสุดๆ ลองใช้แล้วจะติดใจครับ",
            output_path=str(test_out),
            voice_preset="gemini_puck_male_hype",
            speed=1.15
        )
        print("Self-test completed:", res)
    else:
        print("No GEMINI_API_KEY found.")
