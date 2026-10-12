"""ย้ายข้อมูลเดิมเข้าระบบหลายช่อง (multi-channel P2.3) — ค่าเริ่มต้นคือ dry-run (อ่านอย่างเดียว)

ตัวอย่าง (ดูขั้นตอนเต็มใน _Docs/Plans/MIGRATION_RUNBOOK_MULTI_CHANNEL_20261010.md):

    .venv\\Scripts\\python.exe tools/migrate_channels.py --report _Docs/Reports/MIGRATION_DRYRUN
    .venv\\Scripts\\python.exe tools/migrate_channels.py --rehearse-restore <โฟลเดอร์ว่างนอก root>
    .venv\\Scripts\\python.exe tools/migrate_channels.py --apply --expect-plan <plan_hash>
    .venv\\Scripts\\python.exe tools/migrate_channels.py --resume
    .venv\\Scripts\\python.exe tools/migrate_channels.py --rollback
    .venv\\Scripts\\python.exe tools/migrate_channels.py --status

Exit code: 0 สำเร็จ · 1 ผิดพลาด · 2 ถูกบล็อก/ข้อมูลเข้าไม่ถูกต้อง · 3 ข้อมูลเปลี่ยนระหว่างทาง/ตรวจผลไม่ผ่าน
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import config  # noqa: E402
from scripts import channel_migration as cm  # noqa: E402
from scripts import maintenance_lock  # noqa: E402


def _print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:  # Windows consoles (cp874/cp1252)
        sys.stdout.buffer.write((message + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_channels",
        description="Backfill channel_id ให้ข้อมูลเดิม (dry-run เป็นค่าเริ่มต้น; ไม่เขียนอะไรจนกว่าจะสั่ง --apply)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="อ่านอย่างเดียว แสดงแผน (ค่าเริ่มต้น)")
    mode.add_argument("--apply", action="store_true", help="ย้ายข้อมูลจริง (ต้องมี --expect-plan)")
    mode.add_argument("--resume", action="store_true", help="ทำต่อจากรอบที่ค้าง")
    mode.add_argument("--rollback", action="store_true", help="ถอด channel_id ที่ migration เพิ่ม (รักษาข้อมูลใหม่)")
    mode.add_argument("--restore-snapshot", action="store_true", help="คืน snapshot ทั้งชุด (ได้เฉพาะเมื่อยังไม่มีข้อมูลใหม่หลัง apply)")
    mode.add_argument("--rehearse-restore", metavar="WORKDIR", help="ซ้อม backup+restore ลงโฟลเดอร์ว่างนอก root แล้วตรวจ")
    mode.add_argument("--status", action="store_true", help="แสดงสถานะรอบล่าสุดและ maintenance lock")
    mode.add_argument("--release-stale-lock", action="store_true", help="ปลด lock ที่ process เจ้าของตายแล้ว (ไม่ใช่ของรอบที่ค้าง)")
    parser.add_argument("--root", help="root ของข้อมูล (ค่าเริ่มต้น = โฟลเดอร์โปรเจกต์จาก scripts/config.py)")
    parser.add_argument("--report", help="path รายงาน (เขียน <path>.md และ <path>.json)")
    parser.add_argument("--assign", help="ไฟล์ JSON ระบุเจ้าของรายแถว (schema omnicut.channel_assign.v1)")
    parser.add_argument("--expect-plan", help="plan_hash จาก dry-run ที่ตรวจแล้ว (บังคับกับ --apply)")
    parser.add_argument("--rename-templates", action="store_true", help="เปลี่ยน id template default/week:<d> เป็น <channel>:… (เปิดเมื่อโค้ดรองรับแล้วเท่านั้น)")
    parser.add_argument("--legacy-owner", help="เจ้าของข้อมูลเดิมเมื่อ registry มีหลายช่อง (การตัดสินใจของเจ้าของ)")
    parser.add_argument("--skip-server-check", action="store_true", help="ไม่ตรวจว่า API server (127.0.0.1:8000) ยังเปิดอยู่")
    return parser


def _server_probe(root: Path, skip: bool):
    if skip:
        return None
    if os.path.normcase(os.path.abspath(root)) != os.path.normcase(os.path.abspath(config.BASE_DIR)):
        return None  # temp roots are never served by the live API
    return cm.tcp_probe("127.0.0.1", 8000)


def _summary(result: dict) -> List[str]:
    plan = result["plan"]
    lines = [
        f"root: {result['root']}",
        f"plan_hash: {plan['plan_hash']}",
        f"เจ้าของข้อมูลเดิม: {plan['evidence']['legacy_owner']} ({plan['evidence']['legacy_owner_reason_th']})",
        f"แถวที่จะเขียน: {len(plan['actions'])} · มีเจ้าของแล้ว: {plan['already_owned']}",
    ]
    for name, s in plan["stores"].items():
        if s["total"]:
            backfill = ", ".join(f"{k}={v}" for k, v in sorted(s["backfill"].items())) or "0"
            lines.append(
                f"  - {name}: ทั้งหมด {s['total']} · backfill {backfill} · unknown {s['unknown']} · conflict {s['conflict']}"
                f" · deferred {s['deferred']} · unsupported {s['unsupported']} · มีแล้ว {s['already']}"
            )
    blockers = [c for c in result["preflight"]["checks"] if c["level"] == "blocker" and not c["ok"]]
    lines.append(f"preflight blockers: {len(blockers)}")
    for c in blockers:
        lines.append(f"  ! {c['message']}")
    return lines


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root) if args.root else Path(config.BASE_DIR)
    root = Path(os.path.abspath(root))
    if not root.is_dir():
        _print(f"ไม่พบ root: {root}")
        return 2
    migrator = cm.Migrator(root, server_probe=_server_probe(root, args.skip_server_check))
    try:
        assignments = cm.load_assignments(Path(args.assign)) if args.assign else []
        options = dict(assignments=assignments, rename_templates=args.rename_templates, legacy_owner=args.legacy_owner)

        if args.status:
            state = migrator.current_run()
            lock = maintenance_lock.read_lock(root)
            safe_state = {k: state.get(k) for k in ("run_id", "status", "created_at", "applied_at", "rolled_back_at", "error")} if state else None
            safe_lock = {k: lock.get(k) for k in ("owner", "pid", "run_id", "started_at", "stale", "corrupt")} if lock else None
            _print(json.dumps({"run": safe_state, "maintenance_lock": safe_lock}, ensure_ascii=False, indent=2))
            return 0
        if args.release_stale_lock:
            _print(json.dumps(migrator.release_stale_lock(), ensure_ascii=False))
            return 0
        if args.rehearse_restore:
            verdict = cm.rehearse_restore(root, Path(args.rehearse_restore))
            _print(json.dumps(verdict, ensure_ascii=False, indent=2))
            return 0 if verdict["ok"] else 3
        if args.apply:
            if not args.expect_plan:
                _print("--apply ต้องระบุ --expect-plan <plan_hash> จาก dry-run ที่ตรวจรายงานแล้ว")
                return 2
            result = migrator.apply(expect_plan=args.expect_plan, **options)
            _print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.resume:
            _print(json.dumps(migrator.resume(), ensure_ascii=False, indent=2))
            return 0
        if args.rollback:
            _print(json.dumps(migrator.rollback(), ensure_ascii=False, indent=2))
            return 0
        if args.restore_snapshot:
            _print(json.dumps(migrator.restore_snapshot_in_place(), ensure_ascii=False, indent=2))
            return 0

        result = migrator.dry_run(**options)
        for line in _summary(result):
            _print(line)
        if args.report:
            md, js = cm.write_report(result, Path(args.report))
            _print(f"รายงาน: {md}")
            _print(f"รายงาน (JSON): {js}")
        return 0
    except cm.MigrationError as exc:
        _print(f"หยุด: {exc}")
        return exc.exit_code
    except maintenance_lock.MaintenanceLockBusy as exc:
        _print(f"หยุด: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
