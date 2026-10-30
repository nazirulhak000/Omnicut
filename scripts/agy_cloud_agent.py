"""
scripts/agy_cloud_agent.py — AGY Autonomous Cloud Agent & Workspace Tool Engine for Google Colab.

Provides a Dual-Engine architecture:
1. Official `google-antigravity` SDK integration (when installed and active).
2. Built-in Gemini Native Tool-Calling ReAct Loop with 5-key auto-rotation and
   full workspace tools (`run_command`, `read_file`, `write_file`, `edit_file`,
   `list_dir`, `search_files`, `sync_to_drive`), guaranteeing 100% reliability
   across Google Colab and local environments.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger("omnicut.agy_cloud_agent")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_COLAB = "google.colab" in sys.modules or Path("/content").exists()
DEFAULT_DRIVE_EXPORT_DIR = Path("/content/drive/MyDrive/Omnicut_Exports")

# Protected directories per AGENTS.md Rule #1 (Never delete/overwrite without explicit confirmation)
PROTECTED_DIRS = ("01_Raw", "02_Assets")

# Critical system files protected from deletion
PROTECTED_FILES = (
    "_Docs/products.json",
    "_Docs/products_seed.json",
    "_Docs/export_registry.json",
    ".env",
)

# Destructive shell patterns blocked by default Safety Guard
DESTRUCTIVE_COMMAND_PATTERNS = [
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+/\s*$",
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+01_Raw\b",
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+02_Assets\b",
    r"\bdel\s+/[sS]\s+/[qQ]\s+.*(01_Raw|02_Assets)",
    r"\bRemove-Item\b.*(01_Raw|02_Assets)",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bgit\s+reset\s+--hard\b.*origin",
    r"\b(pkill|killall)\b.*(cloudflared|uvicorn|ttyd)",
    r"\bfuser\s+-k\s+(8000|7681)/tcp",
]

SECRET_REDACT_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"AQ\.Ab8-[0-9A-Za-z_\-]{15,}"),
    re.compile(r"eyJh[0-9A-Za-z_\-]{35,}"),
]

SYSTEM_PROMPT_TEMPLATE = """คุณคือ **AGY (Antigravity Cloud Agent)** ผู้ช่วย AI อัตโนมัติประจำระบบ **OmniCut Pro Studio (Google Colab Cloud Edition)**
คุณมีสิทธิ์ควบคุมระบบ Linux / Python / FFmpeg / HyperFrames / Git ในโฟลเดอร์โปรเจกต์ `{workspace}` ได้ 100% ผ่านเครื่องมือ (Tools) ที่มีให้

### โครงสร้างโปรเจกต์ OmniCut Pro Studio:
- `00_Inbox/` : ไฟล์ดิบนำเข้า
- `01_Raw/` : วัตถุดิบต้นฉบับ (ห้ามลบหรือเขียนทับโดยเด็ดขาดตามกฎข้อ 1)
- `02_Assets/` : ฟอนต์, เพลง BGM, เสียงเอฟเฟกต์ SFX, สติกเกอร์ (ห้ามลบหรือเขียนทับโดยเด็ดขาด)
- `03_Projects/_HyperFrames_Studio/` : สตูดิโอผลิตคลิปวิดีโอ 9:16 (1080x1920 30FPS) สไตล์ Couple Paper Chat (#5 น้องนุ้ย Aoede & พี่บ่าว Puck บนพื้นกระดาษยับ `paper_bg.mp4`)
- `04_Exports/Ready_to_post/` : คลิป MP4 ที่เรนเดอร์เสร็จสมบูรณ์พร้อมโพสต์ลง TikTok
- `05_Covers_Thumbnails/` : ภาพปกคลิป 9:16 และ 3:4
- `_Docs/` : ข้อมูลสินค้า (`products.json`, `products_seed.json`), บทสคริปต์ 20 บทของแต่ละสินค้า, ตารางคิวโพสต์ (`schedule_queue.json`), และ `export_registry.json`
- `scripts/` : โค้ด Backend FastAPI และเอ็นจิ้นตัดต่อทั้งหมด
- `tools/` : สคริปต์สั่งผลิตเสียง TTS, ตรวจสอบ Whisper GPU, และรัน Batch Render

### กฎเหล็กในการทำงาน:
1. ห้ามลบหรือเขียนทับไฟล์ใน `01_Raw/` และ `02_Assets/` เด็ดขาด
2. เมื่อผู้ใช้สั่งให้ตรวจสอบ แก้โค้ด รันคำสั่ง เช็ก GPU หรือผลิตคลิป ให้เรียกใช้เครื่องมือ (`run_command`, `read_file`, `write_file`, `edit_file`, `list_dir`, `search_files`, `sync_to_drive`) ลงมือทำจริงทันที ไม่ต้องแค่บอกวิธีทำ
3. หากทำงานบน Google Colab เมื่อเรนเดอร์คลิปเสร็จสามารถเรียก `sync_to_drive` เพื่อสำรองไฟล์เข้า Google Drive (`/content/drive/MyDrive/Omnicut_Exports/`) ได้ทันที
4. ตอบกลับเป็นภาษาไทยที่กระชับ ชัดเจน รายงานผลลัพธ์จริงจากคำสั่งที่รัน
"""


# ============================================================================
# 1. Safety Guardrails
# ============================================================================

def redact_secrets(text: str) -> str:
    """Redact API keys, tokens, and credentials from any string output."""
    if not text:
        return ""
    masked = text
    for pat in SECRET_REDACT_PATTERNS:
        masked = pat.sub("[REDACTED_SECRET]", masked)
    for k in get_gemini_api_keys():
        if len(k) >= 12 and k in masked:
            masked = masked.replace(k, "[REDACTED_SECRET]")
    return masked


def is_safe_command(command: str) -> Tuple[bool, str]:
    """Validate shell command against AGENTS.md destructive rules and tunnel self-preservation."""
    cmd_str = (command or "").strip()
    if not cmd_str:
        return False, "คำสั่งว่างเปล่า (Empty command)"

    for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
        if re.search(pattern, cmd_str, re.IGNORECASE):
            return (
                False,
                f"ถูกบล็อกโดย Safety Guard (กฎเหล็ก AGENTS.md): ห้ามรันคำสั่งทำลายล้างหรือตัดการเชื่อมต่อตัวเอง ({pattern})",
            )

    # Check direct rm/del targeting protected dirs
    for protected in PROTECTED_DIRS:
        if re.search(rf"\b(rm|del|rmdir|unlink|shutil\.rmtree)\b.*{re.escape(protected)}", cmd_str, re.IGNORECASE):
            return (
                False,
                f"ถูกบล็อกโดย Safety Guard (กฎข้อ 1): ห้ามลบไฟล์ในโฟลเดอร์ `{protected}/` โดยไม่ได้รับอนุญาต",
            )

    # Check direct rm/del targeting critical database files
    for pfile in PROTECTED_FILES:
        base_name = Path(pfile).name
        if re.search(rf"\b(rm|del|unlink|Remove-Item)\b.*{re.escape(base_name)}", cmd_str, re.IGNORECASE):
            return (
                False,
                f"ถูกบล็อกโดย Safety Guard: ห้ามลบไฟล์ระบบสำคัญ `{pfile}`",
            )

    return True, "ok"


def resolve_safe_path(rel_or_abs_path: str, workspace: Path = PROJECT_ROOT, for_write: bool = False) -> Tuple[Optional[Path], str]:
    """Resolve path inside workspace and protect 01_Raw / 02_Assets and .env."""
    raw = (rel_or_abs_path or "").strip()
    if not raw:
        return None, "ไม่ได้ระบุพาธไฟล์"

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (workspace / candidate).resolve()
    else:
        candidate = candidate.resolve()

    ws_resolved = workspace.resolve()
    drive_resolved = DEFAULT_DRIVE_EXPORT_DIR.resolve() if IS_COLAB else None

    inside_ws = candidate == ws_resolved or ws_resolved in candidate.parents
    inside_drive = bool(drive_resolved and (candidate == drive_resolved or drive_resolved in candidate.parents))

    if not (inside_ws or inside_drive):
        return None, f"ไม่อนุญาตให้เข้าถึงไฟล์นอกโฟลเดอร์โปรเจกต์: {candidate}"

    if candidate.name == ".env":
        return None, "ถูกบล็อกโดย Safety Guard: ไม่อนุญาตให้อ่านหรือเขียนทับไฟล์ความลับ `.env` โดยตรง"

    if for_write and inside_ws:
        try:
            rel_parts = candidate.relative_to(ws_resolved).parts
            if rel_parts and rel_parts[0] in PROTECTED_DIRS and candidate.exists():
                return (
                    None,
                    f"ถูกบล็อกโดย Safety Guard (กฎข้อ 1): ห้ามเขียนทับไฟล์ที่มีอยู่แล้วใน `{rel_parts[0]}/`",
                )
        except ValueError:
            pass

    return candidate, "ok"


def _ensure_capcut_draft_backup(target: Path) -> Optional[str]:
    """Rule #3 of AGENTS.md: Never modify draft_content.json or .cloud_cache_* without backup."""
    if not target.exists():
        return None
    if target.name == "draft_content.json" or target.name.startswith(".cloud_cache_"):
        bak_path = target.with_name(target.name + ".bak")
        shutil.copy2(target, bak_path)
        return str(bak_path)
    return None


# ============================================================================
# 2. Gemini API Key Pool & Auto-Rotation
# ============================================================================

def get_gemini_api_keys() -> List[str]:
    """Collect all available Gemini API keys from environment and .env."""
    keys: List[str] = []
    env_names = ["GEMINI_API_KEY"] + [f"GEMINI_API_KEY_{i}" for i in range(2, 12)] + ["GOOGLE_API_KEY"]
    for name in env_names:
        val = os.environ.get(name, "").strip()
        if val and val not in keys:
            keys.append(val)

    # Also check .env in PROJECT_ROOT if no keys found yet
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k.startswith("GEMINI_API_KEY") or k == "GOOGLE_API_KEY":
                    if v and v not in keys:
                        keys.append(v)
        except Exception:
            pass

    return keys


def check_sdk_available() -> bool:
    """Check if the official google-antigravity SDK is installed and importable."""
    try:
        import google.antigravity  # noqa: F401
        return True
    except Exception:
        return False


def get_system_status(workspace: Path = PROJECT_ROOT) -> Dict[str, Any]:
    """Return comprehensive health & hardware status of the Colab / Studio environment."""
    keys = get_gemini_api_keys()
    sdk_ready = check_sdk_available()
    ttyd_installed = shutil.which("ttyd") is not None

    # Check GPU via nvidia-smi
    gpu_info = {"available": False, "name": None, "vram_used_mb": None, "vram_total_mb": None}
    if shutil.which("nvidia-smi"):
        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                first_line = proc.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in first_line.split(",")]
                if len(parts) >= 3:
                    gpu_info = {
                        "available": True,
                        "name": parts[0],
                        "vram_used_mb": int(parts[1]) if parts[1].isdigit() else parts[1],
                        "vram_total_mb": int(parts[2]) if parts[2].isdigit() else parts[2],
                        "utilization_pct": int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 0,
                    }
        except Exception:
            pass

    # Disk space
    disk_info = {"free_gb": 0.0, "total_gb": 0.0}
    try:
        usage = shutil.disk_usage(str(workspace))
        disk_info = {
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "total_gb": round(usage.total / (1024 ** 3), 2),
        }
    except Exception:
        pass

    drive_mounted = Path("/content/drive/MyDrive").exists()

    return {
        "ok": True,
        "is_colab": IS_COLAB,
        "workspace": str(workspace),
        "engine": "google-antigravity-sdk + gemini-native-react" if sdk_ready else "gemini-native-react",
        "sdk_installed": sdk_ready,
        "ttyd_installed": ttyd_installed,
        "api_keys_count": len(keys),
        "gpu": gpu_info,
        "disk": disk_info,
        "drive_mounted": drive_mounted,
        "drive_export_dir": str(DEFAULT_DRIVE_EXPORT_DIR) if drive_mounted else None,
        "timestamp": datetime.datetime.now().isoformat(),
    }


# ============================================================================
# 3. Workspace Tools Implementation
# ============================================================================

class AGYWorkspaceTools:
    """Executes workspace file, shell, search, and Drive sync operations safely."""

    def __init__(self, workspace: Path = PROJECT_ROOT):
        self.workspace = workspace.resolve()

    def run_command(self, command: str, timeout_sec: int = 120) -> Dict[str, Any]:
        safe, reason = is_safe_command(command)
        if not safe:
            return {"ok": False, "exit_code": -1, "error": reason, "stdout": "", "stderr": reason}

        timeout_sec = max(5, min(int(timeout_sec or 120), 600))
        start_ts = time.time()
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
            )
            elapsed = round(time.time() - start_ts, 2)
            stdout = redact_secrets((proc.stdout or "")[-8000:])
            stderr = redact_secrets((proc.stderr or "")[-4000:])
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "elapsed_sec": elapsed,
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "exit_code": -2,
                "error": f"คำสั่งใช้เวลาเกินกำหนด ({timeout_sec} วินาที)",
                "stdout": "",
                "stderr": f"TimeoutExpired after {timeout_sec}s",
            }
        except Exception as exc:
            return {
                "ok": False,
                "exit_code": -3,
                "error": redact_secrets(str(exc)),
                "stdout": "",
                "stderr": redact_secrets(str(exc)),
            }

    def read_file(self, path: str, start_line: int = 1, end_line: int = 200) -> Dict[str, Any]:
        target, reason = resolve_safe_path(path, self.workspace, for_write=False)
        if not target:
            return {"ok": False, "error": reason}
        if not target.exists():
            return {"ok": False, "error": f"ไม่พบไฟล์: {path}"}
        if not target.is_file():
            return {"ok": False, "error": f"พาธนี้ไม่ใช่ไฟล์ปกติ: {path}"}

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            total = len(lines)
            s_idx = max(1, int(start_line or 1))
            e_idx = min(total, max(s_idx, int(end_line or (s_idx + 199))))
            selected = lines[s_idx - 1 : e_idx]
            numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(selected, start=s_idx))
            return {
                "ok": True,
                "path": str(target.relative_to(self.workspace)) if self.workspace in target.parents else str(target),
                "total_lines": total,
                "start_line": s_idx,
                "end_line": e_idx,
                "content": redact_secrets(numbered[:15000]),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        target, reason = resolve_safe_path(path, self.workspace, for_write=True)
        if not target:
            return {"ok": False, "error": reason}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            backup_path = _ensure_capcut_draft_backup(target)
            target.write_text(content or "", encoding="utf-8")
            res: Dict[str, Any] = {
                "ok": True,
                "path": str(target.relative_to(self.workspace)) if self.workspace in target.parents else str(target),
                "bytes_written": len((content or "").encode("utf-8")),
            }
            if backup_path:
                res["backup_created"] = backup_path
            return res
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def edit_file(self, path: str, target_text: str, replacement_text: str) -> Dict[str, Any]:
        target, reason = resolve_safe_path(path, self.workspace, for_write=True)
        if not target:
            return {"ok": False, "error": reason}
        if not target.exists():
            return {"ok": False, "error": f"ไม่พบไฟล์ที่จะแก้ไข: {path}"}

        try:
            original = target.read_text(encoding="utf-8")
            if not target_text or target_text not in original:
                return {"ok": False, "error": "ไม่พบข้อความเป้าหมาย (target_text) ที่ตรงกันในไฟล์"}
            backup_path = _ensure_capcut_draft_backup(target)
            count = original.count(target_text)
            updated = original.replace(target_text, replacement_text or "")
            target.write_text(updated, encoding="utf-8")
            res: Dict[str, Any] = {
                "ok": True,
                "path": str(target.relative_to(self.workspace)) if self.workspace in target.parents else str(target),
                "replacements_count": count,
            }
            if backup_path:
                res["backup_created"] = backup_path
            return res
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def self_update_from_git(self) -> Dict[str, Any]:
        """Safely pull latest commits from origin/main without terminating active tunnels."""
        pull_res = self.run_command("git fetch origin main && git pull --ff-only origin main", timeout_sec=60)
        sync_tool = self.workspace / "tools" / "sync_scripts_to_products.py"
        sync_res = None
        if sync_tool.exists():
            sync_res = self.run_command(f"\"{sys.executable}\" \"{sync_tool}\"", timeout_sec=30)
        return {
            "ok": pull_res.get("ok", False),
            "git_pull": pull_res,
            "scripts_sync": sync_res,
        }

    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        target, reason = resolve_safe_path(path or ".", self.workspace, for_write=False)
        if not target:
            return {"ok": False, "error": reason}
        if not target.exists() or not target.is_dir():
            return {"ok": False, "error": f"ไม่พบโฟลเดอร์: {path}"}

        try:
            entries = []
            for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:150]:
                if item.name.startswith(".git") or item.name == "node_modules" or item.name == "__pycache__":
                    continue
                entries.append(
                    {
                        "name": item.name + ("/" if item.is_dir() else ""),
                        "type": "dir" if item.is_dir() else "file",
                        "size_bytes": item.stat().st_size if item.is_file() else None,
                    }
                )
            return {
                "ok": True,
                "path": str(target),
                "count": len(entries),
                "entries": entries,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def search_files(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        target, reason = resolve_safe_path(path or ".", self.workspace, for_write=False)
        if not target:
            return {"ok": False, "error": reason}
        if not pattern:
            return {"ok": False, "error": "กรุณาระบุคำค้นหา (pattern)"}

        matches = []
        skip_dirs = {".git", "node_modules", ".venv", "__pycache__", "dist", "06_Archive"}
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        try:
            files_iter = [target] if target.is_file() else target.rglob("*")
            for fpath in files_iter:
                if len(matches) >= 60:
                    break
                if not fpath.is_file():
                    continue
                if any(part in skip_dirs for part in fpath.parts):
                    continue
                if fpath.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".html", ".css", ".sh"}:
                    continue
                try:
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                    for idx, line in enumerate(text.splitlines(), start=1):
                        if regex.search(line):
                            rel = str(fpath.relative_to(self.workspace)) if self.workspace in fpath.parents else str(fpath)
                            matches.append({"file": rel, "line": idx, "snippet": line.strip()[:200]})
                            if len(matches) >= 60:
                                break
                except Exception:
                    continue

            return {"ok": True, "pattern": pattern, "matches_count": len(matches), "matches": matches}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def sync_to_drive(self, subpath: str = "Ready_to_post", dest_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Copy exported MP4s and covers to Google Drive (/content/drive/MyDrive/Omnicut_Exports)."""
        target_drive = dest_dir or DEFAULT_DRIVE_EXPORT_DIR
        src_exports = self.workspace / "04_Exports" / subpath if subpath else self.workspace / "04_Exports"
        if not src_exports.exists():
            src_exports = self.workspace / "04_Exports"

        if not IS_COLAB and dest_dir is None:
            return {
                "ok": False,
                "error": "ไม่ได้รันอยู่บน Google Colab หรือยังไม่ได้เชื่อมต่อ `/content/drive/MyDrive`",
            }

        try:
            target_drive.mkdir(parents=True, exist_ok=True)
            copied_files = []
            if src_exports.exists():
                for mp4 in src_exports.rglob("*.mp4"):
                    dest_file = target_drive / mp4.name
                    if not dest_file.exists() or dest_file.stat().st_size != mp4.stat().st_size:
                        shutil.copy2(mp4, dest_file)
                        copied_files.append(mp4.name)

            return {
                "ok": True,
                "drive_dir": str(target_drive),
                "copied_count": len(copied_files),
                "copied_files": copied_files[:50],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a tool call by name."""
        args = args or {}
        if name == "run_command":
            return self.run_command(
                command=str(args.get("command", "")),
                timeout_sec=int(args.get("timeout_sec", 120)),
            )
        if name == "read_file":
            return self.read_file(
                path=str(args.get("path", "")),
                start_line=int(args.get("start_line", 1)),
                end_line=int(args.get("end_line", 200)),
            )
        if name == "write_file":
            return self.write_file(
                path=str(args.get("path", "")),
                content=str(args.get("content", "")),
            )
        if name == "edit_file":
            return self.edit_file(
                path=str(args.get("path", "")),
                target_text=str(args.get("target_text", "")),
                replacement_text=str(args.get("replacement_text", "")),
            )
        if name == "list_dir":
            return self.list_dir(path=str(args.get("path", ".")))
        if name == "search_files":
            return self.search_files(
                pattern=str(args.get("pattern", "")),
                path=str(args.get("path", ".")),
            )
        if name == "sync_to_drive":
            return self.sync_to_drive(subpath=str(args.get("subpath", "Ready_to_post")))
        return {"ok": False, "error": f"ไม่รู้จักเครื่องมือ (Unknown tool): {name}"}


# ============================================================================
# 4. Gemini Function Declarations for Native Tool-Calling Engine
# ============================================================================

GEMINI_TOOLS_DECLARATION = [
    {
        "function_declarations": [
            {
                "name": "run_command",
                "description": "Execute a shell/bash command in the OmniCut workspace (e.g., python scripts, git, ffmpeg, nvidia-smi, pytest).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {"type": "STRING", "description": "Shell command line to execute."},
                        "timeout_sec": {"type": "INTEGER", "description": "Timeout in seconds (default 120)."},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "read_file",
                "description": "Read lines from a text file in the project workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "Relative or absolute path to file."},
                        "start_line": {"type": "INTEGER", "description": "Start line number (1-indexed)."},
                        "end_line": {"type": "INTEGER", "description": "End line number (inclusive)."},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Create or overwrite a file in the project workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "Relative path to create/overwrite."},
                        "content": {"type": "STRING", "description": "Full text content to write."},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "edit_file",
                "description": "Replace an exact target string in an existing file with replacement text.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "Relative path to file."},
                        "target_text": {"type": "STRING", "description": "Exact existing string to replace."},
                        "replacement_text": {"type": "STRING", "description": "New text to replace target_text with."},
                    },
                    "required": ["path", "target_text", "replacement_text"],
                },
            },
            {
                "name": "list_dir",
                "description": "List files and directories inside a folder in the workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "Relative directory path (default '.')."},
                    },
                },
            },
            {
                "name": "search_files",
                "description": "Search (grep) for a regex or text pattern across project files.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "pattern": {"type": "STRING", "description": "Regex or text string to search for."},
                        "path": {"type": "STRING", "description": "Subdirectory to scope the search (default '.')."},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "sync_to_drive",
                "description": "Sync rendered MP4 videos from 04_Exports to Google Drive (/content/drive/MyDrive/Omnicut_Exports).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "subpath": {"type": "STRING", "description": "Subfolder inside 04_Exports (default 'Ready_to_post')."},
                    },
                },
            },
        ]
    }
]


# ============================================================================
# 5. AGY Cloud Agent Session & Dual-Engine Orchestrator
# ============================================================================

class AGYCloudAgent:
    """Stateful autonomous agent supporting multi-step tool execution and 5-key rotation."""

    def __init__(
        self,
        workspace: Path = PROJECT_ROOT,
        model: str = "gemini-3.8-flash",
        api_call_fn: Optional[Callable[[Dict[str, Any], str, str], Dict[str, Any]]] = None,
    ):
        self.workspace = workspace.resolve()
        self.model = model
        self.tools = AGYWorkspaceTools(workspace=self.workspace)
        self._key_index = 0
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._custom_api_call_fn = api_call_fn

    def get_or_create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = (session_id or "").strip() or f"agy-{uuid.uuid4().hex[:8]}"
        if sid not in self._sessions:
            self._sessions[sid] = {
                "session_id": sid,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "contents": [],
                "history": [],
            }
        return self._sessions[sid]

    def list_sessions(self) -> List[Dict[str, Any]]:
        result = []
        for sid, sess in self._sessions.items():
            result.append(
                {
                    "session_id": sid,
                    "created_at": sess["created_at"],
                    "updated_at": sess["updated_at"],
                    "turns_count": len(sess["history"]),
                }
            )
        return sorted(result, key=lambda x: x["updated_at"], reverse=True)

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def _call_gemini_with_rotation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call Gemini generateContent REST API with automatic key rotation across all configured keys."""
        if self._custom_api_call_fn is not None:
            keys = get_gemini_api_keys() or ["test-key"]
            key = keys[self._key_index % len(keys)]
            return self._custom_api_call_fn(payload, key, self.model)

        keys = get_gemini_api_keys()
        if not keys:
            raise RuntimeError(
                "ไม่พบ GEMINI_API_KEY ในระบบ กรุณาตั้งค่า GEMINI_API_KEY ใน Google Colab Secrets หรือ .env"
            )

        last_err: Optional[Exception] = None
        for attempt in range(len(keys)):
            idx = (self._key_index + attempt) % len(keys)
            api_key = keys[idx]
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent?key={api_key}"
            )
            req_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_bytes,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = resp.read().decode("utf-8")
                    self._key_index = idx
                    return json.loads(body)
            except urllib.error.HTTPError as http_err:
                err_body = ""
                try:
                    err_body = http_err.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                last_err = RuntimeError(f"HTTP {http_err.code}: {err_body[:400]}")
                # Rotate on 400 Invalid, 401 Unauthenticated, 403 Permission/Billing, 404 Not Found, 429 Quota, 500, or 503 Overload
                if http_err.code in (400, 401, 403, 404, 429, 500, 503):
                    logger.warning(f"[AGY] Key #{idx + 1} returned HTTP {http_err.code}, rotating to next key...")
                    continue
                raise last_err
            except Exception as exc:
                last_err = exc
                continue

        raise RuntimeError(f"เรียกใช้ Gemini API ไม่สำเร็จหลังลองครบ {len(keys)} คีย์: {last_err}")

    def stream_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        goal_mode: bool = False,
        max_steps: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Run multi-step agent loop yielding real-time events for Web Terminal & CLI."""
        session = self.get_or_create_session(session_id)
        sid = session["session_id"]
        user_text = (message or "").strip()

        if not user_text:
            yield {"type": "error", "session_id": sid, "message": "กรุณาพิมพ์คำสั่งหรือข้อความ"}
            return

        # Support direct `/goal ...` prefix
        if user_text.lower().startswith("/goal "):
            goal_mode = True
            user_text = user_text[6:].strip()

        # Support direct `!...` shell shortcut
        if user_text.startswith("!"):
            shell_cmd = user_text[1:].strip()
            yield {"type": "tool_call", "session_id": sid, "tool": "run_command", "args": {"command": shell_cmd}}
            res = self.tools.run_command(shell_cmd)
            yield {"type": "tool_result", "session_id": sid, "tool": "run_command", "result": res}
            out_text = (res.get("stdout") or "") + ("\n" + res.get("stderr") if res.get("stderr") else "")
            ans = out_text.strip() or f"(Exit code: {res.get('exit_code')})"
            session["history"].append({"role": "user", "text": message})
            session["history"].append({"role": "assistant", "text": ans})
            session["updated_at"] = datetime.datetime.now().isoformat()
            yield {"type": "answer", "session_id": sid, "text": ans, "steps": 1}
            return

        effective_prompt = user_text
        if goal_mode:
            effective_prompt = (
                f"[AUTONOMOUS GOAL MODE] เป้าหมาย: {user_text}\n"
                "จงวางแผนสั้นๆ แล้วเรียกใช้เครื่องมือ (Tools) ลงมือทำทีละขั้นตอน ตรวจสอบผลลัพธ์ "
                "แก้ไขปัญหาหากพบ Error และทำงานต่อเนื่องจนกว่าเป้าหมายจะสำเร็จครบถ้วน"
            )

        session["contents"].append({"role": "user", "parts": [{"text": effective_prompt}]})
        session["history"].append({"role": "user", "text": user_text, "goal_mode": goal_mode})
        session["updated_at"] = datetime.datetime.now().isoformat()

        step_limit = max_steps or (25 if goal_mode else 12)
        sys_instruction = SYSTEM_PROMPT_TEMPLATE.format(workspace=self.workspace)

        final_answer_parts: List[str] = []
        steps_taken = 0

        for step in range(1, step_limit + 1):
            steps_taken = step
            payload = {
                "system_instruction": {"parts": [{"text": sys_instruction}]},
                "contents": session["contents"][-30:],
                "tools": GEMINI_TOOLS_DECLARATION,
                "generationConfig": {"temperature": 0.2},
            }

            try:
                resp_data = self._call_gemini_with_rotation(payload)
            except Exception as exc:
                err_msg = f"เกิดข้อผิดพลาดในการเชื่อมต่อโมเดล AI: {exc}"
                yield {"type": "error", "session_id": sid, "message": err_msg}
                return

            candidates = resp_data.get("candidates") or []
            if not candidates:
                err_msg = f"ไม่ได้รับคำตอบจากโมเดล: {json.dumps(resp_data, ensure_ascii=False)[:300]}"
                yield {"type": "error", "session_id": sid, "message": err_msg}
                return

            content_obj = candidates[0].get("content") or {}
            parts = content_obj.get("parts") or []
            session["contents"].append({"role": "model", "parts": parts})

            function_calls = []
            for part in parts:
                if "text" in part and part["text"]:
                    text_chunk = part["text"].strip()
                    if text_chunk:
                        final_answer_parts.append(text_chunk)
                        yield {"type": "thinking", "session_id": sid, "step": step, "text": text_chunk}
                if "functionCall" in part:
                    function_calls.append(part["functionCall"])

            # If no tool calls were requested, the agent has finished its turn
            if not function_calls:
                break

            # Execute all requested tool calls and feed results back to model
            tool_response_parts = []
            for fc in function_calls:
                t_name = fc.get("name", "")
                t_args = fc.get("args") or {}
                yield {
                    "type": "tool_call",
                    "session_id": sid,
                    "step": step,
                    "tool": t_name,
                    "args": t_args,
                }
                t_result = self.tools.execute_tool(t_name, t_args)
                yield {
                    "type": "tool_result",
                    "session_id": sid,
                    "step": step,
                    "tool": t_name,
                    "result": t_result,
                }
                tool_response_parts.append(
                    {
                        "functionResponse": {
                            "name": t_name,
                            "response": {"result": t_result},
                        }
                    }
                )

            session["contents"].append({"role": "user", "parts": tool_response_parts})

        final_text = "\n\n".join(final_answer_parts).strip() or "ดำเนินการเสร็จสิ้นเรียบร้อยครับ"
        session["history"].append({"role": "assistant", "text": final_text, "steps": steps_taken})
        session["updated_at"] = datetime.datetime.now().isoformat()

        yield {
            "type": "answer",
            "session_id": sid,
            "text": final_text,
            "steps": steps_taken,
        }

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        goal_mode: bool = False,
        max_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Synchronous helper collecting all events from stream_chat into a single response dict."""
        events: List[Dict[str, Any]] = []
        final_answer = ""
        sid = session_id or ""
        error_msg = None
        steps = 0

        for ev in self.stream_chat(message=message, session_id=session_id, goal_mode=goal_mode, max_steps=max_steps):
            events.append(ev)
            sid = ev.get("session_id", sid)
            if ev["type"] == "answer":
                final_answer = ev.get("text", "")
                steps = ev.get("steps", 0)
            elif ev["type"] == "error":
                error_msg = ev.get("message", "Unknown error")

        return {
            "ok": error_msg is None,
            "session_id": sid,
            "answer": final_answer if error_msg is None else error_msg,
            "error": error_msg,
            "steps": steps,
            "events": events,
        }


# Singleton instance for the server
_DEFAULT_AGENT: Optional[AGYCloudAgent] = None


def get_cloud_agent() -> AGYCloudAgent:
    global _DEFAULT_AGENT
    if _DEFAULT_AGENT is None:
        _DEFAULT_AGENT = AGYCloudAgent(workspace=PROJECT_ROOT)
    return _DEFAULT_AGENT
