"""
generate_voice_cache.py
=======================
Pre-generates audio preview samples for every VOICE_PRESET x AD_TONE combination
and saves them to frontend/public/voice_cache/.

Usage:
  python scripts/generate_voice_cache.py           # generate all missing
  python scripts/generate_voice_cache.py --force   # re-generate all (overwrite)
  python scripts/generate_voice_cache.py --check   # just print status, no generation
"""

import sys
import os
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CACHE_DIR = PROJECT_ROOT / "frontend" / "public" / "voice_cache"

VOICE_PRESETS = {
    "gemini_puck_male_hype":     {"voice": "Puck",   "label": "Puck — ชายพลังสูง TikTok",      "gender": "male"},
    "gemini_charon_male_pro":    {"voice": "Charon", "label": "Charon — ชายทุ้มลึก น่าเชื่อถือ", "gender": "male"},
    "gemini_kore_female_bright": {"voice": "Kore",   "label": "Kore — หญิงสดใส ป้ายยาเก่ง",    "gender": "female"},
    "gemini_aoede_female_pro":   {"voice": "Aoede",  "label": "Aoede — หญิงพรีเมียม นุ่มนวล",  "gender": "female"},
    "gemini_fenrir_male_strong": {"voice": "Fenrir", "label": "Fenrir — ชายสตรอง คมเข้ม",       "gender": "male"},
}

AD_TONES = {
    "commercial_premium":   "โฆษณาพรีเมียม",
    "commercial_hype":      "ป้ายยาไวรัล",
    "commercial_aesthetic": "มินิมอล ดูแพง",
    "commercial_expert":    "ผู้เชี่ยวชาญ",
}

SAMPLE_TEXTS = {
    "commercial_premium": (
        "สวัสดีครับ วันนี้ผมจะมารีวิวสินค้าตัวใหม่ที่ฮิตมากในตอนนี้ "
        "Design สวยงาม คุณภาพพรีเมียม ความรู้สึกดีตั้งแต่แกะกล่อง "
        "คนที่รักความประณีต ห้ามพลาดตัวนี้เลยครับ"
    ),
    "commercial_hype": (
        "โอ้โห ของตัวนี้ดีจนอยากกระโดดเลย ทำไมไม่เคยใช้มาก่อน "
        "ใช้แล้วติดใจมาก ราคานี้ต้องซื้อเก็บไว้เลย อย่ารอเลย "
        "ลิงก์อยู่ด้านล่างเลยนะ ใครที่กำลังลังเลหยุดลังเลได้เลยครับ"
    ),
    "commercial_aesthetic": (
        "วันนี้อยากแนะนำของที่ใช้แล้วรู้สึกดีมากขึ้นทุกวัน "
        "ดีไซน์เรียบหรู ใช้งานง่าย เข้ากับทุก Lifestyle เลยค่ะ "
        "ลองแล้วจะรู้ว่าทำไมทุกคนถึงพูดถึงมัน"
    ),
    "commercial_expert": (
        "ผมทดสอบสินค้าตัวนี้มาสองสัปดาห์ นี่คือข้อสรุปที่ได้ "
        "Performance ดีเกินราคา ทนทาน และใช้งานได้จริงในชีวิตประจำวัน "
        "ถ้ายังไม่มีตัวนี้ นี่คือสิ่งที่คุณต้องการ"
    ),
}


def get_all_combos():
    return [(v, t) for v in VOICE_PRESETS for t in AD_TONES]


def cache_filename(voice_id, tone_id):
    return f"{voice_id}__{tone_id}.wav"


def check_status():
    result = {}
    for voice_id, tone_id in get_all_combos():
        fname = cache_filename(voice_id, tone_id)
        result[fname] = (CACHE_DIR / fname).exists()
    return result


def generate_combo(voice_id, tone_id, force=False, delay=12):
    """Generate a single combo. Returns True if generated, False if skipped."""
    import time
    from scripts.gemini_tts_engine import GeminiFlashTTSEngine
    fname = cache_filename(voice_id, tone_id)
    out_path = CACHE_DIR / fname
    if out_path.exists() and not force:
        print(f"  Already cached: {fname}")
        return False
    text = SAMPLE_TEXTS[tone_id]
    voice_cfg = VOICE_PRESETS[voice_id]
    print(f"  Generating {voice_cfg['label']} x {AD_TONES[tone_id]} ...")

    # Retry up to 3 times on rate-limit / transient error
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            GeminiFlashTTSEngine.generate_speech(
                text=text,
                output_path=str(out_path),
                voice_preset=voice_id,
                ad_tone=tone_id,
                speed=1.15,
            )
            print(f"  Saved: {fname}")
            # Polite delay after every successful generation to avoid hitting quota
            if delay > 0:
                time.sleep(delay)
            return True
        except Exception as exc:
            err_str = str(exc)
            is_rate_limit = "429" in err_str or "Too Many Requests" in err_str
            if is_rate_limit and attempt < max_retries:
                wait = 30 * attempt  # 30s, 60s, 90s
                print(f"  Rate-limited (429). Waiting {wait}s before retry {attempt}/{max_retries-1}...")
                time.sleep(wait)
            else:
                print(f"  FAILED ({voice_id}/{tone_id}) attempt {attempt}: {exc}")
                if attempt >= max_retries:
                    return False
    return False


def write_manifest(results):
    import datetime
    manifest_path = CACHE_DIR / "manifest.json"
    combos = []
    for voice_id, tone_id in get_all_combos():
        fname = cache_filename(voice_id, tone_id)
        voice_cfg = VOICE_PRESETS[voice_id]
        combos.append({
            "voice_id": voice_id,
            "tone_id": tone_id,
            "voice_label": voice_cfg["label"],
            "tone_label": AD_TONES[tone_id],
            "voice_gender": voice_cfg["gender"],
            "filename": fname,
            "url": f"/voice_cache/{fname}",
            "ready": results.get(fname, False),
        })
    manifest = {
        "generated_at": datetime.datetime.now().isoformat(),
        "total": len(combos),
        "ready": sum(1 for c in combos if c["ready"]),
        "combos": combos,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nManifest saved: {manifest_path}")
    print(f"  {manifest['ready']}/{manifest['total']} combinations ready")


def main():
    parser = argparse.ArgumentParser(description="Pre-generate voice preview cache")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--voice", metavar="VOICE_ID")
    parser.add_argument("--tone", metavar="TONE_ID")
    parser.add_argument(
        "--delay", type=float, default=12,
        metavar="SECONDS",
        help="Seconds to wait between each generation call (default: 12). "
             "Increase if hitting rate limits."
    )
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("OmniCut Pro - Voice Preview Cache Generator")
    print(f"Output dir: {CACHE_DIR}")
    print()

    if args.check:
        status = check_status()
        ready = sum(1 for v in status.values() if v)
        print(f"Cache status: {ready}/{len(status)} files ready\n")
        for fname, exists in sorted(status.items()):
            print(f"  {'OK' if exists else '--'} {fname}")
        return

    try:
        from scripts.gemini_tts_engine import GeminiFlashTTSEngine
        if not GeminiFlashTTSEngine.is_available():
            print("ERROR: GEMINI_API_KEY not set. Add it to .env and retry.")
            sys.exit(1)
    except ImportError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    combos = get_all_combos()
    if args.voice:
        combos = [(v, t) for v, t in combos if v == args.voice]
    if args.tone:
        combos = [(v, t) for v, t in combos if t == args.tone]

    print(f"Processing {len(combos)} combinations (force={args.force}, delay={args.delay}s)\n")
    eta_min = int(len(combos) * args.delay / 60) + 1
    print(f"Estimated time: ~{eta_min} minutes (with {args.delay}s delay per call)\n")

    generated = skipped = failed = 0
    for i, (voice_id, tone_id) in enumerate(combos, 1):
        print(f"[{i}/{len(combos)}]", end=" ")
        try:
            result = generate_combo(voice_id, tone_id, force=args.force, delay=args.delay)
            if result:
                generated += 1
            else:
                skipped += 1
        except Exception as exc:
            print(f"  Unexpected error ({voice_id}/{tone_id}): {exc}")
            failed += 1

    print(f"\nDone! Generated: {generated}, Skipped: {skipped}, Failed: {failed}")
    status = check_status()
    write_manifest(status)


if __name__ == "__main__":
    main()
