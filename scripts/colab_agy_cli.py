#!/usr/bin/env python3
"""
scripts/colab_agy_cli.py — Interactive Terminal CLI (`agy`) for Google Colab & Local Terminal.

Can be launched:
- Interactively via `ttyd` Web Terminal on Google Colab (`agy` or `python scripts/colab_agy_cli.py`)
- One-shot via `agy "ตรวจสอบสถานะ GPU"` or `agy --goal "ผลิตคลิป..."`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.agy_cloud_agent import (
    AGYCloudAgent,
    get_system_status,
)

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_RED = "\033[31m"
C_GRAY = "\033[90m"


def print_banner() -> None:
    status = get_system_status(PROJECT_ROOT)
    gpu = status.get("gpu") or {}
    gpu_str = (
        f"{C_GREEN}{gpu.get('name')} ({gpu.get('vram_used_mb')}/{gpu.get('vram_total_mb')} MB){C_RESET}"
        if gpu.get("available")
        else f"{C_YELLOW}CPU Mode{C_RESET}"
    )
    drive_str = (
        f"{C_GREEN}เชื่อมต่อแล้ว ({status.get('drive_export_dir')}){C_RESET}"
        if status.get("drive_mounted")
        else f"{C_GRAY}ไม่ได้เชื่อมต่อ{C_RESET}"
    )

    print(f"{C_CYAN}{C_BOLD}" + "=" * 72 + f"{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}  🚀 AGY (Antigravity Cloud CLI) — OmniCut Pro Studio Terminal{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}" + "=" * 72 + f"{C_RESET}")
    print(f"  📂 Workspace : {status.get('workspace')}")
    print(f"  🧠 Engine    : {status.get('engine')}")
    print(f"  🎮 GPU       : {gpu_str}")
    print(f"  🔑 API Keys  : {C_GREEN}{status.get('api_keys_count')} คีย์พร้อมสลับอัตโนมัติ{C_RESET}")
    print(f"  💾 Drive     : {drive_str}")
    print(f"{C_GRAY}  พิมพ์คำสั่งภาษาไทย/อังกฤษได้เลย | /help ดูคำสั่งพิเศษ | !คำสั่งเชลล์ | /exit ออก{C_RESET}")
    print(f"{C_CYAN}" + "-" * 72 + f"{C_RESET}")


def print_help() -> None:
    print(f"\n{C_BOLD}{C_CYAN}คำสั่งพิเศษของ AGY CLI:{C_RESET}")
    print(f"  {C_GREEN}/help{C_RESET}              แสดงคู่มือคำสั่งนี้")
    print(f"  {C_GREEN}/status{C_RESET}            ตรวจสอบสถานะ GPU, ดิสก์, API Keys และ Google Drive")
    print(f"  {C_GREEN}/goal <เป้าหมาย>{C_RESET}    สั่งโหมด Autonomous ลุยงานต่อเนื่องหลายขั้นตอนจนกว่าจะสำเร็จ")
    print(f"  {C_GREEN}/drive-sync{C_RESET}        ซิงก์ไฟล์วิดีโอ MP4 จาก 04_Exports เข้า Google Drive")
    print(f"  {C_GREEN}/clear{C_RESET}             ล้างประวัติการสนทนาเริ่มเซสชันใหม่")
    print(f"  {C_GREEN}!<คำสั่งเชลล์>{C_RESET}        รันคำสั่ง Linux Bash โดยตรง เช่น !nvidia-smi หรือ !git status")
    print(f"  {C_GREEN}/exit{C_RESET}              ออกจากโปรแกรม\n")


def run_prompt_stream(agent: AGYCloudAgent, prompt: str, session_id: str, goal_mode: bool = False) -> None:
    for ev in agent.stream_chat(message=prompt, session_id=session_id, goal_mode=goal_mode):
        etype = ev.get("type")
        if etype == "thinking":
            print(f"\n{C_GRAY}💭 [Step {ev.get('step', 1)}] {ev.get('text')}{C_RESET}")
        elif etype == "tool_call":
            args_str = json.dumps(ev.get("args") or {}, ensure_ascii=False)
            print(f"{C_YELLOW}🔧 [Tool: {ev.get('tool')}] {args_str}{C_RESET}")
        elif etype == "tool_result":
            res = ev.get("result") or {}
            ok_mark = f"{C_GREEN}✔{C_RESET}" if res.get("ok") else f"{C_RED}✘{C_RESET}"
            preview = res.get("stdout") or res.get("content") or res.get("error") or json.dumps(res, ensure_ascii=False)
            preview_short = str(preview).strip()[:400]
            print(f"   {ok_mark} {C_GRAY}{preview_short}{C_RESET}")
        elif etype == "answer":
            print(f"\n{C_GREEN}{C_BOLD}🤖 AGY ({ev.get('steps', 1)} steps):{C_RESET}\n{ev.get('text')}\n")
        elif etype == "error":
            print(f"\n{C_RED}❌ Error: {ev.get('message')}{C_RESET}\n")


def interactive_loop() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print_banner()
    agent = AGYCloudAgent(workspace=PROJECT_ROOT)
    session_id = "cli-main"

    while True:
        try:
            user_in = input(f"{C_BLUE}{C_BOLD}agy>{C_RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_GRAY}ออกจาก AGY CLI เรียบร้อยครับ{C_RESET}")
            break

        if not user_in:
            continue

        low = user_in.lower()
        if low in ("/exit", "/quit", "exit", "quit"):
            print(f"{C_GRAY}ออกจาก AGY CLI เรียบร้อยครับ{C_RESET}")
            break
        if low == "/help":
            print_help()
            continue
        if low == "/status":
            st = get_system_status(PROJECT_ROOT)
            print(json.dumps(st, indent=2, ensure_ascii=False))
            continue
        if low == "/clear":
            agent.clear_session(session_id)
            print(f"{C_GREEN}✅ ล้างประวัติเซสชันเรียบร้อยแล้ว{C_RESET}")
            continue
        if low == "/drive-sync":
            res = agent.tools.sync_to_drive()
            print(json.dumps(res, indent=2, ensure_ascii=False))
            continue

        run_prompt_stream(agent, user_in, session_id=session_id, goal_mode=low.startswith("/goal "))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AGY Cloud Agent CLI for OmniCut Pro Studio")
    parser.add_argument("prompt", nargs="*", help="คำสั่งที่ต้องการให้ AGY ดำเนินการทันที")
    parser.add_argument("--goal", action="store_true", help="เปิดโหมด Autonomous Goal")
    parser.add_argument("--status", action="store_true", help="แสดงสถานะระบบเป็น JSON แล้วจบการทำงาน")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.status:
        print(json.dumps(get_system_status(PROJECT_ROOT), indent=2, ensure_ascii=False))
        return 0

    if args.prompt:
        prompt_text = " ".join(args.prompt).strip()
        agent = AGYCloudAgent(workspace=PROJECT_ROOT)
        run_prompt_stream(agent, prompt_text, session_id="cli-oneshot", goal_mode=args.goal)
        return 0

    return interactive_loop()


if __name__ == "__main__":
    raise SystemExit(main())
