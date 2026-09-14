"""
Regression tests for the O(n) rewrite of the matching loops in
scripts/api_exports.py (list_exports) and scripts/api_videos.py
(get_raw_vault). Both used to scan every product x every angle/file per
export/raw file (O(products x angles) / O(products x raw_files)); they now
build lookup dicts once per request and do O(1) lookups per file.

These tests build a small fixture with several products/angles/files and
assert each file still maps to the exact product+angle the OLD nested-loop
code would have picked, including the priority order between the different
match strategies (exact video_url match > project-name match > product-id
fallback) and the first-match-wins tie-break when two candidates could
match the same file. The goal is to catch a semantics regression in the
lookup rewrite, not to test new behavior.

Uses tmp_path + monkeypatch throughout, per .agents/rules/testing_standard.md
rule 3 -- never touches the real _Docs/products.json, 01_Raw/, or
04_Exports/.
"""
import sys
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store as ps
from scripts import api_exports
from scripts import api_videos
from scripts import export_registry
from scripts import media_service


# ---------------------------------------------------------------------------
# list_exports() -- scripts/api_exports.py
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_exports(tmp_path, monkeypatch):
    """Redirects every path list_exports()/get_raw_vault() touch into
    tmp_path: the product store, 04_Exports/{Ready_to_post,Posted},
    01_Raw/, 00_Inbox/, and 03_Projects/."""
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)

    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    posted_dir = tmp_path / "04_Exports" / "Posted"
    exports_dir.mkdir(parents=True, exist_ok=True)
    posted_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_exports, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_exports, "EXPORTS_DIR", exports_dir)
    monkeypatch.setattr(api_exports, "POSTED_DIR", posted_dir)
    monkeypatch.setattr(export_registry, "BASE_DIR", tmp_path)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", tmp_path / "_Docs" / "export_registry.json")

    raw_dir = tmp_path / "01_Raw"
    inbox_dir = tmp_path / "00_Inbox"
    raw_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_videos, "RAW_DIR", raw_dir)
    monkeypatch.setattr(api_videos, "INBOX_DIR", inbox_dir)

    # get_file_info() (used by both list_exports and get_raw_vault via
    # media_service) computes rel_path/cover lookups off ITS OWN
    # module-level BASE_DIR/COVERS_DIR, bound at import time -- must be
    # redirected too or every file falls outside the fake BASE_DIR and
    # relative_to() raises.
    monkeypatch.setattr(media_service, "BASE_DIR", tmp_path)
    monkeypatch.setattr(media_service, "COVERS_DIR", tmp_path / "05_Covers_Thumbnails")

    return tmp_path


def _seed_products(tmp_path, products):
    (tmp_path / "_Docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_Docs" / "products.json").write_text(
        json.dumps(products, ensure_ascii=False), encoding="utf-8",
    )


def test_list_exports_matches_by_exact_video_url_stem(isolated_exports):
    """Check 1: a file whose stem exactly matches an angle's video_url stem
    must resolve to that product+angle, even with several unrelated
    products/angles in the store (this is the O(products x angles) loop
    that got rewritten to a dict lookup)."""
    tmp_path = isolated_exports
    _seed_products(tmp_path, [
        {
            "id": "prod_a", "name": "Product A",
            "angles": [
                {"angle_id": "a1", "video_url": "04_Exports/Ready_to_post/prod_a_hook1_20260101_000000.mp4"},
                {"angle_id": "a2", "video_url": "04_Exports/Ready_to_post/prod_a_hook2_20260101_000000.mp4"},
            ],
        },
        {
            "id": "prod_b", "name": "Product B",
            "angles": [
                {"angle_id": "b1", "video_url": "04_Exports/Ready_to_post/prod_b_hook1_20260101_000000.mp4"},
            ],
        },
    ])

    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    for name in [
        "prod_a_hook1_20260101_000000.mp4",
        "prod_a_hook2_20260101_000000.mp4",
        "prod_b_hook1_20260101_000000.mp4",
    ]:
        (exports_dir / name).write_bytes(b"fake mp4")

    result = api_exports.list_exports()
    by_name = {item["name"]: item for item in result["exports"]}

    assert by_name["prod_a_hook1_20260101_000000.mp4"]["product_id"] == "prod_a"
    assert by_name["prod_a_hook1_20260101_000000.mp4"]["angle_id"] == "a1"
    assert by_name["prod_a_hook2_20260101_000000.mp4"]["product_id"] == "prod_a"
    assert by_name["prod_a_hook2_20260101_000000.mp4"]["angle_id"] == "a2"
    assert by_name["prod_b_hook1_20260101_000000.mp4"]["product_id"] == "prod_b"
    assert by_name["prod_b_hook1_20260101_000000.mp4"]["angle_id"] == "b1"


def test_list_exports_hydrates_all_identities_in_one_bulk_call(isolated_exports, monkeypatch):
    """The export listing must not open one registry transaction per file."""
    tmp_path = isolated_exports
    _seed_products(tmp_path, [{
        "id": "prod_bulk", "name": "Bulk Product",
        "angles": [
            {"angle_id": "a1", "video_url": "04_Exports/Ready_to_post/bulk_1.mp4"},
            {"angle_id": "a2", "video_url": "04_Exports/Ready_to_post/bulk_2.mp4"},
            {"angle_id": "a3", "video_url": "04_Exports/Ready_to_post/bulk_3.mp4"},
        ],
    }])
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    for name in ("bulk_1.mp4", "bulk_2.mp4", "bulk_3.mp4"):
        (exports_dir / name).write_bytes(b"fake mp4")

    calls = []
    original = export_registry.ExportRegistry.ensure_many

    def record_bulk_call(entries):
        calls.append(len(entries))
        return original(entries)

    monkeypatch.setattr(export_registry.ExportRegistry, "ensure_many", record_bulk_call)
    result = api_exports.list_exports()

    assert len(result["exports"]) == 3
    assert calls == [3]


def test_list_exports_first_match_wins_when_two_angles_share_a_video_stem(isolated_exports):
    """If two angles (across different products) reference the exact same
    video_url basename, the OLD code's nested loop stopped at the first
    product/angle in all_products/angles iteration order. A naive
    dict-based rewrite could let the LATER one silently win instead (last
    write to the dict). This locks in first-match-wins."""
    tmp_path = isolated_exports
    _seed_products(tmp_path, [
        {
            "id": "prod_first", "name": "First (should win)",
            "angles": [
                {"angle_id": "only", "video_url": "04_Exports/Ready_to_post/shared_name_20260101_000000.mp4"},
            ],
        },
        {
            "id": "prod_second", "name": "Second (should lose)",
            "angles": [
                {"angle_id": "only", "video_url": "04_Exports/Ready_to_post/shared_name_20260101_000000.mp4"},
            ],
        },
    ])

    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    (exports_dir / "shared_name_20260101_000000.mp4").write_bytes(b"fake mp4")

    result = api_exports.list_exports()
    item = next(i for i in result["exports"] if i["name"] == "shared_name_20260101_000000.mp4")
    assert item["product_id"] == "prod_first", (
        "dict-based rewrite must preserve first-match-wins iteration order, "
        "not let a later product/angle overwrite the earlier match"
    )


def test_list_exports_falls_back_to_product_id_token_match(isolated_exports):
    """Check 3 (product id fallback) must still fire when neither check 1
    (video_url match) nor check 2 (project name match) hits -- and only for
    a file that reaches that fallback."""
    tmp_path = isolated_exports
    _seed_products(tmp_path, [
        {"id": "prodid123", "name": "No angles product", "angles": [], "projects": []},
    ])

    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    (exports_dir / "prodid123_some_clip.mp4").write_bytes(b"fake mp4")

    result = api_exports.list_exports()
    item = next(i for i in result["exports"] if i["name"] == "prodid123_some_clip.mp4")
    assert item["product_id"] == "prodid123"


def test_list_exports_unmatched_file_is_unlinked(isolated_exports):
    """A file matching nothing must be reported unlinked, not accidentally
    grabbed by an unrelated product because of an over-eager lookup."""
    tmp_path = isolated_exports
    _seed_products(tmp_path, [
        {"id": "prod_a", "name": "Product A", "angles": [
            {"angle_id": "a1", "video_url": "04_Exports/Ready_to_post/prod_a_hook1.mp4"},
        ]},
    ])
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    (exports_dir / "totally_unrelated_file.mp4").write_bytes(b"fake mp4")

    result = api_exports.list_exports()
    item = next(i for i in result["exports"] if i["name"] == "totally_unrelated_file.mp4")
    assert item["is_unlinked"] is True
    assert item.get("product_id") is None


# ---------------------------------------------------------------------------
# get_raw_vault() -- scripts/api_videos.py
# ---------------------------------------------------------------------------
def test_raw_vault_matches_by_directory_containment(isolated_exports):
    """A raw file physically living under RAW_DIR/<product_id>/ must be
    grouped under that product (the O(1) dir_owner_by_pid path)."""
    tmp_path = isolated_exports
    _seed_products(tmp_path, [
        {"id": "prod_a", "name": "Product A", "title": "Product A", "videos": []},
        {"id": "prod_b", "name": "Product B", "title": "Product B", "videos": []},
    ])

    raw_dir = tmp_path / "01_Raw"
    (raw_dir / "prod_a").mkdir(parents=True, exist_ok=True)
    (raw_dir / "prod_b").mkdir(parents=True, exist_ok=True)
    (raw_dir / "prod_a" / "clip1.mp4").write_bytes(b"fake")
    (raw_dir / "prod_b" / "clip2.mp4").write_bytes(b"fake")
    (raw_dir / "unassigned_clip.mp4").write_bytes(b"fake")

    result = api_videos.get_raw_vault()
    groups = {g["product_id"]: g for g in result["products"]}

    assert [v["name"] for v in groups["prod_a"]["videos"]] == ["clip1.mp4"]
    assert [v["name"] for v in groups["prod_b"]["videos"]] == ["clip2.mp4"]
    unassigned_names = {v["name"] for v in result["unassigned"]}
    assert unassigned_names == {"unassigned_clip.mp4"}


def test_raw_vault_matches_by_stored_rel_path_reference(isolated_exports):
    """A file NOT physically under RAW_DIR/<pid>/ (e.g. still in the flat
    01_Raw root) but referenced by rel_path in a product's videos[] must
    still be grouped under that product."""
    tmp_path = isolated_exports
    raw_dir = tmp_path / "01_Raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "loose_clip.mp4").write_bytes(b"fake")
    rel_path = "01_Raw/loose_clip.mp4"

    _seed_products(tmp_path, [
        {"id": "prod_a", "name": "Product A", "title": "Product A",
         "videos": [{"rel_path": rel_path, "path": str(raw_dir / "loose_clip.mp4")}]},
    ])

    result = api_videos.get_raw_vault()
    groups = {g["product_id"]: g for g in result["products"]}
    assert [v["name"] for v in groups["prod_a"]["videos"]] == ["loose_clip.mp4"]
    assert result["unassigned"] == []


def test_raw_vault_file_can_match_multiple_products_like_before(isolated_exports):
    """The original code had no `break` after a match -- a file could be
    appended into more than one product's group (e.g. dir-membership under
    prod_a PLUS a stale videos[] reference from prod_b). The rewrite must
    keep that multi-match behavior rather than 'fixing' it into a single
    winner, since that would be an undocumented behavior change."""
    tmp_path = isolated_exports
    raw_dir = tmp_path / "01_Raw"
    (raw_dir / "prod_a").mkdir(parents=True, exist_ok=True)
    clip_path = raw_dir / "prod_a" / "clip1.mp4"
    clip_path.write_bytes(b"fake")

    _seed_products(tmp_path, [
        {"id": "prod_a", "name": "Product A", "title": "Product A", "videos": []},
        # prod_b has a stale reference pointing at prod_a's physical file.
        {"id": "prod_b", "name": "Product B", "title": "Product B",
         "videos": [{"path": str(clip_path), "rel_path": "01_Raw/prod_a/clip1.mp4"}]},
    ])

    result = api_videos.get_raw_vault()
    groups = {g["product_id"]: g for g in result["products"]}
    assert [v["name"] for v in groups["prod_a"]["videos"]] == ["clip1.mp4"]
    assert [v["name"] for v in groups["prod_b"]["videos"]] == ["clip1.mp4"], (
        "a file referenced by one product's stale videos[] AND physically "
        "inside another product's dir must still appear in BOTH groups, "
        "matching the pre-rewrite no-break behavior"
    )
