"""
Tests for scripts/flow_service.py
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from scripts.flow_service import FlowJobStore, FlowService


def test_flow_job_store_crud(tmp_path, monkeypatch):
    test_jobs_file = tmp_path / "flow_jobs.json"
    monkeypatch.setattr("scripts.flow_service.FLOW_JOBS_FILE", test_jobs_file)

    # Empty initially
    assert FlowJobStore.load() == {"jobs": {}}

    # Create job
    job = FlowJobStore.create_job(
        product_id="prod_test_01",
        project_name="TestProj",
        scenes=[{"prompt": "Hello", "type": "video"}],
        client_job_ids=["c_job_1"],
    )
    assert job["product_id"] == "prod_test_01"
    assert job["status"] == "queued"

    # Read back
    fetched = FlowJobStore.get_job(job["id"])
    assert fetched is not None
    assert fetched["project_name"] == "TestProj"

    # Update job
    FlowJobStore.update_job(job["id"], {"status": "completed"})
    updated = FlowJobStore.get_job(job["id"])
    assert updated["status"] == "completed"

    # List jobs
    jobs = FlowJobStore.list_jobs(product_id="prod_test_01")
    assert len(jobs) == 1
    assert jobs[0]["id"] == job["id"]


def test_flow_service_ingest_clip(tmp_path, monkeypatch):
    mock_raw_dir = tmp_path / "01_Raw"
    monkeypatch.setattr("scripts.flow_service.RAW_DIR", mock_raw_dir)

    # Create source video file
    src_video = tmp_path / "rendered_output.mp4"
    src_video.write_bytes(b"FAKE_MP4_CONTENT_123456789")

    service = FlowService(client=MagicMock())
    metadata = service.ingest_clip(
        product_id="prod_abc",
        source_path=str(src_video),
        shot_label="macro_hero",
    )

    assert metadata["product_id"] == "prod_abc"
    assert "macro_hero" in metadata["filename"]
    assert Path(metadata["path"]).exists()
    assert Path(metadata["path"]).read_bytes() == b"FAKE_MP4_CONTENT_123456789"
