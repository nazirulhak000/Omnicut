# -*- coding: utf-8 -*-
"""100% Style 3B Golden Formula HTML Composition Builder for Couple Paper Chat (#5)."""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import wave

from scripts.config import BASE_DIR
from scripts.couple_engine.config import load_couple_product_config

WIN_TOP, WIN_H = 470, 1170
NAME_H, BUBBLE_H, GAP, TURN_GAP = 44, 104, 12, 30
PHOTO_H, STICKER_H = 540, 460
SCROLL_PAD = 40

# Regex matching emoji ranges (supplemental symbols, dingbats, transport/map, etc.)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)
_PRICE_RE = re.compile(r"(?:\d[\d,]*\s*(?:บาท|฿)|(?:ราคา\s*)?\d[\d,]*\s*บ\.|฿\s*\d[\d,]*|บาท|฿)")

CANONICAL_COUPLE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="kit/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/channels.js"></script>
    <script src="kit/kit.js"></script>
    <style>
      /* __CID__ — Canonical Couple Paper Chat (#5) 100% Golden Master Parity */
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

      /* ==================== CTA OUTRO SHOT (STYLE 3B GOLDEN MASTER) ==================== */
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
      .t.center {
        text-align: center;
        width: 100%;
        left: 0;
        right: 0;
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
        font-size: __CTA_TITLE_FONT_SIZE__px;
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
      __CTA_STAGE_CSS__

      .bottom-info {
        position: absolute;
        bottom: 270px;
        left: 40px;
        right: 40px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 14px;
        z-index: 25;
      }
      .swatch-card {
        background: #ffffff;
        border: 3px solid #1b1a17;
        border-radius: 18px;
        box-shadow: 3px 5px 0 #1b1a17;
        padding: 8px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
      }
      .swatch-title {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 24px;
        color: #1b1a17;
      }
      .chips-grid {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .chip-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 22px;
        color: #1b1a17;
      }
      .chip-dot {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 2px solid #1b1a17;
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
        background: #ffffff;
        color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 6px 18px;
        border-radius: 12px;
        box-shadow: 3px 5px 0 #1b1a17;
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
        <div class="t center" id="cta-1"><span class="hl">__CTA_TITLE__</span></div>
        <div class="t center" id="cta-model">__CTA_SUB__</div>
        <div id="cta-stage">
          __CTA_STAGE_HTML__
        </div>

        <div class="bottom-info">
          __BOTTOM_INFO_HTML__
        </div>
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
      __CTA_GSAP_TIMELINE__
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.35);

      window.__timelines = window.__timelines || {};
      window.__timelines["__CID__"] = tl;
    </script>
  </body>
</html>"""


def sanitize_display_text(text: str) -> str:
    """Strip any emoji characters or forbidden price strings ('บาท', '฿') from display text."""
    if not text:
        return ""
    cleaned = _EMOJI_RE.sub("", str(text))
    cleaned = _PRICE_RE.sub("", cleaned)
    return cleaned


def layout_thread(
    timings: Sequence[Sequence[Sequence[float]]],
    turns_spec: Sequence[Tuple[str, Sequence[Tuple[str, str]], Any]],
    cta_phrase: Tuple[int, int],
) -> Tuple[List[Dict[str, Any]], List[Tuple[float, int]], float]:
    """Calculate deterministic vertical scroll and item positions (100% canonical parity)."""
    items: List[Dict[str, Any]] = []
    scrolls: List[Tuple[float, int]] = []
    y = 16
    scroll = 0
    ti_clamp = min(cta_phrase[0], len(timings) - 1)
    pi_clamp = min(cta_phrase[1], len(timings[ti_clamp]) - 1)
    cta_t = timings[ti_clamp][pi_clamp][0]
    tilt = [-1.2, 0.8, -0.6, 1.1, -0.9, 0.5]
    n = 0

    def place(h: int, t: float) -> int:
        nonlocal y, scroll
        top = y
        y += h
        if y - scroll > WIN_H - SCROLL_PAD:
            scroll = y - (WIN_H - SCROLL_PAD)
            scrolls.append((round(t - 0.05, 3), scroll))
        return top

    for ti, (spk, phrases, photo) in enumerate(turns_spec):
        if ti >= len(timings):
            break
        if ti == cta_phrase[0]:
            phrases = phrases[: cta_phrase[1] + 1]
        t0 = timings[ti][0][0]
        items.append({"kind": "name", "spk": spk, "t": t0, "top": place(NAME_H, t0)})
        for pi, (disp, _) in enumerate(phrases):
            if pi >= len(timings[ti]):
                break
            s, e = timings[ti][pi]
            if pi:
                y += GAP
            items.append(
                {
                    "kind": "msg",
                    "spk": spk,
                    "text": sanitize_display_text(disp),
                    "t": s,
                    "e": e,
                    "first": pi == 0,
                    "top": place(BUBBLE_H, s),
                    "rot": tilt[n % len(tilt)],
                }
            )
            n += 1
            if photo and photo[0] == pi:
                tp = round(s + 0.25, 3)
                y += GAP + 6
                h = PHOTO_H if photo[2] == "photo" else STICKER_H
                photo_src = (
                    str(photo[1])
                    .replace("03_Projects/_HyperFrames_Studio/", "")
                    .replace("\\", "/")
                    .lstrip("/")
                )
                items.append(
                    {
                        "kind": photo[2],
                        "spk": spk,
                        "src": photo_src,
                        "t": tp,
                        "top": place(h, tp),
                        "rot": -2.5 if spk == "M" else 2.5,
                    }
                )
        y += TURN_GAP
    return items, scrolls, cta_t


def _normalize_turns_spec(
    raw_turns: Sequence[Any],
) -> List[Tuple[str, List[Tuple[str, str]], Any]]:
    turns_spec: List[Tuple[str, List[Tuple[str, str]], Any]] = []
    for turn in raw_turns:
        if isinstance(turn, (list, tuple)):
            spk = str(turn[0]).strip().upper()[0]
            p_raw = turn[1] if len(turn) > 1 else []
            if isinstance(p_raw, str):
                p_tuples = [(p_raw, p_raw)]
            else:
                p_tuples = []
                for p in p_raw:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        p_tuples.append((str(p[0]), str(p[1])))
                    elif isinstance(p, dict):
                        d = str(p.get("display_text") or p.get("display") or p.get("text") or "")
                        s = str(p.get("spoken_text") or p.get("spoken") or d)
                        p_tuples.append((d, s))
                    else:
                        p_tuples.append((str(p), str(p)))
            photo = turn[2] if len(turn) > 2 else None
        else:
            spk = str(turn.get("speaker", "F")).strip().upper()[0]
            phrases = turn.get("phrases", [])
            if phrases:
                p_tuples = []
                for p in phrases:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        p_tuples.append((str(p[0]), str(p[1])))
                    elif isinstance(p, dict):
                        d = str(p.get("display_text") or p.get("display") or p.get("text") or "")
                        s = str(p.get("spoken_text") or p.get("spoken") or d)
                        p_tuples.append((d, s))
                    else:
                        p_tuples.append((str(p), str(p)))
            else:
                d = str(turn.get("display_text") or turn.get("text") or "")
                s = str(turn.get("spoken_text") or d)
                p_tuples = [(d, s)]
            photo = turn.get("product_photo") or turn.get("photo")
        turns_spec.append((spk, p_tuples, photo))
    return turns_spec


def _normalize_timings(
    timings_input: Union[Dict[str, Any], Sequence[Any]],
    turns_spec: Sequence[Tuple[str, List[Tuple[str, str]], Any]],
) -> Tuple[List[List[Tuple[float, float]]], float]:
    """Extract per-turn phrase timing pairs and total vo_dur."""
    vo_dur: Optional[float] = None
    if isinstance(timings_input, dict):
        vo_dur = timings_input.get("vo")
        raw_turns = timings_input.get("turns", [])
    else:
        raw_turns = list(timings_input)

    normalized: List[List[Tuple[float, float]]] = []
    for ti, (_, phrases, _) in enumerate(turns_spec):
        if ti < len(raw_turns):
            t_entry = raw_turns[ti]
            if isinstance(t_entry, dict) and "start" in t_entry and "end" in t_entry:
                s0 = float(t_entry["start"])
                e0 = float(t_entry["end"])
                n_p = max(1, len(phrases))
                step = (e0 - s0) / n_p
                normalized.append(
                    [(round(s0 + k * step, 3), round(s0 + (k + 1) * step, 3)) for k in range(n_p)]
                )
            elif isinstance(t_entry, (list, tuple)) and len(t_entry) > 0:
                if isinstance(t_entry[0], (int, float)) and len(t_entry) == 2:
                    s0, e0 = float(t_entry[0]), float(t_entry[1])
                    n_p = max(1, len(phrases))
                    step = (e0 - s0) / n_p
                    normalized.append(
                        [(round(s0 + k * step, 3), round(s0 + (k + 1) * step, 3)) for k in range(n_p)]
                    )
                else:
                    normalized.append([(float(p[0]), float(p[1])) for p in t_entry])
            else:
                base = ti * 3.0
                normalized.append([(base, base + 2.5)])
        else:
            base = ti * 3.0
            normalized.append([(base, base + 2.5)])

    if vo_dur is None:
        if normalized and normalized[-1]:
            vo_dur = round(float(normalized[-1][-1][1]) + 0.12, 3)
        else:
            vo_dur = 30.0
    return normalized, round(float(vo_dur), 3)


def compose_clip_html(
    product_config: Union[Dict[str, Any], str],
    clip_spec: Dict[str, Any],
    timings: Union[Dict[str, Any], Sequence[Any]],
    output_html_path: Union[Path, str],
) -> Path:
    """Compose a 1080x1920 9:16 Couple Paper Chat HTML file with 100% Style 3B Golden Formula parity."""
    if isinstance(product_config, str):
        cfg = load_couple_product_config(product_config)
    else:
        cfg = dict(product_config)

    cid = str(
        clip_spec.get("cid")
        or clip_spec.get("clip_id")
        or clip_spec.get("id")
        or f"{cfg.get('clip_prefix', 'couple-pov-s')}01"
    )
    raw_turns = clip_spec.get("turns") or clip_spec.get("dialogue_turns") or []
    turns_spec = _normalize_turns_spec(raw_turns)
    norm_timings, vo_dur = _normalize_timings(timings, turns_spec)

    if "vo_dur" in clip_spec and clip_spec["vo_dur"] is not None:
        vo_dur = round(float(clip_spec["vo_dur"]), 3)

    last_ti = min(len(turns_spec) - 1, len(norm_timings) - 1)
    last_pi = min(len(turns_spec[last_ti][1]) - 1, len(norm_timings[last_ti]) - 1)
    cta_phrase = (last_ti, last_pi)

    items, scrolls, cta_t = layout_thread(norm_timings, turns_spec, cta_phrase)

    # Note: Canonical parity uses `top_headlines` if present in script, else falls back to default 4 headlines
    headlines = clip_spec.get("top_headlines", [])
    if not headlines:
        headlines = [
            {
                "turn": 0,
                "sub": "POV: สไตล์คู่รักสายใต้",
                "t": sanitize_display_text(cfg["title"]),
                "hl": sanitize_display_text(cfg["sub"].split("·")[0]),
            },
            {
                "turn": min(3, len(turns_spec) - 1),
                "sub": "พี่บ่าวแนะนำตัวเด็ด",
                "t": "ของดีต้องมีติดตัว",
                "hl": "ชี้เป้าตัวจบ",
            },
            {
                "turn": min(6, len(turns_spec) - 1),
                "sub": "ของแท้ ปลอดภัย 100%",
                "t": "สเปกจัดเต็มคุ้มราคา",
                "hl": "ลองแล้วจะรัก",
            },
            {
                "turn": len(turns_spec) - 1,
                "sub": "พิกัดโปรสุดคุ้ม",
                "t": "กดตะกร้าเหลือง",
                "hl": "มีจำนวนจำกัด",
            },
        ]

    total = round(vo_dur + 1.4, 2)
    turn_starts = [t[0][0] for t in norm_timings]
    n_turns = len(turn_starts)

    turn_indices: List[int] = []
    for k, h in enumerate(headlines):
        target = h.get("turn", 0)
        if target >= n_turns:
            target = min(int(k * (n_turns - 1) / max(1, len(headlines) - 1)), n_turns - 1)
        turn_indices.append(target)
    for i_idx in range(1, len(turn_indices)):
        if turn_indices[i_idx] <= turn_indices[i_idx - 1]:
            turn_indices[i_idx] = min(turn_indices[i_idx - 1] + 1, n_turns - 1)

    heads = []
    for k, h in enumerate(headlines):
        ti = turn_indices[k]
        sub = sanitize_display_text(h.get("sub", ""))
        l1 = sanitize_display_text(h.get("t", ""))
        l2 = sanitize_display_text(h.get("hl", ""))
        t0 = 0 if k == 0 else round(turn_starts[ti] - 0.1, 3)
        if k + 1 == len(headlines):
            t1 = round(cta_t, 3)
        else:
            next_ti = turn_indices[k + 1]
            t1 = round(turn_starts[next_ti] - 0.1, 3) if next_ti > ti else round(cta_t, 3)
        if t1 <= t0:
            t1 = round(t0 + 2.0, 3)
        heads.append((k, t0, t1, sub, l1, l2))

    rows: List[str] = []
    for i, it in enumerate(items):
        side = "in" if it["spk"] == "F" else "out"
        if it["kind"] == "name":
            label = "น้องนุ้ย" if it["spk"] == "F" else "พี่บ่าว"
            rows.append(f'<div class="nm {side}" id="i{i}" style="top: {it["top"]}px">{label}</div>')
        elif it["kind"] == "msg":
            ava = ""
            if it["first"]:
                ava = f'<div class="ava {"f" if side == "in" else "m"}">{"น" if side == "in" else "บ"}</div>'
            rows.append(
                f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px">{ava}<div class="msg" style="rotate: {it["rot"]}deg">{html.escape(it["text"], quote=True)}</div></div>'
            )
        else:
            cls = "photo" if it["kind"] == "photo" else "sticker"
            rows.append(
                f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px"><div class="{cls}" style="rotate: {it["rot"]}deg"><img src="{it["src"]}" alt=""></div></div>'
            )

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
    sfx.append(("ding.wav", norm_timings[min(5, len(norm_timings) - 1)][0][0] + 0.3, 0.8, 0.3))
    sfx.append(("punch.mp3", norm_timings[min(8, len(norm_timings) - 1)][0][0] + 0.3, 0.5, 0.35))
    sfx.append(("wow.mp3", norm_timings[min(10, len(norm_timings) - 1)][0][0] + 0.2, 1.0, 0.3))
    sfx.append(("whoosh.mp3", cta_t - 0.05, 0.5, 0.18))
    sfx.append(("boom.wav", cta_t + 0.07, 0.8, 0.15))
    sfx.append(("cash_register.mp3", cta_t + 0.55, 1.0, 0.20))

    sfx_html = "\n      ".join(
        f'<audio id="sx{k:02d}" src="assets/shared/sfx/{f}" data-start="{round(t, 3)}" data-duration="{d}" data-track-index="{12 + k % 2}" data-volume="{v}"></audio>'
        for k, (f, t, d, v) in enumerate(sorted(sfx, key=lambda x: x[1]))
    )

    js_items = json.dumps(
        [{"id": f"i{i}", "kind": it["kind"], "side": it["spk"], "t": it["t"], "e": it.get("e")} for i, it in enumerate(items)]
    )
    js_heads = json.dumps([{"id": f"hd{k}", "t0": t0, "t1": t1} for k, t0, t1, *_ in heads])
    js_scrolls = json.dumps(scrolls)
    rows_html = "\n            ".join(rows)

    page = CANONICAL_COUPLE_TEMPLATE
    replacements = {
        "__CID__": cid,
        "__TOTAL__": str(total),
        "__VODUR__": str(vo_dur),
        "__CTA__": str(round(cta_t, 3)),
        "__CTADUR__": str(round(total - cta_t, 3)),
        "__CHATDUR__": str(round(cta_t, 3)),
        "__ROWS__": rows_html,
        "__HEADS__": head_html,
        "__SFX__": sfx_html,
        "__ITEMS__": js_items,
        "__HEADSJS__": js_heads,
        "__SCROLLS__": js_scrolls,
        "__WINTOP__": str(WIN_TOP),
        "__WINH__": str(WIN_H),
        "__CTA_TITLE__": sanitize_display_text(cfg["title"]),
        "__CTA_TITLE_FONT_SIZE__": str(cfg.get("title_font_size", 82)),
        "__CTA_SUB__": sanitize_display_text(cfg["sub"]),
        "__CTA_STAGE_CSS__": cfg["cta_stage_css"],
        "__CTA_STAGE_HTML__": sanitize_display_text(cfg["cta_stage_html"]),
        "__CTA_GSAP_TIMELINE__": cfg["cta_gsap_timeline"],
        "__BOTTOM_INFO_HTML__": sanitize_display_text(cfg["bottom_info_html"]),
    }
    for k, v in replacements.items():
        page = page.replace(k, v)

    out_path = Path(output_html_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def generate_clip(
    product_code: str,
    clip_index: int = 1,
    *,
    project_root: Optional[Path] = None,
    output_html_path: Optional[Union[Path, str]] = None,
    timings: Optional[Union[Dict[str, Any], Sequence[Any]]] = None,
    vo_dur: Optional[float] = None,
) -> Path:
    """Generate a single Couple Paper Chat composition HTML by product code and 1-based clip index."""
    root = Path(project_root).resolve() if project_root else BASE_DIR
    studio = root / "03_Projects" / "_HyperFrames_Studio"
    cfg = load_couple_product_config(product_code, project_root=root)

    scripts_file = cfg.get("scripts_file")
    if not scripts_file or not Path(scripts_file).exists():
        raise FileNotFoundError(f"Scripts file not found for {product_code}: {scripts_file}")

    scripts = json.loads(Path(scripts_file).read_text(encoding="utf-8"))
    if clip_index < 1 or clip_index > len(scripts):
        raise IndexError(f"clip_index {clip_index} out of range (1..{len(scripts)})")

    script_entry = dict(scripts[clip_index - 1])
    cid = f"{cfg['clip_prefix']}{clip_index:02d}"
    script_entry["cid"] = cid

    clip_dir = studio / "clips" / cid
    vo_p = studio / "assets" / "clips" / cid / "vo.wav"
    timings_p = clip_dir / "timings.json"

    if timings is None:
        if timings_p.exists():
            timings = json.loads(timings_p.read_text(encoding="utf-8"))
        else:
            # Deterministic fallback timings when audio has not been generated yet
            raw_turns = script_entry.get("turns") or script_entry.get("dialogue_turns") or []
            turns_spec = _normalize_turns_spec(raw_turns)
            synth_turns = []
            cur = 0.0
            for _, phrases, _ in turns_spec:
                p_list = []
                for _ in phrases:
                    p_list.append([round(cur, 3), round(cur + 1.5, 3)])
                    cur += 1.6
                synth_turns.append(p_list)
                cur += 0.2
            timings = {"vo": round(cur, 3), "turns": synth_turns}

    if vo_dur is None and vo_p.exists():
        with wave.open(str(vo_p), "rb") as wf:
            vo_dur = round(wf.getnframes() / float(wf.getframerate()), 3)
    if vo_dur is not None:
        script_entry["vo_dur"] = vo_dur

    target_html = (
        Path(output_html_path)
        if output_html_path is not None
        else studio / "compositions" / f"{cid}.html"
    )
    out = compose_clip_html(cfg, script_entry, timings, target_html)

    if output_html_path is None and clip_dir.exists():
        (clip_dir / "index.html").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    return out
