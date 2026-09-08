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
import subprocess
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

# Bound on the generate_content() scene-matching call only (not on the client
# used for file upload+polling just above, which legitimately needs minutes
# for a large video and already bounds itself with its own retry/sleep loop
# -- see get_or_upload_video). 180s mirrors the "up to 3 minutes" precedent
# already used for file-processing wait on 3-5 minute footage.
VISION_GENERATE_TIMEOUT_SECONDS = 180

# The proxy the model actually sees. It only has to answer which seconds show
# what, and it samples about one frame a second, so resolution and frame rate
# buy nothing here -- see _vision_proxy for the measurements.
PROXY_WIDTH = 640
PROXY_FPS = 6
PROXY_CRF = 32

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
    def _vision_proxy(cls, video_file: Path, file_hash: str) -> Optional[Path]:
        """
        A small stand-in for the footage, for scene matching only.

        The source here is camera footage: measured on this project's own clip,
        1920x1080 at 60fps came to 241MB for 91 seconds, and uploading that is
        what a first-time scene match spends its minutes on -- around six
        minutes on a 5 Mbps upstream, which matched the ten minutes a 1-Click
        run was taking end to end.

        The model reads this to answer "which seconds of this footage show what
        the script is talking about", which needs neither the resolution nor the
        frame rate: it samples video at about one frame a second. Measured on
        that same clip, 640px wide at 6fps came to 3.7MB -- 66x smaller -- in
        21 seconds of local transcoding, so the upload drops from minutes to
        seconds even counting the transcode.

        Duration and timebase are untouched, so every timestamp the model
        returns still points at the same moment in the original.

        Cached beside the vision cache and keyed by the original's hash, so a
        second run skips the transcode too. Returns None if ffmpeg is missing or
        fails, and the caller then uploads the original.
        """
        proxy_dir = VISION_CACHE_FILE.parent / ".vision_proxies"
        proxy = proxy_dir / f"{file_hash}.mp4"
        if proxy.exists() and proxy.stat().st_size > 0:
            return proxy
        try:
            proxy_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_file),
                "-vf", f"scale={PROXY_WIDTH}:-2,fps={PROXY_FPS}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", str(PROXY_CRF),
                "-an", str(proxy),
            ], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            print(f"   ⚠️  ย่อไฟล์สำหรับ AI Vision ไม่ได้ ({exc}) — จะอัปไฟล์เต็ม")
            return None
        if not proxy.exists() or proxy.stat().st_size == 0:
            return None
        saved = video_file.stat().st_size / max(1, proxy.stat().st_size)
        print(f"   🗜️  ย่อไฟล์ให้ AI Vision: {proxy.stat().st_size / 1048576:.1f} MB "
              f"(เล็กลง {saved:.0f} เท่า) — อัปโหลดเร็วขึ้นมาก")
        return proxy

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

        # Send a small proxy rather than the camera original. The cache stays
        # keyed by the ORIGINAL's hash, so an already-uploaded clip is still
        # recognised and neither the transcode nor the upload happens twice.
        upload_file = cls._vision_proxy(video_file, file_hash) or video_file

        # Upload new file using clean ASCII display name to avoid Windows header issues
        print(f"   📤 Uploading footage to Google AI Studio Vision ({upload_file.name})...")
        from google.genai import types
        with open(upload_file, "rb") as f:
            uploaded = client.files.upload(
                file=f,
                config=types.UploadFileConfig(
                    display_name="raw_footage.mp4",
                    mime_type="video/quicktime" if upload_file.suffix.lower() == ".mov" else "video/mp4"
                )
            )

        # Wait for file processing (up to 3 minutes for 3-5 minute videos)
        retries = 0
        while uploaded.state.name == "PROCESSING" and retries < 90:
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
        # (see _exact_cached_match below for why the fallbacks match on the
        # full key rather than the file hash alone)
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
        except Exception:
            pass
        return None

    @staticmethod
    def _exact_cached_match(cache: Dict, match_cache_key: str) -> Optional[List[Dict]]:
        """The cached scene map for this exact video AND script, or None.

        The fallbacks below used to scan for any key starting with the file
        hash, which is the video half of `{file_hash}_{md5(cue text)}` -- so
        after a script edit they returned the shot list matched against the
        OLD lines: shots timed to text that is no longer there, and no sign
        anything was wrong. Rhythmic cuts are the better answer in that case.
        """
        entry = (cache or {}).get("matches", {}).get(match_cache_key)
        return entry if entry else None

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
        # Fast local cache check before calling API -- a cache hit costs
        # nothing and must never consume quota, so the budget check below
        # sits AFTER this, not before it.
        cached_matched = cls.get_cached_matches(raw_video_path, cues)
        if cached_matched:
            print(f"   ⚡ Reusing {len(cached_matched)} AI Vision matched shots from local cache!")
            return cached_matched

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            print("   ⚠️ No GEMINI_API_KEY found — using standard beat cuts.")
            return []

        # Pre-flight budget check -- only reached on a cache miss, and still
        # before the (expensive) video upload + generate_content call below.
        # Usage is recorded only after a successful match, around :344-ish.
        # Raises AppError(AI_QUOTA_EXCEEDED) if over budget; no-op if
        # unconfigured.
        from scripts.quota import check_budget
        check_budget(task="vision_match")

        file_hash = cls._compute_file_hash(Path(raw_video_path).resolve())
        cache = cls._load_cache()
        # Same derivation as get_cached_matches() above -- needed again here
        # (not just returned from that call) so a successful match can be
        # saved back into the persistent cache under the same key.
        cues_summary = "|".join([f"{c.get('text', '')}" for c in cues])
        match_cache_key = f"{file_hash}_{hashlib.md5(cues_summary.encode('utf-8')).hexdigest()}"

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            remote_video = cls.get_or_upload_video(client, raw_video_path)
            if not remote_video:
                print("   ⚠️ Could not process video file for Vision — checking cached shots or using beat cuts.")
                cached = cls._exact_cached_match(cache, match_cache_key)
                if cached:
                    print(f"   ♻️ Reusing the scene map for this exact script ({len(cached)} shots)!")
                    return cached
                return []

            # Format cues for prompt
            lines_prompt = "\n".join([
                f"{idx+1}. [{c.get('start', 0.0):.2f}s - {c.get('end', 0.0):.2f}s] {c.get('text', '')}"
                for idx, c in enumerate(cues)
            ])

            prompt = f"""คุณเป็น AI ผู้กำกับและตัดต่อวิดีโอมืออาชีพสำหรับ TikTok Shop / Reels (ความยาววิดีโอดิบทั้งหมดประมาณ {raw_duration:.1f} วินาที)
กรุณาดูวิดีโอคลิปนี้อย่างละเอียด
และวิเคราะห์เลือกช่วงเวลา (start_time, end_time ในหน่วยวินาที) จากคลิปดิบ ที่มีภาพหรือการเคลื่อนไหวของมือ/สินค้า ที่ตรงกับความหมายของแต่ละท่อนในสคริปต์มากที่สุด

รายการท่อนสคริปต์ (micro-cue รายคำ/วลี, {len(cues)} ท่อน) — ใช้เป็นข้อมูลจับเวลาพากย์เท่านั้น ไม่ใช่จำนวนช็อตที่ต้องตัด:
{lines_prompt}

กติกาสำคัญ:
1. อย่าตัดช็อตใหม่ทุกท่อน — ให้รวมท่อนที่ต่อเนื่องเป็นประโยค/ใจความเดียวกัน (ยังไม่จบด้วย . ! ? หรือคำลงท้ายอย่าง "ครับ"/"ค่ะ") เข้าเป็น 1 ช็อตเดียว ถ้าภาพช่วงนั้นยังสื่อความหมายเดิมต่อเนื่อง เพื่อให้จังหวะตัดไม่ถี่เกินไปจนดูรก
2. ตัดช็อตใหม่เฉพาะตอนที่ใจความเปลี่ยน (เปลี่ยนหัวข้อ/เปลี่ยนแอ็กชันที่ต้องโชว์) เช่น ท่อนหมุนข้อต่อ ให้เลือกช่วงที่มือหมุนข้อต่อ, ท่อนเสียบชาร์จ ให้เลือกช่วงที่เสียบชาร์จ, ท่อนราคา/ปิดการขาย ให้เลือกช่วงโชว์สินค้าชัดเจน
3. start_time และ end_time ต้องอยู่ในช่วง 0 ถึง {raw_duration:.1f} วินาที และความยาวของแต่ละช็อตควรอยู่ที่ 2.0 - 6.0 วินาที (สั้นกว่านี้จะถี่และรกเกินไป ยาวกว่านี้จะดูนิ่งน่าเบื่อ)
4. cue_ids ต้องเป็น array ของลำดับท่อน (จากเลข 1-{len(cues)} ด้านบน) ที่ช็อตนี้ครอบคลุม เรียงต่อเนื่องกันและไม่มีช่องว่างหรือซ้ำกับช็อตอื่น รวมกันแล้วต้องครบทุกท่อนทั้ง {len(cues)} ท่อน
5. punch_zoom: กำหนดค่า 1.0 ถึง 1.35 เพื่อเพิ่มความตื่นเต้นในสไตล์ TikTok — ใช้ค่าสูงกว่าตรงจุดเฉลย/จุดขายของสินค้า/CTA และค่าต่ำกว่าตรงช่วงเกริ่นนำธรรมดา

ตอบกลับเป็น JSON format เท่านั้น:
```json
{{
  "matched_shots": [
    {{
      "cue_ids": [1, 2],
      "text": "ข้อความรวมของท่อนที่ครอบคลุม",
      "start_time": 0.0,
      "end_time": 4.5,
      "visual_reason": "สิ่งที่เห็นในภาพช่วงนี้ เช่น มือหยิบหัวสายชาร์จขึ้นมาโชว์",
      "punch_zoom": 1.15
    }}
  ]
}}
```
"""
            models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
            response = None
            last_err = None
            chosen_model = "gemini-2.5-flash"
            t_vision_start = time.time()

            # Retry shape per model (bounded -- 2 attempts, short backoff, no
            # elaborate framework), matching scripts/ai_bridge.py's
            # classify_genai_error: rate_limit (429) backs off (retry-after
            # if the SDK gave one, else a default) and retries the SAME
            # model/request once before falling through to the next model;
            # transient (network/timeout) retries once with a short fixed
            # backoff; auth/other classifications stop retrying this model
            # immediately and move on (retrying an invalid key or an
            # unclassified failure on the same model cannot help). A quota
            # AppError can never reach here -- check_budget() above already
            # ran outside this try block and raises before this point.
            from scripts.ai_bridge import (
                classify_genai_error,
                _extract_retry_after_seconds,
                RATE_LIMIT_DEFAULT_BACKOFF_SECONDS,
                RATE_LIMIT_MAX_BACKOFF_SECONDS,
                TRANSIENT_BACKOFF_SECONDS,
            )

            for model_name in models_to_try:
                print(f"   👁️ Calling {model_name} Vision to analyze raw footage...")
                for attempt in range(2):
                    try:
                        from google.genai import types as genai_types
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                remote_video,
                                prompt
                            ],
                            config=genai_types.GenerateContentConfig(
                                http_options=genai_types.HttpOptions(
                                    timeout=VISION_GENERATE_TIMEOUT_SECONDS * 1000
                                )
                            ),
                        )
                        if response and response.text:
                            chosen_model = model_name
                            break
                    except Exception as err:
                        last_err = err
                        kind = classify_genai_error(err)
                        if kind == "rate_limit" and attempt == 0:
                            backoff = _extract_retry_after_seconds(err) or RATE_LIMIT_DEFAULT_BACKOFF_SECONDS
                            backoff = min(backoff, RATE_LIMIT_MAX_BACKOFF_SECONDS)
                            print(f"   ⚠️ Rate Limit (429) hit on {model_name}. Retrying same model in {backoff:.0f}s...")
                            time.sleep(backoff)
                            continue
                        if kind == "transient" and attempt == 0:
                            print(f"   ⚠️ Transient error on {model_name} ({err}). Retrying same model in {TRANSIENT_BACKOFF_SECONDS:.0f}s...")
                            time.sleep(TRANSIENT_BACKOFF_SECONDS)
                            continue
                        print(f"   ⚠️ {model_name} failed ({err}) — moving to next model fallback...")
                        break
                if response and response.text:
                    break

            if not response or not response.text:
                cached = cls._exact_cached_match(cache, match_cache_key)
                if cached:
                    print(f"   ♻️ Rate limit hit: reusing the scene map for this exact script ({len(cached)} shots)!")
                    return cached
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
            cached = cls._exact_cached_match(cache, match_cache_key)
            if cached:
                print(f"   ♻️ Reusing the scene map for this exact script ({len(cached)} shots)!")
                return cached
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
