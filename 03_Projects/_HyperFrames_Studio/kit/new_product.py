"""Add a product to the studio: graded footage + contact sheet (+ optional hero cutout).

  python kit/new_product.py ess02 "01_Raw/<folder>/<clip>.mov" [--hero-at 3.6]

Writes assets/<code>/footage.mp4 (1080x1920 30fps, channel LUT), assets/<code>/contact_sheet.jpg
(1 frame/sec, numbered — pick shot ranges from it), and with --hero-at a frame + rembg cutout in
assets/<code>/img/ for the "type behind the product" beat.
"""
import argparse
import subprocess
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent
OMNICUT = STUDIO.parent.parent
LUT = OMNICUT / "02_Assets" / "LUTs_ColorPresets" / "lut_tech_cool_contrast.cube"
VENV_PY = OMNICUT / ".venv" / "Scripts" / "python.exe"


def run(cmd):
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code", help="short product code, e.g. ess02, hat01")
    ap.add_argument("raw", help="raw footage path (absolute or relative to the Omnicut root)")
    ap.add_argument("--hero-at", type=float, help="second of the footage to freeze + cut out")
    a = ap.parse_args()

    raw = Path(a.raw)
    if not raw.is_absolute():
        raw = OMNICUT / raw
    if not raw.exists():
        sys.exit(f"raw footage not found: {raw}")
    out = STUDIO / "assets" / a.code.lower()
    (out / "img").mkdir(parents=True, exist_ok=True)

    footage = out / "footage.mp4"
    lut = LUT.relative_to(OMNICUT).as_posix()  # ffmpeg filter args choke on the drive colon
    run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-an",
         "-vf", f"scale=1080:1920:flags=lanczos,lut3d={lut},fps=30,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-movflags", "+faststart", str(footage)])
    sheet = out / "contact_sheet.jpg"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(footage), "-vf",
         "fps=1,scale=180:-1,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='%{eif\\:n\\:d}':x=6:y=6:"
         "fontsize=28:fontcolor=yellow:box=1:boxcolor=black,tile=10x8", "-frames:v", "1", str(sheet)])

    if a.hero_at is not None:
        frame = out / "img" / "hero_frame.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.hero_at), "-i", str(footage), "-frames:v", "1", str(frame)])
        code = ("from rembg import remove, new_session; from PIL import Image; import sys; "
                "remove(Image.open(sys.argv[1]), session=new_session('u2net'), post_process_mask=True).save(sys.argv[2])")
        run([str(VENV_PY), "-c", code, str(frame), str(out / "img" / "hero_cutout.png")])

    print(f"\nproduct '{a.code}' ready: {out.relative_to(STUDIO)}")
    print(f"open {sheet.relative_to(STUDIO)} to map shots (frame number = second)")


if __name__ == "__main__":
    import os
    os.chdir(OMNICUT)
    main()
