"""Lazy rembg worker for one-image product subject isolation.

The worker is intentionally separate from the pure ``BackgroundIsolationV1``
contract.  Importing this module never imports rembg, ONNX Runtime, or Pillow;
those dependencies are loaded only after an enabled request has passed the
input/output safety checks.
"""

from __future__ import annotations

import importlib
import io
import json
import os
import shutil
import tempfile
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .background_isolation import (
    build_artifact_id,
    normalize_background_isolation,
    with_artifact_id,
)
from .background_isolation_artifacts import (
    artifact_paths,
    build_artifact_manifest,
    is_artifact_ready,
)

STATUS_NOOP = "noop"
STATUS_READY = "ready"
STATUS_ERROR = "error"

ERROR_CONFIG_MISSING = "config_missing"
ERROR_CONFIG_DISABLED = "config_disabled"
ERROR_CONFIG_INVALID = "config_invalid"
ERROR_INPUT_MISSING = "input_missing"
ERROR_INPUT_NOT_FOUND = "input_not_found"
ERROR_OUTPUT_MISSING = "output_missing"
ERROR_OUTPUT_EQUALS_INPUT = "output_equals_input"
ERROR_OUTPUT_DIRECTORY_MISSING = "output_directory_missing"
ERROR_REMBG_MISSING = "rembg_missing"
ERROR_ONNXRUNTIME_MISSING = "onnxruntime_missing"
ERROR_REMBG_RUNTIME = "rembg_runtime_unavailable"
ERROR_REMBG_OUTPUT = "invalid_rembg_output"
ERROR_REMBG_QUALITY = "rembg_quality_gate_failed"
ERROR_IMAGE_RUNTIME = "image_runtime_unavailable"
ERROR_OUTPUT_WRITE = "output_write_failed"
ERROR_OUTPUT_COMMIT = "output_commit_failed"
ERROR_SOURCE_FINGERPRINT_MISSING = "source_fingerprint_missing"
ERROR_SOURCE_FINGERPRINT_INVALID = "source_fingerprint_invalid"
ERROR_ARTIFACT_COMMIT = "artifact_commit_failed"


class _RuntimeUnavailable(RuntimeError):
    """Internal exception carrying a stable, user-actionable error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _OutputCommitFailed(RuntimeError):
    """Internal exception for a failed final atomic replace."""


class _QualityGateFailed(ValueError):
    """Internal exception for a decoded but unsafe foreground mask."""


def _result(
    *,
    ok: bool,
    status: str,
    error_code: str | None = None,
    message: str,
    output_path: Path | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    """Return one stable result shape for no-op, success, and failure paths."""

    return {
        "ok": ok,
        "status": status,
        "error_code": error_code,
        "message": message,
        "output_path": str(output_path) if output_path is not None else None,
        "artifact_id": artifact_id,
    }


def _runtime_error(exc: BaseException) -> _RuntimeUnavailable:
    missing_name = getattr(exc, "name", None) or ""
    details = str(exc).strip()
    haystack = f"{missing_name} {details}".lower()
    if "onnxruntime" in haystack:
        return _RuntimeUnavailable(
            ERROR_ONNXRUNTIME_MISSING,
            "ONNX Runtime is not available for rembg. Install it in the project venv, then retry.",
        )
    if "rembg" in haystack or isinstance(exc, ModuleNotFoundError):
        return _RuntimeUnavailable(
            ERROR_REMBG_MISSING,
            "rembg is not available. Install the project runtime dependency, then retry.",
        )
    return _RuntimeUnavailable(
        ERROR_REMBG_RUNTIME,
        f"rembg runtime could not start: {details or exc.__class__.__name__}. Check the project venv and model runtime.",
    )


def _load_rembg() -> Any:
    """Import rembg only when an enabled worker request actually needs it."""

    try:
        return importlib.import_module("rembg")
    except (ImportError, ModuleNotFoundError) as exc:
        raise _runtime_error(exc) from exc


_QUALITY_GATE_LIMITS: dict[str, tuple[float, float, float]] = {
    # Keep draft permissive for small subjects, while still rejecting empty or
    # effectively full-frame masks that are common catastrophic rembg outputs.
    "draft": (0.0005, 0.9995, 0.0005),
    "balanced": (0.001, 0.995, 0.001),
    "quality": (0.002, 0.99, 0.002),
}


def _validate_alpha_quality(image: Any, *, expected_size: tuple[int, int], quality: str) -> None:
    """Fail closed on alpha masks with no plausible foreground coverage."""

    if image.size != expected_size:
        raise _QualityGateFailed(
            f"rembg output dimensions {image.size} do not match input dimensions {expected_size}."
        )

    alpha = image.getchannel("A")
    histogram = alpha.histogram()
    total = image.size[0] * image.size[1]
    if total <= 0:
        raise _QualityGateFailed("rembg output has no pixels to evaluate.")

    visible_pixels = total - histogram[0]
    visible_ratio = visible_pixels / total
    alpha_mass = sum(level * count for level, count in enumerate(histogram)) / (255 * total)
    minimum_visible, maximum_visible, minimum_mass = _QUALITY_GATE_LIMITS[quality]

    if visible_pixels == 0:
        raise _QualityGateFailed("rembg mask is effectively transparent; no usable subject was isolated.")
    if visible_ratio <= minimum_visible:
        raise _QualityGateFailed("rembg mask isolates a subject that is too small to be trusted.")
    if alpha_mass <= minimum_mass:
        raise _QualityGateFailed("rembg mask is effectively transparent; no usable subject was isolated.")
    if visible_ratio >= maximum_visible:
        raise _QualityGateFailed("rembg mask covers almost the entire frame; background removal is untrusted.")


class BackgroundIsolationWorker:
    """Process one image at a time with a lazily loaded rembg runtime.

    ``loader`` is injectable for deterministic tests and for a future runtime
    adapter.  A worker instance caches one rembg session per model, while the
    module itself remains safe to import when rembg is not installed.
    """

    def __init__(self, loader: Callable[[], Any] | None = None) -> None:
        self._loader = loader or _load_rembg
        self._rembg: Any | None = None
        self._sessions: dict[str, Any] = {}
        self._load_lock = threading.Lock()

    def _get_session(self, model: str) -> tuple[Any, Any | None]:
        if self._rembg is None:
            with self._load_lock:
                if self._rembg is None:
                    try:
                        self._rembg = self._loader()
                    except _RuntimeUnavailable:
                        raise
                    except (ImportError, ModuleNotFoundError) as exc:
                        raise _runtime_error(exc) from exc
                    except Exception as exc:
                        raise _runtime_error(exc) from exc

        new_session = getattr(self._rembg, "new_session", None)
        if not callable(new_session):
            return self._rembg, None
        if model not in self._sessions:
            try:
                self._sessions[model] = new_session(model_name=model)
            except (ImportError, ModuleNotFoundError) as exc:
                raise _runtime_error(exc) from exc
            except Exception as exc:
                raise _runtime_error(exc) from exc
        return self._rembg, self._sessions[model]

    @staticmethod
    def _validate_paths(input_path: Any, output_path: Any) -> tuple[Path, Path] | dict[str, Any]:
        if input_path is None:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_INPUT_MISSING,
                message="Input image path is required.",
            )
        if output_path is None:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_OUTPUT_MISSING,
                message="Output PNG path is required.",
            )

        try:
            source = Path(input_path)
            target = Path(output_path)
        except (TypeError, ValueError):
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_INPUT_MISSING,
                message="Input and output paths must be valid filesystem paths.",
            )

        if not source.is_file():
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_INPUT_NOT_FOUND,
                message="Input image does not exist or is not a regular file.",
            )

        try:
            same_path = source.resolve() == target.resolve()
            same_file = target.exists() and os.path.samefile(source, target)
        except (FileNotFoundError, OSError, RuntimeError):
            same_path = False
            same_file = False
        if same_path or same_file:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_OUTPUT_EQUALS_INPUT,
                message="Output path must differ from the input image; the source is never overwritten.",
            )

        if not target.parent.is_dir():
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_OUTPUT_DIRECTORY_MISSING,
                message="Output directory does not exist; create the cache directory and retry.",
            )
        return source, target

    @staticmethod
    def _write_rgba_png(
        payload: bytes,
        target: Path,
        *,
        expected_size: tuple[int, int],
        quality: str,
    ) -> None:
        """Validate rembg bytes and write a canonical RGBA PNG to ``target``."""

        try:
            from PIL import Image
        except (ImportError, ModuleNotFoundError) as exc:
            raise _RuntimeUnavailable(
                ERROR_IMAGE_RUNTIME,
                "Pillow is required to validate and write the foreground PNG.",
            ) from exc

        try:
            with Image.open(io.BytesIO(payload)) as image:
                rgba = image.convert("RGBA")
                _validate_alpha_quality(rgba, expected_size=expected_size, quality=quality)
        except Exception as exc:
            if isinstance(exc, _QualityGateFailed):
                raise
            raise ValueError("rembg returned bytes that are not a readable image") from exc
        rgba.save(target, format="PNG")

    @staticmethod
    def _source_size(source: Path) -> tuple[int, int]:
        try:
            from PIL import Image
        except (ImportError, ModuleNotFoundError) as exc:
            raise _RuntimeUnavailable(
                ERROR_IMAGE_RUNTIME,
                "Pillow is required to validate the source image.",
            ) from exc

        try:
            with Image.open(source) as image:
                return image.size
        except Exception as exc:
            raise ValueError("input image is not a readable image") from exc

    @staticmethod
    def _artifact_is_usable(
        foreground_path: Path,
        alpha_path: Path,
        *,
        expected_size: tuple[int, int],
        quality: str,
    ) -> bool:
        """Validate a ready cache hit without mutating the existing artifact."""

        if any(
            path.is_symlink() or not path.is_file()
            for path in (foreground_path, alpha_path)
        ):
            return False
        try:
            from PIL import Image

            with Image.open(foreground_path) as foreground:
                if foreground.mode != "RGBA":
                    return False
                _validate_alpha_quality(foreground, expected_size=expected_size, quality=quality)
            with Image.open(alpha_path) as alpha:
                return alpha.mode == "L" and alpha.size == expected_size
        except Exception:
            return False

    @staticmethod
    def _cleanup_staged(path: Path | None) -> None:
        if path is None:
            return
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
        except OSError:
            pass

    @classmethod
    def _publish_artifact_atomically(cls, temporary: Path, target: Path, namespace: Path) -> None:
        """Publish a complete staged bundle while preserving it on failure."""

        backup: Path | None = None
        try:
            if target.exists():
                backup = Path(tempfile.mkdtemp(prefix=f".{target.name}.stale.", dir=namespace))
                backup.rmdir()
                os.replace(target, backup)
            os.replace(temporary, target)
            temporary = None  # type: ignore[assignment]
        except OSError:
            if backup is not None and not target.exists() and backup.exists():
                try:
                    os.replace(backup, target)
                    backup = None
                except OSError:
                    pass
            raise
        finally:
            cls._cleanup_staged(backup)

    def process(
        self,
        input_path: str | os.PathLike[str] | None,
        output_path: str | os.PathLike[str] | None,
        config: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Isolate one image into an atomically committed foreground PNG.

        Disabled or malformed contracts return without importing rembg and
        without creating an output file.  Every enabled failure is structured
        and leaves an existing output untouched unless the final atomic replace
        succeeds.
        """

        if config is None:
            return _result(
                ok=True,
                status=STATUS_NOOP,
                error_code=ERROR_CONFIG_MISSING,
                message="Background isolation is not configured; skipped.",
            )

        normalized = normalize_background_isolation(config)
        if not normalized["enabled"]:
            reason = normalized.get("reason", "disabled")
            error_code = ERROR_CONFIG_DISABLED if reason == "disabled" else ERROR_CONFIG_INVALID
            return _result(
                ok=True,
                status=STATUS_NOOP,
                error_code=error_code,
                message=f"Background isolation is disabled or invalid ({reason}); skipped.",
            )

        paths = self._validate_paths(input_path, output_path)
        if isinstance(paths, dict):
            return paths
        source, target = paths
        artifact_id = normalized["artifact"].get("id")
        temporary_path: Path | None = None

        try:
            source_size = self._source_size(source)
            rembg, session = self._get_session(normalized["model"])
            source_bytes = source.read_bytes()
            remove = getattr(rembg, "remove", None)
            if not callable(remove):
                raise _RuntimeUnavailable(
                    ERROR_REMBG_RUNTIME,
                    "rembg loaded without its remove() API; check the installed runtime version.",
                )
            result = remove(source_bytes, session=session) if session is not None else remove(source_bytes)
            if not isinstance(result, (bytes, bytearray)) or not result:
                raise ValueError("rembg returned no image bytes")

            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{target.stem}.",
                suffix=".tmp.png",
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            self._write_rgba_png(
                bytes(result),
                temporary_path,
                expected_size=source_size,
                quality=normalized["quality"],
            )
            if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                raise ValueError("foreground PNG was empty after encoding")
            try:
                os.replace(temporary_path, target)
            except OSError as exc:
                raise _OutputCommitFailed(str(exc)) from exc
            temporary_path = None
            return _result(
                ok=True,
                status=STATUS_READY,
                message="Foreground PNG created successfully.",
                output_path=target,
                artifact_id=artifact_id,
            )
        except _RuntimeUnavailable as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=exc.code,
                message=str(exc),
                artifact_id=artifact_id,
            )
        except _OutputCommitFailed as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_OUTPUT_COMMIT,
                message=f"Could not atomically commit the foreground PNG: {exc}",
                artifact_id=artifact_id,
            )
        except _QualityGateFailed as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_REMBG_QUALITY,
                message=str(exc),
                artifact_id=artifact_id,
            )
        except ValueError as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_REMBG_OUTPUT,
                message=str(exc),
                artifact_id=artifact_id,
            )
        except OSError as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_OUTPUT_WRITE,
                message=f"Could not write the foreground PNG: {exc}",
                artifact_id=artifact_id,
            )
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _alpha_png_bytes(foreground_path: Path) -> bytes:
        """Extract the foreground alpha channel as a canonical grayscale PNG."""

        try:
            from PIL import Image
        except (ImportError, ModuleNotFoundError) as exc:
            raise _RuntimeUnavailable(
                ERROR_IMAGE_RUNTIME,
                "Pillow is required to create the alpha PNG.",
            ) from exc

        try:
            with Image.open(foreground_path) as image:
                alpha = image.convert("RGBA").getchannel("A")
                buffer = io.BytesIO()
                alpha.save(buffer, format="PNG")
                return buffer.getvalue()
        except Exception as exc:
            raise ValueError("foreground PNG did not contain a readable alpha channel") from exc

    @staticmethod
    def _cleanup_artifact(cache_root: str | os.PathLike[str], artifact_id: str) -> None:
        """Best-effort cleanup that can never turn a failed run into ready."""

        try:
            clear_artifact(cache_root, artifact_id)
        except (OSError, ValueError):
            pass

    def process_artifact_bundle(
        self,
        input_path: str | os.PathLike[str] | None,
        cache_root: str | os.PathLike[str],
        config: Mapping[str, Any] | None,
        source_fingerprint: str | None,
    ) -> dict[str, Any]:
        """Create one cached foreground/alpha bundle from a source image.

        The artifact ID is derived from the canonical config and source
        fingerprint.  No manifest is written until both PNGs are committed,
        so an interrupted or failed run cannot advertise a false ``ready``
        artifact.  A valid ready bundle is returned without loading rembg.
        """

        if config is None:
            return _result(
                ok=True,
                status=STATUS_NOOP,
                error_code=ERROR_CONFIG_MISSING,
                message="Background isolation is not configured; skipped.",
            )

        normalized = normalize_background_isolation(config)
        if not normalized["enabled"]:
            reason = normalized.get("reason", "disabled")
            error_code = ERROR_CONFIG_DISABLED if reason == "disabled" else ERROR_CONFIG_INVALID
            return _result(
                ok=True,
                status=STATUS_NOOP,
                error_code=error_code,
                message=f"Background isolation is disabled or invalid ({reason}); skipped.",
            )

        if source_fingerprint is None:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_SOURCE_FINGERPRINT_MISSING,
                message="A source fingerprint is required to derive the artifact ID.",
            )

        prepared = with_artifact_id(normalized, source_fingerprint)
        artifact_id = build_artifact_id(source_fingerprint, prepared)
        if artifact_id is None or prepared["artifact"].get("id") != artifact_id:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_SOURCE_FINGERPRINT_INVALID,
                message="The source fingerprint is invalid; no artifact was created.",
            )

        try:
            paths = artifact_paths(cache_root, artifact_id)
        except (OSError, ValueError) as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_ARTIFACT_COMMIT,
                message=f"Could not prepare the artifact cache: {exc}",
                artifact_id=artifact_id,
            )

        try:
            source_size = self._source_size(Path(input_path)) if input_path is not None else None
        except (TypeError, ValueError, _RuntimeUnavailable):
            source_size = None
        if (
            source_size is not None
            and is_artifact_ready(cache_root, artifact_id)
            and self._artifact_is_usable(
                paths.foreground,
                paths.alpha,
                expected_size=source_size,
                quality=normalized["quality"],
            )
        ):
            return _result(
                ok=True,
                status=STATUS_READY,
                message="Foreground and alpha artifact bundle already exists; cache hit.",
                output_path=paths.foreground,
                artifact_id=artifact_id,
            )

        staged_root: Path | None = None
        try:
            namespace = paths.directory.parent
            namespace.mkdir(parents=True, exist_ok=True)
            staged_root = Path(tempfile.mkdtemp(prefix=f".{artifact_id}.", dir=namespace))
            staged_foreground = staged_root / "foreground.png"
            staged_alpha = staged_root / "alpha.png"
            foreground_result = self.process(input_path, staged_foreground, prepared)
            if foreground_result["status"] != STATUS_READY:
                return _result(
                    ok=False,
                    status=STATUS_ERROR,
                    error_code=foreground_result.get("error_code") or ERROR_ARTIFACT_COMMIT,
                    message=foreground_result["message"],
                    artifact_id=artifact_id,
                )

            alpha_payload = self._alpha_png_bytes(staged_foreground)
            staged_alpha.write_bytes(alpha_payload)
            manifest_payload = json.dumps(
                build_artifact_manifest(artifact_id, status=STATUS_READY),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            (staged_root / "manifest.json").write_bytes(manifest_payload)
            if not self._artifact_is_usable(
                staged_foreground,
                staged_alpha,
                expected_size=self._source_size(Path(input_path)),
                quality=normalized["quality"],
            ):
                raise OSError("staged foreground or alpha PNG failed ready verification")
            self._publish_artifact_atomically(staged_root, paths.directory, namespace)
            staged_root = None
            if not is_artifact_ready(cache_root, artifact_id):
                raise OSError("published foreground and alpha artifact is not ready")
            return _result(
                ok=True,
                status=STATUS_READY,
                message="Foreground and alpha artifact bundle created successfully.",
                output_path=paths.foreground,
                artifact_id=artifact_id,
            )
        except _RuntimeUnavailable as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=exc.code,
                message=str(exc),
                artifact_id=artifact_id,
            )
        except (OSError, ValueError) as exc:
            return _result(
                ok=False,
                status=STATUS_ERROR,
                error_code=ERROR_ARTIFACT_COMMIT,
                message=f"Could not commit the artifact bundle: {exc}",
                artifact_id=artifact_id,
            )
        finally:
            self._cleanup_staged(staged_root)


def process_background_isolation(
    input_path: str | os.PathLike[str] | None,
    output_path: str | os.PathLike[str] | None,
    config: Mapping[str, Any] | None,
    *,
    worker: BackgroundIsolationWorker | None = None,
) -> dict[str, Any]:
    """Convenience API for one request without importing rembg at module load."""

    return (worker or BackgroundIsolationWorker()).process(input_path, output_path, config)


process_image = process_background_isolation


def process_background_isolation_bundle(
    input_path: str | os.PathLike[str] | None,
    cache_root: str | os.PathLike[str],
    config: Mapping[str, Any] | None,
    source_fingerprint: str | None,
    *,
    worker: BackgroundIsolationWorker | None = None,
) -> dict[str, Any]:
    """Convenience API for creating one cached foreground/alpha bundle."""

    return (worker or BackgroundIsolationWorker()).process_artifact_bundle(
        input_path,
        cache_root,
        config,
        source_fingerprint,
    )


process_bundle = process_background_isolation_bundle


__all__ = [
    "ERROR_ARTIFACT_COMMIT",
    "ERROR_CONFIG_DISABLED",
    "ERROR_CONFIG_INVALID",
    "ERROR_CONFIG_MISSING",
    "ERROR_IMAGE_RUNTIME",
    "ERROR_INPUT_MISSING",
    "ERROR_INPUT_NOT_FOUND",
    "ERROR_ONNXRUNTIME_MISSING",
    "ERROR_OUTPUT_COMMIT",
    "ERROR_OUTPUT_DIRECTORY_MISSING",
    "ERROR_OUTPUT_EQUALS_INPUT",
    "ERROR_OUTPUT_MISSING",
    "ERROR_OUTPUT_WRITE",
    "ERROR_REMBG_MISSING",
    "ERROR_REMBG_OUTPUT",
    "ERROR_REMBG_QUALITY",
    "ERROR_REMBG_RUNTIME",
    "ERROR_SOURCE_FINGERPRINT_INVALID",
    "ERROR_SOURCE_FINGERPRINT_MISSING",
    "STATUS_ERROR",
    "STATUS_NOOP",
    "STATUS_READY",
    "BackgroundIsolationWorker",
    "process_background_isolation",
    "process_background_isolation_bundle",
    "process_bundle",
    "process_image",
]
