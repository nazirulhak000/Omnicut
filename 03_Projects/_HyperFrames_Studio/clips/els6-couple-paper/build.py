"""els6-couple-paper — Orsen by Eloop S6 (240W C-to-C) as a "พี่บ่าว & น้องนุ้ย" voiced chat story
on a stop-motion crumpled-paper backdrop. Structure: chat → photo → chat (official listing photos
are sent in the thread; this product has no footage). No prices anywhere (TikTok rule).

Run: python clips/els6-couple-paper/build.py   (one TTS take per speaker, cached as tts/take_F.wav /
take_M.wav; delete one to re-voice that speaker). Writes assets/clips/<id>/vo.wav and compositions/<id>.html.
Voices follow .agents/rules/pov_couple_line_chat_standard.md (single-speaker Aoede / Puck).
"""
import html
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
from rebuild_all_pov_clean import (  # noqa: E402  (shared couple-voice helpers)
    align_words_in_waveform,
    split_into_n_segments,
)

CID = HERE.name
IMG = "assets/els6/img"

# (speaker, [(display, spoken), ...], photo_after_phrase_or_None)
# photo = (phrase_index, src, kind) — shown right under that phrase, 0.25s after it starts.
TURNS = [
    ("F", [("พี่บ่าว!", "พี่บ่าว!"), ("โน้ตบุ๊กแบตเหลือ 3%!", "โน้ตบุ๊กน้องแบตเหลือสามเปอร์เซ็นต์!")], None),
    ("F", [("ลืมสายชาร์จไว้บ้าน", "ลืมสายชาร์จไว้บ้าน"), ("อีก 10 นาทีต้องพรีเซนต์!", "อีกสิบนาทีต้องพรีเซนต์แล้ว!")], None),
    ("M", [("ใจเย็นน้องนุ้ย", "ใจเย็นครับน้องนุ้ย"), ("เอาสายมือถือเสียบก่อน", "เอาสายมือถือเสียบไปก่อน")], None),
    ("F", [("เสียบแล้ว แทบไม่ขึ้นเลย!", "เสียบแล้ว แทบไม่ขึ้นเลย!"), ("ช่วยคิดไหรสักอย่างติ!", "พี่บ่าวช่วยคิดไหรสักอย่างติ!")], None),
    ("M", [("สายมือถือรับไฟไม่พอ", "สายมือถือรับไฟไม่พอครับ"), ("ใช้เส้นนี้เลย", "ใช้เส้นนี้เลย")], (1, f"{IMG}/src/coil_240w.jpg", "photo")),
    ("M", [("Orsen S6 รองรับ 240W", "ออร์เซ่น เอสหก รองรับสองร้อยสี่สิบวัตต์"), ("ชาร์จโน้ตบุ๊กได้สบาย", "ชาร์จโน้ตบุ๊กได้สบาย")], None),
    ("F", [("จริงดิ สายเส้นเดียวเนี่ยนะ?", "จริงดิ สายเส้นเดียวเนี่ยนะ?")], None),
    ("M", [("ข้างในมีชิป E-MARK", "ข้างในมีชิปอีมาร์ค"), ("ชาร์จเร็ว เสถียร", "ชาร์จเร็ว แล้วก็เสถียร")], (0, f"{IMG}/src/emark_chip.jpg", "photo")),
    ("M", [("สายถัก 48 เส้น", "สายถักสี่สิบแปดเส้น"), ("ทนทาน ไม่ขาดง่าย", "ทนทาน ไม่ขาดง่าย")], (0, f"{IMG}/src/braided_vs_broken.jpg", "photo")),
    ("F", [("ขึ้นแล้ว ทันพรีเซนต์พอดี!", "ขึ้นแล้ว ทันพรีเซนต์พอดี!"), ("ใช้กับมือถือ iPad ได้ไหม?", "แล้วใช้กับมือถือ ไอแพดได้ด้วยไหม?")], None),
    ("M", [("ได้หมด เส้นเดียวจบ", "ได้หมดครับ เส้นเดียวจบ")], (0, f"{IMG}/src/compat_devices.jpg", "photo")),
    ("F", [("งั้นสั่งให้น้องด้วย", "งั้นสั่งให้น้องด้วย"), ("เอาสีชมพูนะ!", "เอาสีชมพูนะ!")], (1, f"{IMG}/src/pink_heads.jpg", "photo")),
    ("M", [("จัดให้ครับ", "จัดให้ครับ"), ("กดตะกร้าเหลือง", "ใครอยากได้ กดตะกร้าเหลือง"), ("ซ้ายล่างเลย", "ซ้ายล่างเลยครับ")], None),
]
CTA_PHRASE = (12, 1)  # turn, phrase where the chat gives way to the CTA

# headline per scene: starts at turn index
HEADLINES = [
    (0, "POV: แฟนโน้ตบุ๊กแบต 3%", "อีก 10 นาที", "ต้องพรีเซนต์!"),
    (4, "ตัวช่วยฉุกเฉินของพี่บ่าว", "Orsen S6", "240W"),
    (7, "ทำไมชาร์จโน้ตบุ๊กได้?", "ชิป E-MARK", "+ สายถัก 48 เส้น"),
    (9, "ผลลัพธ์", "ทันพรีเซนต์", "เส้นเดียวจบ!"),
]

# chat layout (px, inside the chat window)
WIN_TOP, WIN_H = 470, 1170
NAME_H, BUBBLE_H, GAP, TURN_GAP = 44, 104, 12, 30
PHOTO_H, STICKER_H = 540, 460
SCROLL_PAD = 40


F_STYLE = "Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)"
M_STYLE = "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"


TTS_MODEL = "gemini-3.1-flash-tts-preview"  # pinned: a fallback model has a different timbre


def tts_take(lines, voice_name, style, out_wav):
    """ONE take per speaker (whole clip) so the tone never drifts between turns.
    Model is pinned and never falls back; 429s wait and rotate keys."""
    import base64
    import time
    import urllib.request
    from scripts.config import get_gemini_api_keys

    text = "\n\n".join(lines)
    prompt = (f"[Voice style: {style}\n"
              f'Pronunciation rule: Speak clear, lively, natural Thai with Southern Thai couple charm ("พี่บ่าว" and "น้องนุ้ย"). '
              f"Keep the exact same voice, energy and tone for every line. "
              f"After each paragraph leave a clear 1.5 second silence.]\n\n{text}\n")
    payload = {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"responseModalities": ["AUDIO"],
                                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}}}}
    keys = get_gemini_api_keys()
    for attempt in range(len(keys) * 4):
        key = keys[attempt % len(keys)]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent?key={key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                pcm = base64.b64decode(json.loads(r.read())["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            with wave.open(str(out_wav), "wb") as wf:
                wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(24000), wf.writeframes(pcm)
            print(f"  take ok: {voice_name} -> {out_wav.name}")
            return
        except Exception as e:  # noqa: BLE001
            print(f"  retry {voice_name} key#{attempt % len(keys) + 1}: {e}")
            time.sleep(15 if "429" in str(e) else 3)
    raise RuntimeError(f"TTS failed for {voice_name}")


def split_by_longest_gaps(take, n):
    """Cut a take into n turns at its n-1 longest silences (turn pauses are the long ones)."""
    with wave.open(str(take), "rb") as wf:
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
            if i > 0 and j < len(quiet):  # interior silences only
                gaps.append((j - i, (i + j) // 2))
            i = j
        else:
            i += 1
    cuts = sorted(c for _, c in sorted(gaps, reverse=True)[: n - 1])
    if len(cuts) != n - 1:
        raise RuntimeError(f"{take.name}: found {len(cuts) + 1} turns, expected {n}")
    edges = [0] + [c * win for c in cuts] + [len(audio)]
    return sr, [audio[edges[k]: edges[k + 1]] for k in range(n)]


def voice():
    """Per speaker: one take (cached in tts/take_<F|M>.wav), split into per-turn wavs."""
    out = HERE / "tts"
    out.mkdir(exist_ok=True)
    files = {}
    for spk, voice_name, style in (("F", "Aoede", F_STYLE), ("M", "Puck", M_STYLE)):
        idx = [i for i, t in enumerate(TURNS) if t[0] == spk]
        take = out / f"take_{spk}.wav"
        if not take.exists():
            tts_take([" ".join(s for _, s in TURNS[i][1]) for i in idx], voice_name, style, take)
        sr, parts = split_by_longest_gaps(take, len(idx))
        for i, pcm in zip(idx, parts):
            wav = out / f"turn_{i:02d}_{spk}.wav"
            with wave.open(str(wav), "wb") as wf:
                wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(sr), wf.writeframes(pcm.tobytes())
            files[i] = wav
    return [files[i] for i in range(len(TURNS))]


def assemble(takes):
    """Trim each turn's take, pitch/tempo it per the couple standard and lay the turns end to end."""
    tmp = HERE / "_tmp_segs"
    tmp.mkdir(exist_ok=True)
    out_sr = 48000
    pieces, timings, cur = [], [], 0.0
    for i, (spk, phrases, _) in enumerate(TURNS):
        sr, (chunk,) = split_into_n_segments(takes[i], 1, [1])
        src, dst = tmp / f"in_{i:02d}.wav", tmp / f"out_{i:02d}.wav"
        with wave.open(str(src), "wb") as wf:
            wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(sr), wf.writeframes(chunk.tobytes())
        if spk == "F":
            af = f"asetrate={int(sr * 1.10)},aresample={out_sr},atempo=1.20,highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0"
        else:
            af = "atempo=1.32,highpass=f=95"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", af, "-ar", str(out_sr), "-ac", "1", str(dst)], check=True)
        with wave.open(str(dst), "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        al = align_words_in_waveform(pcm.astype(np.float32) / 32768.0, out_sr, [s for _, s in phrases], cur)
        timings.append([(a["s"], a["e"]) for a in al])
        # a short breath between turns reads as a real back-and-forth chat
        gap = 0.28 if i + 1 < len(TURNS) and TURNS[i + 1][0] != spk else 0.14
        pieces += [pcm, np.zeros(int(gap * out_sr), dtype=np.int16)]
        cur += len(pcm) / out_sr + gap

    full = np.concatenate(pieces)
    pre = tmp / "pre_norm.wav"
    with wave.open(str(pre), "wb") as wf:
        wf.setnchannels(1), wf.setsampwidth(2), wf.setframerate(out_sr), wf.writeframes(full.tobytes())
    vo = STUDIO / "assets" / "clips" / CID / "vo.wav"
    vo.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(pre), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(vo)], check=True)
    vo_dur = round(len(full) / out_sr, 3)
    (HERE / "timings.json").write_text(json.dumps({"vo": vo_dur, "turns": timings}, indent=1), encoding="utf-8")
    return vo_dur, timings


def layout(timings):
    """Stack bubbles/photos top-down; scroll the thread whenever a new item would fall below the window."""
    items, scrolls, y, scroll = [], [], 16, 0
    cta_t = timings[CTA_PHRASE[0]][CTA_PHRASE[1]][0]
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

    for ti, (spk, phrases, photo) in enumerate(TURNS):
        if ti == CTA_PHRASE[0]:
            phrases = phrases[: CTA_PHRASE[1]]
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


def esc(s):
    return html.escape(s, quote=True)


def render_html(vo_dur, timings, items, scrolls, cta_t):
    total = round(vo_dur + 1.4, 2)
    turn_starts = [t[0][0] for t in timings]
    heads = []
    for k, (ti, sub, l1, l2) in enumerate(HEADLINES):
        t0 = 0 if k == 0 else round(turn_starts[ti] - 0.1, 3)
        t1 = round(cta_t, 3) if k + 1 == len(HEADLINES) else round(turn_starts[HEADLINES[k + 1][0]] - 0.1, 3)
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
            rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px">{ava}<div class="msg" style="rotate: {it["rot"]}deg">{esc(it["text"])}</div></div>')
        else:
            cls = "photo" if it["kind"] == "photo" else "sticker"
            rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px"><div class="{cls}" style="rotate: {it["rot"]}deg"><img src="{it["src"]}" alt=""></div></div>')

    head_html = "\n        ".join(
        f'<div class="hd" id="hd{k}"><div class="hd-sub">{esc(sub)}</div><div class="hd-t"><span class="hl">{esc(l1)}</span><br><span class="hl">{esc(l2)}</span></div></div>'
        for k, t0, t1, sub, l1, l2 in heads
    )

    # sfx: chat pings on every turn, paper slap on photos, accents on the proof lines
    sfx = []
    for ti, (spk, _, _) in enumerate(TURNS):
        if ti == CTA_PHRASE[0] + 1:
            break
        sfx.append(("msg_recv.mp3" if spk == "F" else "msg_send.mp3", turn_starts[ti] + 0.01, 0.5, 0.3))
    for it in items:
        if it["kind"] in ("photo", "sticker"):
            sfx.append(("paper.mp3", it["t"], 0.45, 0.5))
    sfx.append(("ding.wav", timings[7][0][0] + 0.6, 0.8, 0.3))
    sfx.append(("punch.mp3", timings[8][0][0] + 0.3, 0.5, 0.35))
    sfx.append(("wow.mp3", timings[11][1][1], 1.0, 0.3))
    sfx.append(("whoosh.mp3", cta_t - 0.05, 0.5, 0.4))
    sfx.append(("boom.wav", cta_t + 0.05, 0.8, 0.4))
    sfx.append(("cash_register.mp3", cta_t + 0.55, 1.0, 0.45))
    sfx_html = "\n      ".join(
        f'<audio id="sx{k:02d}" src="assets/shared/sfx/{f}" data-start="{round(t, 3)}" data-duration="{d}" data-track-index="{12 + k % 2}" data-volume="{v}"></audio>'
        for k, (f, t, d, v) in enumerate(sorted(sfx, key=lambda x: x[1]))
    )

    js_items = json.dumps([{"id": f"i{i}", "kind": it["kind"], "side": it["spk"], "t": it["t"], "e": it.get("e")} for i, it in enumerate(items)])
    js_heads = json.dumps([{"id": f"hd{k}", "t0": t0, "t1": t1} for k, t0, t1, *_ in heads])
    js_scrolls = json.dumps(scrolls)
    rows_html = "\n            ".join(rows)

    page = TEMPLATE
    for k, v in {
        "__CID__": CID, "__TOTAL__": str(total), "__VODUR__": str(vo_dur), "__CTA__": str(round(cta_t, 3)),
        "__CTADUR__": str(round(total - cta_t, 3)), "__CHATDUR__": str(round(cta_t, 3)),
        "__ROWS__": rows_html, "__HEADS__": head_html, "__SFX__": sfx_html,
        "__ITEMS__": js_items, "__HEADSJS__": js_heads, "__SCROLLS__": js_scrolls,
        "__WINTOP__": str(WIN_TOP), "__WINH__": str(WIN_H),
    }.items():
        page = page.replace(k, v)
    out = STUDIO / "compositions" / f"{CID}.html"
    out.write_text(page, encoding="utf-8")
    print(f"composition: {out.relative_to(STUDIO)}  ({total}s, vo {vo_dur}s, cta {cta_t:.2f}s)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/kit.js"></script>
    <style>
      /* __CID__ — generated by clips/__CID__/build.py (edit the builder, not this file).
         "พี่บ่าว & น้องนุ้ย" voiced chat on a stop-motion crumpled-paper video (Pexels 30653724). */
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
      .msg {
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
      }
      .row.out .msg {
        background: #8de07a;
      }
      .photo {
        width: 540px;
        height: 540px;
        padding: 14px;
        background: #fff;
        border: 4px solid var(--ink);
        border-radius: 22px;
        box-shadow: 9px 10px 0 rgba(27, 26, 23, 0.22);
      }
      .photo img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 12px;
        display: block;
      }
      .sticker {
        height: 460px;
        filter: drop-shadow(0 0 0 #fff) drop-shadow(8px 10px 0 rgba(27, 26, 23, 0.25));
      }
      .sticker img {
        height: 100%;
        display: block;
      }
      /* CTA */
      #cta-1 {
        top: 330px;
        font-size: 128px;
        color: var(--ink);
      }
      #cta-model {
        top: 500px;
        font-family: "Anuphan", sans-serif;
        font-size: 66px;
        color: var(--ink);
      }
      #cta-heads {
        position: absolute;
        left: 560px;
        top: 700px;
        display: flex;
        gap: 26px;
      }
      #cta-heads img {
        height: 560px;
        filter: drop-shadow(8px 10px 0 rgba(27, 26, 23, 0.25));
      }
      #cta-arrow {
        left: 0;
        top: 0;
        width: 1080px;
        height: 1920px;
      }
      #cta-arrow path {
        fill: none;
        stroke: var(--line-red);
        stroke-width: 22;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      #cta-2 {
        left: 260px;
        top: 1330px;
        font-size: 120px;
        color: var(--line-red);
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
        <div class="t center" id="cta-1"><span class="hl">กดตะกร้าเหลือง</span></div>
        <div class="t center" id="cta-model">Orsen S6 · 240W · เลือกสีได้</div>
        <div id="cta-heads"><img src="assets/els6/img/head_black.png" alt=""><img src="assets/els6/img/head_pink.png" alt=""></div>
        <svg class="fx" id="cta-arrow" viewBox="0 0 1080 1920">
          <path id="cta-shaft" d="M 330 640 C 180 870 120 1190 160 1460" />
          <path id="cta-head" d="M 80 1380 L 160 1470 L 250 1390" />
        </svg>
        <div class="t" id="cta-2">ซ้ายล่าง</div>
      </div>

      <div id="flash"></div>
      <div id="wm"><span>สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง</span></div>

      <audio id="vo0" src="assets/clips/__CID__/vo.wav" data-start="0" data-media-start="0" data-duration="__VODUR__" data-track-index="10" data-volume="1"></audio>
      <audio id="bgm" src="assets/shared/bgm_lofi.wav" data-start="0" data-duration="__TOTAL__" data-track-index="11" data-volume="0.05" data-carve="0.25" data-carve-targets="vo0"></audio>
      __SFX__
    </div>

    <script>
      const tl = gsap.timeline({ paused: true });
      const $ = (s) => document.querySelector(s);
      const CTA = __CTA__;
      const ITEMS = __ITEMS__;
      const HEADS = __HEADSJS__;
      const SCROLLS = __SCROLLS__;

      // headlines swap per scene
      HEADS.forEach((h) => {
        tl.fromTo(`#${h.id}`, { scale: 1.5, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.28, ease: "power4.out" }, h.t0);
        tl.to(`#${h.id}`, { opacity: 0, duration: 0.12 }, h.t1 - 0.12);
      });

      // bubbles pop like paper cut-outs; the spoken one is red, then settles to black
      ITEMS.forEach((it) => {
        const fromX = it.side === "F" ? -50 : 50;
        if (it.kind === "name") {
          tl.fromTo(`#${it.id}`, { opacity: 0 }, { opacity: 1, duration: 0.15 }, it.t);
        } else if (it.kind === "msg") {
          tl.fromTo(`#${it.id}`, { y: 36, x: fromX, scale: 0.7, opacity: 0 }, { y: 0, x: 0, scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }, it.t);
          const m = `#${it.id} .msg`;
          tl.set(m, { color: "#d90429" }, it.t);
          tl.set(m, { color: "#111111" }, it.e);
        } else {
          tl.fromTo(`#${it.id}`, { y: 60, scale: 0.4, rotation: fromX > 0 ? 14 : -14, opacity: 0 }, { y: 0, scale: 1, rotation: 0, opacity: 1, duration: 0.42, ease: "back.out(1.7)" }, it.t);
        }
      });
      SCROLLS.forEach(([t, y]) => tl.to("#thread", { y: -y, duration: 0.32, ease: "power2.out" }, t));

      // CTA
      tl.to("#chatwin", { y: 140, opacity: 0, duration: 0.25, ease: "power2.in" }, CTA - 0.25);
      HF.flash(tl)(CTA, 0.5, 0.25);
      tl.fromTo("#cta-1", { scale: 1.9, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "power4.out" }, CTA + 0.05);
      tl.fromTo("#cta-model", { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "power3.out" }, CTA + 0.3);
      tl.fromTo("#cta-heads img", { y: -300, rotation: 10, opacity: 0 }, { y: 0, rotation: 0, opacity: 1, duration: 0.45, ease: "back.out(2)", stagger: 0.15 }, CTA + 0.35);
      const sl = HF.dash($("#cta-shaft"));
      const hl = HF.dash($("#cta-head"));
      tl.fromTo("#cta-shaft", { strokeDashoffset: sl }, { strokeDashoffset: 0, duration: 0.45, ease: "power2.inOut" }, CTA + 0.4);
      tl.fromTo("#cta-head", { strokeDashoffset: hl }, { strokeDashoffset: 0, duration: 0.16, ease: "power2.out" }, CTA + 0.82);
      tl.fromTo("#cta-2", { x: -80, opacity: 0 }, { x: 0, opacity: 1, duration: 0.3, ease: "expo.out" }, CTA + 0.95);
      tl.to("#cta-arrow", { x: -18, y: 18, duration: 0.25, ease: "sine.inOut", yoyo: true, repeat: 3 }, CTA + 1.25);

      window.__timelines["__CID__"] = tl;
    </script>
  </body>
</html>
"""


def main():
    vo_dur, timings = assemble(voice())
    items, scrolls, cta_t = layout(timings)
    render_html(vo_dur, timings, items, scrolls, cta_t)


if __name__ == "__main__":
    main()
