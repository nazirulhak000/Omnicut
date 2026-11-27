"""
FastAPI router for the OmniCut Two-Tier Mobile HTTPS Bridge.

Endpoints:
- ``GET  /api/mobile-bridge/status``          (local-only)
- ``POST /api/mobile-bridge/toggle``          (local-only)
- ``GET  /api/mobile-bridge/password``        (strictly local-only, 403 on remote/forwarded)
- ``POST /api/mobile-bridge/password/rotate`` (strictly local-only, 403 on remote/forwarded)
- ``GET  /api/mobile-bridge/ca.crt``          (LAN/local read-only CA download for iOS trust)
"""

from __future__ import annotations

import ipaddress
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from scripts import auth
from scripts.mobile_bridge import (
    generate_human_password,
    mobile_bridge_manager,
    persist_app_password,
)
from scripts.tls_cert_manager import ensure_ca

router = APIRouter(prefix="/api/mobile-bridge", tags=["Mobile Bridge"])


class MobileBridgeToggleRequest(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[Literal["lan_https", "tailscale", "public"]] = None


def _client_host(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _require_local(request: Request) -> None:
    if auth.classify_request(_client_host(request), request.headers) != "local":
        raise HTTPException(status_code=403, detail="Local access only")


def _is_lan_or_local(request: Request) -> bool:
    if auth.has_forward_headers(request.headers):
        return False
    host = (_client_host(request) or "").strip().lower()
    if not host:
        return False
    if host in ("testclient", "localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
        return ip.is_loopback or ip.is_private or ip.is_link_local
    except ValueError:
        return False


@router.get("/status")
def get_mobile_bridge_status(request: Request):
    _require_local(request)
    return mobile_bridge_manager.get_status()


@router.post("/toggle")
async def toggle_mobile_bridge(request: Request, payload: Optional[MobileBridgeToggleRequest] = None):
    _require_local(request)
    body = payload or MobileBridgeToggleRequest()

    if body.mode is not None:
        mobile_bridge_manager.mode = body.mode

    target_enabled = body.enabled
    if target_enabled is None:
        if body.mode is None:
            target_enabled = not mobile_bridge_manager.enabled
        else:
            target_enabled = mobile_bridge_manager.enabled

    if target_enabled:
        return await mobile_bridge_manager.start(request.app, mode=body.mode)
    return await mobile_bridge_manager.stop()


@router.get("/password")
def get_mobile_bridge_password(request: Request):
    _require_local(request)
    return {
        "password": auth.get_app_password(),
        "configured": auth.is_password_configured(),
    }


@router.post("/password/rotate")
def rotate_mobile_bridge_password(request: Request):
    _require_local(request)
    new_password = generate_human_password(8)
    persist_app_password(new_password)
    return {
        "password": new_password,
        "configured": True,
    }


@router.get("/ca.crt")
def download_mobile_bridge_ca(request: Request):
    if not _is_lan_or_local(request):
        raise HTTPException(status_code=403, detail="LAN or local access only")
    ca_crt_path, _ = ensure_ca(mobile_bridge_manager._cert_dir)
    return Response(
        content=ca_crt_path.read_bytes(),
        media_type="application/x-x509-ca-cert",
        headers={"Content-Disposition": 'attachment; filename="OmniCut-Root-CA.crt"'},
    )
