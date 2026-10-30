"""
tests/test_agy_cloud_agent.py — Unit, Security Penetration & Live API tests for AGY Cloud Agent (/agy).
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
    redact_secrets,
    resolve_safe_path,
)
from scripts.api_server import app


def test_safety_guard_blocks_destructive_and_tunnel_kill_commands():
    # 1. Root & protected dir deletion
    ok1, reason1 = is_safe_command("rm -rf /")
    assert not ok1
    assert "Safety Guard" in reason1

    ok2, reason2 = is_safe_command("rm -rf 01_Raw/product")
    assert not ok2
    assert "01_Raw" in reason2

    ok3, reason3 = is_safe_command("del /s /q 02_Assets\\Fonts")
    assert not ok3
    assert "02_Assets" in reason3

    # 2. Tunnel & Server Self-Preservation
    ok4, reason4 = is_safe_command("pkill -f cloudflared")
    assert not ok4
    assert "Safety Guard" in reason4

    ok5, reason5 = is_safe_command("fuser -k 8000/tcp")
    assert not ok5
    assert "Safety Guard" in reason5

    # 3. Critical database deletion
    ok6, reason6 = is_safe_command("rm _Docs/products.json")
    assert not ok6
    assert "products.json" in reason6

    # 4. Safe commands allowed
    ok_safe, _ = is_safe_command("python --version")
    assert ok_safe


def test_resolve_safe_path_protects_raw_assets_and_env(tmp_path: Path):
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

    # Direct access to .env is blocked
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=secret", encoding="utf-8")
    resolved_env, env_reason = resolve_safe_path(".env", workspace=tmp_path, for_write=False)
    assert resolved_env is None
    assert ".env" in env_reason

    # Accessing outside workspace is blocked
    outside, out_reason = resolve_safe_path("../outside_secret.txt", workspace=tmp_path, for_write=False)
    assert outside is None
    assert "ไม่อนุญาต" in out_reason


def test_secret_redaction_masks_api_keys_and_tokens(tmp_path: Path):
    raw_output = (
        "Key1: AIzaSyD9876543210abcdefghijklmnopqrstuv\n"
        "Key2: AQ.Ab8-N-957mUj4B2F7f2677zXlqf4j7-B5E3uWzNf4f0p6V-zQ\n"
        "Tunnel: eyJhIjoiNjQ3NDU3MTM3ZjBlZTdhMzc3MmFlNGEzOWE3OWJkYjciLCJ0IjoiYmFmZmM5MzM\n"
    )
    masked = redact_secrets(raw_output)
    assert "AIzaSyD" not in masked
    assert "AQ.Ab8-" not in masked
    assert "eyJhIjoi" not in masked
    assert masked.count("[REDACTED_SECRET]") == 3

    tools = AGYWorkspaceTools(workspace=tmp_path)
    tools.write_file("notes.txt", raw_output)
    read_res = tools.read_file("notes.txt")
    assert read_res["ok"] is True
    assert "AIzaSyD" not in read_res["content"]
    assert "[REDACTED_SECRET]" in read_res["content"]


def test_capcut_draft_auto_backup_on_write_and_edit(tmp_path: Path):
    tools = AGYWorkspaceTools(workspace=tmp_path)
    draft_path = tmp_path / "03_Projects" / "demo" / "draft_content.json"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text('{"version": 1}', encoding="utf-8")

    # Edit draft_content.json -> must create draft_content.json.bak automatically (Rule #3)
    res = tools.edit_file("03_Projects/demo/draft_content.json", '"version": 1', '"version": 2')
    assert res["ok"] is True
    assert "backup_created" in res
    bak_file = draft_path.with_name("draft_content.json.bak")
    assert bak_file.exists()
    assert bak_file.read_text(encoding="utf-8") == '{"version": 1}'
    assert draft_path.read_text(encoding="utf-8") == '{"version": 2}'


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


def test_fastapi_agy_endpoints_and_sse_streaming():
    client = TestClient(app)

    # 1. GET /agy Web Terminal HTML
    r_html = client.get("/agy")
    assert r_html.status_code == 200
    assert "Antigravity Cloud Terminal" in r_html.text
    assert "ทดสอบ Safety Guard" in r_html.text

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

    # 4. POST /api/agy/exec (blocked destructive command)
    r_blocked = client.post("/api/agy/exec", json={"command": "rm -rf 01_Raw/test_protect", "timeout_sec": 15})
    assert r_blocked.status_code == 200
    assert r_blocked.json()["ok"] is False
    assert "Safety Guard" in r_blocked.json()["error"]

    # 5. POST /api/agy/stream SSE streaming test
    with client.stream(
        "POST",
        "/api/agy/stream",
        json={"message": "!python -c \"print('SSE_STREAM_OK')\"", "session_id": "sse-test-1"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
        assert "SSE_STREAM_OK" in body

    # 6. GET & DELETE /api/agy/sessions
    r_sess = client.get("/api/agy/sessions")
    assert r_sess.status_code == 200
    assert any(s["session_id"] == "sse-test-1" for s in r_sess.json()["sessions"])

    r_del = client.delete("/api/agy/sessions/sse-test-1")
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
