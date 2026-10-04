"""Bounded real SequencePlayer media-clock probe; not physical speaker AV sync."""
from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import statistics
import struct
import subprocess
from time import perf_counter
from urllib.parse import urlencode, urlsplit
import wave

from playwright.sync_api import sync_playwright

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.overlay_pair import vite_fs_url


def _source(root: Path, variant: int) -> Path:
    path = root / f"distinct-source-{variant}.mp4"
    command = [shutil.which("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
               "-f", "lavfi", "-i", f"testsrc2=size=540x960:rate=30:duration=4",
               "-vf", f"hue=h={variant * 100}", "-an", "-c:v", "libx264",
               "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(command, check=True, capture_output=True, timeout=20)
    return path


def _summary(samples: list[dict]) -> dict:
    def metric(values):
        ordered = sorted(values)
        return {"median_ms": round(statistics.median(ordered) * 1000, 2),
                "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))] * 1000, 2),
                "max_ms": round(max(ordered) * 1000, 2)}
    # Stable samples only: decoder not seeking and RVFC observed within 100ms.
    stable = [s for s in samples if s["playing"] and not s["audioPaused"]
              and not s["seeking"] and s["callbackAgeMs"] < 100]
    assert len(stable) >= 20, "no reliable playing compositor timestamps"
    grouped = {}
    for name, group in [("transition", [s for s in stable if s["role"] != "solo"]),
                        ("steady", [s for s in stable if s["role"] == "solo"])]:
        assert group, f"missing {name} samples"
        grouped[name] = {"samples": len(group),
                         "source_pts_minus_expected": metric([abs(s["pts"] - s["expected"]) for s in group]),
                         "presented_timeline_minus_master_media_clock": metric([abs(s["presentedTimeline"] - s["audio"]) for s in group])}
    return {"draw_samples": len(samples), "stable_samples": len(stable), "by_phase": grouped,
            "source_pts_minus_expected": metric([abs(s["pts"] - s["expected"]) for s in stable]),
            "timeline_minus_master_media_clock": metric([abs(s["timeline"] - s["audio"]) for s in stable]),
            "presented_timeline_minus_master_media_clock": metric([abs(s["presentedTimeline"] - s["audio"]) for s in stable]),
            "currentTime_readout_minus_expected": metric([abs(s["currentTime"] - s["expected"]) for s in stable]),
            "ids": sorted({s["id"] for s in stable}), "roles": sorted({s["role"] for s in stable})}


def test_multisource_master_audio_transitions_speed_seek_pause_resume(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("multisource-av-") as directory:
        root = Path(directory)
        sources = [_source(root, variant) for variant in range(3)]
        audio = root / "synthetic-master.wav"
        rate = 48000
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            # Audible non-silent pulse train; clock probe does not measure speaker output latency.
            frames = bytearray()
            for i in range(rate * 10):
                gain = .18 if i % rate < rate // 10 else .03
                frames.extend(struct.pack("<h", int(32767 * gain * math.sin(2 * math.pi * 440 * i / rate))))
            stream.writeframes(frames)
        configs = [{"trim_start": .2, "trim_end": 2.6, "speed": 1, "transition_in": "cut"},
                   {"trim_start": .3, "trim_end": 3.3, "speed": 1.5, "transition_in": "fade", "transition_duration": .5},
                   {"trim_start": .1, "trim_end": 3.1, "speed": .75, "transition_in": "cut"}]
        clips = [{"id": f"av-{i}", "source_path": vite_fs_url(base, source), "duration": 4, **config}
                 for i, (source, config) in enumerate(zip(sources, configs))]
        query = urlencode({"clips": json.dumps(clips), "audio": vite_fs_url(base, audio)})
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1000, "height": 1100}, ignore_https_errors=True)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                start = perf_counter()
                page.goto(f"{base}/multisource_av_preview.html?{query}", wait_until="domcontentloaded")
                stage = page.get_by_test_id("multisource-av-preview")
                play = stage.get_by_role("button", name="เล่นพรีวิว", exact=True)
                play.wait_for(timeout=20000)
                page.wait_for_function("window.avProbe && [...document.querySelectorAll('video,audio')].every(v=>v.readyState>=2)")
                ready_ms = (perf_counter() - start) * 1000
                assert stage.locator("video").count() == 3
                page.evaluate("window.avProbe.reset()")
                play.click()
                page.wait_for_function("document.querySelector('audio').currentTime>2.65")
                stage.get_by_role("button", name="หยุดพรีวิวชั่วคราว", exact=True).click()
                first = page.evaluate("window.avProbe.samples.slice()")
                paused = page.evaluate("({a:document.querySelector('audio').currentTime,v:[...document.querySelectorAll('video')].map(v=>v.currentTime)})")
                page.wait_for_timeout(180)
                after = page.evaluate("({a:document.querySelector('audio').currentTime,v:[...document.querySelectorAll('video')].map(v=>v.currentTime)})")
                assert abs(paused["a"] - after["a"]) < .02
                assert max(abs(a - b) for a, b in zip(paused["v"], after["v"])) < .04
                seek_metrics = []
                all_samples = list(first)
                for target, active, expected, stop in [(0.7, 0, .9, 4.3), (6.0, 2, 1.675, 6.7)]:
                    started = perf_counter()
                    page.evaluate("t=>window.avProbe.seek(t)", target)
                    page.wait_for_function("""({id,want,t})=>{
                        const v=document.querySelectorAll('video')[id], a=document.querySelector('audio');
                        return !v.seeking&&Math.abs(v.currentTime-want)<.04&&Math.abs(a.currentTime-t)<.04;
                    }""", arg={"id": active, "want": expected, "t": target})
                    seek_metrics.append({"target": target, "seek_ms": round((perf_counter() - started) * 1000, 2)})
                    page.evaluate("window.avProbe.reset()")
                    play.click()
                    page.wait_for_function("t=>document.querySelector('audio').currentTime>t", arg=stop)
                    stage.get_by_role("button", name="หยุดพรีวิวชั่วคราว", exact=True).click()
                    all_samples.extend(page.evaluate("window.avProbe.samples.slice()"))
                result = _summary(all_samples)
                result.update({"ready_ms": round(ready_ms, 2), "seeks": seek_metrics})
                print("MULTISOURCE_AV " + json.dumps(result))
                assert result["ids"] == ["av-0", "av-1", "av-2"]
                assert "in" in result["roles"] and "out" in result["roles"]
                assert result["timeline_minus_master_media_clock"]["p95_ms"] < 50
                assert result["source_pts_minus_expected"]["p95_ms"] < 200
                assert result["presented_timeline_minus_master_media_clock"]["p95_ms"] < 200
                assert not errors, errors
            finally:
                browser.close()
