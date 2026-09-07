"""
Script tone-shift classifier.

Text-only Gemini call (no video, unlike gemini_vision_matcher.py) used by
scripts/pipeline.py to decide which shot boundaries deserve a stronger
transition -- a real topic/tone change (pain-point into solution, body into
CTA) versus just a pause between beats of the same idea. Optional: no API
key or a failing call degrades to an empty classification, and pipeline.py's
existing gap/sentence-ending heuristic keeps deciding transitions exactly as
it did before this existed.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List

from scripts.config import ASSETS_DIR

TONE_CACHE_FILE = ASSETS_DIR / ".tone_cache.json"

# Load .env if present -- same pattern as gemini_vision_matcher.py, needed
# when this module is imported before anything else has loaded it.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_file = _PROJECT_ROOT / ".env"
if _env_file.exists():
    try:
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass


class ScriptToneAnalyzer:
    """Classifies the tone-shift severity of each boundary between consecutive shot groups."""

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())

    @classmethod
    def _load_cache(cls) -> Dict[str, list]:
        if TONE_CACHE_FILE.exists():
            try:
                return json.loads(TONE_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_cache(cls, cache: Dict[str, list]) -> None:
        try:
            TONE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            TONE_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def classify_tone_shifts(cls, group_texts: List[str]) -> List[str]:
        """
        `group_texts[i]` is the combined script text of shot group i, in
        timeline order. Returns one classification per boundary between
        consecutive groups (`len(group_texts) - 1` entries), each one of
        "none" / "minor" / "major". Returns `[]` (never raises) when there's
        no API key, fewer than 2 groups, or the call fails/misbehaves for
        any reason -- callers must fall back to their own heuristic then.
        """
        if len(group_texts) < 2:
            return []
        if not cls.is_available():
            return []

        cache_key = hashlib.md5("|".join(group_texts).encode("utf-8")).hexdigest()
        cache = cls._load_cache()
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        expected_len = len(group_texts) - 1

        # Pre-flight budget check, after the cache lookup above so a hit costs
        # no quota, and outside the try below so AppError(AI_QUOTA_EXCEEDED)
        # reaches the caller instead of being folded into the generic fallback.
        from scripts.quota import check_budget
        check_budget(task="tone_shift")

        try:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            client = genai.Client(api_key=api_key)

            numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(group_texts))
            prompt = f"""คุณเป็นนักตัดต่อวิดีโอ TikTok มืออาชีพ กำลังพิจารณาว่าระหว่างช็อตแต่ละคู่ที่ติดกัน ควรใช้ hard cut ธรรมดา หรือ transition ที่แรงกว่า เพราะเนื้อหาเปลี่ยนโทน/หัวข้อจริง

รายการข้อความของแต่ละช็อต ({len(group_texts)} ช็อต) เรียงตามลำดับเวลา:
{numbered}

สำหรับแต่ละคู่ช็อตที่ติดกัน (มีทั้งหมด {expected_len} คู่) ให้จำแนกว่าการเปลี่ยนช็อตนั้นเป็น:
- "major" = เปลี่ยนหัวข้อ/โทนใหญ่จริง (เช่น จากปัญหา ไปเป็นทางแก้/สินค้า, จากเนื้อหา ไปเป็นการปิดการขาย)
- "minor" = แค่พักจังหวะ/เล่าเรื่องต่อเนื่องเดียวกัน
- "none" = ไม่มีการเปลี่ยนแปลงที่ชัดเจนเลย

ตอบเป็น JSON array ของ string เท่านั้น ความยาวต้องเป็น {expected_len} ตัวพอดี เรียงตามลำดับคู่ช็อต เช่น ["minor","major","none"]
"""

            models_to_try = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
            response = None
            for model_name in models_to_try:
                try:
                    response = client.models.generate_content(model=model_name, contents=[prompt])
                    if response and response.text:
                        break
                except Exception as err:
                    err_str = str(err)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        time.sleep(5)
                    continue

            if not response or not response.text:
                return []

            resp_text = response.text.strip()
            m = re.search(r"```json\s*([\s\S]*?)\s*```", resp_text)
            clean_json = m.group(1).strip() if m else resp_text
            m2 = re.search(r"\[[\s\S]*\]", clean_json)
            if m2:
                clean_json = m2.group(0)

            result = json.loads(clean_json)
            if not isinstance(result, list):
                return []
            result = [
                str(r).lower() if str(r).lower() in ("none", "minor", "major") else "none"
                for r in result
            ]

            if len(result) < expected_len:
                # A short response can't be reliably lined up with the real
                # boundaries -- trust the caller's own heuristic instead of
                # guessing which entries are missing.
                return []
            result = result[:expected_len]

        except Exception as e:
            print(f"   ⚠️ Tone-shift analysis skipped ({e}) — transitions stay heuristic-only.")
            return []

        cache[cache_key] = result
        cls._save_cache(cache)
        return result


if __name__ == "__main__":
    print("ScriptToneAnalyzer ready.")
