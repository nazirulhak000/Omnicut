"""Bounded Chromium Timeline interaction probe at 1/10/50/100 clips."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from urllib.parse import urlencode, urlsplit
import wave

import pytest
from playwright.sync_api import sync_playwright

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import create_empty_ass, vite_fs_url
from scripts.video_editor import VideoEditor


@pytest.mark.parametrize("clip_count", [1, 10, 50, 100])
def test_timeline_mount_and_selection_remain_responsive(motion_fixture_url, clip_count):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html?clipCount={clip_count}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            started = perf_counter()
            page.goto(url, wait_until="domcontentloaded")
            clips = page.get_by_test_id("timeline-controls-ready").locator('[data-timeline-item="clip"]')
            assert clips.count() == clip_count
            mount_ms = (perf_counter() - started) * 1000

            started = perf_counter()
            clips.first.click()
            assert clips.first.get_attribute("aria-pressed") == "true"
            select_ms = (perf_counter() - started) * 1000
            state = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert state["selectedClipId"] == state["timelineClips"][0]["id"]

            heap_bytes = page.evaluate("performance.memory?.usedJSHeapSize ?? null")
            print(json.dumps({
                "clip_count": clip_count,
                "mount_ms": round(mount_ms, 1),
                "select_ms": round(select_ms, 1),
                "heap_bytes": heap_bytes,
            }))
            assert mount_ms < 8000
            assert select_ms < 2000
        finally:
            browser.close()


@pytest.mark.parametrize("clip_count", [1, 10, 50, 100])
def test_real_media_preview_seek_and_playback_at_scale(motion_fixture_url, clip_count):
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("editor-media-performance-") as temp_root:
        source = create_clip_source(Path(temp_root))
        query = urlencode({"clipCount": clip_count, "mediaClip": vite_fs_url(base_url, source)})
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                started = perf_counter()
                page.goto(f"{base_url}/editor_controls.html?{query}", wait_until="domcontentloaded")
                preview = page.get_by_test_id("real-media-preview")
                slider = preview.get_by_role("slider", name="เลื่อนตำแหน่งเล่นวิดีโอ")
                slider.wait_for(timeout=20000)
                ready_ms = (perf_counter() - started) * 1000
                assert preview.locator("video").count() == clip_count

                started = perf_counter()
                seek_time = 2 * (clip_count - 1) + 0.5
                slider.fill(str(seek_time))
                page.wait_for_function("""({count}) => {
                    const root = document.querySelector('[data-testid="real-media-preview"]');
                    const active = root?.querySelectorAll('video')[count - 1];
                    return active && active.readyState >= 2 && !active.seeking
                        && Math.abs(active.currentTime - 0.5) < 0.08;
                }""", arg={"count": clip_count}, timeout=20000)
                seek_ms = (perf_counter() - started) * 1000

                slider.fill("0")
                play = preview.get_by_role("button", name="เล่นพรีวิว")
                play.click()
                page.wait_for_function("""() => {
                    const root = document.querySelector('[data-testid="real-media-preview"]');
                    const slider = root?.querySelector('input[type="range"]');
                    return Number(slider?.value) >= 0.7;
                }""", timeout=10000)
                quality = preview.locator("video").first.evaluate("""video => {
                    const q = video.getVideoPlaybackQuality?.();
                    return {decoded: q?.totalVideoFrames ?? 0, dropped: q?.droppedVideoFrames ?? 0};
                }""")
                preview.get_by_role("button", name="หยุดพรีวิวชั่วคราว").click()
                print(json.dumps({
                    "clip_count": clip_count,
                    "real_media_ready_ms": round(ready_ms, 1),
                    "end_seek_ms": round(seek_ms, 1),
                    "decoded_frames": quality["decoded"],
                    "dropped_frames": quality["dropped"],
                    "heap_bytes": page.evaluate("performance.memory?.usedJSHeapSize ?? null"),
                }))
                assert not errors, errors
                assert ready_ms < 20000
                assert seek_ms < 8000
                assert quality["decoded"] > 0
                assert quality["dropped"] < max(quality["decoded"] * 0.5, 5)
            finally:
                browser.close()


@pytest.mark.parametrize("clip_count", [1, 10, 50, 100])
def test_real_media_render_completes_at_scale(monkeypatch, clip_count):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    with temp_capture_dir("editor-render-performance-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root)
        audio = root / "silence.wav"
        with wave.open(str(audio), "wb") as sound:
            sound.setnchannels(2)
            sound.setsampwidth(2)
            sound.setframerate(48000)
            sound.writeframes(b"\x00" * (48000 * 4 * (clip_count + 5) // 10))
        output = root / "rendered.mp4"
        clips = [{"source_path": str(source), "trim_start": 0, "trim_end": 0.1, "speed": 1}
                 for _ in range(clip_count)]
        started = perf_counter()
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(source)],
            total_duration=clip_count * 0.1,
            mixed_audio_path=str(audio),
            ass_subtitle_path=str(create_empty_ass(root)),
            output_mp4_path=str(output),
            clip_list=clips,
            export_preset="draft",
            style_preset="clean_tech_review",
        )
        render_seconds = perf_counter() - started
        ffprobe = shutil.which("ffprobe")
        assert ffprobe is not None
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
            capture_output=True, text=True, check=True,
        )
        output_duration = float(probe.stdout.strip())
        print(json.dumps({"clip_count": clip_count, "render_seconds": round(render_seconds, 2),
                          "output_bytes": output.stat().st_size,
                          "output_duration": output_duration}))
        assert output.stat().st_size > 1000
        assert abs(output_duration - clip_count * 0.1) < 0.15
        assert render_seconds < 180
