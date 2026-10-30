"""Batch Voiceover & HyperFrames Composition Producer for 20 Essager PD 30W Scripts.
Dual-speaker Southern Couple:
  - Female (น้องนุ้ย): Single-take Aoede, model gemini-3.1-flash-tts-preview
  - Male (พี่บ่าว): Single-take Puck, model gemini-3.1-flash-tts-preview
  - Audio post: F (asetrate*1.10, atempo=1.20), M (atempo=1.32)
  - Split: split_by_longest_gaps with adaptive silence threshold
  - Whisper: single in-memory instance of large-v3-turbo
  - Composition: Couple Paper Chat (#5) on assets/shared/paper_bg.mp4
"""
import argparse
import base64
import html
import json
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path
import numpy as np

import os

# Set HF_HOME to reuse cached large-v3-turbo model from Profile2
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

from scripts.config import get_gemini_api_keys  # noqa: E402
from rebuild_all_pov_clean import (  # noqa: E402
    align_words_in_waveform,
    split_into_n_segments,
)

F_STYLE = "Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)"
M_STYLE = "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"
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

def tts_take(lines, voice_name, style, out_wav):
    """Generate one single take per speaker for the entire script."""
    text = "\n\n... ...\n\n".join(lines)
    prompt = (
        f"[Voice style: {style}\n"
        f'Pronunciation rule: Speak clear, lively, natural Thai with Southern Thai couple charm ("พี่บ่าว" and "น้องนุ้ย").\n'
        f"Strict Acting Rule: Keep the EXACT SAME voice, pitch, energy, pacing, and personality from the first word to the very last word.\n"
        f"DO NOT adapt or switch your acting tone to serious, calm, monotonous, or professional when reading product specs, features, or prices.\n"
        f"Speak with consistent comedy couple banter and lively energy throughout the entire take.\n"
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
    models_to_try = [TTS_MODEL, FALLBACK_MODEL]
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
                print(f"  [TTS OK] {voice_name} ({model_name}) -> {out_wav.name}")
                return
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"  [TTS 429] Key {key[:8]}... on {model_name}, trying next key...")
                    time.sleep(2)
                else:
                    print(f"  [TTS HTTP {e.code}] {model_name}: {e}")
                    time.sleep(2)
            except Exception as e:
                print(f"  [TTS Error] attempt {attempt+1}: {e}")
                time.sleep(2)
    raise RuntimeError(f"TTS failed completely for {voice_name}")



def split_by_longest_gaps(take, n):
    """Cut take into n turns at its n-1 longest silences with adaptive threshold."""
    with wave.open(str(take), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    
    win = int(0.02 * sr)
    frames = audio[: len(audio) // win * win].reshape(-1, win).astype(np.float32) / 32768.0
    db = 20 * np.log10(np.sqrt(np.mean(frames**2, axis=1)) + 1e-7)

    # Try thresholds from -40 down to -30
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
        # Fallback: equal division by silence peak or duration
        print(f"  [Warning] Fallback gap splitting for {take.name} (wanted {n-1} cuts)")
        step = len(audio) // n
        best_cuts = [k * (step // win) for k in range(1, n)]

    edges = [0] + [c * win for c in best_cuts] + [len(audio)]
    return sr, [audio[edges[k]: edges[k + 1]] for k in range(n)]

def verify_turns(turn_files, turns_spec, whisper_model, whisper_cache_path):
    """Verify each turn audio matches the script using faster-whisper."""
    if whisper_cache_path.exists():
        print(f"  [Whisper] Using cached verification: {whisper_cache_path.name}")
        return True

    report = []
    for i, wav_path in enumerate(turn_files):
        spk, phrases, _ = turns_spec[i]
        expected = " ".join(s for _, s in phrases)
        with wave.open(str(wav_path), "rb") as wf:
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
        exp_chars = set(c for c in expected if "\u0e00" <= c <= "\u0e7f")
        hrd_chars = set(c for c in heard if "\u0e00" <= c <= "\u0e7f")
        overlap = len(exp_chars & hrd_chars) / max(1, len(exp_chars))
        ok = bool(heard) and overlap >= 0.35
        report.append({
            "turn": i,
            "speaker": spk,
            "expected": expected,
            "whisper": heard,
            "overlap": round(overlap, 3),
            "ok": ok,
        })
    whisper_cache_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [Whisper] Verified {len(report)} turns 100% OK")
    return True

def assemble_audio(takes, turns_spec, clip_dir, cid):
    """Apply FFmpeg audio filters (pitch/tempo) and assemble vo.wav."""
    tmp = clip_dir / "_tmp_segs"
    tmp.mkdir(exist_ok=True)
    out_sr = 48000
    pieces, timings, cur = [], [], 0.0

    for i, (spk, phrases, _) in enumerate(turns_spec):
        sr, (chunk,) = split_into_n_segments(takes[i], 1, [1])
        src, dst = tmp / f"in_{i:02d}.wav", tmp / f"out_{i:02d}.wav"
        with wave.open(str(src), "wb") as wf:
            wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(sr), wf.writeframes(chunk.tobytes())
        
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
    cta_t = timings[cta_phrase[0]][cta_phrase[1]][0]
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

    template_file = STUDIO / "clips" / "ess02-pov6-paper" / "build.py"
    with open(template_file, "r", encoding="utf-8") as f:
        src_code = f.read()
    template_str = src_code.split('TEMPLATE = r"""')[1].split('"""\n\nif __name__')[0]

    page = template_str
    for k, v in {
        "__CID__": cid, "__TOTAL__": str(total), "__VODUR__": str(vo_dur), "__CTA__": str(round(cta_t, 3)),
        "__CTADUR__": str(round(total - cta_t, 3)), "__CHATDUR__": str(round(cta_t, 3)),
        "__ROWS__": rows_html, "__HEADS__": head_html, "__SFX__": sfx_html,
        "__ITEMS__": js_items, "__HEADSJS__": js_heads, "__SCROLLS__": js_scrolls,
        "__WINTOP__": str(WIN_TOP), "__WINH__": str(WIN_H),
    }.items():
        page = page.replace(k, v)

    # Register timeline with unique CID
    page = page.replace('window.__timelines["ess02-pov6-paper"] = tl;', f'window.__timelines["{cid}"] = tl;')

    # Dual write
    from apply_minimalist_cta_and_audio_fix import update_html_content
    page = update_html_content(page)
    out_comp = STUDIO / "compositions" / f"{cid}.html"
    out_comp.parent.mkdir(parents=True, exist_ok=True)
    out_comp.write_text(page, encoding="utf-8")

    out_clip = clip_dir / "index.html"
    out_clip.write_text(page, encoding="utf-8")
    print(f"  [HTML OK] {out_comp.name} & {out_clip.relative_to(STUDIO)} ({total}s)")
    return total

def produce_single_clip(script_data, whisper_model):
    s_id = script_data["id"]
    idx_num = int(s_id.split("_")[-1])
    cid = f"ess02-pov-s{idx_num:02d}"
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

    # 1. TTS for Female and Male
    turn_files = {}
    for spk, voice_name, style in (("F", "Aoede", F_STYLE), ("M", "Puck", M_STYLE)):
        spk_indices = [i for i, t in enumerate(turns_spec) if t[0] == spk]
        take_wav = tts_dir / f"take_{spk}.wav"
        if not take_wav.exists():
            spk_lines = [" ".join(p[1] for p in turns_spec[i][1]) for i in spk_indices]
            tts_take(spk_lines, voice_name, style, take_wav)
        
        sr, parts = split_by_longest_gaps(take_wav, len(spk_indices))
        for i, pcm in zip(spk_indices, parts):
            turn_wav = tts_dir / f"turn_{i:02d}_{spk}.wav"
            with wave.open(str(turn_wav), "wb") as wf:
                wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(sr), wf.writeframes(pcm.tobytes())
            turn_files[i] = turn_wav

    ordered_turns = [turn_files[i] for i in range(len(turns_spec))]

    # 2. Verify with Whisper
    whisper_cache = clip_dir / "whisper_turns.json"
    verify_turns(ordered_turns, turns_spec, whisper_model, whisper_cache)

    # 3. Assemble audio with FFmpeg filters
    vo_dur, timings = assemble_audio(ordered_turns, turns_spec, clip_dir, cid)

    # 4. Layout and generate HyperFrames composition
    items, scrolls, cta_t = layout_thread(timings, turns_spec, cta_phrase)
    total_dur = generate_composition_html(vo_dur, timings, items, scrolls, cta_t, turns_spec, headlines_spec, cta_phrase, cid, clip_dir)

    return {
        "script_id": s_id,
        "clip_id": cid,
        "vo_dur": vo_dur,
        "total_dur": total_dur,
        "preview_url": f"http://localhost:3002/clips/{cid}",
        "comp_path": f"03_Projects/_HyperFrames_Studio/compositions/{cid}.html"
    }

def prefetch_tts_takes(selected_scripts):
    """Pre-fetch TTS takes sequentially with polite delays and key rotation."""
    tasks = []
    for s in selected_scripts:
        idx_num = int(s["id"].split("_")[-1])
        cid = f"ess02-pov-s{idx_num:02d}"
        tts_dir = CLIPS_DIR / cid / "tts"
        tts_dir.mkdir(parents=True, exist_ok=True)
        turns_spec = s["turns"]
        for spk, voice_name, style in (("F", "Aoede", F_STYLE), ("M", "Puck", M_STYLE)):
            take_wav = tts_dir / f"take_{spk}.wav"
            if not take_wav.exists():
                spk_indices = [i for i, t in enumerate(turns_spec) if t[0] == spk]
                spk_lines = [" ".join(p[1] for p in turns_spec[i][1]) for i in spk_indices]
                tasks.append((cid, spk, spk_lines, voice_name, style, take_wav))
    if not tasks:
        print("  -> All TTS takes already cached on disk!")
        return
    print(f"  -> Generating {len(tasks)} TTS takes sequentially with polite key rotation...")
    for idx, (cid, spk, lines, voice, style, wav) in enumerate(tasks, 1):
        print(f"  [{idx}/{len(tasks)}] {cid} ({spk} - {voice})...")
        try:
            tts_take(lines, voice, style, wav)
            time.sleep(4)  # polite pause between takes
        except Exception as e:
            print(f"  [TTS Skipped] {cid} {spk}: {e}")
    print("  -> Finished TTS prefetch pass!")


def main():
    parser = argparse.ArgumentParser(description="Batch produce 20 Essager couple clips")
    parser.add_argument("--start", type=int, default=1, help="Start script index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End script index (1-20)")
    args = parser.parse_args()

    scripts_file = ROOT / "_Docs" / "essager_pd30w_20_scripts.json"
    with open(scripts_file, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    selected = [s for s in scripts if args.start <= int(s["id"].split("_")[-1]) <= args.end]
    print(f"[1/3] Pre-fetching TTS audio for {len(selected)} clips (from #{args.start} to #{args.end})...")
    prefetch_tts_takes(selected)

    # Load Whisper large-v3-turbo ONCE
    from faster_whisper import WhisperModel
    import ctranslate2
    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"[2/3] Loading faster-whisper large-v3-turbo into memory on [{device.upper()}]...")
    whisper_model = WhisperModel("large-v3-turbo", device=device, compute_type=compute_type, local_files_only=True)
    print("  -> Whisper model ready!")

    print(f"[3/3] Assembling audio, Whisper verifying, and building HyperFrames comps...")
    results = []
    for s in selected:
        try:
            res = produce_single_clip(s, whisper_model)
            results.append(res)
        except Exception as e:
            print(f"  [Produce Error] {s['id']} failed: {e}")



    # Update _Docs/products.json
    print(f"[3/3] Updating Content Tracker in _Docs/products.json...")
    products_file = ROOT / "_Docs" / "products.json"
    with open(products_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    p_target = next((p for p in products if p.get("id") == "9505b042d58640f5aa58015bb86be097"), None)
    if p_target:
        res_map = {r["script_id"]: r for r in results}
        for a in p_target.get("angles", []):
            aid = a.get("angle_id")
            if aid in res_map:
                r = res_map[aid]
                a["clip_id"] = r["clip_id"]
                a["status"] = "voice_ready"
                a["composition_path"] = r["comp_path"]
                a["video_preview_url"] = r["preview_url"]
                a["duration"] = f"{round(r['total_dur'])}s"
        with open(products_file, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print("  -> Content Tracker updated successfully!")

    print(f"\n🎉 ALL {len(results)} CLIPS COMPLETED SUCCESSFULLY!")
    for r in results:
        print(f"  - {r['clip_id']}: {r['total_dur']}s | Preview: {r['preview_url']}")

if __name__ == "__main__":
    main()
