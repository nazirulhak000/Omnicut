#!/usr/bin/env python3
"""
sub-srt: accurate .srt subtitles from audio/video for CapCut and any NLE.

Core principle: TIMESTAMPS COME FROM REAL SPEECH RECOGNITION, NEVER FROM GUESSING.
A local Whisper engine produces word/segment timestamps; this script re-chunks
them into clean cues, enforces on-screen timing, and writes strict UTF-8 SRT.

Engines (auto-detected):
  * Apple Silicon   -> mlx-whisper    (GPU / Metal)
  * everything else -> faster-whisper (CPU, or CUDA if present)
Override with env SUBSRT_ENGINE=mlx|faster.

Modes:
  bilingual (default) : each caption = spoken line + English translation stacked
  mono                : single line track, 3-4 words/line karaoke style
  dual                : two files, one original + one English translation

Usage:  python generate_srt.py INPUT [--mode bilingual|mono|dual] [--lang th] [...]
See README.md / SKILL.md for the full flag list.
"""
import argparse, bisect, math, os, platform, subprocess, sys, unicodedata

SR = 16000
CJK_LANGS = {"zh", "ja", "yue"}
NOSPACE_LANGS = CJK_LANGS | {"th", "lo", "my", "km"}
SENT_END = set(".?!…。？！！?～")

MLX_MAP = {
    "tiny": "mlx-community/whisper-tiny",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
    "turbo": "mlx-community/whisper-large-v3-turbo",
}
FW_MAP = {  # faster-whisper size keywords
    "tiny": "tiny", "base": "base", "small": "small", "medium": "medium",
    "large-v3": "large-v3", "large": "large-v3", "turbo": "large-v3-turbo",
}
_FW_MODELS = {}


def eprint(*a):
    print(*a, file=sys.stderr)


# ----------------------------------------------------------------------------
# audio
# ----------------------------------------------------------------------------
def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_audio(path):
    """Decode any audio/video to 16k mono float32 (auto-extracts a video's audio)."""
    import numpy as np
    ff = ffmpeg_exe()
    try:
        raw = subprocess.run(
            [ff, "-nostdin", "-threads", "0", "-i", path,
             "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
            capture_output=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        eprint("ffmpeg failed to decode:", path)
        eprint(e.stderr.decode("utf-8", "replace")[-800:])
        sys.exit(2)
    if not raw:
        eprint("No audio decoded (missing audio track?):", path)
        sys.exit(2)
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


# ----------------------------------------------------------------------------
# engine abstraction
# ----------------------------------------------------------------------------
def detect_engine():
    forced = os.environ.get("SUBSRT_ENGINE")
    if forced:
        return forced
    is_apple = sys.platform == "darwin" and platform.machine() == "arm64"
    if is_apple:
        try:
            import mlx_whisper  # noqa
            return "mlx"
        except ImportError:
            pass
    try:
        import faster_whisper  # noqa
        return "faster"
    except ImportError:
        pass
    try:
        import mlx_whisper  # noqa
        return "mlx"
    except ImportError:
        eprint("No Whisper engine installed. Run: bash setup.sh")
        sys.exit(3)


def _mlx_transcribe(audio, size, language, task, want_words):
    import mlx_whisper
    kw = dict(path_or_hf_repo=MLX_MAP.get(size, size), word_timestamps=want_words,
              # deterministic + repetition-resistant: kills the "avoiravoir" loop
              temperature=0.0, condition_on_previous_text=False,
              compression_ratio_threshold=2.4)
    if language:
        kw["language"] = language
    if task and task != "transcribe":
        kw["task"] = task
    r = mlx_whisper.transcribe(audio, **kw)
    segs = []
    for s in r.get("segments", []):
        words = ([{"s": w["start"], "e": w["end"], "t": w["word"]}
                  for w in (s.get("words") or [])] if want_words else [])
        segs.append({"start": s["start"], "end": s["end"],
                     "text": s.get("text", ""), "words": words})
    return {"language": r.get("language"), "segments": segs}


def _faster_transcribe(audio, size, language, task, want_words):
    from faster_whisper import WhisperModel
    key = FW_MAP.get(size, size)
    if key not in _FW_MODELS:
        # int8 runs everywhere; device="auto" picks CUDA if present
        _FW_MODELS[key] = WhisperModel(key, device="auto", compute_type="int8")
    model = _FW_MODELS[key]
    seg_iter, info = model.transcribe(
        audio, language=language, task=task, word_timestamps=want_words,
        temperature=0.0, condition_on_previous_text=False)
    segs = []
    for s in seg_iter:  # generator -> must be consumed
        words = ([{"s": w.start, "e": w.end, "t": w.word}
                  for w in (s.words or [])] if want_words else [])
        segs.append({"start": s.start, "end": s.end, "text": s.text, "words": words})
    return {"language": info.language, "segments": segs}


def transcribe(audio, size, language, engine, task="transcribe", want_words=True):
    if engine == "mlx":
        return _mlx_transcribe(audio, size, language, task, want_words)
    return _faster_transcribe(audio, size, language, task, want_words)


# ----------------------------------------------------------------------------
# text / line helpers
# ----------------------------------------------------------------------------
def graphemes(text):
    """Split into grapheme clusters (base char + its combining marks) so a Thai
    tone/vowel mark is never separated from its consonant."""
    out = []
    for ch in text:
        if out and unicodedata.category(ch) in ("Mn", "Mc", "Me"):
            out[-1] += ch
        else:
            out.append(ch)
    return out


# Thai marks that must never start a line — attach to the preceding word
_TRAIL_MARKS = ("ๆ", "ฯ")


def _merge_trailing_marks(units):
    out = []
    for u in units:
        if out and u and u[0] in _TRAIL_MARKS:
            out[-1] += u
        else:
            out.append(u)
    return out


def space_latin(text):
    """In no-space scripts (Thai/CJK), put a space before/after any embedded run
    of Latin letters or digits so 'ก็คือExportแค่เสียง' -> 'ก็คือ Export แค่เสียง'
    (less crowded, easier to read). Leaves already-spaced boundaries alone."""
    def latin(ch):
        return ch.isascii() and ch.isalnum()

    def native(ch):
        return (not ch.isascii()) and (ch.isalpha() or unicodedata.category(ch)
                                       in ("Mn", "Mc"))
    out = []
    for i, ch in enumerate(text):
        if i > 0:
            prev = text[i - 1]
            if ((native(prev) and latin(ch)) or (latin(prev) and native(ch))):
                if out and out[-1] not in (" ", "\n"):
                    out.append(" ")
        out.append(ch)
    return "".join(out)


def _is_latin(ch):
    return ch.isascii() and (ch.isalnum() or ch in "._-/'&%+")


def _is_native(ch):
    return (not ch.isascii()) and (ch.isalpha()
                                   or unicodedata.category(ch) in ("Mn", "Mc", "Me"))


def _tokenize_native(t, lang):
    """Tokenize a run of pure Thai/CJK text into words."""
    if not t:
        return []
    units = None
    if lang == "th":
        try:
            from pythainlp.tokenize import word_tokenize
            units = [w for w in word_tokenize(t, engine="newmm") if w.strip()]
        except Exception:
            units = None
    elif lang in ("zh", "yue"):
        try:
            import jieba
            units = [w for w in jieba.cut(t) if w.strip()]
        except Exception:
            units = None
    return units if units is not None else graphemes(t)


def nospace_units(text, lang):
    """Split into VISUAL units. Thai/CJK runs are tokenized into words (so lines
    never break mid-word); embedded Latin/number runs are split on their ORIGINAL
    spaces and kept as separate word-units, so 'Export Audio' stays two words."""
    units, thai_buf, lat_buf = [], [], []

    def flush_thai():
        if thai_buf:
            units.extend(_tokenize_native("".join(thai_buf), lang))
            thai_buf.clear()

    def flush_lat():
        if lat_buf:
            s = "".join(lat_buf).strip()
            if s:
                units.extend(s.split())  # keep each English word separate
            lat_buf.clear()

    for ch in text:
        if ch == " ":
            if lat_buf:
                lat_buf.append(" ")   # preserve spaces between English words
            continue                  # drop Thai-adjacent spaces
        if _is_latin(ch):
            flush_thai(); lat_buf.append(ch)
        elif _is_native(ch):
            flush_lat(); thai_buf.append(ch)
        else:  # punctuation — attach to whichever run is active
            if lat_buf:
                lat_buf.append(ch)
            elif thai_buf:
                thai_buf.append(ch)
            elif ch.strip():
                units.append(ch)
    flush_thai(); flush_lat()
    return _merge_trailing_marks([u for u in units if u.strip()])


def _unit_is_latin(u):
    """A unit is a 'Latin word' if it has ASCII alphanumerics and no native chars
    (so '.srt', '200-300', 'CapCut' count; a Thai word does not)."""
    return (any(c.isascii() and c.isalnum() for c in u)
            and not any(_is_native(c) for c in u))


def _join_nospace(units):
    """Join Thai/CJK word-units with no space, but put a single space at any
    boundary touching a Latin/number word (front, back, and between two of them)."""
    out, prev_latin = "", False
    for u in units:
        u = u.strip()
        if not u:
            continue
        cur_latin = _unit_is_latin(u)
        if out and out[-1] != " " and (cur_latin or prev_latin):
            out += " "
        out += u
        prev_latin = cur_latin
    return out


def units_for(text, lang):
    """Width of a token for cue-size budgeting (graphemes for no-space langs)."""
    if lang in NOSPACE_LANGS:
        return len(graphemes(text.replace(" ", "")))
    return 1


def join_tokens(tokens, lang):
    if lang in NOSPACE_LANGS:
        return _join_nospace(tokens)
    return " ".join(t.strip() for t in tokens if t.strip())


def _wrap_units(units, lang, per_line, max_lines):
    lines, cur, cur_w = [], [], 0
    for u in units:
        w = len(graphemes(u)) if lang in NOSPACE_LANGS else 1
        if cur and cur_w + w > per_line and len(lines) < max_lines - 1:
            lines.append(cur); cur, cur_w = [], 0
        cur.append(u); cur_w += w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines[max_lines - 1:] = [sum(lines[max_lines - 1:], [])]
    if lang in NOSPACE_LANGS:
        return "\n".join(_join_nospace(l) for l in lines)
    return "\n".join(" ".join(l) for l in lines)


def wrap_text(text, lang, per_line, max_lines):
    units = nospace_units(text, lang) if lang in NOSPACE_LANGS else text.split()
    return _wrap_units(units, lang, per_line, max_lines)


def wrap_lines(tokens, lang, per_line, max_lines):
    # whisper word tokens -> clean raw text -> word-aware wrap
    return wrap_text(join_tokens(tokens, lang), lang, per_line, max_lines)


def repair_orphans(cues, lang):
    """Safety net: if a no-space cue starts with a combining mark (a Whisper
    segment split mid-grapheme), move it back onto the previous cue."""
    if lang not in NOSPACE_LANGS:
        return cues
    for i in range(1, len(cues)):
        txt = cues[i].get("text", "")
        j = 0
        while j < len(txt) and txt[j].isspace():
            j += 1
        k = j
        while k < len(txt) and unicodedata.category(txt[k]) in ("Mn", "Mc", "Me"):
            k += 1
        if k > j:
            cues[i]["text"] = txt[:j] + txt[k:]
            cues[i - 1]["text"] = cues[i - 1].get("text", "") + txt[j:k]
    return cues


def collect_words(segments):
    words = []
    for seg in segments:
        for w in seg.get("words", []) or []:
            txt = (w.get("t") or "").strip()
            st, en = w.get("s"), w.get("e")
            if not txt or st is None or en is None:
                continue
            if en < st:
                en = st
            words.append({"t": txt, "s": float(st), "e": float(en)})
    return words


# ----------------------------------------------------------------------------
# cue building
# ----------------------------------------------------------------------------
def build_cues(words, lang, per_line, max_lines, max_dur, pause_gap):
    """Karaoke re-chunk: break at pauses, sentence punctuation, line/dur budgets."""
    max_units = per_line * max_lines
    cues, cur, cur_u = [], [], 0

    def flush():
        nonlocal cur, cur_u
        if cur:
            cues.append({"start": cur[0]["s"], "end": cur[-1]["e"],
                         "tokens": [w["t"] for w in cur]})
        cur, cur_u = [], 0

    prev = None
    for w in words:
        u = units_for(w["t"], lang)
        gap = (w["s"] - prev["e"]) if prev else 0.0
        dur = (w["e"] - cur[0]["s"]) if cur else 0.0
        if cur and (gap >= pause_gap or cur_u + u > max_units or dur > max_dur):
            flush()
        cur.append(w); cur_u += u
        if w["t"] and w["t"][-1] in SENT_END:
            flush()
        prev = w
    flush()
    for c in cues:
        c["text"] = wrap_lines(c["tokens"], lang, per_line, max_lines)
    return [c for c in cues if c["text"].strip()]


def proportional_split(words, n):
    """Split a word list into n groups of roughly equal size, order preserved."""
    n = max(1, n)
    out = [[] for _ in range(n)]
    if not words:
        return out
    per = len(words) / n
    for j, w in enumerate(words):
        out[min(n - 1, int(j / per))].append(w)
    return out


def frac_to_time(s):
    """Map a character-fraction [0,1] of a segment to a real time, using Whisper's
    word-level timings so box boundaries land on actual speech (captures pauses and
    fast/slow pacing). Falls back to uniform if no word timings are present."""
    start, end = s["start"], s["end"]
    uniform = lambda f: start + (end - start) * max(0.0, min(1.0, f))
    words = collect_words([s])
    lens = [len(graphemes((w["t"] or "").strip().replace(" ", ""))) for w in words]
    tot = sum(lens)
    if not words or tot == 0:
        return uniform
    # Whisper sometimes pads seconds of silence onto a single token (a multi-second
    # "word"). Those timings are unreliable and cluster the boxes, leaving false
    # gaps — detect and spread evenly across the segment instead.
    if any((w["e"] - w["s"]) > 2.5 for w in words):
        return uniform
    fracs, times, cum = [], [], 0
    for w, l in zip(words, lens):
        if l == 0:
            continue
        fracs.append(cum / tot); times.append(w["s"])
        cum += l
        fracs.append(cum / tot); times.append(w["e"])

    def f2t(f):
        f = max(0.0, min(1.0, f))
        for i in range(1, len(fracs)):
            if fracs[i] >= f:
                span = fracs[i] - fracs[i - 1]
                if span <= 0:
                    return times[i]
                return times[i - 1] + (times[i] - times[i - 1]) * (f - fracs[i - 1]) / span
        return times[-1]
    return f2t


def boxes_from_segment(s, lang, box_words, max_dur, pause_gap):
    """Split ONE segment into short boxes of <= box_words words each, on a single
    line, with real timing. Spaced langs use reliable word timestamps; Thai/CJK
    re-tokenize the clean text and place box boundaries via Whisper word timings."""
    start, end = s["start"], s["end"]
    if lang not in NOSPACE_LANGS:
        words = collect_words([s])
        if words:
            sub = build_cues(words, lang, box_words, 1, max_dur, pause_gap)
            return [{"start": c["start"], "end": c["end"], "text": c["text"]}
                    for c in sub]
        units = (s.get("text") or "").strip().split()
    else:
        units = nospace_units((s.get("text") or "").strip(), lang)
    if not units:
        return []
    # box time comes from CHARACTER position mapped through real Whisper word
    # timings (frac_to_time) — captures pauses/pacing, so boxes land on speech.
    char_w = [len(graphemes(u)) for u in units]
    total = sum(char_w) or 1
    f2t = frac_to_time(s)
    groups = []
    for i in range(0, len(units), box_words):
        groups.append((units[i:i + box_words], char_w[i:i + box_words]))
    out, acc = [], 0
    for g, cw in groups:
        cs = f2t(acc / total); acc += sum(cw)
        ce = f2t(acc / total)
        out.append({"start": cs, "end": ce, "text": join_tokens(g, lang)})
    return out


def original_cues(segments, lang, box_words, max_dur, pause_gap):
    """Short single-language boxes (mono / dual-original)."""
    cues = []
    for s in segments:
        cues += boxes_from_segment(s, lang, box_words, max_dur, pause_gap)
    return [c for c in cues if c.get("text", "").strip()]


def natural_split(words, n):
    """Split a word list into n roughly-equal groups (order preserved), snapping
    each boundary to a nearby sentence/clause break so chunks read naturally."""
    n = max(1, n)
    if n == 1 or len(words) <= n:
        base = proportional_split(words, n)
        return base
    target = len(words) / n
    groups, i = [], 0
    for k in range(n):
        ideal = len(words) if k == n - 1 else round((k + 1) * target)
        best = ideal
        for cand in (ideal, ideal - 1, ideal + 1, ideal - 2, ideal + 2):
            if i < cand <= len(words) and words[cand - 1][-1:] in (",", ".", "!", "?"):
                best = cand
                break
        best = max(i + 1, min(best, len(words)))
        groups.append(words[i:best])
        i = best
    if i < len(words):
        groups[-1] += words[i:]
    return groups


def build_bilingual_short(orig_segments, trans_segments, lang, box_words,
                          max_dur, pause_gap):
    """Thai/original gets accurate per-box timing. English is placed by its OWN
    Whisper-translate timestamps (reliable at the ~sentence level): each English
    word is assigned to whichever original box is on screen at that word's spoken
    time. So the English matches the voice, not an even spread."""
    boxes = []
    for s in orig_segments:
        boxes += [b for b in boxes_from_segment(s, lang, box_words, max_dur, pause_gap)
                  if b["text"].strip()]
    if not boxes:
        return []
    # english words with a timestamp each (spread within each translate segment)
    ewt = []
    for t in sorted(trans_segments, key=lambda x: x["start"]):
        w = (t.get("text") or "").split()
        if not w:
            continue
        s, e = t["start"], t["end"]
        dur = max(0.001, e - s)
        for i, wd in enumerate(w):
            ewt.append((s + dur * ((i + 0.5) / len(w)), wd))
    ewt.sort(key=lambda x: x[0])
    # assign each English word to the box active at its time (start <= t < next.start)
    starts = [b["start"] for b in boxes]
    buckets = [[] for _ in boxes]
    for tw, wd in ewt:
        idx = bisect.bisect_right(starts, tw) - 1
        buckets[max(0, idx)].append(wd)
    # Where Whisper under-transcribed the Thai, one box can collect far more English
    # than fits. Paginate those over the box's own time span (Thai persists, English
    # pages through) so the translation stays readable and time-paced.
    out = []
    for b, g in zip(boxes, buckets):
        if len(g) <= box_words * 2:  # fits in ~2 lines — keep as one box
            b["en"] = " ".join(g)
            out.append(b)
            continue
        n = math.ceil(len(g) / box_words)
        span = max(0.001, b["end"] - b["start"])
        for k, part in enumerate(natural_split(g, n)):
            nb = dict(b)
            nb["start"] = b["start"] + span * (k / n)
            nb["end"] = b["start"] + span * ((k + 1) / n)
            nb["en"] = " ".join(part)
            out.append(nb)
    return out


def final_cleanup(cues, lang, mode):
    """Last pass on final timings: fold any flash-frame (<0.4s) or empty-English
    box into the previous one, so nothing flickers by or shows a bare line."""
    if not cues:
        return cues
    osep = "" if lang in NOSPACE_LANGS else " "
    out = [cues[0]]
    for c in cues[1:]:
        flash = (c["end"] - c["start"]) < 0.4
        empty_en = mode == "bilingual" and not c.get("en", "").strip()
        if flash or empty_en:
            prev = out[-1]
            merged = (prev["text"] + osep + c["text"]).strip()
            prev["text"] = space_latin(merged) if lang in NOSPACE_LANGS else merged
            prev["en"] = (prev.get("en", "") + " " + c.get("en", "")).strip()
            prev["end"] = c["end"]
        else:
            out.append(c)
    return out


def merge_short_cues(cues, lang, min_flash=0.35):
    """Fold away flash-frame cues (below min_flash seconds) by merging their text
    into the previous cue — a guard against any residual over-splitting."""
    osep = "" if lang in NOSPACE_LANGS else " "
    out = []
    for c in cues:
        if out and (c["end"] - c["start"]) < min_flash:
            prev = out[-1]
            prev["text"] = (prev["text"] + osep + c["text"]).strip()
            prev["end"] = c["end"]
            if c.get("en"):
                prev["en"] = ((prev.get("en", "") + " " + c["en"]).strip())
        else:
            out.append(c)
    return out


# ----------------------------------------------------------------------------
# timing enforcement
# ----------------------------------------------------------------------------
def enforce_timing(cues, min_dur, max_dur, min_gap, lead_out=0.0, audio_dur=None):
    """Gap-free timing: every caption stays on screen until the next one begins
    (minus min_gap), so the subtitle track has no empty holes. The last caption
    runs to the end of the audio."""
    for i, c in enumerate(cues):
        nxt = cues[i + 1] if i + 1 < len(cues) else None
        if nxt:
            c["end"] = max(c["start"] + 0.05, nxt["start"] - min_gap)
        else:
            tail = audio_dur if audio_dur else c["end"]
            c["end"] = max(c["start"] + 0.05, tail)
    return cues


# ----------------------------------------------------------------------------
# writers
# ----------------------------------------------------------------------------
def ts(seconds, sep=","):
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def cue_text(c, field):
    if field == "srt":  # bilingual stack (original + english) or plain original
        top = c["text"]
        return top + "\n" + c["en"] if c.get("en") else top
    return c.get(field, "")


def write_srt(cues, out_path, field="srt", bom=False):
    blocks = []
    for i, c in enumerate(cues, 1):
        body = cue_text(c, field).replace("\n", "\r\n")
        blocks.append(f"{i}\r\n{ts(c['start'])} --> {ts(c['end'])}\r\n{body}\r\n")
    data = "\r\n".join(blocks)  # blank line between cues (CRLF)
    enc = "utf-8-sig" if bom else "utf-8"
    with open(out_path, "w", encoding=enc, newline="") as f:
        f.write(data)


def write_vtt(cues, out_path, field="srt"):
    blocks = ["WEBVTT\r\n"]
    for c in cues:
        body = cue_text(c, field).replace("\n", "\r\n")
        blocks.append(f"{ts(c['start'], '.')} --> {ts(c['end'], '.')}\r\n{body}\r\n")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(blocks))


# ----------------------------------------------------------------------------
# sanity check
# ----------------------------------------------------------------------------
def sanity_check(cues, audio_dur, mode, expect_en=False):
    warn = []
    if not cues:
        return ["NO CAPTIONS produced — transcription may have failed."]
    last_end = cues[-1]["end"]
    coverage = last_end / audio_dur if audio_dur else 0
    if coverage < 0.5:
        warn.append(f"Captions cover only {coverage*100:.0f}% of {audio_dur:.1f}s audio "
                    f"(ends {last_end:.1f}s) — possible wrong language / early stop / silence.")
    if last_end > audio_dur + 1.0:
        warn.append(f"Last caption ({last_end:.1f}s) runs past audio end ({audio_dur:.1f}s).")
    if mode == "bilingual" and expect_en:
        missing = sum(1 for c in cues if not c.get("en"))
        if missing > len(cues) * 0.4:
            warn.append(f"{missing}/{len(cues)} captions have no English line — "
                        f"translation pass may have underperformed.")
    return warn


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Accurate SRT/VTT captions for any NLE.")
    p.add_argument("input")
    p.add_argument("--mode", choices=["bilingual", "mono", "dual"], default="bilingual")
    p.add_argument("--lang", default=None, help="source language (th/zh/en/...). Omit=auto")
    p.add_argument("--translate-to", default="en", help="translation target (whisper: en only)")
    p.add_argument("--model", default="large-v3")
    p.add_argument("--fast", action="store_true", help="use turbo model (draft speed)")
    p.add_argument("--words-per-line", type=int, default=5,
                   help="words per caption box (default 5). Lower = bigger text.")
    p.add_argument("--chars-per-line", type=int, default=None)
    p.add_argument("--max-lines", type=int, default=2)
    p.add_argument("--min-dur", type=float, default=1.0)
    p.add_argument("--max-dur", type=float, default=6.0)
    p.add_argument("--min-gap", type=float, default=80.0, help="milliseconds")
    p.add_argument("--lead-out", type=float, default=1.0,
                   help="extra seconds each caption lingers, capped at the next box "
                        "(default 1.0; never overlaps)")
    p.add_argument("--pause-gap", type=float, default=0.6)
    p.add_argument("--bom", action="store_true", help="write UTF-8 BOM (some Windows tools)")
    p.add_argument("--vtt", action="store_true", help="also emit a .vtt file")
    p.add_argument("--out", default=None)
    p.add_argument("--outdir", default=None)
    a = p.parse_args()

    if not os.path.isfile(a.input):
        eprint("Input file not found:", a.input); sys.exit(2)

    engine = detect_engine()
    size = "turbo" if a.fast else a.model
    min_gap_s = a.min_gap / 1000.0

    eprint(f"[1/5] Engine: {engine} | model: {size} | mode: {a.mode}")
    eprint(f"[2/5] Decoding audio: {os.path.basename(a.input)}")
    audio = load_audio(a.input)
    audio_dur = len(audio) / SR
    eprint(f"      {audio_dur:.1f}s @ {SR} Hz mono")

    eprint("[3/5] Transcribing" + (f" (lang={a.lang})" if a.lang else " (auto-detect)"))
    # word_timestamps makes Whisper DROP/collapse content (esp. Thai), which is the
    # root of alignment drift — so transcribe without it and time boxes from the
    # (reliable, short) segment boundaries instead.
    res = transcribe(audio, size, a.lang, engine, task="transcribe", want_words=False)
    lang = a.lang or res.get("language") or "en"
    eprint(f"      language: {lang}")

    # Each caption box holds this many WORDS (default 4). One short line per
    # language — Thai counts real words (pythainlp), English counts words too.
    box_words = a.words_per_line

    eprint("[4/5] Building cues" + (" + translation" if a.mode != "mono" else ""))
    if a.mode == "mono":
        cues = original_cues(res["segments"], lang, box_words, a.max_dur, a.pause_gap)
        cues = merge_short_cues(cues, lang)
    else:  # bilingual or dual — English chunked to match the boxes
        if lang != a.translate_to:
            tr = transcribe(audio, size, lang, engine, task="translate", want_words=False)
            cues = build_bilingual_short(res["segments"], tr["segments"], lang,
                                         box_words, a.max_dur, a.pause_gap)
            cues = merge_short_cues(cues, lang)
        else:
            eprint("      source already English — skipping translation pass")
            cues = original_cues(res["segments"], lang, box_words, a.max_dur, a.pause_gap)
            cues = merge_short_cues(cues, lang)
            for c in cues:
                c["en"] = ""
    cues = repair_orphans(cues, lang)
    if lang in NOSPACE_LANGS:  # space out embedded English words in Thai/CJK lines
        for c in cues:
            c["text"] = space_latin(c["text"])
    cues = enforce_timing(cues, a.min_dur, a.max_dur, min_gap_s, a.lead_out, audio_dur)
    cues = final_cleanup(cues, lang, a.mode)

    # ---- output paths ----
    base = os.path.splitext(os.path.basename(a.input))[0]
    out_dir = a.outdir or os.path.dirname(os.path.abspath(a.input))
    written = []
    if a.mode == "dual":
        p_orig = a.out or os.path.join(out_dir, f"{base}-sub-{lang}.srt")
        p_en = os.path.join(out_dir, f"{base}-sub-{a.translate_to}.srt")
        os.makedirs(os.path.dirname(os.path.abspath(p_orig)), exist_ok=True)
        write_srt(cues, p_orig, field="text", bom=a.bom); written.append(p_orig)
        write_srt(cues, p_en, field="en", bom=a.bom); written.append(p_en)
        if a.vtt:
            write_vtt(cues, os.path.splitext(p_orig)[0] + ".vtt", field="text")
    else:
        out_path = a.out or os.path.join(out_dir, f"{base}-sub.srt")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        write_srt(cues, out_path, field="srt", bom=a.bom); written.append(out_path)
        if a.vtt:
            write_vtt(cues, os.path.splitext(out_path)[0] + ".vtt", field="srt")

    eprint("[5/5] Sanity check")
    expect_en = a.mode == "bilingual" and lang != a.translate_to
    warns = sanity_check(cues, audio_dur, a.mode, expect_en)
    eprint((f"      {len(cues)} captions, covers 0.0s–"
            f"{cues[-1]['end']:.1f}s of {audio_dur:.1f}s") if cues else "      0 captions")
    if warns:
        eprint("      ⚠ FLAGS:")
        for w in warns:
            eprint("        -", w)
    else:
        eprint("      ✓ no issues flagged")

    for w in written:
        print(w)  # stdout = artifact path(s)


if __name__ == "__main__":
    main()
