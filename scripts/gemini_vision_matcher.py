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
import tempfile
from dataclasses import dataclass, replace as dataclass_replace
from pathlib import Path
from collections import Counter
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

# Matching confidence (roadmap M6). Catalog matches backed by a specific
# keyword/description hit are trusted; ones chosen on priors alone are not.
CATALOG_MATCH_CONFIDENCE = 0.85
CATALOG_LOW_CONFIDENCE = 0.35

# Folded into every scene-match cache key together with the shot-length range
# the prompt asks for. Bump it whenever the match prompt changes in a way that
# makes old answers wrong, so stale cached responses are never reused.
#   v1 (implicit: keys with no suffix): fixed 2-6 s shots in the prompt.
#   v2: the active style's min/max shot range is written into the prompt.
MATCH_PROMPT_VERSION = 2
# Narration seconds treated as the hook when the catalog picks scenes.
CATALOG_HOOK_WINDOW_SEC = 3.0
# Hero preference for an unmatched hook: moving product footage first, then
# a branded close-up. Static overviews are what a position guess produced.
HERO_ACTION_BONUS = {
    "turntable_spin": 4.0,
    "hands_on": 3.5,
    "feature_demo": 3.5,
    "port_connection": 3.0,
    "unboxing": 2.5,
    "closeup": 2.0,
}
HERO_KEYWORDS = ("โลโก้", "logo", "hero", "สกรีนชัดเจน", "ประณีต", "คมชัด")


def normalize_match_confidence(matched):
    """Clamp an optional ``confidence`` to 0..1; drop unusable values.

    Gemini may omit the field (older prompt, cached response) or send text.
    Absence stays absence -- callers read "no confidence" as unknown, never
    as low.
    """
    out = []
    for shot in matched if isinstance(matched, list) else []:
        if isinstance(shot, dict) and "confidence" in shot:
            shot = dict(shot)
            try:
                value = float(shot["confidence"])
                if value != value:  # NaN
                    raise ValueError
                if 10.0 <= value <= 100.0:
                    value = value / 100.0  # sent as a percentage
                shot["confidence"] = round(min(1.0, max(0.0, value)), 3)
            except (TypeError, ValueError):
                shot.pop("confidence", None)
        out.append(shot)
    return out
PROXY_FPS = 6
PROXY_CRF = 32


@dataclass
class VisionRequestContext:
    """One source/cache decision shared by the shot-matching and Vision seams."""

    video_file: Path
    file_hash: str
    cache: Dict[str, Any]
    match_cache_key: Optional[str] = None
    cached_matches: Optional[List[Dict]] = None


class GeminiVisionMatcher:
    """Matches script cues to raw video scene timestamps using Gemini 2.5 Flash Multimodal Vision."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if Gemini Vision is ready to use (requires GEMINI_API_KEY)."""
        from scripts.config import get_gemini_api_keys
        return len(get_gemini_api_keys()) > 0

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
        if not VISION_CACHE_FILE.exists():
            return {}
        try:
            return json.loads(VISION_CACHE_FILE.read_text(encoding="utf-8"))
        except ValueError:
            # Unparseable (JSONDecodeError / UnicodeDecodeError): keep the bad
            # file as a .corrupt backup so the next save cannot silently wipe
            # it, then start empty.
            cls._quarantine_corrupt_cache()
            return {}
        except Exception:
            # Transient read problem (locked file, etc.): leave it untouched.
            return {}

    @classmethod
    def _quarantine_corrupt_cache(cls) -> None:
        try:
            backup = VISION_CACHE_FILE.with_name(VISION_CACHE_FILE.name + ".corrupt")
            if backup.exists():
                backup = VISION_CACHE_FILE.with_name(
                    f"{VISION_CACHE_FILE.name}.{time.strftime('%Y%m%d_%H%M%S')}.corrupt"
                )
                counter = 1
                while backup.exists():
                    backup = VISION_CACHE_FILE.with_name(
                        f"{VISION_CACHE_FILE.name}.{time.strftime('%Y%m%d_%H%M%S')}_{counter}.corrupt"
                    )
                    counter += 1
            os.replace(VISION_CACHE_FILE, backup)
        except Exception:
            pass

    @classmethod
    def _save_cache(cls, cache_data: Dict[str, Any]) -> None:
        tmp_path: Optional[str] = None
        try:
            VISION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(cache_data, ensure_ascii=False, indent=2)
            # Atomic write: temp file in the same directory, then replace, so
            # a crash mid-write can never truncate the existing cache.
            fd, tmp_path = tempfile.mkstemp(
                prefix=VISION_CACHE_FILE.name + ".", suffix=".tmp", dir=str(VISION_CACHE_FILE.parent)
            )
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_path, VISION_CACHE_FILE)
            tmp_path = None
        except Exception:
            pass
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def resolve_shot_range(
        min_shot: Optional[float] = None, max_shot: Optional[float] = None
    ) -> tuple:
        """The (lo, hi) shot length the match prompt asks for.

        Missing values fall back to the config constants; a reversed range is
        swapped. Shared by the prompt and the cache key so they never drift.
        """
        from scripts.config import MAX_SHOT_DURATION, MIN_SHOT_DURATION
        shot_lo = float(min_shot) if min_shot else float(MIN_SHOT_DURATION)
        shot_hi = float(max_shot) if max_shot else float(MAX_SHOT_DURATION)
        if shot_hi < shot_lo:
            shot_lo, shot_hi = shot_hi, shot_lo
        return shot_lo, shot_hi

    @classmethod
    def match_cache_key(
        cls,
        file_hash: str,
        cues: List[Dict],
        min_shot: Optional[float] = None,
        max_shot: Optional[float] = None,
    ) -> str:
        """Scene-match cache key: video + cue text + prompt version + shot range.

        The range and MATCH_PROMPT_VERSION are part of the key because they
        are part of the prompt: an answer cached for a 2-6 s prompt must not
        be reused when the style now asks for 1.5-2.5 s shots.
        """
        cues_summary = "|".join(str(cue.get("text", "")) for cue in cues)
        cues_digest = hashlib.md5(cues_summary.encode("utf-8")).hexdigest()
        shot_lo, shot_hi = cls.resolve_shot_range(min_shot, max_shot)
        return f"{file_hash}_{cues_digest}_v{MATCH_PROMPT_VERSION}_{shot_lo:.2f}-{shot_hi:.2f}"

    @classmethod
    def _lookup_cached_matches(
        cls, cache: Dict[str, Any], file_hash: str, match_cache_key: str, cues: List[Dict]
    ) -> Optional[List[Dict]]:
        cached_matches = cls._exact_cached_match(cache, match_cache_key)
        if cached_matches:
            catalog = cache.get("catalogs", {}).get(file_hash) or {}
            if catalog.get("scenes") and all(
                isinstance(match, dict) and "scene_id" in match for match in cached_matches
            ):
                # Catalog scoring is local and cheap. Re-evaluate it
                # for the current cues/policy instead of freezing old
                # diversity-first choices (or old cue durations) in
                # the text-keyed match cache. Direct Vision matches
                # without catalog scene IDs keep their cache behavior.
                catalog_end = max(float(scene.get("end", 0)) for scene in catalog["scenes"])
                cached_matches = cls.match_script_with_catalog(catalog, cues, raw_duration=catalog_end)
            cached_matches = cls._bind_catalog_windows(cached_matches, catalog)
        return cached_matches

    @classmethod
    def prepare_request_context(
        cls,
        raw_video_path: str,
        cues: Optional[List[Dict]] = None,
        min_shot: Optional[float] = None,
        max_shot: Optional[float] = None,
    ) -> Optional[VisionRequestContext]:
        """Read source identity and the local Vision cache once for one job.

        Pass the same ``min_shot`` / ``max_shot`` that ``match_script_to_video``
        will get; the match cache is keyed by that range.
        """
        try:
            video_file = Path(raw_video_path).resolve()
            if not video_file.exists():
                return None
            file_hash = cls._compute_file_hash(video_file)
            cache = cls._load_cache()
            match_cache_key = None
            cached_matches = None
            if cues is not None:
                match_cache_key = cls.match_cache_key(file_hash, cues, min_shot, max_shot)
                cached_matches = cls._lookup_cached_matches(cache, file_hash, match_cache_key, cues)
            return VisionRequestContext(
                video_file=video_file,
                file_hash=file_hash,
                cache=cache,
                match_cache_key=match_cache_key,
                cached_matches=cached_matches,
            )
        except Exception:
            return None

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
        context = cls.prepare_request_context(raw_video_path)
        if context is None:
            return None

        return cls._get_or_upload_context(client, context)

    @classmethod
    def _get_or_upload_context(cls, client: Any, context: VisionRequestContext) -> Optional[Any]:
        """Upload using an already-prepared request context; never rehash/reload."""
        video_file = context.video_file
        file_hash = context.file_hash
        cache = context.cache

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

    @staticmethod
    def _bind_catalog_windows(matches, catalog):
        scenes = {scene.get("id"): scene for scene in catalog.get("scenes", []) if isinstance(scene, dict)}
        bounded = []
        for match in matches:
            scene = scenes.get(match.get("scene_id")) if isinstance(match, dict) else None
            if not scene:
                bounded.append(match)
                continue
            try:
                first, stop = float(scene["start"]), float(scene["end"])
                if stop - first < 1 / 30:
                    bounded.append(match)
                    continue
                start = max(first, min(float(match.get("start_time", first)), stop - 1 / 30))
                end = min(stop, float(match.get("end_time", stop)))
                if end <= start:
                    start, end = first, stop
                bounded.append({**match, "start_time": start, "end_time": end,
                                "scene_start": first, "scene_end": stop})
            except (TypeError, ValueError, KeyError):
                bounded.append(match)
        return bounded

    @classmethod
    def get_cached_matches(
        cls,
        raw_video_path: str,
        cues: List[Dict],
        min_shot: Optional[float] = None,
        max_shot: Optional[float] = None,
    ) -> Optional[List[Dict]]:
        """Checks if scene matches exist in the local cache without calling any API or printing warnings."""
        context = cls.prepare_request_context(raw_video_path, cues, min_shot=min_shot, max_shot=max_shot)
        return context.cached_matches if context else None

    @classmethod
    def get_cached_catalog(
        cls, raw_video_path: str, request_context: Optional[VisionRequestContext] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves cached Scene Catalog for a raw video by file hash if available."""
        try:
            if request_context is not None:
                cache = request_context.cache
                file_hash = request_context.file_hash
            else:
                video_file = Path(raw_video_path).resolve()
                if not video_file.exists():
                    return None
                file_hash = cls._compute_file_hash(video_file)
                cache = cls._load_cache()
            catalog = cache.get("catalogs", {}).get(file_hash)
            if catalog and isinstance(catalog, dict) and catalog.get("scenes"):
                return catalog
        except Exception:
            pass
        return None

    @classmethod
    def save_cached_catalog(cls, file_hash: str, catalog: Dict[str, Any]) -> None:
        """Persists a Scene Catalog to .vision_cache.json under 'catalogs'."""
        try:
            cache = cls._load_cache()
            if "catalogs" not in cache:
                cache["catalogs"] = {}
            cache["catalogs"][file_hash] = catalog
            cls._save_cache(cache)
        except Exception:
            pass

    @classmethod
    def match_script_with_catalog(
        cls,
        catalog: Dict[str, Any],
        cues: List[Dict],
        raw_duration: float = 60.0,
        apply_sweet_spot: bool = True,
    ) -> List[Dict]:
        """
        Maps script cues to scenes in an indexed Scene Catalog with zero API calls.
        Features:
        - Group cues into logical sentence/thought units (2.0s - 5.0s).
        - Semantic and keyword relevance scoring (Thai/English product & action terms).
        - Dynamic visual variety for turntable / 360 spin footage (rotates angle phases and punch zooms).
        - Anti-duplicate lock: avoids consecutive identical scenes or start times < 2.0s apart.
        """
        scenes = catalog.get("scenes") or []
        if not scenes:
            return []

        is_spin = bool(catalog.get("is_spin_footage", False))
        total_cues = len(cues)
        if total_cues == 0:
            return []

        # 1. Group consecutive micro-cues into natural sentence/thought units
        sentence_enders = (".", "!", "?", "ครับ", "ค่ะ", "นะคะ", "นะครับ", "เลยครับ", "เลยค่ะ", "จ้า")
        groups: List[List[int]] = []
        cur_group: List[int] = []
        cur_dur = 0.0

        for idx, cue in enumerate(cues):
            c_start = float(cue.get("start", 0.0))
            c_end = float(cue.get("end", c_start + 1.0))
            dur = max(0.2, c_end - c_start)
            cur_group.append(idx)
            cur_dur += dur
            text = str(cue.get("text", "")).strip()

            is_end = (
                text.endswith(sentence_enders)
                or cur_dur >= 4.0
                or idx == total_cues - 1
            )
            if is_end and cur_dur >= 1.8:
                groups.append(cur_group)
                cur_group = []
                cur_dur = 0.0

        if cur_group:
            if groups and cur_dur < 1.5:
                groups[-1].extend(cur_group)
            else:
                groups.append(cur_group)

        if not groups:
            groups = [[i] for i in range(total_cues)]

        # 2. Domain keyword matching dictionary
        domain_patterns = {
            "unboxing": ("กล่อง", "แกะ", "แพ็กเกจ", "แถม", "ซอง", "อุปกรณ์ในกล่อง", "package", "box"),
            "port_connection": ("ชาร์จ", "เสียบ", "พอร์ต", "usb", "type-c", "ยูเอสบี", "ยูเอสบีซี", "ไทป์ซี", "ไว", "วัตต์", "watt", "66w", "fast", "สายชาร์จ", "หัวเสียบ", "หัวชาร์จ"),
            "anti_tangle_magnet": ("แม่เหล็ก", "ไม่พันกัน", "ประกบ", "กันสายพัน", "จัดเก็บ", "สายแบน", "เก็บง่าย", "tangle", "magnet"),
            "controls_mic": ("ปุ่ม", "รีโมท", "เพิ่มเสียง", "ลดเสียง", "ไมค์", "ไมโครโฟน", "คุยสาย", "สนทนา", "รับสาย", "ปรับระดับ"),
            "sound_driver": ("เสียง", "เบส", "hi-res", "มิติ", "แบนราบ", "สะใจ", "ใส", "คมชัด", "นุ่มลึก", "ไดร์เวอร์", "pure bass"),
            "turntable_spin": ("หมุน", "ข้อต่อ", "360", "540", "องศา", "ปรับ", "ทิศทาง", "รอบทิศ", "spin"),
            "closeup": ("ไฟ", "จอ", "แสดง", "หน้าจอ", "สถานะ", "เตือน", "ไฟกระพริบ", "ชัดๆ", "close", "โลโก้", "งานประกอบ", "บอดี้"),
            "hands_on": ("ทน", "หัก", "งอ", "จับ", "ถนัด", "มือ", "เกม", "นอน", "ดึง", "เหนียว", "วัสดุ", "น้ำหนัก"),
            "cta_showcase": ("ราคา", "บาท", "โปร", "คุ้ม", "พิกัด", "ตะกร้า", "สั่ง", "กด", "จิ้ม", "ลด", "พิเศษ", "ด่วน")
        }

        generic_kws = {"สินค้า", "ตัวเครื่อง", "ของ", "ตัวนี้", "รุ่นนี้", "สาย", "หูฟัง", "jbl"}
        broad_quality_words = {"คมชัด", "ใส"}

        angle_cycle = ["front", "45deg", "side", "macro_closeup", "back"]
        zoom_cycle = [1.10, 1.20, 1.12, 1.25, 1.15]

        matched_shots: List[Dict] = []
        prev_scene_id = None
        prev_start_time = -10.0
        prev_angle_phase = None
        prev_action_type = None
        used_scene_counts: Counter[Any] = Counter()
        used_start_times: List[float] = []
        consumed_scene_until = {}

        for g_idx, group_indices in enumerate(groups):
            group_cues = [cues[i] for i in group_indices]
            group_text = " ".join(str(c.get("text", "")).strip() for c in group_cues)
            group_cue_ids = [i + 1 for i in group_indices]  # 1-based indexing

            needed_dur = float(group_cues[-1].get("end", 0.0)) - float(group_cues[0].get("start", 0.0))
            needed_dur = max(2.0, min(6.0, needed_dur))

            progress = g_idx / max(1, len(groups) - 1)  # 0.0 = hook/start, 1.0 = CTA/end

            # Score each catalog scene against this group
            scored_scenes = []
            for scene in scenes:
                s_id = scene.get("id", 0)
                s_type = scene.get("action_type", "overview")
                s_angle = scene.get("angle_phase", "front")
                s_desc = scene.get("description", "")
                s_keywords = scene.get("keywords", [])
                s_start = float(scene.get("start", 0.0))
                score = 1.0
                evidence = set()

                # Priority bonus for scenes not yet used in this video
                if s_id not in used_scene_counts and len(used_scene_counts) < len(scenes):
                    score += 3.5

                # Check exact scene keywords against cue text
                for kw in s_keywords:
                    kw_clean = str(kw).strip().lower()
                    if not kw_clean:
                        continue
                    if kw_clean in generic_kws:
                        if kw_clean in group_text.lower():
                            score += 0.8
                    else:
                        if kw_clean in group_text.lower():
                            score += 5.0
                            if kw_clean not in broad_quality_words:
                                evidence.add(kw_clean)

                # Check domain pattern match
                for pat_type, words in domain_patterns.items():
                    matched_words = [w for w in words if w in group_text.lower()]
                    if matched_words:
                        # Generic product names and broad action fragments
                        # cannot lock a scene to a feature. Specific metadata
                        # evidence takes precedence over visual variety.
                        evidence.update(w for w in matched_words if w in s_desc.lower()
                                        and w not in generic_kws
                                        and w not in broad_quality_words
                                        and w not in {"ไว", "fast", "ปรับ", "มือ", "close"})
                        if pat_type == "anti_tangle_magnet":
                            if any(w in s_desc.lower() for w in ("แม่เหล็ก", "ประกบ", "พัน", "สายแบน", "จัดเก็บ")):
                                score += 6.0
                            elif s_type in ("feature_demo", "hands_on"):
                                score += 3.0
                        elif pat_type == "controls_mic":
                            if any(w in s_desc.lower() for w in ("ปุ่ม", "รีโมท", "ไมค์", "เพิ่มลด")):
                                score += 6.0
                            elif s_type in ("feature_demo", "closeup"):
                                score += 3.0
                        elif pat_type == "sound_driver":
                            if any(w in s_desc.lower() for w in ("จุก", "อินเอียร์", "เสียง", "บอดี้", "ลำโพง", "ไดร์เวอร์", "หูฟัง")):
                                score += 4.5
                        elif s_type == pat_type:
                            score += 4.5
                        elif any(w in s_desc.lower() for w in matched_words):
                            score += 3.0

                # Narrative stage priors
                if progress < 0.25:  # Hook / Intro
                    if s_type in ("overview", "unboxing", "hands_on", "closeup"):
                        score += 2.5

                # Hook / Cover Hero Priority (Shot 1 / Beat 1)
                # Video opening and thumbnail cover need the sharpest hero shot with clear branding/logo
                if g_idx == 0 or progress < 0.15:
                    if s_angle == "macro_closeup" or s_type == "closeup":
                        if any(k in s_desc.lower() for k in ("สกรีนชัดเจน", "ประณีต", "ซูมเน้น", "คมชัด", "โลโก้")) or any(k in str(kw).lower() for kw in s_keywords for k in ("สกรีนชัดเจน", "โลโก้", "logo", "hero")):
                            score += 4.5
                    if "ฝ่ามือ" in s_desc:
                        score -= 2.5

                if progress > 0.75:  # CTA / Closer
                    if s_type in ("cta_showcase", "overview", "turntable_spin"):
                        score += 3.0
                elif progress >= 0.25:  # Middle features
                    if s_type in ("feature_demo", "closeup", "port_connection", "hands_on"):
                        score += 2.0

                # Turntable angle diversity
                target_angle = angle_cycle[g_idx % len(angle_cycle)]
                if is_spin or all(s.get("action_type") == "turntable_spin" for s in scenes):
                    if s_angle == target_angle:
                        score += 3.0

                # Visual Contrast & Anti-Jump-Cut:
                # Avoid consecutive identical angles/action types, encourage complementary visual variety
                if prev_angle_phase:
                    # Avoid back-to-back macro close-ups (visual fatigue & jump cut)
                    if prev_angle_phase == "macro_closeup" and s_angle == "macro_closeup":
                        score -= 4.0
                    # Contrast bonus when switching from close-up to broader action/front
                    elif prev_angle_phase == "macro_closeup" and s_angle in ("front", "45deg", "top") and s_type in ("hands_on", "feature_demo", "overview"):
                        score += 3.0
                    # Avoid consecutive identical camera angles when catalog has diverse angles
                    elif s_angle == prev_angle_phase and len(scenes) >= 3 and not is_spin:
                        score -= 2.5

                # Anti-duplicate lock:
                # 1. Heavy penalty for immediately consecutive repeat
                if len(scenes) > 1 and s_id == prev_scene_id:
                    score -= 12.0

                # 2. Cumulative penalty for already used scenes across the video
                if used_scene_counts[s_id] > 0:
                    score -= 6.0 * used_scene_counts[s_id]

                # 3. Proximity distance penalty
                if abs(s_start - prev_start_time) < 2.0:
                    score -= 5.0
                if any(abs(s_start - pst) < 1.5 for pst in used_start_times):
                    score -= 3.0

                scored_scenes.append((score, scene, evidence))

            relevant = [candidate for candidate in scored_scenes if candidate[2]]
            hero_fallback = False
            if relevant:
                scored_scenes = relevant
            elif float(group_cues[0].get("start", 0.0)) < CATALOG_HOOK_WINDOW_SEC:
                # M6: nothing in the hook matched a keyword -- open on the
                # moving / branded hero footage instead of the scene the
                # positional priors happen to favour.
                def _hero_bonus(scene):
                    desc = str(scene.get("description", "")).lower()
                    kws = " ".join(str(k).lower() for k in scene.get("keywords", []) or [])
                    bonus = HERO_ACTION_BONUS.get(scene.get("action_type", ""), 0.0)
                    if any(k in desc or k in kws for k in HERO_KEYWORDS):
                        bonus += 2.0
                    return bonus

                scored_scenes = [(score + _hero_bonus(scene), scene, evidence) for score, scene, evidence in scored_scenes]
                hero_fallback = True
            scored_scenes.sort(key=lambda x: x[0], reverse=True)
            best_scene = scored_scenes[0][1]
            match_confidence = CATALOG_MATCH_CONFIDENCE if scored_scenes[0][2] else CATALOG_LOW_CONFIDENCE

            orig_start = float(best_scene.get("start", 0.0))
            orig_end = float(best_scene.get("end", orig_start + needed_dur))
            scene_len = max(0.1, orig_end - orig_start)
            excess_dur = scene_len - needed_dur

            sweet_offset = 0.0
            s_action = best_scene.get("action_type", "")
            s_id = best_scene.get("id")

            if apply_sweet_spot and excess_dur >= 1.0:
                # 1. Scene Sweet-Spot Offset:
                # Skip initial dead air / camera-shake / autofocus hunt / hand entry at scene start
                if s_action in ("closeup", "hands_on", "feature_demo", "overview", "cta_showcase"):
                    sweet_offset = min(1.2, max(0.6, excess_dur * 0.35))
                elif s_action in ("turntable_spin",):
                    sweet_offset = min(0.8, max(0.4, excess_dur * 0.25))
                elif s_action in ("port_connection", "unboxing"):
                    sweet_offset = min(0.5, max(0.2, excess_dur * 0.15))
                else:
                    sweet_offset = min(0.8, max(0.4, excess_dur * 0.25))

            # Advance by consumed footage, never by reuse_count * current duration.
            # The stage refines this against the final beat/J-lead shot spans.
            scene_key = (s_id, orig_start, orig_end)
            consumed_until = consumed_scene_until.get(scene_key)
            requested_start = consumed_until if consumed_until is not None else orig_start + sweet_offset
            s_start = max(orig_start, min(requested_start, orig_end - 1 / 30))
            s_end = min(raw_duration, orig_end)
            consumed_scene_until[scene_key] = min(s_end, requested_start + needed_dur)

            # Dynamic punch zoom
            base_zoom = float(best_scene.get("punch_zoom", 1.15))
            cyclic_zoom = zoom_cycle[g_idx % len(zoom_cycle)]
            if progress > 0.8:
                zoom = max(1.18, min(1.30, base_zoom + 0.05))
            else:
                zoom = cyclic_zoom if is_spin else base_zoom

            used_scene_counts[best_scene.get("id")] += 1
            prev_scene_id = best_scene.get("id")
            prev_start_time = s_start
            prev_angle_phase = best_scene.get("angle_phase")
            prev_action_type = best_scene.get("action_type")
            used_start_times.append(s_start)

            matched_shots.append({
                "cue_ids": group_cue_ids,
                "text": group_text,
                "scene_id": best_scene.get("id"),
                "scene_start": round(orig_start, 2),
                "scene_end": orig_end,
                "start_time": s_start,
                "end_time": round(s_end, 2),
                **({"consumed_source_until": consumed_until} if consumed_until is not None else {}),
                "visual_reason": f"จับคู่ฉาก {best_scene.get('action_type', 'scene')} ({best_scene.get('angle_phase', 'normal')}): {best_scene.get('description', '')[:45]}",
                "punch_zoom": round(zoom, 2),
                "selection_evidence": sorted(scored_scenes[0][2]),
                "confidence": match_confidence,
                **({"hero_fallback": True} if hero_fallback else {}),
            })

        return matched_shots

    @classmethod
    def index_raw_video_catalog(
        cls,
        raw_video_path: str,
        raw_duration: float = 60.0,
        request_context: Optional[VisionRequestContext] = None,
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Indexes raw footage once into a structured Scene Catalog using Gemini Vision.
        Stores result in .vision_cache.json under 'catalogs'.
        Once indexed, any script can be matched instantly with 0 API calls.
        """
        video_file = Path(raw_video_path).resolve()
        if not video_file.exists():
            return None

        file_hash = cls._compute_file_hash(video_file)
        if not force:
            cached_cat = cls.get_cached_catalog(raw_video_path, request_context=request_context)
            if cached_cat:
                return cached_cat

        from scripts.config import get_gemini_api_keys
        api_keys = get_gemini_api_keys()
        if not api_keys:
            return cls._generate_heuristic_catalog(raw_duration)

        from scripts.quota import check_budget
        check_budget(task="vision_catalog")

        catalog_prompt = f"""คุณเป็น AI ผู้กำกับและตัดต่อวิดีโอมืออาชีพสำหรับ TikTok Shop / Reels (ความยาววิดีโอดิบทั้งหมดประมาณ {raw_duration:.1f} วินาที)
กรุณาดูวิดีโอคลิปนี้อย่างละเอียด และวิเคราะห์แบ่งคลิปออกเป็น "สารบัญฉาก (Scene Catalog)" อย่างเป็นระบบ เพื่อนำไปจับคู่ตัดต่อกับสคริปต์การตลาด

ให้วิเคราะห์และระบุ:
1. is_spin_footage (boolean): วิดีโอนี้เป็นคลิปโชว์สินค้าหมุนรอบตัว (360 Turntable / หมุนโชว์ซ้ายขวา) หรือไม่
2. summary: สรุปภาพรวมของคลิปดิบนี้ (เช่น โชว์สินค้าหมุนรอบตัว, มีจังหวะแกะกล่อง, โชว์เสียบสายชาร์จ ฯลฯ)
3. scenes: แบ่งช่วงเวลาของคลิปดิบออกเป็นฉากๆ (ความยาวช่วงละประมาณ 2.5 - 8.0 วินาที ให้ครอบคลุมทั้งคลิปตั้งแต่ 0.0s ถึง {raw_duration:.1f}s) โดยในแต่ละฉากให้ระบุ:
   - id: ลำดับฉาก (ตัวเลข 1, 2, 3...)
   - start: เวลาเริ่มต้น (วินาที)
   - end: เวลาสิ้นสุด (วินาที)
   - action_type: ชนิดของฉาก (เลือกหนึ่งในนี้: "overview", "unboxing", "feature_demo", "hands_on", "closeup", "port_connection", "turntable_spin", "cta_showcase")
   - angle_phase: มุมกล้องหรือองศาของสินค้า (เช่น "front", "side", "back", "top", "45deg", "macro_closeup")
   - description: บรรยายภาพที่เห็นอย่างละเอียด (เช่น มือหยิบสินค้าขึ้นมา, เสียบสายชาร์จเข้ามือถือ, หมุนข้อต่อโชว์ 360 องศา, โชว์กล่องและอุปกรณ์ที่แถม, โชว์โลโก้แบรนด์คมชัดระยะประชิด)
   - keywords: คำสำคัญของภาพในฉากนี้ สำหรับจับคู่กับคำในสคริปต์ (เช่น ["หมุน", "ข้อต่อ", "360"], ["สายชาร์จ", "เสียบ", "พอร์ต Type-C"], ["กล่อง", "แพ็กเกจ", "แกะ"], ["หน้าจอ", "ไฟแสดงผล"], ["โลโก้", "สกรีนชัดเจน", "บอดี้"], ["ราคา", "โปร", "ส่วนลด"])
   - punch_zoom: แนะนำระยะซูมไดนามิกสำหรับ TikTok (1.05 ถึง 1.30)

ตอบกลับเป็น JSON format เท่านั้น:
```json
{{
  "is_spin_footage": true,
  "summary": "...",
  "scenes": [
    {{
      "id": 1,
      "start": 0.0,
      "end": 6.5,
      "action_type": "overview",
      "angle_phase": "front",
      "description": "...",
      "keywords": ["..."],
      "punch_zoom": 1.10
    }}
  ]
}}
```
"""
        models_to_try = [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash",
        ]

        from google import genai
        from google.genai import types as genai_types
        from scripts.ai_bridge import (
            classify_genai_error,
            _extract_retry_after_seconds,
            RATE_LIMIT_DEFAULT_BACKOFF_SECONDS,
            RATE_LIMIT_MAX_BACKOFF_SECONDS,
            TRANSIENT_BACKOFF_SECONDS,
        )

        response = None
        chosen_model = "gemini-3.6-flash"
        t_start = time.time()

        for key_idx, cur_key in enumerate(api_keys, 1):
            key_tag = f"Key #{key_idx} (..{cur_key[-6:]})"
            try:
                client = genai.Client(api_key=cur_key)
                remote_video = (
                    cls._get_or_upload_context(client, request_context)
                    if request_context is not None
                    else cls.get_or_upload_video(client, raw_video_path)
                )
            except Exception as upload_err:
                print(f"   ⚠️ [Catalog Index] Failed upload on {key_tag} ({upload_err})")
                continue

            if not remote_video:
                continue

            key_rate_limited = False
            for model_name in models_to_try:
                print(f"   👁️ [Catalog Index] Calling {model_name} on {key_tag} to index scenes...")
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[remote_video, catalog_prompt],
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
                        kind = classify_genai_error(err)
                        if kind == "rate_limit":
                            key_rate_limited = True
                            if attempt == 0:
                                backoff = _extract_retry_after_seconds(err) or RATE_LIMIT_DEFAULT_BACKOFF_SECONDS
                                backoff = min(backoff, RATE_LIMIT_MAX_BACKOFF_SECONDS)
                                time.sleep(backoff)
                                continue
                            break
                        if kind == "transient" and attempt == 0:
                            time.sleep(TRANSIENT_BACKOFF_SECONDS)
                            continue
                        break

                if response and response.text:
                    break
                if key_rate_limited:
                    break

            if response and response.text:
                break

        if not response or not response.text:
            return cls._generate_heuristic_catalog(raw_duration)

        resp_text = response.text or ""
        import re
        m = re.search(r"```json\s*([\s\S]*?)\s*```", resp_text)
        clean_json = m.group(1).strip() if m else resp_text.strip()

        try:
            cat_data = json.loads(clean_json)
            scenes = cat_data.get("scenes")
            if not isinstance(scenes, list) or len(scenes) == 0:
                return cls._generate_heuristic_catalog(raw_duration)

            catalog = {
                "raw_file": str(video_file),
                "duration": float(raw_duration),
                "is_spin_footage": bool(cat_data.get("is_spin_footage", False)),
                "summary": str(cat_data.get("summary", "")),
                "scenes": scenes,
                "indexed_at": time.time(),
                "indexed_by": chosen_model,
            }
            cls.save_cached_catalog(file_hash, catalog)
            print(f"   ✓ [Scene Catalog] Indexed {len(scenes)} scenes for {video_file.name} ({catalog['summary'][:60]})")

            try:
                from scripts.token_tracker import TokenTracker
                TokenTracker.record_event(
                    task="vision_catalog",
                    model=chosen_model,
                    provider="gemini_free_tier",
                    input_tokens=int(raw_duration * 300) + len(catalog_prompt) // 2,
                    output_tokens=max(100, len(resp_text) // 2),
                    latency_seconds=time.time() - t_start,
                    project_name=video_file.stem,
                    metadata={"scenes_count": len(scenes), "is_spin": catalog["is_spin_footage"]},
                )
            except Exception:
                pass

            return catalog
        except Exception:
            return cls._generate_heuristic_catalog(raw_duration)

    @classmethod
    def _generate_heuristic_catalog(cls, raw_duration: float = 60.0) -> Dict[str, Any]:
        """Fallback smart heuristic scene catalog if offline or API unavailable."""
        scene_dur = 5.0
        num_scenes = max(3, int(raw_duration / scene_dur))
        scenes = []
        action_types = ["overview", "unboxing", "feature_demo", "hands_on", "closeup", "port_connection", "turntable_spin", "cta_showcase"]
        angle_phases = ["front", "45deg", "side", "macro_closeup", "back"]

        for idx in range(num_scenes):
            s_start = idx * scene_dur
            s_end = min(raw_duration, (idx + 1) * scene_dur)
            a_type = action_types[idx % len(action_types)]
            a_phase = angle_phases[idx % len(angle_phases)]
            scenes.append({
                "id": idx + 1,
                "start": round(s_start, 2),
                "end": round(s_end, 2),
                "action_type": a_type,
                "angle_phase": a_phase,
                "description": f"ฉากที่ {idx+1}: โชว์สินค้ามุม {a_phase} ({a_type})",
                "keywords": ["สินค้า", "ตัวเครื่อง", "โชว์", a_phase],
                "punch_zoom": 1.10 + (0.05 * (idx % 3)),
            })

        return {
            "duration": raw_duration,
            "is_spin_footage": False,
            "summary": "สารบัญฉากอัตโนมัติแบบแบ่งช่วงเวลาครอบคลุมทั้งคลิป",
            "scenes": scenes,
            "indexed_at": time.time(),
            "indexed_by": "heuristic_fallback",
        }

    @staticmethod
    def _exact_cached_match(cache: Dict, match_cache_key: str) -> Optional[List[Dict]]:
        """The cached scene map for this exact video AND script, or None."""
        entry = (cache or {}).get("matches", {}).get(match_cache_key)
        return entry if entry else None

    @classmethod
    def match_script_to_video(
        cls,
        raw_video_path: str,
        cues: List[Dict],
        raw_duration: float = 60.0,
        request_context: Optional[VisionRequestContext] = None,
        min_shot: Optional[float] = None,
        max_shot: Optional[float] = None,
    ) -> List[Dict]:
        """
        Uses Gemini 2.5 Flash with Native Video Understanding to map each script cue
        to the best visual time slice in the raw video.

        ``min_shot`` / ``max_shot`` are the active style's shot range; the
        prompt asks for shots inside it (default: the config constants).
        """
        # The match cache is keyed by the shot range the prompt asks for. A
        # context prepared without that range (or for another one) is re-keyed
        # here so an answer cached under a different prompt is never reused.
        if request_context is not None:
            range_key = cls.match_cache_key(request_context.file_hash, cues, min_shot, max_shot)
            if request_context.match_cache_key != range_key:
                request_context = dataclass_replace(
                    request_context,
                    match_cache_key=range_key,
                    cached_matches=cls._lookup_cached_matches(
                        request_context.cache, request_context.file_hash, range_key, cues
                    ),
                )

        # Fast local cache check before calling API -- a cache hit costs
        # nothing and must never consume quota, so the budget check below
        # sits AFTER this, not before it.
        if request_context is not None:
            cached_matched = request_context.cached_matches
        elif min_shot is None and max_shot is None:
            # Same key as passing None explicitly; kept positional-only so
            # existing two-argument stubs of get_cached_matches still fit.
            cached_matched = cls.get_cached_matches(raw_video_path, cues)
        else:
            cached_matched = cls.get_cached_matches(raw_video_path, cues, min_shot=min_shot, max_shot=max_shot)
        if cached_matched:
            print(f"   ⚡ Reusing {len(cached_matched)} AI Vision matched shots from local cache!")
            return cached_matched

        # Check Scene Catalog cache -- if the raw video has been indexed,
        # map any script to it instantly (0 API calls, 0 quota used).
        catalog = cls.get_cached_catalog(raw_video_path, request_context=request_context)
        if catalog and catalog.get("scenes"):
            matched = cls.match_script_with_catalog(catalog, cues, raw_duration=raw_duration)
            if matched:
                print(f"   ⚡ Reusing Scene Catalog ({len(catalog['scenes'])} scenes) — instant semantic matching!")
                if request_context is not None:
                    cache = request_context.cache
                    match_cache_key = request_context.match_cache_key
                else:
                    video_file = Path(raw_video_path).resolve()
                    file_hash = cls._compute_file_hash(video_file)
                    cache = cls._load_cache()
                    match_cache_key = cls.match_cache_key(file_hash, cues, min_shot, max_shot)
                if "matches" not in cache:
                    cache["matches"] = {}
                if match_cache_key:
                    cache["matches"][match_cache_key] = matched
                    cls._save_cache(cache)
                return matched

        from scripts.config import get_gemini_api_keys
        api_keys = get_gemini_api_keys()
        api_key = api_keys[0] if api_keys else ""
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

        if request_context is not None:
            file_hash = request_context.file_hash
            cache = request_context.cache
            match_cache_key = request_context.match_cache_key
        else:
            file_hash = cls._compute_file_hash(Path(raw_video_path).resolve())
            cache = cls._load_cache()
            match_cache_key = cls.match_cache_key(file_hash, cues, min_shot, max_shot)

        shot_lo, shot_hi = cls.resolve_shot_range(min_shot, max_shot)
        shot_cap = shot_hi * 1.25

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
2. ตัดช็อตใหม่เฉพาะตอนที่ใจความเปลี่ยน (เปลี่ยนหัวข้อ/เปลี่ยนแอ็กชันที่ต้องโชว์) เช่น ท่อนหมุนข้อต่อ ให้เลือกช่วงที่มือหมุนข้อต่อ, ท่อนเสียบชาร์จ ให้เลือกช่วงที่เสียบชาร์จ, ท่อนปิดการขาย ให้เลือกช่วงโชว์สินค้าชัดเจน
3. start_time และ end_time ต้องอยู่ในช่วง 0 ถึง {raw_duration:.1f} วินาที และความยาวของแต่ละช็อตควรอยู่ที่ {shot_lo:.1f} - {shot_hi:.1f} วินาที และห้ามเกิน {shot_cap:.1f} วินาที (สั้นกว่านี้จะถี่และรกเกินไป ยาวกว่านี้จะดูนิ่งน่าเบื่อ) ถ้าใจความเดียวยาวกว่านั้น ให้แบ่งเป็นหลายช็อตต่อเนื่องที่ยังโชว์เรื่องเดิม
4. cue_ids ต้องเป็น array ของลำดับท่อน (จากเลข 1-{len(cues)} ด้านบน) ที่ช็อตนี้ครอบคลุม เรียงต่อเนื่องกันและไม่มีช่องว่างหรือซ้ำกับช็อตอื่น รวมกันแล้วต้องครบทุกท่อนทั้ง {len(cues)} ท่อน
5. punch_zoom: กำหนดค่า 1.0 ถึง 1.35 เพื่อเพิ่มความตื่นเต้นในสไตล์ TikTok — ใช้ค่าสูงกว่าตรงจุดเฉลย/จุดขายของสินค้า/CTA และค่าต่ำกว่าตรงช่วงเกริ่นนำธรรมดา
6. confidence: ความมั่นใจ 0.0 ถึง 1.0 ว่าภาพช่วงนี้ตรงกับใจความของท่อนจริง (1.0 = เห็นสิ่งที่พูดชัดเจน, ต่ำกว่า 0.5 = ไม่มีภาพที่ตรง ต้องเดาเอา) ห้ามให้ค่าสูงถ้าไม่เห็นสิ่งที่พูดในภาพ

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
      "punch_zoom": 1.15,
      "confidence": 0.85
    }}
  ]
}}
```
"""
        try:
            models_to_try = [
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-flash-latest",
                "gemini-3.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
            ]
            response = None
            last_err = None
            chosen_model = "gemini-3.6-flash"
            t_vision_start = time.time()

            from scripts.ai_bridge import (
                classify_genai_error,
                _extract_retry_after_seconds,
                RATE_LIMIT_DEFAULT_BACKOFF_SECONDS,
                RATE_LIMIT_MAX_BACKOFF_SECONDS,
                TRANSIENT_BACKOFF_SECONDS,
            )
            from google import genai
            from google.genai import types as genai_types

            # Multi-key and multi-model fallback loop (Key 1 -> Key 2 -> ... -> Key N)
            for key_idx, cur_key in enumerate(api_keys, 1):
                key_tag = f"Key #{key_idx} (..{cur_key[-6:]})"
                try:
                    client = genai.Client(api_key=cur_key)
                    remote_video = (
                        cls._get_or_upload_context(client, request_context)
                        if request_context is not None
                        else cls.get_or_upload_video(client, raw_video_path)
                    )
                except Exception as upload_err:
                    print(f"   ⚠️ [AI Vision] Failed to upload/verify video on {key_tag} ({upload_err}) — trying next key...")
                    continue

                if not remote_video:
                    print(f"   ⚠️ [AI Vision] Could not process video on {key_tag} — trying next key...")
                    continue

                key_rate_limited = False
                for model_name in models_to_try:
                    print(f"   👁️ [AI Vision] Calling {model_name} on {key_tag} to analyze raw footage...")
                    for attempt in range(2):
                        try:
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
                            if kind == "rate_limit":
                                key_rate_limited = True
                                if attempt == 0:
                                    backoff = _extract_retry_after_seconds(err) or RATE_LIMIT_DEFAULT_BACKOFF_SECONDS
                                    backoff = min(backoff, RATE_LIMIT_MAX_BACKOFF_SECONDS)
                                    print(f"   ⚠️ [AI Vision] Rate Limit (429) hit on {key_tag} ({model_name}). Retrying in {backoff:.0f}s...")
                                    time.sleep(backoff)
                                    continue
                                print(f"   ⚠️ [AI Vision] Rate Limit (429) on {key_tag} — switching to next key...")
                                break
                            if kind == "transient" and attempt == 0:
                                print(f"   ⚠️ [AI Vision] Transient error on {key_tag} ({model_name}): {err}. Retrying in {TRANSIENT_BACKOFF_SECONDS:.0f}s...")
                                time.sleep(TRANSIENT_BACKOFF_SECONDS)
                                continue
                            print(f"   ⚠️ [AI Vision] {model_name} failed on {key_tag} ({err}) — moving to next fallback...")
                            break

                    if response and response.text:
                        break
                    if key_rate_limited:
                        break

                if response and response.text:
                    print(f"✨ [AI Vision] Successfully analyzed footage with {chosen_model} using {key_tag}")
                    break

            if not response or not response.text:
                cached = cls._exact_cached_match(cache, match_cache_key)
                if cached:
                    print(f"   ♻️ Rate limit hit: reusing the scene map for this exact script ({len(cached)} shots)!")
                    return cached
                raise last_err or RuntimeError("No response from Gemini Vision models across all API keys.")

            resp_text = response.text or ""
            # Extract JSON from markdown
            import re
            m = re.search(r"```json\s*([\s\S]*?)\s*```", resp_text)
            if m:
                clean_json = m.group(1).strip()
            else:
                clean_json = resp_text.strip()

            data = json.loads(clean_json)
            matched = normalize_match_confidence(data.get("matched_shots", []))
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
        {"start": 22.7, "end": 25.8, "text": "สนใจดูรายละเอียดเพิ่มเติม"},
        {"start": 26.2, "end": 28.3, "text": "กดในตะกร้าซ้ายล่างได้เลยครับ!"}
    ]

    res = GeminiVisionMatcher.match_script_to_video(test_video, test_cues, raw_duration=128.0)
    print("\nResult matched count:", len(res))
