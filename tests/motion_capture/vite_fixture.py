"""Self-host the real Vite motion fixture for parity tests.

The server is test-owned: it binds a free loopback port, waits for HTTPS
readiness, and always terminates the exact Node process it started.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Iterator
from urllib.error import URLError
from urllib.request import urlopen

from .capture import REPO_ROOT


FRONTEND_ROOT = REPO_ROOT / "frontend"
VITE_ENTRY = FRONTEND_ROOT / "node_modules" / "vite" / "bin" / "vite.js"


class ViteFixtureUnavailable(RuntimeError):
    """Raised when the test-owned frontend fixture cannot become ready."""


@dataclass(frozen=True)
class ViteFixtureServer:
    url: str
    base_url: str
    port: int
    pid: int


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _read_log(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _wait_until_ready(process: subprocess.Popen[str], url: str, log_path: Path, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    https_context = ssl._create_unverified_context()  # noqa: SLF001 - loopback test certificate
    last_error = "server did not accept a connection"
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            log = _read_log(log_path)
            raise ViteFixtureUnavailable(
                f"Vite fixture exited with code {return_code} before readiness. {log}"
            )
        try:
            with urlopen(url, timeout=0.75, context=https_context) as response:  # noqa: S310 - fixed loopback URL
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except (OSError, URLError) as exc:
            last_error = str(exc)
        time.sleep(0.1)
    log = _read_log(log_path)
    raise ViteFixtureUnavailable(
        f"Vite fixture was not ready after {timeout:.1f}s ({last_error}). {log}"
    )


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@contextmanager
def serve_motion_capture_fixture(timeout: float = 30.0) -> Iterator[ViteFixtureServer]:
    """Yield a deterministic URL backed by the project's real Vite pipeline."""

    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise ViteFixtureUnavailable("Node.js is required for the self-hosted motion fixture")
    if not VITE_ENTRY.exists():
        raise ViteFixtureUnavailable(
            f"Vite is not installed at {VITE_ENTRY}; run npm install in frontend"
        )

    temp_root = REPO_ROOT / ".tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="motion-vite-", dir=temp_root) as temp_dir:
        log_path = Path(temp_dir) / "vite.log"
        port = _free_loopback_port()
        base_url = f"https://127.0.0.1:{port}"
        fixture_url = f"{base_url}/motion_capture.html?in=hook.in.bounce"
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with log_path.open("w", encoding="utf-8", newline="\n") as log_handle:
            process = subprocess.Popen(
                [
                    node,
                    str(VITE_ENTRY),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--strictPort",
                ],
                cwd=FRONTEND_ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creation_flags,
            )
            try:
                _wait_until_ready(process, fixture_url, log_path, timeout)
                yield ViteFixtureServer(
                    url=fixture_url,
                    base_url=base_url,
                    port=port,
                    pid=process.pid,
                )
            finally:
                _stop_process(process)
