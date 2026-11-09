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
from scripts.config import DEFAULT_AD_TONE, DEFAULT_VOICE_PRESET

# Gemini takes open with ~0.1-0.4 s of silence before the first word, and may
# contain trailing silence or end-of-stream digital noise spikes (buffer clipping
# bursts / EOF glitch). Same -42 dBFS speech threshold as Edge, with:
# - 40ms head pad to preserve soft onsets (fricatives, breathy vowels)
# - 80ms tail pad to preserve natural acoustic speech decay
# - Tail artifact rejection: detects and removes isolated digital noise bursts
#   (short energy spikes within the last 350ms preceded by silence)
# - 15ms smooth linear fade-out to prevent zero-crossing clicks
GEMINI_LEAD_SILENCE_THRESHOLD_DB = -42.0
GEMINI_LEAD_SILENCE_PAD_S = 0.040
GEMINI_LEAD_SILENCE_MAX_S = 0.050
GEMINI_TAIL_SILENCE_PAD_S = 0.080
GEMINI_FADE_OUT_MS = 15.0
# Trims smaller than this are skipped so a second pass over an already
# trimmed file is a no-op (returns (0.0, 0.0) and leaves the file -- and its
# mtime -- untouched). Without it the 10ms hop grid shifted after the first
# trim and every re-run shaved another 1-5ms, rewriting the file (S2-02).
GEMINI_MIN_TRIM_S = 0.020
# EOF glitch classification (S2-13): a tail burst after a silence gap is only
# discarded when it is very short, much quieter than the speech, or clipping
# -- a real short final word ("ครับ", ~300ms at -12dB) is none of those.
GEMINI_GLITCH_MAX_SHORT_HOPS = 15       # <=150ms: too short to be a word
GEMINI_GLITCH_MAX_HOPS = 35             # <=350ms: longest burst ever treated as a glitch
GEMINI_GLITCH_QUIET_RATIO = 0.10        # burst RMS < -20dB of the loudest speech
GEMINI_GLITCH_CLIP_LEVEL = 32000        # int16 peak at/near full scale = buffer clip


def trim_silence_and_tail_artifacts_wav(
    wav_path: Path,
    threshold_db: float = GEMINI_LEAD_SILENCE_THRESHOLD_DB,
    pad_head_s: float = GEMINI_LEAD_SILENCE_PAD_S,
    pad_tail_s: float = GEMINI_TAIL_SILENCE_PAD_S,
    fade_out_ms: float = GEMINI_FADE_OUT_MS,
    trim_tail: bool = True,
) -> tuple[float, float]:
    """Trim a 16-bit PCM WAV in place: removes leading silence, trailing dead silence,
    and eliminates isolated EOF digital noise bursts (buffer pop/buzz glitches).

    Guarantees:
    - Soft speech onsets (fricatives, breathy vowels) are preserved via ``pad_head_s``.
    - Natural acoustic speech decay is preserved via ``pad_tail_s``.
    - Isolated tail artifacts (short noise bursts occurring after silence) are cleanly stripped.
    - Tail ends on a gentle linear fade-out to guarantee zero zero-crossing clicks.

    Returns ``(head_trimmed_s, tail_trimmed_s)``.
    """
    import numpy as np

    wav_path = Path(wav_path)
    if not wav_path.exists() or wav_path.stat().st_size < 44:
        return 0.0, 0.0

    with wave.open(str(wav_path), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if sampwidth != 2 or rate <= 0 or channels <= 0:
        return 0.0, 0.0

    samples = np.frombuffer(frames, dtype="<i2")
    n_frames = len(samples) // channels
    if n_frames == 0:
        return 0.0, 0.0

    # Reshape samples to (n_frames, channels)
    samples_2d = samples[: n_frames * channels].reshape(n_frames, channels)
    per_frame_max = np.abs(samples_2d.astype(np.int32)).max(axis=1)
    threshold = (10.0 ** (threshold_db / 20.0)) * 32768.0

    loud = np.flatnonzero(per_frame_max > threshold)
    if len(loud) == 0:
        return 0.0, 0.0

    # 1. Leading silence boundary
    first_loud_frame = int(loud[0])
    start_frame = max(0, first_loud_frame - int(round(pad_head_s * rate)))

    # 2. Trailing boundary with EOF artifact rejection
    if not trim_tail:
        end_frame = n_frames
    else:
        hop = max(1, int(0.01 * rate))  # 10ms energy hops
        n_hops = n_frames // hop
        if n_hops > 0:
            samples_float = samples_2d[: n_hops * hop].astype(np.float32) / 32768.0
            hop_matrix = samples_float.reshape(n_hops, hop, channels)
            hop_rms = np.sqrt(np.mean(hop_matrix ** 2, axis=(1, 2)))
            peak_rms = float(np.max(hop_rms)) if len(hop_rms) > 0 else 1.0
            speech_thresh = max(0.003, peak_rms * 0.045)
            is_speech = hop_rms >= speech_thresh

            curr_hop = n_hops - 1
            # Check if take ends with high energy (possible EOF digital artifact)
            if curr_hop >= 0 and (is_speech[curr_hop] or (curr_hop > 0 and is_speech[curr_hop - 1])):
                burst_hops = 0
                while curr_hop >= 0 and is_speech[curr_hop]:
                    burst_hops += 1
                    curr_hop -= 1
                silence_gap_hops = 0
                while curr_hop >= 0 and not is_speech[curr_hop]:
                    silence_gap_hops += 1
                    curr_hop -= 1

                # An isolated EOF glitch is <= 350ms preceded by >= 60ms
                # silence AND looks like a glitch: very short, much quieter
                # than the speech, or clipping. A short final word after a
                # breath (e.g. "ครับ") must survive.
                is_glitch = False
                if silence_gap_hops >= 6 and 0 < burst_hops <= GEMINI_GLITCH_MAX_HOPS:
                    burst_start = (n_hops - burst_hops) * hop
                    burst_rms = float(np.mean(hop_rms[n_hops - burst_hops:]))
                    burst_peak = int(per_frame_max[burst_start:].max()) if burst_start < n_frames else 0
                    is_glitch = (
                        burst_hops <= GEMINI_GLITCH_MAX_SHORT_HOPS
                        or burst_rms < peak_rms * GEMINI_GLITCH_QUIET_RATIO
                        or burst_peak >= GEMINI_GLITCH_CLIP_LEVEL
                    )
                if not is_glitch:
                    curr_hop = n_hops - 1

            last_speech_hop = 0
            for j in range(curr_hop, -1, -1):
                if is_speech[j]:
                    last_speech_hop = j
                    break

            end_frame = min(n_frames, (last_speech_hop + 1) * hop + int(round(pad_tail_s * rate)))
        else:
            last_loud_frame = int(loud[-1])
            end_frame = min(n_frames, last_loud_frame + 1 + int(round(pad_tail_s * rate)))

    if end_frame <= start_frame:
        return 0.0, 0.0

    # Sub-threshold trims are noise from the hop grid, not real silence --
    # skipping them keeps the trim idempotent.
    # The head tolerance is capped so a skipped head trim still leaves the
    # first sound within GEMINI_LEAD_SILENCE_MAX_S.
    min_head_frames = int(round(min(GEMINI_MIN_TRIM_S, max(0.0, GEMINI_LEAD_SILENCE_MAX_S - pad_head_s)) * rate))
    min_tail_frames = int(round(GEMINI_MIN_TRIM_S * rate))
    if start_frame < min_head_frames:
        start_frame = 0
    if n_frames - end_frame < min_tail_frames:
        end_frame = n_frames

    # If already tight at both ends, nothing to trim
    if start_frame == 0 and end_frame == n_frames:
        return 0.0, 0.0

    out_samples = samples[start_frame * channels : end_frame * channels].copy()

    # Apply smooth micro-fadeout at the end only if tail was trimmed
    fade_samples = int(round((fade_out_ms / 1000.0) * rate))
    out_frame_count = len(out_samples) // channels
    if trim_tail and end_frame < n_frames and out_frame_count > fade_samples > 0:
        fade_curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        for c in range(channels):
            tail_slice = out_samples[
                (out_frame_count - fade_samples) * channels + c :: channels
            ]
            faded = (tail_slice.astype(np.float32) * fade_curve).astype("<i2")
            out_samples[(out_frame_count - fade_samples) * channels + c :: channels] = faded

    tmp_path = wav_path.with_suffix(".trim.tmp.wav")
    try:
        with wave.open(str(tmp_path), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(sampwidth)
            out.setframerate(rate)
            out.writeframes(out_samples.tobytes())
        os.replace(tmp_path, wav_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    head_trimmed_s = start_frame / rate
    tail_trimmed_s = (n_frames - end_frame) / rate
    return head_trimmed_s, tail_trimmed_s


def trim_leading_silence_wav(
    wav_path: Path,
    threshold_db: float = GEMINI_LEAD_SILENCE_THRESHOLD_DB,
    pad_s: float = GEMINI_LEAD_SILENCE_PAD_S,
) -> float:
    """Trim a 16-bit PCM WAV in place so the first sound starts within ``pad_s``.

    Only leading silence is removed; nothing after the first sample above
    ``threshold_db`` (plus the ``pad_s`` before it) is touched, so the speech
    onset is never clipped. Returns the seconds removed (0.0 when the file is
    already tight, entirely silent, or not 16-bit PCM).
    Backward-compatible wrapper around ``trim_silence_and_tail_artifacts_wav``.
    """
    head_s, _ = trim_silence_and_tail_artifacts_wav(
        wav_path=wav_path,
        threshold_db=threshold_db,
        pad_head_s=pad_s,
        trim_tail=False,
    )
    return head_s


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
_FEMALE_VOICES = frozenset(
    p["voice"] for p in GEMINI_VOICE_PRESETS.values() if p.get("gender") == "female"
)


class GeminiFlashTTSEngine:
    """Google Gemini 3.1 Flash Speech Generation Engine."""
    MODEL_CANDIDATES = [
        "gemini-3.8-flash-tts",
        "gemini-2.5-flash-preview-tts",
    ]

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
        voice_preset: str = DEFAULT_VOICE_PRESET,
        voice_name: Optional[str] = None,
        ad_tone: str = DEFAULT_AD_TONE,
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

        # Determine Gemini Voice Name. An unknown preset falls back through
        # resolve_voice() to the canonical male voice (Fenrir), the same
        # answer preview gives -- it used to fall back to the female Kore.
        target_voice = voice_name or cls.resolve_voice(preset=voice_preset)
        voice_gender = "female" if target_voice in _FEMALE_VOICES else "male"

        out_wav = Path(output_path).resolve()
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        # Remove any pre-existing file at destination so a failed synthesis
        # run can never silently leave stale audio behind.
        out_wav.unlink(missing_ok=True)

        clean_text = text.strip()

        # Sanitize for TTS — strip emoji, expand abbreviations, remove hashtags
        try:
            from scripts.tts_sanitizer import TTSSanitizer
            clean_text = TTSSanitizer.clean(clean_text, gender=voice_gender)
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
        model_candidates = list(cls.MODEL_CANDIDATES)

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

                # Speech starts within GEMINI_LEAD_SILENCE_MAX_S, with trailing silence and
                # EOF digital noise bursts eliminated cleanly.
                # A trim failure keeps the untrimmed (still valid) take.
                try:
                    head_s, tail_s = trim_silence_and_tail_artifacts_wav(out_wav)
                    if head_s > 0 or tail_s > 0:
                        parts = []
                        if head_s > 0:
                            parts.append(f"ตัดช่วงเงียบต้นเสียง {head_s * 1000:.0f}ms")
                        if tail_s > 0:
                            parts.append(f"ตัดช่วงเงียบ/เสียงขยะท้ายเสียง {tail_s * 1000:.0f}ms")
                        print(f"   [Gemini Flash TTS] {', '.join(parts)}")
                except Exception as trim_err:
                    print(f"⚠️ [Gemini Flash TTS] ตัดเสียงส่วนเกินไม่สำเร็จ ใช้ไฟล์เดิม: {trim_err}")

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
        # Self-test output goes to .tmp/, never the real asset library (S2-20).
        test_out = PROJECT_ROOT / ".tmp" / "test_gemini_cli.wav"
        res = GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ สายชาร์จแม่เหล็กตัวนี้แรงดูดดีมาก ชาร์จไวสุดๆ ลองใช้แล้วจะติดใจครับ",
            output_path=str(test_out),
            voice_preset=DEFAULT_VOICE_PRESET,
            speed=1.15
        )
        print("Self-test completed:", res)
    else:
        print("No GEMINI_API_KEY found.")
