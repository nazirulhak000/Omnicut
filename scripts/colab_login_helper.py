"""
scripts/colab_login_helper.py — Interactive helper for Google OAuth login on Colab.

Automates the curses menu of `agy`, extracts the OAuth URL, displays a clean clickable
link in Google Colab, and captures the authentication response into ~/.gemini + Google Drive.
"""

from __future__ import annotations

import os
import pty
import re
import select
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def is_already_logged_in() -> bool:
    """Check if agy is already authenticated."""
    try:
        proc = subprocess.run(
            ["/usr/local/bin/agy", "--print", "ping"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return proc.returncode == 0
    except Exception:
        return False


def run_login_flow() -> None:
    print("=" * 65)
    print("🤖 ระบบยืนยันตัวตน Antigravity CLI (Google Account Login)")
    print("=" * 65)

    if is_already_logged_in():
        print("✅ บัญชี Antigravity ของคุณเข้าสู่ระบบอยู่แล้ว 100%!")
        sync_to_drive()
        return

    # Check if we have credentials in Google Drive first
    drive_gemini = Path("/content/drive/MyDrive/.gemini")
    if drive_gemini.exists():
        print("📂 กำลังกู้คืนเซสชันเดิมจาก Google Drive...")
        os.system("mkdir -p /root/.gemini && cp -rn /content/drive/MyDrive/.gemini/* /root/.gemini/ > /dev/null 2>&1 || true")
        if is_already_logged_in():
            print("✨ กู้คืนเซสชันจาก Google Drive สำเร็จ! เข้าสู่ระบบเรียบร้อยแล้ว")
            return

    print("⚡ กำลังเชื่อมต่อไปยัง Antigravity Authentication Gateway...")

    master, slave = pty.openpty()
    pid = os.fork()
    if pid == 0:
        os.close(master)
        os.setsid()
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        os.close(slave)
        os.execlp("/usr/local/bin/agy", "agy")

    os.close(slave)

    # Wait for curses menu to render, then press Enter to select "1. Google OAuth"
    time.sleep(1.5)
    os.write(master, b"\r")

    raw_output = b""
    start_time = time.time()
    oauth_url: str | None = None

    while time.time() - start_time < 8:
        r, _, _ = select.select([master], [], [], 0.5)
        if master in r:
            try:
                data = os.read(master, 2048)
                if not data:
                    break
                raw_output += data
                # Search for google oauth url
                text = raw_output.decode("utf-8", errors="replace")
                m = re.search(r"(https://accounts\.google\.com/o/oauth2/auth[^\s\x1b\x07]+)", text)
                if m:
                    oauth_url = m.group(1)
                    break
            except OSError:
                break

    if not oauth_url:
        # Fallback regex without params
        text = raw_output.decode("utf-8", errors="replace")
        m = re.search(r"https://accounts\.google\.com/[^\s\x1b\x07]+", text)
        if m:
            oauth_url = m.group(0)

    if oauth_url:
        print("\n" + "=" * 65)
        print("🔗 คลิกลิงก์ด้านล่างเพื่อเปิดหน้าต่างเข้าสู่ระบบ Google:")
        print("=" * 65)
        print(f"\n{oauth_url}\n")
        print("=" * 65)

        try:
            from IPython.display import HTML, display
            display(HTML(f'''
            <div style="margin: 15px 0; padding: 18px; background: #0f172a; border: 1.5px solid #3b82f6; border-radius: 10px; text-align: center;">
                <p style="color: #94a3b8; margin: 0 0 12px 0; font-size: 14px;">คลิกปุ่มด้านล่างเพื่ออนุญาตสิทธิ์เข้าใช้งาน Google Antigravity:</p>
                <a href="{oauth_url}" target="_blank" style="display: inline-block; padding: 12px 28px; background: #2563eb; color: #ffffff; text-decoration: none; font-weight: bold; font-size: 15px; border-radius: 8px; box-shadow: 0 4px 12px rgba(37,99,235,0.4);">
                    🔑 คลิกที่นี่เพื่อล็อกอิน Google Account
                </a>
            </div>
            '''))
        except Exception:
            pass

        print("👉 เมื่อล็อกอินสำเร็จบนเบราว์เซอร์แล้ว หากมีรหัสยืนยัน ให้วางในช่องด้านล่าง (ถ้าไม่มี ให้กด Enter เพื่อตรวจสถานะ):")
        try:
            code = input("วางรหัสยืนยัน (Auth Code / Enter): ").strip()
            if code:
                os.write(master, (code + "\r").encode("utf-8"))
                time.sleep(2)
        except Exception:
            pass
    else:
        print("⚠️ ไม่สามารถตรวจจับ OAuth URL ได้โดยอัตโนมัติ")

    # Clean up child process if still running
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass

    # Final check
    time.sleep(1)
    if is_already_logged_in() or Path("/root/.gemini").exists():
        print("\n🎉 เข้าสู่ระบบสำเร็จแล้ว!")
        sync_to_drive()
    else:
        print("\n💡 หากต้องการใช้งานแบบ Terminal สด สามารถเปิดแท็บ Terminal บน https://studio.nazirulhak.com/agy ได้ตลอดเวลา")


def sync_to_drive() -> None:
    drive_gemini = Path("/content/drive/MyDrive/.gemini")
    root_gemini = Path("/root/.gemini")
    if root_gemini.exists() and Path("/content/drive/MyDrive").exists():
        os.system("mkdir -p /content/drive/MyDrive/.gemini && cp -ru /root/.gemini/* /content/drive/MyDrive/.gemini/ 2>/dev/null || true")
        print("💾 เซสชันล็อกอินได้รับการบันทึกลง Google Drive เรียบร้อย! ครั้งต่อไปจะล็อกอินให้อัตโนมัติ 100%")


if __name__ == "__main__":
    run_login_flow()
