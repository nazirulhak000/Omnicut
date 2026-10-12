"""Record-level channel ownership helpers for channel-owned stores (multi-channel P2).

Contract (ADR ``_Docs/Plans/ADR_MULTI_CHANNEL_20261010.md`` section "P2 store contract"):

* Every channel-owned record carries a top-level ``channel_id`` (slug).  A
  record WITHOUT ``channel_id`` (key missing or ``None``) is *legacy*.
* Legacy rows belong to ``main`` ONLY while strict mode is off (compat).  In
  strict mode they are invisible to scoped reads and unwritable until the
  migration tool (P2.3) assigns an owner.
* Store methods take keyword ``channel_id``:
    - ``"a"``  -> scoped to channel ``a`` (+ legacy rows when ``a`` is main and
      strict is off);
    - ``None`` -> compat only: the old unscoped behaviour (every row).  In
      strict mode ``None`` raises 422 ``channel_scope_missing``;
    - ``all_channels=True`` -> explicit system/maintenance/migration bypass in
      any mode.  Allowed only in the modules listed in
      :data:`ALL_CHANNELS_ALLOWED_MODULES` (enforced by a repo test).
* New records are stamped server-side; a client-supplied ``channel_id`` that
  differs from the scope is rejected; an owner never changes through a
  normal update.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping, Optional

from scripts import config
from scripts.channel_store import ChannelError, is_valid_channel_id

OWNER_KEY = "channel_id"

# Modules (repo-relative POSIX paths) that may pass ``all_channels=True``.
# Route handlers (``scripts/api_*.py``) must never appear here -- see
# tests/test_channel_store_primitives.py::test_all_channels_only_in_allowlisted_modules.
ALL_CHANNELS_ALLOWED_MODULES = frozenset(
    {
        # ownership core + store modules themselves
        "scripts/channel_ownership.py",
        "scripts/db.py",
        "scripts/product_store.py",
        "scripts/export_registry.py",
        "scripts/post_log.py",
        "scripts/schedule_store.py",
        # maintenance / backfill / migration tools
        "scripts/backfill_product_codes.py",
        "scripts/migrate_paths_to_relative.py",
        "scripts/migrate_json_to_sqlite.py",
        "scripts/migrate_compound_angle_ids.py",
        "tools/migrate_channels.py",
    }
)


@dataclasses.dataclass(frozen=True)
class StoreScope:
    """Resolved store-level scope.

    ``channel_id is None`` means "every row" (compat unscoped call or an
    explicit ``all_channels`` maintenance call).
    """

    channel_id: Optional[str]
    include_legacy: bool
    all_channels: bool = False

    @property
    def unscoped(self) -> bool:
        return self.channel_id is None

    @property
    def effective_owner(self) -> Optional[str]:
        """Owner stamped on NEW records created under this scope.

        Compat unscoped calls (``channel_id=None``, strict off) create records
        for the default channel -- exactly what an implicit-``main`` request
        would do.  ``all_channels`` has no owner: creating records under it
        is refused (a maintenance tool must name the owner explicitly).
        """
        if self.channel_id is not None:
            return self.channel_id
        if self.all_channels:
            return None
        return config.DEFAULT_CHANNEL_ID

    def owns(self, record: Mapping[str, Any]) -> bool:
        if self.channel_id is None:
            return True
        owner = record.get(OWNER_KEY)
        if owner is None:
            return self.include_legacy
        return owner == self.channel_id


def _missing_scope_error() -> ChannelError:
    return ChannelError(
        422,
        "channel_scope_missing",
        "ต้องระบุช่องก่อนทำรายการนี้ (โหมดหลายช่องเปิดอยู่) กรุณาอัปเดตแอปหรือเลือกช่อง",
    )


def resolve_store_scope(channel_id: Optional[str] = None, *, all_channels: bool = False) -> StoreScope:
    """Turn a store call's ``channel_id``/``all_channels`` into a :class:`StoreScope`.

    Strict mode is read on every call (``config.is_multi_channel_strict``).
    """
    if all_channels:
        if channel_id is not None:
            raise ValueError("all_channels=True ใช้คู่กับ channel_id ไม่ได้")
        return StoreScope(None, True, True)
    strict = config.is_multi_channel_strict()
    if channel_id is None:
        if strict:
            raise _missing_scope_error()
        return StoreScope(None, True, False)
    if not is_valid_channel_id(channel_id):
        raise ChannelError(422, "channel_scope_invalid", "รหัสช่องไม่ถูกต้อง กรุณาเลือกช่องใหม่")
    include_legacy = channel_id == config.DEFAULT_CHANNEL_ID and not strict
    return StoreScope(channel_id, include_legacy, False)


def owner_for_new_record(scope: StoreScope, client_value: Any = None) -> str:
    """Owner to stamp on a new record; rejects a conflicting client value (422)."""
    owner = scope.effective_owner
    if owner is None:
        raise ValueError("สร้างข้อมูลใหม่แบบ all_channels ไม่ได้ ต้องระบุช่องเจ้าของ")
    if client_value is not None and client_value != owner:
        raise ChannelError(
            422,
            "channel_scope_conflict",
            f"channel_id ในข้อมูล ({client_value}) ไม่ตรงกับช่องที่เลือก ({owner})",
        )
    return owner


def reject_owner_change(current: Mapping[str, Any], requested: Any) -> None:
    """A normal update may repeat the current owner but never change it (422)."""
    if requested != current.get(OWNER_KEY):
        raise ChannelError(
            422,
            "channel_id_immutable",
            "เปลี่ยนช่องเจ้าของข้อมูลผ่านการแก้ไขทั่วไปไม่ได้",
        )


def reject_foreign_body_channel(payload: Any, channel_id: str) -> None:
    """API helper: a body ``channel_id`` must equal the request scope (422)."""
    if isinstance(payload, Mapping) and payload.get(OWNER_KEY) is not None and payload.get(OWNER_KEY) != channel_id:
        raise ChannelError(
            422,
            "channel_scope_conflict",
            f"channel_id ในข้อมูล ({payload.get(OWNER_KEY)}) ไม่ตรงกับช่องที่เลือก ({channel_id})",
        )
