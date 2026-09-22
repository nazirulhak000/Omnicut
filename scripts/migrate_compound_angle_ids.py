"""
Database Migration Script: Enforces Compound Unique Angle IDs across all products.
Ensures no product has duplicate angle_ids across batches (e.g. pain_point in Batch 2 becomes pain_point_b2).
Also updates associated project.json manifests, ExportRegistry entries, and ShotListsStore records.
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from scripts.product_store import ProductStore, BASE_DIR
from scripts.config import PROJECTS_DIR
from scripts.export_registry import ExportRegistry
from scripts.shot_lists_store import ShotListsStore, _TABLE as SHOT_LISTS_TABLE


def migrate_all_products() -> Dict[str, Any]:
    print("🚀 [Migration] Starting Compound Angle ID Migration...")
    products = ProductStore.get_all()
    total_migrated_angles = 0
    migrated_products = []

    # Map of (product_id, old_angle_id, batch) -> new_angle_id
    id_mapping: Dict[tuple, str] = {}

    for p in products:
        pid = p.get("id")
        pname = p.get("name") or p.get("title") or "Unknown"
        angles = p.get("angles", [])
        if not angles:
            continue

        changed = False
        seen_aids = set()
        new_angles = []

        for angle in angles:
            a_copy = dict(angle)
            aid = str(a_copy.get("angle_id") or a_copy.get("id") or "").strip()
            batch = a_copy.get("batch") or 1

            new_aid = aid
            # If batch > 1 and doesn't already have _b{batch} suffix
            if batch > 1:
                batch_suffix = f"_b{batch}"
                if not aid.endswith(batch_suffix):
                    new_aid = f"{aid}{batch_suffix}"
            
            # Disambiguate if still duplicate in seen_aids
            if new_aid in seen_aids:
                counter = 1
                candidate = f"{new_aid}_{counter}"
                while candidate in seen_aids:
                    counter += 1
                    candidate = f"{new_aid}_{counter}"
                new_aid = candidate

            seen_aids.add(new_aid)

            if new_aid != aid:
                print(f"  ⚡ [{pname[:25]}] Angle Migrated: '{aid}' (batch {batch}) -> '{new_aid}'")
                id_mapping[(pid, aid, batch)] = new_aid
                a_copy["angle_id"] = new_aid
                changed = True
                total_migrated_angles += 1

            new_angles.append(a_copy)

        if changed:
            ProductStore.update(pid, angles=new_angles)
            migrated_products.append(pid)

    print(f"\n✅ [Migration] Products Migration complete: {len(migrated_products)} product(s) modified, {total_migrated_angles} angle(s) updated.")

    # 2. Update project.json manifests
    updated_manifests = 0
    if PROJECTS_DIR.exists() and id_mapping:
        for p_dir in PROJECTS_DIR.iterdir():
            if not p_dir.is_dir():
                continue
            manifest_file = p_dir / "project.json"
            if not manifest_file.exists():
                continue
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                rp = data.get("render_params", {}) or {}
                pid = rp.get("product_id") or data.get("product_id")
                aid = rp.get("angle_id") or data.get("angle_id")
                batch = rp.get("batch") or data.get("batch")
                if batch is None:
                    from scripts.product_store import _extract_batch_from_name
                    batch = _extract_batch_from_name(p_dir.name) or 1

                if (pid, aid, batch) in id_mapping:
                    new_aid = id_mapping[(pid, aid, batch)]
                    if "angle_id" in data:
                        data["angle_id"] = new_aid
                    if "render_params" in data and isinstance(data["render_params"], dict):
                        data["render_params"]["angle_id"] = new_aid
                    manifest_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    updated_manifests += 1
                    print(f"  📝 Updated manifest for project: {p_dir.name} -> angle_id: {new_aid}")
            except Exception as e:
                print(f"  ⚠️ Warning reading {manifest_file}: {e}")

    print(f"✅ [Migration] Project manifests updated: {updated_manifests} file(s).")

    # 3. Update ExportRegistry
    updated_exports = 0
    if id_mapping:
        try:
            with ExportRegistry._mutate() as records:
                for row in records:
                    pid = row.get("product_id")
                    aid = row.get("angle_id")
                    batch = row.get("batch")
                    if batch is None:
                        from scripts.product_store import _extract_batch_from_name
                        batch = _extract_batch_from_name(row.get("project_name")) or _extract_batch_from_name(row.get("path")) or 1
                    if (pid, aid, batch) in id_mapping:
                        row["angle_id"] = id_mapping[(pid, aid, batch)]
                        updated_exports += 1
            print(f"✅ [Migration] ExportRegistry updated: {updated_exports} record(s).")
        except Exception as e:
            print(f"  ⚠️ Warning updating ExportRegistry: {e}")

    # 4. Update ShotListsStore
    updated_shots = 0
    if id_mapping:
        try:
            with SHOT_LISTS_TABLE.mutate() as records:
                for rec in records:
                    pid = rec.get("product_id")
                    aid = rec.get("angle_id")
                    batch = rec.get("batch") or 1
                    if (pid, aid, batch) in id_mapping:
                        new_aid = id_mapping[(pid, aid, batch)]
                        rec["angle_id"] = new_aid
                        rec["id"] = f"{pid}:{new_aid}:b{batch}"
                        updated_shots += 1
            print(f"✅ [Migration] ShotListsStore updated: {updated_shots} record(s).")
        except Exception as e:
            print(f"  ⚠️ Warning updating ShotListsStore: {e}")

    return {
        "migrated_products": len(migrated_products),
        "total_migrated_angles": total_migrated_angles,
        "updated_manifests": updated_manifests,
        "updated_exports": updated_exports,
        "updated_shots": updated_shots,
    }


if __name__ == "__main__":
    result = migrate_all_products()
    print("\n🎉 Migration Result Summary:", result)
