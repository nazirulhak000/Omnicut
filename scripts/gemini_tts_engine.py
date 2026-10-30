import os
import sys
import json
import math
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

from scripts.error_handler import AppError, ErrorCategory

class GeminiTTSError(AppError, RuntimeError):
    """Specific error for Gemini Flash TTS failures with actionable wait time and reasons."""
    def __init__(
        self,
        message_th: str,
        suggestion_th: str = "",
        code: str = "GEMINI_TTS_FAILED",
        details: Optional[str] = None,
        retry_delay_seconds: Optional[float] = None,
    ):
        super().__init__(
            category=ErrorCategory.AI_PROVIDER,
            code=code,
            message_th=message_th,
            suggestion_th=suggestion_th,
            details=details,
        )
        self.retry_delay_seconds = retry_delay_seconds

    def __str__(self) -> str:
        sugg = f" — {self.suggestion_th}" if self.suggestion_th else ""
        return f"[{self.category.value.upper()}:{self.code}] {self.message_th}{sugg} (Details: {self.details})"

def _load_env_file(env_file: Path) -> None:
    """Fill missing settings without overriding explicit process configuration."""
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env_file(PROJECT_ROOT / ".env")

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
    },
    "tech_journalism_calm": {
        "name": "🎙️ ผู้ประกาศข่าวนวัตกรรม นุ่มนวล น่าเชื่อถือ (Calm Tech Journalism)",
        "prompt": "Scene: High-End Tech Documentary & Studio.\nSample Context: Warm, calm, smooth, soothing, and deeply trustworthy tech journalist. Natural tempo, articulate, objective, elegant, and credible. No shouting, no hype, no sales pitch."
    }
}

VALID_VOICES = ("Puck", "Charon", "Kore", "Aoede", "Fenrir")


class GeminiFlashTTSEngine:
    """Google Gemini 3.1 Flash Speech Generation Engine."""

    @classmethod
    def get_api_keys(cls) -> list[str]:
        """Returns all configured Gemini API keys from environment and .env in priority order."""
        from scripts.config import get_gemini_api_keys
        return get_gemini_api_keys()

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
        return "Fenrir"

    @staticmethod
    def build_atempo_filter(speed: float) -> str:
        """Construct FFmpeg atempo audio filter chain.

        FFmpeg's atempo filter strictly requires 0.5 <= value <= 2.0.
        Speeds outside this range are decomposed into chained filters,
        e.g. speed=2.5 becomes 'atempo=2.0,atempo=1.25'.
        """
        try:
            val = float(speed)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Speed must be a valid float, got: {speed!r}") from exc

        if not (math.isfinite(val) and val > 0):
            raise ValueError(f"Speed must be a positive finite number, got: {speed}")

        filters = []
        curr = val
        while curr > 2.0:
            filters.append("atempo=2.0")
            curr /= 2.0
        while curr < 0.5:
            filters.append("atempo=0.5")
            curr /= 0.5

        formatted_val = f"{round(curr, 4):g}"
        filters.append(f"atempo={formatted_val}")
        return ",".join(filters)

    @classmethod
    def generate_speech(
        cls,
        text: str,
        output_path: str,
        voice_preset: str = "gemini_fenrir_male_strong",
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
        # Remove any pre-existing file at destination so a failed synthesis
        # run can never silently leave stale audio behind.
        out_wav.unlink(missing_ok=True)

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
        # Priority: gemini-3.8-flash-tts (best & active), gemini-2.5-flash-preview-tts
        model_candidates = [
            "gemini-3.8-flash-tts",
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
        rate_limit_diag = None

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
                        err_body = ""
                        try:
                            if hasattr(he, "read"):
                                raw_bytes = he.read()
                                err_body = raw_bytes.decode("utf-8", errors="ignore") if isinstance(raw_bytes, bytes) else str(raw_bytes)
                        except Exception:
                            pass

                        if he.code == 429:
                            retry_delay_seconds = None
                            try:
                                if hasattr(he, "headers") and he.headers and he.headers.get("Retry-After"):
                                    retry_delay_seconds = float(he.headers.get("Retry-After"))
                            except (TypeError, ValueError):
                                pass

                            if retry_delay_seconds is None and err_body:
                                try:
                                    err_json = json.loads(err_body)
                                    for detail in err_json.get("error", {}).get("details", []):
                                        if isinstance(detail, dict) and "retryDelay" in detail:
                                            raw_delay = str(detail["retryDelay"]).rstrip("s")
                                            retry_delay_seconds = float(raw_delay)
                                            break
                                except Exception:
                                    pass
                                if retry_delay_seconds is None:
                                    import re
                                    m = re.search(r'retryDelay["\']?\s*:\s*["\']?([\d\.]+)s?', err_body)
                                    if m:
                                        try:
                                            retry_delay_seconds = float(m.group(1))
                                        except ValueError:
                                            pass

                            is_rpm = any(term in err_body.lower() for term in ["per minute", "rpm", "minute"])
                            is_rpd = any(term in err_body.lower() for term in ["per day", "rpd", "daily"])

                            rate_limit_diag = {
                                "key_tag": key_tag,
                                "model_name": model_name,
                                "retry_delay_seconds": retry_delay_seconds,
                                "is_rpm": is_rpm,
                                "is_rpd": is_rpd,
                                "err_body": err_body,
                            }

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
                                backoff = retry_delay_seconds if retry_delay_seconds and retry_delay_seconds <= RATE_LIMIT_MAX_BACKOFF else RATE_LIMIT_DEFAULT_BACKOFF
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
            if rate_limit_diag:
                delay = rate_limit_diag.get("retry_delay_seconds")
                if delay and delay > 0:
                    if delay >= 3600:
                        wait_str = f"{int(delay // 3600)} ชั่วโมง {int((delay % 3600) // 60)} นาที"
                    elif delay >= 60:
                        wait_str = f"{int(delay // 60)} นาที {int(delay % 60)} วินาที"
                    else:
                        wait_str = f"{int(delay)} วินาที"
                    wait_instruction = f"สร้างเสียงถี่เกินไป กรุณารอประมาณ {wait_str} แล้วลองใหม่อีกครั้ง"
                elif rate_limit_diag.get("is_rpm"):
                    wait_instruction = "คำขอสร้างเสียงถี่เกินไป (RPM Rate Limit) กรุณารอสักครู่ (ประมาณ 1–2 นาที) แล้วลองใหม่อีกครั้ง"
                elif rate_limit_diag.get("is_rpd"):
                    wait_instruction = "โควตาสร้างเสียงรายวัน (Daily Quota) เต็มแล้ว กรุณารอรีเซ็ตในวันถัดไป หรือเพิ่ม API Key สำรองใน .env"
                else:
                    wait_instruction = "ติดลิมิตการส่งคำขอ กรุณารอประมาณ 1–2 นาที หรือเพิ่ม Gemini API Key สำรองใน .env"

                msg_th = "Gemini TTS ติดขีดจำกัดการใช้งาน (HTTP 429 Rate Limit/Quota)"
                sugg_th = f"{wait_instruction} (ระบบหยุดการทำงาน ไม่สลับไป Edge-TTS ตามที่กำหนด)"
                raise GeminiTTSError(
                    message_th=msg_th,
                    suggestion_th=sugg_th,
                    code="GEMINI_TTS_RATE_LIMITED",
                    details=f"All Gemini Flash TTS keys and models failed. Last error: {last_error}",
                    retry_delay_seconds=delay,
                )

            raise GeminiTTSError(
                message_th="Gemini TTS สร้างเสียงไม่สำเร็จ",
                suggestion_th="กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต หรือตรวจสอบ Gemini API Key ใน .env (ระบบหยุดการทำงาน ไม่สลับไป Edge-TTS ตามที่กำหนด)",
                code="GEMINI_TTS_FAILED",
                details=f"All Gemini Flash TTS keys and models failed. Last error: {last_error}",
            )

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
                temp_speed_wav = out_wav.with_suffix(".speed.tmp.wav")
                try:
                    with wave.open(str(temp_raw_wav), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) # 16-bit
                        wf.setframerate(24000)
                        wf.writeframes(pcm_bytes)

                    # If speed adjustment requested, run ffmpeg atempo
                    if abs(speed - 1.0) > 0.02:
                        filter_chain = cls.build_atempo_filter(speed)
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", str(temp_raw_wav),
                            "-filter:a", filter_chain,
                            "-ar", "24000",
                            str(temp_speed_wav)
                        ]
                        try:
                            proc = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="ignore"
                            )
                        except FileNotFoundError as fnf_err:
                            raise RuntimeError(
                                "ไม่พบคำสั่ง 'ffmpeg' ในระบบ กรุณาติดตั้ง FFmpeg หรือตรวจสอบ PATH"
                            ) from fnf_err

                        if proc.returncode != 0:
                            err_msg = (proc.stderr or proc.stdout or "").strip()
                            raise RuntimeError(
                                f"FFmpeg atempo failed with exit code {proc.returncode}: {err_msg[:400]}"
                            )
                        if not temp_speed_wav.exists() or temp_speed_wav.stat().st_size == 0:
                            raise RuntimeError(
                                f"FFmpeg atempo succeeded with code 0 but target file is missing or empty: {temp_speed_wav.name}"
                            )
                        os.replace(temp_speed_wav, out_wav)
                    else:
                        os.replace(temp_raw_wav, out_wav)
                finally:
                    for transient in (temp_raw_wav, temp_speed_wav):
                        if transient.exists():
                            try:
                                transient.unlink()
                            except Exception:
                                pass

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
            voice_preset="gemini_fenrir_male_strong",
            speed=1.15
        )
        print("Self-test completed:", res)
    else:
        print("No GEMINI_API_KEY found.")
