"""
scripts/api_agy.py — FastAPI Router & Interactive Web Terminal UI for AGY Cloud Agent (/agy & /api/agy/*).

Allows the user to open `https://studio.nazirulhak.com/agy` (or `http://localhost:8000/agy`)
from any browser, smartphone, or tablet to command the Antigravity (AGY) Agent in natural
language (Thai/English) or run raw Linux/shell commands on Google Colab.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from scripts.agy_cloud_agent import (
    get_cloud_agent,
    get_system_status,
)

logger = logging.getLogger("omnicut.api_agy")

router = APIRouter(tags=["AGY Cloud Terminal & Agent"])


class AGYChatRequest(BaseModel):
    message: str = Field(..., description="คำสั่งภาษาคน หรือ /goal ... หรือ !คำสั่งเชลล์")
    session_id: Optional[str] = Field(None, description="รหัสเซสชัน (เว้นว่างเพื่อสร้างเซสชันใหม่)")
    goal_mode: bool = Field(False, description="เปิดโหมด Autonomous Goal ทำงานต่อเนื่องจนเสร็จ")
    max_steps: Optional[int] = Field(None, description="จำนวนก้าวสูงสุดในการเรียกใช้เครื่องมือ")


class AGYExecRequest(BaseModel):
    command: str = Field(..., description="คำสั่ง Shell/Bash ที่ต้องการรันในโปรเจกต์")
    timeout_sec: int = Field(120, description="เวลาสูงสุดที่อนุญาตให้รัน (วินาที)")


class AGYDriveSyncRequest(BaseModel):
    subpath: str = Field("Ready_to_post", description="โฟลเดอร์ย่อยใน 04_Exports ที่ต้องการซิงก์เข้า Google Drive")


# ============================================================================
# 1. REST & SSE Endpoints (/api/agy/*)
# ============================================================================

@router.get("/api/agy/status")
def api_agy_status() -> Dict[str, Any]:
    """Return system, GPU, API keys, and Google Drive status for AGY Cloud Agent."""
    return get_system_status()


@router.get("/api/agy/sessions")
def api_agy_list_sessions() -> Dict[str, Any]:
    """List active AGY conversation sessions."""
    agent = get_cloud_agent()
    return {"ok": True, "sessions": agent.list_sessions()}


@router.delete("/api/agy/sessions/{session_id}")
def api_agy_delete_session(session_id: str) -> Dict[str, Any]:
    """Clear a specific AGY session history."""
    agent = get_cloud_agent()
    deleted = agent.clear_session(session_id)
    return {"ok": True, "deleted": deleted, "session_id": session_id}


@router.post("/api/agy/exec")
def api_agy_exec_command(payload: AGYExecRequest) -> Dict[str, Any]:
    """Execute a safe shell command directly in the workspace."""
    agent = get_cloud_agent()
    result = agent.tools.run_command(command=payload.command, timeout_sec=payload.timeout_sec)
    return result


@router.post("/api/agy/drive-sync")
def api_agy_drive_sync(payload: AGYDriveSyncRequest) -> Dict[str, Any]:
    """Sync exported MP4 videos to Google Drive."""
    agent = get_cloud_agent()
    return agent.tools.sync_to_drive(subpath=payload.subpath)


@router.post("/api/agy/self-update")
def api_agy_self_update() -> Dict[str, Any]:
    """Pull latest commits from origin/main and sync product scripts without killing active tunnels."""
    agent = get_cloud_agent()
    return agent.tools.self_update_from_git()


@router.post("/api/agy/chat")
def api_agy_chat(payload: AGYChatRequest) -> Dict[str, Any]:
    """Send a prompt/command to AGY Cloud Agent and receive the complete multi-step result."""
    if not (payload.message or "").strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุคำสั่ง (message ห้ามว่าง)")
    agent = get_cloud_agent()
    return agent.chat(
        message=payload.message,
        session_id=payload.session_id,
        goal_mode=payload.goal_mode,
        max_steps=payload.max_steps,
    )


@router.post("/api/agy/stream")
def api_agy_stream(payload: AGYChatRequest):
    """Stream real-time SSE events (thinking, tool_call, tool_result, answer) from AGY Cloud Agent."""
    if not (payload.message or "").strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุคำสั่ง (message ห้ามว่าง)")

    agent = get_cloud_agent()

    def event_generator():
        try:
            for ev in agent.stream_chat(
                message=payload.message,
                session_id=payload.session_id,
                goal_mode=payload.goal_mode,
                max_steps=payload.max_steps,
            ):
                data_str = json.dumps(ev, ensure_ascii=False)
                yield f"data: {data_str}\n\n"
        except Exception as exc:
            err_str = json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)
            yield f"data: {err_str}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# 2. Interactive Web Terminal Console UI (GET /agy)
# ============================================================================

AGY_WEB_TERMINAL_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AGY Cloud Terminal — OmniCut Pro Studio</title>
  <style>
    :root {
      --bg-deep: #070a12;
      --bg-panel: #0f1523;
      --bg-card: #151d30;
      --bg-input: #0b101d;
      --border: #1e293b;
      --border-focus: #3b82f6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --accent-blue: #3b82f6;
      --accent-cyan: #06b6d4;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --font-sans: 'Anuphan', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-deep);
      color: var(--text-main);
      font-family: var(--font-sans);
      height: 100dvh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    /* Top Header */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
      gap: 12px;
      flex-wrap: wrap;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-badge {
      background: linear-gradient(135deg, #2563eb, #06b6d4);
      color: #fff;
      font-family: var(--font-mono);
      font-weight: 800;
      font-size: 13px;
      padding: 5px 10px;
      border-radius: 6px;
      letter-spacing: 0.5px;
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
    }
    .brand-sub {
      font-size: 12px;
      color: var(--text-muted);
    }
    .status-pills {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pill {
      font-size: 12px;
      font-family: var(--font-mono);
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }
    .pill.ok {
      border-color: rgba(16, 185, 129, 0.4);
      color: #34d399;
      background: rgba(16, 185, 129, 0.08);
    }
    .pill.warn {
      border-color: rgba(245, 158, 11, 0.4);
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.08);
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 7px 14px;
      border-radius: 7px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s ease;
    }
    .btn:hover {
      border-color: var(--accent-blue);
      background: #1e293b;
    }
    .btn-primary {
      background: var(--accent-blue);
      border-color: var(--accent-blue);
      color: #fff;
    }
    .btn-primary:hover {
      background: #2563eb;
    }
    /* Quick Prompts Bar */
    .quickbar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      background: #0b0f1b;
      border-bottom: 1px solid var(--border);
      overflow-x: auto;
      flex-shrink: 0;
    }
    .chip {
      background: var(--bg-card);
      color: #cbd5e1;
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .chip:hover {
      border-color: var(--accent-cyan);
      color: #fff;
    }
    /* Terminal Log Area */
    .terminal-stream {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .msg {
      max-width: 920px;
      width: 100%;
      margin: 0 auto;
      padding: 14px 18px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--bg-panel);
      line-height: 1.6;
      font-size: 14px;
    }
    .msg.user {
      background: #13203c;
      border-color: #2563eb;
    }
    .msg-header {
      font-size: 11px;
      font-family: var(--font-mono);
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-muted);
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }
    .msg.user .msg-header { color: #60a5fa; }
    .msg.assistant .msg-header { color: #34d399; }
    .msg-body {
      white-space: pre-wrap;
      word-break: break-word;
    }
    .tool-box {
      margin-top: 8px;
      padding: 10px 12px;
      background: #070a12;
      border: 1px solid #1e293b;
      border-left: 3px solid var(--accent-cyan);
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: #93c5fd;
      overflow-x: auto;
    }
    .tool-result {
      margin-top: 6px;
      padding: 8px 10px;
      background: #05070c;
      border-radius: 4px;
      color: #a7f3d0;
      font-family: var(--font-mono);
      font-size: 11.5px;
      max-height: 220px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    /* Composer Footer */
    .composer {
      padding: 14px 20px;
      background: var(--bg-panel);
      border-top: 1px solid var(--border);
      flex-shrink: 0;
    }
    .composer-inner {
      max-width: 920px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .composer-row {
      display: flex;
      gap: 10px;
      align-items: flex-end;
    }
    textarea {
      flex: 1;
      background: var(--bg-input);
      color: var(--text-main);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 11px 14px;
      font-family: var(--font-sans);
      font-size: 14px;
      resize: none;
      min-height: 46px;
      max-height: 150px;
      outline: none;
    }
    textarea:focus {
      border-color: var(--border-focus);
    }
    .composer-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      color: var(--text-muted);
      flex-wrap: wrap;
      gap: 8px;
    }
    .goal-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      user-select: none;
      color: #cbd5e1;
    }
    .goal-toggle input {
      accent-color: var(--accent-blue);
      width: 15px;
      height: 15px;
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <span class="brand-badge">AGY CLI / SDK</span>
      <div>
        <div class="brand-title">Antigravity Cloud Terminal</div>
        <div class="brand-sub">สั่งงาน AI อัตโนมัติ & ควบคุมระบบ Google Colab 100%</div>
      </div>
    </div>
    <div class="status-pills">
      <span id="pill-env" class="pill">กำลังตรวจระบบ...</span>
      <span id="pill-gpu" class="pill">GPU: -</span>
      <span id="pill-keys" class="pill">Keys: -</span>
      <span id="pill-drive" class="pill">Drive: -</span>
    </div>
    <div class="nav-actions">
      <button class="btn" onclick="selfUpdateGit()">อัปเดตโค้ดจาก Git</button>
      <button class="btn" onclick="syncDrive()">ซิงก์เข้า Drive</button>
      <button class="btn" onclick="resetSession()">ล้างหน้าจอ</button>
      <a href="/" class="btn btn-primary">เปิดหน้าหลัก Studio</a>
    </div>
  </header>

  <div class="quickbar">
    <button class="chip" onclick="sendQuick('ตรวจสอบสถานะ GPU, พื้นที่ดิสก์ และความพร้อมของระบบในตอนนี้ให้หน่อย')">เช็กสถานะ GPU & ระบบ</button>
    <button class="chip" onclick="sendQuick('แสดงรายการสินค้าทั้งหมดใน _Docs/products.json และดูว่ามีคลิปรุ่นไหนเรนเดอร์เสร็จแล้วบ้าง')">ดูรายการสินค้า & คลิป</button>
    <button class="chip" onclick="sendQuick('!git status -s && git log -n 3 --oneline')">เช็กสถานะ Git ล่าสุด</button>
    <button class="chip" onclick="sendQuick('!nvidia-smi')">รัน nvidia-smi</button>
    <button class="chip" onclick="sendQuick('!rm -rf 01_Raw/test_protect')">ทดสอบ Safety Guard (ป้องกันลบไฟล์)</button>
    <button class="chip" onclick="sendQuick('ตรวจสอบไฟล์ MP4 ใน 04_Exports/Ready_to_post/ และซิงก์เข้า Google Drive ให้หน่อย')">ซิงก์คลิปเข้า Google Drive</button>
  </div>

  <main id="stream" class="terminal-stream">
    <div class="msg assistant">
      <div class="msg-header">
        <span>AGY CLOUD AGENT</span>
        <span>READY</span>
      </div>
      <div class="msg-body">สวัสดีครับ! ผมคือ <b>AGY (Antigravity Cloud Agent)</b> ประจำเซิร์ฟเวอร์นี้
คุณสามารถพิมพ์สั่งงานผมเป็นภาษาคนได้ทุกอย่าง เช่น:
• สั่งผลิตคลิป / แก้สคริปต์ / ตรวจสอบเสียงพากย์และซับไตเติล
• สั่งแก้โค้ด แก้บั๊ก รันชุดทดสอบ หรือดึงโค้ดล่าสุดจาก GitHub
• พิมพ์นำหน้าด้วย <code>!</code> เพื่อรันคำสั่ง Linux Shell โดยตรง (เช่น <code>!nvidia-smi</code> หรือ <code>!git status</code>)
• ติ๊กเปิดโหมด <b>ทำงานอัตโนมัติจนจบเป้าหมาย (/goal)</b> เพื่อให้ผมวางแผนและลุยงานหลายขั้นตอนต่อเนื่องจนเสร็จ</div>
    </div>
  </main>

  <footer class="composer">
    <div class="composer-inner">
      <div class="composer-row">
        <textarea id="promptInput" rows="2" placeholder="พิมพ์คำสั่งให้ AGY ทำงาน หรือพิมพ์ !ตามด้วยคำสั่ง Linux (กด Enter เพื่อส่ง, Shift+Enter ขึ้นบรรทัดใหม่)..."></textarea>
        <button id="sendBtn" class="btn btn-primary" style="height: 46px; padding: 0 22px;" onclick="submitPrompt()">ส่งคำสั่ง</button>
      </div>
      <div class="composer-controls">
        <label class="goal-toggle">
          <input type="checkbox" id="goalModeCheck" />
          <span>เปิดโหมดเป้าหมายอัตโนมัติ (/goal — ลุยงานต่อเนื่องหลายขั้นตอนจนเสร็จ)</span>
        </label>
        <span id="sessionLabel">Session: เริ่มต้น</span>
      </div>
    </div>
  </footer>

  <script>
    let currentSessionId = null;
    let isBusy = false;

    async function refreshStatus() {
      try {
        const res = await fetch('/api/agy/status');
        const data = await res.json();
        const envEl = document.getElementById('pill-env');
        const gpuEl = document.getElementById('pill-gpu');
        const keysEl = document.getElementById('pill-keys');
        const driveEl = document.getElementById('pill-drive');

        envEl.textContent = data.is_colab ? 'Colab Cloud' : 'Local Server';
        envEl.className = 'pill ok';

        if (data.gpu && data.gpu.available) {
          gpuEl.textContent = `GPU: ${data.gpu.name} (${data.gpu.vram_used_mb}/${data.gpu.vram_total_mb} MB)`;
          gpuEl.className = 'pill ok';
        } else {
          gpuEl.textContent = 'GPU: CPU Mode';
          gpuEl.className = 'pill warn';
        }

        keysEl.textContent = `API Keys: ${data.api_keys_count} คีย์`;
        keysEl.className = data.api_keys_count > 0 ? 'pill ok' : 'pill warn';

        driveEl.textContent = data.drive_mounted ? 'Drive: เชื่อมต่อแล้ว' : 'Drive: ไม่ได้เชื่อม';
        driveEl.className = data.drive_mounted ? 'pill ok' : 'pill';
      } catch (e) {
        console.error('Status check failed:', e);
      }
    }

    function appendUserMessage(text, goalMode) {
      const stream = document.getElementById('stream');
      const div = document.createElement('div');
      div.className = 'msg user';
      div.innerHTML = `
        <div class="msg-header">
          <span>USER COMMAND ${goalMode ? '(GOAL MODE)' : ''}</span>
          <span>${new Date().toLocaleTimeString('th-TH')}</span>
        </div>
        <div class="msg-body"></div>
      `;
      div.querySelector('.msg-body').textContent = text;
      stream.appendChild(div);
      stream.scrollTop = stream.scrollHeight;
    }

    function createAssistantContainer() {
      const stream = document.getElementById('stream');
      const div = document.createElement('div');
      div.className = 'msg assistant';
      div.innerHTML = `
        <div class="msg-header">
          <span>AGY CLOUD AGENT</span>
          <span class="step-status">กำลังทำงาน...</span>
        </div>
        <div class="events-log"></div>
        <div class="msg-body" style="margin-top: 8px;"></div>
      `;
      stream.appendChild(div);
      stream.scrollTop = stream.scrollHeight;
      return div;
    }

    async function submitPrompt() {
      if (isBusy) return;
      const input = document.getElementById('promptInput');
      const text = input.value.trim();
      if (!text) return;

      const goalMode = document.getElementById('goalModeCheck').checked;
      input.value = '';
      isBusy = true;
      document.getElementById('sendBtn').disabled = true;

      appendUserMessage(text, goalMode);
      const container = createAssistantContainer();
      const eventsLog = container.querySelector('.events-log');
      const bodyEl = container.querySelector('.msg-body');
      const statusEl = container.querySelector('.step-status');
      const stream = document.getElementById('stream');

      try {
        const res = await fetch('/api/agy/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            session_id: currentSessionId,
            goal_mode: goalMode
          })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\\n\\n');
          buffer = parts.pop() || '';

          for (const chunk of parts) {
            const line = chunk.trim();
            if (!line.startsWith('data:')) continue;
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;

            const ev = JSON.parse(jsonStr);
            if (ev.session_id) {
              currentSessionId = ev.session_id;
              document.getElementById('sessionLabel').textContent = `Session: ${currentSessionId}`;
            }

            if (ev.type === 'thinking') {
              statusEl.textContent = `กำลังคิด (Step ${ev.step || 1})...`;
              bodyEl.textContent = ev.text;
            } else if (ev.type === 'tool_call') {
              statusEl.textContent = `กำลังรัน ${ev.tool}...`;
              const tb = document.createElement('div');
              tb.className = 'tool-box';
              tb.textContent = `▶ [${ev.tool}] ${JSON.stringify(ev.args)}`;
              eventsLog.appendChild(tb);
            } else if (ev.type === 'tool_result') {
              const tr = document.createElement('div');
              tr.className = 'tool-result';
              const r = ev.result || {};
              const preview = r.stdout || r.content || JSON.stringify(r);
              tr.textContent = String(preview).slice(0, 1200);
              eventsLog.appendChild(tr);
            } else if (ev.type === 'answer') {
              statusEl.textContent = `สำเร็จ (${ev.steps || 1} ขั้นตอน)`;
              bodyEl.textContent = ev.text;
            } else if (ev.type === 'error') {
              statusEl.textContent = 'เกิดข้อผิดพลาด';
              bodyEl.textContent = ev.message || 'Error';
            }
            stream.scrollTop = stream.scrollHeight;
          }
        }
      } catch (err) {
        statusEl.textContent = 'การเชื่อมต่อขัดข้อง';
        bodyEl.textContent = 'เกิดข้อผิดพลาด: ' + err.message;
      } finally {
        isBusy = false;
        document.getElementById('sendBtn').disabled = false;
      }
    }

    function sendQuick(cmd) {
      document.getElementById('promptInput').value = cmd;
      submitPrompt();
    }

    async function selfUpdateGit() {
      sendQuick('!git fetch origin main && git pull --ff-only origin main');
    }

    async function syncDrive() {
      sendQuick('!python -c "from scripts.agy_cloud_agent import AGYWorkspaceTools; print(AGYWorkspaceTools().sync_to_drive())"');
    }

    async function resetSession() {
      if (currentSessionId) {
        await fetch(`/api/agy/sessions/${currentSessionId}`, { method: 'DELETE' });
        currentSessionId = null;
      }
      document.getElementById('sessionLabel').textContent = 'Session: เริ่มต้นใหม่';
      document.getElementById('stream').innerHTML = '';
    }

    document.getElementById('promptInput').addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitPrompt();
      }
    });

    refreshStatus();
    setInterval(refreshStatus, 15000);
  </script>
</body>
</html>
"""


@router.get("/agy", response_class=HTMLResponse)
def serve_agy_web_terminal() -> HTMLResponse:
    """Serve the interactive AGY Cloud Web Terminal UI."""
    return HTMLResponse(content=AGY_WEB_TERMINAL_HTML, status_code=200)
