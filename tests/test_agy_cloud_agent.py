"""
tests/test_agy_cloud_agent.py — Unit & API tests for AGY Cloud Agent & Web Terminal (/agy).
Deterministic, offline-safe, uses pytest tmp_path without touching production data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from scripts.agy_cloud_agent import (
    AGYCloudAgent,
    AGYWorkspaceTools,
    get_gemini_api_keys,
    get_system_status,
    is_safe_command,
    resolve_safe_path,
)
from scripts.api_server import app


def test_safety_guard_blocks_destructive_commands():
    ok1, reason1 = is_safe_command("rm -rf /")
    assert not ok1
    assert "Safety Guard" in reason1

    ok2, reason2 = is_safe_command("rm -rf 01_Raw/product")
    assert not ok2
    assert "01_Raw" in reason2

    ok3, reason3 = is_safe_command("del /s /q 02_Assets\\Fonts")
    assert not ok3
    assert "02_Assets" in reason3

    ok_safe, _ = is_safe_command("python --version")
    assert ok_safe


def test_resolve_safe_path_protects_raw_and_assets(tmp_path: Path):
    raw_dir = tmp_path / "01_Raw"
    raw_dir.mkdir()
    existing_raw_file = raw_dir / "clip.mp4"
    existing_raw_file.write_text("dummy", encoding="utf-8")

    # Reading existing raw file is allowed
    resolved_read, _ = resolve_safe_path("01_Raw/clip.mp4", workspace=tmp_path, for_write=False)
    assert resolved_read == existing_raw_file

    # Overwriting existing file in 01_Raw is blocked
    resolved_write, reason = resolve_safe_path("01_Raw/clip.mp4", workspace=tmp_path, for_write=True)
    assert resolved_write is None
    assert "01_Raw" in reason

    # Accessing outside workspace is blocked
    outside, out_reason = resolve_safe_path("../outside_secret.txt", workspace=tmp_path, for_write=False)
    assert outside is None
    assert "ไม่อนุญาต" in out_reason


def test_workspace_tools_crud_and_search(tmp_path: Path):
    tools = AGYWorkspaceTools(workspace=tmp_path)

    # 1. write_file
    w_res = tools.write_file("scripts/demo.py", "def hello():\n    return 'omnicut_agy'\n")
    assert w_res["ok"] is True

    # 2. read_file
    r_res = tools.read_file("scripts/demo.py", start_line=1, end_line=10)
    assert r_res["ok"] is True
    assert "omnicut_agy" in r_res["content"]

    # 3. edit_file
    e_res = tools.edit_file("scripts/demo.py", "omnicut_agy", "omnicut_agy_v2")
    assert e_res["ok"] is True
    assert e_res["replacements_count"] == 1

    # 4. search_files
    s_res = tools.search_files("omnicut_agy_v2")
    assert s_res["ok"] is True
    assert s_res["matches_count"] == 1
    assert s_res["matches"][0]["file"].endswith("demo.py")

    # 5. list_dir
    l_res = tools.list_dir("scripts")
    assert l_res["ok"] is True
    assert any(item["name"] == "demo.py" for item in l_res["entries"])

    # 6. sync_to_drive to custom destination in tmp_path
    exp_dir = tmp_path / "04_Exports" / "Ready_to_post"
    exp_dir.mkdir(parents=True)
    (exp_dir / "20261030_test_clip.mp4").write_bytes(b"fake_mp4_bytes")
    drive_dest = tmp_path / "mock_drive"
    sync_res = tools.sync_to_drive(subpath="Ready_to_post", dest_dir=drive_dest)
    assert sync_res["ok"] is True
    assert sync_res["copied_count"] == 1
    assert (drive_dest / "20261030_test_clip.mp4").exists()


def test_agent_multi_step_tool_calling_and_goal_mode(tmp_path: Path):
    call_counter = {"count": 0}

    def fake_gemini_api(payload: Dict[str, Any], api_key: str, model: str) -> Dict[str, Any]:
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            # First step: model thinks and calls write_file
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "กำลังสร้างไฟล์ทดสอบ note.txt"},
                                {
                                    "functionCall": {
                                        "name": "write_file",
                                        "args": {"path": "note.txt", "content": "AGY Colab Ready 100%"},
                                    }
                                },
                            ]
                        }
                    }
                ]
            }
        # Second step: model sees tool result and returns final answer
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "สร้างไฟล์ note.txt เรียบร้อยแล้วครับ!"}
                        ]
                    }
                }
            ]
        }

    agent = AGYCloudAgent(workspace=tmp_path, api_call_fn=fake_gemini_api)
    res = agent.chat("/goal สร้างไฟล์ note.txt ให้หน่อย", session_id="test-goal-1")
    assert res["ok"] is True
    assert res["steps"] == 2
    assert "สร้างไฟล์ note.txt เรียบร้อยแล้ว" in res["answer"]
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "AGY Colab Ready 100%"


def test_agent_shell_shortcut_bang_command(tmp_path: Path):
    agent = AGYCloudAgent(workspace=tmp_path)
    res = agent.chat("!python --version", session_id="test-shell")
    assert res["ok"] is True
    assert "Python" in res["answer"]


def test_fastapi_agy_endpoints():
    client = TestClient(app)

    # 1. GET /agy Web Terminal HTML
    r_html = client.get("/agy")
    assert r_html.status_code == 200
    assert "Antigravity Cloud Terminal" in r_html.text

    # 2. GET /api/agy/status
    r_status = client.get("/api/agy/status")
    assert r_status.status_code == 200
    st = r_status.json()
    assert st["ok"] is True
    assert "gpu" in st
    assert "disk" in st

    # 3. POST /api/agy/exec (safe command)
    r_exec = client.post("/api/agy/exec", json={"command": "python --version", "timeout_sec": 15})
    assert r_exec.status_code == 200
    assert r_exec.json()["ok"] is True

    # 4. POST /api/agy/chat with !command shortcut
    r_chat = client.post(
        "/api/agy/chat",
        json={"message": "!python -c \"print('AGY_OK')\"", "session_id": "api-test-sess"},
    )
    assert r_chat.status_code == 200
    chat_data = r_chat.json()
    assert chat_data["ok"] is True
    assert "AGY_OK" in chat_data["answer"]

    # 5. GET & DELETE /api/agy/sessions
    r_sess = client.get("/api/agy/sessions")
    assert r_sess.status_code == 200
    assert any(s["session_id"] == "api-test-sess" for s in r_sess.json()["sessions"])

    r_del = client.delete("/api/agy/sessions/api-test-sess")
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True


def test_colab_notebook_contains_agy_setup():
    nb_path = Path(__file__).resolve().parent.parent / "Omnicut_Cloud_Runner.ipynb"
    assert nb_path.exists()
    nb_data = json.loads(nb_path.read_text(encoding="utf-8"))
    source_joined = "\n".join("".join(c.get("source", [])) for c in nb_data.get("cells", []))
    assert "/usr/local/bin/agy" in source_joined
    assert "colab_agy_cli.py" in source_joined
    assert "/agy" in source_joined
