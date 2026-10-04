"""Browser smoke of the real EditorShell with an isolated in-memory API."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
import pytest

from scripts.video_editor import VideoEditor
from tests.motion_capture.ass_fixture import compare_frames
from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import _render_frames, create_clip_source
from tests.motion_capture.frame_pair import _composite_canvas_frame
from tests.motion_capture.overlay_pair import create_empty_ass, create_silent_audio, vite_fs_url


@pytest.mark.parametrize("mode", ["trim", "fade-boundary", "fade-boundary-compact", "split-boundary"])
def test_editor_shell_save_reload_preview_matches_render(motion_fixture_url, monkeypatch, mode):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    with_fade = mode.startswith("fade-boundary")
    with_split = mode == "split-boundary"
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("editor-shell-browser-") as temp_root:
        sample_times = (
            (0.0, 0.35, 0.5, 0.7, 1.2) if with_fade else
            (0.0, 0.467, 0.5, 0.533, 1.2) if with_split else
            (0.0, 0.6, 1.2)
        )
        root = Path(temp_root)
        sources = [create_clip_source(root)]
        if with_fade:
            sources.append(create_clip_source(root, variant=2))
        clip_url = vite_fs_url(base_url, sources[0])
        clip_list = [{"source_path": clip_url, "trim_start": 0, "trim_end": 1.2 if with_fade else 2,
                      "duration": 1.2 if with_fade else 2}]
        manifest = {
            "project_name": "editor-audit",
            "clip_list": clip_list,
            "transitions": [],
            "total_duration": 2,
            "cues": [],
            "artifacts": {},
            "show_watermark": False,
        }
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                viewport = {"width": 1024, "height": 768} if mode.endswith("compact") else {"width": 1600, "height": 1100}
                page = browser.new_page(viewport=viewport, ignore_https_errors=True)
                # This contract exercises the optional paused inspection over
                # smooth playback; full-resolution playback has its own suite.
                page.add_init_script("localStorage.setItem('omnicut.previewQuality', 'smooth540')")
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def mock_api(route):
                    request = route.request
                    path = urlsplit(request.url).path
                    if path == "/api/projects/editor-audit" and request.method == "GET":
                        response = manifest
                    elif path == "/api/projects/editor-audit/state" and request.method == "PATCH":
                        manifest.update(request.post_data_json or {})
                        response = manifest
                    elif path == "/api/projects":
                        response = {"projects": ["editor-audit"]}
                    elif path == "/api/assets/all":
                        response = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                    elif path == "/api/hook-motion-presets":
                        response = {"catalog": {}, "default": None}
                    else:
                        response = {"tasks": [], "milestones": [], "custom": []}
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(response))

                page.route("**/api/**", mock_api)
                clip2_query = f"&clip2={vite_fs_url(base_url, sources[1])}" if with_fade else ""
                page.goto(f"{base_url}/editor_shell_audit.html?clip={clip_url}{clip2_query}", wait_until="domcontentloaded")
                if with_fade:
                    page.get_by_title("audit second clip").first.click()
                    page.locator('[data-timeline-item="clip"]:visible').nth(1).wait_for(timeout=10000)
                    trigger = page.locator('[data-transition-trigger]:visible').first
                    trigger.click()
                    assert trigger.get_attribute("aria-expanded") == "true"
                    assert page.get_by_role("dialog", name="ตั้งค่ารอยต่อคลิป").is_visible()
                    page.get_by_role("button", name="จางเข้าหากัน").click()
                    assert trigger.get_attribute("aria-expanded") == "false"
                    trigger.click()
                    page.keyboard.press("Escape")
                    assert trigger.get_attribute("aria-expanded") == "false"
                    assert page.get_by_role("dialog", name="ตั้งค่ารอยต่อคลิป").count() == 0
                if with_split:
                    ruler = page.locator('[title="คลิกหรือลากเพื่อเลื่อนหัวอ่าน"]:visible').first
                    tick = ruler.locator(':scope > div').nth(1)
                    minutes, seconds = tick.inner_text().strip().split(':')
                    px_per_second = float(tick.evaluate("node => parseFloat(node.style.left)")) / (
                        int(minutes) * 60 + float(seconds)
                    )
                    ruler.click(position={"x": px_per_second, "y": 10})
                    page.locator('[data-timeline-item="clip"]:visible').first.click(
                        button="right", position={"x": 5, "y": 5}
                    )
                    page.get_by_role("button", name="ผ่าคลิปตรงหัวอ่าน").click()
                    assert page.locator('[data-timeline-item="clip"]:visible').count() == 2
                clip = page.locator('[data-timeline-item="clip"]:visible').first
                clip.wait_for(timeout=10000)
                clip.click(position={"x": 5, "y": 5})
                assert clip.get_attribute("aria-pressed") == "true"
                if with_fade:
                    clips = page.locator('[data-timeline-item="clip"]:visible')
                    clip.focus()
                    page.keyboard.press("]")
                    assert "clip_source_2_" in clips.first.get_attribute("aria-label")
                    page.keyboard.press("Control+z")
                    assert "clip_source_0_" in clips.first.get_attribute("aria-label")
                    page.keyboard.press("Control+Shift+z")
                    assert "clip_source_2_" in clips.first.get_attribute("aria-label")
                    page.keyboard.press("Control+z")
                    assert "clip_source_0_" in clips.first.get_attribute("aria-label")
                trim_in = page.locator('input[aria-label="Trim เข้า (วิ)"]:visible').first
                trim_in.fill("0.5")
                save_button = page.get_by_title("บันทึกการแก้ไขลงโปรเจกต์ (Ctrl+S)")
                with page.expect_response(lambda response: (
                    "/api/projects/editor-audit/state" in response.url
                    and response.request.method == "PATCH"
                )):
                    save_button.click()
                assert manifest["clip_list"][0]["trim_start"] == 0.5
                if with_fade:
                    assert manifest["transitions"][0]["type"] == "fade"
                if with_split:
                    assert len(manifest["clip_list"]) == 2
                    assert manifest["clip_list"][0]["trim_end"] == 1.0
                    assert manifest["clip_list"][1]["trim_start"] == 1.0

                page.reload(wait_until="domcontentloaded")
                restored_clip = page.locator('[data-timeline-item="clip"]:visible').first
                restored_clip.wait_for(timeout=10000)
                restored_clip.click(position={"x": 5, "y": 5})
                assert page.locator('input[aria-label="Trim เข้า (วิ)"]:visible').first.input_value() == "0.5"

                canvas = page.locator('canvas[width="540"][height="960"]:visible').first
                page.wait_for_function("""() => {
                    const image = [...document.querySelectorAll('img[data-testid="high-resolution-still-preview"]')]
                        .find(node => node.getBoundingClientRect().width > 0);
                    return image && image.complete && image.naturalWidth === 1080
                        && image.naturalHeight === 1920
                        && image.dataset.previewResolution === '1080x1920'
                        && image.dataset.previewSource === 'master';
                }""", timeout=15000)
                sharp_button = page.locator('[data-testid="toggle-high-resolution-preview"]:visible').first
                assert sharp_button.get_attribute("aria-pressed") == "true"
                sharp_button.click()
                assert sharp_button.get_attribute("aria-pressed") == "false"
                assert page.locator('img[data-testid="high-resolution-still-preview"]:visible').count() == 0
                sharp_button.click()
                assert sharp_button.get_attribute("aria-pressed") == "true"
                page.wait_for_function("""() => {
                    const image = [...document.querySelectorAll('img[data-testid="high-resolution-still-preview"]')]
                        .find(node => node.getBoundingClientRect().width > 0);
                    return image && image.complete && image.naturalWidth === 1080
                        && image.naturalHeight === 1920;
                }""", timeout=15000)
                sharp_image = page.locator('img[data-testid="high-resolution-still-preview"]:visible').first
                sharp_live = Path(temp_root) / "high_resolution_live.png"
                capture_ms = int(sharp_image.get_attribute("data-capture-duration-ms"))
                encoded_bytes = int(sharp_image.get_attribute("data-capture-encoded-bytes"))
                assert 0 < capture_ms < 15000
                assert encoded_bytes > 0
                print(f"1080p paused preview capture: {capture_ms} ms, {encoded_bytes / 1024:.1f} KiB PNG")
                sharp_live.write_bytes(base64.b64decode(sharp_image.evaluate(
                    "node => node.src.slice(node.src.indexOf(',') + 1)"
                )))
                ruler = page.locator('[title="คลิกหรือลากเพื่อเลื่อนหัวอ่าน"]:visible').first
                tick = ruler.locator(':scope > div').nth(1)
                tick_timecode = tick.inner_text().strip()
                minutes, seconds = tick_timecode.split(':')
                tick_seconds = int(minutes) * 60 + float(seconds)
                px_per_second = float(tick.evaluate("node => parseFloat(node.style.left)")) / tick_seconds

                live_frames = []
                for index, sample_time in enumerate(sample_times):
                    if sample_time:
                        # Shift bypasses scrub snapping: these samples sit a frame either
                        # side of a cut and must land exactly there, not on the cut.
                        ruler.click(position={"x": sample_time * px_per_second, "y": 10}, modifiers=["Shift"])
                    active_index = 1 if (with_fade and sample_time >= 0.7) or (with_split and sample_time >= 0.5) else 0
                    active_source_time = (sample_time - 0.3) if with_fade and active_index else (0.5 + sample_time)
                    page.wait_for_function("""({variant, elementIndex, expected}) => {
                    const canvas = [...document.querySelectorAll('canvas[width="540"][height="960"]')]
                        .find(node => node.getBoundingClientRect().width > 0);
                    const video = [...document.querySelectorAll('video')]
                        .filter(node => node.currentSrc.includes(`clip_source_${variant}_`))[elementIndex];
                    return canvas && video && video.readyState >= 2 && !video.seeking
                        && Math.abs(video.currentTime - expected) < 0.05
                        && canvas.getContext('2d').getImageData(100, 100, 1, 1).data[3] > 0;
                    }""", arg={
                        "variant": 2 if with_fade and active_index else 0,
                        "elementIndex": active_index if with_split else 0,
                        "expected": active_source_time,
                    }, timeout=10000)
                    live = Path(temp_root) / f"live_{index:02d}.png"
                    live.write_bytes(base64.b64decode(canvas.evaluate(
                        "node => node.toDataURL('image/png').split(',')[1]"
                    )))
                    live_frames.append(live)
                assert not page_errors, page_errors
            finally:
                browser.close()

        rendered = root / "rendered.mp4"
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(source) for source in sources],
            total_duration=1.5,
            mixed_audio_path=str(create_silent_audio(root)),
            ass_subtitle_path=str(create_empty_ass(root)),
            output_mp4_path=str(rendered),
            clip_list=[
                {**clip, "source_path": str(sources[1] if with_fade and index == 1 else sources[0])}
                for index, clip in enumerate(manifest["clip_list"])
            ],
            transitions=manifest["transitions"],
            export_preset="post",
            style_preset="clean_tech_review",
        )
        rendered_frames = _render_frames(rendered, root, sample_times)
        for index, (live, rendered_frame) in enumerate(zip(live_frames, rendered_frames, strict=True)):
            composited = root / f"live_composited_{index:02d}.png"
            _composite_canvas_frame(live, composited, "0x000000")
            comparison = compare_frames(composited, rendered_frame).to_dict()
            assert comparison["passed"], f"t={sample_times[index]}: {json.dumps(comparison, ensure_ascii=False)}"

        sharp_rendered_frames = _render_frames(
            rendered, root / "sharp_render", (sample_times[0],), size=(1080, 1920),
        )
        sharp_comparison = compare_frames(sharp_live, sharp_rendered_frames[0]).to_dict()
        assert sharp_comparison["passed"], (
            f"1080p paused preview: {json.dumps(sharp_comparison, ensure_ascii=False)}"
        )
