"""Default cover frame: nameplate on screen, product sharp, nothing stamped twice.

Every video here is synthetic and lives in `tmp_path`; nothing touches
04_Exports or 05_Covers_Thumbnails.
"""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from scripts import cover_frame_picker as picker

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _hook(start, end, **extra):
    return {"kind": "hook", "start": start, "end": end, **extra}


class TestResolveHookWindow:
    def test_default_nameplate_sits_after_the_hook_line(self):
        lo, hi = picker.resolve_hook_window(None, 20.0)
        assert lo == pytest.approx(1.8 + picker.SETTLE_AFTER_START_SEC)
        assert hi == pytest.approx(4.8 - picker.CLEAR_BEFORE_END_SEC)

    def test_reads_the_projects_own_hook_overlay(self):
        # An older clip: nameplate 0-5 s, no hook line.
        lo, hi = picker.resolve_hook_window([_hook(0, 5)], 45.0)
        assert (lo, hi) == (pytest.approx(0.6), pytest.approx(4.7))

    def test_a_retimed_nameplate_moves_the_window(self):
        lo, hi = picker.resolve_hook_window([_hook(3.0, 6.0)], 30.0)
        assert lo == pytest.approx(3.6) and hi == pytest.approx(5.7)

    def test_hidden_hook_falls_back_to_the_default(self):
        assert picker.resolve_hook_window([_hook(0, 5, hidden=True)], 20.0) == picker.resolve_hook_window(None, 20.0)

    def test_window_stays_inside_a_short_clip(self):
        lo, hi = picker.resolve_hook_window([_hook(1.8, 4.8)], 3.0)
        assert 0.0 <= lo <= hi <= 3.0

    def test_a_very_short_nameplate_still_gives_a_usable_window(self):
        lo, hi = picker.resolve_hook_window([_hook(1.0, 1.5)], 20.0)
        assert lo < hi


class TestCandidateTimes:
    def test_ascending_inside_the_window_and_bounded(self):
        times = picker.candidate_times((2.4, 4.5))
        assert times == sorted(times)
        assert times[0] == pytest.approx(2.4) and times[-1] == pytest.approx(4.5)
        assert len(times) <= picker.MAX_SAMPLES

    def test_long_window_is_capped(self):
        assert len(picker.candidate_times((0.0, 600.0))) == picker.MAX_SAMPLES

    def test_degenerate_window_gives_one_time(self):
        assert picker.candidate_times((3.0, 3.0)) == [3.0]


class TestFrameHasNameplate:
    def test_inside_the_window(self):
        assert picker.frame_has_nameplate([_hook(1.8, 4.8)], 3.0)

    def test_before_it_has_appeared(self):
        assert not picker.frame_has_nameplate([_hook(1.8, 4.8)], 0.5)
        assert not picker.frame_has_nameplate([_hook(1.8, 4.8)], 1.9)   # still sliding in

    def test_after_it_has_gone(self):
        assert not picker.frame_has_nameplate([_hook(1.8, 4.8)], 6.0)

    def test_unknown_or_hidden_means_not_known_to_be_burned_in(self):
        assert not picker.frame_has_nameplate(None, 3.0)
        assert not picker.frame_has_nameplate([_hook(1.8, 4.8, hidden=True)], 3.0)


def _textured(h=480, w=270, seed=1):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, (h, w, 3), dtype=np.uint8)


class TestScoreFrame:
    def test_sharp_beats_flat(self):
        flat = np.full((480, 270, 3), 128, dtype=np.uint8)
        assert picker.score_frame(_textured()) > picker.score_frame(flat) * 10

    def test_a_cut_on_the_frame_is_penalised(self):
        frame = _textured()
        same = picker.score_frame(frame, frame, frame)
        cut = picker.score_frame(frame, _textured(seed=2), np.full((480, 270, 3), 255, dtype=np.uint8))
        assert cut == pytest.approx(same * picker.CUT_PENALTY)

    def test_text_bands_do_not_count_as_the_product(self):
        """Busy hook text on top and captions below must not raise the score."""
        flat = np.full((480, 270, 3), 128, dtype=np.uint8)
        busy = flat.copy()
        busy[:int(480 * 0.25)] = _textured()[:int(480 * 0.25)]
        busy[int(480 * 0.75):] = _textured()[int(480 * 0.75):]
        assert picker.score_frame(busy) == pytest.approx(picker.score_frame(flat))


class TestFindProjectOverlays:
    def _project(self, root, folder, mp4_name, overlays, duration=30.0):
        d = root / folder
        d.mkdir(parents=True)
        (d / "project.json").write_text(json.dumps({
            "artifacts": {"mp4_video": {"path": f"04_Exports/Ready_to_post/{mp4_name}"}},
            "overlays": overlays, "total_duration": duration,
        }), encoding="utf-8")

    def test_matches_on_the_recorded_mp4_not_the_folder_name(self, tmp_path):
        self._project(tmp_path, "AAA01_1", "AAA01_1_20260101_000000.mp4", [_hook(1.8, 4.8)])
        self._project(tmp_path, "BBB01_1", "BBB01_1_20260101_000000.mp4", [_hook(0, 5)], 12.0)
        overlays, dur = picker.find_project_overlays(Path("x/BBB01_1_20260101_000000.mp4"), tmp_path)
        assert overlays == [_hook(0, 5)] and dur == 12.0

    def test_no_fuzzy_match(self, tmp_path):
        self._project(tmp_path, "AAA01_1", "AAA01_1_20260101_000000.mp4", [_hook(1.8, 4.8)])
        assert picker.find_project_overlays(Path("x/AAA01_1_20260101_000001.mp4"), tmp_path) == (None, None)

    def test_missing_projects_dir(self, tmp_path):
        assert picker.find_project_overlays(Path("a.mp4"), tmp_path / "nope") == (None, None)


def _make_video(path: Path) -> Path:
    """8 s: 0-2 flat grey, 2-5 sharp texture, 5-8 the same texture heavily blurred."""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=gray:s=270x480:d=2:r=30",
        "-f", "lavfi", "-i", "testsrc2=s=270x480:d=3:r=30",
        "-f", "lavfi", "-i", "testsrc2=s=270x480:d=3:r=30,boxblur=14",
        "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0",
        "-pix_fmt", "yuv420p", str(path),
    ], check=True, timeout=60)
    return path


@needs_ffmpeg
class TestPickCoverTimestamp:
    def test_lands_on_the_sharp_part_of_the_nameplate_window(self, tmp_path):
        video = _make_video(tmp_path / "clip.mp4")
        # window = (1.6, 5.7): flat until 2.0, sharp until 5.0, blurred after.
        got = picker.pick_cover_timestamp(video, [_hook(1.0, 6.0)], 8.0)
        assert got["reason"] == "scored"
        assert got["window"] == (pytest.approx(1.6), pytest.approx(5.7))
        assert 2.0 <= got["timestamp"] <= 5.0, got["timestamp"]
        assert got["score"] > 0

    def test_always_inside_the_window(self, tmp_path):
        video = _make_video(tmp_path / "clip.mp4")
        got = picker.pick_cover_timestamp(video, [_hook(1.0, 6.0)], 8.0)
        assert got["window"][0] - 1e-6 <= got["timestamp"] <= got["window"][1] + 1e-6

    def test_unreadable_video_falls_back_to_the_window_midpoint(self, tmp_path):
        bogus = tmp_path / "missing.mp4"
        got = picker.pick_cover_timestamp(bogus, [_hook(1.8, 4.8)], 20.0)
        assert got["reason"] == "fallback"
        lo, hi = got["window"]
        assert got["timestamp"] == pytest.approx((lo + hi) / 2, abs=0.01)


@needs_ffmpeg
class TestApiIntegration:
    @pytest.fixture
    def api(self, tmp_path, monkeypatch):
        from scripts import api_covers

        projects = tmp_path / "03_Projects"
        monkeypatch.setattr(api_covers, "BASE_DIR", tmp_path)
        monkeypatch.setattr(api_covers, "COVERS_DIR", tmp_path / "05_Covers_Thumbnails")
        monkeypatch.setattr(api_covers, "PROJECTS_DIR", projects)
        api_covers._RECOMMENDED_CACHE.clear()
        return api_covers, projects

    def _export(self, tmp_path, projects):
        video = _make_video(tmp_path / "EXP01_1_20260101_000000.mp4")
        d = projects / "EXP01_1"
        d.mkdir(parents=True)
        (d / "project.json").write_text(json.dumps({
            "artifacts": {"mp4_video": {"path": f"04_Exports/{video.name}"}},
            "overlays": [_hook(1.0, 6.0)], "total_duration": 8.0,
        }), encoding="utf-8")
        return video

    def test_recommended_timestamp_uses_the_projects_window(self, api, tmp_path):
        mod, projects = api
        video = self._export(tmp_path, projects)
        ts = mod.recommended_cover_timestamp(video)
        assert ts is not None and 2.0 <= ts <= 5.0

    def test_highlights_lead_with_the_recommended_frame(self, api, tmp_path):
        mod, projects = api
        video = self._export(tmp_path, projects)
        res = mod.extract_highlight_candidates(video)
        first = res["candidates"][0]
        assert first["recommended"] is True
        assert first["label"] == "ปกแนะนำ (Hook + สินค้า)"
        assert first["timestamp"] == pytest.approx(mod.recommended_cover_timestamp(video))
        # A fixed point within 0.3 s of the recommended frame is the same shot.
        stamps = [c["timestamp"] for c in res["candidates"]]
        assert all(abs(a - b) >= 0.3 for i, a in enumerate(stamps) for b in stamps[i + 1:])
        assert sum(1 for c in res["candidates"] if c["recommended"]) == 1

    def test_an_explicit_time_is_never_overridden(self, api, tmp_path):
        mod, projects = api
        assert mod.resolve_cover_seconds("anything.mp4", 7.25) == 7.25

    def test_omitted_time_resolves_to_the_recommended_frame(self, api, tmp_path, monkeypatch):
        mod, projects = api
        video = self._export(tmp_path, projects)
        monkeypatch.setattr(mod, "_resolve_media", lambda p: video)
        assert mod.resolve_cover_seconds("EXP01.mp4", None) == mod.recommended_cover_timestamp(video)

    def test_a_raw_footage_frame_keeps_the_old_default(self, api, tmp_path):
        mod, _ = api
        assert mod.resolve_cover_seconds("clip.mp4", None, raw_video_path_str="raw.mp4") == 1.0

    def test_unanalysable_video_keeps_the_old_default(self, api, tmp_path, monkeypatch):
        mod, _ = api
        monkeypatch.setattr(mod, "_resolve_media", lambda p: tmp_path / "gone.mp4")
        assert mod.resolve_cover_seconds("gone.mp4", None) == 1.0


@needs_ffmpeg
class TestGenerateCoverStampGuard:
    """POST /covers/generate: a frame that already shows the nameplate is not stamped again."""

    @pytest.fixture
    def endpoint(self, tmp_path, monkeypatch):
        from types import SimpleNamespace

        from scripts import api_covers

        projects = tmp_path / "03_Projects"
        monkeypatch.setattr(api_covers, "BASE_DIR", tmp_path)
        monkeypatch.setattr(api_covers, "COVERS_DIR", tmp_path / "05_Covers_Thumbnails")
        monkeypatch.setattr(api_covers, "PROJECTS_DIR", projects)
        api_covers._RECOMMENDED_CACHE.clear()
        video = _make_video(tmp_path / "EXP01_1_20260101_000000.mp4")
        folder = projects / "EXP01_1"
        folder.mkdir(parents=True)
        (folder / "project.json").write_text(json.dumps({
            "artifacts": {"mp4_video": {"path": f"04_Exports/{video.name}"}},
            "overlays": [_hook(1.8, 4.8)], "total_duration": 8.0,
        }), encoding="utf-8")

        calls = []

        def fake_generate(video_rel, at, brand, model, label, template, output_dir=None):
            calls.append({"at": at, "tiers": (brand, model, label)})
            out = tmp_path / "cover.jpg"
            out.write_bytes(b"x")
            return out

        monkeypatch.setattr(api_covers, "generate_cover", fake_generate)
        monkeypatch.setattr(api_covers, "_resolve_media", lambda p: video)
        monkeypatch.setattr(api_covers, "require_media_owner", lambda *a, **k: None)
        monkeypatch.setattr(api_covers, "register_companion", lambda *a, **k: None)
        scope = SimpleNamespace(channel_id="c1")

        def call(**kw):
            req = api_covers.GenerateCoverRequest(video_path="EXP01.mp4", brand="HOYAUP", model="X1", label="Cooler", **kw)
            api_covers.generate_cover_endpoint(req, scope)
            return calls[-1]

        return call

    def test_frame_inside_the_nameplate_window_is_not_stamped(self, endpoint):
        got = endpoint(at_seconds=3.0)
        assert got["tiers"] == ("", "", "")

    def test_frame_before_the_nameplate_is_still_stamped(self, endpoint):
        got = endpoint(at_seconds=0.5)
        assert got["tiers"] == ("HOYAUP", "X1", "Cooler")

    def test_omitted_time_picks_a_frame_with_the_nameplate_and_skips_the_stamp(self, endpoint):
        got = endpoint()
        assert 2.4 <= got["at"] <= 4.5
        assert got["tiers"] == ("", "", "")
