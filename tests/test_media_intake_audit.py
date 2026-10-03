from __future__ import annotations

from pathlib import Path

from tools import media_intake_audit as audit


def _probe(_path: Path, _ffprobe: str) -> dict:
    return {"streams": [{"codec_type": "video", "width": 1920, "height": 1080,
                         "avg_frame_rate": "30/1", "duration": "4"}],
            "format": {"duration": "4"}}


def test_cjk_ocr_text_is_flagged_for_human_review(tmp_path, monkeypatch):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"same-source-bytes")
    monkeypatch.setattr(audit, "_probe", _probe)
    monkeypatch.setattr(audit, "_ocr_frame", lambda *_args: "新品评测")

    result = audit.audit_media(video, ffprobe="ffprobe", ffmpeg="ffmpeg", tesseract="tesseract")

    assert result["status"] == "review_required"
    assert any(signal["code"] == "possible_foreign_subtitle" for signal in result["signals"])
    assert result["ocr"]["samples"]


def test_no_tesseract_never_claims_visual_approval(tmp_path, monkeypatch):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(audit, "_probe", _probe)
    monkeypatch.setattr(audit.shutil, "which", lambda _name: None)

    result = audit.audit_media(video, ffprobe="ffprobe", ffmpeg="ffmpeg", tesseract=None)

    assert result["status"] == "review_required"
    assert result["ocr"]["available"] is False


def test_same_sha256_files_are_reported_as_duplicate_candidates(tmp_path, monkeypatch):
    first = tmp_path / "one.mp4"
    second = tmp_path / "two.mp4"
    first.write_bytes(b"same")
    second.write_bytes(b"same")

    def fake_audit(path: Path, **_kwargs):
        return {"path": str(path), "sha256": "same-hash", "status": "screened_visual_review_required", "signals": []}

    monkeypatch.setattr(audit, "audit_media", fake_audit)
    report = audit.build_report([tmp_path])

    assert report["file_count"] == 2
    assert all(item["status"] == "review_required" for item in report["files"])
    assert all(item["signals"][0]["code"] == "duplicate_content" for item in report["files"])


def test_directory_scan_only_includes_supported_video_extensions(tmp_path, monkeypatch):
    (tmp_path / "clip.mp4").write_bytes(b"video")
    (tmp_path / "note.txt").write_text("not video", encoding="utf-8")
    monkeypatch.setattr(audit, "audit_media", lambda path, **_kwargs: {"path": str(path), "status": "review_required", "signals": []})

    assert audit.build_report([tmp_path])["file_count"] == 1


def test_ocr_failure_is_reviewed_instead_of_claiming_clean(tmp_path, monkeypatch):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(audit, "_probe", _probe)
    monkeypatch.setattr(audit, "_ocr_frame", lambda *_args: (_ for _ in ()).throw(RuntimeError("language pack missing")))

    result = audit.audit_media(video, ffprobe="ffprobe", ffmpeg="ffmpeg", tesseract="tesseract")

    assert result["status"] == "review_required"
    assert result["ocr"]["available"] is False
    assert any(signal["code"] == "ocr_failed" for signal in result["signals"])


def test_report_cannot_overwrite_source_media(tmp_path, monkeypatch):
    video = tmp_path / "source.mp4"
    original = b"source-bytes"
    video.write_bytes(original)
    monkeypatch.setattr(audit, "build_report", lambda paths, **_kwargs: {
        "file_count": 1, "files": [{"path": str(video.resolve())}], "read_only": True,
    })

    try:
        audit.main([str(video), "--output", str(video)])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI should reject output path that collides with input")
    assert video.read_bytes() == original
