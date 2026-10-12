"""Route scope policy loader (multi-channel P1).

``scripts/channel_route_policy.json`` declares, for every FastAPI route
(method + path template), whether it needs a channel scope:

* ``channel`` -- the request must resolve a :class:`ChannelScope`
  (header ``X-OmniCut-Channel``; ``?channel=`` only when
  ``allow_query_scope``; implicit ``main`` only while strict mode is off).
* ``shared`` / ``global`` -- not scope-gated.  A header that is present is
  still validated (unknown -> 422) unless the row sets
  ``ignore_scope_header`` (the channel-registry routes, so a client holding a
  stale channel id can always reload the channel list).

Every new route MUST get a row; ``tests/test_channel_scope.py`` fails when a
live ``APIRoute`` has no row or a row has no live route.  A request that
matches a route without a row is treated as ``channel`` (fail closed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

POLICY_FILE = Path(__file__).resolve().with_name("channel_route_policy.json")

SCOPE_CHANNEL = "channel"
SCOPE_SHARED = "shared"
SCOPE_GLOBAL = "global"
SCOPES = (SCOPE_CHANNEL, SCOPE_SHARED, SCOPE_GLOBAL)
ACCESS_VALUES = ("read", "write", "read_write")
RISK_VALUES = ("blocker", "major", "minor")
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


@dataclass(frozen=True)
class RoutePolicy:
    method: str
    path: str
    scope: str
    allow_query_scope: bool = False
    access: str = "read"
    risk: str = "minor"
    resource_params: tuple[str, ...] = field(default_factory=tuple)
    module: str = ""
    ignore_scope_header: bool = False

    @property
    def key(self) -> tuple[str, str]:
        return (self.method, self.path)


# Fail-closed policy for a matched route that has no row.
UNLISTED_ROUTE_POLICY = RoutePolicy(method="*", path="*", scope=SCOPE_CHANNEL, risk="blocker")


class RoutePolicyTable:
    def __init__(self, rows: Iterable[RoutePolicy]) -> None:
        self._rows: dict[tuple[str, str], RoutePolicy] = {}
        for row in rows:
            if row.key in self._rows:
                raise ValueError(f"duplicate route policy row: {row.method} {row.path}")
            self._rows[row.key] = row

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows.values())

    def keys(self) -> set[tuple[str, str]]:
        return set(self._rows)

    def get(self, method: str, path: str) -> Optional[RoutePolicy]:
        row = self._rows.get((method, path))
        if row is None and method == "HEAD":
            row = self._rows.get(("GET", path))
        return row


def _parse_row(raw: dict) -> RoutePolicy:
    if not isinstance(raw, dict):
        raise ValueError("route policy row must be an object")
    method = raw.get("method")
    path = raw.get("path")
    scope = raw.get("scope")
    if method not in METHODS:
        raise ValueError(f"invalid method in route policy: {method!r}")
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError(f"invalid path in route policy: {path!r}")
    if scope not in SCOPES:
        raise ValueError(f"invalid scope for {method} {path}: {scope!r}")
    allow_query = raw.get("allow_query_scope", False)
    ignore_header = raw.get("ignore_scope_header", False)
    if not isinstance(allow_query, bool) or not isinstance(ignore_header, bool):
        raise ValueError(f"boolean flags must be true/false for {method} {path}")
    if allow_query and method != "GET":
        raise ValueError(f"allow_query_scope is only allowed on GET routes: {method} {path}")
    if ignore_header and scope != SCOPE_GLOBAL:
        raise ValueError(f"ignore_scope_header is only allowed on global routes: {method} {path}")
    access = raw.get("access", "read")
    risk = raw.get("risk", "minor")
    if access not in ACCESS_VALUES:
        raise ValueError(f"invalid access for {method} {path}: {access!r}")
    if risk not in RISK_VALUES:
        raise ValueError(f"invalid risk for {method} {path}: {risk!r}")
    params = raw.get("resource_params", [])
    if not isinstance(params, list) or not all(isinstance(p, str) for p in params):
        raise ValueError(f"resource_params must be a list of strings: {method} {path}")
    return RoutePolicy(
        method=method,
        path=path,
        scope=scope,
        allow_query_scope=allow_query,
        access=access,
        risk=risk,
        resource_params=tuple(params),
        module=str(raw.get("module", "")),
        ignore_scope_header=ignore_header,
    )


def load_route_policy(path: Optional[Path] = None) -> RoutePolicyTable:
    """Parse and validate a policy file (raises ``ValueError`` on any problem)."""
    target = Path(path) if path is not None else POLICY_FILE
    doc = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 or not isinstance(doc.get("routes"), list):
        raise ValueError("route policy must be {schema_version: 1, routes: [...]}")
    return RoutePolicyTable(_parse_row(r) for r in doc["routes"])


@lru_cache(maxsize=1)
def default_route_policy() -> RoutePolicyTable:
    return load_route_policy(POLICY_FILE)
