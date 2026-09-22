"""Offline live probe for the installed rembg model and FFmpeg compositor.

This is intentionally not collected by pytest because model weights are an
environment prerequisite. It writes only below ``.tmp`` and removes every
generated file before returning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from scripts.background_isolation_worker import BackgroundIsolationWorker


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "subprocess failed")


def run_probe(source: Path, *, at_seconds: float = 1.0, model: str = "u2net") -> dict:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise FileNotFoundError(source)
    source_hash = _sha256(source)
    temp_root = Path(".tmp").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="bg-cutout-live-", dir=temp_root) as temporary:
        work = Path(temporary)
        frame = work / "source.png"
        foreground = work / "foreground.png"
        background = work / "background.png"
        preview = work / "preview.png"
        rendered = work / "rendered.png"

        _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-ss", f"{max(0.0, at_seconds):.3f}", "-i", str(source),
            "-frames:v", "1", "-vf", "scale=256:456:force_original_aspect_ratio=decrease,"
            "pad=256:456:(ow-iw)/2:(oh-ih)/2:color=black", str(frame),
        ])

        result = BackgroundIsolationWorker().process(
            frame,
            foreground,
            {
                "enabled": True,
                "mode": "cutout",
                "engine": "rembg",
                "model": model,
                "quality": "balanced",
                "fallback": "spotlight",
            },
        )
        if not result.get("ok") or result.get("status") != "ready":
            raise RuntimeError(result.get("message") or "rembg probe failed")

        with Image.open(foreground) as image:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")
            alpha_extrema = alpha.getextrema()
            if alpha_extrema[0] == alpha_extrema[1]:
                raise RuntimeError(f"cutout alpha is uniform: {alpha_extrema}")
            bg = Image.new("RGBA", rgba.size, (11, 18, 32, 255))
            bg.save(background)
            Image.alpha_composite(bg, rgba).convert("RGB").save(preview)

        # This is the same alpha split/merge/overlay order used by
        # VideoEditor before transitions and text overlays.
        graph = (
            "[1:v]format=rgba,split=2[fg_rgb][fg_alpha_source];"
            "[fg_rgb]format=rgb24[fg_rgb_rgb];"
            "[fg_alpha_source]alphaextract[fg_alpha];"
            "[fg_rgb_rgb][fg_alpha]alphamerge[subject];"
            "[0:v][subject]overlay=eof_action=pass:format=auto[out]"
        )
        _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", str(background), "-i", str(foreground),
            "-filter_complex", graph, "-map", "[out]", "-frames:v", "1", rendered,
        ])

        with Image.open(preview) as expected_image, Image.open(rendered) as actual_image:
            expected = expected_image.convert("RGB")
            actual = actual_image.convert("RGB")
            difference = ImageChops.difference(expected, actual)
            mean_channels = ImageStat.Stat(difference).mean
            nmae = sum(mean_channels) / (3 * 255)
            max_delta = max(channel[1] for channel in difference.getextrema())

        if nmae > 0.002 or max_delta > 4:
            raise RuntimeError(f"preview/render composite drift: nmae={nmae}, max_delta={max_delta}")
        if _sha256(source) != source_hash:
            raise RuntimeError("source media changed during the probe")

        return {
            "ok": True,
            "model": model,
            "alpha_extrema": list(alpha_extrema),
            "preview_render_nmae": nmae,
            "preview_render_max_delta": max_delta,
            "source_unchanged": True,
            "temporary_artifacts_cleaned": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--at", type=float, default=1.0, dest="at_seconds")
    parser.add_argument("--model", choices=("u2netp", "u2net", "isnet-general-use"), default="u2net")
    args = parser.parse_args()
    print(json.dumps(run_probe(args.source, at_seconds=args.at_seconds, model=args.model), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
