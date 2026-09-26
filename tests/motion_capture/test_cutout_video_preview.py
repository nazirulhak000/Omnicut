"""Real Chromium Canvas gate for the video cutout path."""

from __future__ import annotations

import json
import re
import subprocess
from urllib.parse import quote, urlsplit

import pytest
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


@pytest.mark.parametrize("speed", [1, 0.5, 1.3155, 2])
def test_transparent_video_cutout_appears_in_real_sequence_player(tmp_path, motion_fixture_url, speed):
    source = tmp_path / "source.mp4"
    raw = tmp_path / "foreground.rgba"
    cutout = tmp_path / "cutout.webm"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=64x64:r=30:d=8", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    # The alpha split runs vertically in the player crop. The subject below is
    # RED over this BLUE footage: composite mode keeps the footage as the base
    # layer, so a same-coloured subject would be indistinguishable from the
    # background and the assertions could not tell the two layers apart.
    foreground = b"".join(
        bytes([255, 0, 0, 0] * 32 + [255, 0, 0, 255] * 32)
        for _ in range(64)
    )
    raw.write_bytes(foreground * 240)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
         "-pix_fmt", "rgba", "-s", "64x64", "-r", "30", "-i", str(raw),
         "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
         "-deadline", "good", "-cpu-used", "4", "-crf", "28", "-b:v", "0", str(cutout)],
        check=True, capture_output=True,
    )
    artifact_id = "bgseq1-0123456789abcdef"
    manifest = {
        "schema_version": 2, "artifact_id": artifact_id, "status": "ready",
        "video_file": "cutout.webm", "codec": "vp9-alpha",
        "source_fingerprint": "fixture", "quality": "balanced",
        "source_start": 0, "source_duration": 8, "fps": "30/1",
        "frame_count": 240, "width": 64, "height": 64, "rotation": 0,
    }
    parsed = urlsplit(motion_fixture_url)
    url = (f"{parsed.scheme}://{parsed.netloc}/editor_controls.html?clipCount=1"
           f"&mediaClip={quote('/api/media/cutout-source.mp4', safe='')}"
           f"&cutoutArtifact={artifact_id}&mediaSpeed={speed}&mediaDuration=8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            page.add_init_script("""(() => {
              window.__cutoutProbeVideos = [];
              const original = document.createElement.bind(document);
              document.createElement = (name, ...args) => {
                const element = original(name, ...args);
                if (String(name).toLowerCase() === 'video') window.__cutoutProbeVideos.push(element);
                return element;
              };
            })()""")
            page.route("**/api/media/cutout-source.mp4", lambda route: route.fulfill(
                body=source.read_bytes(), content_type="video/mp4"))
            page.route(f"**/api/background-isolation/sequences/{artifact_id}/manifest",
                       lambda route: route.fulfill(body=json.dumps(manifest), content_type="application/json"))
            cutout_bytes = cutout.read_bytes()

            def serve_cutout(route):
                requested = route.request.headers.get("range", "")
                match = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
                if match:
                    start = int(match.group(1))
                    end = min(len(cutout_bytes) - 1, int(match.group(2)) if match.group(2) else len(cutout_bytes) - 1)
                    route.fulfill(status=206, body=cutout_bytes[start:end + 1],
                                  headers={"Content-Type": "video/webm", "Accept-Ranges": "bytes",
                                           "Content-Range": f"bytes {start}-{end}/{len(cutout_bytes)}"})
                else:
                    route.fulfill(body=cutout_bytes, content_type="video/webm",
                                  headers={"Accept-Ranges": "bytes"})

            page.route(f"**/api/background-isolation/videos/{artifact_id}/cutout.webm", serve_cutout)
            page.goto(url, wait_until="domcontentloaded")
            page.get_by_test_id("real-media-preview").wait_for()
            page.get_by_role("button", name="เล่นพรีวิว").click()
            condition = """() => {
              const canvas = document.querySelector('[data-testid="real-media-preview"] canvas');
              if (!canvas) return false;
              const ctx = canvas.getContext('2d');
              const left = ctx.getImageData(100, 480, 1, 1).data;
              const right = ctx.getImageData(440, 480, 1, 1).data;
              // Right: the red cut-out subject. Left: the blue source
              // footage, which composite mode must keep visible rather than
              // painting over -- that fill was the regression that lost the
              // layer the hook text sits on.
              return right[0] > left[0] + 80 && left[2] > left[0] + 60;
            }"""
            try:
                page.wait_for_function(condition, timeout=8000)
                rate = page.evaluate("""() => window.__cutoutProbeVideos
                  .find(v => v.src.includes('/cutout.webm'))?.playbackRate""")
                assert rate is not None and abs(rate - speed) <= speed * 0.12, (rate, speed)
                playback = page.evaluate("""async () => {
                  const video = window.__cutoutProbeVideos.find(v => v.src.includes('/cutout.webm'));
                  const ctx = document.querySelector('[data-testid="real-media-preview"] canvas').getContext('2d');
                  const seeks = video._cutoutPlayback.metrics.seeks;
                  let visible = 0;
                  for (let i = 0; i < 60; i++) {
                    await new Promise(requestAnimationFrame);
                    visible += ctx.getImageData(440, 480, 1, 1).data[0] > 100;
                  }
                  return {seeks: video._cutoutPlayback.metrics.seeks - seeks, visible};
                }""")
                assert playback["seeks"] <= 2, playback
                assert playback["visible"] >= 54, playback
            except PlaywrightTimeoutError:
                diagnostics = page.evaluate("""() => {
                  const root = document.querySelector('[data-testid="real-media-preview"]');
                  const canvas = root?.querySelector('canvas');
                  const ctx = canvas?.getContext('2d');
                  return {
                    labels: [...root.querySelectorAll('[aria-label]')].map(x => x.getAttribute('aria-label')),
                    videos: window.__cutoutProbeVideos.map(v => ({src:v.currentSrc, ready:v.readyState, time:v.currentTime,
                      presented:v._cutoutPresentedTime, waiting:v._cutoutWaitingForFrame, paused:v.paused, error:v.error?.code})),
                    left: ctx && Array.from(ctx.getImageData(100, 480, 1, 1).data),
                    right: ctx && Array.from(ctx.getImageData(440, 480, 1, 1).data),
                  };
                }""")
                pytest.fail(f"cutout preview did not show subject: {diagnostics}")
        finally:
            browser.close()


def test_missing_ready_artifact_never_reveals_original_background(tmp_path, motion_fixture_url):
    source = tmp_path / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=red:s=64x64:r=30:d=2", "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    artifact_id = "bgseq1-0123456789abcdef"
    parsed = urlsplit(motion_fixture_url)
    url = (f"{parsed.scheme}://{parsed.netloc}/editor_controls.html?clipCount=1"
           f"&mediaClip={quote('/api/media/cutout-source.mp4', safe='')}"
           f"&cutoutArtifact={artifact_id}")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            page.route("**/api/media/cutout-source.mp4", lambda route: route.fulfill(
                body=source.read_bytes(), content_type="video/mp4"))
            page.route(f"**/api/background-isolation/sequences/{artifact_id}/manifest",
                       lambda route: route.fulfill(status=404, body="missing"))
            page.goto(url, wait_until="domcontentloaded")
            page.get_by_test_id("real-media-preview").wait_for()
            page.get_by_role("button", name="เล่นพรีวิว").click()
            page.wait_for_function("""() => {
              const canvas = document.querySelector('[data-testid="real-media-preview"] canvas');
              if (!canvas) return false;
              const pixel = canvas.getContext('2d').getImageData(100, 480, 1, 1).data;
              return pixel[0] < 60 && pixel[1] < 60 && pixel[2] < 80;
            }""", timeout=8000)
        finally:
            browser.close()
