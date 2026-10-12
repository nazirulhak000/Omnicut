"""Maintenance (read-only) lock for data migrations (multi-channel P2.3).

While ``<root>/_Docs/.maintenance.lock`` exists every *writer* of that data
root refuses to write:

* ``scripts.db.DocumentTable`` -- ``save()`` and any ``mutate()`` /
  ``scoped_mutate()`` block that would actually change rows raise
  :class:`MaintenanceModeError` (the transaction is rolled back, 0 rows).
  A block that changes nothing still commits (so reads that *might* write,
  e.g. product reconcile, keep working when there is nothing to reconcile).
  The JSON-mirror auto-import is skipped while locked (a hand-edited mirror
  can never clobber the database mid-migration).
* the API (``install_maintenance_gate``) answers every non-GET/HEAD/OPTIONS
  request with 503 ``maintenance_mode``; a refusal raised deeper (e.g. a GET
  whose reconcile wants to write) is also mapped to 503 instead of 500.
* ``TaskManager.create_task`` and the batch-render dispatcher/recovery refuse
  to start new jobs.

Reads keep working.  The migration tool that holds the lock writes through
:func:`bypass` with the lock's own token (a ``ContextVar``: other threads of
the same process stay blocked).

A lock whose owner process is gone (same host, dead pid) is reported as
*stale* but STILL blocks writers: a crashed migration may have left data
half-migrated, so only ``--resume`` / ``--rollback`` (or an explicit
``--release-stale-lock`` after review) may clear it.  A lock file that cannot
be parsed also blocks (fail closed).

Stdlib only (imported by ``scripts/db.py``) -- no import of other project
modules at import time.
"""

from __future__ import annotations

import contextlib
import contextvars
import datetime as _dt
import json
import os
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

LOCK_RELATIVE_PATH = Path("_Docs") / ".maintenance.lock"
ERROR_CODE = "maintenance_mode"
ERROR_CODE_HEADER = "X-OmniCut-Error-Code"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

_BYPASS_TOKEN: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "omnicut_maintenance_bypass", default=None
)


class MaintenanceModeError(RuntimeError):
    """A write was refused because the data root is in maintenance mode."""

    status_code = 503
    code = ERROR_CODE

    def __init__(self, info: Optional[Dict[str, Any]] = None, message: Optional[str] = None):
        self.info = dict(info or {})
        reason = str(self.info.get("reason") or "").strip()
        default = "ระบบอยู่ระหว่างปรับปรุงข้อมูล (maintenance) งดบันทึกชั่วคราว กรุณารอให้ย้ายข้อมูลเสร็จแล้วลองใหม่"
        if reason and message is None:
            default = f"{default} ({reason})"
        super().__init__(message or default)

    def to_body(self) -> Dict[str, Any]:
        return {
            "detail": str(self),
            "code": self.code,
            "maintenance": {
                key: self.info.get(key)
                for key in ("owner", "reason", "started_at", "run_id", "stale")
                if key in self.info
            },
        }


class MaintenanceLockBusy(RuntimeError):
    """``acquire`` found a lock held by someone else."""

    def __init__(self, info: Dict[str, Any]):
        self.info = dict(info)
        stale = " (ค้างจาก process ที่ปิดไปแล้ว)" if info.get("stale") else ""
        super().__init__(
            "มี maintenance lock อยู่แล้ว"
            f"{stale}: owner={info.get('owner')} pid={info.get('pid')} run_id={info.get('run_id')} "
            f"เริ่มเมื่อ {info.get('started_at')}"
        )


# -- paths ------------------------------------------------------------------

def default_root() -> Path:
    from scripts import config  # lazy: keep this module stdlib-only at import

    return Path(config.BASE_DIR)


def lock_path(root: Optional[Path] = None) -> Path:
    return Path(root if root is not None else default_root()) / LOCK_RELATIVE_PATH


def root_for_db(db_path: Path) -> Path:
    """Data root of a store database (``<root>/_Docs/store.db`` and
    ``<root>/03_Projects/batch_render_queue.db`` both map to ``<root>``)."""
    return Path(db_path).parent.parent


# -- process liveness -----------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            # ERROR_ACCESS_DENIED means it exists but belongs to someone else.
            return ctypes.get_last_error() == 5
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


# -- reading --------------------------------------------------------------------

def read_lock(root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Lock info, or ``None`` when no lock file exists.

    Adds ``stale`` (bool) and ``corrupt`` (bool).  Never raises for a
    missing file; an unreadable/garbled file is returned as a corrupt lock
    (which still blocks writers).
    """
    path = lock_path(root)
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        return {"corrupt": True, "stale": False, "reason": "อ่านไฟล์ lock ไม่ได้"}
    try:
        info = json.loads(raw.decode("utf-8"))
        if not isinstance(info, dict):
            raise ValueError("not an object")
    except (UnicodeDecodeError, ValueError):
        return {"corrupt": True, "stale": False, "reason": "ไฟล์ lock เสีย"}
    info = dict(info)
    info["corrupt"] = False
    try:
        pid = int(info.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    same_host = str(info.get("host") or "") == socket.gethostname()
    info["stale"] = bool(same_host and pid and not _pid_alive(pid))
    return info


def is_locked(root: Optional[Path] = None) -> bool:
    return lock_path(root).exists()


def current_bypass_token() -> Optional[str]:
    return _BYPASS_TOKEN.get()


def _blocking_info(root: Optional[Path]) -> Optional[Dict[str, Any]]:
    path = lock_path(root)
    if not path.exists():  # fast path: one stat per write
        return None
    info = read_lock(root)
    if info is None:
        return None
    token = _BYPASS_TOKEN.get()
    if token and not info.get("corrupt") and info.get("token") == token:
        return None
    return info


def is_blocked(root: Optional[Path] = None) -> bool:
    """True when a lock exists and this context does not hold its bypass token."""
    return _blocking_info(root) is not None


def assert_writable(root: Optional[Path] = None) -> None:
    info = _blocking_info(root)
    if info is not None:
        raise MaintenanceModeError(info)


def assert_writable_db(db_path: Path) -> None:
    assert_writable(root_for_db(db_path))


def is_blocked_db(db_path: Path) -> bool:
    return is_blocked(root_for_db(db_path))


# -- acquiring / releasing --------------------------------------------------------

def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _write_new(path: Path, payload: bytes) -> None:
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def acquire(
    root: Path,
    *,
    owner: str,
    reason: str,
    run_id: Optional[str] = None,
    token: Optional[str] = None,
    take_over_stale: bool = False,
    take_over_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create the lock (atomic ``O_EXCL``).  Returns the lock info incl. token.

    ``take_over_token``: an existing lock carrying exactly this token is
    adopted (resume of the same run after a crash).  ``take_over_stale``: a
    lock whose owner process is dead is replaced.  Anything else ->
    :class:`MaintenanceLockBusy`.
    """
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "schema": 1,
        "owner": owner,
        "reason": reason,
        "run_id": run_id,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": _now_iso(),
        "token": token or uuid.uuid4().hex,
    }
    payload = json.dumps(info, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        _write_new(path, payload)
        return dict(info)
    except FileExistsError:
        existing = read_lock(root) or {}
        adopt = bool(take_over_token) and not existing.get("corrupt") and existing.get("token") == take_over_token
        if not adopt and not (take_over_stale and existing.get("stale")):
            raise MaintenanceLockBusy(existing)
        if adopt:
            info["token"] = take_over_token
            payload = json.dumps(info, ensure_ascii=False, indent=2).encode("utf-8")
        tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_bytes(payload)
        _replace(tmp, path)
        confirmed = read_lock(root) or {}
        if confirmed.get("token") != info["token"]:
            raise MaintenanceLockBusy(confirmed)
        return dict(info)


def _replace(src: Path, dst: Path) -> None:
    last: Optional[BaseException] = None
    for attempt in range(20):
        try:
            os.replace(str(src), str(dst))
            return
        except PermissionError as exc:  # Windows: reader holds the file briefly
            last = exc
            time.sleep(0.02 * (attempt + 1))
    assert last is not None
    raise last


def release(root: Path, token: str) -> bool:
    """Remove the lock only when it carries ``token``.  Returns True if removed."""
    info = read_lock(root)
    if info is None:
        return False
    if info.get("corrupt") or info.get("token") != token:
        return False
    path = lock_path(root)
    for attempt in range(20):
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
        except PermissionError:
            time.sleep(0.02 * (attempt + 1))
    return False


@contextlib.contextmanager
def bypass(token: str) -> Iterator[None]:
    """Let the current context write while it holds the lock with ``token``."""
    reset = _BYPASS_TOKEN.set(token)
    try:
        yield
    finally:
        _BYPASS_TOKEN.reset(reset)


# -- worker helpers -------------------------------------------------------------------

def refuse_new_job(root: Optional[Path] = None, *, job_label: str = "งานใหม่") -> None:
    """Raise :class:`MaintenanceModeError` if new jobs must not start."""
    info = _blocking_info(root)
    if info is not None:
        raise MaintenanceModeError(
            info,
            f"ระบบอยู่ระหว่างปรับปรุงข้อมูล (maintenance) ยังเริ่ม{job_label}ไม่ได้ กรุณารอให้ย้ายข้อมูลเสร็จ",
        )


# -- ASGI gate ----------------------------------------------------------------------------

def _error_response(exc: MaintenanceModeError):
    from starlette.responses import JSONResponse

    return JSONResponse(
        exc.to_body(),
        status_code=exc.status_code,
        headers={ERROR_CODE_HEADER: exc.code, "Retry-After": "60"},
    )


class MaintenanceGateMiddleware:
    """Pure ASGI: 503 ``maintenance_mode`` for non-safe methods while locked.

    The lock root is resolved per request (``config.BASE_DIR``) so tests can
    monkeypatch it.  Adds no routes.
    """

    def __init__(self, app, root_fn=None):
        self.app = app
        self._root_fn = root_fn or default_root

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or str(scope.get("method", "GET")).upper() in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        info = _blocking_info(self._root_fn())
        if info is not None:
            await _error_response(MaintenanceModeError(info))(scope, receive, send)
            return
        await self.app(scope, receive, send)


async def maintenance_error_handler(_request, exc: MaintenanceModeError):
    return _error_response(exc)


def install_maintenance_gate(app, *, root_fn=None) -> None:
    """Register the gate middleware + the 503 exception mapping (no routes)."""
    app.add_middleware(MaintenanceGateMiddleware, root_fn=root_fn)
    app.add_exception_handler(MaintenanceModeError, maintenance_error_handler)
