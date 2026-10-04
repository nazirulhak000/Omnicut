"""Offline SAM2 propagation/encode contract, using a predictor with real seed semantics."""
from contextlib import nullcontext
import io
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image

from scripts import background_isolation_sam2_worker as worker
from scripts import background_isolation_video_worker as video_worker


class _Mask:
    def __gt__(self, _threshold):
        return self

    def any(self, dim):
        return self

    def squeeze(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return np.ones((4, 4), dtype=bool)


def test_sparse_reseeding_conditions_frame_zero_and_encodes_every_source_frame(monkeypatch, tmp_path):
    seeds = []
    decoded = []
    encoded = []

    class Predictor:
        def init_state(self, path, **_kwargs):
            return path

        def add_new_points_or_box(self, _state, *, frame_idx, **_kwargs):
            seeds.append(frame_idx)

        def propagate_in_video(self, _state):
            # SAM2 defaults to its earliest conditioned frame; missing frame
            # zero would silently produce too few bytes despite manifest count.
            for index in range(min(seeds), 6):
                decoded.append(index)
                yield index, [1], _Mask()

    monkeypatch.setitem(sys.modules, "sam2", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "sam2.build_sam", SimpleNamespace(
        build_sam2_video_predictor=lambda *_args, **_kwargs: Predictor()))
    cuda = SimpleNamespace(is_available=lambda: True, reset_peak_memory_stats=lambda: None,
        get_device_name=lambda _index: "offline fake", max_memory_allocated=lambda: 0,
        max_memory_reserved=lambda: 0)
    monkeypatch.setattr(worker, "torch", SimpleNamespace(cuda=cuda, __version__="fake",
        inference_mode=lambda: nullcontext(), autocast=lambda *_args, **_kwargs: nullcontext(), bfloat16="fake"))
    monkeypatch.setattr(worker, "resolve_checkpoint", lambda *_args: tmp_path / "model.pt")
    monkeypatch.setattr(worker, "_verify_video", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker, "build_alpha_preview", lambda *_args, **_kwargs: {})
    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(
        virtual_memory=lambda: SimpleNamespace(available=100 * 1024**3)))

    def extract_frames(command, **_kwargs):
        template = Path(command[-1])
        for index in range(6):
            Image.new("RGB", (4, 4), "blue").save(template.parent / f"{index + 1:05d}.jpg")
    monkeypatch.setattr(worker.subprocess, "run", extract_frames)

    class Input(io.BytesIO):
        def close(self):
            if not self.closed:
                encoded.append(self.getvalue())
            super().close()

    class Encoder:
        def __init__(self, command, **_kwargs):
            self.stdin = Input()
            self.returncode = None
            self.output = Path(command[-1])

        def wait(self, timeout):
            self.output.write_bytes(b"offline encoded cutout")
            self.returncode = 0

        def poll(self):
            return self.returncode
    monkeypatch.setattr(worker.subprocess, "Popen", Encoder)
    monkeypatch.setattr(video_worker, "_derive_points_for_timestamp", lambda *_args:
        [{"x": 0.4, "y": 0.5, "label": 1}])
    points = video_worker.derive_sam2_prompts({"subject_points": [{"x": 0.2, "y": 0.3}],
        "prompt_reference_start": 0}, tmp_path / "source.mp4", tmp_path,
        start=0, width=4, height=4, worker=None, active_intervals=[(2 / 30, 3 / 30), (4 / 30, 5 / 30)], fps=30)
    prompts = [{"object_id": 1, "frame": point["frame"],
        "points": [[point["x"], point["y"]]], "labels": [point["label"]]} for point in points]
    manifest = worker.process_video_sam2(tmp_path / "source.mp4", tmp_path / "out", width=4,
        height=4, duration=6 / 30, prompts=prompts, active_intervals=[(2 / 30, 3 / 30), (4 / 30, 5 / 30)])
    assert seeds == [0, 2, 4]
    assert decoded == list(range(6))
    assert len(encoded[0]) == 6 * 4 * 4 * 4
    alpha = np.frombuffer(encoded[0], dtype=np.uint8).reshape(6, 4, 4, 4)[..., 3]
    assert [int(frame.max()) for frame in alpha] == [0, 0, 255, 0, 255, 0]
    assert manifest["frame_count"] == 6 and manifest["isolated_frame_count"] == 2
    assert not list(tmp_path.rglob("sam2_frames_*"))
