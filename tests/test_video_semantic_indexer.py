"""Unit tests for VideoSemanticIndexer and Auto B-Roll Matcher."""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.video_semantic_indexer import (
    VideoSemanticIndexer,
    _compute_file_hash,
    TAG_SYNONYMS,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_store.db"


@pytest.fixture
def indexer(temp_db_path: Path) -> VideoSemanticIndexer:
    return VideoSemanticIndexer(db_path=temp_db_path)


class TestVideoSemanticIndexerDatabase:
    """Test SQLite schema creation, insertion, querying, and updating."""

    def test_schema_creation(self, temp_db_path: Path, indexer: VideoSemanticIndexer) -> None:
        conn = sqlite3.connect(str(temp_db_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_video_scenes'")
        assert cur.fetchone() is not None

        cur.execute("PRAGMA table_info(raw_video_scenes)")
        columns = [row[1] for row in cur.fetchall()]
        assert "file_hash" in columns
        assert "start_sec" in columns
        assert "end_sec" in columns
        assert "action_summary" in columns
        assert "tags" in columns
        assert "visual_features" in columns
        conn.close()

    def test_record_and_get_scenes(self, indexer: VideoSemanticIndexer) -> None:
        raw_scenes = [
            {
                "start_sec": 0.0,
                "end_sec": 4.2,
                "action_summary": "Unboxing phone box and showing accessories",
                "tags": ["unboxing", "package"],
                "visual_features": {"shot": "top_down"},
            },
            {
                "start_sec": 4.2,
                "end_sec": 9.5,
                "action_summary": "Zooming into 200MP camera lens module",
                "tags": ["camera", "lens", "zoom"],
                "visual_features": {"shot": "macro"},
            },
        ]

        saved = indexer.record_scenes("01_Raw/clip_01.mp4", "hash_abc123", raw_scenes)
        assert len(saved) == 2
        assert saved[0]["duration"] == 4.2
        assert saved[1]["duration"] == 5.3

        retrieved = indexer.get_scenes_by_hash("hash_abc123")
        assert len(retrieved) == 2
        assert retrieved[0]["action_summary"] == "Unboxing phone box and showing accessories"
        assert retrieved[0]["tags"] == ["unboxing", "package"]
        assert retrieved[1]["tags"] == ["camera", "lens", "zoom"]

    def test_record_replaces_old_scenes_on_same_hash(self, indexer: VideoSemanticIndexer) -> None:
        raw_v1 = [{"start_sec": 0.0, "end_sec": 2.0, "action_summary": "old scene", "tags": ["old"]}]
        indexer.record_scenes("01_Raw/clip_01.mp4", "hash_same", raw_v1)
        assert len(indexer.get_scenes_by_hash("hash_same")) == 1

        raw_v2 = [
            {"start_sec": 0.0, "end_sec": 3.0, "action_summary": "new scene 1", "tags": ["new1"]},
            {"start_sec": 3.0, "end_sec": 6.0, "action_summary": "new scene 2", "tags": ["new2"]},
        ]
        indexer.record_scenes("01_Raw/clip_01.mp4", "hash_same", raw_v2)
        retrieved = indexer.get_scenes_by_hash("hash_same")
        assert len(retrieved) == 2
        assert retrieved[0]["action_summary"] == "new scene 1"


class TestFileHashingAndProxy:
    """Test file hashing and proxy extraction handling."""

    def test_file_hash_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "non_existent.mp4"
        with pytest.raises(FileNotFoundError):
            _compute_file_hash(missing)

    def test_file_hash_deterministic(self, tmp_path: Path) -> None:
        sample = tmp_path / "sample.mp4"
        sample.write_bytes(b"dummy video content 123456789")
        h1 = _compute_file_hash(sample)
        h2 = _compute_file_hash(sample)
        assert h1 == h2
        assert len(h1) == 32


class TestSemanticBRollMatching:
    """Test semantic keyword matching, scoring, and auto-assembly."""

    @pytest.fixture
    def candidate_scenes(self) -> list[dict]:
        return [
            {
                "id": 1,
                "video_path": "01_Raw/sample.mp4",
                "file_hash": "hash_sample",
                "start_sec": 0.0,
                "end_sec": 4.0,
                "action_summary": "แกะกล่องสินค้า Unboxing package and accessories",
                "tags": ["unboxing", "accessories"],
                "confidence": 1.0,
            },
            {
                "id": 2,
                "video_path": "01_Raw/sample.mp4",
                "file_hash": "hash_sample",
                "start_sec": 4.0,
                "end_sec": 9.0,
                "action_summary": "โชว์กล้องหลัง 200MP Triple camera lens zoom in",
                "tags": ["camera", "lens", "zoom"],
                "confidence": 1.0,
            },
            {
                "id": 3,
                "video_path": "01_Raw/sample.mp4",
                "file_hash": "hash_sample",
                "start_sec": 9.0,
                "end_sec": 14.0,
                "action_summary": "เสียบสายชาร์จไว Fast charging USB-C 100W",
                "tags": ["charging", "battery", "usb-c"],
                "confidence": 1.0,
            },
            {
                "id": 4,
                "video_path": "01_Raw/sample.mp4",
                "file_hash": "hash_sample",
                "start_sec": 14.0,
                "end_sec": 18.0,
                "action_summary": "เล่นเกมลื่นๆ หน้าจอ 120Hz display gaming FPS test",
                "tags": ["performance", "display", "gaming"],
                "confidence": 1.0,
            },
        ]

    def test_score_scene_relevance_camera(self, indexer: VideoSemanticIndexer, candidate_scenes: list[dict]) -> None:
        camera_scene = candidate_scenes[1]
        charging_scene = candidate_scenes[2]

        script_text = "กล้องหลังตัวนี้ถ่ายสวยมาก คมชัดระดับโปร"
        score_cam = indexer.score_scene_relevance(script_text, camera_scene)
        score_charge = indexer.score_scene_relevance(script_text, charging_scene)

        assert score_cam > score_charge
        assert score_cam >= 0.7

    def test_score_scene_relevance_charging(self, indexer: VideoSemanticIndexer, candidate_scenes: list[dict]) -> None:
        charging_scene = candidate_scenes[2]
        unboxing_scene = candidate_scenes[0]

        script_text = "แบตเตอรี่อึด พร้อมระบบชาร์จไว 100W"
        score_charge = indexer.score_scene_relevance(script_text, charging_scene)
        score_unbox = indexer.score_scene_relevance(script_text, unboxing_scene)

        assert score_charge > score_unbox
        assert score_charge >= 0.7

    def test_match_broll_selects_best_candidate(self, indexer: VideoSemanticIndexer, candidate_scenes: list[dict]) -> None:
        match = indexer.match_broll("มาแกะกล่องดูพร้อมกันเลย", candidate_scenes)
        assert match is not None
        assert match["scene_id"] == 1
        assert "unboxing" in match["tags"]
        assert match["start_sec"] == 0.0

    def test_match_broll_clamps_duration(self, indexer: VideoSemanticIndexer, candidate_scenes: list[dict]) -> None:
        # Candidate 2 duration is 5.0s (4.0 to 9.0)
        match = indexer.match_broll(
            "กล้องเทพ 200 ล้าน",
            candidate_scenes,
            min_duration=2.0,
            max_duration=3.5,
        )
        assert match is not None
        assert match["duration"] <= 3.5
        assert match["duration"] >= 2.0

    def test_auto_assemble_broll_timeline(self, indexer: VideoSemanticIndexer, candidate_scenes: list[dict]) -> None:
        script_cues = [
            {"text": "สวัสดีครับ วันนี้เรามาแกะกล่องมือถือรุ่นใหม่", "duration": 3.0},
            {"text": "จุดเด่นแรกคือกล้องหลัง 200 ล้านพิกเซล", "duration": 3.5},
            {"text": "และที่สำคัญชาร์จไว 100W เต็มเร็วทันใจ", "duration": 2.5},
        ]

        cuts = indexer.auto_assemble_broll_timeline(script_cues, candidate_scenes)
        assert len(cuts) == 3
        assert cuts[0]["cut_start"] == 0.0  # unboxing
        assert cuts[1]["cut_start"] == 4.0  # camera
        assert cuts[2]["cut_start"] == 9.0  # charging
