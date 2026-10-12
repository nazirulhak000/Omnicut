"""Clip ess02-hype-25s — style "Velocity Hype": no voice, every cut and word lands on the phonk beat.

Beat grid comes from `npx hyperframes beats` (beats.json, strong beats only, 135 BPM).
Run: python clips/ess02-hype-25s/make.py  → writes compositions/ess02-hype-25s.html
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent.parent
CID = HERE.name
BEATS = [b["time"] for b in json.loads((HERE / "beats.json").read_text())["beats"] if b["strength"] > 0.55]
B = lambda n: round(BEATS[n], 3)  # noqa: E731  strong beat n (0.445s apart, 4 per bar)
TOTAL = round(B(56) + 0.1, 2)

# (start_beat, end_beat, src_second, playback_rate, zoom_from, zoom_to, treatment)
SHOTS = [
    (0, 4, 33.0, 0.5, 1.3, 1.15, "dark"),     # intro: logo side, slow-mo
    (4, 8, 36.0, 0.5, 1.25, 1.12, "dark"),
    (8, 9, 7.0, 1, 1.45, 1.3, ""),           # build: a cut on every beat
    (9, 10, 24.0, 1, 1.5, 1.35, ""),
    (10, 11, 11.2, 1, 1.45, 1.3, ""),
    (11, 12, 26.5, 1, 1.5, 1.35, ""),
    (12, 13, 33.5, 1, 1.4, 1.25, ""),
    (13, 14, 28.5, 1, 1.5, 1.35, ""),
    (14, 15, 13.5, 1, 1.45, 1.3, ""),
    (15, 16, 30.0, 1, 1.5, 1.35, ""),
    (16, 24, 1.2, 0.35, 1.0, 1.18, ""),        # drop: the reveal in slow motion
    (24, 26, 54.0, 1, 1.15, 1.25, ""),         # features: two cuts per bar
    (26, 28, 55.8, 1, 1.25, 1.12, ""),
    (28, 30, 42.3, 1, 1.12, 1.22, ""),
    (30, 32, 45.4, 1, 1.22, 1.1, ""),
    (32, 34, 46.5, 1, 1.15, 1.25, ""),
    (34, 36, 44.0, 1, 1.25, 1.12, ""),
    (36, 38, 16.0, 1, 1.2, 1.3, ""),
    (38, 40, 20.6, 1, 1.3, 1.18, ""),
    (40, 44, 7.0, 2.0, 1.2, 1.35, ""),         # speed ramp: rushing...
    (44, 48, 53.2, 0.4, 1.35, 1.15, ""),       # ...then hanging in slow-mo
    (48, 56, 55.0, 0.45, 1.1, 1.2, ""),        # outro
]

# (beat, text, css class, entrance) — words punch on the beat
WORDS = [
    (1, "30W", "w-huge volt", "slam"), (3, "USB-C", "w-mid", "slam"), (5, "PD", "w-huge outline", "slam"), (7, "ESSAGER", "w-big", "stretch"),
    (8, "SMALL", "w-big", "cut"), (10, "FAST", "w-big volt", "cut"), (12, "SAFE", "w-big", "cut"), (14, "30W", "w-huge volt", "cut"),
    (16, "ESSAGER", "w-big", "stretch"), (18, "PD 30W", "w-mid volt", "slam"),
    (24, "เล็กแค่ฝ่ามือ", "w-th", "slam"), (28, "30 นาที 50%", "w-th volt", "slam"), (32, "iPhone 15 | 16", "w-th", "slam"),
    (36, "ป้องกันไฟเกิน", "w-th volt", "slam"), (40, "ไม่ต้องรอ", "w-th", "slam"),
    (48, "ESSAGER", "w-big", "stretch"), (50, "PD 30W", "w-mid volt", "slam"), (52, "ตะกร้าเหลือง", "w-th volt", "slam"), (54, "ซ้ายล่าง", "w-th", "slam"),
]
FLASH_BEATS = [8, 12, 16, 24, 28, 32, 36, 40, 44, 48]   # white hits on section downbeats
SHAKE_BEATS = [16, 44]                                  # the two drops


def main():
    cams, shots_js = [], []
    for i, (b0, b1, src, rate, z0, z1, treat) in enumerate(SHOTS):
        t0, t1 = B(b0), B(b1) if b1 < len(BEATS) else TOTAL
        if b1 == 56:
            t1 = TOTAL
        dur = round(t1 - t0, 3)
        rate_attr = f' data-playback-rate="{rate}"' if rate != 1 else ""
        cls = "cam dark" if treat == "dark" else "cam"
        cams.append(
            f'      <div class="{cls}" id="c{i}"><div class="kb" id="k{i}" data-layout-allow-overflow><video id="v{i}" class="clip" '
            f'src="assets/ess02/footage.mp4" muted playsinline data-start="{t0}" data-duration="{dur}" data-media-start="{src}"{rate_attr} '
            f'data-track-index="0"></video></div></div>'
        )
        shots_js.append(f"[{t0}, {dur}, {z0}, {z1}]")
    words_html, words_js = [], []
    for j, (b, txt, cls, ent) in enumerate(WORDS):
        t0 = B(b)
        nxt = WORDS[j + 1][0] if j + 1 < len(WORDS) else 56
        t1 = min(B(nxt) if nxt < len(BEATS) else TOTAL, t0 + 0.445 * 2)
        words_html.append(
            f'      <div class="beat clip" id="wd{j}" data-start="{t0}" data-duration="{round(t1 - t0, 3)}" data-track-index="3">'
            f'<div class="t center w {cls}" id="wt{j}">{txt}</div></div>'
        )
        words_js.append(f'["#wt{j}", {t0}, "{ent}"]')
    sfx = [("boom.wav", B(16), 0.8, 0.55), ("boom.wav", B(44), 0.8, 0.5), ("whoosh.mp3", B(40) - 0.1, 0.5, 0.45),
           ("cinematic_boom.mp3", B(48), 1.2, 0.4), ("cash_register.mp3", B(52) + 0.1, 1.0, 0.45)]
    sfx_html = [
        f'      <audio id="s{k:02d}" src="assets/shared/sfx/{f}" data-start="{round(t, 3)}" data-duration="{d}" data-track-index="{12 + k % 2}" data-volume="{v}"></audio>'
        for k, (f, t, d, v) in enumerate(sfx)
    ]
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    html = (tpl.replace("{{TOTAL}}", str(TOTAL)).replace("{{CAMS}}", "\n".join(cams)).replace("{{WORDS}}", "\n".join(words_html))
            .replace("{{SFX}}", "\n".join(sfx_html)).replace("{{SHOTS}}", ", ".join(shots_js)).replace("{{WORDSJS}}", ", ".join(words_js))
            .replace("{{FLASH}}", json.dumps([B(b) for b in FLASH_BEATS])).replace("{{SHAKE}}", json.dumps([B(b) for b in SHAKE_BEATS]))
            .replace("{{BEATS}}", json.dumps([B(n) for n in range(57)])).replace("{{FADE}}", str(round(TOTAL - 1.2, 2))))
    (STUDIO / "compositions" / f"{CID}.html").write_text(html, encoding="utf-8")
    print(f"{CID}: {len(SHOTS)} shots, {len(WORDS)} words, total {TOTAL}s")


if __name__ == "__main__":
    main()
