"""Shared timing pipeline for every clip in the studio.

A clip's clips/<id>/build.py declares its CLAUSES and SFX and calls build().
build() aligns them against the real whisper timestamps (never hand-estimated), then
  - writes assets/clips/<id>/timing.js   (window.TIMING = {cues, captions})
  - injects karaoke captions and SFX <audio> into compositions/<id>.html
  - regenerates the studio index.html (clip library)
"""
import json
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent


class Aligner:
    """Finds phrases (as whisper spelled them) in the char-level transcript, in order."""

    def __init__(self, path):
        self.chars, self.starts, self.ends = [], [], []
        for t in json.loads(Path(path).read_text(encoding="utf-8")):
            for ch in t["w"].replace(" ", ""):
                self.chars.append(ch)
                self.starts.append(t["s"])
                self.ends.append(t["e"])
        self.text = "".join(self.chars)
        self.cursor = 0

    def find(self, spoken):
        key = spoken.replace(" ", "")
        i = self.text.find(key, self.cursor)
        if i < 0:
            raise ValueError(f"{spoken!r} not found after char {self.cursor}: …{self.text[self.cursor:self.cursor + 40]}")
        last = i + len(key) - 1
        self.cursor = last + 1
        self.last_idx = last
        return round(self.starts[i], 3), round(self.ends[last], 3)


def needs_space(prev, nxt):
    """Thai runs on without spaces; keep one around Latin/digits and after the ๆ repeat mark."""
    return prev.endswith("ๆ") or any(c.isascii() for c in prev[-1] + nxt[0])


def build(clip_dir, clauses, sfx, caption_stop=None, gaps=()):
    """clauses: [(show_caption, [(display, whisper_spelling, cue_name_or_None), ...]), ...]
    sfx: callable(cues) -> [(file_in_assets/shared/sfx, time, duration, volume), ...]
    caption_stop: cue name where the caption bar ends (kinetic CTA takes over), or None.
    gaps: [(cue_name, seconds), ...] — "meme pauses": silence inserted after that word; the
          voiceover is split into <audio> segments and every later cue shifts by the pause."""
    clip_dir = Path(clip_dir)
    cid = clip_dir.name
    al = Aligner(clip_dir / "whisper_words.json")
    cues, captions, next_char = {}, [], {}
    for show, words in clauses:
        out = []
        for display, spoken, cue in words:
            s, e = al.find(spoken)
            out.append({"w": display, "s": s, "e": e})
            if cue:
                next_char[cue] = al.last_idx + 1
                cues[cue] = s
                cues[cue + "_end"] = e
        if show:
            for i in range(1, len(out)):
                out[i]["sp"] = needs_space(out[i - 1]["w"], out[i]["w"])
            captions.append(out)
    cues["voice_end"] = round(al.ends[-1], 3)

    # meme pauses: split point = midway between the cue's last syllable and the next one
    splits = []
    for name, dur in gaps:
        end = cues[name + "_end"]
        i = next_char[name]
        nxt = al.starts[i] if i < len(al.starts) else end + 0.2
        splits.append((round((end + max(nxt, end)) / 2, 3), dur))
    splits.sort()

    def shift(t):
        return round(t + sum(d for at, d in splits if at <= t), 3)

    cues = {k: shift(v) for k, v in cues.items()}
    for words in captions:
        for w in words:
            w["s"], w["e"] = shift(w["s"]), shift(w["e"])
    vo_len = float(json.loads((clip_dir / "vo_meta.json").read_text())["duration"]) if (clip_dir / "vo_meta.json").exists() else None
    bounds = [0.0] + [at for at, _ in splits] + [vo_len or cues["voice_end"] + 0.3]
    vo_rows = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        vo_rows.append(
            f'      <audio id="vo{i}" src="assets/clips/{cid}/vo.wav" data-start="{shift(a) if i else 0}" '
            f'data-media-start="{a}" data-duration="{round(b - a, 3)}" data-track-index="10" data-volume="1"></audio>'
        )
    cues["total"] = round(shift(bounds[-1]) + 0.15, 2)

    js = STUDIO / "assets" / "clips" / cid / "timing.js"
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_text("window.TIMING = " + json.dumps({"cues": cues, "captions": captions}, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")

    html = STUDIO / "compositions" / f"{cid}.html"
    stop = cues[caption_stop] if caption_stop else float("inf")
    shown = [c for c in captions if c[0]["s"] < stop]
    rows = []
    for i, words in enumerate(shown):
        start = words[0]["s"]
        if i + 1 < len(shown):
            end = min(shown[i + 1][0]["s"], words[-1]["e"] + 0.5)
        else:
            end = stop if caption_stop else words[-1]["e"] + 0.5
        spans = "".join((" " if w.get("sp") else "") + f'<span class="w" data-s="{w["s"]}">{w["w"]}</span>' for w in words)
        rows.append(
            f'      <div class="cap clip" id="cap{i:02d}" data-start="{start}" data-duration="{round(end - start, 3)}" '
            f'data-track-index="6"><div class="cap-in">{spans}</div></div>'
        )

    sfx_rows, lanes = [], []  # overlapping hits go to the next free audio lane (track 12, 13, ...)
    for i, (f, t, d, v) in enumerate(sorted(sfx(cues), key=lambda x: x[1])):
        lane = next((k for k, end in enumerate(lanes) if end <= t), len(lanes))
        if lane == len(lanes):
            lanes.append(0.0)
        lanes[lane] = t + d
        sfx_rows.append(
            f'      <audio id="sfx{i:02d}" src="assets/shared/sfx/{f}" data-start="{round(t, 3)}" data-duration="{d}" '
            f'data-track-index="{12 + lane}" data-volume="{v}"></audio>'
        )

    text = html.read_text(encoding="utf-8")
    blocks = [("CAPTIONS", rows), ("SFX", sfx_rows)]
    if "<!-- VO:BEGIN -->" in text:
        blocks.append(("VO", vo_rows))
    for tag, body in blocks:
        a, b = f"<!-- {tag}:BEGIN -->", f"<!-- {tag}:END -->"
        head, rest = text.split(a, 1)
        _, tail = rest.split(b, 1)
        text = head + a + "\n" + "\n".join(body) + "\n      " + b + tail
    html.write_text(text, encoding="utf-8")
    write_index()
    print(f"{cid}: {len(cues) // 2} cues, {len(rows)} captions, {len(sfx_rows)} sfx, total {cues['total']}s"
          + (f", {len(splits)} meme pauses" if splits else ""))
    return cues


def write_index():
    """Clip library shown as the studio root: one line per composition."""
    clips = sorted(p.stem for p in (STUDIO / "compositions").glob("*.html"))
    items = "\n".join(f'          <p class="clip-row">{c}</p>' for c in clips)
    template = (STUDIO / "kit" / "index.template.html").read_text(encoding="utf-8")
    (STUDIO / "index.html").write_text(template.replace("{{CLIPS}}", items).replace("{{COUNT}}", str(len(clips))), encoding="utf-8")
