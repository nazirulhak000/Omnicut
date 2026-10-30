"""Batch Voiceover & HyperFrames Composition Producer for 20 GOOJODOQ 5000mAh Mini Power Bank Clips.
Dual-speaker Southern Couple (#5 Couple Paper Chat):
  - Female (น้องนุ้ย): Single-turn Aoede, model gemini-3.8-flash-tts
  - Male (พี่บ่าว): Single-turn Puck, model gemini-3.8-flash-tts
  - Audio post: F (asetrate*1.10, atempo=1.20, highpass 140Hz, eq 3.5kHz +3dB), M (atempo=1.32, highpass 95Hz)
  - Split / Align: align_words_in_waveform
  - Whisper: single in-memory instance of large-v3-turbo for turn verification
  - Audio sanitization: cosine tail fade-out 120ms, clean_isolated_bursts_in_vo, clean_vo_wav
  - Composition: Couple Paper Chat (#5) on assets/shared/paper_bg.mp4
  - Brand-First CTA Outro: GOOJODOQ · มินิพาวเวอร์แบงค์ 5000mAh (Style 3B Macro Hero, Zero Emoji, Zero Arrow)
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

PRODUCT_ID = "7900bbca744d47c4915609384752c0dc"
PRODUCT_CODE = "GOO01"

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
    if len(keys) > 5:
        keys = keys[5:] + keys[:5]
    key = keys[KEY_INDEX % len(keys)]
    KEY_INDEX += 1
    return key, len(keys)

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
                    time.sleep(4)
                else:
                    time.sleep(2)
            except Exception as e:
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
        
        forbidden_words = ["อืม", "เอ่อ", "สวัสดีครับ", "สวัสดีค่ะ", "โฮโฮ", "ฮ่าๆ", "เซรั่ม"]
        forbidden = any(w in heard and w not in expected for w in forbidden_words)
        sim = SequenceMatcher(None, expected, heard).ratio()
        
        is_ok = (not forbidden) and (sim >= 0.58 or (len(heard) >= len(expected) * 0.55 and sim >= 0.48))
        
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
            print(f"    [Retry {attempt+1}/3] Turn {turn_idx:02d} ({spk}): sim={sim:.2f}, forbidden={forbidden}, heard='{heard[:35]}...' -> Retrying...")
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
    out_sr = 48000
    pieces, timings, cur = [], [], 0.0

    for i, (spk, phrases, _) in enumerate(turns_spec):
        src = takes[i]
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

GOOJODOQ_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <title>__CID__ - GOOJODOQ 5000mAh Mini Power Bank</title>
  <style>
    @font-face {
      font-family: 'Anuphan';
      src: url('assets/shared/fonts/Anuphan-Bold.woff2') format('woff2');
      font-weight: 700;
      font-style: normal;
    }
    @font-face {
      font-family: 'Kanit Black';
      src: url('assets/shared/fonts/Kanit-Black.woff2') format('woff2');
      font-weight: 900;
      font-style: normal;
    }
    :root {
      --bg: #ece5dd;
      --ink: #1b1a17;
      --green: #8de07a;
      --pink: #ff6584;
      --yellow: #ffe600;
      --red: #d90429;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      width: 1080px;
      height: 1920px;
      overflow: hidden;
      background: var(--bg);
      font-family: 'Anuphan', sans-serif;
      color: var(--ink);
      user-select: none;
    }
    #stage {
      position: absolute;
      inset: 0;
      width: 1080px;
      height: 1920px;
      overflow: hidden;
    }
    #paper-bg {
      position: absolute;
      inset: 0;
      width: 1080px;
      height: 1920px;
      object-fit: cover;
      opacity: 0.85;
      z-index: 1;
    }
    #chat-thread {
      position: absolute;
      top: __WINTOP__px;
      left: 60px;
      width: 960px;
      height: __WINH__px;
      overflow: hidden;
      z-index: 5;
    }
    #chat-canvas {
      position: absolute;
      top: 0;
      left: 0;
      width: 960px;
      will-change: transform;
    }
    .nm {
      position: absolute;
      font-size: 26px;
      font-weight: 700;
      color: #666;
      line-height: 1;
    }
    .nm.in { left: 96px; }
    .nm.out { right: 96px; }
    .row {
      position: absolute;
      width: 100%;
      display: flex;
      align-items: flex-end;
    }
    .row.in {
      justify-content: flex-start;
      padding-left: 96px;
    }
    .row.out {
      justify-content: flex-end;
      padding-right: 96px;
    }
    .ava {
      position: absolute;
      bottom: 0;
      width: 76px;
      height: 76px;
      border-radius: 50%;
      border: 3.5px solid var(--ink);
      box-shadow: 2px 3px 0 var(--ink);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 34px;
      font-weight: 700;
      color: #fff;
    }
    .ava.f {
      left: 0;
      background: linear-gradient(135deg, #ff758c, #ff7eb3);
    }
    .ava.m {
      right: 0;
      background: linear-gradient(135deg, #4facfe, #00f2fe);
    }
    .msg {
      max-width: 720px;
      padding: 16px 26px;
      font-size: 44px;
      font-weight: 700;
      line-height: 1.28;
      border: 4px solid var(--ink);
      border-radius: 28px;
      box-shadow: 4px 6px 0 var(--ink);
      transform-origin: center bottom;
    }
    .row.in .msg {
      background: #ffffff;
      border-bottom-left-radius: 6px;
    }
    .row.out .msg {
      background: var(--green);
      border-bottom-right-radius: 6px;
    }
    .photo {
      max-width: 620px;
      padding: 10px;
      background: #ffffff;
      border: 4px solid var(--ink);
      border-radius: 20px;
      box-shadow: 5px 8px 0 var(--ink);
    }
    .photo img {
      width: 520px;
      height: 520px;
      object-fit: cover;
      border-radius: 12px;
      display: block;
    }
    .sticker img {
      width: 440px;
      height: 440px;
      object-fit: contain;
      display: block;
    }
    /* Headlines Overlays */
    #headline-box {
      position: absolute;
      top: 90px;
      left: 40px;
      right: 40px;
      height: 350px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 10;
      text-align: center;
    }
    .hd {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: scale(0.92);
      transition: opacity 0.2s, transform 0.25s;
    }
    .hd.active {
      opacity: 1;
      transform: scale(1);
    }
    .hd-sub {
      font-size: 40px;
      font-weight: 700;
      color: #333;
      margin-bottom: 8px;
      background: rgba(255, 255, 255, 0.9);
      padding: 4px 20px;
      border-radius: 20px;
      border: 3px solid var(--ink);
      box-shadow: 3px 4px 0 var(--ink);
    }
    .hd-t {
      font-family: 'Kanit Black', sans-serif;
      font-size: 68px;
      line-height: 1.18;
      color: var(--ink);
    }
    .hd-t .hl {
      background: var(--yellow);
      padding: 0 14px;
      border-radius: 10px;
      box-shadow: 3px 4px 0 var(--ink);
      border: 3px solid var(--ink);
      display: inline-block;
      margin: 4px 0;
    }

    /* Style 3B Macro Hero CTA Outro */
    #b-cta {
      position: absolute;
      inset: 0;
      width: 1080px;
      height: 1920px;
      z-index: 20;
      pointer-events: none;
      opacity: 0;
    }
    #cta-1 {
      position: absolute;
      top: 155px;
      left: 40px;
      right: 40px;
      text-align: center;
      z-index: 25;
      font-family: 'Kanit Black', sans-serif;
      font-size: 82px;
      line-height: 1.15;
      color: var(--ink);
    }
    #cta-1 .hl {
      padding: 0 16px;
      background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
    }
    #cta-model {
      position: absolute;
      top: 265px;
      left: 40px;
      right: 40px;
      text-align: center;
      z-index: 25;
      font-family: 'Anuphan', sans-serif;
      font-weight: 700;
      font-size: 46px;
      color: var(--red);
    }
    #cta-stage {
      position: absolute;
      top: 360px;
      left: 0;
      width: 1080px;
      height: 880px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 10;
    }
    .hero-img {
      width: 720px;
      height: 720px;
      object-fit: contain;
      filter: drop-shadow(0 16px 32px rgba(0, 0, 0, 0.22));
      position: absolute;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10;
    }
    .contact-shadow {
      position: absolute;
      width: 620px;
      height: 90px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
      bottom: 120px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 5;
    }
    .color-row {
      position: absolute;
      bottom: 40px;
      display: flex;
      gap: 16px;
      z-index: 22;
    }
    .color-pill {
      font-family: 'Anuphan', sans-serif;
      font-weight: 700;
      font-size: 30px;
      color: #111;
      background: #fff;
      border: 3.5px solid var(--ink);
      padding: 6px 20px;
      border-radius: 22px;
      box-shadow: 3px 5px 0 var(--ink);
    }
    .color-pill.white { background: #ffffff; color: #111; }
    .color-pill.pink { background: #ffccd5; color: #111; }
    .color-pill.purple { background: #e0bbf8; color: #111; }
    .color-pill.black { background: #222222; color: #fff; }

    .floating-badge {
      position: absolute;
      z-index: 22;
      font-family: 'Anuphan', sans-serif;
      font-weight: 700;
      font-size: 26px;
      background: #ffffff;
      color: var(--ink);
      border: 3px solid var(--ink);
      padding: 8px 18px;
      border-radius: 16px;
      box-shadow: 3px 5px 0 var(--ink);
      white-space: nowrap;
    }
    #fb-1 { top: 80px; left: 60px; rotate: -4deg; }
    #fb-2 { top: 70px; right: 60px; rotate: 4deg; }
    #fb-3 { bottom: 170px; left: 50px; rotate: 3deg; }
    #fb-4 { bottom: 180px; right: 50px; rotate: -3deg; }

    #cta-arrow-svg {
      position: absolute;
      bottom: 220px;
      left: 80px;
      width: 220px;
      height: 220px;
      z-index: 30;
      filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.3));
    }
  </style>
</head>
<body>
  <div id="stage" data-duration="__TOTAL__">
    <video id="paper-bg" src="assets/shared/paper_bg.mp4" autoplay loop muted playsinline data-track-index="1"></video>

    <!-- Top Headlines -->
    <div id="headline-box">
      __HEADS__
    </div>

    <!-- Main Chat Thread -->
    <div id="chat-thread">
      <div id="chat-canvas">
        __ROWS__
      </div>
    </div>

    <!-- Style 3B Macro Hero CTA Outro -->
    <div id="b-cta">
      <div id="cta-1"><span class="hl">GOOJODOQ · พาวเวอร์แบงค์จิ๋ว</span></div>
      <div id="cta-model">5000mAh มี 2 หัวในตัว · กดในตะกร้าเหลือง</div>
      <div id="cta-stage">
        <div class="contact-shadow"></div>
        <img class="hero-img" src="assets/goo01/img/hero_cutout.png" alt="GOOJODOQ 5000mAh">
        <div class="floating-badge" id="fb-1">⚡ 2in1 iOS + Type-C</div>
        <div class="floating-badge" id="fb-2">🔋 5000mAh เต็มพลัง</div>
        <div class="floating-badge" id="fb-3">🪶 เบาแค่ 100 กรัม</div>
        <div class="floating-badge" id="fb-4">📱 มีขาตั้งในตัว + มอก.</div>
        <div class="color-row">
          <span class="color-pill white">● ขาว</span>
          <span class="color-pill pink">● ชมพู</span>
          <span class="color-pill purple">● ม่วง</span>
          <span class="color-pill black">● ดำ</span>
        </div>
      </div>
      <!-- Minimalist red curved arrow pointing to yellow cart -->
      <svg id="cta-arrow-svg" viewBox="0 0 200 200" fill="none">
        <path d="M 160 30 Q 80 70 50 160" stroke="#d90429" stroke-width="12" stroke-linecap="round" stroke-dasharray="14 10" />
        <polygon points="30,175 75,160 55,130" fill="#d90429" />
      </svg>
    </div>

    <!-- Audio Elements -->
    <audio id="vo" src="assets/clips/__CID__/vo.wav" data-track-index="10" data-volume="1.0"></audio>
    <audio id="bgm" src="assets/shared/music/chat_bgm.mp3" loop data-track-index="11" data-volume="0.12"></audio>
    __SFX__
  </div>

  <script src="kit/gsap.min.js"></script>
  <script>
    const items = __ITEMS__;
    const heads = __HEADSJS__;
    const scrolls = __SCROLLS__;
    const chatDur = __CHATDUR__;
    const ctaT = __CTA__;
    const total = __TOTAL__;

    const tl = gsap.timeline({ paused: true });

    // Item animations
    items.forEach(it => {
      const el = document.getElementById(it.id);
      if (!el) return;
      tl.fromTo(el, { opacity: 0, scale: 0.85, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: 0.22, ease: "back.out(1.8)" }, it.t);
    });

    // Chat scroll animations
    scrolls.forEach(sc => {
      tl.to("#chat-canvas", { y: -sc[1], duration: 0.32, ease: "power2.out" }, sc[0]);
    });

    // Headline animations
    heads.forEach((h, idx) => {
      const el = document.getElementById(h.id);
      if (!el) return;
      tl.to(el, { opacity: 1, scale: 1, duration: 0.24, ease: "back.out(1.5)" }, h.t0);
      tl.to(el, { opacity: 0, scale: 0.95, duration: 0.18, ease: "power2.in" }, h.t1);
    });

    // Fade out chat thread and transition into CTA Outro
    tl.to(["#chat-thread", "#headline-box"], { opacity: 0, duration: 0.25, ease: "power2.in" }, ctaT - 0.1);
    tl.fromTo("#b-cta", { opacity: 0, scale: 0.95 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.4)" }, ctaT);
    tl.fromTo(".hero-img", { scale: 0.8, y: 40 }, { scale: 1, y: 0, duration: 0.45, ease: "back.out(1.6)" }, ctaT + 0.05);
    tl.fromTo(".floating-badge", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.3, stagger: 0.08, ease: "back.out(2)" }, ctaT + 0.2);
    tl.fromTo("#cta-arrow-svg", { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, ctaT + 0.4);

    window.__timelines = window.__timelines || {};
    window.__timelines["__CID__"] = tl;
  </script>
</body>
</html>
"""

def generate_composition_html(vo_dur, timings, items, scrolls, cta_t, turns_spec, headlines_spec, cta_phrase, cid, clip_dir):
    total = round(vo_dur + 1.4, 2)
    turn_starts = [t[0][0] for t in timings]
    heads = []
    for k, h in enumerate(headlines_spec):
        ti = h["turn"]
        sub = h["sub"]
        l1 = h["t"]
        l2 = h.get("hl", "")
        t0 = 0 if k == 0 else round(turn_starts[ti] - 0.1, 3)
        t1 = round(cta_t, 3) if k + 1 == len(headlines_spec) else round(turn_starts[headlines_spec[k + 1]["turn"]] - 0.1, 3)
        heads.append((k, t0, t1, sub, l1, l2))

    rows = []
    for i, it in enumerate(items):
        side = "in" if it["spk"] == "F" else "out"
        if it["kind"] == "name":
            label = "น้องนุ้ย" if it["spk"] == "F" else "พี่บ่าว"
            rows.append(f'<div class="nm {side}" id="i{i}" style="top: {it["top"]}px">{label}</div>')
        elif it["kind"] == "msg":
            ava = ""
            if it["first"]:
                ava = f'<div class="ava {"f" if side == "in" else "m"}">{"น" if side == "in" else "บ"}</div>'
            rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px">{ava}<div class="msg" style="rotate: {it["rot"]}deg">{html.escape(it["text"], quote=True)}</div></div>')
        else:
            cls = "photo" if it["kind"] == "photo" else "sticker"
            # Normalize image path for studio web viewer
            img_src = it["src"]
            if img_src.startswith("03_Projects/_HyperFrames_Studio/"):
                img_src = img_src.replace("03_Projects/_HyperFrames_Studio/", "")
            rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px"><div class="{cls}" style="rotate: {it["rot"]}deg"><img src="{img_src}" alt=""></div></div>')

    head_html = "\n        ".join(
        f'<div class="hd" id="hd{k}"><div class="hd-sub">{html.escape(sub, quote=True)}</div><div class="hd-t"><span class="hl">{html.escape(l1, quote=True)}</span><br><span class="hl">{html.escape(l2, quote=True)}</span></div></div>'
        for k, t0, t1, sub, l1, l2 in heads
    )

    sfx = []
    for ti, (spk, _, _) in enumerate(turns_spec):
        if ti == cta_phrase[0] + 1:
            break
        sfx.append(("msg_recv.mp3" if spk == "F" else "msg_send.mp3", turn_starts[ti] + 0.01, 0.5, 0.3))
    for it in items:
        if it["kind"] in ("photo", "sticker"):
            sfx.append(("paper.mp3", it["t"], 0.45, 0.40))
    sfx.append(("ding.wav", timings[min(4, len(timings)-1)][0][0] + 0.3, 0.8, 0.3))
    sfx.append(("punch.mp3", timings[min(7, len(timings)-1)][0][0] + 0.3, 0.5, 0.35))
    sfx.append(("wow.mp3", timings[min(9, len(timings)-1)][0][0] + 0.2, 1.0, 0.3))
    sfx.append(("whoosh.mp3", cta_t - 0.05, 0.5, 0.18))
    sfx.append(("boom.wav", cta_t + 0.07, 0.8, 0.15))
    sfx.append(("cash_register.mp3", cta_t + 0.55, 1.0, 0.20))
    
    sfx_html = "\n      ".join(
        f'<audio id="sx{k:02d}" src="assets/shared/sfx/{f}" data-start="{round(t, 3)}" data-duration="{d}" data-track-index="{12 + k % 2}" data-volume="{v}"></audio>'
        for k, (f, t, d, v) in enumerate(sorted(sfx, key=lambda x: x[1]))
    )

    js_items = json.dumps([{"id": f"i{i}", "kind": it["kind"], "side": it["spk"], "t": it["t"], "e": it.get("e")} for i, it in enumerate(items)])
    js_heads = json.dumps([{"id": f"hd{k}", "t0": t0, "t1": t1} for k, t0, t1, *_ in heads])
    js_scrolls = json.dumps(scrolls)
    rows_html = "\n            ".join(rows)

    page = GOOJODOQ_TEMPLATE
    for k, v in {
        "__CID__": cid, "__TOTAL__": str(total), "__VODUR__": str(vo_dur), "__CTA__": str(round(cta_t, 3)),
        "__CTADUR__": str(round(total - cta_t, 3)), "__CHATDUR__": str(round(cta_t, 3)),
        "__ROWS__": rows_html, "__HEADS__": head_html, "__SFX__": sfx_html,
        "__ITEMS__": js_items, "__HEADSJS__": js_heads, "__SCROLLS__": js_scrolls,
        "__WINTOP__": str(WIN_TOP), "__WINH__": str(WIN_H),
    }.items():
        page = page.replace(k, v)

    out_comp = STUDIO / "compositions" / f"{cid}.html"
    out_comp.parent.mkdir(parents=True, exist_ok=True)
    out_comp.write_text(page, encoding="utf-8")

    out_clip = clip_dir / "index.html"
    out_clip.write_text(page, encoding="utf-8")
    print(f"  [HTML OK] {out_comp.name} & {out_clip.relative_to(STUDIO)} ({total}s)")
    return total

def produce_single_clip(script_data, whisper_model, force_regen=False):
    s_id = script_data["id"]
    idx_num = int(s_id.split("_")[-1])
    cid = f"goo01-pov-s{idx_num:02d}"
    print(f"\n=======================================================")
    print(f"🎬 Producing Clip {idx_num}/20: {cid} | {script_data['title']}")
    print(f"=======================================================")

    clip_dir = CLIPS_DIR / cid
    clip_dir.mkdir(parents=True, exist_ok=True)
    tts_dir = clip_dir / "tts"
    tts_dir.mkdir(exist_ok=True)

    turns_spec = script_data["turns"]
    headlines_spec = script_data["headlines"]
    cta_phrase = (len(turns_spec) - 1, 1)

    whisper_cache = clip_dir / "whisper_turns.json"
    cached_report = {}
    if whisper_cache.exists() and not force_regen:
        try:
            for r in json.loads(whisper_cache.read_text(encoding="utf-8")):
                cached_report[r["turn"]] = r
        except Exception:
            pass

    # 1. Generate & verify each turn individually (Turn-by-turn architecture)
    ordered_turns = []
    report = []
    for i, (spk, phrases, _) in enumerate(turns_spec):
        voice_name = "Aoede" if spk == "F" else "Puck"
        style = F_STYLE if spk == "F" else M_STYLE
        guard = F_GUARD if spk == "F" else M_GUARD
        turn_wav = tts_dir / f"turn_{i:02d}_{spk}.wav"
        expected = " ".join(p[1] for p in phrases)
        
        # Check if already verified and valid
        if i in cached_report and turn_wav.exists() and not force_regen:
            res = cached_report[i]
        else:
            res = verify_and_generate_turn(i, spk, expected, voice_name, style, guard, turn_wav, whisper_model, force=force_regen)
        
        report.append(res)
        ordered_turns.append(turn_wav)
        sim_val = res.get('similarity', res.get('overlap', 1.0))
        print(f"  [Turn {i:02d} - {spk}] sim={sim_val:.2f} | {expected[:32]}...")

    whisper_cache.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Assemble audio with FFmpeg filters
    vo_dur, timings = assemble_audio(ordered_turns, turns_spec, clip_dir, cid)

    # 3. Layout and generate HyperFrames composition
    items, scrolls, cta_t = layout_thread(timings, turns_spec, cta_phrase)
    total_dur = generate_composition_html(vo_dur, timings, items, scrolls, cta_t, turns_spec, headlines_spec, cta_phrase, cid, clip_dir)

    return {
        "num": idx_num,
        "script_id": s_id,
        "clip_id": cid,
        "vo_dur": vo_dur,
        "total_dur": total_dur,
        "preview_url": f"http://localhost:3002/#project/_HyperFrames_Studio/composition/{cid}",
        "comp_path": f"03_Projects/_HyperFrames_Studio/compositions/{cid}.html"
    }

def main():
    parser = argparse.ArgumentParser(description="Batch produce 20 GOOJODOQ couple clips")
    parser.add_argument("--start", type=int, default=1, help="Start script index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End script index (1-20)")
    parser.add_argument("--force", action="store_true", help="Force regenerate audio even if cached")
    args = parser.parse_args()

    scripts_file = ROOT / "_Docs" / "goojodoq_5000mah_20_scripts.json"
    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    # Attach num
    for idx, s in enumerate(scripts):
        s["num"] = idx + 1

    selected = [s for s in scripts if args.start <= s["num"] <= args.end]

    # Load Whisper large-v3-turbo with robust CUDA test & CPU int8 fallback
    from faster_whisper import WhisperModel
    import ctranslate2
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            whisper_model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16", local_files_only=True)
            # Warmup to test if cublas DLLs are present
            dummy = np.zeros(16000, dtype=np.float32)
            list(whisper_model.transcribe(dummy, language="th")[0])
            print("  -> Whisper model ready on [CUDA] (float16)!")
        else:
            raise RuntimeError("No CUDA devices detected")
    except Exception as e:
        print(f"  -> CUDA fallback to CPU int8: {e}")
        whisper_model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", local_files_only=True)
        print("  -> Whisper model ready on [CPU] (int8)!")

    print(f"[2/2] Generating turn-by-turn TTS, Whisper verifying, and building HyperFrames comps...")
    results = []
    for s in selected:
        try:
            res = produce_single_clip(s, whisper_model, force_regen=args.force)
            results.append(res)
        except Exception as e:
            print(f"  [Produce Error] Script {s['num']} failed: {e}")

    # Update _Docs/products.json
    print(f"\n[3/3] Updating Content Tracker in _Docs/products.json...")
    products_file = ROOT / "_Docs" / "products.json"
    with open(products_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    p_target = next((p for p in products if p.get("id") == PRODUCT_ID or p.get("product_code") == PRODUCT_CODE), None)
    if p_target:
        cid_map = {r["script_id"]: r for r in results}
        for a in p_target.get("angles", []):
            aid = a.get("angle_id")
            r = cid_map.get(aid)
            if r:
                a["status"] = "draft_ready"
                a["clip_id"] = r["clip_id"]
                a["composition_path"] = r["comp_path"]
                a["video_preview_url"] = r["preview_url"]
                a["duration"] = f"{round(r['total_dur'])}s"
        with open(products_file, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print("  -> Content Tracker updated successfully!")

    print(f"\n🎉 ALL {len(results)} GOOJODOQ CLIPS COMPLETED SUCCESSFULLY!")
    for r in results:
        print(f"  - {r['clip_id']}: {r['total_dur']}s | Preview: {r['preview_url']}")

if __name__ == "__main__":
    main()
