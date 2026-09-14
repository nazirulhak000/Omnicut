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

VALID_VOICES = ("Puck", "Charon", "Kore", "Aoede", "Fenrir")


class GeminiFlashTTSEngine:
    """Google Gemini 3.1 Flash Speech Generation Engine."""

    @classmethod
    def get_api_keys(cls) -> list[str]:
        """Returns all configured Gemini API keys from environment and .env in priority order."""
        keys = []
        # Reload latest .env
        env_f = PROJECT_ROOT / ".env"
        if env_f.exists():
            for line in env_f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k_str, v_str = k.strip(), v.strip()
                    if "GEMINI_API_KEY" in k_str and v_str and v_str not in keys:
                        keys.append(v_str)

        # Check current process environment
        for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_OLD"]:
            v = os.environ.get(k, "").strip()
            if v and v not in keys:
                keys.append(v)

        return keys

    @classmethod
    def is_available(cls) -> bool:
        return len(cls.get_api_keys()) > 0

    @classmethod
    def resolve_voice(cls, preset: Optional[str] = None, gender: Optional[str] = None) -> str:
        """
        Single source of truth for preset/gender -> Gemini voice name.

        Preview and render both call this, so what the user auditions is what
        they get in the finished clip.
        """
        if preset:
            if preset in GEMINI_VOICE_PRESETS:
                return GEMINI_VOICE_PRESETS[preset]["voice"]
            if preset in VALID_VOICES:
                return preset
            # Tolerate raw voice names in any casing, e.g. "puck"
            for voice in VALID_VOICES:
                if preset.strip().lower() == voice.lower():
                    return voice

        if gender and "female" in gender.lower():
            return "Kore"
        return "Puck"

    @classmethod
    def generate_speech(
        cls,
        text: str,
        output_path: str,
        voice_preset: str = "gemini_puck_male_hype",
        voice_name: Optional[str] = None,
        ad_tone: str = "commercial_hype",
        speed: float = 1.15
    ) -> str:
        """
        Generates crystal-clear Thai speech using Gemini Flash TTS with Commercial Ad Direction.
        Supports multi-key fallback and model failover across all keys in .env.
        """
        api_keys = cls.get_api_keys()
        if not api_keys:
            raise ValueError("GEMINI_API_KEY is missing. Please set it in .env or environment.")

        # Pre-flight budget check -- before the paid network call below
        # (usage is recorded only after a successful generation, around
        # :257-ish). Raises AppError(AI_QUOTA_EXCEEDED) if over budget;
        # no-op if unconfigured.
        from scripts.quota import check_budget
        check_budget(task="tts")

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

        # Sanitize for TTS — strip emoji, expand abbreviations, remove hashtags
        try:
            from scripts.tts_sanitizer import TTSSanitizer
            clean_text = TTSSanitizer.clean(clean_text)
        except ImportError:
            pass  # Graceful fallback if sanitizer not available

        # Build Acting Direction Prompt.
        # An unrecognised tone deliberately keeps reading with the
        # commercial_premium direction rather than failing the synthesis --
        # but say so, since the voice then follows a direction nobody asked
        # for and the result only sounds slightly off, never broken.
        if ad_tone not in AD_TONE_PRESETS:
            print(f"   ⚠️ [GeminiTTS] ไม่รู้จัก ad_tone '{ad_tone}' — ใช้ commercial_premium แทน")
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

        # Models supporting Thai audio generation in Google Gemini API
        # Priority: gemini-3.1-flash-tts-preview (best & active), gemini-2.5-flash-preview-tts
        model_candidates = [
            "gemini-3.1-flash-tts-preview",
            "gemini-2.5-flash-preview-tts",
        ]

        import time
        data = None
        last_error = None

        # Retry shape per (key, model) -- bounded, not an elaborate
        # framework. HTTPError.code is a real int status (no string
        # matching needed, unlike the SDK path in ai_bridge.py this engine
        # doesn't use): 429 backs off (Retry-After header if present, else a
        # short default) and retries the SAME key+model once before moving
        # on; a non-HTTP URLError/timeout (network down, DNS, connect
        # refused) is transient and retries the SAME key+model once after a
        # short fixed backoff; 401/403 (invalid/revoked key) and any other
        # HTTP status rotate immediately -- retrying can't fix those.
        RATE_LIMIT_DEFAULT_BACKOFF = 5.0
        RATE_LIMIT_MAX_BACKOFF = 30.0
        TRANSIENT_BACKOFF = 2.0

        # Multi-model & Multi-key fallback matrix (Model-First Strategy)
        # We try the best quality model across ALL keys first (Key 1 -> Key 2 -> ...)
        # If all keys hit rate-limit / quota on the primary model, we then fallback to the next model across all keys.
        from scripts.token_tracker import TokenTracker

        success_key_tag = None
        success_model_name = None

        for model_name in model_candidates:
            for key_idx, cur_key in enumerate(api_keys, 1):
                key_tag = f"Key #{key_idx} (..{cur_key[-6:]})"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={cur_key}"
                for attempt in range(2):
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=75) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            print(f"✨ [Gemini Flash TTS] Used model '{model_name}' on {key_tag} with voice '{target_voice}'")
                            success_key_tag = key_tag
                            success_model_name = model_name
                            break
                    except urllib.error.HTTPError as he:
                        last_error = he
                        if he.code == 429:
                            # Record alert to TokenTracker
                            try:
                                TokenTracker.record_alert(
                                    task="tts",
                                    model=model_name,
                                    key_tag=key_tag,
                                    error_type="RATE_LIMIT_429",
                                    message=f"{key_tag} ติดขีดจำกัด Rate-Limit / Quota (HTTP 429) สำหรับโมเดล '{model_name}' — ระบบกำลังสลับไป Key หรือโมเดลถัดไป...",
                                    level="warning"
                                )
                            except Exception:
                                pass

                            if attempt == 0 and len(api_keys) == 1:
                                backoff = RATE_LIMIT_DEFAULT_BACKOFF
                                try:
                                    retry_after = he.headers.get("Retry-After") if he.headers else None
                                    if retry_after:
                                        backoff = min(float(retry_after), RATE_LIMIT_MAX_BACKOFF)
                                except (TypeError, ValueError):
                                    pass
                                print(f"⚠️ [Gemini Flash TTS] {key_tag} with '{model_name}' rate-limited (429) — retrying same key/model in {backoff:.0f}s...")
                                time.sleep(backoff)
                                continue
                            else:
                                print(f"⚠️ [Gemini Flash TTS] {key_tag} with '{model_name}' rate-limited (HTTP 429) — jumping to next key/fallback immediately...")
                                break
                        print(f"⚠️ [Gemini Flash TTS] {key_tag} with '{model_name}' returned HTTP {he.code} — checking next fallback...")
                        break
                    except Exception as e:
                        last_error = e
                        if attempt == 0:
                            print(f"⚠️ [Gemini Flash TTS] {key_tag} with '{model_name}' failed ({e}) — retrying same key/model in {TRANSIENT_BACKOFF:.0f}s...")
                            time.sleep(TRANSIENT_BACKOFF)
                            continue
                        print(f"⚠️ [Gemini Flash TTS] {key_tag} with '{model_name}' failed ({e}) — checking next fallback...")
                        break
                if data:
                    break
            if data:
                break

        if not data:
            raise RuntimeError(f"All Gemini Flash TTS keys and models failed. Last error: {last_error}")

        if success_key_tag and len(api_keys) > 1 and success_key_tag != f"Key #1 (..{api_keys[0][-6:]})":
            try:
                TokenTracker.record_alert(
                    task="tts",
                    model=success_model_name,
                    key_tag=success_key_tag,
                    error_type="KEY_FAILOVER_SUCCESS",
                    message=f"สลับมาใช้ {success_key_tag} สำหรับโมเดล '{success_model_name}' สำเร็จเรียบร้อย",
                    level="info"
                )
            except Exception:
                pass

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

                # Record token analytics
                try:
                    from scripts.token_tracker import TokenTracker
                    in_tok = max(50, len(formatted_prompt) // 2)
                    out_tok = max(100, len(clean_text) * 2)
                    TokenTracker.record_event(
                        task="tts",
                        model="gemini-3.1-flash-tts",
                        provider="gemini_free_tier",
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        project_name=out_wav.stem,
                        metadata={"voice": target_voice, "ad_tone": ad_tone}
                    )
                except Exception:
                    pass

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
