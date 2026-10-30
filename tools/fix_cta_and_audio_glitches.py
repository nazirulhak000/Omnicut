"""Script to fix CTA font-size overflow and clean audio glitches for all hoy01 clips.
"""
from pathlib import Path
import sys
import wave
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.clean_all_inter_turn_audio_glitches import clean_isolated_bursts_in_vo
COMPS = ROOT / "03_Projects" / "_HyperFrames_Studio" / "compositions"
CLIPS = ROOT / "03_Projects" / "_HyperFrames_Studio" / "clips"
ASSETS = ROOT / "03_Projects" / "_HyperFrames_Studio" / "assets" / "clips"

def update_html_files():
    old_cta_1 = '      #cta-1 {\n        position: absolute;\n        top: 230px;\n        font-size: 108px;\n        line-height: 1.15;\n      }'
    new_cta_1 = '      #cta-1 {\n        position: absolute;\n        top: 230px;\n        font-size: 84px;\n        line-height: 1.15;\n        max-width: 960px;\n        margin: 0 auto;\n        left: 60px;\n        right: 60px;\n        width: 960px;\n      }'

    old_cta_model = '      #cta-model {\n        position: absolute;\n        top: 385px;\n        font-family: "Anuphan", sans-serif;\n        font-weight: 700;\n        font-size: 62px;\n        color: #d90429;\n      }'
    new_cta_model = '      #cta-model {\n        position: absolute;\n        top: 365px;\n        font-family: "Anuphan", sans-serif;\n        font-weight: 700;\n        font-size: 56px;\n        color: #d90429;\n        max-width: 960px;\n        margin: 0 auto;\n        left: 60px;\n        right: 60px;\n        width: 960px;\n      }'

    old_spec_css = '      .spec-row {\n        display: flex;\n        gap: 14px;\n      }\n      .spec-tag {\n        font-family: "Anuphan", sans-serif;\n        font-weight: 700;\n        font-size: 30px;\n        background: #fff;\n        border: 3px solid var(--ink);\n        padding: 6px 20px;\n        border-radius: 18px;\n        box-shadow: 3px 5px 0 var(--ink);\n        color: #111111;\n      }'
    new_spec_css = '      .spec-row {\n        display: flex;\n        flex-wrap: wrap;\n        justify-content: center;\n        max-width: 960px;\n        gap: 10px;\n        margin: 0 auto;\n      }\n      .spec-tag {\n        font-family: "Anuphan", sans-serif;\n        font-weight: 700;\n        font-size: 26px;\n        background: #fff;\n        border: 3px solid var(--ink);\n        padding: 6px 16px;\n        border-radius: 18px;\n        box-shadow: 3px 5px 0 var(--ink);\n        color: #111111;\n        white-space: nowrap;\n      }'

    count = 0
    for f in list(COMPS.glob("hoy01-pov-*.html")) + list(CLIPS.glob("hoy01-pov-*/index.html")):
        txt = f.read_text(encoding="utf-8")
        orig = txt
        if old_cta_1 in txt:
            txt = txt.replace(old_cta_1, new_cta_1)
        if old_cta_model in txt:
            txt = txt.replace(old_cta_model, new_cta_model)
        if old_spec_css in txt:
            txt = txt.replace(old_spec_css, new_spec_css)
        txt = txt.replace('data-track-index="11" data-volume="0.10"', 'data-track-index="11" data-volume="0.05"')
        if txt != orig:
            f.write_text(txt, encoding="utf-8")
            count += 1
            print(f"  [Updated CSS] {f.name} in {f.parent.name}")
    print(f"Updated {count} HTML files successfully.")

def clean_all_audio():
    for d in sorted(ASSETS.glob("hoy01-pov-*")):
        wav_path = d / "vo.wav"
        if not wav_path.exists():
            continue
        with wave.open(str(wav_path), "rb") as wf:
            sr = wf.getframerate()
            ch = wf.getnchannels()
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        cleaned, log = clean_isolated_bursts_in_vo(pcm, sr, ch)
        if log:
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(ch)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(cleaned.tobytes())
            print(f"  [Cleaned Audio] {d.name}: removed {len(log)} glitches")
        else:
            print(f"  [Audio Clean] {d.name}: zero glitches found")

if __name__ == "__main__":
    print("=" * 60)
    print("1. Updating HTML layout to eliminate text overflow & set BGM 0.05")
    update_html_files()
    print("\n2. Sanitizing audio glitches in all existing clips")
    clean_all_audio()
    print("=" * 60)
