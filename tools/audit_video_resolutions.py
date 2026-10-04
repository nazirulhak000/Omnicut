import argparse
import subprocess
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = PROJECT_ROOT / ".tmp" / "gadget_products"


def audit_video_resolutions(base_dir: Path = None):
    if base_dir is None:
        base_dir = DEFAULT_BASE

    results = []

    if not base_dir.exists():
        print(f"[INFO] Directory does not exist: {base_dir}")
        return results

    for p in sorted(base_dir.glob("*")):
        if not p.is_dir():
            continue
        vid = p / "video_clean_1080p.mp4"
        if not vid.exists():
            results.append((p.name, "NO VIDEO", 0, 0))
            continue
        cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json "{vid}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        try:
            data = json.loads(res.stdout)
            s = data["streams"][0]
            w, h = s["width"], s["height"]
            is_fhd = (w >= 1920 or h >= 1080)
            status = "FHD" if is_fhd else f"LOW_RES ({w}x{h})"
            results.append((p.name, status, w, h))
        except Exception as e:
            results.append((p.name, f"ERROR {e}", 0, 0))

    print(f"{'PRODUCT':<45} | {'STATUS':<15} | {'RESOLUTION'}")
    print("-" * 75)
    for name, status, w, h in results:
        print(f"{name:<45} | {status:<15} | {w}x{h}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Audit video resolutions in product directory")
    parser.add_argument("--base-dir", type=str, default=None, help="Base product directory")
    args = parser.parse_args()

    base = Path(args.base_dir) if args.base_dir else DEFAULT_BASE
    audit_video_resolutions(base)


if __name__ == '__main__':
    main()
