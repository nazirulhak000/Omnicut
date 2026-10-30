"""
Generator script to build Omnicut_Cloud_Runner.ipynb

One-click Colab runner for OmniCut Pro Studio + AGY web terminal, designed to be
used from a phone through a Cloudflare tunnel:

- No secret literal lives in this file or in the generated notebook. The
  Cloudflare tunnel token and the app password come from Colab Secrets,
  the environment, or files under ``/content/drive/MyDrive/Omnicut/.secrets``.
- The app password (``OMNICUT_APP_PASSWORD``) and session secret
  (``OMNICUT_SESSION_SECRET``) are generated once and persisted when missing.
- ttyd binds loopback only and runs ``agy`` inside tmux (sessions survive
  reconnects); it is reached through the FastAPI ``/api/agy`` proxy.
- FastAPI, ttyd and cloudflared are supervised by a background thread, so
  Cell 1 finishes and Cell 2 (AGY login) can run.

Usage:  python scripts/build_colab_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_OUT_PATH = Path(__file__).resolve().parent.parent / "Omnicut_Cloud_Runner.ipynb"


def make_markdown_cell(source_lines):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source_lines],
    }


def make_code_cell(source_lines, collapsed=False):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"cellView": "form"} if collapsed else {},
        "outputs": [],
        "source": [line + "\n" for line in source_lines],
    }


def _lines(block: str) -> list[str]:
    return block.strip("\n").splitlines()


# ==========================================================================
# Cell 1: Master One-Click Runner (finishes; supervisor runs in a thread)
# ==========================================================================
CELL_MASTER_RUNNER = r'''
# @title 🚀 คลิกปุ่มนี้ปุ่มเดียว: เปิดระบบ OmniCut Pro Studio + AGY Cloud Terminal { vertical-output: true }
# @markdown **Cloudflare Tunnel Token** — แนะนำให้เว้นว่าง แล้วตั้งใน Colab Secrets (รูปแม่กุญแจ 🔑) ชื่อ `CLOUDFLARE_TUNNEL_TOKEN` แทน
# @markdown ⚠️ ถ้าวาง token ในช่องนี้ ห้ามเซฟ notebook ขึ้น GitHub เด็ดขาด
CLOUDFLARE_TUNNEL_TOKEN = ""  # @param {type:"string"}
# @markdown โดเมนถาวรของ Named Tunnel (ใช้แสดงลิงก์เท่านั้น)
PUBLIC_HOSTNAME = "https://studio.nazirulhak.com"  # @param {type:"string"}
# @markdown เชื่อม Google Drive เพื่อจำรหัสเข้าแอป / token / เซสชัน AGY ถาวร (ปฏิเสธได้ ระบบยังทำงานต่อ)
MOUNT_GOOGLE_DRIVE = True  # @param {type:"boolean"}
# @markdown ถ้ามีไฟล์แก้ค้างบนเครื่อง Colab: ติ๊กเพื่อเก็บเข้า `git stash` (กู้คืนได้) แล้วอัปเดตโค้ด · ไม่ติ๊ก = ข้ามการอัปเดต
AUTO_STASH_LOCAL_CHANGES = False  # @param {type:"boolean"}

import os
import sys
import time
import shlex
import shutil
import socket
import secrets
import datetime
import re
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

IS_COLAB = 'google.colab' in sys.modules
REPO_DIR = Path('/content/Omnicut') if IS_COLAB else Path.cwd()
DRIVE_ROOT = Path('/content/drive/MyDrive')
DRIVE_SECRETS_DIR = DRIVE_ROOT / 'Omnicut' / '.secrets'
WATCHDOG_LOG = '/tmp/omnicut_watchdog.log'
print('🚀 [1/6] เริ่มต้นระบบ OmniCut Pro Studio + AGY Cloud Agent...')

# หยุด Supervisor รอบก่อน (กรณีรันเซลล์นี้ซ้ำ) เพื่อไม่ให้มีตัวเฝ้าระวังซ้อนกัน
_prev_supervisor = globals().get('_OMNICUT_SUPERVISOR')
if _prev_supervisor:
    _prev_supervisor['stop'].set()
    _prev_supervisor['thread'].join(timeout=15)
    for _svc in _prev_supervisor.get('services', {}).values():
        _p = _svc.get('proc')
        if _p is not None and _p.poll() is None:
            _p.terminate()
    print('  ♻️ หยุดตัวเฝ้าระวังรอบก่อนแล้ว กำลังเริ่มใหม่...')

# ----------------------------------------------------------------
# 0. เชื่อม Google Drive (ไม่บังคับ)
# ----------------------------------------------------------------
if IS_COLAB and MOUNT_GOOGLE_DRIVE and not DRIVE_ROOT.exists():
    try:
        from google.colab import drive
        print('  📁 ขอสิทธิ์เชื่อม Google Drive (กดอนุญาต หรือปฏิเสธก็ได้)...')
        drive.mount('/content/drive')
    except Exception as exc:
        print(f'  ⚠️ ไม่ได้เชื่อม Google Drive ({type(exc).__name__}) — ระบบทำงานต่อ แต่รหัส/เซสชันจะไม่ถูกจำข้ามเครื่อง')
DRIVE_OK = DRIVE_ROOT.exists()
if DRIVE_OK:
    print('  ✅ เชื่อม Google Drive แล้ว')

# ----------------------------------------------------------------
# 1. ซิงก์โค้ดล่าสุดจาก GitHub (ไม่ทับงานที่แก้ค้างบนเครื่อง)
# ----------------------------------------------------------------
def _git(*args):
    return subprocess.run(['git', '-C', str(REPO_DIR), *args], capture_output=True, text=True)

if IS_COLAB:
    if not REPO_DIR.exists():
        print('  📂 กำลังโคลนโค้ด OmniCut จาก GitHub...')
        os.system(f'git clone -q https://github.com/nazirulhak000/Omnicut.git {REPO_DIR}')
    else:
        print('  🔄 ตรวจสอบโค้ดล่าสุดจาก GitHub (git fetch)...')
        # products_seed.json ถูกสร้างใหม่ทุกรอบโดย sync_scripts_to_products.py — คืนค่าก่อนตรวจไฟล์ค้าง
        _git('checkout', '--', '_Docs/products_seed.json')
        _fetch = _git('fetch', '-q', 'origin', 'main')
        _dirty = [l for l in _git('status', '--porcelain', '--untracked-files=no').stdout.splitlines() if l.strip()]
        if _fetch.returncode == 0 and _dirty and AUTO_STASH_LOCAL_CHANGES:
            _stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            _stash = _git('stash', 'push', '-m', f'omnicut-colab-autostash-{_stamp}')
            if _stash.returncode == 0:
                print(f'  📦 เก็บไฟล์ที่แก้ค้าง {len(_dirty)} ไฟล์เข้า git stash แล้ว (กู้คืน: git stash list / git stash pop)')
                _dirty = [l for l in _git('status', '--porcelain', '--untracked-files=no').stdout.splitlines() if l.strip()]
        if _fetch.returncode != 0:
            print('  ⚠️ git fetch ไม่สำเร็จ — ใช้โค้ดเดิมบนเครื่องไปก่อน')
        elif _dirty:
            print('  ⚠️ พบไฟล์ที่ถูกแก้ไขค้างบนเครื่อง Colab — ข้ามการอัปเดตเพื่อไม่ให้งานหาย:')
            for _line in _dirty[:15]:
                print('     ' + _line)
            print('  👉 ถ้าต้องการอัปเดต: สำรอง/commit ไฟล์เหล่านี้ก่อน (หรือ git stash) แล้วรันเซลล์นี้ใหม่')
        else:
            _reset = _git('reset', '-q', '--hard', 'origin/main')
            if _reset.returncode == 0:
                print('  ✅ อัปเดตโค้ดเป็น origin/main ล่าสุดแล้ว')
            else:
                print('  ⚠️ อัปเดตโค้ดไม่สำเร็จ — ใช้โค้ดเดิมบนเครื่องไปก่อน')
    (REPO_DIR / 'scripts' / '__init__.py').touch()
    if str(REPO_DIR) not in sys.path:
        sys.path.insert(0, str(REPO_DIR))
    if '/content' not in sys.path:
        sys.path.insert(0, '/content')
    sync_tool = REPO_DIR / 'tools' / 'sync_scripts_to_products.py'
    if sync_tool.exists():
        print('  ✨ ซิงก์ฐานข้อมูลและสคริปต์ 180 บทเข้าสู่ระบบ...')
        os.system(f'cd "{REPO_DIR}" && {sys.executable} "{sync_tool}"')

# ----------------------------------------------------------------
# 2. ตรวจสอบ System Packages, Python Dependencies & AGY CLI
# ----------------------------------------------------------------
print('\n📦 [2/6] ตรวจสอบความพร้อมของแพ็กเกจระบบและ AGY Cloud Agent...')
if IS_COLAB:
    req_file = REPO_DIR / 'requirements.txt'
    if req_file.exists():
        os.system(f'{sys.executable} -m pip install -q -r "{req_file}" aiofiles')
    else:
        os.system(f'{sys.executable} -m pip install -q fastapi "uvicorn[standard]" python-multipart aiofiles pythainlp soundfile faster-whisper')

    # ติดตั้ง google-antigravity SDK (ถ้าแพลตฟอร์มรองรับ)
    os.system(f'{sys.executable} -m pip install -q google-antigravity > /dev/null 2>&1 || true')

    # ติดตั้ง cloudflared ถ้ายังไม่มี
    cf_bin = Path('/usr/local/bin/cloudflared')
    if not cf_bin.exists():
        print('  ⚡ ติดตั้ง Cloudflare Tunnel binary...')
        os.system('curl -sSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared')

    # ติดตั้ง ttyd Interactive Web Terminal binary
    ttyd_bin = Path('/usr/local/bin/ttyd')
    if not ttyd_bin.exists():
        print('  🖥️ ติดตั้ง ttyd Interactive Web Terminal binary...')
        os.system('curl -sSL https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64 -o /usr/local/bin/ttyd && chmod +x /usr/local/bin/ttyd')

    # ติดตั้ง tmux (ให้เซสชัน AGY อยู่รอดเมื่อมือถือหลุดแล้วต่อใหม่)
    if shutil.which('tmux') is None:
        print('  🧵 ติดตั้ง tmux...')
        os.system('apt-get install -y -qq tmux > /tmp/tmux_install.log 2>&1 || (apt-get update -qq > /dev/null 2>&1 && apt-get install -y -qq tmux >> /tmp/tmux_install.log 2>&1)')

    # กู้คืนเซสชันล็อกอิน Antigravity (~/.gemini) จาก Google Drive ถาวร
    drive_gemini = Path('/content/drive/MyDrive/.gemini')
    if drive_gemini.exists():
        print('  ✨ กู้คืนเซสชันล็อกอิน Antigravity จาก Google Drive สำเร็จ!')
        os.system('mkdir -p /root/.gemini && cp -rn /content/drive/MyDrive/.gemini/* /root/.gemini/ > /dev/null 2>&1 || true')

    # ติดตั้ง Official Google Antigravity CLI (agy) Native Binary
    official_agy = Path('/root/.local/bin/agy')
    if not official_agy.exists():
        print('  🤖 ติดตั้ง Official Google Antigravity CLI (agy) Native Binary...')
        os.system('curl -fsSL https://antigravity.google/cli/install.sh | bash > /tmp/agy_install.log 2>&1 || true')

    if official_agy.exists():
        os.system('ln -sf /root/.local/bin/agy /usr/local/bin/agy && chmod +x /usr/local/bin/agy')
        print('  ✅ ติดตั้ง Official Google Antigravity CLI สำเร็จ (พร้อมล็อกอินผ่าน Google Account)!')
    else:
        agy_bin = Path('/usr/local/bin/agy')
        agy_bin.write_text(f'#!/bin/bash\ncd "{REPO_DIR}" && {sys.executable} "{REPO_DIR}/scripts/colab_agy_cli.py" "$@"\n', encoding='utf-8')
        os.system('chmod +x /usr/local/bin/agy')
        print('  ⚡ ใช้ AGY Cloud Agent Python CLI สำรองเรียบร้อย!')
print('  ✅ Dependencies & AGY CLI พร้อมทำงาน 100%')

# ----------------------------------------------------------------
# 3. โหลดและตั้งค่า Gemini API Keys (Colab Secrets / Drive / .env)
# ----------------------------------------------------------------
print('\n🔑 [3/6] ตั้งค่า Gemini API Keys (Colab Secrets / Drive / .env)...')
active_keys = []
try:
    from google.colab import userdata
    for secret_name in ['GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3', 'GOOGLE_API_KEY']:
        try:
            uk = userdata.get(secret_name)
            if uk and uk.strip() and uk.strip() != '-' and len(uk.strip()) >= 10 and uk.strip() not in active_keys:
                active_keys.append(uk.strip())
        except Exception:
            pass
    if active_keys:
        print(f'  ✨ ดึงคีย์จาก Google Colab Secrets (รูปแม่กุญแจ 🔑) สำเร็จ ({len(active_keys)} คีย์)')
except Exception:
    pass

# ตรวจสอบไฟล์ .env บน Google Drive หรือในโฟลเดอร์โปรเจกต์
drive_env = Path('/content/drive/MyDrive/Omnicut/.env')
if drive_env.exists() and not active_keys:
    for line in drive_env.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('GEMINI_API_KEY') or line.startswith('GOOGLE_API_KEY'):
            if '=' in line:
                v = line.split('=', 1)[1].strip().strip('"').strip("'")
                if v and v != '-' and len(v) >= 10 and v not in active_keys:
                    active_keys.append(v)
    if active_keys:
        print(f'  ✨ โหลดคีย์จาก Google Drive ({drive_env}) สำเร็จ ({len(active_keys)} คีย์)')

colab_env = REPO_DIR / '.env'
if colab_env.exists() and not active_keys:
    for line in colab_env.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('GEMINI_API_KEY') or line.startswith('GOOGLE_API_KEY'):
            if '=' in line:
                v = line.split('=', 1)[1].strip().strip('"').strip("'")
                if v and v != '-' and len(v) >= 10 and v not in active_keys:
                    active_keys.append(v)

if not active_keys:
    print('  ⚠️ ไม่พบคีย์ใน Colab Secrets หรือ Google Drive!')
    print('  👉 กรุณาเพิ่มคีย์ที่เมนู Secrets (รูปแม่กุญแจ 🔑 ด้านซ้าย) ชื่อ GEMINI_API_KEY')
    try:
        import getpass
        prompted_key = getpass.getpass('🔑 หรือวาง GEMINI_API_KEY ที่นี่ (ซ่อนตัวอักษร): ').strip()
        if prompted_key:
            active_keys.append(prompted_key)
    except Exception:
        pass

# ซิงก์คีย์ลง Environment และไฟล์ .env สำหรับ FastAPI / AGY Cloud Agent
env_lines = []
for i, k in enumerate(active_keys):
    var_name = 'GEMINI_API_KEY' if i == 0 else f'GEMINI_API_KEY_{i+1}'
    os.environ[var_name] = k
    env_lines.append(f'{var_name}={k}')

if env_lines:
    colab_env.write_text('\n'.join(env_lines) + '\n', encoding='utf-8')
    print(f'  ✅ โหลดคีย์พร้อมใช้งาน {len(active_keys)} คีย์ (ซิงก์สู่ .env เรียบร้อย)!')
else:
    print('  ⚠️ ยังไม่มีคีย์ API — ระบบจะรอให้คุณใส่ผ่านเมนู Secrets หรือ Web Terminal')

# ----------------------------------------------------------------
# 4. รหัสเข้าแอป (OMNICUT_APP_PASSWORD) + Session Secret + Tunnel Token
# ----------------------------------------------------------------
print('\n🔐 [4/6] ตั้งค่ารหัสเข้าแอปและ Cloudflare Tunnel Token...')

def _colab_secret(name):
    if not IS_COLAB:
        return ''
    try:
        from google.colab import userdata
        return (userdata.get(name) or '').strip()
    except Exception:
        return ''

def _read_secret_file(path):
    try:
        return path.read_text(encoding='utf-8').strip() if path.exists() else ''
    except Exception:
        return ''

def _save_secret_file(path, value):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value + '\n', encoding='utf-8')
    except Exception:
        return False
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return True

def _resolve_persistent_secret(name, drive_name, local_path, generator):
    """คืน (ค่า, แหล่งที่มา, สร้างใหม่หรือไม่) — Colab Secret > env > Drive > ไฟล์ในเครื่อง > สุ่มใหม่"""
    value = _colab_secret(name)
    if value:
        return value, f'Colab Secrets ({name})', False
    value = os.environ.get(name, '').strip()
    if value:
        return value, f'environment ({name})', False
    drive_file = DRIVE_SECRETS_DIR / drive_name
    if DRIVE_OK:
        value = _read_secret_file(drive_file)
        if value:
            return value, str(drive_file), False
    value = _read_secret_file(local_path)
    if value:
        if DRIVE_OK:
            _save_secret_file(drive_file, value)
        return value, str(local_path), False
    value = generator()
    target = drive_file if DRIVE_OK else local_path
    saved = _save_secret_file(target, value)
    return value, (str(target) if saved else 'หน่วยความจำ (บันทึกไฟล์ไม่สำเร็จ)'), True

def _readable_password():
    alphabet = 'abcdefghjkmnpqrstuvwxyz23456789'
    raw = ''.join(secrets.choice(alphabet) for _ in range(12))
    return '-'.join(raw[i:i + 4] for i in range(0, 12, 4))

APP_PASSWORD, _pw_source, _pw_generated = _resolve_persistent_secret(
    'OMNICUT_APP_PASSWORD', 'app_password', Path('/root/.omnicut_app_password'), _readable_password)
SESSION_SECRET, _ss_source, _ss_generated = _resolve_persistent_secret(
    'OMNICUT_SESSION_SECRET', 'session_secret', Path('/root/.omnicut_session_secret'), lambda: secrets.token_urlsafe(32))

if _pw_generated:
    _box = [
        f'🔐 รหัสเข้าแอปบน iPhone:  {APP_PASSWORD}',
        'เก็บไว้ให้ดี — ระบบแสดงรหัสนี้ครั้งเดียว',
        f'บันทึกไว้ที่: {_pw_source}',
        'ตั้งเองได้ใน Colab Secrets ชื่อ OMNICUT_APP_PASSWORD',
    ]
    print('\n  ' + '╔' + '═' * 66)
    for _row in _box:
        print('  ║ ' + _row)
    print('  ' + '╚' + '═' * 66 + '\n')
else:
    print(f'  ✅ ใช้รหัสเข้าแอปจาก {_pw_source} (ไม่แสดงซ้ำ)')
print('  ✅ Session Secret พร้อมใช้งาน' + (' (สร้างใหม่)' if _ss_generated else ''))

TUNNEL_TOKEN = CLOUDFLARE_TUNNEL_TOKEN.strip()
_tunnel_source = 'ช่องกรอกในฟอร์ม' if TUNNEL_TOKEN else ''
if not TUNNEL_TOKEN:
    TUNNEL_TOKEN = _colab_secret('CLOUDFLARE_TUNNEL_TOKEN')
    _tunnel_source = 'Colab Secrets (CLOUDFLARE_TUNNEL_TOKEN)' if TUNNEL_TOKEN else ''
if not TUNNEL_TOKEN:
    TUNNEL_TOKEN = (os.environ.get('CLOUDFLARE_TUNNEL_TOKEN') or os.environ.get('TUNNEL_TOKEN') or '').strip()
    _tunnel_source = 'environment' if TUNNEL_TOKEN else ''
if not TUNNEL_TOKEN and DRIVE_OK:
    TUNNEL_TOKEN = _read_secret_file(DRIVE_SECRETS_DIR / 'cloudflare_tunnel_token')
    _tunnel_source = str(DRIVE_SECRETS_DIR / 'cloudflare_tunnel_token') if TUNNEL_TOKEN else ''
if TUNNEL_TOKEN:
    print(f'  ✅ พบ Cloudflare Tunnel Token จาก {_tunnel_source}')
else:
    print('  ⚠️ ไม่พบ CLOUDFLARE_TUNNEL_TOKEN — รอบนี้จะใช้ลิงก์ชั่วคราว (trycloudflare) แทนโดเมนถาวร')
    print('  👉 ตั้งถาวร: เมนู 🔑 Secrets ด้านซ้าย → Add new secret ชื่อ CLOUDFLARE_TUNNEL_TOKEN → เปิด Notebook access → รันเซลล์นี้ใหม่')

# ----------------------------------------------------------------
# 5. เปิดบริการ FastAPI (8000) + ttyd/tmux (127.0.0.1:7681) + Cloudflare Tunnel
#    พร้อม Supervisor ใน Background Thread (เซลล์นี้จบได้ เซลล์ล็อกอินถัดไปรันได้)
# ----------------------------------------------------------------
print('\n🎬 [5/6] เปิดเซิร์ฟเวอร์ OmniCut Pro Studio, AGY Terminal และ Cloudflare Tunnel...')
os.system('fuser -k 8000/tcp > /dev/null 2>&1')
os.system('fuser -k 7681/tcp > /dev/null 2>&1')
os.system('pkill -f cloudflared > /dev/null 2>&1')
time.sleep(1)

# token/รหัสไม่ส่งต่อให้ process ที่ไม่จำเป็นต้องรู้
_CHILD_STRIP = ('CLOUDFLARE_TUNNEL_TOKEN', 'TUNNEL_TOKEN', 'OMNICUT_APP_PASSWORD', 'OMNICUT_SESSION_SECRET')
base_env = {k: v for k, v in os.environ.items() if k not in _CHILD_STRIP}
base_env['PYTHONPATH'] = str(REPO_DIR)
api_env = dict(base_env)
api_env['OMNICUT_APP_PASSWORD'] = APP_PASSWORD
api_env['OMNICUT_SESSION_SECRET'] = SESSION_SECRET
term_env = dict(base_env)
tunnel_env = dict(base_env)
if TUNNEL_TOKEN:
    tunnel_env['TUNNEL_TOKEN'] = TUNNEL_TOKEN  # ส่งผ่าน env ไม่โผล่ใน ps/command line

CLOUDFLARED = '/usr/local/bin/cloudflared' if Path('/usr/local/bin/cloudflared').exists() else 'cloudflared'
API_CMD = [sys.executable, '-m', 'uvicorn', 'scripts.api_server:app', '--host', '0.0.0.0', '--port', '8000']
TTYD_CMD = [
    '/usr/local/bin/ttyd', '-W', '-i', 'lo', '-p', '7681',
    '-t', 'fontSize=15', '-t', 'disableLeaveAlert=true',
    'tmux', 'new', '-A', '-s', 'agy', f'cd {shlex.quote(str(REPO_DIR))} && agy',
]
if TUNNEL_TOKEN:
    TUNNEL_CMD = [CLOUDFLARED, 'tunnel', '--no-autoupdate', 'run']
else:
    TUNNEL_CMD = [CLOUDFLARED, 'tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:8000']

def _wlog(msg):
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(WATCHDOG_LOG, 'a', encoding='utf-8') as f:
            f.write(f'[{stamp}] {msg}\n')
    except Exception:
        pass

def _http_alive(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # เซิร์ฟเวอร์ตอบกลับ (เช่น 401/503 จากระบบรหัสผ่าน) = ยังทำงานอยู่
    except Exception:
        return False

def _port_open(port, host='127.0.0.1'):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False

SERVICES = {}

def _register(name, cmd, env, log, health=None):
    SERVICES[name] = {
        'cmd': cmd, 'env': env, 'log': log, 'health': health,
        'proc': None, 'fails': 0, 'restarts': 0, 'next_try': 0.0, 'bad_checks': 0, 'started_at': 0.0,
    }

def _start_service(name):
    svc = SERVICES[name]
    logf = open(svc['log'], 'a', encoding='utf-8')
    try:
        svc['proc'] = subprocess.Popen(
            svc['cmd'], cwd=str(REPO_DIR), env=svc['env'],
            stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        )
    finally:
        logf.close()
    svc['started_at'] = time.time()

def _supervise(stop):
    tick = 0
    while not stop.wait(10):
        tick += 1
        try:
            now = time.time()
            for name, svc in SERVICES.items():
                proc = svc['proc']
                alive = proc is not None and proc.poll() is None
                if alive and svc['health'] is not None and now - svc['started_at'] > 45:
                    if svc['health']():
                        svc['bad_checks'] = 0
                    else:
                        svc['bad_checks'] += 1
                        if svc['bad_checks'] >= 3:
                            _wlog(f'⚠️ {name} ไม่ตอบสนอง 3 ครั้งติด — สั่งรีสตาร์ต')
                            proc.terminate()
                            try:
                                proc.wait(timeout=10)
                            except Exception:
                                proc.kill()
                            alive = False
                if alive:
                    if now - svc['started_at'] > 300:
                        svc['fails'] = 0  # ทำงานนิ่งเกิน 5 นาที รีเซ็ต backoff
                    continue
                if now < svc['next_try']:
                    continue
                code = proc.returncode if proc is not None else None
                svc['fails'] += 1
                svc['restarts'] += 1
                svc['bad_checks'] = 0
                delay = min(300, 5 * 2 ** min(svc['fails'] - 1, 6))
                svc['next_try'] = now + delay
                _wlog(f'⚠️ {name} หยุดทำงาน (exit={code}) — รีสตาร์ตครั้งที่ {svc["restarts"]} (ถ้าล้มอีกจะรอ {delay}s)')
                if name == 'cloudflared' and not TUNNEL_TOKEN:
                    _wlog('   ℹ️ Quick Tunnel รีสตาร์ตแล้วลิงก์ trycloudflare จะเปลี่ยน — ดูลิงก์ใหม่ใน /tmp/cloudflared.log')
                _start_service(name)
            if tick % 30 == 0:
                # สำรองเซสชัน ~/.gemini สู่ Google Drive ทุก 5 นาที
                if Path('/root/.gemini').exists() and DRIVE_ROOT.exists():
                    os.system('mkdir -p /content/drive/MyDrive/.gemini && cp -ru /root/.gemini/* /content/drive/MyDrive/.gemini/ > /dev/null 2>&1 || true')
                states = ', '.join(
                    f'{n}={"ok" if s["proc"] is not None and s["proc"].poll() is None else "down"}(r{s["restarts"]})'
                    for n, s in SERVICES.items()
                )
                _wlog(f'💓 Heartbeat | {states}')
        except Exception as exc:
            _wlog(f'❌ Supervisor error: {type(exc).__name__}: {exc}')

_register('fastapi', API_CMD, api_env, '/tmp/fastapi.log',
          health=lambda: _http_alive('http://127.0.0.1:8000/api/ai/status'))
_ttyd_ready = IS_COLAB and Path('/usr/local/bin/ttyd').exists() and shutil.which('tmux') is not None
if _ttyd_ready:
    _register('ttyd', TTYD_CMD, term_env, '/tmp/ttyd.log')
elif IS_COLAB:
    print('  ⚠️ ไม่พบ ttyd หรือ tmux — ข้าม AGY Web Terminal (ดู /tmp/tmux_install.log)')
_register('cloudflared', TUNNEL_CMD, tunnel_env, '/tmp/cloudflared.log')

for _f in ('/tmp/fastapi.log', '/tmp/ttyd.log', '/tmp/cloudflared.log'):
    try:
        open(_f, 'w').close()
    except Exception:
        pass

_start_service('fastapi')
server_ok = False
for _ in range(60):
    if _http_alive('http://127.0.0.1:8000/api/ai/status', timeout=1):
        server_ok = True
        break
    time.sleep(0.5)
if server_ok:
    print('  ✅ OmniCut FastAPI Server ทำงานบนพอร์ต 8000 สมบูรณ์')
else:
    print('  ⚠️ FastAPI ยังไม่ตอบ — ตรวจสอบบันทึก /tmp/fastapi.log:')
    if os.path.exists('/tmp/fastapi.log'):
        print(open('/tmp/fastapi.log', encoding='utf-8', errors='replace').read()[-800:])

if 'ttyd' in SERVICES:
    _start_service('ttyd')
    for _ in range(20):
        if _port_open(7681):
            break
        time.sleep(0.5)
    if _port_open(7681):
        print('  ✅ AGY Web Terminal (ttyd + tmux) ฟังเฉพาะ 127.0.0.1:7681 — เข้าผ่าน /agy เท่านั้น')
    else:
        print('  ⚠️ ttyd ยังไม่พร้อม — ดู /tmp/ttyd.log')

# ----------------------------------------------------------------
# 6. เชื่อมต่อ Cloudflare Tunnel & แสดงลิงก์
# ----------------------------------------------------------------
print('\n🌐 [6/6] กำลังเชื่อมต่อ Cloudflare Tunnel...')
_start_service('cloudflared')
if TUNNEL_TOKEN:
    print('  ⚡ ใช้ Named Cloudflare Tunnel (ถาวร)...')
    public_url = PUBLIC_HOSTNAME.strip().rstrip('/') or None
else:
    print('  ⚡ ใช้ Instant Quick Tunnel (สร้างลิงก์ชั่วคราว)...')
    public_url = None
    for _ in range(35):
        time.sleep(1)
        content = open('/tmp/cloudflared.log', encoding='utf-8', errors='replace').read()
        match = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', content)
        if match:
            public_url = match.group(0)
            break

_stop = threading.Event()
_thread = threading.Thread(target=_supervise, args=(_stop,), name='omnicut-supervisor', daemon=True)
_thread.start()
_OMNICUT_SUPERVISOR = {'stop': _stop, 'thread': _thread, 'services': SERVICES}
_wlog('🛡️ Supervisor เริ่มทำงาน (fastapi / ttyd / cloudflared)')

if public_url:
    agy_url = f'{public_url.rstrip("/")}/agy'
    from IPython.display import display, HTML
    print('\n' + '=' * 70)
    print('🎉 OmniCut Pro Studio + AGY Cloud Terminal พร้อมใช้งานแล้ว!')
    print(f'👉 ลิงก์สตูดิโอหลัก   : {public_url}')
    print(f'🤖 ลิงก์ AGY Terminal : {agy_url}')
    print('🔐 เข้าแอปด้วยรหัสเข้าแอป (OMNICUT_APP_PASSWORD) ที่ตั้งไว้ด้านบน')
    print('=' * 70 + '\n')
    display(HTML(f"""
    <div style="padding: 24px; background: linear-gradient(135deg, #090d16 0%, #171d31 100%); border-radius: 14px; color: white; font-family: sans-serif; text-align: center; border: 1.5px solid #3b82f6; box-shadow: 0 10px 30px rgba(0,0,0,0.6);">
        <h2 style="margin: 0 0 10px 0; color: #60a5fa; font-size: 24px;">🚀 OmniCut Pro Studio + AGY Cloud Agent (Online)</h2>
        <p style="margin: 0 0 20px 0; color: #94a3b8; font-size: 14px;">สตูดิโอตัดต่อวิดีโอ TikTok 9:16 และคอนโซลสั่งงาน AI อัตโนมัติ (AGY) บน Cloud — เข้าด้วยรหัสเข้าแอป</p>
        <div style="display: flex; gap: 14px; justify-content: center; flex-wrap: wrap;">
            <a href="{public_url}" target="_blank" style="display: inline-block; padding: 14px 30px; background: #2563eb; color: white; text-decoration: none; font-weight: bold; font-size: 15px; border-radius: 8px;">เปิด OmniCut Pro Studio</a>
            <a href="{agy_url}" target="_blank" style="display: inline-block; padding: 14px 30px; background: #0d9488; color: white; text-decoration: none; font-weight: bold; font-size: 15px; border-radius: 8px;">เปิด AGY Cloud Terminal</a>
        </div>
        <div style="margin-top: 16px; font-size: 13px; color: #64748b;">
            Studio: <a href="{public_url}" target="_blank" style="color: #38bdf8;">{public_url}</a> &nbsp;|&nbsp;
            AGY Terminal: <a href="{agy_url}" target="_blank" style="color: #2dd4bf;">{agy_url}</a>
        </div>
    </div>
    """))
else:
    print('⚠️ ไม่สามารถรับ Tunnel URL ได้ กรุณาดูบันทึกที่ /tmp/cloudflared.log')

print('\n🛡️ [Watchdog Active] ระบบเฝ้าระวังทำงานใน Background แล้ว (รีสตาร์ต FastAPI / ttyd / cloudflared อัตโนมัติ)')
print(f'   ดูบันทึก: !tail -n 30 {WATCHDOG_LOG}  ·  เซลล์ถัดไป (ล็อกอิน AGY) รันต่อได้ทันที')
'''

# ==========================================================================
# Cell 2: One-Time Antigravity Account Login & Drive Sync
# ==========================================================================
CELL_AGY_LOGIN = r'''
# @title 🔑 ล็อกอินบัญชี Antigravity สำหรับ AGY CLI (ทำครั้งเดียว จำถาวรลง Google Drive) { vertical-output: true }
# @markdown รันเซลล์นี้เพื่อล็อกอินบัญชี Google เข้ากับ AGY CLI โดยตรง (จะมีปุ่มคลิกล็อกอินขึ้นมาให้กด)
import sys, os
from pathlib import Path
REPO_DIR = Path('/content/Omnicut') if Path('/content/Omnicut').exists() else Path.cwd()
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
from scripts.colab_login_helper import run_login_flow
run_login_flow()
'''

# ==========================================================================
# Cell 3: Optional foreground keepalive / status view
# ==========================================================================
CELL_KEEPALIVE = r'''
# @title 🛡️ (ไม่บังคับ) Keepalive — แสดงสถานะบริการทุก 5 นาที { vertical-output: true }
# @markdown บริการทั้งหมดถูกเฝ้าระวังใน Background อยู่แล้ว เซลล์นี้ช่วยให้ Colab เห็นว่ามีงานรันอยู่ · กดหยุดได้ทุกเมื่อ บริการไม่ดับ
import time, datetime
_sup = globals().get('_OMNICUT_SUPERVISOR')
if not _sup:
    print('⚠️ ยังไม่ได้รันเซลล์ 🚀 ด้านบน')
else:
    try:
        while _sup['thread'].is_alive():
            _now = datetime.datetime.now().strftime('%H:%M:%S')
            _states = ', '.join(
                f'{n}={"ok" if s["proc"] is not None and s["proc"].poll() is None else "down"}'
                for n, s in _sup['services'].items()
            )
            print(f'💓 [{_now}] {_states}')
            time.sleep(300)
        print('⚠️ Supervisor หยุดทำงาน — รันเซลล์ 🚀 ใหม่')
    except KeyboardInterrupt:
        print('⏹️ หยุด Keepalive แล้ว (บริการยังทำงานต่อใน Background)')
'''


def build_notebook() -> dict:
    cells = []

    # Cell 0: Header Banner
    cells.append(make_markdown_cell([
        "# 🚀 OmniCut Pro Studio + AGY Cloud Agent — Master Cloud Runner",
        "### ระบบผลิตและตัดต่อคลิปวิดีโอ AI อัตโนมัติ พร้อม AGY Interactive Web Terminal (FastAPI + React SPA + HyperFrames + Gemini Flash TTS)",
        "",
        "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nazirulhak000/Omnicut/blob/main/Omnicut_Cloud_Runner.ipynb)",
        "",
        "> ⚡ **วิธีเปิดใช้งาน:** กดปุ่ม **▶ (Play)** ที่เซลล์ 🚀 ด้านล่าง ระบบจะติดตั้ง ซิงก์โค้ด ตั้งค่าคีย์ เปิดหน้าเว็บสตูดิโอ และเปิด **AGY Cloud Terminal (`/agy`)** ให้ พร้อมตัวเฝ้าระวัง (Watchdog) ใน Background — เซลล์จบเองแล้วรันเซลล์ล็อกอินต่อได้ทันที",
        "",
        "> 🔐 **ตั้งค่าใน Colab Secrets (รูปแม่กุญแจ 🔑 ด้านซ้าย) — เปิด Notebook access ทุกตัว:**",
        "> - `CLOUDFLARE_TUNNEL_TOKEN` — token ของ Named Tunnel (studio.nazirulhak.com) · ไม่ตั้ง = ใช้ลิงก์ชั่วคราว trycloudflare",
        "> - `OMNICUT_APP_PASSWORD` — รหัสเข้าแอปบน iPhone · ไม่ตั้ง = ระบบสุ่มให้และแสดงครั้งเดียว (จำไว้ใน Google Drive)",
        "> - `GEMINI_API_KEY` (+ `_2`, `_3`) — คีย์ Gemini",
        "> - `OMNICUT_SESSION_SECRET` (ไม่บังคับ) — ไม่ตั้ง = สุ่มและจำไว้ให้อัตโนมัติ",
    ]))

    cells.append(make_code_cell(_lines(CELL_MASTER_RUNNER)))
    cells.append(make_code_cell(_lines(CELL_AGY_LOGIN)))
    cells.append(make_code_cell(_lines(CELL_KEEPALIVE)))

    return {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {
                "name": "Omnicut_Cloud_Runner.ipynb",
                "provenance": [],
                "toc_visible": True,
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
            },
            "language_info": {
                "name": "python",
            },
        },
        "cells": cells,
    }


def generate_notebook(out_path: Path | str | None = None) -> Path:
    notebook_data = build_notebook()
    out = Path(out_path) if out_path is not None else DEFAULT_OUT_PATH
    out.write_text(json.dumps(notebook_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Generated {out.resolve()} successfully! ({len(notebook_data['cells'])} cells)")
    return out


if __name__ == "__main__":
    generate_notebook()
