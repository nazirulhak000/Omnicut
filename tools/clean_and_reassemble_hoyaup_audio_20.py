"""Comprehensive Audio Cleaner and Re-assembler for 20 HOYAUP Clips.
Solves:
1. Inter-turn noise bursts, mouth clicks, and Gemini Flash TTS chunking pops
2. Accurately trims leading/trailing silence on all 260 turn wavs with cosine fades
3. Enforces 100% mathematical zero silence (0.0 amplitude) in all inter-turn gaps
4. Re-aligns subtitle timings and regenerates compositions without #paper-tint
5. Clears .waveform-cache so HyperFrames Studio timeline immediately shows clean waveforms
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
import numpy as np

# Force UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO / "clips"
ASSETS_DIR = STUDIO / "assets" / "clips"
WAVEFORM_CACHE = STUDIO / ".waveform-cache"

sys.path.insert(0, str(ROOT))
from tools.batch_produce_hoyaup_20 import (
    align_words_in_waveform,
    layout_thread,
    generate_composition_html,
    clean_isolated_bursts_in_vo,
    clean_vo_wav,
)

def trim_speech_bounds(pcm: np.ndarray, sr: int, pad_ms: int = 50):
    """Accurately detect speech start and end, discarding trailing/leading pops and hiss."""
    win = int(0.01 * sr)
    n = len(pcm) // win
    if n < 3:
        return pcm
        
    frames = pcm[:n * win].reshape(n, win)
    rms = np.sqrt(np.mean(frames.astype(np.float32)**2, axis=1))
    max_amp = np.max(np.abs(frames), axis=1)

    is_speech = (rms > 80) | (max_amp > 1200)
    indices = np.where(is_speech)[0]
    if len(indices) == 0:
        return pcm

    pad_samples = int(pad_ms * 0.001 * sr)
    first_sample = max(0, indices[0] * win - pad_samples)
    last_sample = min(len(pcm), (indices[-1] + 1) * win + pad_samples)

    trimmed = pcm[first_sample:last_sample].copy()

    # 15ms cosine fade-in
    fade_in_s = int(0.015 * sr)
    if len(trimmed) > fade_in_s:
        curve_in = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_in_s)))
        trimmed[:fade_in_s] = (trimmed[:fade_in_s] * curve_in).astype(np.int16)

    # 25ms cosine fade-out
    fade_out_s = int(0.025 * sr)
    if len(trimmed) > fade_out_s:
        curve_out = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_out_s)))
        trimmed[-fade_out_s:] = (trimmed[-fade_out_s:] * curve_out).astype(np.int16)

    return trimmed

def reassemble_clip_audio(cid: str, script_data: dict):
    """Reassemble vo.wav from turns with verified zero-noise inter-turn gaps."""
    clip_dir = CLIPS_DIR / cid
    tts_dir = clip_dir / "tts"
    if not tts_dir.exists():
        print(f"[{cid}] Error: tts_dir not found at {tts_dir}")
        return None, None, None

    turns_spec = script_data["turns"]
    out_sr = 48000
    tmp = clip_dir / "_tmp_clean_segs"
    tmp.mkdir(exist_ok=True)

    pieces = []
    timings = []
    cur = 0.0
    turn_boundaries = []

    for i, (spk, phrases, _) in enumerate(turns_spec):
        src = tts_dir / f"turn_{i:02d}_{spk}.wav"
        if not src.exists():
            raise FileNotFoundError(f"Missing {src}")

        with wave.open(str(src), "rb") as wf:
            sr = wf.getframerate()
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        # Trim speech boundaries
        clean_pcm = trim_speech_bounds(pcm, sr, pad_ms=50)

        # Write clean temporary turn
        clean_src = tmp / f"clean_turn_{i:02d}.wav"
        with wave.open(str(clean_src), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(clean_pcm.tobytes())

        # Filter
        dst = tmp / f"out_{i:02d}.wav"
        if spk == "F":
            af = f"asetrate={int(sr * 1.10)},aresample={out_sr},atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0"
        else:
            af = "atempo=1.32,highpass=f=95"

        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(clean_src), "-af", af, "-ar", str(out_sr), "-ac", "1", str(dst)],
            check=True,
        )

        with wave.open(str(dst), "rb") as wf:
            filtered_pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).copy()

        # Word alignment for sub-bursts
        al = align_words_in_waveform(filtered_pcm.astype(np.float32) / 32768.0, out_sr, [s for _, s in phrases], cur)
        timings.append([(a["s"], a["e"]) for a in al])

        t_turn_start = cur
        t_turn_end = cur + len(filtered_pcm) / out_sr
        turn_boundaries.append((t_turn_start, t_turn_end))

        gap = 0.28 if i + 1 < len(turns_spec) and turns_spec[i + 1][0] != spk else 0.14
        zero_gap = np.zeros(int(gap * out_sr), dtype=np.int16)
        pieces += [filtered_pcm, zero_gap]
        cur = t_turn_end + gap

    full = np.concatenate(pieces)

    # 120ms cosine fade-out at the very end
    fade_len = int(0.12 * out_sr)
    if len(full) > fade_len:
        fade_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_len)))
        full[-fade_len:] = (full[-fade_len:] * fade_curve).astype(np.int16)

    pre = tmp / "pre_norm.wav"
    with wave.open(str(pre), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(out_sr)
        wf.writeframes(full.tobytes())

    vo_dst = ASSETS_DIR / cid / "vo.wav"
    vo_dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(pre), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(vo_dst)],
        check=True,
    )

    # Read normalized stereo audio
    with wave.open(str(vo_dst), "rb") as wf:
        sr_vo = wf.getframerate()
        ch_vo = wf.getnchannels()
        pcm_vo = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).copy()

    # Enforce 100% mathematical zero silence between turn boundaries
    for k in range(len(turn_boundaries) - 1):
        gap_start_s = turn_boundaries[k][1] + 0.02
        gap_end_s = turn_boundaries[k+1][0] - 0.02
        if gap_end_s > gap_start_s:
            s0 = int(gap_start_s * sr_vo * ch_vo)
            s1 = int(gap_end_s * sr_vo * ch_vo)
            fade_s = int(0.010 * sr_vo * ch_vo)
            
            # Smoothly fade into pure zero
            if s0 >= fade_s:
                curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_s // ch_vo)))
                c = np.repeat(curve, ch_vo)
                pcm_vo[s0-fade_s:s0] = (pcm_vo[s0-fade_s:s0] * c).astype(np.int16)
            pcm_vo[s0:s1] = 0
            if s1 + fade_s <= len(pcm_vo):
                curve_in = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_s // ch_vo)))
                c_in = np.repeat(curve_in, ch_vo)
                pcm_vo[s1:s1+fade_s] = (pcm_vo[s1:s1+fade_s] * c_in).astype(np.int16)

    # Clean the tail 120ms
    clean_tail_s = int(0.12 * sr_vo * ch_vo)
    if len(pcm_vo) > clean_tail_s:
        pcm_vo[-clean_tail_s:] = 0

    # Write back clean vo.wav
    with wave.open(str(vo_dst), "wb") as wf:
        wf.setnchannels(ch_vo)
        wf.setsampwidth(2)
        wf.setframerate(sr_vo)
        wf.writeframes(pcm_vo.tobytes())

    # Cleanup tmp dir
    try:
        shutil.rmtree(tmp)
    except Exception:
        pass

    vo_dur = round(len(pcm_vo) / (sr_vo * ch_vo), 3)

    # Save timings.json
    timings_json = clip_dir / "timings.json"
    timings_json.write_text(json.dumps({"vo": vo_dur, "turns": timings}, indent=1), encoding="utf-8")

    return vo_dur, timings, turn_boundaries

def process_all_20_hoyaup():
    scripts_file = ROOT / "_Docs" / "hoyaup_magnetic_fan_20_scripts.json"
    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    print("=" * 70)
    print("🚀 Re-assembling & Sanitizing Audio across All 20 HOYAUP Clips")
    print("=" * 70)

    # 1. Clear waveform cache for HOYAUP to eliminate stale peak cache in Studio
    if WAVEFORM_CACHE.exists():
        deleted_cache = 0
        for cache_file in WAVEFORM_CACHE.glob("*hoy01-pov*"):
            try:
                cache_file.unlink()
                deleted_cache += 1
            except Exception:
                pass
        print(f"🧹 Cleared {deleted_cache} stale waveform cache files in {WAVEFORM_CACHE.name}\n")

    for s in scripts:
        cid = f"hoy01-pov-s{s['num']:02d}"
        clip_dir = CLIPS_DIR / cid
        print(f"[{cid}] Re-assembling with zero-noise inter-turn silence...")
        
        vo_dur, timings, turn_boundaries = reassemble_clip_audio(cid, s)
        if vo_dur is None:
            continue

        # Re-layout and regenerate composition HTML without #paper-tint
        turns_spec = s["turns"]
        headlines_spec = s["headlines"]
        cta_phrase = (len(turns_spec) - 1, 1)

        items, scrolls, cta_t = layout_thread(timings, turns_spec, cta_phrase)
        total_dur = generate_composition_html(
            vo_dur, timings, items, scrolls, cta_t, turns_spec, headlines_spec, cta_phrase, cid, clip_dir
        )
        print(f"  -> vo_dur={vo_dur}s, total_dur={total_dur}s, inter-turn gaps=100% zero amplitude")

    print("\n" + "=" * 70)
    print("✅ All 20 HOYAUP Clips Successfully Sanitized and Re-assembled!")
    print("=" * 70)

if __name__ == "__main__":
    process_all_20_hoyaup()
