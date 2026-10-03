"""Master1080 playback, source switching and full-resolution FFmpeg parity."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from urllib.parse import urlencode, urlsplit
import wave

import pytest
from playwright.sync_api import sync_playwright

from scripts.video_editor import VideoEditor
from tests.motion_capture.ass_fixture import compare_frames
from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import _render_frames
from tests.motion_capture.frame_pair import _composite_canvas_frame
from tests.motion_capture.overlay_pair import create_empty_ass, vite_fs_url


def _source(root: Path, *, landscape: bool, animated: bool = True) -> Path:
    width, height = (1920, 1080) if landscape else (1080, 1920)
    path = root / f"master_{width}x{height}.mp4"
    subprocess.run([
        shutil.which("ffmpeg") or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"{'testsrc2' if animated else 'smptebars'}=size={width}x{height}:rate=30:duration=4",
        "-vf", "drawgrid=w=8:h=8:t=1:c=white@0.2",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14", "-pix_fmt", "yuv420p", str(path),
    ], check=True, capture_output=True)
    return path


def _serve_video(route, path: Path):
    payload = path.read_bytes()
    requested = re.match(r"bytes=(\d+)-(\d*)", route.request.headers.get("range", ""))
    if not requested:
        route.fulfill(status=200, body=payload, content_type="video/mp4", headers={"Accept-Ranges": "bytes"})
        return
    start = int(requested.group(1))
    end = min(int(requested.group(2) or len(payload) - 1), len(payload) - 1)
    route.fulfill(status=206, body=payload[start:end + 1], content_type="video/mp4",
                  headers={"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{len(payload)}"})


@pytest.mark.parametrize("transition", ["cut", "circleopen", "dissolve"])
def test_master1080_stays_sharp_while_playing_and_matches_render(motion_fixture_url, monkeypatch, transition):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("high-resolution-playback-") as temporary:
        root = Path(temporary)
        # Static fine details isolate spatial/transition parity from wall-clock
        # decoder scheduling; the separate performance probe uses moving testsrc2.
        sources = [_source(root, landscape=False, animated=False), _source(root, landscape=True, animated=False)]
        configs = [
            {"trim_start": 0.1, "trim_end": 2.3, "speed": 1, "zoom": 1.08},
            {"trim_start": 0.1, "trim_end": 2.3, "speed": 1, "transition_in": transition,
             "transition_duration": 0.5, "mirror": True},
        ]
        query = urlencode({
            "mode": "clips", "duration": 4.4, "previewQuality": "master1080",
            "clip": vite_fs_url(base_url, sources[0]), "clip2": vite_fs_url(base_url, sources[1]),
            "clipConfig": json.dumps(configs[0]), "clip2Config": json.dumps(configs[1]),
        })
        captures = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1080, "height": 1100}, ignore_https_errors=True)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                started = perf_counter()
                page.goto(f"{base_url}/motion_capture.html?{query}", wait_until="domcontentloaded")
                preview = page.get_by_test_id("motion-capture-sequence-player")
                preview.wait_for(state="attached", timeout=20000)
                canvas = preview.get_by_test_id("sequence-preview-canvas")
                play = preview.get_by_role("button", name="เล่นพรีวิว", exact=True)
                play.wait_for(timeout=20000)
                page.wait_for_function("Array.from(document.querySelectorAll('video')).every(v => v.readyState >= 2)")
                ready_ms = (perf_counter() - started) * 1000
                assert canvas.evaluate("c => [c.width,c.height]") == [1080, 1920]
                assert preview.locator('video[data-preview-source="master"]').count() == 2
                play.click()
                # Capture before the boundary, in its overlap, then after it.
                for target in (0.6, 1.95, 2.9):
                    page.wait_for_function("""t => {
                        const c = document.querySelector('[data-testid=sequence-preview-canvas]');
                        const time = Number(c?.dataset.previewTime);
                        if (!(time >= t)) return false;
                        window.highPreviewSample = {time,playing:c.dataset.previewPlaying,width:c.width,height:c.height,
                            data:c.toDataURL('image/png'),source:Array.from(document.querySelectorAll('video')).map(v=>({url:v.currentSrc,w:v.videoWidth,h:v.videoHeight,time:v.currentTime,seeking:v.seeking}))};
                        return true;
                    }""", arg=target)
                    result = page.evaluate("window.highPreviewSample")
                    if target == 1.95 and transition != "cut":
                        assert 1.7 <= result["time"] < 2.2, "sample must exercise the real transition overlap"
                    assert result["playing"] == "true", "sample must be taken during real playback"
                    assert [result["width"], result["height"]] == [1080, 1920]
                    assert result["source"][0]["w"] == 1080 and result["source"][1]["w"] == 1920
                    capture = root / f"canvas_{len(captures)}.png"
                    capture.write_bytes(base64.b64decode(result["data"].split(",", 1)[1]))
                    captures.append((result["time"], capture))
                # Changing mode during playback keeps the timeline moving.
                quality = page.get_by_test_id("preview-quality-select")
                before = float(canvas.get_attribute("data-preview-time"))
                quality.select_option("smooth540")
                assert canvas.evaluate("c => [c.width,c.height]") == [540, 960]
                page.wait_for_function("t => Number(document.querySelector('[data-testid=sequence-preview-canvas]').dataset.previewTime) > t + .1", arg=before)
                quality.select_option("master1080")
                assert canvas.evaluate("c => [c.width,c.height]") == [1080, 1920]
                assert canvas.get_attribute("data-preview-playing") == "true"
                assert not errors, errors
                print(json.dumps({"transition": transition, "ready_ms": round(ready_ms, 1),
                                  "playing_samples": [round(t, 3) for t, _ in captures]}))
            finally:
                browser.close()

        audio = root / "silent.wav"
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(48000)
            stream.writeframes(b'\0' * int(4.4 * 48000) * 2)
        subtitles = create_empty_ass(root)
        output = root / "post.mp4"
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(path) for path in sources], total_duration=4.4,
            mixed_audio_path=str(audio), ass_subtitle_path=str(subtitles), output_mp4_path=str(output),
            clip_list=[{"source_path": str(path), **config} for path, config in zip(sources, configs)],
            transitions=[{"type": transition, "duration": 0.5}],
            export_preset="post",
        )
        rendered = _render_frames(output, root / "rendered", tuple(t for t, _ in captures), size=(1080, 1920))
        for (timestamp, capture), reference in zip(captures, rendered):
            live_rgb = capture.with_name(capture.stem + "_rgb.png")
            _composite_canvas_frame(capture, live_rgb, "0x000000")
            # Dissolve contains single-pixel colour changes. Export's YUV420
            # chroma subsampling changes those colours; compare the same colour
            # format, while the independent monochrome mask test checks pixels.
            if transition == "dissolve":
                encoded_rgb = live_rgb.with_name(live_rgb.stem + "_yuv420.png")
                subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(live_rgb),
                                "-vf", "format=yuv420p,format=rgb24", "-frames:v", "1", str(encoded_rgb)],
                               check=True, capture_output=True)
                live_rgb = encoded_rgb
            result = compare_frames(live_rgb, reference)
            print("FRAME_ERROR " + json.dumps({"transition":transition,"time":round(timestamp,3),
                                              "mae":result.mean_abs_error,"colour_format":"YUV420 normalized" if transition=="dissolve" else "RGB"}))
            assert result.mean_abs_error < 0.08, (transition, timestamp, result)


def test_proxy_source_is_only_used_in_smooth_mode(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("high-resolution-proxy-") as temporary:
        root = Path(temporary)
        source = _source(root, landscape=False)
        proxy = root / "proxy.mp4"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
                        "-vf", "scale=540:960", "-c:v", "libx264", "-preset", "ultrafast", str(proxy)],
                       check=True, capture_output=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
                page.route("**/api/media/high-master.mp4", lambda route: _serve_video(route, source))
                page.route("**/api/media/high-proxy.mp4", lambda route: _serve_video(route, proxy))
                requests = []
                def serve_proxy(route):
                    requests.append(route.request.url)
                    route.fulfill(content_type="application/json", body=json.dumps({
                        "url": "/api/media/high-proxy.mp4", "is_proxy": True, "status": "ready",
                    }))
                page.route("**/api/proxy/for-clip?**", serve_proxy)
                query = urlencode({"clipCount": 1, "mediaClip": "/api/media/high-master.mp4", "mediaDuration": 4,
                                   "previewQuality": "master1080"})
                page.goto(f"{base_url}/editor_controls.html?{query}")
                preview = page.get_by_test_id("real-media-preview")
                quality = preview.get_by_test_id("preview-quality-select")
                quality.wait_for(timeout=20000)
                video = preview.locator("video").first
                assert "high-master.mp4" in video.get_attribute("src")
                assert not requests, "Master mode should not start expensive proxy jobs"
                slider = preview.get_by_role("slider", name="เลื่อนตำแหน่งเล่นวิดีโอ")
                slider.fill("1.2")
                quality.select_option("smooth540")
                page.wait_for_function("document.querySelector('[data-testid=real-media-preview] video').currentSrc.includes('high-proxy.mp4')")
                try:
                    page.wait_for_function("Math.abs(document.querySelector('[data-testid=real-media-preview] video').currentTime-1.2)<.08", timeout=10000)
                except Exception:
                    print(page.evaluate("""() => { const v=document.querySelector('[data-testid=real-media-preview] video');
                        return {time:v.currentTime,duration:v.duration,seeking:v.seeking,ready:v.readyState,error:v.error?.message,
                            canvas:document.querySelector('[data-testid=real-media-preview] canvas').dataset.previewTime}; }"""))
                    raise
                assert video.get_attribute("data-preview-source") == "proxy"
                quality.select_option("master1080")
                page.wait_for_function("document.querySelector('[data-testid=real-media-preview] video').currentSrc.includes('high-master.mp4')")
                page.wait_for_function("Math.abs(document.querySelector('[data-testid=real-media-preview] video').currentTime-1.2)<.08")
                assert video.get_attribute("data-preview-source") == "master"
                assert page.evaluate("localStorage.getItem('omnicut.previewQuality')") == "master1080"
            finally:
                browser.close()


def test_high_resolution_playback_performance_probe(motion_fixture_url):
    """Bounded synthetic timing; heap metrics do not include total browser/GPU RAM."""
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("high-resolution-timing-") as temporary:
        root = Path(temporary)
        sources = [_source(root, landscape=False), _source(root, landscape=True)]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for quality in ("smooth540", "master1080"):
                    page = browser.new_page(viewport={"width": 1080, "height": 1100}, ignore_https_errors=True)
                    page.add_init_script("""(() => {
                        const raf = window.requestAnimationFrame.bind(window);
                        window.previewProbe = [];
                        window.requestAnimationFrame = callback => raf(timestamp => {
                            const c = document.querySelector('[data-testid=sequence-preview-canvas]');
                            const before = c?.dataset.previewTime;
                            const start = performance.now();
                            callback(timestamp);
                            if (c?.dataset.previewPlaying === 'true' && before !== c.dataset.previewTime) {
                                window.previewProbe.push({at:start,paintMs:performance.now()-start,time:Number(c.dataset.previewTime)});
                            }
                        });
                    })()""")
                    query = urlencode({"mode": "clips", "duration": 4.4, "previewQuality": quality,
                                       "clip": vite_fs_url(base_url, sources[0]), "clip2": vite_fs_url(base_url, sources[1]),
                                       "clipConfig": json.dumps({"trim_end": 2.2}),
                                       "clip2Config": json.dumps({"trim_end": 2.2, "transition_in": "circleopen", "transition_duration": .5})})
                    started = perf_counter()
                    page.goto(f"{base_url}/motion_capture.html?{query}", wait_until="domcontentloaded")
                    stage = page.get_by_test_id("motion-capture-sequence-player")
                    stage.wait_for(state="attached", timeout=20000)
                    play = page.get_by_role("button", name="เล่นพรีวิว", exact=True)
                    play.wait_for(timeout=20000)
                    page.wait_for_function("Array.from(document.querySelectorAll('video')).every(v => v.readyState >= 2)")
                    ready_ms = (perf_counter() - started) * 1000
                    # Seek decoder and backing Canvas at a representative point.
                    started = perf_counter()
                    page.evaluate("window.motionCapture.capture({frameIndex:18})")
                    seek_ms = (perf_counter() - started) * 1000
                    play.click()
                    page.wait_for_function("Number(document.querySelector('[data-testid=sequence-preview-canvas]').dataset.previewTime)>3.8")
                    measurements = page.evaluate("""() => {
                        const samples = window.previewProbe.filter(p=>p.time>.8&&p.time<3.8);
                        const percentile = (xs,p) => xs.slice().sort((a,b)=>a-b)[Math.min(xs.length-1,Math.floor(xs.length*p))];
                        const gaps = samples.slice(1).map((p,i)=>p.at-samples[i].at);
                        return {samples:samples.length, paint_p50_ms:percentile(samples.map(p=>p.paintMs),.5),
                            paint_p95_ms:percentile(samples.map(p=>p.paintMs),.95),
                            callback_gap_p95_ms:percentile(gaps,.95),gap_over_50ms:gaps.filter(x=>x>50).length,
                            video_quality:[...document.querySelectorAll('video')].map(v=>{
                                const q=v.getVideoPlaybackQuality(); return {width:v.videoWidth,height:v.videoHeight,
                                    decoded_frames:q.totalVideoFrames,dropped_frames:q.droppedVideoFrames};}),
                            js_heap_bytes:performance.memory?.usedJSHeapSize??null,
                            backing_dimensions:[...document.querySelectorAll('[data-testid=sequence-preview-canvas]')].map(c=>[c.width,c.height])};
                    }""")
                    measurements.update({"quality": quality, "ready_ms": round(ready_ms, 1), "seek_ms": round(seek_ms, 1),
                                         "main_rgba_surface_bytes": 540 * 960 * 4 * (4 if quality == "master1080" else 1),
                                         "memory_scope": "JS heap measured; RGBA surface calculated; decoder/GPU/total RAM not measured"})
                    print("PREVIEW_PERFORMANCE " + json.dumps(measurements))
                    assert measurements["samples"] >= 30
                    assert measurements["paint_p95_ms"] < 100, measurements
                    page.close()
            finally:
                browser.close()


def test_dissolve_mask_matches_ffmpeg_export_pixels(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("high-resolution-dissolve-") as temporary:
        root = Path(temporary)
        reference = root / "ffmpeg.png"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30:d=2",
                        "-f", "lavfi", "-i", "color=white:s=1080x1920:r=30:d=2",
                        "-filter_complex", "[0:v][1:v]xfade=transition=dissolve:duration=1:offset=1,format=rgb24",
                        "-ss", "1.5", "-frames:v", "1", str(reference)], check=True, capture_output=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(ignore_https_errors=True)
                page.goto(f"{base_url}/motion_capture.html", wait_until="domcontentloaded")
                data = page.evaluate("""async () => {
                    const {dissolveMaskFor}=await import('/src/components/SequencePlayer.jsx');
                    return dissolveMaskFor(.5,2).toDataURL('image/png').split(',')[1];
                }""")
                mask = root / "mask.png"
                mask.write_bytes(base64.b64decode(data))
                live = root / "mask_rgb.png"
                _composite_canvas_frame(mask, live, "0x000000")
                comparison = compare_frames(live, reference)
                print("DISSOLVE_MASK_ERROR", comparison.mean_abs_error)
                assert comparison.mean_abs_error < .01
            finally:
                browser.close()
