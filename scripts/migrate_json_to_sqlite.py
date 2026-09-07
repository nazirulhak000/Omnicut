"""
One-time (but idempotent, re-run-safe) migration: import the existing
_Docs/products.json and _Docs/post_log.json into the SQLite store that now
backs ProductStore and PostLog.

Why this script exists even though ProductStore._load()/PostLog._load()
already auto-import a JSON file into SQLite the first time they see it
(scripts/db.py: DocumentTable._sync_from_json_if_newer) -- that lazy path
only fires on the next call to .get_all()/.list_posts()/etc from wherever
the app happens to run first. This script does the same import explicitly,
up front, from the command line, so deploying this change has a clear "run
this once" step instead of relying on whichever request happens to touch
the store first.

Guarantees
----------
- Every existing id is preserved exactly as-is (never regenerated) --
  project manifests and export filenames reference these ids.
- Every field on every record is preserved (the row is a JSON blob of the
  exact record on import -- see scripts/db.py's DocumentTable).
- The JSON files on disk are left untouched -- they stay the readable
  backup. This script only ever reads them, it never deletes or moves them.
- Idempotent: running it twice (or a hundred times) in a row imports the
  same rows and reports 0 changes the second time onward, because it only
  imports a JSON file when its mtime is newer than the last import this
  script (or any store call) recorded.
- Safe if the DB already has newer data than the JSON file (e.g. the app
  ran and wrote through ProductStore.add() since the last JSON export) --
  it does not clobber the DB with a stale file; it only imports a file that
  is actually newer than what SQLite last saw.

Usage
-----
    python -m scripts.migrate_json_to_sqlite
    python -m scripts.migrate_json_to_sqlite --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys

from scripts import post_log as post_log_mod
from scripts import product_store as product_store_mod
from scripts.post_log import LOG_PATH, PostLog
from scripts.product_store import STORE_PATH, ProductStore


def _count_in_json(path) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return len(data) if isinstance(data, list) else 0


def _ids_in_json(path) -> set:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(data, list):
        return set()
    return {str(r["id"]) for r in data if isinstance(r, dict) and "id" in r}


def migrate(dry_run: bool = False) -> int:
    """Returns 0 on success, 1 if a losslessness check failed."""
    print(f"products.json : {STORE_PATH}")
    print(f"post_log.json : {LOG_PATH}")

    before_products = _count_in_json(STORE_PATH)
    before_posts = _count_in_json(LOG_PATH)
    product_ids_before = _ids_in_json(STORE_PATH)
    post_ids_before = _ids_in_json(LOG_PATH)

    print(f"\nFound {before_products} product(s) in products.json")
    print(f"Found {before_posts} post(s) in post_log.json")

    if dry_run:
        print("\n--dry-run: not importing. Re-run without --dry-run to actually migrate.")
        return 0

    # ProductStore._load() / PostLog._load() trigger DocumentTable's
    # import-if-newer logic -- this is the same path the app itself uses,
    # just invoked explicitly and up front rather than lazily.
    products_after = ProductStore._load()
    posts_after = PostLog._load()

    product_ids_after = {str(p["id"]) for p in products_after}
    post_ids_after = {str(p["id"]) for p in posts_after}

    ok = True

    missing_products = product_ids_before - product_ids_after
    if missing_products:
        print(f"\n[ERROR] {len(missing_products)} product id(s) present in the JSON file "
              f"but missing from SQLite after import: {sorted(missing_products)[:10]}")
        ok = False

    missing_posts = post_ids_before - post_ids_after
    if missing_posts:
        print(f"\n[ERROR] {len(missing_posts)} post id(s) present in the JSON file "
              f"but missing from SQLite after import: {sorted(missing_posts)[:10]}")
        ok = False

    print(f"\nSQLite now has {len(products_after)} product(s), {len(posts_after)} post(s).")

    if ok:
        print("\nMigration OK -- every existing id from both JSON files is present in SQLite, "
              "with its original id preserved. The JSON files on disk are untouched.")
        return 0
    else:
        print("\nMigration completed with losslessness check FAILURES -- see [ERROR] lines above.")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only report counts, do not import.")
    args = parser.parse_args()
    sys.exit(migrate(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
