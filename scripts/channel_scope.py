"""Channel scope resolution + enforcement (multi-channel foundation, P1).

Contract (full text: ``_Docs/Plans/ADR_MULTI_CHANNEL_20261010.md``):

* Scope travels in the ``X-OmniCut-Channel`` header (channel id slug).
  ``?channel=<id>`` is accepted only on routes whose policy row sets
  ``allow_query_scope`` (media-style GET used in ``<img>/<video>`` src).
* A header/query naming an invalid or unknown channel is ALWAYS rejected
  with 422 (never falls back).  Conflicting header/query values -> 422.
* ``channel``-class route without scope: strict mode -> 422; compatibility
  mode (default) -> implicit ``main`` (loaded lazily: no registry read, no
  behaviour change for existing clients).
* ``shared``/``global`` routes are not scope-gated (header still validated
  when present, unless the row sets ``ignore_scope_header``).
* A ``channel_id`` in a request body never overrides the header scope; the
  middleware never reads request bodies.

:class:`ChannelScopeMiddleware` is a pure ASGI middleware (no
``BaseHTTPMiddleware``) so streaming/file responses and background tasks are
untouched.  Handlers obtain the scope with ``Depends(get_channel_scope)``.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Iterable, Optional, Sequence
from urllib.parse import parse_qsl

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from starlette.routing import Match

from scripts import config
from scripts.channel_route_policy import (
    SCOPE_CHANNEL,
    UNLISTED_ROUTE_POLICY,
    RoutePolicy,
    RoutePolicyTable,
    default_route_policy,
)
from scripts.channel_store import (
    ERROR_CODE_HEADER,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    STATUS_LABEL_TH,
    ChannelError,
    ChannelStore,
    get_default_store,
    is_valid_channel_id,
    readiness as channel_readiness,
)

CHANNEL_HEADER = "X-OmniCut-Channel"
CHANNEL_QUERY_PARAM = "channel"
SOURCE_HEADER = "header"
SOURCE_QUERY = "query"
SOURCE_DEFAULT = "default"
STATE_SCOPE_KEY = "channel_scope"
STATE_POLICY_KEY = "channel_route_policy"
_HEADER_BYTES = CHANNEL_HEADER.lower().encode("latin-1")
_HEADER_STRIP = " \t"

StoreFactory = Callable[[], ChannelStore]


class ChannelScope:
    """Resolved channel for one request.

    ``channel`` is a deep-copied registry snapshot.  For the implicit default
    scope it is loaded lazily on first access, so compatibility-mode requests
    that never ask for it cost nothing and cannot fail on a bad registry.
    """

    __slots__ = ("channel_id", "source", "strict", "_channel", "_store_factory")

    def __init__(
        self,
        channel_id: str,
        source: str,
        strict: bool,
        channel: Optional[dict[str, Any]] = None,
        store_factory: Optional[StoreFactory] = None,
    ) -> None:
        self.channel_id = channel_id
        self.source = source
        self.strict = strict
        self._channel = channel
        self._store_factory = store_factory or get_default_store

    def __repr__(self) -> str:
        return f"ChannelScope(channel_id={self.channel_id!r}, source={self.source!r}, strict={self.strict!r})"

    @property
    def is_implicit_default(self) -> bool:
        return self.source == SOURCE_DEFAULT

    @property
    def channel(self) -> dict[str, Any]:
        if self._channel is None:
            channel = self._store_factory().find(self.channel_id)
            if channel is None:
                raise ChannelError(422, "channel_scope_unknown", f"ไม่รู้จักช่อง {self.channel_id}")
            self._channel = channel
        return self._channel

    @property
    def status(self) -> str:
        return self.channel["status"]

    @property
    def revision(self) -> int:
        return int(self.channel.get("revision", 0))

    @property
    def identity_hash(self) -> str:
        return self.channel.get("identity_hash") or ""

    def to_dict(self) -> dict[str, Any]:
        return {"channel_id": self.channel_id, "source": self.source, "strict": self.strict}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def _scope_error(code: str, message: str, status_code: int = 422) -> ChannelError:
    return ChannelError(status_code, code, message)


def resolve_scope(
    *,
    header_values: Sequence[str] = (),
    query_values: Sequence[str] = (),
    policy: Optional[RoutePolicy] = None,
    strict: Optional[bool] = None,
    store_factory: Optional[StoreFactory] = None,
) -> Optional[ChannelScope]:
    """Resolve the request scope for one route.

    Returns ``None`` for shared/global routes without a scope (and for rows
    with ``ignore_scope_header``).  Raises :class:`ChannelError` (422) for
    missing/invalid/unknown/conflicting scope.
    """
    row = policy or UNLISTED_ROUTE_POLICY
    strict_mode = config.is_multi_channel_strict() if strict is None else bool(strict)
    factory = store_factory or get_default_store
    if row.ignore_scope_header:
        return None

    headers = [v.strip(_HEADER_STRIP) for v in header_values]
    queries = [v.strip(_HEADER_STRIP) for v in query_values] if row.allow_query_scope else []
    if len(set(headers)) > 1:
        raise _scope_error("channel_scope_conflict", f"ส่ง header {CHANNEL_HEADER} มาหลายค่าไม่ตรงกัน")
    if len(set(queries)) > 1:
        raise _scope_error("channel_scope_conflict", "ส่ง ?channel= มาหลายค่าไม่ตรงกัน")
    if headers and queries and headers[0] != queries[0]:
        raise _scope_error("channel_scope_conflict", f"ช่องใน header ({headers[0]}) ไม่ตรงกับ ?channel= ({queries[0]})")
    if query_values and not row.allow_query_scope and row.scope == SCOPE_CHANNEL:
        raise _scope_error(
            "channel_query_not_allowed",
            f"คำสั่งนี้ไม่รับช่องทาง ?channel= กรุณาส่ง header {CHANNEL_HEADER}",
        )

    if headers:
        explicit, source = headers[0], SOURCE_HEADER
    elif queries:
        explicit, source = queries[0], SOURCE_QUERY
    else:
        explicit, source = None, SOURCE_DEFAULT

    if explicit is not None:
        if not is_valid_channel_id(explicit):
            raise _scope_error("channel_scope_invalid", "รหัสช่องไม่ถูกต้อง กรุณาเลือกช่องใหม่")
        channel = factory().find(explicit)
        if channel is None:
            raise _scope_error("channel_scope_unknown", f"ไม่รู้จักช่อง {explicit} กรุณาเลือกช่องใหม่")
        return ChannelScope(explicit, source, strict_mode, channel=channel, store_factory=factory)

    if row.scope != SCOPE_CHANNEL:
        return None
    if strict_mode:
        raise _scope_error(
            "channel_scope_missing",
            "ต้องระบุช่องก่อนทำรายการนี้ (โหมดหลายช่องเปิดอยู่) กรุณาอัปเดตแอปหรือเลือกช่อง",
        )
    return ChannelScope(config.DEFAULT_CHANNEL_ID, SOURCE_DEFAULT, False, store_factory=factory)


def _query_channel_values(query_string: bytes) -> list[str]:
    if not query_string or b"channel" not in query_string:
        return []
    try:
        decoded = query_string.decode("latin-1")
    except Exception:  # pragma: no cover - latin-1 decodes every byte
        return []
    return [value for key, value in parse_qsl(decoded, keep_blank_values=True) if key == CHANNEL_QUERY_PARAM]


def _header_channel_values(raw_headers: Iterable[tuple[bytes, bytes]]) -> list[str]:
    return [value.decode("latin-1") for key, value in raw_headers if key.lower() == _HEADER_BYTES]


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------


def _error_response(exc: ChannelError) -> JSONResponse:
    return JSONResponse(exc.to_body(), status_code=exc.status_code, headers={ERROR_CODE_HEADER: exc.code})


class ChannelScopeMiddleware:
    """Resolve ``request.state.channel_scope`` for every HTTP request.

    * Non-HTTP (websocket/lifespan) and ``OPTIONS`` pass through untouched.
    * Unmatched paths (404/405) pass through; only ``APIRoute`` matches are
      policy-checked (Starlette docs routes are global).
    * Never reads the request body; does not wrap the response except to add
      ``X-OmniCut-Channel`` when the client sent an explicit scope.
    """

    _CACHE_LIMIT = 4096

    def __init__(
        self,
        app: Any,
        *,
        router_app: Any = None,
        policy: Optional[RoutePolicyTable] = None,
        store_factory: Optional[StoreFactory] = None,
        strict: Optional[bool] = None,
    ) -> None:
        self.app = app
        self.router_app = router_app
        self.policy = policy if policy is not None else default_route_policy()
        self.store_factory = store_factory
        self.strict = strict
        self._match_cache: dict[tuple[str, str], tuple[bool, Optional[RoutePolicy]]] = {}
        self._cache_routes_len = -1

    def _routes(self, scope: dict) -> list:
        app = self.router_app or scope.get("app")
        router = getattr(app, "router", None)
        return list(getattr(router, "routes", None) or [])

    def lookup(self, scope: dict) -> tuple[bool, Optional[RoutePolicy]]:
        """``(matched_api_route, policy_row)`` for this request (cached per method+path)."""
        routes = self._routes(scope)
        if len(routes) != self._cache_routes_len:
            self._match_cache.clear()
            self._cache_routes_len = len(routes)
        method = scope.get("method", "GET")
        key = (method, scope.get("path", ""))
        cached = self._match_cache.get(key)
        if cached is not None:
            return cached
        result: tuple[bool, Optional[RoutePolicy]] = (False, None)
        for route in routes:
            try:
                match, _child = route.matches(scope)
            except Exception:
                continue
            if match == Match.FULL:
                if isinstance(route, APIRoute):
                    row = self.policy.get(method, route.path)
                    if row is None:
                        for route_method in sorted(route.methods or ()):
                            row = self.policy.get(route_method, route.path)
                            if row is not None:
                                break
                    result = (True, row or UNLISTED_ROUTE_POLICY)
                break
        if len(self._match_cache) >= self._CACHE_LIMIT:
            self._match_cache.clear()
        self._match_cache[key] = result
        return result

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http" or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return
        matched, row = self.lookup(scope)
        if not matched:
            await self.app(scope, receive, send)
            return
        try:
            channel_scope = resolve_scope(
                header_values=_header_channel_values(scope.get("headers") or []),
                query_values=_query_channel_values(scope.get("query_string") or b""),
                policy=row,
                strict=self.strict,
                store_factory=self.store_factory,
            )
        except ChannelError as exc:
            await _error_response(exc)(scope, receive, send)
            return
        state = scope.setdefault("state", {})
        state[STATE_SCOPE_KEY] = channel_scope
        state[STATE_POLICY_KEY] = row
        if channel_scope is None or channel_scope.is_implicit_default:
            await self.app(scope, receive, send)
            return
        echo = (_HEADER_BYTES, channel_scope.channel_id.encode("latin-1"))

        async def send_with_scope(message: dict) -> None:
            if message.get("type") == "http.response.start":
                headers = [h for h in (message.get("headers") or []) if h[0].lower() != _HEADER_BYTES]
                headers.append(echo)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_scope)


async def channel_error_handler(_request: Request, exc: ChannelError) -> JSONResponse:
    """App exception handler: ``{"detail": <Thai>, "code": ..., **extra}``."""
    return _error_response(exc)


def install_channel_scope(
    app: Any,
    *,
    policy: Optional[RoutePolicyTable] = None,
    store_factory: Optional[StoreFactory] = None,
    strict: Optional[bool] = None,
) -> None:
    """Register the middleware + ChannelError handler on a FastAPI app.

    Call BEFORE other ``add_middleware``/``app.middleware`` registrations so
    the scope middleware is the innermost layer (auth and CORS wrap it).
    """
    app.add_middleware(
        ChannelScopeMiddleware,
        router_app=app,
        policy=policy,
        store_factory=store_factory,
        strict=strict,
    )
    app.add_exception_handler(ChannelError, channel_error_handler)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def _resolve_from_request(request: Request, *, require: bool) -> Optional[ChannelScope]:
    state = request.scope.get("state") or {}
    if STATE_SCOPE_KEY in state:
        current = state[STATE_SCOPE_KEY]
        if current is not None or not require:
            return current
    row: RoutePolicy = state.get(STATE_POLICY_KEY) or UNLISTED_ROUTE_POLICY
    if require:
        row = dataclasses.replace(row, scope=SCOPE_CHANNEL, ignore_scope_header=False)
    resolved = resolve_scope(
        header_values=request.headers.getlist(CHANNEL_HEADER),
        query_values=request.query_params.getlist(CHANNEL_QUERY_PARAM),
        policy=row,
    )
    request.scope.setdefault("state", {})[STATE_SCOPE_KEY] = resolved
    return resolved


def get_channel_scope(request: Request) -> ChannelScope:
    """Dependency for channel-owned handlers. Always returns a scope or raises 422."""
    scope = _resolve_from_request(request, require=True)
    assert scope is not None  # resolve_scope never returns None for channel rows
    return scope


def get_optional_channel_scope(request: Request) -> Optional[ChannelScope]:
    """Dependency for shared/global handlers: the scope if the client sent one."""
    return _resolve_from_request(request, require=False)


# ---------------------------------------------------------------------------
# Enforcement helpers (raise ChannelError; used from P2 on)
# ---------------------------------------------------------------------------


def _status_label(status: str) -> str:
    return STATUS_LABEL_TH.get(status, status)


def require_writable(scope: ChannelScope) -> ChannelScope:
    """Archived channels are read-only (409)."""
    if scope.status == STATUS_ARCHIVED:
        raise ChannelError(
            409,
            "channel_archived",
            f"ช่อง {scope.channel_id} อยู่ในสถานะ{_status_label(STATUS_ARCHIVED)} แก้ไขข้อมูลไม่ได้",
            channel_status=scope.status,
        )
    return scope


def require_active_for_new_work(scope: ChannelScope) -> ChannelScope:
    """New jobs/claims need an ``active`` channel (draft/archived -> 409)."""
    if scope.status != STATUS_ACTIVE:
        raise ChannelError(
            409,
            "channel_not_active",
            f"ช่อง {scope.channel_id} อยู่ในสถานะ{_status_label(scope.status)} ยังเริ่มงานใหม่ไม่ได้",
            channel_status=scope.status,
        )
    return scope


def require_final_ready(scope: ChannelScope, *, store: Optional[ChannelStore] = None) -> ChannelScope:
    """Final render/export/post gate (AC15): active + no readiness issues (409)."""
    require_active_for_new_work(scope)
    target = store or scope._store_factory()
    doc = target.load()
    channel = next((c for c in doc["channels"] if c["id"] == scope.channel_id), None)
    if channel is None:
        raise ChannelError(422, "channel_scope_unknown", f"ไม่รู้จักช่อง {scope.channel_id}")
    issues = channel_readiness(channel, channels=doc["channels"], project_root=target.project_root, metrics=target.metrics)
    if issues:
        raise ChannelError(
            409,
            "channel_not_ready",
            f"ช่อง {scope.channel_id} ยังไม่พร้อมทำคลิปจริง: {issues[0].message}",
            issues=[issue.to_dict() for issue in issues],
        )
    return scope


def ensure_same_channel(
    scope: ChannelScope,
    owner_channel_id: Optional[str],
    *,
    resource_label: str = "ข้อมูล",
    allow_legacy_main: bool = False,
) -> None:
    """Ownership check for a resource: another channel's resource looks like 404.

    ``owner_channel_id`` None = legacy record without ownership; accepted only
    when ``allow_legacy_main`` and the scope is the default channel (P2 sets
    this only for the verified main migration cohort).
    """
    if owner_channel_id is None and allow_legacy_main and scope.channel_id == config.DEFAULT_CHANNEL_ID:
        return
    if owner_channel_id != scope.channel_id:
        raise ChannelError(404, "resource_not_found", f"ไม่พบ{resource_label}ที่ร้องขอ")
