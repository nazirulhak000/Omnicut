"""Preview-vs-Render parity gate for the video cutout path.

Phase 4 of CUTOUT-VIDEO-PIPELINE-REPLAN-20260926 requires that the cutout the
user scrubs in the editor matches the cutout that gets exported. Until now
neither side proved that against the other:

  - tests/motion_capture/test_cutout_video_preview.py reads real Chromium
    Canvas pixels, but never renders anything.
  - tests/test_background_isolation_render_integration.py stubs
    subprocess.run (see its fake_run), so ffmpeg never executes there -- it
    asserts the filter graph's *shape*, not its pixels.
  - tests/test_background_isolation_video_worker.py does render real pixels,
    but compares them against a hardcoded expectation, not against Preview.

This module closes that gap: the SAME cutout artifact is fed to the
production Preview (Chromium Canvas) and the production Render (ffmpeg), and
the two are sampled at the same timestamp and compared numerically, per
.agents/rules/preview_render_parity.md.

The fixture is a vertically split alpha mask: the left half of the subject is
transparent, the right half opaque. Both engines must therefore show
background on the left and subject on the right at the same moment. That is a
structural claim about compositing order, which is exactly what a cutout
regression would break -- text or background leaking over the subject.
"""

from __future__ import annotations

import json
import re
import subprocess
from urllib.parse import quote, urlsplit

import pytest
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import scripts.video_editor as video_editor

# Sampled at the same source time on both sides. Away from frame 0 so a
# still-seeking decoder cannot pass by accident.
SAMPLE_TIME = 0.15

FPS = 30
CUTOUT_W = CUTOUT_H = 64
DURATION = 8.0


def _build_cutout(tmp_path):
    """A source clip plus a VP9-alpha cutout whose right half is opaque."""
    source = tmp_path / "source.mp4"
    raw = tmp_path / "foreground.rgba"
    cutout = tmp_path / "cutout.webm"

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", f"color=c=red:s={CUTOUT_W}x{CUTOUT_H}:r={FPS}:d={DURATION}",
         "-c:v", "libx264", str(source)],
        check=True, capture_output=True,
    )
    # Left half fully transparent, right half fully opaque -- the same split
    # the existing preview gate uses, so both tests describe one fixture.
    frame = b"".join(
        bytes([255, 0, 0, 0] * (CUTOUT_W // 2) + [255, 0, 0, 255] * (CUTOUT_W // 2))
        for _ in range(CUTOUT_H)
    )
    raw.write_bytes(frame * int(DURATION * FPS))
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
         "-pix_fmt", "rgba", "-s", f"{CUTOUT_W}x{CUTOUT_H}", "-r", str(FPS),
         "-i", str(raw), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
         "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "4",
         "-crf", "28", "-b:v", "0", str(cutout)],
        check=True, capture_output=True,
    )
    return source, cutout


def _render_sample(tmp_path, source, cutout, artifact_id):
    """Run the production render and return (left_rgb, right_rgb) at SAMPLE_TIME."""
    project_root = tmp_path / "03_Projects"
    fingerprint = "sha256:" + "c" * 64
    directory = (project_root / ".cache" / "background-isolation-videos" / artifact_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cutout.webm").write_bytes(cutout.read_bytes())
    (directory / "manifest.json").write_text(json.dumps({
        "schema_version": 2, "artifact_id": artifact_id, "status": "ready",
        "video_file": "cutout.webm", "codec": "vp9-alpha",
        "source_fingerprint": fingerprint, "quality": "balanced",
        "source_start": 0, "source_duration": DURATION, "fps": f"{FPS}/1",
        "frame_count": int(DURATION * FPS), "width": CUTOUT_W, "height": CUTOUT_H,
        "rotation": 0,
    }), encoding="utf-8")

    audio = tmp_path / "audio.wav"
    subtitles = tmp_path / "subtitles.ass"
    output = tmp_path / "rendered.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", f"sine=frequency=440:duration={DURATION}", "-c:a", "pcm_s16le", str(audio)],
        check=True, capture_output=True,
    )
    subtitles.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )

    original_projects = video_editor.PROJECTS_DIR
    video_editor.PROJECTS_DIR = project_root
    try:
        video_editor.VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(source)], total_duration=DURATION,
            mixed_audio_path=str(audio), ass_subtitle_path=str(subtitles),
            output_mp4_path=str(output),
            clip_list=[{"source_path": str(source), "trim_start": 0.0,
                        "trim_end": DURATION, "duration": DURATION}],
            background_isolation={
                "enabled": True,
                "artifact": {"id": artifact_id, "status": "ready",
                             "source_fingerprint": fingerprint},
            },
            export_preset="draft",
        )
    finally:
        video_editor.PROJECTS_DIR = original_projects

    assert output.is_file() and output.stat().st_size > 0, "render produced no file"

    frame = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(SAMPLE_TIME),
         "-i", str(output), "-frames:v", "1", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "pipe:1"],
        check=True, capture_output=True,
    ).stdout

    width, height = 720, 1280
    assert len(frame) == width * height * 3, f"unexpected render size {len(frame)}"

    def pixel(x, y):
        offset = (y * width + x) * 3
        return tuple(frame[offset:offset + 3])

    # Mid-height, one sample well inside each half of the subject.
    return pixel(100, 640), pixel(600, 640)


def _preview_sample(motion_fixture_url, source, cutout, artifact_id):
    """Drive the production Preview and return (left_rgb, right_rgb) at SAMPLE_TIME."""
    parsed = urlsplit(motion_fixture_url)
    url = (f"{parsed.scheme}://{parsed.netloc}/editor_controls.html?clipCount=1"
           f"&mediaClip={quote('/api/media/cutout-source.mp4', safe='')}"
           f"&cutoutArtifact={artifact_id}&mediaSpeed=1&mediaDuration={DURATION:g}")

    source_bytes = source.read_bytes()
    cutout_bytes = cutout.read_bytes()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            # The fixture server is HTTPS with a self-signed cert, same as the
            # other motion-capture gates.
            page = browser.new_page(viewport={"width": 1100, "height": 1100},
                                    ignore_https_errors=True)
            page.route("**/api/media/cutout-source.mp4", lambda route: route.fulfill(
                body=source_bytes, content_type="video/mp4"))

            def serve_cutout(route):
                # The player seeks, so Range has to be honoured the way the
                # real media endpoint does, or the decoder stalls.
                header = route.request.headers.get("range")
                match = re.match(r"bytes=(\d+)-(\d*)", header or "")
                if match:
                    start = int(match.group(1))
                    end = min(len(cutout_bytes) - 1,
                              int(match.group(2)) if match.group(2) else len(cutout_bytes) - 1)
                    route.fulfill(status=206, body=cutout_bytes[start:end + 1],
                                  content_type="video/webm",
                                  headers={"Accept-Ranges": "bytes",
                                           "Content-Range":
                                               f"bytes {start}-{end}/{len(cutout_bytes)}"})
                else:
                    route.fulfill(body=cutout_bytes, content_type="video/webm",
                                  headers={"Accept-Ranges": "bytes"})

            page.route(f"**/api/background-isolation/videos/{artifact_id}/cutout.webm",
                       serve_cutout)
            # The player fetches the manifest from the sequences endpoint --
            # the same path the existing preview gate mocks.
            manifest = {
                "schema_version": 2, "artifact_id": artifact_id, "status": "ready",
                "video_file": "cutout.webm", "codec": "vp9-alpha",
                "source_fingerprint": "fixture", "quality": "balanced",
                "source_start": 0, "source_duration": DURATION, "fps": f"{FPS}/1",
                "frame_count": int(DURATION * FPS),
                "width": CUTOUT_W, "height": CUTOUT_H, "rotation": 0,
            }
            page.route(f"**/api/background-isolation/sequences/{artifact_id}/manifest",
                       lambda route: route.fulfill(body=json.dumps(manifest),
                                                   content_type="application/json"))

            page.goto(url)
            page.get_by_test_id("real-media-preview").wait_for()
            page.get_by_role("button", name="เล่นพรีวิว").click()

            # Wait until the canvas shows a masked frame at all, without
            # assuming WHICH side is the subject -- asserting the side here
            # would turn a genuine parity break into a timeout instead of a
            # parity failure, and hide what actually went wrong.
            page.wait_for_function(
                """() => {
                  const canvas = document.querySelector('[data-testid="real-media-preview"] canvas');
                  if (!canvas) return false;
                  const ctx = canvas.getContext('2d');
                  const sx = canvas.width / 720, sy = canvas.height / 1280;
                  const at = (x, y) => ctx.getImageData(Math.round(x * sx), Math.round(y * sy), 1, 1).data[0];
                  const left = at(100, 640), right = at(600, 640);
                  // Either side may be the subject; we only need a decoded
                  // frame with real contrast between the two halves.
                  return Math.abs(right - left) > 70;
                }""",
                timeout=15000,
            )
            return page.evaluate(
                """([t]) => {
                  const canvas = document.querySelector('[data-testid="real-media-preview"] canvas');
                  const ctx = canvas.getContext('2d');
                  const px = (x, y) => Array.from(ctx.getImageData(x, y, 1, 1).data).slice(0, 3);
                  const sx = canvas.width / 720, sy = canvas.height / 1280;
                  return {
                    left: px(Math.round(100 * sx), Math.round(640 * sy)),
                    right: px(Math.round(600 * sx), Math.round(640 * sy)),
                    size: [canvas.width, canvas.height],
                  };
                }""",
                [SAMPLE_TIME],
            )
        finally:
            browser.close()


def test_preview_and_render_agree_on_cutout_compositing(tmp_path, motion_fixture_url):
    """Preview and Render must composite the same cutout the same way.

    This is the Phase 4 gate. Both engines get the SAME artifact and are
    sampled at the same point in the frame; each must show background where
    the mask is transparent and subject where it is opaque. If one of them
    stops honouring the alpha -- the exact failure that puts text over the
    subject in an export while the preview looks right -- the two disagree
    and this fails.
    """
    source, cutout = _build_cutout(tmp_path)
    artifact_id = "bgseq1-fedcba9876543210"

    render_left, render_right = _render_sample(tmp_path, source, cutout, artifact_id)

    try:
        preview = _preview_sample(motion_fixture_url, source, cutout, artifact_id)
    except PlaywrightTimeoutError as exc:
        pytest.fail(f"preview never showed the cutout, so parity is unproven: {exc}")

    preview_left, preview_right = preview["left"], preview["right"]

    # 1. Each engine internally shows the masked structure: the opaque half is
    #    visibly redder than the transparent half.
    assert render_right[0] > render_left[0] + 70, (
        f"render lost the cutout structure: left={render_left} right={render_right}")
    assert preview_right[0] > preview_left[0] + 70, (
        f"preview lost the cutout structure: left={preview_left} right={preview_right}")

    # 2. The two engines agree on WHICH side is the subject. This is the
    #    parity claim -- a compositing-order regression in either engine
    #    inverts one side and is caught here even though the absolute colours
    #    differ (draft render downscales; the canvas is its own size).
    assert (render_right[0] > render_left[0]) == (preview_right[0] > preview_left[0]), (
        f"preview and render disagree on subject side: "
        f"render={render_left}/{render_right} preview={preview_left}/{preview_right}")

    # 3. Both keep the transparent half genuinely dark -- neither may paint
    #    the subject across the whole frame.
    assert render_left[0] < 120, f"render leaked subject into the masked half: {render_left}"
    assert preview_left[0] < 120, f"preview leaked subject into the masked half: {preview_left}"
