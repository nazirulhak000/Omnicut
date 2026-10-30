# -*- coding: utf-8 -*-
"""Batch Voiceover & HyperFrames Composition Producer for 20 Jeep EW011 (JEE01) Clips.
Dual-speaker Southern Couple (#5 Couple Paper Chat):
  - Female (น้องนุ้ย): Single-take Aoede, model gemini-3.8-flash-tts
  - Male (พี่บ่าว): Single-take Puck, model gemini-3.8-flash-tts
  - Audio post: F (asetrate*1.10, atempo=1.20, highpass 140Hz, eq 3.5kHz +3dB), M (atempo=1.32, highpass 95Hz)
  - Split / Align: align_words_in_waveform
  - Whisper: single in-memory instance of large-v3-turbo for turn verification
  - Strict Silence Trimming: trims turn lead/tail dead air (<300 amp), 40ms safety, 0.20s/0.12s gap
  - Audio sanitization: cosine tail fade-out 120ms, clean_isolated_bursts_in_vo, loudnorm -16 LUFS
  - Composition: Couple Paper Chat (#5) on assets/shared/paper_bg.mp4, BGM bgm_lofi.wav (0.05)
  - Brand-First CTA Outro: Jeep EW011 (Style 3B Duo Hero / Clean Cutouts, Zero Emoji, Zero Arrow)
"""
import argparse
import base64
from difflib import SequenceMatcher
import html
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path
import numpy as np

# Set HF_HOME to reuse cached large-v3-turbo model from Profile2 if present
p2_hf = r"C:\Users\nazir\AppData\Roaming\AntigravityProfiles\Profile2\.cache\huggingface"
if os.path.exists(p2_hf):
    os.environ["HF_HOME"] = p2_hf

# Auto-wire CUDA & cuDNN DLLs if available
torch_lib = r"C:\Users\nazir\AppData\Roaming\VoiceStudio\runtime\project\.venv\Lib\site-packages\torch\lib"
if os.path.exists(torch_lib):
    try:
        os.add_dll_directory(torch_lib)
    except Exception:
        pass
    os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")

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
COMPS_DIR = STUDIO / "compositions"
DOCS_DIR = ROOT / "_Docs"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CLIPS_DIR))
sys.path.insert(0, str(STUDIO / "kit"))

from scripts.config import get_gemini_api_keys
from rebuild_all_pov_clean import (
    align_words_in_waveform,
    split_into_n_segments,
)
from tools.clean_all_inter_turn_audio_glitches import clean_isolated_bursts_in_vo

PRODUCT_CODE = "JEE01"
TTS_MODEL = "gemini-3.8-flash-tts"
FALLBACK_MODEL = "gemini-2.5-flash-preview-tts"

F_STYLE = (
    "น้ำเสียงเด็กสาวชาวใต้ (น้องนุ้ย) สดใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ จังหวะฉะฉาน "
    "ไม่เรียบร้อย อารมณ์เหวี่ยงๆ ขี้โวยวายแต่มีเสน่ห์ แฟนสาวจอมบงการประจำช่อง"
)
F_GUARD = (
    "STRICT NO-SWEETNESS GUARD: DO NOT sound sweet, calm, or polite. "
    "Maintain the sassy, energetic, sharp Southern Thai girl persona across ALL turns without exception."
)

M_STYLE = (
    "น้ำเสียงพี่บ่าว ผู้ชายใต้คนซื่อ อารมณ์ดี กวนประสาท ขี้เล่น ตกใจง่าย ฮาๆ เอาใจแฟน "
    "พูดเร็ว คล่องแคล่ว มีจังหวะโบ๊ะบ๊ะ ไม่เก๊กหล่อ"
)
M_GUARD = (
    "STRICT NO-SERIOUSNESS GUARD: DO NOT sound serious, calm, professional, or corporate. "
    "Maintain the playful, flustered, cheeky Southern Thai guy persona across ALL turns without exception."
)

# Multi-key rotation
_KEY_INDEX = 0

def get_next_key():
    global _KEY_INDEX
    keys = get_gemini_api_keys()
    if not keys:
        raise RuntimeError("No GEMINI_API_KEY available in .env!")
    key = keys[_KEY_INDEX % len(keys)]
    _KEY_INDEX += 1
    return key, len(keys)


def tts_take(lines, voice_name, style, guard_rule, out_wav):
    """Generate one single take per speaker for all lines with 2s silence gaps."""
    text = "\n\n... ...\n\n".join(lines)
    prompt = (
        f"[Voice style: {style}\n"
        f"{guard_rule}\n"
        f"Between each section where you see '... ...' leave a clear 2 second silence.]\n\n{text}\n"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            },
        },
    }

    keys = get_gemini_api_keys()
    models_to_try = ["gemini-3.1-flash-tts-preview", TTS_MODEL, FALLBACK_MODEL]
    for model_name in models_to_try:
        for attempt in range(len(keys)):
            key, total_keys = get_next_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    res_data = json.loads(r.read())
                    pcm = base64.b64decode(
                        res_data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                    )
                with wave.open(str(out_wav), "wb") as wf:
                    wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(24000), wf.writeframes(pcm)
                clean_take_or_turn_wav(out_wav)
                return True
            except urllib.error.HTTPError as e:
                time.sleep(3 if e.code == 429 else 2)
            except Exception:
                time.sleep(2)
    raise RuntimeError(f"TTS take failed completely for {voice_name}")


def split_by_longest_gaps(take_wav, n_expected):
    """Split Single-Take WAV into N segments using silence energy gaps."""
    with wave.open(str(take_wav), "rb") as wf:
        sr = wf.getframerate()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    if n_expected == 1:
        return sr, [pcm]

    # Calculate frame energy (50ms window, 25ms hop)
    win = int(0.05 * sr)
    hop = int(0.025 * sr)
    n_frames = (len(pcm) - win) // hop
    if n_frames <= 0:
        return sr, [pcm] * n_expected

    shape = (n_frames, win)
    strides = (pcm.strides[0] * hop, pcm.strides[0])
    frames = np.lib.stride_tricks.as_strided(pcm, shape=shape, strides=strides)
    energy = np.mean(np.abs(frames), axis=1)

    # Threshold for silence
    thresh = max(180, np.percentile(energy, 25) * 1.5)
    silent_frames = np.where(energy < thresh)[0]

    # Find contiguous silent islands
    islands = []
    if len(silent_frames):
        start = silent_frames[0]
        for i in range(1, len(silent_frames)):
            if silent_frames[i] != silent_frames[i - 1] + 1:
                islands.append((start, silent_frames[i - 1]))
                start = silent_frames[i]
        islands.append((start, silent_frames[-1]))

    # Sort islands by duration (longest gaps first)
    islands.sort(key=lambda x: (x[1] - x[0]), reverse=True)
    cut_candidates = sorted([int(((s + e) / 2) * hop + win // 2) for s, e in islands[: n_expected - 1]])

    if len(cut_candidates) < n_expected - 1:
        # Fallback to even split
        step = len(pcm) // n_expected
        cut_candidates = [step * i for i in range(1, n_expected)]

    cuts = [0] + cut_candidates + [len(pcm)]
    chunks = [pcm[cuts[i]:cuts[i + 1]] for i in range(n_expected)]
    return sr, chunks


def clean_take_or_turn_wav(wav_path):
    """Normalize and clean turn audio file."""
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    cleaned, log = clean_isolated_bursts_in_vo(pcm, sr, ch)
    if log:
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(ch), wf.setsampwidth(2), wf.setframerate(sr), wf.writeframes(cleaned.tobytes())


def verify_and_generate_turn(turn_idx, spk, expected, voice_name, style, guard_rule, turn_wav, whisper_model, force=False):
    """Verify turn audio with Whisper."""
    if not turn_wav.exists() or force:
        raise FileNotFoundError(f"Turn wav {turn_wav} does not exist!")

    with wave.open(str(turn_wav), "rb") as wf:
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    audio_float = pcm.astype(np.float32) / 32768.0

    segments, _ = whisper_model.transcribe(audio_float, language="th", beam_size=5)
    heard = " ".join(s.text.strip() for s in segments)

    clean_exp = "".join(expected.split())
    clean_hrd = "".join(heard.split())
    sim = SequenceMatcher(None, clean_exp, clean_hrd).ratio()

    return {
        "turn": turn_idx,
        "speaker": spk,
        "expected": expected,
        "whisper": heard,
        "similarity": sim,
        "wav": str(turn_wav),
    }


def clean_vo_wav(vo_path):
    """Remove trailing clicks or pops in final vo.wav."""
    with wave.open(str(vo_path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).copy()

    # 80ms tail zeroing to ensure silence at clip end
    tail_len = int(0.08 * sr) * ch
    if len(pcm) > tail_len:
        pcm[-tail_len:] = 0

    with wave.open(str(vo_path), "wb") as wf:
        wf.setnchannels(ch), wf.setsampwidth(2), wf.setframerate(sr), wf.writeframes(pcm.tobytes())


def assemble_audio(takes, turns_spec, clip_dir, cid):
    """Apply FFmpeg audio filters (pitch/tempo), strict silence trimming, and assemble vo.wav."""
    tmp = clip_dir / "_tmp_segs"
    tmp.mkdir(exist_ok=True)
    out_sr = 24000
    pieces, timings, cur = [], [], 0.0
    total_trimmed_silence = 0.0

    for i, (spk, phrases, _) in enumerate(turns_spec):
        src = takes[i]
        dst = tmp / f"out_{i:02d}.wav"

        if spk == "F":
            af = "asetrate=24000*1.10,aresample=48000,atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0"
        else:
            af = "atempo=1.32,highpass=f=95"

        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", af, "-ar", str(out_sr), "-ac", "1", str(dst)],
            check=True,
        )
        with wave.open(str(dst), "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        # Strict silence trimming on turn edges (< 300 amplitude, 40ms safety buffer)
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
    # Cosine tail fade-out 120ms to prevent clipping/DC pop
    fade_len = int(0.12 * out_sr)
    if len(full) > fade_len:
        fade_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_len)))
        full[-fade_len:] = (full[-fade_len:] * fade_curve).astype(np.int16)

    pre = tmp / "pre_norm.wav"
    with wave.open(str(pre), "wb") as wf:
        wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(out_sr), wf.writeframes(full.tobytes())

    norm_tmp = tmp / "norm_tmp.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(pre), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(norm_tmp)],
        check=True,
    )

    with wave.open(str(norm_tmp), "rb") as wf:
        sr_vo = wf.getframerate()
        ch_vo = wf.getnchannels()
        pcm_vo = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).copy()

    # 1. Sanitize inter-turn white noise and splice glitches
    cleaned_vo, log = clean_isolated_bursts_in_vo(pcm_vo, sr_vo, ch_vo)
    if log:
        print(f"  [Audio Sanitized] Removed {len(log)} glitches from {cid} vo.wav")

    # 2. 80ms tail zeroing to ensure silence at clip end
    tail_len = int(0.08 * sr_vo) * ch_vo
    if len(cleaned_vo) > tail_len:
        cleaned_vo[-tail_len:] = 0

    # 3. Write final vo.wav ONCE
    vo = STUDIO / "assets" / "clips" / cid / "vo.wav"
    vo.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(vo), "wb") as wf:
        wf.setnchannels(ch_vo), wf.setsampwidth(2), wf.setframerate(sr_vo), wf.writeframes(cleaned_vo.tobytes())

    try:
        norm_tmp.unlink(missing_ok=True)
    except Exception:
        pass

    vo_dur = round(len(full) / out_sr, 3)
    (clip_dir / "timings.json").write_text(json.dumps({"vo": vo_dur, "turns": timings}, indent=1), encoding="utf-8")
    print(f"     Trimmed {total_trimmed_silence:.2f}s dead air -> Punchy dialogue duration: {vo_dur:.2f}s")
    return vo_dur, timings


# Canonical Template for Jeep EW011 (JEE01) with Duo Hero & 4 Floating Badges
JEEP_EW011_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/channels.js"></script>
    <script src="kit/kit.js"></script>
    <style>
      /* __CID__ — Jeep EW011 Couple Paper Chat (#5) 100% Golden Master Parity */
      @font-face {
        font-family: "Kanit Black";
        src: url("kit/fonts/Kanit-Black.ttf") format("truetype");
        font-weight: 900;
      }
      @font-face {
        font-family: "Anuphan";
        src: url("kit/fonts/Anuphan-Bold.ttf") format("truetype");
        font-weight: 700;
      }
      :root {
        --ink: #1b1a17;
        --line-red: #d90429;
      }
      #root {
        background: #efece6;
      }
      #paper {
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
        object-fit: cover;
        filter: brightness(1.02);
      }
      /* Headline overlay */
      .hd {
        position: absolute;
        left: 60px;
        right: 60px;
        top: 110px;
        text-align: center;
        color: var(--ink);
        opacity: 0;
        will-change: transform, opacity;
      }
      .hd-sub {
        font-family: "Anuphan", sans-serif;
        font-size: 50px;
        line-height: 1.2;
      }
      .hd-t {
        margin-top: 10px;
        font-size: 92px;
        line-height: 1.12;
      }
      .hl {
        padding: 0 14px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.92) 52%, rgba(255, 230, 0, 0.92) 92%, transparent 92%);
      }
      /* Chat window bounds */
      #chatwin {
        position: absolute;
        left: 0;
        right: 0;
        top: 470px;
        height: 1170px;
        overflow: hidden;
      }
      #thread {
        position: absolute;
        inset: 0;
        will-change: transform;
      }
      .row,
      .nm {
        position: absolute;
        left: 40px;
        right: 40px;
        display: flex;
        align-items: flex-start;
        gap: 16px;
        opacity: 0;
        will-change: transform, opacity;
      }
      .row.out,
      .nm.out {
        justify-content: flex-end;
      }
      .nm {
        font-family: "Anuphan", sans-serif;
        font-size: 32px;
        color: #55514a;
        padding: 0 104px;
      }
      .row.in {
        padding-left: 96px;
      }
      .row.out {
        padding-right: 96px;
      }
      .ava {
        position: absolute;
        top: 0;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 4px solid var(--ink);
        color: #fff;
        font-family: "Anuphan", sans-serif;
        font-size: 40px;
        line-height: 72px;
        text-align: center;
      }
      .row.in .ava {
        left: 0;
      }
      .row.out .ava {
        right: 0;
      }
      .ava.f {
        background: linear-gradient(135deg, #ff9eb5, #ff5277);
      }
      .ava.m {
        background: linear-gradient(135deg, #60a5fa, #2563eb);
      }
      /* Comic paper sticker bubble */
      .msg {
        display: inline-block;
        padding: 18px 28px;
        border-radius: 34px;
        border: 4px solid var(--ink);
        box-shadow: 4px 6px 0 var(--ink);
        font-family: "Anuphan", sans-serif;
        font-size: 44px;
        line-height: 1.25;
        color: var(--ink);
        will-change: transform;
      }
      .row.in .msg {
        background: #fff;
      }
      .row.out .msg {
        background: #8de07a;
      }
      /* Official listing photo sticker */
      .photo {
        display: inline-block;
        border: 4px solid var(--ink);
        box-shadow: 5px 8px 0 var(--ink);
        background: #fff;
        padding: 10px;
        border-radius: 18px;
      }
      .photo img {
        display: block;
        width: 520px;
        height: 520px;
        object-fit: cover;
        border-radius: 10px;
      }

      /* ==================== CTA OUTRO SHOT (STYLE 3B DUO HERO) ==================== */
      #b-cta {
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
        background: transparent;
        z-index: 20;
        pointer-events: none;
      }
      .t {
        font-family: "Kanit Black", sans-serif;
        color: var(--ink);
        text-align: center;
        line-height: 1.1;
      }
      #cta-1 {
        position: absolute;
        top: 165px;
        left: 0;
        right: 0;
        width: 100%;
        text-align: center;
        z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: 64px;
        line-height: 1.15;
        color: #1b1a17;
      }
      #cta-1 .hl {
        padding: 0 16px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
      }
      #cta-model {
        position: absolute;
        top: 275px;
        left: 0;
        right: 0;
        width: 100%;
        text-align: center;
        z-index: 25;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 44px;
        color: #d90429;
      }
      #cta-stage {
        position: absolute;
        top: 370px;
        left: 0;
        width: 1080px;
        height: 880px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 10;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        z-index: 5;
        pointer-events: none;
      }
      .earbuds-wrap {
        position: absolute;
      }
      .earbuds-img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: contain;
        filter: drop-shadow(0 16px 28px rgba(0, 0, 0, 0.22));
      }
      #f-left {
        width: 480px;
        height: 520px;
        left: 90px;
        bottom: 40px;
        transform: rotate(-5deg);
        z-index: 3;
      }
      #f-right {
        width: 480px;
        height: 520px;
        right: 90px;
        bottom: 40px;
        transform: rotate(5deg);
        z-index: 4;
      }
      #cs-left {
        width: 380px;
        height: 48px;
        bottom: 35px;
        left: 120px;
        z-index: 1;
      }
      #cs-right {
        width: 380px;
        height: 48px;
        bottom: 35px;
        right: 120px;
        z-index: 1;
      }
      .floating-badge {
        position: absolute;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 18px;
        border-radius: 999px;
        border: 3.5px solid #1b1a17;
        background: #ffffff;
        box-shadow: 4px 6px 0 #1b1a17;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 25px;
        color: #1b1a17;
        z-index: 15;
      }
      #badge-1 { top: 60px; left: 65px; }
      #badge-2 { top: 60px; right: 65px; }
      #badge-3 { bottom: 60px; left: 65px; }
      #badge-4 { bottom: 60px; right: 65px; }

      .bottom-info {
        position: absolute;
        bottom: 270px;
        left: 40px;
        right: 40px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        z-index: 25;
      }
      .color-palette {
        display: flex;
        gap: 16px;
      }
      .swatch {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 20px;
        border-radius: 999px;
        border: 3px solid #1b1a17;
        background: #ffffff;
        box-shadow: 3px 4px 0 #1b1a17;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 26px;
        color: #1b1a17;
      }
      .swatch-dot {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px solid #1b1a17;
        display: inline-block;
      }
      .cta-bottom-line {
        position: absolute;
        bottom: 155px;
        left: 0;
        right: 0;
        width: 100%;
        text-align: center;
        font-family: "Kanit Black", sans-serif;
        font-size: 40px;
        color: #d90429;
        z-index: 25;
      }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="__CID__" data-duration="__TOTAL__">
      <video id="paper" src="assets/shared/paper_bg.mp4" data-start="0" data-duration="__TOTAL__" data-playback-rate="0.5" muted playsinline></video>
      <audio id="vo" src="assets/clips/__CID__/vo.wav" data-start="0" data-duration="__VODUR__" data-track-index="11" data-volume="1.0"></audio>
      <audio id="bgm" src="assets/shared/bgm_lofi.wav" data-start="0" data-duration="__TOTAL__" data-track-index="10" data-volume="0.05" data-fade-in="0.6" data-fade-out="1.5"></audio>

      <!-- Chat Thread -->
      <div id="chatwin">
        <div id="thread">
__ROWS__
        </div>
      </div>

      <!-- Headline Overlays -->
__HEADS__

      <!-- CTA Outro Shot (Style 3B Duo Hero) -->
      <div id="b-cta">
        <h1 id="cta-1"><span class="hl">หูฟังบลูทูธ Jeep EW011</span></h1>
        <div id="cta-model">ของแท้หลักร้อย · กดตะกร้าเหลือง</div>

        <div id="cta-stage">
          <div class="floating-badge" id="badge-1">Bluetooth 5.3</div>
          <div class="floating-badge" id="badge-2">ไดรเวอร์ 13mm HiFi</div>
          <div class="floating-badge" id="badge-3">แบตอึด 24 ชม.</div>
          <div class="floating-badge" id="badge-4">กันน้ำ IPX5</div>

          <!-- Duo Hero White & Black -->
          <div class="contact-shadow" id="cs-left"></div>
          <div class="earbuds-wrap" id="f-left">
            <img class="earbuds-img" src="assets/jee01/cutouts/hero_white.png" alt="Jeep EW011 White">
          </div>

          <div class="contact-shadow" id="cs-right"></div>
          <div class="earbuds-wrap" id="f-right">
            <img class="earbuds-img" src="assets/jee01/cutouts/hero_black.png" alt="Jeep EW011 Black">
          </div>
        </div>

        <div class="bottom-info">
          <div class="color-palette">
            <div class="swatch"><span class="swatch-dot" style="background: #ffffff;"></span>ขาวมินิมอล</div>
            <div class="swatch"><span class="swatch-dot" style="background: #1b1a17;"></span>ดำสปอร์ต</div>
          </div>
        </div>
        <div class="cta-bottom-line">ของแท้ศูนย์ไทย ประกันเต็มปี กดตะกร้าซ้ายล่าง</div>
      </div>

      <!-- SFX Tracks -->
__SFX__
    </div>

    <script>
      (function() {
        const items = __ITEMS__;
        const heads = __HEADSJS__;
        const scrolls = __SCROLLS__;
        const ctaT = __CTA__;
        const chatDur = __CHATDUR__;

        const tl = gsap.timeline({ paused: true });

        // Thread scrolls
        scrolls.forEach(s => {
          tl.to('#thread', { y: s.y, duration: 0.28, ease: 'power2.out' }, s.t);
        });

        // Chat bubble animations
        items.forEach(it => {
          if (it.kind === 'msg') {
            tl.fromTo('#' + it.id,
              { opacity: 0, scale: 0.65, y: 15 },
              { opacity: 1, scale: 1, y: 0, duration: 0.22, ease: 'back.out(2)' },
              it.t
            );
          } else if (it.kind === 'photo') {
            tl.fromTo('#' + it.id,
              { opacity: 0, scale: 0.4, rotation: it.side === 'in' ? -6 : 6 },
              { opacity: 1, scale: 1, rotation: 0, duration: 0.35, ease: 'back.out(1.8)' },
              it.t
            );
          } else if (it.kind === 'row') {
            tl.fromTo('#' + it.id, { opacity: 0 }, { opacity: 1, duration: 0.1 }, it.t);
          }
        });

        // Headline pop-in and fade-out
        heads.forEach(h => {
          tl.fromTo('#' + h.id,
            { opacity: 0, scale: 0.85, y: -20 },
            { opacity: 1, scale: 1, y: 0, duration: 0.25, ease: 'back.out(2)' },
            h.t
          );
          if (h.e) {
            tl.to('#' + h.id, { opacity: 0, y: -15, duration: 0.2, ease: 'power2.in' }, h.e);
          }
        });

        // Thread fade-out into CTA
        tl.to('#chatwin', { opacity: 0, y: -30, duration: 0.25, ease: 'power2.in' }, ctaT - 0.2);

        // CTA Outro Animations
        tl.fromTo('#cta-1',
          { opacity: 0, scale: 0.85, y: -25 },
          { opacity: 1, scale: 1, y: 0, duration: 0.35, ease: 'back.out(2)' },
          ctaT
        );
        tl.fromTo('#cta-model',
          { opacity: 0, y: -15 },
          { opacity: 1, y: 0, duration: 0.25, ease: 'power2.out' },
          ctaT + 0.1
        );

        // Duo Hero Springs
        tl.fromTo('#f-left',
          { opacity: 0, scale: 0.4, rotation: -12, y: 40 },
          { opacity: 1, scale: 1, rotation: -5, y: 0, duration: 0.48, ease: 'back.out(1.8)' },
          ctaT + 0.12
        );
        tl.fromTo('#f-right',
          { opacity: 0, scale: 0.4, rotation: 12, y: 40 },
          { opacity: 1, scale: 1, rotation: 5, y: 0, duration: 0.48, ease: 'back.out(1.8)' },
          ctaT + 0.18
        );
        tl.fromTo('.contact-shadow',
          { opacity: 0, scaleX: 0.3 },
          { opacity: 1, scaleX: 1, duration: 0.35, ease: 'power2.out' },
          ctaT + 0.2
        );

        // Floating badges pop
        tl.fromTo('.floating-badge',
          { opacity: 0, scale: 0.6, y: 15 },
          { opacity: 1, scale: 1, y: 0, duration: 0.28, stagger: 0.08, ease: 'back.out(2)' },
          ctaT + 0.3
        );
        tl.fromTo('.bottom-info',
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' },
          ctaT + 0.45
        );
        tl.fromTo('.cta-bottom-line',
          { opacity: 0, scale: 0.9 },
          { opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(1.8)' },
          ctaT + 0.55
        );

        // Sync with HyperFrames player
        window.renderReady = true;
        window.hyperframesSeek = function(t) {
          tl.seek(t, false);
        };
      })();
    </script>
  </body>
</html>
"""

def build_composition(vo_dur, timings, clip_dir, cid, script):
    """Generate HyperFrames composition HTML file for Jeep EW011."""
    turns_spec = script["turns"]
    heads_spec = script["headlines"]
    total = round(vo_dur + 0.4, 2)
    cta_t = round(timings[-1][-1][0] - 0.2, 2) if timings else round(vo_dur - 4.5, 2)
    cta_dur = round(total - cta_t, 2)
    chat_dur = round(cta_t, 2)

    # 1. Headlines
    heads_html = []
    heads_js = []
    for hi, h in enumerate(heads_spec):
        t_turn = h["turn"]
        t_start = timings[t_turn][0][0] if t_turn < len(timings) else 0.0
        if hi + 1 < len(heads_spec):
            next_turn = heads_spec[hi + 1]["turn"]
            t_end = timings[next_turn][0][0] if next_turn < len(timings) else cta_t
        else:
            t_end = cta_t
        hid = f"hd{hi:02d}"
        heads_html.append(
            f'      <div class="hd" id="{hid}">\n'
            f'        <div class="hd-sub">{html.escape(h["sub"])}</div>\n'
            f'        <div class="hd-t"><span class="hl">{html.escape(h["hl"])}</span> {html.escape(h["t"])}</div>\n'
            f'      </div>'
        )
        heads_js.append({"id": hid, "t": round(t_start, 2), "e": round(t_end, 2)})

    # 2. Rows, Bubbles, Photos
    rows_html = []
    items_js = []
    scrolls = []
    cur_y = 40
    WIN_H = 1170

    for ti, (spk, phrases, photo) in enumerate(turns_spec):
        side = "in" if spk == "F" else "out"
        spk_letter = "น" if spk == "F" else "บ"
        spk_cls = "f" if spk == "F" else "m"
        spk_name = "น้องนุ้ย" if spk == "F" else "พี่บ่าว"

        turn_start_t = timings[ti][0][0]

        # Name row
        nm_id = f"nm{ti:02d}"
        rows_html.append(f'          <div class="nm {side}" id="{nm_id}" style="top: {cur_y}px;">{spk_name}</div>')
        items_js.append({"id": nm_id, "kind": "row", "t": round(turn_start_t, 2)})
        cur_y += 44

        # Message bubbles
        for pi, (disp, _) in enumerate(phrases):
            msg_id = f"m{ti:02d}_{pi:02d}"
            phrase_t = timings[ti][pi][0]
            ava_html = f'<div class="ava {spk_cls}">{spk_letter}</div>' if pi == 0 else ""
            rows_html.append(
                f'          <div class="row {side}" id="row_{msg_id}" style="top: {cur_y}px;">\n'
                f'            {ava_html}\n'
                f'            <div class="msg" id="{msg_id}">{html.escape(disp)}</div>\n'
                f'          </div>'
            )
            items_js.append({"id": msg_id, "kind": "msg", "t": round(phrase_t, 2)})
            cur_y += 114

        # Listing photo sticker if present
        if photo:
            p_idx, p_src, _ = photo
            p_id = f"p{ti:02d}"
            p_t = timings[ti][-1][1]
            rows_html.append(
                f'          <div class="row {side}" id="row_{p_id}" style="top: {cur_y}px;">\n'
                f'            <div class="photo" id="{p_id}">\n'
                f'              <img src="{p_src}" alt="Jeep EW011">\n'
                f'            </div>\n'
                f'          </div>'
            )
            items_js.append({"id": p_id, "kind": "photo", "side": side, "t": round(p_t, 2)})
            cur_y += 560

        cur_y += 30

        # Auto-scroll if content overflows chat window
        if cur_y > WIN_H - 120:
            target_scroll = -(cur_y - (WIN_H - 180))
            scrolls.append({"t": round(turn_start_t, 2), "y": round(target_scroll, 1)})

    # SFX tracks
    sfx_html = []
    sx_idx = 0
    for it in items_js:
        if it["kind"] == "msg":
            snd = "msg_recv.mp3" if "m" in it["id"] and "row_m" not in it["id"] else "msg_send.mp3"
            t_snd = max(0.01, round(it["t"] + 0.01, 3))
            track = 12 if sx_idx % 2 == 0 else 13
            sfx_html.append(f'      <audio id="sx{sx_idx:02d}" src="assets/shared/sfx/{snd}" data-start="{t_snd}" data-duration="0.5" data-track-index="{track}" data-volume="0.3"></audio>')
            sx_idx += 1
        elif it["kind"] == "photo":
            t_snd = max(0.01, round(it["t"], 3))
            sfx_html.append(f'      <audio id="sx{sx_idx:02d}" src="assets/shared/sfx/paper.mp3" data-start="{t_snd}" data-duration="0.45" data-track-index="12" data-volume="0.4"></audio>')
            sx_idx += 1

    # CTA Outro SFX
    sfx_html.append(f'      <audio id="sx{sx_idx:02d}" src="assets/shared/sfx/whoosh.mp3" data-start="{round(cta_t - 0.05, 3)}" data-duration="0.5" data-track-index="13" data-volume="0.18"></audio>')
    sx_idx += 1
    sfx_html.append(f'      <audio id="sx{sx_idx:02d}" src="assets/shared/sfx/boom.wav" data-start="{round(cta_t + 0.07, 3)}" data-duration="0.8" data-track-index="12" data-volume="0.15"></audio>')
    sx_idx += 1
    sfx_html.append(f'      <audio id="sx{sx_idx:02d}" src="assets/shared/sfx/cash_register.mp3" data-start="{round(cta_t + 0.55, 3)}" data-duration="1.0" data-track-index="13" data-volume="0.2"></audio>')

    out_html = JEEP_EW011_TEMPLATE
    out_html = out_html.replace("__CID__", cid)
    out_html = out_html.replace("__TOTAL__", str(total))
    out_html = out_html.replace("__CHATDUR__", str(chat_dur))
    out_html = out_html.replace("__CTA__", str(cta_t))
    out_html = out_html.replace("__CTADUR__", str(cta_dur))
    out_html = out_html.replace("__VODUR__", str(vo_dur))
    out_html = out_html.replace("__HEADS__", "\n".join(heads_html))
    out_html = out_html.replace("__ROWS__", "\n".join(rows_html))
    out_html = out_html.replace("__SFX__", "\n".join(sfx_html))
    out_html = out_html.replace("__ITEMS__", json.dumps(items_js, ensure_ascii=False))
    out_html = out_html.replace("__HEADSJS__", json.dumps(heads_js, ensure_ascii=False))
    out_html = out_html.replace("__SCROLLS__", json.dumps(scrolls))

    comp_file = COMPS_DIR / f"{cid}.html"
    comp_file.write_text(out_html, encoding="utf-8")
    return comp_file, cta_t, total


def sync_products_json(cid, aid, total_dur):
    """Sync angle status in _Docs/products.json to 'draft_ready'."""
    products_file = DOCS_DIR / "products.json"
    if not products_file.exists():
        return
    try:
        prods = json.loads(products_file.read_text(encoding="utf-8"))
        p_target = next((p for p in prods if p.get("id") == "jee01" or "Jeep EW011" in p.get("name", "")), None)
        if p_target:
            for a in p_target.get("angles", []):
                if a.get("id") == aid or a.get("clip_id") == cid:
                    if a.get("status") != "rendered":
                        a["status"] = "draft_ready"
                    a["duration"] = total_dur
            products_file.write_text(json.dumps(prods, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  [Warn] Could not sync products.json: {e}")


def produce_one(idx, script, whisper_model, force=False):
    """Produce single clip audio & HyperFrames composition."""
    cid = f"jee01-pov-s{idx:02d}"
    aid = f"ang_jee_{idx:02d}"
    clip_dir = CLIPS_DIR / cid
    clip_dir.mkdir(parents=True, exist_ok=True)
    comp_file = COMPS_DIR / f"{cid}.html"
    vo_file = STUDIO / "assets" / "clips" / cid / "vo.wav"

    print("=" * 68)
    print(f"🎬 PRODUCING [{idx:02d}/20]: {cid} — {script['title']}")
    print(f"   Hook: {script['hook_title']}")
    print("=" * 68)

    t0 = time.time()
    turns_spec = script["turns"]
    takes = [clip_dir / f"turn_{ti:02d}_{spk}.wav" for ti, (spk, _, _) in enumerate(turns_spec)]

    missing_turns = [ti for ti, p in enumerate(takes) if not p.exists() or force]

    if missing_turns:
        print(f"  🎤 Step 1: Generating Audio via Single-Take (2 requests/clip)...")
        f_indices = [i for i, (spk, _, _) in enumerate(turns_spec) if spk == "F"]
        m_indices = [i for i, (spk, _, _) in enumerate(turns_spec) if spk == "M"]

        # Female take (Aoede)
        take_f_wav = clip_dir / "take_F.wav"
        if not take_f_wav.exists() or force or any(ti in f_indices for ti in missing_turns):
            f_lines = [" ".join(spoken for _, spoken in turns_spec[i][1]) for i in f_indices]
            tts_take(f_lines, "Aoede", F_STYLE, F_GUARD, take_f_wav)
            sr_f, f_chunks = split_by_longest_gaps(take_f_wav, len(f_indices))
            for i, fi in enumerate(f_indices):
                dst = clip_dir / f"turn_{fi:02d}_F.wav"
                with wave.open(str(dst), "wb") as wf:
                    wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(sr_f), wf.writeframes(f_chunks[i].tobytes())
                clean_take_or_turn_wav(dst)

        # Male take (Puck)
        take_m_wav = clip_dir / "take_M.wav"
        if not take_m_wav.exists() or force or any(ti in m_indices for ti in missing_turns):
            m_lines = [" ".join(spoken for _, spoken in turns_spec[i][1]) for i in m_indices]
            tts_take(m_lines, "Puck", M_STYLE, M_GUARD, take_m_wav)
            sr_m, m_chunks = split_by_longest_gaps(take_m_wav, len(m_indices))
            for i, mi in enumerate(m_indices):
                dst = clip_dir / f"turn_{mi:02d}_M.wav"
                with wave.open(str(dst), "wb") as wf:
                    wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(sr_m), wf.writeframes(m_chunks[i].tobytes())
                clean_take_or_turn_wav(dst)

    # Step 1b: Verify turns with Whisper
    if whisper_model:
        print(f"  🔍 Verifying {len(turns_spec)} turns with Whisper...")
        for ti, (spk, phrases, _) in enumerate(turns_spec):
            t_wav = takes[ti]
            full_text = " ".join(spoken for _, spoken in phrases)
            voice = "Aoede" if spk == "F" else "Puck"
            style = F_STYLE if spk == "F" else M_STYLE
            guard = F_GUARD if spk == "F" else M_GUARD
            res = verify_and_generate_turn(ti, spk, full_text, voice, style, guard, t_wav, whisper_model, force=False)
            print(f"     Turn {ti:02d} ({spk}): sim={res['similarity']:.2f} | heard: \"{res['whisper'][:28]}...\"")

    # Step 2: Assemble Audio, Strict Silence Trimming & Glitch Sanitization
    print("  🎵 Step 2: Assembling Audio & Strict Silence Trimming...")
    vo_dur, timings = assemble_audio(takes, turns_spec, clip_dir, cid)
    print(f"     -> Assembled vo.wav ({vo_dur:.2f}s) at {vo_file.name}")

    # Step 3: Build HyperFrames Composition
    print("  🎨 Step 3: Building HyperFrames Composition (Style 3B Duo Hero)...")
    comp_path, cta_t, total_dur = build_composition(vo_dur, timings, clip_dir, cid, script)
    print(f"     -> Composition created: {comp_path.name} (Total: {total_dur:.2f}s, CTA: {cta_t:.2f}s)")

    # Step 4: Sync Products JSON
    sync_products_json(cid, aid, total_dur)
    dur_sec = round(time.time() - t0, 1)
    print(f"  ✅ [DONE] {cid} finished in {dur_sec}s -> status='draft_ready'")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch TTS & Composition Producer for Jeep EW011")
    parser.add_argument("--start", type=int, default=1, help="Start index (default: 1)")
    parser.add_argument("--end", type=int, default=20, help="End index (default: 20)")
    parser.add_argument("--force", action="store_true", help="Force re-generate turns")
    parser.add_argument("--no-whisper", action="store_true", help="Skip Whisper verification to save time")
    args = parser.parse_args()

    # Load 20 scripts
    scripts_file = DOCS_DIR / "jeep_ew011_20_scripts.json"
    if not scripts_file.exists():
        print(f"❌ Scripts file {scripts_file} not found!")
        sys.exit(1)

    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    whisper_model = None
    if not args.no_whisper:
        print("🚀 Loading Faster-Whisper large-v3-turbo model...")
        from faster_whisper import WhisperModel
        try:
            whisper_model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16", local_files_only=True)
            print("  -> Whisper model loaded on GPU (CUDA float16)")
        except Exception as e:
            print(f"  [Warn] CUDA failed ({e}), falling back to CPU int8...")
            whisper_model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", local_files_only=True)
            print("  -> Whisper model loaded on CPU (int8)")

    total_start = time.time()
    success_count = 0

    for idx in range(args.start, args.end + 1):
        script = scripts[idx - 1]
        try:
            if produce_one(idx, script, whisper_model, force=args.force):
                success_count += 1
        except Exception as e:
            print(f"❌ Error producing clip {idx:02d}: {e}")
            import traceback
            traceback.print_exc()

    elapsed = round(time.time() - total_start, 1)
    print("=" * 68)
    print(f"🎉 BATCH COMPLETE: {success_count}/{args.end - args.start + 1} clips produced in {elapsed}s")
    print(f"   Outputs: 03_Projects/_HyperFrames_Studio/compositions/jee01-pov-s01..s20.html")
    print(f"   Audio:   03_Projects/_HyperFrames_Studio/assets/clips/jee01-pov-s01..s20/vo.wav")
    print("=" * 68)


if __name__ == "__main__":
    main()
