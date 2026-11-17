import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from scripts.api_server import app

client = TestClient(app)

def test_iphone_status_mock_disconnected():
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = '{"connected": false, "accessible": false, "error": "ไม่พบอุปกรณ์ iPhone"}'
    
    with patch("subprocess.run", return_value=mock_res):
        resp = client.get("/api/iphone/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["accessible"] is False

def test_iphone_status_mock_connected():
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = '{"connected": true, "accessible": true, "device_name": "Apple iPhone", "folder": "202611_a", "total_videos": 10}'
    
    with patch("subprocess.run", return_value=mock_res):
        resp = client.get("/api/iphone/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["device_name"] == "Apple iPhone"

def test_iphone_clips_mock():
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = '''{
        "connected": true,
        "accessible": true,
        "device_name": "Apple iPhone",
        "folder": "202611_a",
        "clips": [
            {"name": "IMG_8216", "file_name": "IMG_8216.MOV", "size": "154.4 MB", "date": "15/11/2569"}
        ]
    }'''
    
    mock_index = {"img_8216.mov": "00_Inbox/iPhone_Clips/IMG_8216.MOV", "img_8216": "00_Inbox/iPhone_Clips/IMG_8216.MOV"}
    with patch("subprocess.run", return_value=mock_res), patch("scripts.api_iphone._get_local_media_index", return_value=mock_index):
        resp = client.get("/api/iphone/clips?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert len(data["clips"]) == 1
        assert data["clips"][0]["name"] == "IMG_8216"
        assert data["clips"][0]["already_imported"] is True
        assert data["clips"][0]["imported_path"] == "00_Inbox/iPhone_Clips/IMG_8216.MOV"

def test_iphone_pull_validation():
    # Empty clip_names should fail with 400
    resp = client.post("/api/iphone/pull", json={"clip_names": []})
    assert resp.status_code == 400
