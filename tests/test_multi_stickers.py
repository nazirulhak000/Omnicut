import pytest
from pathlib import Path
from scripts.video_editor import VideoEditor
from scripts.pipeline_context import PipelineContext
from scripts.api_schemas import RenderRequest

def test_multi_stickers_pipeline_context_and_schema():
    stickers_payload = [
        {
            "id": "stk-1",
            "badge": "accent_sparkle_star_3d.png",
            "start": 0.5,
            "end": 3.5,
            "scale": 1.2,
            "normX": 0.8,
            "normY": 0.2,
        },
        {
            "id": "stk-2",
            "badge": "plate_banner_yellow_3d.png",
            "start": 1.0,
            "end": 4.0,
            "scale": 1.0,
            "normX": 0.5,
            "normY": 0.7,
        },
    ]

    # Test Pydantic RenderRequest schema
    req = RenderRequest(
        project_name="test_proj",
        product_name="Test Product",
        raw_video_path="01_Raw/test.mp4",
        key_features="feat1",
        pain_point="pain",
        price_deal="deal",
        script={"hook": "test", "body": "test"},
        stickers=stickers_payload,
    )
    assert req.stickers is not None
    assert len(req.stickers) == 2
    assert req.stickers[0]["id"] == "stk-1"
    assert req.stickers[1]["id"] == "stk-2"

    # Test PipelineContext
    ctx = PipelineContext(
        project_name="test_proj",
        product_name="Test Product",
        raw_video_path="01_Raw/test.mp4",
        stickers=stickers_payload,
    )
    assert ctx.stickers == stickers_payload
    assert len(ctx.stickers) == 2


def test_video_editor_multi_stickers_filter_graph(monkeypatch, tmp_path):
    # Ensure STICKERS_DIR exists
    test_sticker1 = tmp_path / "test_s1.png"
    test_sticker2 = tmp_path / "test_s2.png"
    test_sticker1.write_bytes(b"\x89PNG\r\n\x1a\n")
    test_sticker2.write_bytes(b"\x89PNG\r\n\x1a\n")

    executed_cmd = []
    class FakeProc:
        def __init__(self, cmd, *args, **kwargs):
            executed_cmd.extend(cmd)
            self.args = cmd
            self.stdout = self
            self.stderr = self
            self.returncode = 0
        def readline(self):
            return ""
        def poll(self):
            return 0
        def wait(self, timeout=None):
            return 0
        def communicate(self, input=None, timeout=None):
            return ("", "")
        def kill(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            return None

    import subprocess
    monkeypatch.setattr(subprocess, "Popen", FakeProc)

    # Mock media info
    monkeypatch.setattr(VideoEditor, "get_media_info", lambda p: {"width": 1080, "height": 1920, "duration": 10.0})

    dummy_video = tmp_path / "raw.mp4"
    dummy_video.write_bytes(b"dummy")
    dummy_audio = tmp_path / "audio.mp3"
    dummy_audio.write_bytes(b"dummy")
    output_mp4 = tmp_path / "out.mp4"

    stickers = [
        {
            "id": "s1",
            "path": str(test_sticker1),
            "start": 1.0,
            "end": 4.0,
            "scale": 1.0,
            "norm_x": 0.3,
            "norm_y": 0.4,
        },
        {
            "id": "s2",
            "path": str(test_sticker2),
            "start": 2.0,
            "end": 5.0,
            "scale": 1.5,
            "norm_x": 0.7,
            "norm_y": 0.8,
        },
    ]

    dummy_ass = tmp_path / "sub.ass"
    dummy_ass.write_text("[Script Info]\n", encoding="utf-8")

    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(dummy_video)],
        mixed_audio_path=str(dummy_audio),
        output_mp4_path=str(output_mp4),
        total_duration=10.0,
        ass_subtitle_path=str(dummy_ass),
        stickers=stickers,
    )

    cmd_str = " ".join(executed_cmd)
    # Check that both sticker files were added as inputs
    assert str(test_sticker1.resolve()) in cmd_str
    assert str(test_sticker2.resolve()) in cmd_str
    # Check that multi-stickers overlay chaining was generated
    assert "between(t,1.00,4.00)" in cmd_str
    assert "between(t,2.00,5.00)" in cmd_str
    assert "[v_stickered_0]" in cmd_str
    assert "[v_stickered_1]" in cmd_str

