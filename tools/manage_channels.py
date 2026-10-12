"""CLI Utility to manage multi-channel registry in OmniCut Pro Studio.

Usage:
    # 1. ดูรายการช่องทั้งหมด
    python tools/manage_channels.py list

    # 2. เพิ่มช่องใหม่
    python tools/manage_channels.py add --id tech_th --name "Tech Review TH" --handle @techreviewth --watermark "สงวนลิขสิทธิ์ช่อง Tech Review TH" --avatar "03_Projects/_HyperFrames_Studio/assets/shared/img/channel_avatar.jpg"

    # 3. ยืนยันบัญชี TikTok (สำหรับระบบ Auto-Post)
    python tools/manage_channels.py bind tech_th --handle @techreviewth

    # 4. ซิงก์ข้อมูลช่องเข้าสู่ HyperFrames Studio
    python tools/manage_channels.py sync
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import config
from scripts.channel_store import (
    ChannelError,
    get_default_store,
    STATUS_ACTIVE,
    STATUS_DRAFT,
    STATUS_ARCHIVED,
    BINDING_VERIFIED,
    BINDING_UNVERIFIED,
)


def cmd_list(args: argparse.Namespace) -> int:
    store = get_default_store()
    doc = store.load()
    channels = doc.get("channels", [])

    print("\n" + "=" * 70)
    print("  📺 OmniCut Pro Studio — รายชื่อช่องในระบบ (Multi-Channel)")
    print("=" * 70)

    if not channels:
        print("  (ไม่พบข้อมูลช่องในระบบ)")
        return 0

    for ch in channels:
        status_tag = f"[{ch.get('status', 'draft').upper()}]"
        active_mark = " (ช่องหลัก/Default)" if ch.get("id") == "main" else ""
        binding = ch.get("account_binding", {})
        bind_status = binding.get("status", "unverified")

        print(f"\n* ID: {ch.get('id')}{active_mark}")
        print(f"  ชื่อแสดง (Name):     {ch.get('display_name')}")
        print(f"  TikTok Handle:       {ch.get('handle')}")
        print(f"  สถานะ (Status):       {status_tag}")
        print(f"  ลายน้ำ (Watermark):   {ch.get('watermark_text')}")
        print(f"  คำชวนติดตาม (Follow): {ch.get('follow_title')}")
        print(f"  รูปโปรไฟล์ (Avatar):  {ch.get('avatar_asset_path')}")
        print(f"  Auto-Post TikTok:    {'เปิด (Enabled)' if ch.get('posting_enabled') else 'ปิด (Disabled)'} | Binding: {bind_status}")

    print("\n" + "=" * 70)
    print(f"รวมทั้งหมด: {len(channels)} ช่อง | Registry Revision: {doc.get('revision', 0)}\n")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    store = get_default_store()
    cid = args.id.strip().lower()
    name = args.name.strip()
    handle = args.handle.strip()
    if not handle.startswith("@"):
        handle = "@" + handle

    watermark = args.watermark.strip() if args.watermark else f"สงวนลิขสิทธิ์ช่อง {name} ห้ามคัดลอก/ดัดแปลง"
    follow = args.follow.strip() if args.follow else "กดติดตามด้วยนะ"
    avatar = args.avatar.strip() if args.avatar else "03_Projects/_HyperFrames_Studio/assets/shared/img/channel_avatar.jpg"

    payload = {
        "id": cid,
        "display_name": name,
        "handle": handle,
        "watermark_text": watermark,
        "follow_title": follow,
        "avatar_asset_path": avatar,
        "posting_enabled": args.enable_posting,
    }

    try:
        created = store.create(payload)
        # Activate immediately if requested
        if args.active:
            created = store.activate(cid)

        print("\n" + "=" * 60)
        print(f"  ✅ สร้างช่อง '{cid}' สำเร็จเรียบร้อยแล้ว!")
        print("=" * 60)
        print(f"  ID:           {created.get('id')}")
        print(f"  ชื่อช่อง:     {created.get('display_name')}")
        print(f"  Handle:       {created.get('handle')}")
        print(f"  สถานะ:        {created.get('status')}")
        print(f"  ลายน้ำ:       {created.get('watermark_text')}")
        print("=" * 60)
        print("\n💡 แนะนำ: รัน 'python tools/manage_channels.py sync' เพื่ออัปเดตช่องเข้าสู่ HyperFrames Studio\n")
        return 0
    except ChannelError as e:
        print(f"\n❌ ข้อผิดพลาด: {e.detail} (Code: {e.status_code})\n", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาดไม่คาดคิด: {e}\n", file=sys.stderr)
        return 1


def cmd_bind(args: argparse.Namespace) -> int:
    store = get_default_store()
    cid = args.id.strip().lower()
    handle = args.handle.strip() if args.handle else None

    if not handle:
        ch = store.get(cid)
        handle = ch.get("handle")

    if not handle.startswith("@"):
        handle = "@" + handle

    try:
        updated = store.set_account_binding(
            cid,
            status=BINDING_VERIFIED,
            verified_handle=handle,
        )
        print(f"\n✅ ยืนยันการผูกบัญชี TikTok สำหรับช่อง '{cid}' ด้วย handle '{handle}' สำเร็จ!")
        print(f"   สถานะ Account Binding: verified\n")
        return 0
    except ChannelError as e:
        print(f"\n❌ ข้อผิดพลาด: {e.detail} (Code: {e.status_code})\n", file=sys.stderr)
        return 1


def cmd_sync(args: argparse.Namespace) -> int:
    from tools import sync_channels
    try:
        print("\nกำลังซิงก์ข้อมูลช่องเข้าสู่ HyperFrames Studio...")
        code = sync_channels.sync(
            registry_path=Path(config.CHANNELS_FILE),
            kit_dir=Path(config.HYPERFRAMES_STUDIO_DIR) / "kit",
            project_root=Path(config.BASE_DIR),
            apply=True,
        )
        if code == 0:
            print("✅ ซิงก์ข้อมูลเข้าสู่ HyperFrames Studio เรียบร้อยแล้ว!\n")
            return 0
        else:
            print(f"❌ ซิงก์ไม่สำเร็จ (Exit code: {code})\n", file=sys.stderr)
            return code
    except Exception as e:
        print(f"\n❌ ข้อผิดพลาดขณะซิงก์: {e}\n", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="manage_channels",
        description="OmniCut Pro Studio — เครื่องมือจัดการช่องและบัญชี (Multi-Channel CLI)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # list
    p_list = sub.add_parser("list", help="แสดงรายชื่อช่องทั้งหมด")
    p_list.set_defaults(func=cmd_list)

    # add
    p_add = sub.add_parser("add", help="เพิ่มช่องใหม่")
    p_add.add_argument("--id", required=True, help="รหัสช่อง (ตัวพิมพ์เล็ก เช่น tech_th, rizanntry)")
    p_add.add_argument("--name", required=True, help="ชื่อแสดงของช่อง (Display Name)")
    p_add.add_argument("--handle", required=True, help="TikTok Handle (เช่น @techreviewth)")
    p_add.add_argument("--watermark", default="", help="ข้อความลายน้ำท้ายคลิป")
    p_add.add_argument("--follow", default="", help="ข้อความชวนกดติดตาม (Outro)")
    p_add.add_argument("--avatar", default="", help="Path รูปโปรไฟล์ช่อง")
    p_add.add_argument("--active", action="store_true", default=True, help="เปิดใช้งานทันที (Active)")
    p_add.add_argument("--enable-posting", action="store_true", default=False, help="เปิดใช้งาน TikTok Auto-Post")
    p_add.set_defaults(func=cmd_add)

    # bind
    p_bind = sub.add_parser("bind", help="ผูก/ยืนยันบัญชี TikTok ของช่อง")
    p_bind.add_argument("id", help="รหัสช่อง (เช่น tech_th)")
    p_bind.add_argument("--handle", default="", help="TikTok Handle ที่ยืนยัน (ถ้าเว้นจะใช้ handle ของช่อง)")
    p_bind.set_defaults(func=cmd_bind)

    # sync
    p_sync = sub.add_parser("sync", help="ซิงก์รายชื่อช่องเข้าสู่ HyperFrames Studio")
    p_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
