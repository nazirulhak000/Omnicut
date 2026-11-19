# -*- coding: utf-8 -*-
"""Regression tests for Speed Round 2 Category 1 fixes (R1, R2, R3, ข1, ก1).

Runs with both ``pytest`` and stdlib ``python3 -m unittest``.
All files live in temporary directories — never touches 01_Raw/02_Assets/04_Exports.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import media_validation, render_jobs, tiktok_enhancer

ROOT = Path(__file__).resolve().parents[1]


class TestSpeedRound2Category1(unittest.TestCase):
    # ------------------------------------------------------------------ R1
    def test_r1_audio_mix_stage_and_sfx_manager_do_not_trim_voiceover(self):
        """R1: Mixing must never overwrite voiceover.wav via trim_silence_and_tail_artifacts_wav."""
        mix_src = (ROOT / "scripts" / "stages" / "audio_mix_stage.py").read_text(encoding="utf-8")
        self.assertNotIn("trim_silence_and_tail_artifacts_wav", mix_src)

        sfx_src = (ROOT / "scripts" / "sfx_manager.py").read_text(encoding="utf-8")
        self.assertNotIn("trim_silence_and_tail_artifacts_wav", sfx_src)

    # ------------------------------------------------------------------ R2
    def test_r2_validate_mp4_rejects_truncated_faststart_long_clip(self):
        """R2: A +faststart MP4 cut in half (even longer than tail_seconds) must be rejected."""
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg/ffprobe required")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = root / "good_10s.mp4"
            half = root / "half_10s.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=10.0",
                    "-f", "lavfi", "-i", "sine=frequency=800:duration=10.0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-g", "60", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "64k", "-shortest",
                    "-movflags", "+faststart",
                    str(good),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            data = good.read_bytes()
            half.write_bytes(data[: len(data) // 2])

            res_good = media_validation.validate_mp4(good, use_cache=False)
            self.assertTrue(res_good.ok, res_good.reason)

            res_half = media_validation.validate_mp4(half, use_cache=False)
            self.assertFalse(res_half.ok, "Truncated +faststart MP4 must be rejected")
            self.assertIn("ขาดไม่ครบไฟล์", res_half.reason)

    # ------------------------------------------------------------------ R3
    def test_r3_api_iphone_forces_utf8_and_handles_none_stdout(self):
        """R3: api_iphone uses UTF-8 encoding and never crashes on None stdout."""
        from scripts import api_iphone

        self.assertIn("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8", api_iphone.SCAN_PS_SCRIPT)

        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stdout = None
        with patch("scripts.api_iphone.subprocess.run", return_value=mock_res) as mock_run:
            out = api_iphone.get_iphone_status()
            self.assertFalse(out["connected"])
            self.assertNotIn("NoneType", str(out.get("error") or ""))
            _, kwargs = mock_run.call_args
            self.assertEqual(kwargs.get("encoding"), "utf-8")
            self.assertEqual(kwargs.get("errors"), "replace")

    # ------------------------------------------------------------------ ข1
    def test_kh1_enhancer_uses_real_probe_and_supports_amf_fallback(self):
        """ข1: check_nvenc_support uses a real encode probe (not -encoders grep) and supports AMF/QSV/NVENC."""
        src = Path(tiktok_enhancer.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"-encoders"', src)
        self.assertIn("h264_amf", src)
        self.assertIn("h264_qsv", src)
        self.assertIn("h264_videotoolbox", src)

        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg/ffprobe required")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clip = root / "clip.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:d=0.5:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=1000:duration=0.5",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k",
                    str(clip),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            out = tiktok_enhancer.enhance_video_for_tiktok(clip)
            self.assertTrue(out.is_file())
            self.assertTrue(media_validation.is_valid_mp4(out, use_cache=False))

    # ------------------------------------------------------------------ ก1
    def test_k1_ram_safe_concurrency_caps_by_available_ram(self):
        """ก1: Batch workers are capped to min(requested, avail_ram // 3.5 GB)."""
        gb = 1024 ** 3
        self.assertEqual(render_jobs.ram_safe_concurrency(4, available_ram_bytes=int(1.2 * gb)), 1)
        self.assertEqual(render_jobs.ram_safe_concurrency(4, available_ram_bytes=int(4.5 * gb)), 1)
        self.assertEqual(render_jobs.ram_safe_concurrency(4, available_ram_bytes=int(8.0 * gb)), 2)
        self.assertEqual(render_jobs.ram_safe_concurrency(4, available_ram_bytes=int(11.0 * gb)), 3)
        self.assertEqual(render_jobs.ram_safe_concurrency(4, available_ram_bytes=int(20.0 * gb)), 4)
        self.assertEqual(render_jobs.ram_safe_concurrency(2, available_ram_bytes=int(20.0 * gb)), 2)


if __name__ == "__main__":
    unittest.main()
