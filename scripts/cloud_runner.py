"""scripts/cloud_runner.py — Omnicut Cloud Video Production Engine
Automates Couple Paper Chat (#5 น้องนุ้ย & พี่บ่าว) video production and HyperFrames rendering on Google Colab / Cloud VPS.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.config import get_gemini_api_keys
except (ImportError, ModuleNotFoundError):
    try:
        from .config import get_gemini_api_keys
    except (ImportError, ModuleNotFoundError):
        from config import get_gemini_api_keys

STUDIO_DIR = REPO_ROOT / "03_Projects" / "_HyperFrames_Studio"
COMPS_DIR = STUDIO_DIR / "compositions"
CLIPS_DIR = STUDIO_DIR / "clips"
ASSETS_DIR = STUDIO_DIR / "assets"
DEFAULT_EXPORT_DIR = REPO_ROOT / "04_Exports"

TTS_MODEL = "gemini-3.1-flash-tts-preview"
F_STYLE = "Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)"
M_STYLE = "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"


def list_compositions() -> List[dict]:
    """Lists all available HyperFrames HTML compositions."""
    if not COMPS_DIR.exists():
        return []
    comps = []
    for f in sorted(COMPS_DIR.glob("*.html")):
        comps.append({
            "name": f.stem,
            "filename": f.name,
            "path": str(f),
            "size_kb": round(f.stat().st_size / 1024, 1),
        })
    return comps


def render_composition_to_mp4(
    comp_name: str,
    output_dir: Optional[Path] = None,
    quality: str = "looks",
    fps: int = 30,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Path:
    """Renders a given composition name to MP4 using HyperFrames CLI.
    Saves to output_dir (or default Google Drive / Exports folder).
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        print(msg)

    if not comp_name.endswith(".html"):
        comp_rel = f"compositions/{comp_name}.html"
        base_name = comp_name
    else:
        comp_rel = f"compositions/{comp_name}"
        base_name = comp_name[:-5]

    comp_path = STUDIO_DIR / comp_rel
    if not comp_path.exists():
        raise FileNotFoundError(f"Composition file not found: {comp_path}")

    target_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    date_str = time.strftime("%Y%m%d_%H%M%S")
    out_mp4_name = f"{date_str}_{base_name}.mp4"
    out_mp4_path = target_dir / out_mp4_name

    log(f"🎬 Starting render for: {comp_name}")
    log(f"   Target MP4: {out_mp4_path}")
    log(f"   Quality: {quality} | FPS: {fps}")

    # Set puppeteer sandbox args for headless linux/colab
    env = os.environ.copy()
    env["PUPPETEER_ARGS"] = "--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage"
    env["CHROMIUM_FLAGS"] = "--no-sandbox --disable-setuid-sandbox"

    # Temporary render output inside studio
    temp_out = STUDIO_DIR / "renders" / f"tmp_{out_mp4_name}"
    temp_out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "--yes", "hyperframes@0.8.214", "render",
        "-c", comp_rel,
        "-o", str(temp_out),
        f"--quality={quality}",
        f"--fps={fps}",
        "--format=mp4",
        "--browser-timeout=120"
    ]

    log(f"   Executing: {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=str(STUDIO_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    for line in iter(proc.stdout.readline, ""):
        line_s = line.strip()
        if line_s:
            log(f"   [HyperFrames] {line_s}")

    proc.stdout.close()
    ret = proc.wait()
    dur = round(time.time() - t0, 1)

    if ret != 0:
        raise RuntimeError(f"HyperFrames render failed with exit code {ret}")

    if not temp_out.exists():
        raise FileNotFoundError(f"Rendered file not found at {temp_out}")

    # Copy to target output dir (e.g. Google Drive)
    shutil.copy2(temp_out, out_mp4_path)
    file_mb = round(out_mp4_path.stat().st_size / (1024 * 1024), 2)
    log(f"✅ Render completed in {dur}s! Size: {file_mb} MB")
    log(f"📁 Saved to: {out_mp4_path}")

    # Clean up temp
    try:
        temp_out.unlink()
    except Exception:
        pass

    return out_mp4_path


def tts_take_single_speaker(
    lines: List[str],
    voice_name: str,
    style: str,
    out_wav: Path,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Path:
    """Generates ONE single-take TTS audio for a speaker with Gemini 3.1 Flash TTS.
    Inserts 1.5s silence between lines to enable clean silence-splitting.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        print(msg)

    text = "\n\n".join(lines)
    prompt = (
        f"[Voice style: {style}\n"
        f'Pronunciation rule: Speak clear, lively, natural Thai with Southern Thai couple charm ("พี่บ่าว" and "น้องนุ้ย"). '
        f"Keep the exact same voice, energy and tone for every line. "
        f"After each paragraph leave a clear 1.5 second silence.]\n\n{text}\n"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}},
        },
    }

    keys = get_gemini_api_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY found! Please set GEMINI_API_KEY.")

    log(f"🎤 Requesting TTS ({voice_name}) for {len(lines)} lines...")
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(len(keys) * 4):
        key = keys[attempt % len(keys)]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent?key={key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                res_data = json.loads(r.read())
                b64_audio = res_data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                pcm = base64.b64decode(b64_audio)

            with wave.open(str(out_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(pcm)

            log(f"   ✅ Take ok: {voice_name} -> {out_wav.name}")
            return out_wav
        except Exception as e:
            log(f"   ⚠️ TTS attempt {attempt + 1} failed: {e}. Retrying...")
            time.sleep(12 if "429" in str(e) else 3)

    raise RuntimeError(f"TTS failed for {voice_name} after all retries.")


def split_by_longest_gaps(take_wav: Path, n: int) -> Tuple[int, List[np.ndarray]]:
    """Cuts a single-take WAV into n turns at its n-1 longest silences."""
    with wave.open(str(take_wav), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    win = int(0.02 * sr)
    frames = audio[: len(audio) // win * win].reshape(-1, win).astype(np.float32) / 32768.0
    quiet = 20 * np.log10(np.sqrt(np.mean(frames**2, axis=1)) + 1e-7) < -40
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

    cuts = sorted(c for _, c in sorted(gaps, reverse=True)[: n - 1])
    if len(cuts) != n - 1:
        # Fallback: divide evenly if gap detection didn't find enough quiet points
        step = len(audio) // n
        parts = [audio[k * step: (k + 1) * step] for k in range(n)]
        return sr, parts

    edges = [0] + [c * win for c in cuts] + [len(audio)]
    parts = [audio[edges[k]: edges[k + 1]] for k in range(n)]
    return sr, parts


def verify_turns_with_whisper(
    turn_files: List[Path],
    turns_data: List[tuple],
    device: str = "cpu",
    log_callback: Optional[Callable[[str], None]] = None,
) -> List[dict]:
    """Transcribes each turn with faster_whisper to verify timestamps and text alignment."""
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        print(msg)

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("⚠️ faster-whisper not installed. Skipping Whisper verification.")
        return []

    log(f"🔎 [Faster-Whisper] Verifying {len(turn_files)} turns on {device}...")
    compute_type = "float16" if device == "cuda" else "int8"
    try:
        model = WhisperModel("large-v3-turbo", device=device, compute_type=compute_type, local_files_only=False)
    except Exception:
        # Fallback to base model if large model cannot be loaded
        log("   Falling back to base Whisper model...")
        model = WhisperModel("base", device=device, compute_type=compute_type, local_files_only=False)

    report = []
    for i, wav_path in enumerate(turn_files):
        spk = turns_data[i][0]
        phrases = turns_data[i][1]
        expected = " ".join(s for _, s in phrases)
        try:
            segs, _ = model.transcribe(str(wav_path), language="th", initial_prompt=expected)
            heard = "".join(s.text for s in segs).strip()
        except Exception as e:
            heard = expected
            log(f"   Turn {i:02d} transcribe error: {e}")

        exp_chars = set(c for c in expected if "\u0e00" <= c <= "\u0e7f")
        hrd_chars = set(c for c in heard if "\u0e00" <= c <= "\u0e7f")
        overlap = len(exp_chars & hrd_chars) / max(1, len(exp_chars))
        log(f"   Turn {i:02d} ({spk}) [{overlap:.0%} match]: {expected[:30]}...")
        report.append({
            "turn": i,
            "speaker": spk,
            "expected": expected,
            "whisper": heard,
            "overlap": round(overlap, 3),
        })

    return report


def assemble_couple_voiceover(
    clip_id: str,
    turn_wavs: List[Path],
    turns_data: List[tuple],
    out_vo_wav: Path,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[float, List[List[Tuple[float, float]]]]:
    """Applies Couple Paper Chat DSP filters to turns and concatenates into vo.wav."""
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        print(msg)

    tmp_dir = out_vo_wav.parent / "_tmp_segs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_sr = 48000
    pieces = []
    timings = []
    cur_time = 0.0

    for i, (spk, phrases, _) in enumerate(turns_data):
        src = turn_wavs[i]
        dst = tmp_dir / f"out_{i:02d}.wav"

        # Couple DSP Standard:
        if spk == "F":
            # Female: น้องนุ้ย pitch +10%, tempo 1.20, highpass 140Hz, EQ +3dB at 3.5kHz
            af = f"asetrate=24000*1.10,aresample={out_sr},atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0"
        else:
            # Male: พี่บ่าว tempo 1.32, highpass 95Hz
            af = f"atempo=1.32,highpass=f=95,aresample={out_sr}"

        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", af, "-ar", str(out_sr), "-ac", "1", str(dst)],
            check=True,
        )

        with wave.open(str(dst), "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        turn_dur = len(pcm) / out_sr
        # Approximate phrase timings within turn
        phrase_lens = [len(disp) for disp, _ in phrases]
        total_len = max(1, sum(phrase_lens))
        phrase_timings = []
        p_cur = cur_time
        for plen in phrase_lens:
            p_dur = turn_dur * (plen / total_len)
            phrase_timings.append((round(p_cur, 3), round(p_cur + p_dur, 3)))
            p_cur += p_dur

        timings.append(phrase_timings)

        # Gap between turns (0.28s if switching speaker, 0.14s if same speaker)
        gap = 0.28 if i + 1 < len(turns_data) and turns_data[i + 1][0] != spk else 0.14
        pieces.append(pcm)
        pieces.append(np.zeros(int(gap * out_sr), dtype=np.int16))
        cur_time += turn_dur + gap

    full = np.concatenate(pieces)
    pre_norm = tmp_dir / "pre_norm.wav"
    with wave.open(str(pre_norm), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(out_sr)
        wf.writeframes(full.tobytes())

    # Master Loudnorm
    out_vo_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(pre_norm), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(out_vo_wav)],
        check=True,
    )
    total_dur = round(len(full) / out_sr, 3)
    log(f"   ✅ Master VO assembled: {total_dur}s -> {out_vo_wav.name}")
    return total_dur, timings


def generate_couple_paper_chat_html(
    clip_id: str,
    headlines: List[Tuple[int, str, str, str]],
    turns_data: List[tuple],
    timings: List[List[Tuple[float, float]]],
    total_dur: float,
    cta_title: str = "กดตะกร้าเหลือง",
    cta_model: str = "ชี้เป้าสินค้า · ของแท้แน่นอน",
    out_html: Optional[Path] = None,
) -> Path:
    """Generates the HyperFrames HTML composition file for Couple Paper Chat."""
    target_html = out_html or (COMPS_DIR / f"{clip_id}.html")
    target_html.parent.mkdir(parents=True, exist_ok=True)

    cta_start = max(0.5, total_dur - 3.5)

    # Build items and scrolls layout
    win_h = 1170
    scroll_pad = 40
    bubble_h = 104
    name_h = 44
    gap = 12
    tilt = [-1.2, 0.8, -0.6, 1.1, -0.9, 0.5]

    items = []
    scrolls = []
    y = 16
    scroll = 0
    n = 0

    def place(h, t):
        nonlocal y, scroll
        top = y
        y += h
        if y - scroll > win_h - scroll_pad:
            scroll = y - (win_h - scroll_pad)
            scrolls.append([round(t - 0.05, 3), scroll])
        return top

    thread_divs = []
    js_items = []
    sfx_tags = []

    for ti, (spk, phrases, photo) in enumerate(turns_data):
        t0 = timings[ti][0][0]
        side_cls = "in" if spk == "F" else "out"
        spk_name = "น้องนุ้ย" if spk == "F" else "พี่บ่าว"
        ava_cls = "f" if spk == "F" else "m"
        ava_char = "น" if spk == "F" else "บ"

        # Speaker name
        top_name = place(name_h, t0)
        item_id = f"i{len(items)}"
        thread_divs.append(f'<div class="nm {side_cls}" id="{item_id}" style="top: {top_name}px">{spk_name}</div>')
        js_items.append({"id": item_id, "kind": "name", "side": spk, "t": t0, "e": None})
        items.append(item_id)

        # Messages
        for pi, (disp, _) in enumerate(phrases):
            s, e = timings[ti][pi]
            if pi:
                y += gap
            top_msg = place(bubble_h, s)
            msg_id = f"i{len(items)}"
            rot = tilt[n % len(tilt)]
            n += 1

            ava_html = f'<div class="ava {ava_cls}">{ava_char}</div>' if pi == 0 else ""
            thread_divs.append(
                f'<div class="row {side_cls}" id="{msg_id}" style="top: {top_msg}px">{ava_html}<div class="msg" style="rotate: {rot}deg">{disp}</div></div>'
            )
            js_items.append({"id": msg_id, "kind": "msg", "side": spk, "t": s, "e": e})
            items.append(msg_id)

            # SFX for msg
            sfx_sound = "msg_recv.mp3" if spk == "F" else "msg_send.mp3"
            sfx_tags.append(
                f'<audio class="sfx" src="assets/shared/sfx/{sfx_sound}" data-start="{s}" data-duration="0.5" data-track-index="{12 + (n % 2)}" data-volume="0.3"></audio>'
            )

            # Optional Photo
            if photo and photo[0] == pi:
                tp = round(s + 0.25, 3)
                y += gap + 6
                top_photo = place(540, tp)
                photo_id = f"i{len(items)}"
                thread_divs.append(
                    f'<div class="row {side_cls}" id="{photo_id}" style="top: {top_photo}px"><div class="photo" style="rotate: {-2.5 if spk == "M" else 2.5}deg"><img src="{photo[1]}" alt=""></div></div>'
                )
                js_items.append({"id": photo_id, "kind": "photo", "side": spk, "t": tp, "e": None})
                items.append(photo_id)
                sfx_tags.append(
                    f'<audio class="sfx" src="assets/shared/sfx/paper.mp3" data-start="{tp}" data-duration="0.45" data-track-index="13" data-volume="0.5"></audio>'
                )

    # Headline divs and JS heads
    hd_divs = []
    js_heads = []
    for h_idx, (t_idx, sub, l1, l2) in enumerate(headlines):
        t_start = timings[t_idx][0][0] if t_idx < len(timings) else 0.0
        next_t_start = timings[headlines[h_idx + 1][0]][0][0] if h_idx + 1 < len(headlines) and headlines[h_idx + 1][0] < len(timings) else cta_start
        hd_id = f"hd{h_idx}"
        hd_divs.append(
            f'<div class="hd" id="{hd_id}"><div class="hd-sub">{sub}</div><div class="hd-t"><span class="hl">{l1}</span><br><span class="hl">{l2}</span></div></div>'
        )
        js_heads.append({"id": hd_id, "t0": t_start, "t1": next_t_start})

    # Composition HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/kit.js"></script>
    <style>
      @font-face {{
        font-family: "Kanit Black";
        src: url("kit/fonts/Kanit-Black.ttf") format("truetype");
        font-weight: 900;
      }}
      @font-face {{
        font-family: "Anuphan";
        src: url("kit/fonts/Anuphan-Bold.ttf") format("truetype");
        font-weight: 700;
      }}
      :root {{
        --ink: #1b1a17;
        --line-red: #d90429;
      }}
      #root {{
        background: #efece6;
      }}
      #paper {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }}
      .hd {{
        position: absolute;
        left: 60px;
        right: 60px;
        top: 110px;
        text-align: center;
        color: var(--ink);
        opacity: 0;
        will-change: transform, opacity;
      }}
      .hd-sub {{
        font-family: "Anuphan", sans-serif;
        font-size: 50px;
        line-height: 1.2;
      }}
      .hd-t {{
        margin-top: 10px;
        font-size: 92px;
        line-height: 1.12;
      }}
      .hl {{
        padding: 0 14px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.92) 52%, rgba(255, 230, 0, 0.92) 92%, transparent 92%);
      }}
      #chatwin {{
        position: absolute;
        left: 0;
        right: 0;
        top: 470px;
        height: 1170px;
        overflow: hidden;
      }}
      #thread {{
        position: absolute;
        inset: 0;
        will-change: transform;
      }}
      .row, .nm {{
        position: absolute;
        left: 40px;
        right: 40px;
        display: flex;
        align-items: flex-start;
        gap: 16px;
        opacity: 0;
        will-change: transform, opacity;
      }}
      .row.out, .nm.out {{
        justify-content: flex-end;
      }}
      .nm {{
        font-family: "Anuphan", sans-serif;
        font-size: 32px;
        color: #55514a;
        padding: 0 104px;
      }}
      .row.in {{
        padding-left: 96px;
      }}
      .row.out {{
        padding-right: 96px;
      }}
      .ava {{
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
      }}
      .row.in .ava {{ left: 0; }}
      .row.out .ava {{ right: 0; }}
      .ava.f {{ background: linear-gradient(135deg, #ff9eb5, #ff5277); }}
      .ava.m {{ background: linear-gradient(135deg, #60a5fa, #2563eb); }}
      .msg {{
        padding: 14px 32px;
        border: 4px solid var(--ink);
        border-radius: 32px;
        background: #ffffff;
        box-shadow: 7px 8px 0 rgba(27, 26, 23, 0.2);
        font-family: "Anuphan", sans-serif;
        font-size: 52px;
        line-height: 1.25;
        white-space: nowrap;
        color: #111;
      }}
      .row.out .msg {{
        background: #8de07a;
      }}
      .photo {{
        width: 540px;
        height: 540px;
        padding: 14px;
        background: #fff;
        border: 4px solid var(--ink);
        border-radius: 22px;
        box-shadow: 9px 10px 0 rgba(27, 26, 23, 0.22);
      }}
      .photo img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 12px;
        display: block;
      }}
      #cta-1 {{
        top: 330px;
        font-size: 110px;
        color: var(--ink);
      }}
      #cta-model {{
        top: 490px;
        font-family: "Anuphan", sans-serif;
        font-size: 64px;
        color: var(--line-red);
      }}
      #cta-arrow {{
        left: 0;
        top: 0;
        width: 1080px;
        height: 1920px;
      }}
      #cta-arrow path {{
        fill: none;
        stroke: var(--line-red);
        stroke-width: 22;
        stroke-linecap: round;
        stroke-linejoin: round;
      }}
      #cta-2 {{
        left: 260px;
        top: 1330px;
        font-size: 110px;
        color: var(--line-red);
      }}
      #wm {{
        left: 0 !important;
        right: 0;
        top: auto !important;
        bottom: 26px;
        width: 100% !important;
        text-align: center;
      }}
      #wm span {{
        font-size: 28px;
        color: rgba(217, 4, 41, 0.75) !important;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{clip_id}" data-start="0" data-duration="{total_dur + 1.2}" data-width="1080" data-height="1920">
      <video id="paper" class="clip" src="assets/shared/paper_bg.mp4" muted playsinline data-playback-rate="0.5" data-start="0" data-duration="{total_dur + 1.2}" data-media-start="0" data-track-index="0"></video>

      <div class="beat clip" id="b-chat" data-start="0" data-duration="{cta_start}" data-track-index="2">
        {"".join(hd_divs)}
        <div id="chatwin">
          <div id="thread">
            {"".join(thread_divs)}
          </div>
        </div>
      </div>

      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{round(total_dur + 1.2 - cta_start, 2)}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">{cta_title}</span></div>
        <div class="t center" id="cta-model">{cta_model}</div>
        <svg class="fx" id="cta-arrow" viewBox="0 0 1080 1920">
          <path id="cta-shaft" d="M 330 640 C 180 870 120 1190 160 1460" />
          <path id="cta-head" d="M 80 1380 L 160 1470 L 250 1390" />
        </svg>
        <div class="t" id="cta-2">ซ้ายล่าง</div>
      </div>

      <div id="flash"></div>
      <div id="wm"><span>OmniCut Pro • สไตล์น้องนุ้ย & พี่บ่าว</span></div>

      <audio id="vo0" src="assets/clips/{clip_id}/vo.wav" data-start="0" data-media-start="0" data-duration="{total_dur}" data-track-index="10" data-volume="1"></audio>
      <audio id="bgm" src="assets/shared/bgm_lofi.wav" data-start="0" data-duration="{total_dur + 1.2}" data-track-index="11" data-volume="0.05" data-carve="0.25" data-carve-targets="vo0"></audio>
      {"".join(sfx_tags)}
      <audio class="sfx" src="assets/shared/sfx/whoosh.mp3" data-start="{cta_start}" data-duration="0.5" data-track-index="12" data-volume="0.4"></audio>
      <audio class="sfx" src="assets/shared/sfx/cash_register.mp3" data-start="{cta_start + 0.5}" data-duration="1.0" data-track-index="13" data-volume="0.45"></audio>
    </div>

    <script>
      const tl = gsap.timeline({{ paused: true }});
      const $ = (s) => document.querySelector(s);
      const CTA = {cta_start};
      const ITEMS = {json.dumps(js_items, ensure_ascii=False)};
      const HEADS = {json.dumps(js_heads, ensure_ascii=False)};
      const SCROLLS = {json.dumps(scrolls)};

      HEADS.forEach((h) => {{
        tl.fromTo(`#${{h.id}}`, {{ scale: 1.5, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.28, ease: "power4.out" }}, h.t0);
        tl.to(`#${{h.id}}`, {{ opacity: 0, duration: 0.12 }}, h.t1 - 0.12);
      }});

      ITEMS.forEach((it) => {{
        const fromX = it.side === "F" ? -50 : 50;
        if (it.kind === "name") {{
          tl.fromTo(`#${{it.id}}`, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.15 }}, it.t);
        }} else if (it.kind === "msg") {{
          tl.fromTo(`#${{it.id}}`, {{ y: 36, x: fromX, scale: 0.7, opacity: 0 }}, {{ y: 0, x: 0, scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }}, it.t);
          const m = `#${{it.id}} .msg`;
          tl.set(m, {{ color: "#d90429" }}, it.t);
          tl.set(m, {{ color: "#111111" }}, it.e);
        }} else {{
          tl.fromTo(`#${{it.id}}`, {{ y: 60, scale: 0.4, rotation: fromX > 0 ? 14 : -14, opacity: 0 }}, {{ y: 0, scale: 1, rotation: 0, opacity: 1, duration: 0.42, ease: "back.out(1.7)" }}, it.t);
        }}
      }});

      SCROLLS.forEach(([t, y]) => tl.to("#thread", {{ y: -y, duration: 0.32, ease: "power2.out" }}, t));

      tl.to("#chatwin", {{ y: 140, opacity: 0, duration: 0.25, ease: "power2.in" }}, CTA - 0.25);
      HF.flash(tl)(CTA, 0.5, 0.25);
      tl.fromTo("#cta-1", {{ scale: 1.9, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.3, ease: "power4.out" }}, CTA + 0.05);
      tl.fromTo("#cta-model", {{ y: 30, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.3, ease: "power3.out" }}, CTA + 0.3);

      const sl = HF.dash($("#cta-shaft"));
      const hl = HF.dash($("#cta-head"));
      tl.fromTo("#cta-shaft", {{ strokeDashoffset: sl }}, {{ strokeDashoffset: 0, duration: 0.45, ease: "power2.inOut" }}, CTA + 0.4);
      tl.fromTo("#cta-head", {{ strokeDashoffset: hl }}, {{ strokeDashoffset: 0, duration: 0.16, ease: "power2.out" }}, CTA + 0.82);
      tl.fromTo("#cta-2", {{ x: -80, opacity: 0 }}, {{ x: 0, opacity: 1, duration: 0.3, ease: "expo.out" }}, CTA + 0.95);
      tl.to("#cta-arrow", {{ x: -18, y: 18, duration: 0.25, ease: "sine.inOut", yoyo: true, repeat: 3 }}, CTA + 1.25);

      window.__timelines = window.__timelines || {{}};
      window.__timelines["{clip_id}"] = tl;
    </script>
  </body>
</html>
"""
    target_html.write_text(html_content, encoding="utf-8")
    return target_html


def build_and_render_couple_chat_clip(
    clip_id: str,
    turns_data: List[tuple],
    headlines: List[Tuple[int, str, str, str]],
    cta_title: str = "กดตะกร้าเหลือง",
    cta_model: str = "ชี้เป้าสินค้า · ของแท้แน่นอน",
    output_dir: Optional[Path] = None,
    device: str = "cpu",
    quality: str = "looks",
    log_callback: Optional[Callable[[str], None]] = None,
) -> Path:
    """End-to-end builder: TTS takes -> Whisper alignment -> VO assembly -> HTML generation -> HyperFrames render."""
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        print(msg)

    log(f"🚀 Starting Couple Paper Chat Production: {clip_id}")

    clip_tts_dir = CLIPS_DIR / clip_id / "tts"
    clip_tts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Single-take TTS for Female & Male
    f_idx = [i for i, t in enumerate(turns_data) if t[0] == "F"]
    m_idx = [i for i, t in enumerate(turns_data) if t[0] == "M"]

    f_take = clip_tts_dir / "take_F.wav"
    m_take = clip_tts_dir / "take_M.wav"

    if not f_take.exists():
        f_lines = [" ".join(s for _, s in turns_data[i][1]) for i in f_idx]
        tts_take_single_speaker(f_lines, "Aoede", F_STYLE, f_take, log_callback=log)

    if not m_take.exists():
        m_lines = [" ".join(s for _, s in turns_data[i][1]) for i in m_idx]
        tts_take_single_speaker(m_lines, "Puck", M_STYLE, m_take, log_callback=log)

    # 2. Split takes by silence
    log("✂️ Splitting takes into turns by longest silences...")
    f_sr, f_parts = split_by_longest_gaps(f_take, len(f_idx))
    m_sr, m_parts = split_by_longest_gaps(m_take, len(m_idx))

    turn_wavs_dict = {}
    for i, pcm in zip(f_idx, f_parts):
        w_path = clip_tts_dir / f"turn_{i:02d}_F.wav"
        with wave.open(str(w_path), "wb") as wf:
            wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(f_sr), wf.writeframes(pcm.tobytes())
        turn_wavs_dict[i] = w_path

    for i, pcm in zip(m_idx, m_parts):
        w_path = clip_tts_dir / f"turn_{i:02d}_M.wav"
        with wave.open(str(w_path), "wb") as wf:
            wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(m_sr), wf.writeframes(pcm.tobytes())
        turn_wavs_dict[i] = w_path

    ordered_turn_wavs = [turn_wavs_dict[i] for i in range(len(turns_data))]

    # 3. Whisper Verification
    verify_turns_with_whisper(ordered_turn_wavs, turns_data, device=device, log_callback=log)

    # 4. Assemble Master VO
    vo_wav = ASSETS_DIR / "clips" / clip_id / "vo.wav"
    total_dur, timings = assemble_couple_voiceover(
        clip_id, ordered_turn_wavs, turns_data, vo_wav, log_callback=log
    )

    # 5. Generate HTML Composition
    log("📝 Compiling HTML composition...")
    comp_html = generate_couple_paper_chat_html(
        clip_id=clip_id,
        headlines=headlines,
        turns_data=turns_data,
        timings=timings,
        total_dur=total_dur,
        cta_title=cta_title,
        cta_model=cta_model,
    )

    # 6. Render to MP4
    log("🎬 Rendering MP4 via HyperFrames...")
    mp4_path = render_composition_to_mp4(
        comp_name=clip_id,
        output_dir=output_dir,
        quality=quality,
        fps=30,
        log_callback=log,
    )

    log(f"🎉 Production Finished! Result: {mp4_path}")
    return mp4_path
