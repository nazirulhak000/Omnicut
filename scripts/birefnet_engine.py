"""BiRefNet High-Precision Matting & Sticker Engine for Omnicut.

Provides high-resolution (1024x1024) foreground matting using BiRefNet
(Bilateral Reference Network) and IS-Net/U2Net models with NVIDIA RTX 4060
GPU acceleration (CUDAExecutionProvider) and seamless CPU fallback.

Also implements automated white die-cut sticker generation (12-16px border)
with soft ambient drop shadow according to .agents/rules/sticker_generation.md.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CUTOUT_VENV_PYTHON = PROJECT_ROOT / "tools" / "cutout_runtime" / ".venv" / "Scripts" / "python.exe"
TORCH_LIB_DIR = PROJECT_ROOT / "tools" / "cutout_runtime" / ".venv" / "lib" / "site-packages" / "torch" / "lib"

SUPPORTED_MODELS = (
    "birefnet-general",
    "birefnet-general-lite",
    "birefnet-dis",
    "isnet-general-use",
    "u2net",
    "u2netp",
)
DEFAULT_MODEL = "birefnet-general"


def _setup_cuda_dll_directory() -> bool:
    """Register torch/lib CUDA and cuDNN DLLs into Windows DLL search path."""
    if sys.platform != "win32":
        return True

    found = False
    candidates = [
        TORCH_LIB_DIR,
        PROJECT_ROOT / ".venv" / "lib" / "site-packages" / "torch" / "lib",
    ]
    for cand in candidates:
        if cand.is_dir() and (cand / "cublasLt64_12.dll").exists():
            cand_str = str(cand.resolve())
            try:
                os.add_dll_directory(cand_str)
                found = True
            except (AttributeError, OSError):
                pass
            if cand_str not in os.environ.get("PATH", ""):
                os.environ["PATH"] = cand_str + os.pathsep + os.environ.get("PATH", "")
            found = True
            break
    return found


def _has_cuda_provider() -> bool:
    """Check if onnxruntime is available with CUDAExecutionProvider."""
    try:
        _setup_cuda_dll_directory()
        import onnxruntime as ort
        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


class BiRefNetEngine:
    """High-precision matting and sticker engine with GPU acceleration."""

    _shared_sessions: dict[str, Any] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        default_model: str = DEFAULT_MODEL,
        prefer_gpu: bool = True,
        gpu_device_id: int = 0,
        gpu_mem_limit: int = 0,
    ) -> None:
        self.default_model = default_model if default_model in SUPPORTED_MODELS else DEFAULT_MODEL
        self.prefer_gpu = prefer_gpu
        self.gpu_device_id = gpu_device_id
        self.gpu_mem_limit = gpu_mem_limit
        self._cuda_available: bool | None = None

    @property
    def is_cuda_available(self) -> bool:
        if self._cuda_available is None:
            self._cuda_available = _has_cuda_provider()
        return self._cuda_available

    def _get_provider_spec(self) -> list[Any]:
        """Construct safe ONNX Runtime execution provider list."""
        if not self.prefer_gpu or not self.is_cuda_available:
            return ["CPUExecutionProvider"]

        cuda_options = {
            "device_id": self.gpu_device_id,
            "cudnn_conv_algo_search": "DEFAULT",
            "do_copy_in_default_stream": True,
        }
        if self.gpu_mem_limit and self.gpu_mem_limit > 0:
            cuda_options["gpu_mem_limit"] = self.gpu_mem_limit

        return [("CUDAExecutionProvider", cuda_options), "CPUExecutionProvider"]

    def _get_rembg_session(self, model_name: str) -> Any:
        """Get or create cached rembg session with CUDA acceleration."""
        _setup_cuda_dll_directory()
        import rembg

        cache_key = f"{model_name}:{self.prefer_gpu}:{self.gpu_device_id}"
        with self._lock:
            if cache_key in self._shared_sessions:
                return self._shared_sessions[cache_key]

            providers = self._get_provider_spec()
            try:
                session = rembg.new_session(model_name, providers=providers)
            except Exception as exc:
                # If CUDA fails (e.g. out of memory), gracefully fallback to CPU
                if "CUDA" in str(exc) or "cuda" in str(exc).lower():
                    print(f"[BiRefNetEngine] CUDA initialization failed ({exc}); falling back to CPU.")
                    session = rembg.new_session(model_name, providers=["CPUExecutionProvider"])
                else:
                    raise

            self._shared_sessions[cache_key] = session
            return session

    def remove_background(
        self,
        image: Image.Image | Path | str,
        model_name: str | None = None,
        alpha_matting: bool = False,
        alpha_matting_foreground_threshold: int = 240,
        alpha_matting_background_threshold: int = 10,
        alpha_matting_erode_size: int = 10,
        return_mask: bool = False,
    ) -> Image.Image:
        """Remove background from an image using BiRefNet or configured model.

        Parameters:
            image: PIL Image or path to image file.
            model_name: Model identifier (defaults to self.default_model).
            alpha_matting: Whether to refine boundaries with pymatting.
            return_mask: If True, returns single-channel 'L' mask instead of RGBA cutout.

        Returns:
            Cutout PIL.Image in 'RGBA' mode (or 'L' mode if return_mask is True).
        """
        model = model_name or self.default_model
        if model not in SUPPORTED_MODELS:
            model = self.default_model

        # Check if we should delegate to cutout_runtime venv when main venv has no CUDA
        if self.prefer_gpu and not self.is_cuda_available and CUTOUT_VENV_PYTHON.is_file():
            # Delegate to cutout_runtime subprocess for GPU speed
            return self._remove_background_via_subprocess(
                image,
                model_name=model,
                alpha_matting=alpha_matting,
                return_mask=return_mask,
            )

        # In-process execution
        if isinstance(image, (str, Path)):
            input_img = Image.open(image).convert("RGBA")
        else:
            input_img = image.convert("RGBA")

        session = self._get_rembg_session(model)
        import rembg

        result = rembg.remove(
            input_img,
            session=session,
            only_mask=return_mask,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
        )

        return result

    def _remove_background_via_subprocess(
        self,
        image: Image.Image | Path | str,
        model_name: str,
        alpha_matting: bool,
        return_mask: bool,
    ) -> Image.Image:
        """Execute background removal in cutout_runtime Python environment with CUDA."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
            tmp_in_path = Path(tmp_in.name)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_out:
            tmp_out_path = Path(tmp_out.name)

        try:
            if isinstance(image, (str, Path)):
                img = Image.open(image).convert("RGBA")
            else:
                img = image.convert("RGBA")
            img.save(tmp_in_path, format="PNG")

            cmd = [
                str(CUTOUT_VENV_PYTHON),
                str(Path(__file__).resolve()),
                "--input", str(tmp_in_path),
                "--output", str(tmp_out_path),
                "--model", model_name,
            ]
            if return_mask:
                cmd.append("--only-mask")
            if alpha_matting:
                cmd.append("--alpha-matting")

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(PROJECT_ROOT),
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Subprocess background removal failed (code {proc.returncode}):\n"
                    f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
                )

            with Image.open(tmp_out_path) as out_img:
                return out_img.copy()
        finally:
            if tmp_in_path.exists():
                try:
                    tmp_in_path.unlink()
                except OSError:
                    pass
            if tmp_out_path.exists():
                try:
                    tmp_out_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def create_diecut_sticker(
        image: Image.Image,
        border_width: int = 14,
        border_color: tuple[int, int, int, int] = (255, 255, 255, 255),
        shadow_blur: int = 16,
        shadow_offset: tuple[int, int] = (0, 10),
        shadow_opacity: int = 140,
        padding: int = 32,
    ) -> Image.Image:
        """Create a premium 3D die-cut sticker with a clean white contour and soft drop shadow.

        Parameters:
            image: Foreground subject image in RGBA format (with clean transparent background).
            border_width: Width of the solid white die-cut stroke in pixels (default 14px, rule 12-16px).
            border_color: RGBA color of the die-cut border (default pure white #FFFFFF).
            shadow_blur: Gaussian blur radius for the soft ambient shadow.
            shadow_offset: (x, y) pixel offset for the drop shadow.
            shadow_opacity: Alpha opacity (0-255) for the ambient drop shadow.
            padding: Safety padding in pixels around the image to prevent edge clipping.

        Returns:
            Composite RGBA sticker image.
        """
        src = image.convert("RGBA")
        w, h = src.size

        # Create expanded canvas to fit border, shadow, and padding
        ext = max(border_width, shadow_blur) + max(abs(shadow_offset[0]), abs(shadow_offset[1])) + padding
        new_w, new_h = w + ext * 2, h + ext * 2
        ox, oy = ext, ext

        # Extract source alpha channel
        src_alpha = src.split()[3]

        # 1. Place source alpha into extended canvas
        padded_alpha = Image.new("L", (new_w, new_h), 0)
        padded_alpha.paste(src_alpha, (ox, oy))

        # 2. Morphological dilation for the outer die-cut border
        # Using MaxFilter creates a smooth outer contour
        filter_size = max(3, border_width * 2 + 1)
        dilated_alpha = padded_alpha.filter(ImageFilter.MaxFilter(filter_size))

        # Apply slight smoothing to eliminate pixel stepping on curved contours
        dilated_alpha = dilated_alpha.filter(ImageFilter.GaussianBlur(1.0))
        # Threshold slightly to keep crisp die-cut outer edge
        dilated_alpha = dilated_alpha.point(lambda p: 255 if p > 80 else int(p * 255 / 80))

        # 3. Create ambient drop shadow layer
        shadow_alpha = dilated_alpha.filter(ImageFilter.GaussianBlur(shadow_blur))
        # Scale shadow alpha by shadow_opacity
        scale = shadow_opacity / 255.0
        shadow_alpha = shadow_alpha.point(lambda p: int(p * scale))

        shadow_layer = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        shadow_color_layer = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 255))
        shadow_layer.paste(shadow_color_layer, shadow_offset, shadow_alpha)

        # 4. Create die-cut white border layer
        border_layer = Image.new("RGBA", (new_w, new_h), border_color)
        border_layer.putalpha(dilated_alpha)

        # 5. Composite: Shadow -> Border -> Original Foreground
        final_canvas = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        final_canvas.paste(shadow_layer, (0, 0), shadow_layer)
        final_canvas.paste(border_layer, (0, 0), border_layer)
        final_canvas.paste(src, (ox, oy), src)

        # 6. Auto-crop to content bounding box with a 4px cushion
        bbox = final_canvas.getbbox()
        if bbox:
            cushion = 4
            crop_box = (
                max(0, bbox[0] - cushion),
                max(0, bbox[1] - cushion),
                min(new_w, bbox[2] + cushion),
                min(new_h, bbox[3] + cushion),
            )
            final_canvas = final_canvas.crop(crop_box)

        return final_canvas

    def process_file(
        self,
        input_path: Path | str,
        output_path: Path | str,
        model_name: str | None = None,
        add_diecut: bool = False,
        border_width: int = 14,
    ) -> Path:
        """Process image file to isolated PNG, optionally applying die-cut sticker effect."""
        source = Path(input_path).resolve()
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        if not source.is_file():
            raise FileNotFoundError(f"Input image not found: {source}")

        isolated = self.remove_background(source, model_name=model_name)
        if add_diecut:
            final_img = self.create_diecut_sticker(isolated, border_width=border_width)
        else:
            final_img = isolated

        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{target.stem}.",
            suffix=".tmp.png",
            dir=target.parent,
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            final_img.save(tmp_path, format="PNG")
            os.replace(tmp_path, target)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        return target


def main() -> None:
    """CLI interface for BiRefNet engine and cutout_runtime subprocess calls."""
    import argparse

    parser = argparse.ArgumentParser(description="Omnicut BiRefNet Matting & Sticker Tool")
    parser.add_argument("--input", "-i", required=True, help="Input image file path")
    parser.add_argument("--output", "-o", required=True, help="Output PNG file path")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, choices=SUPPORTED_MODELS, help="Matting model")
    parser.add_argument("--diecut", action="store_true", help="Add 3D white die-cut sticker border and shadow")
    parser.add_argument("--border-width", type=int, default=14, help="Die-cut border width in px (12-16)")
    parser.add_argument("--only-mask", action="store_true", help="Return alpha mask only")
    parser.add_argument("--alpha-matting", action="store_true", help="Enable boundary refinement")
    parser.add_argument("--cpu", action="store_true", help="Force CPU execution")

    args = parser.parse_args()

    engine = BiRefNetEngine(
        default_model=args.model,
        prefer_gpu=not args.cpu,
    )

    if args.only_mask:
        mask = engine.remove_background(args.input, model_name=args.model, return_mask=True)
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        mask.save(out_p, format="PNG")
        print(f"[OK] Saved mask to {out_p}")
    else:
        out_p = engine.process_file(
            input_path=args.input,
            output_path=args.output,
            model_name=args.model,
            add_diecut=args.diecut,
            border_width=args.border_width,
        )
        print(f"[OK] Saved cutout to {out_p}")


if __name__ == "__main__":
    main()
