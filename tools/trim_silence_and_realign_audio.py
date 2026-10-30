#!/usr/bin/env python3
"""Trim dead air silence from turn audio files, re-align phrases, and reassemble punchy vo.wav for all 60 clips.

Eliminates the 1.0 - 2.5s dead air pauses caused by raw Single-Take turn splitting,
re-pacing dialogue to snappy 0.20s turn gaps (cross-speaker) and 0.12s (same-speaker).
"""
import json
from pathlib import Path
import subprocess
import sys
import time
import wave
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO / "clips"
DOCS_DIR = ROOT / "_Docs"

sys.path.insert(0, str(CLIPS_DIR))
from rebuild_all_pov_clean import align_words_in_waveform

CONFIGS = {
    "GOO01": {
        "scripts_file": DOCS_DIR / "goojodoq_5000mah_20_scripts.json",
        "clip_prefix": "goo01-pov-s",
    },
    "HAT01": {
        "scripts_file": DOCS_DIR / "hatari_16inch_20_scripts.json",
        "clip_prefix": "hat01-pov-s",
    },
    "RED01": {
        "scripts_file": DOCS_DIR / "redmi_buds8_20_scripts.json",
        "clip_prefix": "red01-pov-s",
    },
}

def clean_isolated_bursts_in_vo(pcm: np.ndarray, sr: int, ch: int = 2) -> tuple:
    """Sanitize inter-turn white noise and pop glitches."""
    if ch == 2:
        mono = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
    else:
        mono = pcm
    win = int(0.010 * sr)
    hop = int(0.005 * sr)
    n_frames = (len(mono) - win) // hop
    if n_frames <= 0:
        return pcm, []
    shape = (n_frames, win)
    strides = (mono.strides[0] * hop, mono.strides[0])
    frames = np.lib.stride_tricks.as_strided(mono, shape=shape, strides=strides)
    rms = np.sqrt(np.mean(frames.astype(np.float32) ** 2, axis=1))
    noise_floor = np.percentile(rms, 15)
    silence_thresh = max(80.0, noise_floor * 2.5)

    burst_ranges = []
    in_burst = False
    start_frame = 0
    for idx, r in enumerate(rms):
        if r > silence_thresh * 4.0:
            if not in_burst:
                in_burst = True
                start_frame = idx
        else:
            if in_burst:
                in_burst = False
                burst_len = idx - start_frame
                if burst_len <= 8:  # <= 40ms burst in silence
                    left_context = rms[max(0, start_frame - 15) : start_frame]
                    right_context = rms[idx : min(len(rms), idx + 15)]
                    left_quiet = len(left_context) == 0 or np.mean(left_context) < silence_thresh * 1.5
                    right_quiet = len(right_context) == 0 or np.mean(right_context) < silence_thresh * 1.5
                    if left_quiet and right_quiet:
                        burst_ranges.append((start_frame * hop, (idx * hop) + win))

    if not burst_ranges:
        return pcm, []

    cleaned = pcm.copy()
    if ch == 2:
        cleaned_2d = cleaned.reshape(-1, 2)
        for s_idx, e_idx in burst_ranges:
            cleaned_2d[s_idx:e_idx] = 0
    else:
        for s_idx, e_idx in burst_ranges:
            cleaned[s_idx:e_idx] = 0
    return cleaned, burst_ranges

def process_clip(cid: str, script: dict) -> tuple:
    clip_dir = CLIPS_DIR / cid
    tmp = clip_dir / "_tmp_segs"
    tmp.mkdir(exist_ok=True)
    out_sr = 48000

    # Locate turn WAV files
    turn_files = []
    turns_in_tts = list((clip_dir / "tts").glob("turn_*.wav"))
    turns_in_root = list(clip_dir.glob("turn_*.wav"))
    source_dir = (clip_dir / "tts") if turns_in_tts else clip_dir

    turns = script.get("turns") or script.get("dialogue_turns", [])
    turns_spec = []
    for ti, turn in enumerate(turns):
        if isinstance(turn, (list, tuple)):
            spk = turn[0]
            p_tuples = turn[1]
            photo = turn[2] if len(turn) > 2 else None
        else:
            spk = turn.get("speaker", "F")[0].upper()
            phrases = turn.get("phrases", [])
            p_tuples = [(p.get("display_text", ""), p.get("spoken_text", "")) for p in phrases]
            photo = turn.get("product_photo")
        turns_spec.append((spk, p_tuples, photo))

    pieces, timings, cur = [], [], 0.0
    total_trimmed_silence = 0.0

    for i, (spk, phrases, _) in enumerate(turns_spec):
        cand1 = source_dir / f"turn_{i:02d}_{spk}.wav"
        cand2 = source_dir / f"turn_{i:02d}.wav"
        src = cand1 if cand1.exists() else cand2
        if not src.exists():
            # Search by pattern
            matches = list(source_dir.glob(f"turn_{i:02d}*.wav"))
            if matches:
                src = matches[0]
            else:
                raise FileNotFoundError(f"Missing turn {i} for {cid} in {source_dir}")

        with wave.open(str(src), "rb") as wf:
            sr = wf.getframerate()
        dst = tmp / f"out_{i:02d}.wav"

        if spk == "F":
            af = f"asetrate={int(sr * 1.10)},aresample={out_sr},atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0"
        else:
            af = "atempo=1.32,highpass=f=95"

        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", af, "-ar", str(out_sr), "-ac", "1", str(dst)],
            check=True,
        )
        with wave.open(str(dst), "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        # Strict silence trimming on turn edges (remove dead air)
        amp = np.abs(pcm)
        idx = np.where(amp > 300)[0]
        if len(idx):
            lead_idx = max(0, idx[0] - int(0.04 * out_sr))  # 40ms safety
            tail_idx = min(len(pcm), idx[-1] + int(0.04 * out_sr))  # 40ms safety
            dead_air = (len(pcm) - (tail_idx - lead_idx)) / out_sr
            total_trimmed_silence += dead_air
            pcm_trimmed = pcm[lead_idx:tail_idx]
        else:
            pcm_trimmed = pcm

        al = align_words_in_waveform(pcm_trimmed.astype(np.float32) / 32768.0, out_sr, [s for _, s in phrases], cur)
        timings.append([(a["s"], a["e"]) for a in al])

        # Snappy conversational pacing: 0.20s cross-speaker, 0.12s same-speaker
        gap = 0.20 if i + 1 < len(turns_spec) and turns_spec[i + 1][0] != spk else 0.12
        pieces += [pcm_trimmed, np.zeros(int(gap * out_sr), dtype=np.int16)]
        cur += len(pcm_trimmed) / out_sr + gap

    full = np.concatenate(pieces)
    # Cosine tail fade-out 120ms
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

    vo = STUDIO / "assets" / "clips" / cid / "vo.wav"
    vo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(pre), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(vo)],
        check=True,
    )

    # Sanitize glitches
    with wave.open(str(vo), "rb") as wf:
        sr_vo = wf.getframerate()
        ch_vo = wf.getnchannels()
        pcm_vo = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    cleaned_vo, log = clean_isolated_bursts_in_vo(pcm_vo, sr_vo, ch_vo)
    if log:
        with wave.open(str(vo), "wb") as wf:
            wf.setnchannels(ch_vo)
            wf.setsampwidth(2)
            wf.setframerate(sr_vo)
            wf.writeframes(cleaned_vo.tobytes())

    # Write updated timings.json
    timings_p = clip_dir / "timings.json"
    timings_p.write_text(json.dumps({"turns": timings}, ensure_ascii=False, indent=2), encoding="utf-8")

    vo_dur = round(len(cleaned_vo) / (sr_vo * ch_vo), 2)
    return vo_dur, total_trimmed_silence

def main():
    print("=" * 70)
    print("🚀 BATCH AUDIO SILENCE TRIMMER & SNAPPY PACING OPTIMIZER (60 CLIPS)")
    print("=" * 70)
    t0 = time.time()

    for pcode, cfg in CONFIGS.items():
        scripts = json.loads(cfg["scripts_file"].read_text(encoding="utf-8"))
        print(f"\n>>> Processing {pcode} (20 clips)...")
        p_trimmed = 0.0
        for idx, s in enumerate(scripts, start=1):
            cid = f"{cfg['clip_prefix']}{idx:02d}"
            try:
                vo_dur, trimmed = process_clip(cid, s)
                p_trimmed += trimmed
                print(f"  [{idx:02d}/20] ✅ {cid}: new dur={vo_dur}s (trimmed {trimmed:.2f}s dead air)")
            except Exception as e:
                print(f"  [{idx:02d}/20] ❌ {cid} error: {e}")
        print(f"  -> Total dead air eliminated for {pcode}: {p_trimmed:.2f} seconds!")

    total_time = round(time.time() - t0, 1)
    print("\n" + "=" * 70)
    print(f"🎉 ALL 60 CLIPS RE-ALIGNED & TRIMMED IN {total_time}s")
    print("=" * 70)

if __name__ == "__main__":
    main()
