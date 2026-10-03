"""Read-only technical and subtitle-risk audit for explicitly selected media.

This tool never moves, renames, or modifies source files. OCR is optional and
is only a screening signal; every clip remains subject to visual review.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable


MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def _run(command: list[str], *, input_bytes: bytes | None = None, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, input=input_bytes, capture_output=True, timeout=timeout, check=False)


def _files(paths: Iterable[Path]) -> list[Path]:
    found: dict[str, Path] = {}
    for requested in paths:
        path = requested.expanduser().resolve(strict=False)
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
            found[str(path).casefold()] = path
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in MEDIA_EXTENSIONS:
                    resolved = candidate.resolve(strict=False)
                    found[str(resolved).casefold()] = resolved
    return [found[key] for key in sorted(found)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe(path: Path, ffprobe: str) -> dict[str, Any]:
    result = _run([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-1200:].strip() or "ffprobe failed")
    return json.loads(result.stdout.decode("utf-8"))


def _sample_times(duration: float, *, step_s: float = 2.5, limit: int = 30) -> list[float]:
    if duration <= 0:
        return [0.0]
    count = min(limit, max(1, int(duration / step_s) + 1))
    if count == 1:
        return [min(0.1, duration / 2)]
    return [round((duration - min(0.05, duration / 10)) * i / (count - 1), 3) for i in range(count)]


def _ocr_frame(path: Path, at_s: float, ffmpeg: str, tesseract: str, language: str) -> str:
    frame = _run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{at_s:.3f}", "-i", str(path),
        "-frames:v", "1", "-vf", "scale='min(960,iw)':-2", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ], timeout=45)
    if frame.returncode or not frame.stdout:
        return ""
    result = _run([tesseract, "stdin", "stdout", "-l", language, "--psm", "6"], input_bytes=frame.stdout, timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-600:].strip() or "OCR failed")
    return result.stdout.decode("utf-8", "replace").strip()


def audit_media(path: Path, *, ffprobe: str | None = None, ffmpeg: str | None = None,
                tesseract: str | None = None, language: str = "eng+tha+chi_sim+jpn+kor") -> dict[str, Any]:
    """Return a read-only media audit record for one video."""
    ffprobe = ffprobe or shutil.which("ffprobe")
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    tesseract = tesseract or shutil.which("tesseract")
    record: dict[str, Any] = {"path": str(path.resolve(strict=False)), "status": "fail", "signals": []}
    try:
        stat = path.stat()
        record.update({"size_bytes": stat.st_size, "sha256": _sha256(path)})
        if not ffprobe:
            raise RuntimeError("ffprobe was not found on PATH")
        data = _probe(path, ffprobe)
        streams = data.get("streams", [])
        video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        if not video:
            raise RuntimeError("No video stream found")
        duration = float((video.get("duration") or data.get("format", {}).get("duration") or 0) or 0)
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        review_times = _sample_times(duration)
        record["media"] = {
            "duration_s": duration,
            "width": width,
            "height": height,
            "video_codec": video.get("codec_name"),
            "fps": video.get("avg_frame_rate") or video.get("r_frame_rate"),
            "has_audio": bool(audio),
            "audio_codec": audio.get("codec_name") if audio else None,
        }
        record["review_timestamps_s"] = review_times
        if min(width, height) < 1080:
            record["signals"].append({"code": "resolution_below_1080p", "severity": "review", "message": "ความละเอียดต่ำกว่า 1080p"})
        if not tesseract:
            record["signals"].append({"code": "ocr_unavailable", "severity": "review", "message": "ไม่พบ Tesseract; ต้องตรวจภาพด้วยคน"})
            record["ocr"] = {"available": False, "sample_count": 0, "samples": []}
        elif not ffmpeg:
            record["signals"].append({"code": "ffmpeg_unavailable", "severity": "review", "message": "ไม่พบ FFmpeg; ข้าม OCR และต้องตรวจภาพด้วยคน"})
            record["ocr"] = {"available": False, "sample_count": 0, "samples": []}
        else:
            samples = []
            ocr_error = None
            sample_times = review_times
            try:
                for at_s in sample_times:
                    text = _ocr_frame(path, at_s, ffmpeg, tesseract, language)
                    if text:
                        samples.append({"at_s": at_s, "text": text})
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                ocr_error = str(exc)[:600]
            record["ocr"] = {"available": ocr_error is None, "sample_count": len(sample_times),
                             "samples": samples, "error": ocr_error}
            if ocr_error:
                record["signals"].append({"code": "ocr_failed", "severity": "review",
                                          "message": "OCR ใช้งานไม่ได้หรือขาดภาษา; ต้องตรวจภาพด้วยคน", "detail": ocr_error})
            else:
                cjk = any(CJK_RE.search(sample["text"]) for sample in samples)
                if cjk:
                    record["signals"].append({"code": "possible_foreign_subtitle", "severity": "review", "message": "OCR พบอักษรจีน/ญี่ปุ่น/เกาหลีในเฟรมตัวอย่าง ต้องตรวจภาพจริง"})
                elif samples:
                    record["signals"].append({"code": "visible_text_detected", "severity": "review", "message": "OCR พบข้อความในเฟรมตัวอย่าง ต้องตรวจว่าเป็นซับฝังหรือข้อความในภาพสินค้า"})
                else:
                    record["signals"].append({"code": "no_text_in_samples", "severity": "info", "message": "ไม่พบข้อความจาก OCR ในเฟรมตัวอย่าง; ยังต้องตรวจภาพก่อนอนุมัติวัตถุดิบ"})
        record["status"] = "review_required" if any(s["severity"] == "review" for s in record["signals"]) else "screened_visual_review_required"
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        record["signals"].append({"code": "media_audit_failed", "severity": "fail", "message": str(exc)[:1200]})
    return record


def build_report(paths: Iterable[Path], **kwargs: Any) -> dict[str, Any]:
    requested = list(paths)
    media_paths = _files(requested)
    records = [audit_media(path, **kwargs) for path in media_paths]
    resolved_media = {str(path.resolve(strict=False)).casefold() for path in media_paths}
    for requested_path in requested:
        path = requested_path.expanduser().resolve(strict=False)
        invalid_message = None
        if not path.exists():
            invalid_message = "path does not exist"
        elif path.is_file() and path.suffix.lower() not in MEDIA_EXTENSIONS:
            invalid_message = "unsupported media extension"
        elif path.is_dir() and not any(str(candidate.resolve(strict=False)).casefold() in resolved_media
                                       for candidate in path.rglob("*") if candidate.is_file()):
            invalid_message = "directory contains no supported video files"
        if invalid_message:
            records.append({"path": str(path), "status": "fail", "signals": [
                {"code": "invalid_input_path", "severity": "fail", "message": invalid_message}
            ]})
    hashes: dict[str, list[str]] = {}
    for record in records:
        if record.get("sha256"):
            hashes.setdefault(record["sha256"], []).append(record["path"])
    for record in records:
        if len(hashes.get(record.get("sha256", ""), [])) > 1:
            record["signals"].append({"code": "duplicate_content", "severity": "review", "message": "พบไฟล์เนื้อหาเหมือนกัน (SHA-256 ตรงกัน)"})
            record["status"] = "review_required"
    has_failures = any(record.get("status") == "fail" for record in records)
    return {"schema_version": "media-intake-audit.v1", "read_only": True,
            "visual_approval_required": True,
            "status": "fail" if has_failures else "review_required",
            "file_count": len(records), "files": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Video file(s) or folders to audit")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    default_output = Path(__file__).resolve().parents[1] / ".tmp" / f"media_intake_audit_{stamp}.json"
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--ocr-language", default="eng+tha+chi_sim+jpn+kor")
    args = parser.parse_args(argv)
    report = build_report(args.paths, language=args.ocr_language)
    output_path = args.output.expanduser().resolve(strict=False)
    if any(output_path == Path(item["path"]).resolve(strict=False) for item in report["files"]):
        parser.error("report output must not overwrite an input media file")
    if output_path.exists():
        parser.error("report output already exists; choose a new path to avoid overwriting it")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "visual_approval_required": True,
                      "file_count": report["file_count"], "report": str(args.output)}, ensure_ascii=True))
    return 2 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
