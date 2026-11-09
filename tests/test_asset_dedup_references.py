"""Duplicate cleaning never breaks product links; scans are channel-scoped
(audit S1-12). Temp media roots only; product rows are stubbed."""

import os
import time
from pathlib import Path

import pytest

from scripts.asset_dedup import AssetDedupEngine
from scripts.product_store import ProductStore

DATA = b"same clip bytes " * 200


@pytest.fixture
def env(tmp_path, monkeypatch):
    inbox, raw, archive = tmp_path / "00_Inbox", tmp_path / "01_Raw", tmp_path / "06_Archive"
    for d in (inbox, raw, archive):
        d.mkdir()
    monkeypatch.setattr("scripts.asset_dedup.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.asset_dedup.INBOX_DIR", inbox)
    monkeypatch.setattr("scripts.asset_dedup.RAW_DIR", raw)
    monkeypatch.setattr("scripts.asset_dedup.ARCHIVE_DIR", archive)
    monkeypatch.setattr("scripts.asset_dedup.TRASH_DIR", archive / ".trash")
    products = []
    monkeypatch.setattr(ProductStore, "_load", classmethod(lambda cls: products))
    return inbox, raw, products


def _pair(inbox, raw, pid="p1"):
    a = inbox / "a.mp4"
    a.write_bytes(DATA)
    (raw / pid).mkdir(exist_ok=True)
    b = raw / pid / "b.mp4"
    b.write_bytes(DATA)
    return a, b


def test_referenced_file_is_never_deleted(env):
    inbox, raw, products = env
    a, b = _pair(inbox, raw)
    products.append({"id": "p1", "channel_id": "main", "videos": [{"path": "01_Raw/p1/b.mp4"}]})

    res = AssetDedupEngine.clean_duplicates([str(b)], move_to_trash=False)

    assert res["cleaned_count"] == 0
    assert b.exists()
    assert any("ถูกใช้งานอยู่ในสินค้า" in e for e in res["errors"])


def test_reference_inside_angle_and_absolute_path_counts(env):
    inbox, raw, products = env
    a, b = _pair(inbox, raw)
    products.append({"id": "p1", "channel_id": "main", "angles": [{"selected_videos": [str(a)]}]})

    res = AssetDedupEngine.clean_duplicates([str(a)], move_to_trash=False)

    assert res["cleaned_count"] == 0 and a.exists()


def test_unreferenced_copy_is_still_cleaned(env):
    inbox, raw, products = env
    a, b = _pair(inbox, raw)
    products.append({"id": "p1", "channel_id": "main", "videos": [{"path": "01_Raw/p1/b.mp4"}]})

    res = AssetDedupEngine.clean_duplicates([str(a)], move_to_trash=False)

    assert res["cleaned_count"] == 1
    assert not a.exists() and b.exists()


def test_scan_keeps_referenced_copy_as_original(env):
    inbox, raw, products = env
    a, b = _pair(inbox, raw)
    old = time.time() - 3600
    os.utime(a, (old, old))  # a is older, but b is the one a product uses
    products.append({"id": "p1", "channel_id": "main", "videos": [{"path": "01_Raw/p1/b.mp4"}]})

    res = AssetDedupEngine.scan_duplicates(min_file_size_bytes=10)

    group = res["groups"][0]
    assert Path(group["original"]["full_path"]) == b.resolve()
    assert [d["file_name"] for d in group["duplicates"]] == ["a.mp4"]


def test_scan_hides_other_channels_media(env):
    inbox, raw, products = env
    _pair(inbox, raw, pid="foreign")
    (raw / "foreign" / "c.mp4").write_bytes(DATA)
    products.append({"id": "foreign", "channel_id": "other", "videos": []})

    main_view = AssetDedupEngine.scan_duplicates(
        min_file_size_bytes=10,
        path_filter=AssetDedupEngine.channel_path_filter("main"),
    )
    other_view = AssetDedupEngine.scan_duplicates(
        min_file_size_bytes=10,
        path_filter=AssetDedupEngine.channel_path_filter("other"),
    )

    main_paths = {d["file_name"] for g in main_view["groups"] for d in g["duplicates"]} | {
        g["original"]["file_name"] for g in main_view["groups"]
    }
    assert "b.mp4" not in main_paths and "c.mp4" not in main_paths
    assert other_view["total_duplicate_files"] == 2  # a (shared inbox), b, c -> 1 original + 2 dups
