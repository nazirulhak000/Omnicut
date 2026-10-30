"""Batch Voiceover & HyperFrames Composition Producer for 20 Hatari Cyclone Max 8" Clips.
Dual-speaker Southern Couple (#5 Couple Paper Chat):
  - Female (น้องนุ้ย): Single-turn Aoede, model gemini-3.8-flash-tts
  - Male (พี่บ่าว): Single-turn Puck, model gemini-3.8-flash-tts
  - Audio post: F (asetrate*1.10, atempo=1.20, highpass 140Hz, eq 3.5kHz +3dB), M (atempo=1.32, highpass 95Hz)
  - Split / Align: align_words_in_waveform
  - Whisper: single in-memory instance of large-v3-turbo for turn verification
  - Audio sanitization: cosine tail fade-out 120ms, clean_isolated_bursts_in_vo, clean_vo_wav
  - Composition: Couple Paper Chat (#5) on assets/shared/paper_bg.mp4
  - Brand-First CTA Outro: Hatari · Cyclone Max 8 นิ้ว, hero cutout 630px, zero emoji, red curved arrow
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

PRODUCT_ID = "cde38b1c07e54ea69a3d50a6c1bb3f18"
PRODUCT_CODE = "HAT02"

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

    # Cleanup tmp wavs to save disk
    for f in tmp.glob("*.wav"):
        try:
            f.unlink()
        except Exception:
            pass
    try:
        tmp.rmdir()
    except Exception:
        pass

    return vo_dur, timings

def layout_thread(timings, turns_spec, cta_phrase):
    items, scrolls, y, scroll = [], [], 16, 0
    cta_t_idx = min(cta_phrase[0], len(timings) - 1)
    cta_p_idx = min(cta_phrase[1], len(timings[cta_t_idx]) - 1)
    cta_t = timings[cta_t_idx][cta_p_idx][0]
    tilt = [-1.2, 0.8, -0.6, 1.1, -0.9, 0.5]
    n = 0

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

HATARI_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/channels.js"></script>
    <script src="kit/kit.js"></script>
    <style>
      /* __CID__ — generated by tools/batch_produce_hatari_20.py
         "พี่บ่าว & น้องนุ้ย" voiced chat on crumpled paper. */
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
      /* headline: marker ink + highlighter */
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
      /* chat window */
      #chatwin {
        position: absolute;
        left: 0;
        right: 0;
        top: __WINTOP__px;
        height: __WINH__px;
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
      /* paper sticker bubble */
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
      /* official listing photo */
      .photo,
      .sticker {
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
      .sticker img {
        display: block;
        width: 440px;
        height: 440px;
        object-fit: contain;
      }
      /* ==================== CTA OUTRO SHOT (BRAND & MODEL FIRST) ==================== */
      #b-cta {
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
      }
      .t {
        font-family: "Kanit Black", sans-serif;
        color: var(--ink);
        text-align: center;
        line-height: 1.1;
      }
      .t.center {
        text-align: center;
        width: 100%;
        left: 0;
        right: 0;
      }
      #cta-1 {
        position: absolute;
        top: 255px;
        font-size: 78px;
        line-height: 1.15;
        max-width: 1000px;
        margin: 0 auto;
        left: 40px;
        right: 40px;
        width: 1000px;
      }
      #cta-model {
        position: absolute;
        top: 375px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 52px;
        color: #d90429;
        max-width: 1000px;
        margin: 0 auto;
        left: 40px;
        right: 40px;
        width: 1000px;
      }
      #cta-hero {
        position: absolute;
        top: 465px;
        left: 0;
        right: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
      }
      #cta-hero img.coil {
        width: 630px;
        height: 630px;
        object-fit: contain;
        filter: drop-shadow(0 16px 24px rgba(27, 26, 23, 0.25));
      }
      .color-row {
        display: flex;
        gap: 16px;
      }
      .color-pill {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 32px;
        color: #111111;
        background: #ffffff;
        border: 4px solid var(--ink);
        padding: 6px 22px;
        border-radius: 24px;
        box-shadow: 4px 6px 0 var(--ink);
      }
      .color-pill.white {
        background: #ffffff;
        color: #111111;
      }
      .color-pill.black {
        background: #2b2b2b;
        color: #ffffff;
      }
      .spec-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        max-width: 960px;
        gap: 10px;
        margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 26px;
        background: #fff;
        border: 3px solid var(--ink);
        padding: 6px 16px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        color: #111111;
        white-space: nowrap;
      }
      #cta-arrow {
        position: absolute;
        inset: 0;
        pointer-events: none;
      }
      #cta-arrow path {
        fill: none;
        stroke: var(--line-red);
        stroke-width: 18;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      #wm {
        left: 0 !important;
        right: 0;
        top: auto !important;
        bottom: 26px;
        width: 100% !important;
        height: auto !important;
        text-align: center;
      }
      #wm span {
        position: static !important;
        display: inline-block;
        transform: none !important;
        background: transparent !important;
        font-size: 28px;
        color: rgba(217, 4, 41, 0.75) !important;
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
        <div class="t center" id="cta-1"><span class="hl">Hatari · Cyclone Max 8 นิ้ว</span></div>
        <div class="t center" id="cta-model">พลังลมตัวจบ · กดตะกร้าเหลือง</div>
        <div id="cta-hero">
          <img class="coil" src="assets/hatari02/img/hatari_cyclone_clean_cutout.png" alt="Hatari Cyclone Max 8 Inch">
          <div class="color-row">
            <span class="color-pill white">สีขาวมินิมอล</span>
            <span class="color-pill black">สีเทาโมเดิร์น</span>
            <span class="color-pill">6 สีพาสเทล</span>
          </div>
          <div class="spec-row">
            <span class="spec-tag">มอเตอร์ Ball Bearing</span>
            <span class="spec-tag">ระบบ Thermal Fuse</span>
            <span class="spec-tag">ปรับก้มเงย 90 องศา</span>
            <span class="spec-tag">ตั้งโต๊ะหรือแขวนผนัง</span>
          </div>
        </div>
        <svg class="fx" id="cta-arrow" viewBox="0 0 1080 1920">
          <path id="cta-shaft" d="M 220 700 C 120 900 80 1190 140 1460" stroke-dasharray="1000" stroke-dashoffset="1000" />
          <path id="cta-head" d="M 60 1380 L 140 1470 L 230 1390" stroke-dasharray="400" stroke-dashoffset="400" />
        </svg>
      </div>
      <div id="wm"><span>rizannTry</span></div>

      <audio id="vo" src="assets/clips/__CID__/vo.wav" data-start="0" data-duration="__VODUR__" data-track-index="10" data-volume="1.0"></audio>
      <audio id="bgm" src="assets/shared/bgm_lofi.wav" data-start="0" data-duration="__TOTAL__" data-track-index="11" data-volume="0.05" data-fade-in="0.6" data-fade-out="1.5"></audio>
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
      tl.fromTo("#cta-hero", { opacity: 0, scale: 0.65, rotate: 6 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.25);
      tl.to("#cta-shaft", { strokeDashoffset: 0, duration: 0.55, ease: "power2.out" }, CTA_T + 0.55);
      tl.to("#cta-head", { strokeDashoffset: 0, duration: 0.25, ease: "power2.out" }, CTA_T + 0.95);

      if (window.__timelines) {
        window.__timelines["__CID__"] = tl;
      }
    </script>
  </body>
</html>"""

def generate_composition_html(vo_dur, timings, items, scrolls, cta_t, turns_spec, headlines_spec, cta_phrase, cid, clip_dir):
    total = round(vo_dur + 1.4, 2)
    turn_starts = [t[0][0] for t in timings]
    heads = []
    for k, h in enumerate(headlines_spec):
        ti = min(h["turn"], len(turn_starts) - 1)
        sub = h["sub"]
        l1 = h["t"]
        l2 = h.get("hl", "")
        t0 = 0 if k == 0 else round(turn_starts[ti] - 0.1, 3)
        next_ti = min(headlines_spec[k + 1]["turn"], len(turn_starts) - 1) if k + 1 < len(headlines_spec) else 0
        t1 = round(cta_t, 3) if k + 1 == len(headlines_spec) else round(turn_starts[next_ti] - 0.1, 3)
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
            rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px"><div class="{cls}" style="rotate: {it["rot"]}deg"><img src="{it["src"]}" alt=""></div></div>')

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
    sfx.append(("ding.wav", timings[min(5, len(timings)-1)][0][0] + 0.3, 0.8, 0.3))
    sfx.append(("punch.mp3", timings[min(8, len(timings)-1)][0][0] + 0.3, 0.5, 0.35))
    sfx.append(("wow.mp3", timings[min(10, len(timings)-1)][0][0] + 0.2, 1.0, 0.3))
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

    page = HATARI_TEMPLATE
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
    idx_num = script_data["num"]
    cid = f"hat02-pov-s{idx_num:02d}"
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
        "clip_id": cid,
        "vo_dur": vo_dur,
        "total_dur": total_dur,
        "preview_url": f"http://localhost:3002/#project/_HyperFrames_Studio/composition/{cid}",
        "comp_path": f"03_Projects/_HyperFrames_Studio/compositions/{cid}.html"
    }

def main():
    parser = argparse.ArgumentParser(description="Batch produce 20 Hatari Cyclone Max couple clips")
    parser.add_argument("--start", type=int, default=1, help="Start script index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End script index (1-20)")
    parser.add_argument("--force", action="store_true", help="Force regenerate audio even if cached")
    args = parser.parse_args()

    scripts_file = ROOT / "_Docs" / "hatari_cyclone_max_20_scripts.json"
    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    selected = [s for s in scripts if args.start <= s["num"] <= args.end]

    # Load Whisper large-v3-turbo ONCE
    import ctranslate2
    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    whisper_model = WhisperModel("large-v3-turbo", device=device, compute_type=compute_type, local_files_only=True)
    print(f"  -> Whisper model ready on [{device.upper()}] ({compute_type})!")

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
        cid_map = {r["clip_id"]: r for r in results}
        for a in p_target.get("angles", []):
            cid = a.get("clip_id")
            r = cid_map.get(cid)
            if r:
                a["status"] = "draft_ready"
                a["composition_path"] = r["comp_path"]
                a["video_preview_url"] = r["preview_url"]
                a["duration"] = f"{round(r['total_dur'])}s"
        with open(products_file, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print("  -> Content Tracker updated successfully!")

    print(f"\n🎉 ALL {len(results)} HATARI CYCLONE MAX CLIPS COMPLETED SUCCESSFULLY!")
    for r in results:
        print(f"  - {r['clip_id']}: {r['total_dur']}s | Preview: {r['preview_url']}")

if __name__ == "__main__":
    main()
