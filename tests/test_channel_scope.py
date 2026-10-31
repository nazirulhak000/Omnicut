"""Channel scope middleware/dependency/route-policy contracts (multi-channel P1).

Covers plan §5.1 + ADR: header scope, query scope only on flagged routes,
422 for unknown/invalid/missing(strict) scope, 409 status gates, 404 for
another channel's resource, OPTIONS/streaming/background passthrough, the
"no live route without a policy row" safety net, /api/channels end-to-end,
and default-mode compatibility of representative existing routes.

Offline + tmp_path only.  Real routes are either rejected by the middleware
before their handler runs, or have their store layer stubbed / redirected to
tmp_path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi import BackgroundTasks, Body, Depends, FastAPI
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from scripts import channel_store as cs
from scripts import config
from scripts.channel_route_policy import (
    POLICY_FILE,
    RoutePolicy,
    RoutePolicyTable,
    default_route_policy,
    load_route_policy,
)
from scripts.channel_scope import (
    CHANNEL_HEADER,
    ChannelScope,
    ChannelScopeMiddleware,
    ensure_same_channel,
    get_channel_scope,
    get_optional_channel_scope,
    install_channel_scope,
    require_active_for_new_work,
    require_final_ready,
    require_writable,
    resolve_scope,
)

STRICT_ENV = config.MULTI_CHANNEL_STRICT_ENV
P0_MATRIX = Path(__file__).resolve().parent.parent / "_Docs" / "Reports" / "MULTI_CHANNEL_P0_ROUTE_MATRIX_20261010.json"
QUERY_SCOPE_ROUTES = {
    ("GET", "/api/hyperframes/render-jobs/{job_id}/artifact/{kind}"),
    ("GET", "/api/media/{file_path:path}"),
    ("GET", "/api/editor/filmstrip"),
    ("GET", "/api/producer/ref-media/{filename}"),
    ("GET", "/api/background-isolation/videos/{artifact_id}/cutout.webm"),
    ("GET", "/api/background-isolation/videos/{artifact_id}/preview.webm"),
    ("GET", "/api/background-isolation/sequences/{artifact_id}/frames/{frame_index}"),
}


class FakeMetrics:
    def width_px(self, text, font_file, size):
        return float(len(text) * 10)

    def unsupported_chars(self, text, font_file):
        return cs._fallback_unsupported(text)


def _write(root: Path, rel: str, data: bytes = b"img") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    """Isolated registry: main (active), second (active), draft1 (draft), old (archived)."""
    root = tmp_path / "project"
    _write(root, cs.MAIN_SEED["avatar_asset_path"])
    _write(root, "assets/second.jpg")
    _write(root, "assets/old.jpg")
    monkeypatch.setattr(config, "CHANNELS_FILE", root / "_Docs" / "channels.json")
    monkeypatch.setattr(config, "CHANNELS_PROJECT_ROOT", root)
    monkeypatch.setattr(cs, "_DEFAULT_METRICS", FakeMetrics())
    monkeypatch.delenv(STRICT_ENV, raising=False)
    store = cs.get_default_store()
    store.seed()
    profile = {
        "display_name": "ช่องรอง",
        "watermark_text": "สงวนลิขสิทธิ์ช่องรอง",
        "follow_title": "กดติดตาม",
    }
    store.create({"id": "second", "handle": "@second_shop", "avatar_asset_path": "assets/second.jpg", **profile})
    store.activate("second")
    store.create({"id": "draft1", "display_name": "ร่าง"})
    store.create({"id": "old", "handle": "@old_shop", "avatar_asset_path": "assets/old.jpg", **profile})
    store.activate("old")
    store.archive("old")
    return store


# --------------------------------------------------------------------------- mini app

MINI_POLICY = RoutePolicyTable(
    [
        RoutePolicy("GET", "/api/items", "channel"),
        RoutePolicy("POST", "/api/items/{item_id}", "channel", access="write"),
        RoutePolicy("GET", "/api/media/{file_path:path}", "channel", allow_query_scope=True),
        RoutePolicy("GET", "/api/shared", "shared"),
        RoutePolicy("GET", "/api/global", "global"),
        RoutePolicy("GET", "/api/registry", "global", ignore_scope_header=True),
        RoutePolicy("GET", "/api/stream", "channel"),
        RoutePolicy("POST", "/api/bg", "channel", access="write"),
        RoutePolicy("POST", "/api/write", "channel", access="write"),
        RoutePolicy("POST", "/api/newjob", "channel", access="write"),
        RoutePolicy("POST", "/api/final", "channel", access="write"),
        RoutePolicy("GET", "/api/owned/{owner}", "channel"),
        RoutePolicy("GET", "/api/lazy", "channel"),
    ]
)


def build_mini_app(store_factory=None, policy=MINI_POLICY):
    app = FastAPI()
    calls: list[str] = []

    @app.get("/api/items")
    def items(scope: ChannelScope = Depends(get_channel_scope)):
        calls.append("items")
        return {**scope.to_dict(), "status": scope.status}

    @app.post("/api/items/{item_id}")
    def update_item(item_id: str, payload: dict = Body(...), scope: ChannelScope = Depends(get_channel_scope)):
        return {"scope": scope.channel_id, "body_channel_id": payload.get("channel_id")}

    @app.get("/api/media/{file_path:path}")
    def media(file_path: str, scope: ChannelScope = Depends(get_channel_scope)):
        return {"scope": scope.channel_id, "source": scope.source, "path": file_path}

    @app.get("/api/shared")
    def shared(scope=Depends(get_optional_channel_scope)):
        return {"scope": scope.channel_id if scope else None}

    @app.get("/api/global")
    def global_route(scope=Depends(get_optional_channel_scope)):
        return {"scope": scope.channel_id if scope else None}

    @app.get("/api/registry")
    def registry_route():
        return {"ok": True}

    @app.get("/api/stream")
    def stream(scope: ChannelScope = Depends(get_channel_scope)):
        def chunks():
            for i in range(3):
                yield f"{scope.channel_id}:{i};".encode()

        return StreamingResponse(chunks(), media_type="text/plain")

    @app.post("/api/bg")
    def bg(background: BackgroundTasks, scope: ChannelScope = Depends(get_channel_scope)):
        background.add_task(calls.append, f"bg:{scope.channel_id}")
        return {"queued": True}

    @app.post("/api/write")
    def write(scope: ChannelScope = Depends(get_channel_scope)):
        require_writable(scope)
        return {"ok": scope.channel_id}

    @app.post("/api/newjob")
    def newjob(scope: ChannelScope = Depends(get_channel_scope)):
        require_active_for_new_work(scope)
        return {"ok": scope.channel_id}

    @app.post("/api/final")
    def final(scope: ChannelScope = Depends(get_channel_scope)):
        require_final_ready(scope)
        return {"ok": scope.channel_id}

    @app.get("/api/owned/{owner}")
    def owned(owner: str, scope: ChannelScope = Depends(get_channel_scope)):
        ensure_same_channel(scope, None if owner == "legacy" else owner, resource_label="สินค้า", allow_legacy_main=True)
        return {"ok": owner}

    @app.get("/api/lazy")
    def lazy(scope: ChannelScope = Depends(get_channel_scope)):
        return {"scope": scope.channel_id, "source": scope.source}

    @app.get("/api/unlisted")
    def unlisted(scope=Depends(get_optional_channel_scope)):
        return {"scope": scope.channel_id if scope else None}

    install_channel_scope(app, policy=policy, store_factory=store_factory)
    return app, calls


@pytest.fixture()
def mini(registry):
    app, calls = build_mini_app()
    return TestClient(app), calls


def H(value):
    return {CHANNEL_HEADER: value}


# --------------------------------------------------------------------------- strict on/off matrix


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize(
    "headers, url, status, expect",
    [
        ({}, "/api/items", None, "main"),
        (H("main"), "/api/items", 200, "main"),
        (H("second"), "/api/items", 200, "second"),
        (H("draft1"), "/api/items", 200, "draft1"),
        (H("old"), "/api/items", 200, "old"),  # archived: reads allowed
        (H("unknown"), "/api/items", 422, "channel_scope_unknown"),
        (H("Main"), "/api/items", 422, "channel_scope_invalid"),
        (H(""), "/api/items", 422, "channel_scope_invalid"),
        (H("../main"), "/api/items", 422, "channel_scope_invalid"),
        (H(" second "), "/api/items", 200, "second"),
        ([(CHANNEL_HEADER, "main"), (CHANNEL_HEADER, "second")], "/api/items", 422, "channel_scope_conflict"),
        ([(CHANNEL_HEADER, "main"), (CHANNEL_HEADER, "main")], "/api/items", 200, "main"),
        ({}, "/api/items?channel=second", 422, "channel_query_not_allowed"),
        (H("second"), "/api/items?channel=second", 422, "channel_query_not_allowed"),
        ({}, "/api/media/a/b.mp4?channel=second", 200, "second"),
        ({}, "/api/media/a/b.mp4?channel=nope", 422, "channel_scope_unknown"),
        (H("second"), "/api/media/a/b.mp4?channel=second", 200, "second"),
        (H("main"), "/api/media/a/b.mp4?channel=second", 422, "channel_scope_conflict"),
        ({}, "/api/media/a/b.mp4?channel=main&channel=second", 422, "channel_scope_conflict"),
        ({}, "/api/media/a/b.mp4", None, "main"),
    ],
)
def test_scope_resolution_matrix(registry, monkeypatch, strict, headers, url, status, expect):
    if strict:
        monkeypatch.setenv(STRICT_ENV, "1")
    app, _ = build_mini_app()
    client = TestClient(app)
    response = client.get(url, headers=headers)
    if status is None:  # implicit default scope
        if strict:
            assert response.status_code == 422
            assert response.json()["code"] == "channel_scope_missing"
            return
        assert response.status_code == 200
        body = response.json()
        assert body.get("channel_id", body.get("scope")) == "main"
        assert CHANNEL_HEADER.lower() not in {k.lower() for k in response.headers}
        return
    assert response.status_code == status, response.text
    if status == 200:
        body = response.json()
        assert body.get("channel_id", body.get("scope")) == expect
        assert response.headers[CHANNEL_HEADER] == expect  # explicit scope is echoed
    else:
        body = response.json()
        assert body["code"] == expect
        assert isinstance(body["detail"], str) and re.search("[฀-๿]", body["detail"])
        assert response.headers["X-OmniCut-Error-Code"] == expect


def test_strict_flag_is_read_at_call_time(registry, monkeypatch):
    client = TestClient(build_mini_app()[0])
    assert client.get("/api/items").status_code == 200
    for value in ("1", "true", "YES", " on "):
        monkeypatch.setenv(STRICT_ENV, value)
        assert client.get("/api/items").status_code == 422
    for value in ("", "0", "false", "off", "no"):
        monkeypatch.setenv(STRICT_ENV, value)
        assert client.get("/api/items").status_code == 200
    assert config.is_multi_channel_strict() is False


def test_shared_and_global_routes(registry, monkeypatch):
    monkeypatch.setenv(STRICT_ENV, "1")
    client = TestClient(build_mini_app()[0])
    assert client.get("/api/shared").json() == {"scope": None}
    assert client.get("/api/global").json() == {"scope": None}
    assert client.get("/api/shared", headers=H("second")).json() == {"scope": "second"}
    assert client.get("/api/shared", headers=H("nope")).status_code == 422  # header still validated
    assert client.get("/api/global", headers=H("nope")).status_code == 422
    assert client.get("/api/registry", headers=H("nope")).status_code == 200  # ignore_scope_header
    assert client.get("/api/shared?channel=second").json() == {"scope": None}  # query ignored on unflagged shared


def test_unlisted_route_fails_closed(registry, monkeypatch):
    client = TestClient(build_mini_app()[0])
    assert client.get("/api/unlisted").json() == {"scope": "main"}  # treated as channel route
    monkeypatch.setenv(STRICT_ENV, "1")
    response = client.get("/api/unlisted")
    assert response.status_code == 422 and response.json()["code"] == "channel_scope_missing"


def test_body_channel_id_never_overrides_header(mini):
    client, _ = mini
    response = client.post("/api/items/1", headers=H("second"), json={"channel_id": "main"})
    assert response.json() == {"scope": "second", "body_channel_id": "main"}
    response = client.post("/api/items/1", json={"channel_id": "second"})
    assert response.json() == {"scope": "main", "body_channel_id": "second"}


def test_options_preflight_passes_through(registry, monkeypatch):
    monkeypatch.setenv(STRICT_ENV, "1")
    client = TestClient(build_mini_app()[0])
    response = client.options("/api/items", headers=H("nope"))
    assert response.status_code == 405  # reached the router: middleware did not reject OPTIONS


def test_unknown_paths_and_methods_pass_through(registry, monkeypatch):
    monkeypatch.setenv(STRICT_ENV, "1")
    client = TestClient(build_mini_app()[0])
    assert client.get("/api/does-not-exist", headers=H("nope")).status_code == 404
    assert client.delete("/api/items", headers=H("nope")).status_code == 405


def test_streaming_and_background_tasks_unaffected(mini):
    client, calls = mini
    response = client.get("/api/stream", headers=H("second"))
    assert response.status_code == 200
    assert response.text == "second:0;second:1;second:2;"
    assert response.headers[CHANNEL_HEADER] == "second"
    assert client.post("/api/bg", headers=H("second")).json() == {"queued": True}
    assert "bg:second" in calls


def test_default_scope_is_lazy_and_never_reads_registry(registry, monkeypatch):
    def exploding_factory():
        raise AssertionError("registry must not be read for implicit default scope")

    app, _ = build_mini_app(store_factory=exploding_factory)
    client = TestClient(app)
    assert client.get("/api/lazy").json() == {"scope": "main", "source": "default"}


def test_corrupt_registry_only_affects_explicit_scope(registry):
    config.CHANNELS_FILE.write_text("{broken", encoding="utf-8")
    client = TestClient(build_mini_app()[0])
    assert client.get("/api/lazy").status_code == 200  # compatibility mode unaffected
    response = client.get("/api/lazy", headers=H("main"))
    assert response.status_code == 500 and response.json()["code"] == "channel_registry_invalid"


def test_middleware_does_not_read_request_body(registry):
    app, _ = build_mini_app()
    seen = []

    async def inner(scope, receive, send):
        seen.append(scope["state"]["channel_scope"].channel_id)
        message = await receive()
        seen.append(message["body"])
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = ChannelScopeMiddleware(inner, router_app=app, policy=MINI_POLICY)
    body = b'{"channel_id": "main"}'
    sent = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    import asyncio

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/items/1",
        "raw_path": b"/api/items/1",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"x-omnicut-channel", b"second")],
    }
    asyncio.run(middleware(scope, receive, send))
    assert seen == ["second", body]  # handler still receives the untouched body
    assert sent[0]["status"] == 204
    assert (b"x-omnicut-channel", b"second") in sent[0]["headers"]


def test_websocket_and_lifespan_scopes_pass_through(registry):
    import asyncio

    reached = []

    async def inner(scope, receive, send):
        reached.append(scope["type"])

    middleware = ChannelScopeMiddleware(inner, router_app=FastAPI(), policy=MINI_POLICY, strict=True)
    for kind in ("websocket", "lifespan"):
        asyncio.run(middleware({"type": kind, "path": "/api/items", "headers": []}, None, None))
    assert reached == ["websocket", "lifespan"]


# --------------------------------------------------------------------------- status helpers (AC15)


def test_status_helpers(mini):
    client, _ = mini
    assert client.post("/api/write", headers=H("draft1")).status_code == 200
    archived = client.post("/api/write", headers=H("old"))
    assert archived.status_code == 409 and archived.json()["code"] == "channel_archived"
    assert "archived" in archived.json()["detail"]
    for channel_id, label in (("draft1", "draft"), ("old", "archived")):
        response = client.post("/api/newjob", headers=H(channel_id))
        assert response.status_code == 409 and response.json()["code"] == "channel_not_active"
        assert label in response.json()["detail"]
        assert response.json()["channel_status"] == label
    assert client.post("/api/newjob", headers=H("second")).status_code == 200
    assert client.post("/api/newjob").status_code == 200  # implicit main is active


def test_final_ready_gate_ac15(mini, registry):
    client, _ = mini
    assert client.post("/api/final", headers=H("second")).json() == {"ok": "second"}
    assert client.post("/api/final", headers=H("draft1")).json()["code"] == "channel_not_active"
    assert client.post("/api/final", headers=H("old")).json()["code"] == "channel_not_active"
    # missing avatar file blocks final render
    (config.CHANNELS_PROJECT_ROOT / "assets" / "second.jpg").unlink()
    response = client.post("/api/final", headers=H("second"))
    assert response.status_code == 409 and response.json()["code"] == "channel_not_ready"
    assert [i["code"] for i in response.json()["issues"]] == ["avatar_file_missing"]
    # duplicate handle / over-long text from a hand-edited registry also block
    doc = json.loads(config.CHANNELS_FILE.read_text(encoding="utf-8"))
    for channel in doc["channels"]:
        if channel["id"] == "draft1":
            channel.update(status="active", handle="@rizanntry", display_name="x" * 60)
    config.CHANNELS_FILE.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    codes = [i["code"] for i in client.post("/api/final", headers=H("draft1")).json()["issues"]]
    assert "handle_duplicate" in codes and "text_too_long" in codes
    main_codes = [i["code"] for i in client.post("/api/final").json()["issues"]]
    assert main_codes == ["handle_duplicate"]


def test_other_channel_resource_looks_like_404(mini):
    client, _ = mini
    assert client.get("/api/owned/second", headers=H("second")).status_code == 200
    response = client.get("/api/owned/main", headers=H("second"))
    assert response.status_code == 404 and response.json()["code"] == "resource_not_found"
    assert "สินค้า" in response.json()["detail"]
    assert client.get("/api/owned/legacy").status_code == 200  # legacy cohort only for main
    assert client.get("/api/owned/legacy", headers=H("second")).status_code == 404


def test_resolve_scope_pure_function(registry):
    channel_row = RoutePolicy("GET", "/x", "channel")
    scope = resolve_scope(header_values=["second"], policy=channel_row, strict=True)
    assert scope.channel_id == "second" and scope.source == "header" and scope.revision >= 1
    assert scope.identity_hash == registry.get("second")["identity_hash"]
    assert resolve_scope(policy=RoutePolicy("GET", "/x", "shared"), strict=True) is None
    default = resolve_scope(policy=channel_row, strict=False)
    assert default.channel_id == "main" and default.is_implicit_default and default.status == "active"
    with pytest.raises(cs.ChannelError) as info:
        resolve_scope(policy=channel_row, strict=True)
    assert info.value.status_code == 422


# --------------------------------------------------------------------------- route policy safety net


def _live_api_routes():
    from scripts.api_server import app

    return app, [r for r in app.routes if isinstance(r, APIRoute)]


def test_every_live_route_has_exactly_one_policy_row():
    _app, routes = _live_api_routes()
    live = {(method, route.path) for route in routes for method in route.methods}
    policy = load_route_policy(POLICY_FILE).keys()
    missing = sorted(live - policy)
    stale = sorted(policy - live)
    assert not missing, f"routes without a channel scope policy row (add to scripts/channel_route_policy.json): {missing}"
    assert not stale, f"stale policy rows without a live route: {stale}"
    assert all(len(route.methods) == 1 for route in routes)


def test_policy_file_shape_and_decisions():
    table = default_route_policy()
    rows = list(table)
    by_scope = {}
    for row in rows:
        by_scope[row.scope] = by_scope.get(row.scope, 0) + 1
    # global +17: /api/auth/{me,login,logout}, /api/health, plus previously unregistered agy/terminal/token/SPA catch-all rows
    # channel +1: GET /api/tiktok-stats/style-performance
    # global +9: /api/ssd/{drives,inspect,stage,reconcile} + /api/archive/{status,progress,execute,restore,reveal}
    # -- device/Drive maintenance over the whole export registry, no channel input
    assert by_scope == {"channel": 247, "shared": 38, "global": 68}
    release = table.get("POST", "/api/tiktok-autopost/release")
    assert release.scope == "channel" and release.access == "write" and not release.allow_query_scope
    assert {row.key for row in rows if row.allow_query_scope} == QUERY_SCOPE_ROUTES
    channels_rows = [row for row in rows if row.path.startswith("/api/channels")]
    assert len(channels_rows) == 7
    assert all(row.scope == "global" and row.ignore_scope_header for row in channels_rows)
    assert [row.key for row in rows if row.ignore_scope_header] == [row.key for row in channels_rows]


def test_policy_matches_p0_classification():
    if not P0_MATRIX.is_file():
        pytest.skip("P0 route matrix report not present")
    p0 = json.loads(P0_MATRIX.read_text(encoding="utf-8"))
    table = default_route_policy()
    assert len(p0) == 228
    for row in p0:
        policy = table.get(row["method"], row["path"])
        assert policy is not None, row["path"]
        assert policy.scope == row["scope"], (row["method"], row["path"])


@pytest.mark.parametrize(
    "bad_row, fragment",
    [
        ({"method": "GET", "path": "/x", "scope": "tenant"}, "scope"),
        ({"method": "TRACE", "path": "/x", "scope": "global"}, "method"),
        ({"method": "POST", "path": "/x", "scope": "channel", "allow_query_scope": True}, "GET"),
        ({"method": "GET", "path": "/x", "scope": "channel", "ignore_scope_header": True}, "global"),
        ({"method": "GET", "path": "x", "scope": "global"}, "path"),
    ],
)
def test_policy_loader_rejects_bad_rows(tmp_path, bad_row, fragment):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"schema_version": 1, "routes": [bad_row]}), encoding="utf-8")
    with pytest.raises(ValueError, match=fragment):
        load_route_policy(path)


def test_policy_loader_rejects_duplicates(tmp_path):
    path = tmp_path / "policy.json"
    row = {"method": "GET", "path": "/x", "scope": "global"}
    path.write_text(json.dumps({"schema_version": 1, "routes": [row, row]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_route_policy(path)


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


def test_router_lookup_resolves_each_route_to_its_own_row():
    app, routes = _live_api_routes()
    middleware = ChannelScopeMiddleware(lambda *a: None, router_app=app)
    probes = {
        ("GET", "/api/tasks/active"): "/api/tasks/active",
        ("GET", "/api/schedule-queue/template"): "/api/schedule-queue/template",
    }
    for route in routes:
        method = next(iter(route.methods))
        url = probes.get((method, route.path), _concrete(route.path))
        scope = {"type": "http", "method": method, "path": url, "root_path": "", "query_string": b"", "headers": []}
        matched, row = middleware.lookup(scope)
        assert matched, (method, url)
        if "{" not in route.path or (method, route.path) in probes:
            assert row.key == (method, route.path), (method, url, row.key)


def test_every_channel_route_rejects_missing_scope_in_strict_mode(monkeypatch, registry):
    """No real handler runs: the middleware answers 422 before routing to it."""
    monkeypatch.setenv(STRICT_ENV, "1")
    app, routes = _live_api_routes()
    client = TestClient(app)
    middleware = ChannelScopeMiddleware(lambda *a: None, router_app=app)
    checked = 0
    for route in routes:
        method = next(iter(route.methods))
        row = default_route_policy().get(method, route.path)
        if row.scope != "channel":
            continue
        url = _concrete(route.path)
        matched, matched_row = middleware.lookup(
            {"type": "http", "method": method, "path": url, "root_path": "", "query_string": b"", "headers": []}
        )
        if matched_row.scope != "channel":  # e.g. /api/tasks/x shadowed by a literal path
            continue
        response = client.request(method, url)
        assert response.status_code == 422, (method, url, response.status_code)
        assert response.json()["code"] == "channel_scope_missing"
        response = client.request(method, url, headers=H("nope"))
        assert response.status_code == 422 and response.json()["code"] == "channel_scope_unknown"
        checked += 1
    assert checked == sum(1 for row in default_route_policy() if row.scope == "channel")


# --------------------------------------------------------------------------- real app wiring


def test_middleware_order_on_real_app():
    from scripts.api_server import app

    names = [m.cls.__name__ for m in app.user_middleware]
    # MaintenanceGateMiddleware (P2.3) is the innermost layer: 503 for writes during migration.
    assert names == ["CORSMiddleware", "AuthGateMiddleware", "ChannelScopeMiddleware", "MaintenanceGateMiddleware"]


def test_cors_preflight_allows_channel_header(monkeypatch, registry):
    from scripts.api_server import app

    monkeypatch.setenv(STRICT_ENV, "1")
    client = TestClient(app)
    response = client.options(
        "/api/products",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-omnicut-channel",
        },
    )
    assert response.status_code == 200
    assert "x-omnicut-channel" in response.headers["access-control-allow-headers"].lower()
    rejected = client.get("/api/products", headers={"Origin": "http://localhost:5173", CHANNEL_HEADER: "nope"})
    assert rejected.status_code == 422
    assert rejected.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert CHANNEL_HEADER.lower() in rejected.headers["access-control-expose-headers"].lower()


def test_api_key_gate_runs_before_scope(monkeypatch, registry):
    from scripts.api_server import app

    monkeypatch.setenv("OMNICUT_API_KEY", "secret-key")
    client = TestClient(app)
    assert client.get("/api/products", headers=H("nope")).status_code == 401
    response = client.get("/api/products", headers={**H("nope"), "X-API-Key": "secret-key"})
    assert response.status_code == 422


# --------------------------------------------------------------------------- default-mode compatibility on real routes


@pytest.fixture()
def stubbed_real_routes(monkeypatch, tmp_path, registry):
    """Stub/redirect the store layer of one representative route per router."""
    from scripts import api_covers, api_exports, api_phase1, api_videos, export_registry, media_service
    from scripts import product_store as product_store_module
    from scripts.post_log import PostLog
    from scripts.product_store import ProductStore
    from scripts.schedule_store import ScheduleQueueStore
    from scripts.task_manager import TaskManager

    calls: list[str] = []

    def record(name, value):
        def stub(*_args, **_kwargs):
            calls.append(name)
            return value

        return stub

    monkeypatch.setattr(ProductStore, "list", staticmethod(record("products", [])))
    monkeypatch.setattr(ProductStore, "summary", staticmethod(record("products_summary", {"total": 0})))
    monkeypatch.setattr(ProductStore, "get_all", staticmethod(record("products_all", [])))
    monkeypatch.setattr(PostLog, "list_posts", staticmethod(record("post_log", [])))
    monkeypatch.setattr(PostLog, "summary", staticmethod(record("post_log_summary", {"count": 0})))
    monkeypatch.setattr(ScheduleQueueStore, "_load", staticmethod(record("schedule", [])))
    monkeypatch.setattr(export_registry.ExportRegistry, "path_index", staticmethod(record("registry_index", {})))
    monkeypatch.setattr(TaskManager, "get_active_tasks", staticmethod(record("tasks", [])))
    # exports + covers read folders: redirect every root they touch to tmp_path
    ready = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    stickers = tmp_path / "02_Assets" / "Stickers_Memes"
    for folder in (ready, posted, covers, stickers):
        folder.mkdir(parents=True)
    for module, name, value in (
        (api_exports, "BASE_DIR", tmp_path),
        (api_exports, "EXPORTS_DIR", ready),
        (api_exports, "POSTED_DIR", posted),
        (api_exports, "COVERS_DIR", covers),
        (media_service, "BASE_DIR", tmp_path),
        (media_service, "COVERS_DIR", covers),
        (api_videos, "BASE_DIR", tmp_path),
        (product_store_module, "BASE_DIR", tmp_path),
        (product_store_module, "STORE_PATH", tmp_path / "_Docs" / "products.json"),
        (export_registry, "BASE_DIR", tmp_path),
        (export_registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json"),
        (api_covers, "STICKERS_DIR", stickers),
        (api_covers, "BASE_DIR", tmp_path),
    ):
        monkeypatch.setattr(module, name, value)
    assert api_phase1 is not None
    return calls


REPRESENTATIVE_ROUTES = [
    ("/api/products", "channel", "products"),
    ("/api/exports", "channel", None),
    ("/api/schedule-queue", "channel", "schedule"),
    ("/api/post-log", "channel", "post_log"),
    ("/api/tasks/active", "channel", "tasks"),
    ("/api/covers/badges", "shared", None),
]


def test_default_mode_compatibility_on_real_routes(stubbed_real_routes):
    from scripts.api_server import app

    client = TestClient(app)
    for url, scope_class, stub_name in REPRESENTATIVE_ROUTES:
        plain = client.get(url)
        assert plain.status_code == 200, (url, plain.text)
        assert CHANNEL_HEADER.lower() not in {k.lower() for k in plain.headers}
        scoped = client.get(url, headers=H("main"))
        assert scoped.status_code == 200
        assert scoped.json() == plain.json(), url  # explicit main == implicit main
        if scope_class == "channel":
            assert scoped.headers[CHANNEL_HEADER] == "main"
        if stub_name:
            assert stub_name in stubbed_real_routes


def test_strict_mode_on_real_routes(stubbed_real_routes, monkeypatch):
    from scripts.api_server import app

    monkeypatch.setenv(STRICT_ENV, "1")
    client = TestClient(app)
    for url, scope_class, stub_name in REPRESENTATIVE_ROUTES:
        stubbed_real_routes.clear()
        response = client.get(url)
        if scope_class == "channel":
            assert response.status_code == 422, url
            assert response.json()["code"] == "channel_scope_missing"
            assert stubbed_real_routes == []  # handler never ran
            assert client.get(url, headers=H("main")).status_code == 200
        else:
            assert response.status_code == 200, url


def test_real_app_registry_untouched_by_default_requests(stubbed_real_routes, registry):
    from scripts.api_server import app

    before = config.CHANNELS_FILE.read_bytes()
    client = TestClient(app)
    for url, _scope, _stub in REPRESENTATIVE_ROUTES:
        client.get(url)
        client.get(url, headers=H("second"))
    assert config.CHANNELS_FILE.read_bytes() == before


# --------------------------------------------------------------------------- /api/channels end-to-end


@pytest.fixture()
def empty_registry(tmp_path, monkeypatch):
    root = tmp_path / "project"
    _write(root, cs.MAIN_SEED["avatar_asset_path"])
    monkeypatch.setattr(config, "CHANNELS_FILE", root / "_Docs" / "channels.json")
    monkeypatch.setattr(config, "CHANNELS_PROJECT_ROOT", root)
    monkeypatch.setattr(cs, "_DEFAULT_METRICS", FakeMetrics())
    monkeypatch.delenv(STRICT_ENV, raising=False)
    return root


def test_channels_api_end_to_end(empty_registry, monkeypatch):
    from scripts.api_server import app

    client = TestClient(app)
    listing = client.get("/api/channels")
    assert listing.status_code == 200
    body = listing.json()
    assert body["strict_mode"] is False and body["registry_exists"] is False
    assert body["default_channel_id"] == "main" and body["revision"] == 0
    assert [c["id"] for c in body["channels"]] == ["main"]
    assert not config.CHANNELS_FILE.exists()  # GET has no side effects

    monkeypatch.setenv(STRICT_ENV, "1")
    assert client.get("/api/channels", headers=H("stale")).json()["strict_mode"] is True
    monkeypatch.delenv(STRICT_ENV)

    created = client.post("/api/channels", json={"id": "second", "display_name": "ช่องรอง", "handle": "tiktok.com/@Second_Shop"})
    assert created.status_code == 201, created.text
    channel = created.json()["channel"]
    assert channel["status"] == "draft" and channel["handle"] == "@second_shop"
    assert config.CHANNELS_FILE.is_file()

    assert client.get("/api/channels/second").json()["channel"]["id"] == "second"
    missing = client.get("/api/channels/nope")
    assert missing.status_code == 404 and missing.json()["code"] == "channel_not_found"

    no_rev = client.patch("/api/channels/second", json={"display_name": "ใหม่"})
    assert no_rev.status_code == 422 and no_rev.json()["code"] == "expected_revision_required"
    patched = client.patch("/api/channels/second", json={"display_name": "ใหม่", "expected_revision": channel["revision"]})
    assert patched.status_code == 200 and patched.json()["channel"]["display_name"] == "ใหม่"
    conflict = client.patch("/api/channels/second", json={"display_name": "x", "expected_revision": channel["revision"]})
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "revision_conflict"
    assert conflict.json()["current_revision"] == patched.json()["channel"]["revision"]
    assert conflict.headers["X-OmniCut-Error-Code"] == "revision_conflict"
    immutable = client.patch("/api/channels/second", json={"id": "x", "expected_revision": 2})
    assert immutable.status_code == 422 and immutable.json()["code"] == "channel_id_immutable"

    not_ready = client.post("/api/channels/second/activate")
    assert not_ready.status_code == 409 and not_ready.json()["code"] == "channel_not_ready"
    assert any(i["code"] == "avatar_missing" for i in not_ready.json()["issues"])

    readiness = client.get("/api/channels/second/readiness").json()
    assert readiness["ready"] is False and readiness["status"] == "draft"
    assert {"channel_draft", "watermark_missing"} <= {i["code"] for i in readiness["issues"]}
    assert readiness["posting_ready"] is False

    _write(empty_registry, "assets/second.png")
    rev = client.get("/api/channels/second").json()["channel"]["revision"]
    filled = client.patch(
        "/api/channels/second",
        json={
            "expected_revision": rev,
            "watermark_text": "สงวนลิขสิทธิ์",
            "follow_title": "กดติดตาม",
            "avatar_asset_path": "assets/second.png",
        },
    )
    assert filled.status_code == 200, filled.text
    bad_extra = client.post("/api/channels/second/activate", json={"status": "active"})
    assert bad_extra.status_code == 422 and bad_extra.json()["code"] == "field_not_editable"
    activated = client.post("/api/channels/second/activate", json={"expected_revision": filled.json()["channel"]["revision"]})
    assert activated.status_code == 200 and activated.json()["channel"]["status"] == "active"
    assert client.get("/api/channels/second/readiness").json()["ready"] is True

    archived = client.post("/api/channels/second/archive")
    assert archived.status_code == 200 and archived.json()["channel"]["status"] == "archived"
    assert client.post("/api/channels/main/archive").status_code == 409
    assert [c["id"] for c in client.get("/api/channels?include_archived=false").json()["channels"]] == ["main"]

    assert client.delete("/api/channels/second").status_code == 405  # no delete endpoint
    assert client.post("/api/channels", json=[1, 2]).json()["code"] == "payload_invalid"
    dup = client.post("/api/channels", json={"id": "second", "display_name": "x"})
    assert dup.status_code == 409 and dup.json()["code"] == "channel_exists"


def test_channels_api_never_stores_secrets(empty_registry):
    from scripts.api_server import app

    client = TestClient(app)
    for field_name in ("cookie", "api_key", "password", "session"):
        response = client.post("/api/channels", json={"id": "second", "display_name": "x", field_name: "secret"})
        assert response.status_code == 422 and response.json()["code"] == "field_not_editable"
    assert not config.CHANNELS_FILE.exists()
