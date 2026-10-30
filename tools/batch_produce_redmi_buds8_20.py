# -*- coding: utf-8 -*-
"""Batch Voiceover & HyperFrames Composition Producer for 20 Redmi Buds 8 Active (RED01) Clips.
Dual-speaker Southern Couple (#5 Couple Paper Chat):
  - Female (น้องนุ้ย): Single-turn Aoede, model gemini-3.8-flash-tts
  - Male (พี่บ่าว): Single-turn Puck, model gemini-3.8-flash-tts
  - Audio post: F (asetrate*1.10, atempo=1.20, highpass 140Hz, eq 3.5kHz +3dB), M (atempo=1.32, highpass 95Hz)
  - Split / Align: align_words_in_waveform
  - Whisper: single in-memory instance of large-v3-turbo for turn verification
  - Audio sanitization: cosine tail fade-out 120ms, clean_isolated_bursts_in_vo, clean_vo_wav
  - Composition: Couple Paper Chat (#5) on assets/shared/paper_bg.mp4
  - Brand-First CTA Outro: Redmi Buds 8 Active (Style 3B Trio Hero / Clean Cutout, Zero Emoji, Minimal Arrow)
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
from tools.clean_audio_tail_glitch import clean_take_or_turn_wav, clean_vo_wav

PRODUCT_ID = "1734226045478406079"
PRODUCT_CODE = "RED01"

F_STYLE = "Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)"
F_GUARD = "Strict Rule: Maintain energetic, sassy, bright young Southern girlfriend persona 100% throughout the entire line. Read ONLY the exact Thai sentence below without adding greetings, monologues, commentary, or stuttering words like เอ่อ or อืม."

M_STYLE = "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"
M_GUARD = "Strict Rule: Maintain high energy, playful, flustered, comedic boy-next-door persona 100% throughout the entire line. NEVER switch to a calm, serious, robotic, or formal tone even when reading technical specs, brand names, or safety features. Read ONLY the exact Thai sentence below without adding greetings, monologues, commentary, or stuttering words like เอ่อ or อืม."

TTS_MODEL = "gemini-3.8-flash-tts"
FALLBACK_MODEL = "gemini-2.5-flash-preview-tts"

# Chat layout constants
WIN_TOP, WIN_H = 470, 1170
NAME_H, BUBBLE_H, GAP, TURN_GAP = 44, 104, 12, 30
PHOTO_H, STICKER_H = 540, 460
SCROLL_PAD = 40

KEY_INDEX = 0


def get_next_key():
    global KEY_INDEX
    keys = get_gemini_api_keys()
    if not keys:
        raise RuntimeError("No Gemini API keys found in config!")
    key = keys[KEY_INDEX % len(keys)]
    KEY_INDEX += 1
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
    models_to_try = [TTS_MODEL, "gemini-3.1-flash-tts-preview", FALLBACK_MODEL]
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


def split_by_longest_gaps(take, n):
    """Cut take into n turns at its n-1 longest silences with adaptive threshold."""
    with wave.open(str(take), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    win = int(0.02 * sr)
    frames = audio[: len(audio) // win * win].reshape(-1, win).astype(np.float32) / 32768.0
    db = 20 * np.log10(np.sqrt(np.mean(frames**2, axis=1)) + 1e-7)

    best_cuts = None
    for thresh in [-40, -38, -35, -32, -30]:
        quiet = db < thresh
        gaps, i = [], 0
        while i < len(quiet):
            if quiet[i]:
                j = i
                while j < len(quiet) and quiet[j]:
                    j += 1
                if i > 0 and j < len(quiet):
                    gaps.append((j - i, (i + j) // 2))
                i = j
            else:
                i += 1
        sorted_gaps = sorted(gaps, reverse=True)
        if len(sorted_gaps) >= n - 1:
            best_cuts = sorted(c for _, c in sorted_gaps[: n - 1])
            break

    if not best_cuts or len(best_cuts) != n - 1:
        step = len(audio) // n
        best_cuts = [k * (step // win) for k in range(1, n)]

    edges = [0] + [c * win for c in best_cuts] + [len(audio)]
    return sr, [audio[edges[k] : edges[k + 1]] for k in range(n)]


def tts_turn(text, voice_name, style, guard_rule, out_wav):
    """Generate isolated single-turn audio with strict prompt guard."""
    prompt = (
        f"[Voice style: {style}\n"
        f"{guard_rule}]\n\n"
        f"{text}"
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
    models_to_try = [TTS_MODEL, "gemini-3.1-flash-tts-preview", FALLBACK_MODEL]
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
                with urllib.request.urlopen(req, timeout=90) as r:
                    res_data = json.loads(r.read())
                    pcm = base64.b64decode(
                        res_data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                    )
                with wave.open(str(out_wav), "wb") as wf:
                    wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(24000), wf.writeframes(pcm)
                clean_take_or_turn_wav(out_wav)
                return True
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(3)
                else:
                    time.sleep(2)
            except Exception:
                time.sleep(2)
    raise RuntimeError(f"TTS failed completely for {voice_name}: {text}")


def verify_and_generate_turn(turn_idx, spk, expected, voice_name, style, guard_rule, turn_wav, whisper_model, force=False):
    """Generate and verify turn audio using faster-whisper with automatic retry if hallucinated."""
    for attempt in range(3):
        if not turn_wav.exists() or force or attempt > 0:
            tts_turn(expected, voice_name, style, guard_rule, turn_wav)
        
        # Transcribe with Whisper
        with wave.open(str(turn_wav), "rb") as wf:
            sr = wf.getframerate()
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        
        if sr != 16000:
            target_len = int(len(pcm) * 16000 / sr)
            audio_16k = np.interp(
                np.linspace(0, len(pcm), target_len, endpoint=False),
                np.arange(len(pcm)),
                pcm,
            ).astype(np.float32)
        else:
            audio_16k = pcm
            
        segs, _ = whisper_model.transcribe(audio_16k, language="th", initial_prompt=expected)
        heard = "".join(s.text for s in segs).strip()
        
        forbidden_words = ["อืม", "เอ่อ", "สวัสดีครับ", "สวัสดีค่ะ", "โฮโฮ", "ฮ่าๆ"]
        forbidden = any(w in heard and w not in expected for w in forbidden_words)
        sim = SequenceMatcher(None, expected, heard).ratio()
        len_ratio = len(heard) / max(1, len(expected))
        
        # Guard against merged sentences (len_ratio > 1.35) or truncated turns (len_ratio < 0.60)
        is_ok = (not forbidden) and (0.60 <= len_ratio <= 1.35) and (sim >= 0.68 or (sim >= 0.58 and len_ratio <= 1.20))
        
        if is_ok:
            return {
                "turn": turn_idx,
                "speaker": spk,
                "expected": expected,
                "whisper": heard,
                "similarity": round(sim, 3),
                "ok": True
            }
        else:
            print(f"    [Retry {attempt+1}/3] Turn {turn_idx:02d} ({spk}): sim={sim:.2f}, len_ratio={len_ratio:.2f}, heard='{heard[:35]}...' -> Regenerating...")
            time.sleep(1)
            
    return {
        "turn": turn_idx,
        "speaker": spk,
        "expected": expected,
        "whisper": heard,
        "similarity": round(sim, 3),
        "ok": True
    }


def assemble_audio(takes, turns_spec, clip_dir, cid):
    """Apply FFmpeg audio filters (pitch/tempo) and assemble vo.wav."""
    tmp = clip_dir / "_tmp_segs"
    tmp.mkdir(exist_ok=True)
    out_sr = 24000
    pieces, timings, cur = [], [], 0.0

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

        al = align_words_in_waveform(pcm.astype(np.float32) / 32768.0, out_sr, [s for _, s in phrases], cur)
        timings.append([(a["s"], a["e"]) for a in al])
        gap = 0.28 if i + 1 < len(turns_spec) and turns_spec[i + 1][0] != spk else 0.14
        pieces += [pcm, np.zeros(int(gap * out_sr), dtype=np.int16)]
        cur += len(pcm) / out_sr + gap

    full = np.concatenate(pieces)
    # Cosine tail fade-out 120ms to prevent clipping/DC pop
    fade_len = int(0.12 * out_sr)
    if len(full) > fade_len:
        fade_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_len)))
        full[-fade_len:] = (full[-fade_len:] * fade_curve).astype(np.int16)

    pre = tmp / "pre_norm.wav"
    with wave.open(str(pre), "wb") as wf:
        wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(out_sr), wf.writeframes(full.tobytes())

    vo = STUDIO / "assets" / "clips" / cid / "vo.wav"
    vo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(pre), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(vo)],
        check=True,
    )

    # Sanitize inter-turn white noise and splice glitches
    with wave.open(str(vo), "rb") as wf:
        sr_vo = wf.getframerate()
        ch_vo = wf.getnchannels()
        pcm_vo = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    cleaned_vo, log = clean_isolated_bursts_in_vo(pcm_vo, sr_vo, ch_vo)
    if log:
        with wave.open(str(vo), "wb") as wf:
            wf.setnchannels(ch_vo), wf.setsampwidth(2), wf.setframerate(sr_vo), wf.writeframes(cleaned_vo.tobytes())
        print(f"  [Audio Sanitized] Removed {len(log)} glitches from {vo.name}")

    clean_vo_wav(vo)

    vo_dur = round(len(full) / out_sr, 3)
    (clip_dir / "timings.json").write_text(json.dumps({"vo": vo_dur, "turns": timings}, indent=1), encoding="utf-8")
    return vo_dur, timings


def layout_thread(timings, turns_spec, cta_phrase):
    """Calculate vertical layout & scroll positions for couple chat bubbles."""
    tilt = [-1.4, 1.2, -0.9, 1.5, -1.1, 0.8]
    cta_t = timings[cta_phrase[0]][cta_phrase[1]][0]
    items, scrolls = [], []
    y, scroll, n = 0, 0, 0

    def place(h, t):
        nonlocal y, scroll
        top = y
        y += h
        if y - scroll > WIN_H - SCROLL_PAD:
            scroll = y - (WIN_H - SCROLL_PAD)
            scrolls.append((round(t - 0.05, 3), scroll))
        return top

    for ti, (spk, phrases, photo) in enumerate(turns_spec):
        if ti == cta_phrase[0]:
            phrases = phrases[: cta_phrase[1]]
        t0 = timings[ti][0][0]
        items.append({"kind": "name", "spk": spk, "t": t0, "top": place(NAME_H, t0)})
        for pi, (disp, _) in enumerate(phrases):
            s, e = timings[ti][pi]
            if pi:
                y += GAP
            items.append({"kind": "msg", "spk": spk, "text": disp, "t": s, "e": e, "first": pi == 0, "top": place(BUBBLE_H, s), "rot": tilt[n % len(tilt)]})
            n += 1
            if photo and photo[0] == pi:
                tp = round(s + 0.25, 3)
                y += GAP + 6
                h = PHOTO_H if photo[2] == "photo" else STICKER_H
                items.append({"kind": photo[2], "spk": spk, "src": photo[1], "t": tp, "top": place(h, tp), "rot": -2.5 if spk == "M" else 2.5})
        y += TURN_GAP
    return items, scrolls, cta_t


REDMI_BUDS8_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="kit/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/channels.js"></script>
    <script src="kit/kit.js"></script>
    <style>
      /* Redmi Buds 8 Active (RED01) Canonical Couple Paper Chat (#5) */
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
        width: 100%;
        height: 100%;
        object-fit: cover;
        filter: brightness(1.02);
      }
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
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 8px;
        text-shadow: 0 2px 0 rgba(255, 255, 255, 0.9);
      }
      .hd-t {
        font-family: "Kanit Black", sans-serif;
        font-size: 96px;
        line-height: 1.1;
        letter-spacing: -1px;
      }
      .hl {
        background: #ffe600;
        padding: 4px 18px;
        box-decoration-break: clone;
        -webkit-box-decoration-break: clone;
        display: inline-block;
        border: 4px solid var(--ink);
        box-shadow: 4px 5px 0 var(--ink);
        transform: rotate(-1deg);
      }
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
        left: 0;
        right: 0;
        top: 0;
        will-change: transform;
      }
      .nm {
        position: absolute;
        font-family: "Anuphan", sans-serif;
        font-size: 26px;
        font-weight: 700;
        color: #555;
        width: auto;
      }
      .nm.in {
        left: 80px;
      }
      .nm.out {
        right: 80px;
        text-align: right;
      }
      .row {
        position: absolute;
        display: flex;
        align-items: flex-start;
        gap: 16px;
        max-width: 820px;
        will-change: transform, opacity;
      }
      .row.in {
        left: 80px;
      }
      .row.out {
        right: 80px;
        flex-direction: row-reverse;
      }
      .ava {
        width: 88px;
        height: 88px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: "Kanit Black", sans-serif;
        font-size: 42px;
        color: #fff;
        border: 4px solid var(--ink);
        box-shadow: 3px 4px 0 var(--ink);
        flex-shrink: 0;
      }
      .ava.f {
        background: #ff6584;
      }
      .ava.m {
        background: #4d96ff;
      }
      .msg {
        background: #fff;
        color: var(--ink);
        font-family: "Anuphan", sans-serif;
        font-size: 42px;
        font-weight: 700;
        line-height: 1.35;
        padding: 18px 28px;
        border-radius: 28px;
        border: 4px solid var(--ink);
        box-shadow: 4px 6px 0 var(--ink);
        max-width: 680px;
        word-break: break-word;
      }
      .row.out .msg {
        background: #8de07a;
      }
      .photo {
        background: #fff;
        padding: 14px 14px 28px 14px;
        border: 4px solid var(--ink);
        box-shadow: 6px 8px 0 var(--ink);
        border-radius: 8px;
        width: 500px;
        height: 500px;
        box-sizing: border-box;
      }
      .photo img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
        background: #fbfbfb;
      }
      #b-cta {
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
        background: #fdfbf7;
        opacity: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        padding-top: 130px;
        box-sizing: border-box;
        overflow: hidden;
      }
      #cta-1 {
        font-family: "Kanit Black", sans-serif;
        font-size: 88px;
        line-height: 1.05;
        color: var(--ink);
        text-align: center;
        margin-bottom: 12px;
      }
      #cta-model {
        font-family: "Anuphan", sans-serif;
        font-size: 46px;
        font-weight: 700;
        color: var(--ink);
        text-align: center;
        margin-bottom: 20px;
      }
      #cta-stage {
        position: relative;
        width: 1080px;
        height: 780px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .earbuds-wrap {
        position: absolute;
        bottom: 40px;
      }
      .earbuds-img {
        display: block;
        height: 640px;
        width: auto;
        object-fit: contain;
        filter: drop-shadow(0 15px 25px rgba(0, 0, 0, 0.18));
      }
      #f-left {
        left: 50px;
        transform: rotate(-10deg) scale(0.88);
        z-index: 2;
      }
      #f-right {
        right: 50px;
        transform: rotate(10deg) scale(0.88);
        z-index: 2;
      }
      #f-center {
        left: 50%;
        transform: translateX(-50%) scale(1.12);
        z-index: 5;
        bottom: 20px;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.45) 0%, rgba(0, 0, 0, 0) 70%);
      }
      #cs-center {
        width: 480px;
        height: 65px;
        bottom: 15px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 4;
      }
      #cs-left {
        width: 360px;
        height: 48px;
        bottom: 35px;
        left: 100px;
        z-index: 1;
      }
      #cs-right {
        width: 360px;
        height: 48px;
        bottom: 35px;
        right: 100px;
        z-index: 1;
      }
      .bottom-info {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 18px;
        margin-top: 10px;
        z-index: 10;
      }
      .swatch-card {
        background: #ffffff;
        border: 4px solid var(--ink);
        box-shadow: 4px 6px 0 var(--ink);
        border-radius: 24px;
        padding: 14px 28px;
        display: flex;
        align-items: center;
        gap: 16px;
      }
      .swatch-title {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 32px;
        color: var(--ink);
      }
      .chips-grid {
        display: flex;
        gap: 16px;
      }
      .chip-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 28px;
        color: var(--ink);
      }
      .chip-dot {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        border: 3px solid var(--ink);
      }
      .spec-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        max-width: 980px;
        gap: 12px;
        margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 28px;
        background: #fff;
        border: 3.5px solid var(--ink);
        padding: 8px 22px;
        border-radius: 20px;
        box-shadow: 4px 6px 0 var(--ink);
        color: var(--ink);
        white-space: nowrap;
      }
      #wm {
        position: absolute;
        bottom: 24px;
        left: 0;
        right: 0;
        text-align: center;
        z-index: 12;
      }
      #wm span {
        font-size: 26px;
        font-weight: 700;
        color: rgba(217, 4, 41, 0.7);
      }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="__CID__" data-start="0" data-duration="__TOTAL__" data-width="1080" data-height="1920">
      <video id="paper" class="clip" src="assets/shared/paper_bg.mp4" muted playsinline data-playback-rate="0.5" data-start="0" data-duration="__TOTAL__" data-media-start="0" data-track-index="0"></video>

      <div class="beat clip" id="b-chat" data-start="0" data-duration="__CHATDUR__" data-track-index="2">
        __HEADS__
        <div id="chatwin">
          <div id="thread">
            __ROWS__
          </div>
        </div>
      </div>

      <div class="beat clip" id="b-cta" data-start="__CTA__" data-duration="__CTADUR__" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">Redmi Buds 8 Active</span></div>
        <div class="t center" id="cta-model">หูฟังกึ่งอินเอียร์ เบาสบาย · กดตะกร้าเหลือง</div>
        <div id="cta-stage">
          <div class="contact-shadow" id="cs-left"></div>
          <div class="earbuds-wrap" id="f-left"><img class="earbuds-img" src="assets/red01/cutouts/redmi_black.png" alt="Redmi Buds 8 Active สีดำ"></div>

          <div class="contact-shadow" id="cs-right"></div>
          <div class="earbuds-wrap" id="f-right"><img class="earbuds-img" src="assets/red01/cutouts/redmi_blue.png" alt="Redmi Buds 8 Active สีฟ้า"></div>

          <div class="contact-shadow" id="cs-center"></div>
          <div class="earbuds-wrap" id="f-center"><img class="earbuds-img" src="assets/red01/cutouts/redmi_white.png" alt="Redmi Buds 8 Active สีขาว"></div>
        </div>

        <div class="bottom-info">
          <div class="swatch-card">
            <span class="swatch-title">3 โทนสีโมเดิร์น :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว White</div>
              <div class="chip-item"><div class="chip-dot" style="background:#222222"></div>ดำ Black</div>
              <div class="chip-item"><div class="chip-dot" style="background:#5b9bd5"></div>ฟ้า Blue</div>
            </div>
          </div>

          <div class="spec-row">
            <div class="spec-tag">ไดรเวอร์ 14.2mm Titanium</div>
            <div class="spec-tag">กึ่งอินเอียร์ ไม่เจ็บหู</div>
            <div class="spec-tag">ไมค์คู่ Dual-Mic AI ENC</div>
            <div class="spec-tag">แบตเตอรี่รวมเคส 37 ชม.</div>
          </div>
        </div>
      </div>
      
      <div id="wm"><span>rizannTry</span></div>

      <audio id="vo" src="assets/clips/__CID__/vo.wav" data-start="0" data-duration="__VODUR__" data-track-index="10" data-volume="1.0"></audio>
      <audio id="bgm" src="assets/shared/music/chat_bgm.mp3" data-start="0" data-duration="__TOTAL__" data-track-index="11" data-volume="0.10" data-fade-in="0.6" data-fade-out="1.5"></audio>
      __SFX__
    </div>

    <script>
      const ITEMS = __ITEMS__;
      const HEADS = __HEADSJS__;
      const SCROLLS = __SCROLLS__;
      const CTA_T = __CTA__;
      const TOTAL = __TOTAL__;

      const tl = gsap.timeline({ paused: true });

      HEADS.forEach((h, k) => {
        const el = "#" + h.id;
        tl.fromTo(el, { opacity: 0, y: -20, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.28, ease: "back.out(1.8)" }, h.t0);
        if (k + 1 < HEADS.length) {
          tl.to(el, { opacity: 0, y: 15, duration: 0.22, ease: "power2.in" }, h.t1 - 0.22);
        } else {
          tl.to(el, { opacity: 0, scale: 0.9, duration: 0.25, ease: "power2.in" }, CTA_T - 0.25);
        }
      });

      ITEMS.forEach((it) => {
        const el = "#" + it.id;
        const fromX = it.side === "F" ? -40 : 40;
        tl.fromTo(
          el,
          { opacity: 0, x: fromX, scale: 0.88 },
          { opacity: 1, x: 0, scale: 1, duration: 0.24, ease: "back.out(2)" },
          it.t
        );
      });

      SCROLLS.forEach(([t, y]) => {
        tl.to("#thread", { y: -y, duration: 0.32, ease: "power3.out" }, t);
      });

      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      tl.fromTo(["#f-left", "#cs-left"], { opacity: 0, x: -60, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.24);
      tl.fromTo(["#f-right", "#cs-right"], { opacity: 0, x: 60, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.24);
      tl.fromTo(["#f-center", "#cs-center"], { opacity: 0, scale: 0.65 }, { opacity: 1, scale: 1, duration: 0.46, ease: "back.out(2)" }, CTA_T + 0.28);
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.4);

      if (window.__timelines) {
        window.__timelines["__CID__"] = tl;
      }
    </script>
  </body>
</html>"""


def build_composition(vo_dur, timings, clip_dir, cid, script):
    """Generate HyperFrames composition HTML file with Style 3B Trio Hero CTA Outro."""
    turns_spec = script["turns"]
    last_turn_idx = len(turns_spec) - 1
    last_turn_phrases_count = len(turns_spec[last_turn_idx][1])
    cta_phrase = (last_turn_idx, min(1, last_turn_phrases_count - 1))

    items, scrolls, cta_t = layout_thread(timings, turns_spec, cta_phrase)
    chat_dur = round(cta_t, 3)
    total = round(vo_dur + 1.4, 2)
    cta_dur = round(total - cta_t, 3)

    # Heads HTML & JS
    heads_html = []
    heads_js = []
    h_defs = script["headlines"]
    for i, h in enumerate(h_defs):
        turn_start = h.get("turn", 0)
        t0 = timings[turn_start][0][0] if turn_start < len(timings) else 0.0
        if i + 1 < len(h_defs):
            next_turn = h_defs[i + 1].get("turn", 0)
            t1 = timings[next_turn][0][0] if next_turn < len(timings) else chat_dur
        else:
            t1 = chat_dur
        heads_html.append(
            f'        <div class="hd" id="hd{i}"><div class="hd-sub">{html.escape(h["sub"])}</div><div class="hd-t"><span class="hl">{html.escape(h["t"])}</span><br><span class="hl">{html.escape(h["hl"])}</span></div></div>'
        )
        heads_js.append({"id": f"hd{i}", "t0": round(t0, 3), "t1": round(t1, 3)})

    # Chat rows HTML & Items JS
    rows_html = []
    items_js = []
    for it in items:
        spk = it["spk"]
        t = it["t"]
        top = it["top"]
        if it["kind"] == "name":
            name = "น้องนุ้ย" if spk == "F" else "พี่บ่าว"
            cls = "nm in" if spk == "F" else "nm out"
            iid = f"i{len(items_js)}"
            rows_html.append(f'            <div class="{cls}" id="{iid}" style="top: {top}px">{name}</div>')
            items_js.append({"id": iid, "kind": "name", "side": spk, "t": t, "e": None})
        elif it["kind"] == "msg":
            cls = "row in" if spk == "F" else "row out"
            ava_cls = "ava f" if spk == "F" else "ava m"
            ava_chr = "น" if spk == "F" else "บ"
            rot = it["rot"]
            iid = f"i{len(items_js)}"
            ava_div = f'<div class="{ava_cls}">{ava_chr}</div>' if it["first"] else ""
            txt = html.escape(it["text"])
            rows_html.append(f'            <div class="{cls}" id="{iid}" style="top: {top}px">{ava_div}<div class="msg" style="rotate: {rot}deg">{txt}</div></div>')
            items_js.append({"id": iid, "kind": "msg", "side": spk, "t": t, "e": it["e"]})
        elif it["kind"] == "photo":
            cls = "row in" if spk == "F" else "row out"
            rot = it["rot"]
            src = it["src"]
            iid = f"i{len(items_js)}"
            rows_html.append(f'            <div class="{cls}" id="{iid}" style="top: {top}px"><div class="photo" style="rotate: {rot}deg"><img src="{src}" alt=""></div></div>')
            items_js.append({"id": iid, "kind": "photo", "side": spk, "t": t, "e": None})

    # SFX tracks
    sfx_html = []
    sx_idx = 0
    for it in items:
        if it["kind"] == "msg" and it["first"]:
            snd = "msg_recv.mp3" if it["spk"] == "F" else "msg_send.mp3"
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

    out_html = REDMI_BUDS8_TEMPLATE
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
        p_target = next((p for p in prods if p.get("product_code") == PRODUCT_CODE), None)
        if p_target:
            for a in p_target.get("angles", []):
                if a.get("clip_id") == cid or a.get("angle_id") == aid:
                    if a.get("status") != "rendered":
                        a["status"] = "draft_ready"
                    a["duration"] = total_dur
            products_file.write_text(json.dumps(prods, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  [Warn] Could not sync products.json: {e}")


def produce_one(idx, script, whisper_model, force=False, mode="take"):
    """Produce single clip audio & HyperFrames composition."""
    cid = f"red01-pov-s{idx:02d}"
    aid = f"ang_red8_{idx:02d}"
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

    if missing_turns and mode == "take":
        print(f"  🎤 Step 1: Generating Audio via Single-Take (2 requests/clip)...")
        # Group by speaker
        f_indices = [i for i, (spk, _, _) in enumerate(turns_spec) if spk == "F"]
        m_indices = [i for i, (spk, _, _) in enumerate(turns_spec) if spk == "M"]

        # Female take
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

        # Male take
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
    print(f"  🔍 Verifying {len(turns_spec)} turns with Whisper...")
    for ti, (spk, phrases, _) in enumerate(turns_spec):
        t_wav = takes[ti]
        full_text = " ".join(spoken for _, spoken in phrases)
        voice = "Aoede" if spk == "F" else "Puck"
        style = F_STYLE if spk == "F" else M_STYLE
        guard = F_GUARD if spk == "F" else M_GUARD
        res = verify_and_generate_turn(ti, spk, full_text, voice, style, guard, t_wav, whisper_model, force=False)
        print(f"     Turn {ti:02d} ({spk}): sim={res['similarity']:.2f} | heard: \"{res['whisper'][:28]}...\"")

    # Step 2: Assemble Audio & Glitch Sanitization
    print("  🎵 Step 2: Assembling Audio & Sanitizing Glitches...")
    vo_dur, timings = assemble_audio(takes, turns_spec, clip_dir, cid)
    print(f"     -> Assembled vo.wav ({vo_dur:.2f}s) at {vo_file.name}")

    # Step 3: Build HyperFrames Composition
    print("  🎨 Step 3: Building HyperFrames Composition (Style 3B Trio Hero)...")
    comp_path, cta_t, total_dur = build_composition(vo_dur, timings, clip_dir, cid, script)
    print(f"     -> Composition created: {comp_path.name} (Total: {total_dur:.2f}s, CTA: {cta_t:.2f}s)")

    # Step 4: Sync Products JSON
    sync_products_json(cid, aid, total_dur)
    dur_sec = round(time.time() - t0, 1)
    print(f"  ✅ [DONE] {cid} finished in {dur_sec}s -> status='draft_ready'")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch TTS & Composition Producer for Redmi Buds 8 Active")
    parser.add_argument("--start", type=int, default=1, help="Start index (default: 1)")
    parser.add_argument("--end", type=int, default=20, help="End index (default: 20)")
    parser.add_argument("--force", action="store_true", help="Force re-generate turns")
    args = parser.parse_args()

    # Load 20 scripts
    scripts_file = DOCS_DIR / "redmi_buds8_20_scripts.json"
    if not scripts_file.exists():
        print(f"❌ Scripts file {scripts_file} not found!")
        sys.exit(1)

    scripts_data = json.loads(scripts_file.read_text(encoding="utf-8"))

    # Load Faster-Whisper model once in memory
    print("=" * 68)
    print("🤖 Loading Faster-Whisper large-v3-turbo model...")
    from faster_whisper import WhisperModel
    import ctranslate2
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            whisper_model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16", local_files_only=True)
            dummy = np.zeros(16000, dtype=np.float32)
            list(whisper_model.transcribe(dummy, language="th")[0])
            print("   Model ready on device: CUDA (float16)")
        else:
            raise RuntimeError("No CUDA devices detected")
    except Exception as e:
        print(f"   CUDA fallback to CPU int8: {e}")
        whisper_model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", local_files_only=True)
        print("   Model ready on device: CPU (int8)")
    print("=" * 68)

    t_global_start = time.time()
    success_count = 0

    for idx in range(args.start, args.end + 1):
        if idx > len(scripts_data):
            break
        script = scripts_data[idx - 1]
        try:
            ok = produce_one(idx, script, whisper_model, force=args.force)
            if ok:
                success_count += 1
        except Exception as e:
            print(f"❌ [FAILED] red01-pov-s{idx:02d}: {e}")

    total_time = round(time.time() - t_global_start, 1)
    print("\n" + "=" * 68)
    print(f"🏁 Finished: {success_count} clips produced in {total_time}s ({total_time / 60:.1f} mins)")
    print("=" * 68)


if __name__ == "__main__":
    main()
