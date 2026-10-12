"""Start a new clip: voiceover + whisper timestamps + build.py and composition skeletons.

  python kit/new_clip.py ess02-trick-21s --product ess02 --vo "03_Projects/ESS02-ทริกลึก_1/voiceover.wav" [--script script.txt]

Then: fill CLAUSES/sfx in clips/<id>/build.py (whisper spelling is printed below), design the
beats in compositions/<id>.html, run `python clips/<id>/build.py`, and `npx hyperframes check`.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent
OMNICUT = STUDIO.parent.parent

BUILD_TEMPLATE = '''"""Clip {cid}: captions + SFX on the real whisper timestamps.
Run: python clips/{cid}/build.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
# whisper spelling: {spelling}
CLAUSES = [
    # (False, [("hook word", "whisper spelling", "hookA")]),   # hook voiced by kinetic type
    # (True, [("ข้อความ", "ข้อความ", "cue1"), ("30W", "30W", "w30")]),
]


def sfx(c):
    return [  # (file in assets/shared/sfx, time, duration, volume)
        # ("pop.wav", c["hookA"], 0.15, 0.55),
    ]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop=None, gaps=[])  # gaps: [("cue", 0.8)] meme pauses
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id", help="<product>-<angle>-<len>, e.g. ess02-trick-21s")
    ap.add_argument("--product", required=True, help="product code under assets/")
    ap.add_argument("--vo", required=True, help="voiceover wav (absolute or relative to the Omnicut root)")
    ap.add_argument("--script", help="script text file, used as the whisper prompt")
    a = ap.parse_args()

    cid = a.clip_id
    clip_dir, asset_dir = STUDIO / "clips" / cid, STUDIO / "assets" / "clips" / cid
    comp = STUDIO / "compositions" / f"{cid}.html"
    if comp.exists():
        sys.exit(f"{comp} already exists")
    if not (STUDIO / "assets" / a.product / "footage.mp4").exists():
        sys.exit(f"product '{a.product}' has no footage — run kit/new_product.py first")
    vo = Path(a.vo) if Path(a.vo).is_absolute() else OMNICUT / a.vo
    clip_dir.mkdir(parents=True)
    asset_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(vo, asset_dir / "vo.wav")
    prompt = ""
    if a.script:
        sp = Path(a.script) if Path(a.script).is_absolute() else OMNICUT / a.script
        shutil.copy2(sp, clip_dir / "script.txt")
        prompt = sp.read_text(encoding="utf-8")

    from faster_whisper import WhisperModel  # system python has it; large-v3-turbo is cached
    model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", local_files_only=True)
    segs, _ = model.transcribe(str(asset_dir / "vo.wav"), language="th", word_timestamps=True, initial_prompt=prompt or None)
    words = []
    for s in segs:
        print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}")
        words += [{"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3)} for w in s.words]
    (clip_dir / "whisper_words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    spelling = "".join(w["w"] for w in words)
    duration = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                     str(asset_dir / "vo.wav")], capture_output=True, text=True).stdout)
    total = round(duration + 0.1, 2)
    (clip_dir / "vo_meta.json").write_text(json.dumps({"duration": duration}), encoding="utf-8")

    (clip_dir / "build.py").write_text(BUILD_TEMPLATE.format(cid=cid, spelling=spelling), encoding="utf-8")
    starter = (STUDIO / "kit" / "starter.html").read_text(encoding="utf-8")
    comp.write_text(starter.replace("{{CID}}", cid).replace("{{PRODUCT}}", a.product)
                    .replace("{{TOTAL}}", str(total)).replace("{{VO}}", str(round(duration, 2))), encoding="utf-8")
    print(f"\nclip '{cid}' started ({total}s). whisper spelling:\n{spelling}")


if __name__ == "__main__":
    main()
