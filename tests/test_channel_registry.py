"""Channel registry contracts (multi-channel P1: plan §4.1, AC15).

Offline + tmp_path only: the registry, avatar files and the "project root"
live under tmp_path; fonts are replaced by a deterministic fake metrics
object so no test reads 02_Assets/ or 03_Projects/.
"""

from __future__ import annotations

import itertools
import json
import os
import threading
import unicodedata
from pathlib import Path

import pytest

from scripts import channel_store as cs
from scripts.channel_store import ChannelError, ChannelStore, HandleError, normalize_handle

FIXTURE = Path(__file__).parent / "fixtures" / "channel_handle_cases.json"
HANDLE_CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
MAIN_AVATAR_REL = cs.MAIN_SEED["avatar_asset_path"]


class FakeMetrics:
    """Deterministic metrics: 10px per char; '#' counts 100px; emoji unsupported."""

    def width_px(self, text, font_file, size):
        return float(sum(100 if ch == "#" else 10 for ch in text))

    def unsupported_chars(self, text, font_file):
        return cs._fallback_unsupported(text)


def _clock():
    counter = itertools.count(1)
    return lambda: f"2026-10-10T00:00:{next(counter) % 60:02d}Z"


def _write_avatar(root: Path, rel: str, content: bytes = b"\xff\xd8avatar") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture()
def root(tmp_path):
    project = tmp_path / "project"
    _write_avatar(project, MAIN_AVATAR_REL)
    return project


@pytest.fixture()
def store(root):
    return ChannelStore(root / "_Docs" / "channels.json", project_root=root, metrics=FakeMetrics(), clock=_clock())


def _complete_profile(**overrides):
    data = {
        "display_name": "ช่องสินค้าทั่วไป",
        "handle": "@second_shop",
        "watermark_text": "สงวนลิขสิทธิ์ช่อง second",
        "follow_title": "กดติดตามเลย",
        "avatar_asset_path": "assets/second.jpg",
    }
    data.update(overrides)
    return data


def _make_active(store, root, channel_id="second", **overrides):
    _write_avatar(root, "assets/second.jpg")
    created = store.create({"id": channel_id, **_complete_profile(**overrides)})
    return store.activate(channel_id, expected_revision=created["revision"])


def _codes(issues):
    return [issue.code for issue in issues]


# --------------------------------------------------------------------------- handles


@pytest.mark.parametrize("case", HANDLE_CASES, ids=[repr(c["input"])[:40] for c in HANDLE_CASES])
def test_handle_normalization_matches_shared_fixture(case):
    if "expected" in case:
        assert normalize_handle(case["input"]) == case["expected"]
        assert normalize_handle(case["expected"]) == case["expected"]  # idempotent
    else:
        with pytest.raises(HandleError) as info:
            normalize_handle(case["input"])
        assert info.value.reason == case["error"]
        assert info.value.status_code == 422
        assert info.value.message == cs.HANDLE_ERROR_MESSAGES[case["error"]]


def test_handle_fixture_covers_every_error_code():
    used = {c["error"] for c in HANDLE_CASES if "error" in c}
    assert used == set(cs.HANDLE_ERROR_MESSAGES)


# --------------------------------------------------------------------------- read side


def test_missing_registry_read_has_no_side_effects(store, root):
    before = sorted(p.relative_to(root) for p in root.rglob("*"))
    doc = store.load()
    assert doc["revision"] == 0 and doc["schema_version"] == cs.SCHEMA_VERSION
    assert [c["id"] for c in doc["channels"]] == ["main"]
    main = store.get("main")
    assert main["status"] == "active" and main["handle"] == "@rizanntry"
    assert main["display_name"] == "rizannTry"
    assert store.list_channels() and store.readiness("main") == []
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == before
    assert not store.path.exists() and not store.lock_path.exists()


def test_seed_main_matches_existing_identity_sources():
    from scripts import subtitle_engine

    assert cs.MAIN_SEED["watermark_text"] == subtitle_engine.WATERMARK_TEXT
    assert cs.MAIN_SEED["id"] == "main" and cs.MAIN_SEED["status"] == "active"
    assert cs.MAIN_SEED["posting_enabled"] is False


def test_returned_records_are_copies(store):
    main = store.get("main")
    main["display_name"] = "hacked"
    store.load()["channels"][0]["handle"] = "@x"
    assert store.get("main")["display_name"] == "rizannTry"
    assert store.get("main")["handle"] == "@rizanntry"


def test_unknown_channel_is_404(store):
    for bad in ("nope", "../x", "", None, 5):
        with pytest.raises(ChannelError) as info:
            store.get(bad)
        assert info.value.status_code == 404 and info.value.code == "channel_not_found"


@pytest.mark.parametrize(
    "content, fragment",
    [
        (b"{not json", "JSON"),
        (b"[]", "object"),
        (json.dumps({"schema_version": 99, "revision": 0, "channels": []}).encode(), "schema_version"),
        (json.dumps({"schema_version": 1, "revision": 0, "channels": [{"id": "main", "status": "active"}, {"id": "main", "status": "active"}]}).encode(), "ซ้ำ"),
        (json.dumps({"schema_version": 1, "revision": 0, "channels": [{"id": "Bad Id", "status": "active"}]}).encode(), "id"),
        (json.dumps({"schema_version": 1, "revision": 0, "channels": [{"id": "main", "status": "deleted"}]}).encode(), "สถานะ"),
        (json.dumps({"schema_version": 1, "revision": -1, "channels": []}).encode(), "revision"),
    ],
)
def test_corrupt_registry_raises_typed_500(store, content, fragment):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_bytes(content)
    with pytest.raises(ChannelError) as info:
        store.load()
    assert info.value.status_code == 500 and info.value.code == "channel_registry_invalid"
    assert fragment in info.value.message
    with pytest.raises(ChannelError):
        store.create({"id": "second", "display_name": "x"})
    assert store.path.read_bytes() == content  # never rewritten


def test_file_without_main_still_resolves_main(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps({"schema_version": 1, "revision": 3, "channels": []}), encoding="utf-8")
    assert store.get("main")["status"] == "active"
    assert store.revision() == 3


# --------------------------------------------------------------------------- seed / create


def test_seed_is_explicit_and_idempotent(store):
    doc = store.seed()
    assert store.path.is_file()
    assert doc["revision"] == 1
    main = doc["channels"][0]
    assert main["created_at"] and main["revision"] == 1
    raw_before = store.path.read_bytes()
    assert store.seed()["revision"] == 1
    assert store.path.read_bytes() == raw_before
    on_disk = json.loads(raw_before.decode("utf-8"))
    assert on_disk["channels"][0]["identity_hash"] == main["identity_hash"]


def test_create_draft_channel(store):
    channel = store.create({"id": "second", "display_name": "  ช่องรอง  ", "handle": "https://www.tiktok.com/@Second_Shop?lang=th"})
    assert channel["status"] == "draft"
    assert channel["display_name"] == "ช่องรอง"
    assert channel["handle"] == "@second_shop"
    assert channel["timezone"] == "Asia/Bangkok"
    assert channel["posting_enabled"] is False
    assert channel["account_binding"] == {"status": "unverified", "verified_handle": None, "verified_at": None}
    assert channel["overrides"] == {}
    assert channel["revision"] == 1 and len(channel["identity_hash"]) == 64
    assert store.revision() == 1
    assert [c["id"] for c in store.list_channels()] == ["main", "second"]


@pytest.mark.parametrize("bad_id", ["", "a", "Main", "1abc", "-abc", "ab cd", "a" * 33, "ช่อง", None, 12, "a/b", "a.b"])
def test_create_rejects_invalid_ids(store, bad_id):
    with pytest.raises(ChannelError) as info:
        store.create({"id": bad_id, "display_name": "x"})
    assert info.value.status_code == 422 and info.value.code == "channel_id_invalid"
    assert not store.path.exists()


def test_create_validation_errors(store):
    cases = [
        ({"id": "main", "display_name": "x"}, 409, "channel_exists"),
        ({"id": "second"}, 422, "display_name_required"),
        ({"id": "second", "display_name": "x", "posting_enabled": True}, 409, "posting_not_allowed"),
        ({"id": "second", "display_name": "x", "status": "active"}, 422, "field_not_editable"),
        ({"id": "second", "display_name": "x", "api_key": "secret"}, 422, "field_not_editable"),
        ({"id": "second", "display_name": "x", "cookie": "sid=1"}, 422, "field_not_editable"),
        ({"id": "second", "display_name": "x", "account_binding": {"status": "verified"}}, 422, "field_not_editable"),
        ({"id": "second", "display_name": "x", "handle": "bad handle"}, 422, "handle_invalid_chars"),
        ({"id": "second", "display_name": "x", "handle": "@RIZANNTRY"}, 409, "handle_conflict"),
        ({"id": "second", "display_name": "x", "timezone": "Mars/Base"}, 422, "timezone_invalid"),
        ({"id": "second", "display_name": "x", "overrides": []}, 422, "overrides_invalid"),
        ({"id": "second", "display_name": "x", "overrides": {"a": float("nan")}}, 422, "overrides_invalid"),
    ]
    for payload, status, code in cases:
        with pytest.raises(ChannelError) as info:
            store.create(payload)
        assert (info.value.status_code, info.value.code) == (status, code), payload
    assert not store.path.exists()


def test_archived_ids_are_never_reused(store, root):
    _make_active(store, root)
    store.archive("second")
    with pytest.raises(ChannelError) as info:
        store.create({"id": "second", "display_name": "new"})
    assert info.value.code == "channel_exists"


# --------------------------------------------------------------------------- text rules


def test_text_is_nfc_normalized_and_trimmed(store):
    decomposed = unicodedata.normalize("NFD", "Café ช่อง")
    channel = store.create({"id": "second", "display_name": decomposed + "\u200b"})
    assert channel["display_name"] == unicodedata.normalize("NFC", "Café ช่อง")


@pytest.mark.parametrize(
    "field_name, value, code",
    [
        ("display_name", "ab\x00c", "text_control_chars"),
        ("display_name", "ab\u200bc", "text_control_chars"),
        ("watermark_text", "line1\nline2", "text_control_chars"),
        ("watermark_text", "a\u2028b", "text_control_chars"),
        ("follow_title", "x\u202ey", "text_control_chars"),
        ("display_name", "ช่อง😀", "text_unsupported_chars"),
        ("follow_title", "ติดตาม\u2764\ufe0f", "text_unsupported_chars"),
        ("display_name", "ก" * 41, "text_too_long"),
        ("watermark_text", "a" * 65, "text_too_long"),
        ("follow_title", "a" * 25, "text_too_long"),
        ("display_name", "#####", "text_too_wide"),
        ("display_name", 123, "text_invalid_type"),
    ],
)
def test_text_rules_reject_instead_of_truncating(store, field_name, value, code):
    payload = {"id": "second", "display_name": "ok"}
    payload[field_name] = value
    with pytest.raises(ChannelError) as info:
        store.create(payload)
    assert info.value.status_code == 422 and info.value.code == code
    assert info.value.extra.get("field") == field_name
    assert not store.path.exists()


def test_text_limits_accept_exact_boundaries(store):
    channel = store.create(
        {"id": "second", "display_name": "ก" * 40, "watermark_text": "a" * 60, "follow_title": "b" * 24}
    )
    assert len(channel["display_name"]) == 40 and len(channel["follow_title"]) == 24


def test_real_metrics_fallback_without_fonts(tmp_path):
    metrics = cs.TextMetrics(fonts_dir=tmp_path)  # empty dir: no font files
    assert metrics.width_px("abc", "Anuphan-Bold.ttf", 40) is None
    assert metrics.unsupported_chars("ok😀", "Anuphan-Bold.ttf") == ["😀"]
    assert metrics.unsupported_chars("ช่อง ok", "Anuphan-Bold.ttf") == []


def test_layout_limits_are_documented_numbers():
    limits = cs.TEXT_FIELD_LIMITS
    assert (limits["display_name"].font_px, limits["display_name"].max_width_px) == (40, 446.0)
    assert (limits["watermark_text"].font_px, limits["watermark_text"].max_width_px) == (26, 600.0)
    assert (limits["follow_title"].font_px, limits["follow_title"].max_width_px) == (124, 960.0)


# --------------------------------------------------------------------------- avatar


@pytest.mark.parametrize(
    "path",
    ["/etc/passwd.jpg", "C:/x/a.jpg", "C:\\x\\a.jpg", "../outside.jpg", "assets/../../x.jpg", "assets//a.jpg", "assets/a.gif", "assets/a", "//server/share/a.jpg"],
)
def test_avatar_path_containment(store, path):
    with pytest.raises(ChannelError) as info:
        store.create({"id": "second", "display_name": "x", "avatar_asset_path": path})
    assert info.value.code == "avatar_path_invalid"


def test_avatar_missing_file_is_readiness_issue_not_crash(store, root):
    channel = store.create({"id": "second", **_complete_profile(avatar_asset_path="assets\\missing.png")})
    assert channel["avatar_asset_path"] == "assets/missing.png"
    assert "avatar_file_missing" in _codes(store.readiness("second"))


def test_identity_hash_tracks_identity_fields_and_avatar_bytes(store, root):
    avatar = _write_avatar(root, "assets/second.jpg", b"v1")
    created = store.create({"id": "second", **_complete_profile()})
    h1 = created["identity_hash"]
    tz = store.update("second", {"timezone": "Asia/Tokyo"}, expected_revision=created["revision"])
    assert tz["identity_hash"] == h1 and tz["revision"] == 2  # timezone is not identity
    noop = store.update("second", {"timezone": "Asia/Tokyo"}, expected_revision=tz["revision"])
    assert noop["revision"] == 2 and store.revision() == 2  # no-op does not bump
    renamed = store.update("second", {"watermark_text": "ลายน้ำใหม่"}, expected_revision=2)
    assert renamed["identity_hash"] != h1 and renamed["revision"] == 3
    avatar.write_bytes(b"v2")
    refreshed = store.update("second", {}, expected_revision=3)
    assert refreshed["revision"] == 4 and refreshed["identity_hash"] != renamed["identity_hash"]
    assert refreshed["identity_hash"] == cs.compute_identity_hash(refreshed, project_root=root)


def test_identity_hash_is_stable_and_field_ordered():
    channel = {"display_name": "a", "handle": "@ab", "watermark_text": "w", "follow_title": "f", "avatar_asset_path": ""}
    shuffled = dict(reversed(list(channel.items())))
    root = Path(".")
    assert cs.compute_identity_hash(channel, project_root=root) == cs.compute_identity_hash(shuffled, project_root=root)
    assert cs.compute_identity_hash({**channel, "status": "archived", "timezone": "UTC", "id": "x"}, project_root=root) == cs.compute_identity_hash(channel, project_root=root)


# --------------------------------------------------------------------------- update / revision


def test_update_requires_expected_revision_and_detects_conflicts(store):
    created = store.create({"id": "second", "display_name": "x"})
    with pytest.raises(ChannelError) as info:
        store.update("second", {"display_name": "y"}, expected_revision=None)
    assert (info.value.status_code, info.value.code) == (422, "expected_revision_required")
    for bad in (True, -1, "1", 1.0):
        with pytest.raises(ChannelError) as info:
            store.update("second", {"display_name": "y"}, expected_revision=bad)
        assert info.value.code == "expected_revision_invalid"
    store.update("second", {"display_name": "y"}, expected_revision=created["revision"])
    with pytest.raises(ChannelError) as info:
        store.update("second", {"display_name": "z"}, expected_revision=created["revision"])
    assert (info.value.status_code, info.value.code) == (409, "revision_conflict")
    assert info.value.extra["current_revision"] == 2
    assert store.get("second")["display_name"] == "y"


def test_id_is_immutable(store):
    created = store.create({"id": "second", "display_name": "x"})
    with pytest.raises(ChannelError) as info:
        store.update("second", {"id": "third"}, expected_revision=created["revision"])
    assert info.value.code == "channel_id_immutable"
    for field_name in ("status", "revision", "identity_hash", "created_at", "account_binding"):
        with pytest.raises(ChannelError) as info:
            store.update("second", {field_name: "x"}, expected_revision=created["revision"])
        assert info.value.code == "field_not_editable"


def test_active_channel_cannot_lose_required_fields(store, root):
    active = _make_active(store, root)
    with pytest.raises(ChannelError) as info:
        store.update("second", {"watermark_text": ""}, expected_revision=active["revision"])
    assert info.value.code == "watermark_missing"
    with pytest.raises(ChannelError) as info:
        store.update("second", {"display_name": "   "}, expected_revision=active["revision"])
    assert info.value.code == "display_name_required"


def test_unknown_fields_in_file_are_preserved(store):
    store.seed()
    doc = json.loads(store.path.read_text(encoding="utf-8"))
    doc["future_top_level"] = {"x": 1}
    doc["channels"][0]["future_field"] = "keep"
    store.path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    store.create({"id": "second", "display_name": "x"})
    after = json.loads(store.path.read_text(encoding="utf-8"))
    assert after["future_top_level"] == {"x": 1}
    assert after["channels"][0]["future_field"] == "keep"


# --------------------------------------------------------------------------- status transitions


def test_activate_requires_complete_profile(store, root):
    created = store.create({"id": "second", "display_name": "x"})
    with pytest.raises(ChannelError) as info:
        store.activate("second", expected_revision=created["revision"])
    assert (info.value.status_code, info.value.code) == (409, "channel_not_ready")
    codes = [i["code"] for i in info.value.extra["issues"]]
    assert {"handle_missing", "watermark_missing", "follow_title_missing", "avatar_missing"} <= set(codes)
    assert store.get("second")["status"] == "draft"


def test_activate_archive_lifecycle(store, root):
    active = _make_active(store, root)
    assert active["status"] == "active"
    assert store.activate("second")["revision"] == active["revision"]  # idempotent
    archived = store.archive("second", expected_revision=active["revision"])
    assert archived["status"] == "archived" and archived["posting_enabled"] is False
    assert store.get("second")["status"] == "archived"  # reads keep working
    assert store.archive("second")["revision"] == archived["revision"]  # idempotent
    with pytest.raises(ChannelError) as info:
        store.update("second", {"display_name": "x"}, expected_revision=archived["revision"])
    assert (info.value.status_code, info.value.code) == (409, "channel_archived")
    assert "archived" in info.value.message
    reactivated = store.activate("second", expected_revision=archived["revision"])
    assert reactivated["status"] == "active"


def test_main_cannot_be_archived(store):
    with pytest.raises(ChannelError) as info:
        store.archive("main")
    assert (info.value.status_code, info.value.code) == (409, "default_channel_protected")


def test_handle_unique_among_non_archived_only(store, root):
    _make_active(store, root, "second")
    with pytest.raises(ChannelError) as info:
        store.create({"id": "third", "display_name": "x", "handle": "second_shop"})
    assert (info.value.status_code, info.value.code) == (409, "handle_conflict")
    store.archive("second")
    third = store.create({"id": "third", "display_name": "x", "handle": "second_shop"})
    assert third["handle"] == "@second_shop"
    with pytest.raises(ChannelError) as info:
        store.activate("second")
    assert info.value.code == "handle_conflict"


def test_display_name_is_never_used_for_matching(store):
    store.create({"id": "second", "display_name": "rizannTry"})
    assert store.get("second")["display_name"] == store.get("main")["display_name"]


# --------------------------------------------------------------------------- posting / binding


def test_posting_requires_active_ready_and_verified_binding(store, root):
    active = _make_active(store, root)
    with pytest.raises(ChannelError) as info:
        store.update("second", {"posting_enabled": True}, expected_revision=active["revision"])
    assert (info.value.status_code, info.value.code) == (409, "posting_not_allowed")
    assert "account_unverified" in [i["code"] for i in info.value.extra["issues"]]
    with pytest.raises(ChannelError) as info:
        store.set_account_binding("second", status="verified", verified_handle="@someone_else")
    assert info.value.code == "account_handle_mismatch"
    bound = store.set_account_binding("second", status="verified", verified_handle="https://www.tiktok.com/@Second_Shop")
    assert bound["account_binding"]["status"] == "verified"
    assert bound["account_binding"]["verified_handle"] == "@second_shop"
    enabled = store.update("second", {"posting_enabled": True}, expected_revision=bound["revision"])
    assert enabled["posting_enabled"] is True
    assert store.posting_issues("second") == []
    # Changing the handle invalidates the binding and disables posting.
    moved = store.update("second", {"handle": "@second_new"}, expected_revision=enabled["revision"])
    assert moved["posting_enabled"] is False
    assert moved["account_binding"]["status"] == "unverified"


def test_posting_blocked_for_draft_even_if_bound(store, root):
    _write_avatar(root, "assets/second.jpg")
    created = store.create({"id": "second", **_complete_profile()})
    bound = store.set_account_binding("second", status="verified", verified_handle="@second_shop")
    with pytest.raises(ChannelError) as info:
        store.update("second", {"posting_enabled": True}, expected_revision=bound["revision"])
    assert "channel_draft" in [i["code"] for i in info.value.extra["issues"]]
    assert created["status"] == "draft"


# --------------------------------------------------------------------------- readiness (AC15)


def test_readiness_ac15_matrix(store, root):
    # draft
    store.create({"id": "draft1", "display_name": "x"})
    assert "channel_draft" in _codes(store.readiness("draft1"))
    # archived
    _make_active(store, root, "second")
    store.archive("second")
    assert "channel_archived" in _codes(store.readiness("second"))
    # main with avatar removed
    (root / MAIN_AVATAR_REL).unlink()
    assert _codes(store.readiness("main")) == ["avatar_file_missing"]


def test_readiness_flags_hand_edited_registry(store, root):
    store.seed()
    doc = json.loads(store.path.read_text(encoding="utf-8"))
    doc["channels"].append(
        {
            "id": "hand",
            "status": "active",
            "display_name": "x" * 50,
            "handle": "@rizanntry",
            "watermark_text": "bad\u0007text",
            "follow_title": "ok",
            "avatar_asset_path": "../escape.jpg",
            "timezone": "Nowhere/City",
        }
    )
    store.path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    codes = _codes(store.readiness("hand"))
    for expected in ("text_too_long", "text_control_chars", "handle_duplicate", "avatar_path_invalid", "timezone_invalid"):
        assert expected in codes, (expected, codes)
    assert "handle_duplicate" in _codes(store.readiness("main"))


def test_readiness_issues_have_thai_messages(store):
    store.create({"id": "draft1", "display_name": "x"})
    for issue in store.readiness("draft1"):
        assert issue.message and any("\u0e00" <= ch <= "\u0e7f" for ch in issue.message)
        assert set(issue.to_dict()) == {"code", "message", "field"}


# --------------------------------------------------------------------------- write safety


def test_atomic_write_failure_keeps_previous_file(store, monkeypatch):
    store.seed()
    before = store.path.read_bytes()

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(cs.os, "replace", boom)
    with pytest.raises(OSError):
        store.create({"id": "second", "display_name": "x"})
    monkeypatch.undo()
    assert store.path.read_bytes() == before
    leftovers = [p.name for p in store.path.parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert [c["id"] for c in store.list_channels()] == ["main"]


def test_written_file_is_valid_utf8_json_with_thai(store):
    store.seed()
    text = store.path.read_text(encoding="utf-8")
    assert "สงวนลิขสิทธิ์" in text  # ensure_ascii=False
    assert json.loads(text)["schema_version"] == 1


def test_concurrent_creates_do_not_lose_updates(store):
    store.seed()
    errors = []
    barrier = threading.Barrier(12)

    def worker(i):
        try:
            other = ChannelStore(store.path, project_root=store.project_root, metrics=FakeMetrics())
            barrier.wait()
            other.create({"id": f"chan{i:02d}", "display_name": f"ช่อง {i}"})
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    doc = store.load()
    assert sorted(c["id"] for c in doc["channels"]) == sorted(["main"] + [f"chan{i:02d}" for i in range(12)])
    assert doc["revision"] == 1 + 12


def test_concurrent_read_modify_write_with_expected_revision(store):
    created = store.create({"id": "second", "display_name": "x", "overrides": {"n": 0}})
    per_thread = 5
    threads_n = 6
    errors = []

    def worker():
        try:
            done = 0
            while done < per_thread:
                current = store.get("second")
                n = current["overrides"]["n"]
                try:
                    store.update("second", {"overrides": {"n": n + 1}}, expected_revision=current["revision"])
                    done += 1
                except ChannelError as exc:
                    if exc.code != "revision_conflict":
                        raise
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    final = store.get("second")
    assert final["overrides"]["n"] == per_thread * threads_n
    assert final["revision"] == created["revision"] + per_thread * threads_n


def test_external_file_change_is_picked_up(store):
    store.seed()
    doc = json.loads(store.path.read_text(encoding="utf-8"))
    doc["channels"][0]["display_name"] = "changed outside"
    doc["revision"] = 7
    store.path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    os.utime(store.path, ns=(1, 1))  # even with an old mtime the size/inode signature changes
    assert store.get("main")["display_name"] == "changed outside"
    assert store.revision() == 7


_PROCESS_WRITER = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from scripts import channel_store as cs

class M:
    def width_px(self, *a):
        return 1.0
    def unsupported_chars(self, text, font_file):
        return []

store = cs.ChannelStore(Path(sys.argv[2]), project_root=Path(sys.argv[3]), metrics=M())
for i in range(int(sys.argv[5])):
    store.create({"id": f"{sys.argv[4]}{i:02d}", "display_name": "x"})
"""


def test_cross_process_writers_do_not_lose_updates(store, tmp_path):
    import subprocess
    import sys

    store.seed()
    script = tmp_path / "writer.py"
    script.write_text(_PROCESS_WRITER, encoding="utf-8")
    project_root = str(Path(__file__).resolve().parent.parent)
    procs = [
        subprocess.Popen(
            [sys.executable, str(script), project_root, str(store.path), str(store.project_root), prefix, "6"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for prefix in ("pa", "pb", "pc")
    ]
    reads = 0
    while any(proc.poll() is None for proc in procs):  # read while other processes replace the file
        cs._READ_CACHE.clear()
        assert store.get("main")["id"] == "main"
        reads += 1
    assert reads > 0
    for proc in procs:
        _out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err.decode("utf-8", "replace")[-2000:]
    doc = store.load()
    assert len(doc["channels"]) == 1 + 18
    assert doc["revision"] == 1 + 18
    assert not [p for p in store.path.parent.iterdir() if p.name.endswith(".tmp")]


def test_readers_never_fail_while_writers_replace_the_file(store):
    store.seed()
    stop = threading.Event()
    errors = []
    reads = [0]

    def reader():
        local = ChannelStore(store.path, project_root=store.project_root, metrics=FakeMetrics())
        while not stop.is_set():
            try:
                cs._READ_CACHE.clear()  # force real file reads, racing os.replace
                assert local.get("main")["id"] == "main"
                reads[0] += 1
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)
                return

    readers = [threading.Thread(target=reader) for _ in range(4)]
    for t in readers:
        t.start()
    try:
        for i in range(40):
            store.create({"id": f"w{i:02d}", "display_name": "x"})
    finally:
        stop.set()
        for t in readers:
            t.join()
    assert errors == []
    assert reads[0] > 0
    assert len(store.list_channels()) == 41


def test_posting_gate_only_on_enable_transition(store, root):
    active = _make_active(store, root)
    bound = store.set_account_binding("second", status="verified", verified_handle="@second_shop")
    enabled = store.update("second", {"posting_enabled": True}, expected_revision=bound["revision"])
    (root / "assets" / "second.jpg").unlink()
    # an unrelated edit is not blocked; readiness still reports the gap
    edited = store.update("second", {"timezone": "Asia/Tokyo"}, expected_revision=enabled["revision"])
    assert edited["posting_enabled"] is True
    assert "avatar_file_missing" in _codes(store.posting_issues("second"))
    assert active["status"] == "active"
