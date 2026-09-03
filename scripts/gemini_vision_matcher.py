"""
Gemini Vision Matcher
Uses Google AI Studio (Gemini 2.5 Flash) to watch raw footage and semantically match
every line of a marketing script to the exact visual action segment in the video.
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

from scripts.config import ASSETS_DIR

# Load .env if present
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

# Vision cache file to avoid re-uploading the same large video files
VISION_CACHE_FILE = ASSETS_DIR / ".vision_cache.json"

class GeminiVisionMatcher:
    """Matches script cues to raw video scene timestamps using Gemini 2.5 Flash Multimodal Vision."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if Gemini Vision is ready to use (requires GEMINI_API_KEY)."""
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())

    @staticmethod
    def _compute_file_hash(filepath: Path) -> str:
        """Calculate quick MD5 hash of first 8MB + file size for instant cache lookup."""
        hasher = hashlib.md5()
        hasher.update(str(filepath.stat().st_size).encode("utf-8"))
        with open(filepath, "rb") as f:
            chunk = f.read(8 * 1024 * 1024)
            hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def _load_cache(cls) -> Dict[str, Any]:
        if VISION_CACHE_FILE.exists():
            try:
                return json.loads(VISION_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_cache(cls, cache_data: Dict[str, Any]) -> None:
        try:
            VISION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            VISION_CACHE_FILE.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def get_or_upload_video(cls, client: Any, raw_video_path: str) -> Optional[Any]:
        """Uploads raw video to Google AI Studio Files API with local caching."""
        video_file = Path(raw_video_path).resolve()
        if not video_file.exists():
            return None

        file_hash = cls._compute_file_hash(video_file)
        cache = cls._load_cache()

        cached_file_name = cache.get(file_hash, {}).get("remote_file_name")
        if cached_file_name:
            try:
                remote_file = client.files.get(name=cached_file_name)
                if remote_file.state.name == "ACTIVE":
                    return remote_file
            except Exception:
                pass

        # Upload new file using clean ASCII display name to avoid Windows header issues
        print(f"   📤 Uploading raw footage to Google AI Studio Vision ({video_file.name})...")
        from google.genai import types
        with open(video_file, "rb") as f:
            uploaded = client.files.upload(
                file=f,
                config=types.UploadFileConfig(
                    display_name="raw_footage.mov",
                    mime_type="video/quicktime" if video_file.suffix.lower() == ".mov" else "video/mp4"
                )
            )

        # Wait for file processing
        retries = 0
        while uploaded.state.name == "PROCESSING" and retries < 40:
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)
            retries += 1

        if uploaded.state.name == "ACTIVE":
            cache[file_hash] = {
                "remote_file_name": uploaded.name,
                "local_path": str(video_file),
                "uploaded_at": time.time()
            }
            cls._save_cache(cache)
            return uploaded

        return None

    @classmethod
    def get_cached_matches(cls, raw_video_path: str, cues: List[Dict]) -> Optional[List[Dict]]:
        """Checks if scene matches exist in the local cache without calling any API or printing warnings."""
        try:
            file_hash = cls._compute_file_hash(Path(raw_video_path).resolve())
            cues_summary = "|".join([f"{c.get('text', '')}" for c in cues])
            match_cache_key = f"{file_hash}_{hashlib.md5(cues_summary.encode('utf-8')).hexdigest()}"
            cache = cls._load_cache()
            if "matches" in cache:
                if match_cache_key in cache["matches"]:
                    cached_matched = cache["matches"][match_cache_key]
                    if cached_matched and len(cached_matched) > 0:
                        return cached_matched
                if file_hash in cache["matches"]:
                    cached_matched = cache["matches"][file_hash]
                    if cached_matched and len(cached_matched) > 0:
                        return cached_matched
        except Exception:
            pass
        return None

    @classmethod
    def match_script_to_video(
        cls,
        raw_video_path: str,
        cues: List[Dict],
        raw_duration: float = 60.0
    ) -> List[Dict]:
        """
        Uses Gemini 2.5 Flash with Native Video Understanding to map each script cue
        to the best visual time slice in the raw video.
        """
        # Fast local cache check before calling API
        cached_matched = cls.get_cached_matches(raw_video_path, cues)
        if cached_matched:
            print(f"   ⚡ Reusing {len(cached_matched)} AI Vision matched shots from local cache!")
            return cached_matched

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            print("   ⚠️ No GEMINI_API_KEY found — using standard beat cuts.")
            return []

        file_hash = cls._compute_file_hash(Path(raw_video_path).resolve())
        cache = cls._load_cache()

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            remote_video = cls.get_or_upload_video(client, raw_video_path)
            if not remote_video:
                print("   ⚠️ Could not process video file for Vision — checking cached shots or using beat cuts.")
                # Fallback to any cached match for this video
                if "matches" in cache:
                    for k, v in cache["matches"].items():
                        if k.startswith(file_hash) and v:
                            print(f"   ♻️ Reusing previous scene map ({len(v)} shots) for this video!")
                            return v
                return []

            # Format cues for prompt
            lines_prompt = "\n".join([
                f"{idx+1}. [{c.get('start', 0.0):.2f}s - {c.get('end', 0.0):.2f}s] {c.get('text', '')}"
                for idx, c in enumerate(cues)
            ])

            prompt = f"""คุณเป็น AI ผู้กำกับและตัดต่อวิดีโอมืออาชีพสำหรับ TikTok Shop / Reels (ความยาววิดีโอดิบทั้งหมดประมาณ {raw_duration:.1f} วินาที)
กรุณาดูวิดีโอคลิปนี้อย่างละเอียด
และวิเคราะห์เลือกช่วงเวลา (start_time, end_time ในหน่วยวินาที) จากคลิปดิบ ที่มีภาพหรือการเคลื่อนไหวของมือ/สินค้า ที่ตรงกับความหมายของแต่ละท่อนในสคริปต์มากที่สุด

รายการสคริปต์ที่ต้องจับคู่ ({len(cues)} ท่อน):
{lines_prompt}

กติกาสำคัญ:
1. แต่ละท่อนให้เลือกช่วงเวลา (start_time, end_time) ที่มีแอ็กชันตรงกับประโยค เช่น ท่อนหมุนข้อต่อ ให้เลือกช่วงที่มือหมุนข้อต่อ, ท่อนเสียบชาร์จ ให้เลือกช่วงที่เสียบชาร์จ, ท่อนราคา/ปิดการขาย ให้เลือกช่วงโชว์สินค้าชัดเจน
2. start_time และ end_time ต้องอยู่ในช่วง 0 ถึง {raw_duration:.1f} วินาที และความยาวของแต่ละช่วงควรอยู่ที่ 1.5 - 4.0 วินาที
3. punch_zoom: กำหนดค่า 1.0 ถึง 1.35 เพื่อเพิ่มความตื่นเต้นในสไตล์ TikTok

ตอบกลับเป็น JSON format เท่านั้น:
```json
{{
  "matched_shots": [
    {{
      "cue_id": 1,
      "text": "ประโยคสคริปต์",
      "start_time": 0.0,
      "end_time": 3.0,
      "visual_reason": "สิ่งที่เห็นในภาพช่วงนี้ เช่น มือหยิบหัวสายชาร์จขึ้นมาโชว์",
      "punch_zoom": 1.15
    }}
  ]
}}
```
"""
            models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
            response = None
            last_err = None
            chosen_model = "gemini-2.5-flash"
            t_vision_start = time.time()

            for model_name in models_to_try:
                print(f"   👁️ Calling {model_name} Vision to analyze raw footage...")
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                remote_video,
                                prompt
                            ]
                        )
                        if response and response.text:
                            chosen_model = model_name
                            break
                    except Exception as err:
                        last_err = err
                        err_str = str(err)
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            print(f"   ⚠️ Rate Limit (429) hit on {model_name}. Retrying in 10s...")
                            time.sleep(10)
                        else:
                            time.sleep(2)
                if response and response.text:
                    break

            if not response or not response.text:
                # If API quota failed, check if any previous match exists for this video
                if "matches" in cache:
                    for k, v in cache["matches"].items():
                        if k.startswith(file_hash) and v:
                            print(f"   ♻️ Rate limit hit: Reusing previous video scene map ({len(v)} shots)!")
                            return v
                raise last_err or RuntimeError("No response from Gemini Vision models.")

            resp_text = response.text or ""
            # Extract JSON from markdown
            import re
            m = re.search(r"```json\s*([\s\S]*?)\s*```", resp_text)
            if m:
                clean_json = m.group(1).strip()
            else:
                clean_json = resp_text.strip()

            data = json.loads(clean_json)
            matched = data.get("matched_shots", [])
            print(f"   ✓ Gemini Vision successfully matched {len(matched)} visual scenes to the script!")
            for idx, m_shot in enumerate(matched[:3]):
                print(f"     • Shot {idx+1}: [{m_shot.get('start_time')}s-{m_shot.get('end_time')}s] ({m_shot.get('punch_zoom', 1.15)}x) -> {m_shot.get('visual_reason', '')[:50]}")

            # Save to persistent cache so future runs reuse immediately
            if "matches" not in cache:
                cache["matches"] = {}
            cache["matches"][match_cache_key] = matched
            cls._save_cache(cache)

            # Record token analytics
            try:
                from scripts.token_tracker import TokenTracker
                vid_tokens = int(raw_duration * 300)
                prompt_tokens = len(prompt) // 2
                out_tokens = max(50, len(resp_text) // 2)
                TokenTracker.record_event(
                    task="vision_match",
                    model=chosen_model,
                    provider="gemini_free_tier",
                    input_tokens=vid_tokens + prompt_tokens,
                    output_tokens=out_tokens,
                    latency_seconds=time.time() - t_vision_start,
                    project_name=Path(raw_video_path).stem,
                    metadata={"raw_duration_s": raw_duration, "matched_shots": len(matched)}
                )
            except Exception:
                pass

            return matched

        except Exception as e:
            print(f"   ⚠️ Gemini Vision Matcher error ({e}) — checking fallback.")
            if "matches" in cache:
                for k, v in cache["matches"].items():
                    if k.startswith(file_hash) and v:
                        print(f"   ♻️ Reusing previous scene map ({len(v)} shots) for this video!")
                        return v
            return []

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    test_video = "01_Raw/20260812_Esseger-สายชาร์จแม่เหล็ก/Video/esseger_สายชาร์จ_raw.mov"
    test_cues = [
        {"start": 0.0, "end": 2.6, "text": "ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา"},
        {"start": 3.0, "end": 4.8, "text": "ถ้ายังไม่เห็นตัวนี้"},
        {"start": 5.0, "end": 8.0, "text": "บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1"},
        {"start": 8.3, "end": 11.4, "text": "คือดูดแน่นมากกก ชาร์จไว 66W"},
        {"start": 11.6, "end": 14.4, "text": "แถมข้อต่อยังหมุนได้ 540 องศา"},
        {"start": 14.7, "end": 17.5, "text": "จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ"},
        {"start": 17.7, "end": 19.8, "text": "หมดปัญหาสายหักตรงคอ"},
        {"start": 20.0, "end": 22.4, "text": "เสียบในที่มืดได้สบายๆ เลยครับ"},
        {"start": 22.7, "end": 25.8, "text": "พิกัดราคาพิเศษวันนี้แค่ 149 บาท"},
        {"start": 26.2, "end": 28.3, "text": "กดในตะกร้าซ้ายล่างได้เลยครับ!"}
    ]

    res = GeminiVisionMatcher.match_script_to_video(test_video, test_cues, raw_duration=128.0)
    print("\nResult matched count:", len(res))
