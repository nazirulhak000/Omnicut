"""
In-process Two-Tier Mobile HTTPS Bridge for OmniCut Pro Studio.

Primary FastAPI stays on 127.0.0.1:8000 (or configured bind host).
When enabled, this manager runs an in-process secondary ``uvicorn.Server``
asyncio task on ``0.0.0.0:8443`` (or ``OMNICUT_MOBILE_TLS_PORT``) with TLS
certificates from ``scripts.tls_cert_manager``, sharing the exact same FastAPI
``app``, ``TaskManager``, ``RenderSlotPool``, SSE, and SQLite state.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import uvicorn

from scripts import auth
from scripts.media_service import get_local_ip
from scripts.tls_cert_manager import ensure_server_cert

logger = logging.getLogger("omnicut.mobile_bridge")

BridgeMode = Literal["lan_https", "tailscale", "public"]
_VALID_MODES = {"lan_https", "tailscale", "public"}

# Unambiguous uppercase + digits (excludes 0/O, 1/I/l) for easy phone entry.
_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEFAULT_TLS_PORT = 8443


def get_configured_tls_port() -> int:
    raw = (os.environ.get("OMNICUT_MOBILE_TLS_PORT") or "").strip()
    if raw:
        try:
            port = int(raw)
            if 1 <= port <= 65535:
                return port
        except ValueError:
            pass
    return DEFAULT_TLS_PORT


def generate_human_password(length: int = 8) -> str:
    """Generate a random 8-char human-typable password (never '12345678')."""
    if length < 8:
        length = 8
    while True:
        candidate = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
        if candidate != "12345678":
            return candidate


def persist_app_password(password: str, env_file: Optional[Path] = None) -> Path:
    """Persist ``OMNICUT_APP_PASSWORD`` to ``.env`` and update ``os.environ``."""
    target = Path(env_file) if env_file is not None else auth.ENV_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if target.exists():
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []

    updated = False
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _ = stripped.split("=", 1)
            if key.strip() == "OMNICUT_APP_PASSWORD":
                new_lines.append(f"OMNICUT_APP_PASSWORD={password}")
                updated = True
                continue
        new_lines.append(line)

    if not updated:
        new_lines.append(f"OMNICUT_APP_PASSWORD={password}")

    target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ["OMNICUT_APP_PASSWORD"] = password
    return target


def ensure_bridge_password(env_file: Optional[Path] = None) -> Optional[str]:
    """Ensure ``OMNICUT_APP_PASSWORD`` is set when auth is not disabled."""
    if auth.is_auth_disabled():
        return None
    existing = auth.get_app_password()
    if existing:
        return existing
    generated = generate_human_password(8)
    persist_app_password(generated, env_file=env_file)
    return generated


def detect_tailscale_url() -> Optional[str]:
    """Detect active Tailscale HTTPS origin via ``tailscale status --json``."""
    if not shutil.which("tailscale"):
        return None
    try:
        proc = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        backend_state = str(data.get("BackendState") or "")
        if backend_state and backend_state.lower() != "running":
            return None
        self_info = data.get("Self") or {}
        dns_name = str(self_info.get("DNSName") or "").strip().rstrip(".")
        if not dns_name:
            return None
        return f"https://{dns_name}"
    except Exception:
        return None


def count_active_uploads() -> int:
    """Count in-progress chunked uploads in staging without raising."""
    try:
        from scripts.api_uploads import get_staging_dir

        staging_dir = get_staging_dir()
        if not staging_dir.exists():
            return 0
        count = 0
        for meta_file in staging_dir.glob("*.meta.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                if data.get("status") not in ("completed", "cancelled", "failed"):
                    count += 1
            except Exception:
                continue
        return count
    except Exception:
        return 0


def count_active_filming_sessions() -> int:
    """Count active guided-take filming sessions without raising."""
    try:
        from scripts.recording_sessions import RecordingSessionStore

        sessions = RecordingSessionStore.list_sessions()
        return sum(
            1 for s in sessions
            if str(s.get("status") or "").lower() in ("active", "recording", "open", "pending")
        )
    except Exception:
        return 0


class MobileBridgeManager:
    """Manages the in-process secondary TLS uvicorn task on ``0.0.0.0:8443``."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.mode: BridgeMode = "lan_https"
        self._server: Optional[uvicorn.Server] = None
        self._task: Optional[asyncio.Task] = None
        self._lan_ip: Optional[str] = None
        self._cert_dir: Optional[Path] = None

    @property
    def tls_port(self) -> int:
        return get_configured_tls_port()

    def _create_uvicorn_server(
        self,
        app: Any,
        host: str,
        port: int,
        certfile: Path,
        keyfile: Path,
    ) -> uvicorn.Server:
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            ssl_certfile=str(certfile),
            ssl_keyfile=str(keyfile),
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        # Never let the secondary listener hijack primary SIGINT/SIGTERM handlers.
        server.install_signal_handlers = lambda: None
        return server

    async def start(
        self,
        app: Any,
        mode: Optional[BridgeMode] = None,
        cert_dir: Optional[Path] = None,
        env_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        if mode is not None and mode in _VALID_MODES:
            self.mode = mode
        if cert_dir is not None:
            self._cert_dir = Path(cert_dir)

        ensure_bridge_password(env_file=env_file)

        lan_ip = get_local_ip(force=True)
        self._lan_ip = lan_ip

        if self._task is not None and not self._task.done():
            self.enabled = True
            return self.get_status()

        cert_path, key_path = ensure_server_cert(lan_ip, cert_dir=self._cert_dir)
        bind_host = os.environ.get("OMNICUT_MOBILE_BIND_HOST", "0.0.0.0").strip() or "0.0.0.0"
        server = self._create_uvicorn_server(
            app=app,
            host=bind_host,
            port=self.tls_port,
            certfile=cert_path,
            keyfile=key_path,
        )
        self._server = server
        self._task = asyncio.create_task(server.serve(), name="omnicut-mobile-tls-bridge")
        self.enabled = True
        logger.info("Mobile HTTPS bridge started on https://%s:%s", lan_ip, self.tls_port)
        return self.get_status()

    async def stop(self) -> Dict[str, Any]:
        server = self._server
        task = self._task
        self._server = None
        self._task = None
        self.enabled = False

        if server is not None:
            server.should_exit = True
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except asyncio.TimeoutError:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            except Exception:
                pass
        logger.info("Mobile HTTPS bridge stopped")
        return self.get_status()

    def get_active_tailscale_url(self) -> Optional[str]:
        if not self.enabled:
            return None
        return detect_tailscale_url()

    def get_status(self) -> Dict[str, Any]:
        lan_ip = self._lan_ip or get_local_ip()
        tls_port = self.tls_port
        lan_url = f"https://{lan_ip}:{tls_port}" if lan_ip and lan_ip != "127.0.0.1" else f"https://127.0.0.1:{tls_port}"
        tailscale_url = detect_tailscale_url()
        public_url = (os.environ.get("OMNICUT_PUBLIC_URL") or "").strip().rstrip("/") or None

        return {
            "enabled": bool(self.enabled),
            "mode": self.mode,
            "urls": {
                "lan_https": lan_url,
                "tailscale": tailscale_url,
                "public": public_url,
            },
            "tls_port": tls_port,
            "password_configured": auth.is_password_configured(),
            "auth_disabled_warning": auth.is_auth_disabled(),
            "active_uploads": count_active_uploads(),
            "active_filming_sessions": count_active_filming_sessions(),
        }


mobile_bridge_manager = MobileBridgeManager()
