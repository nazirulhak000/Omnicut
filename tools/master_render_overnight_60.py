"""Master Overnight Batch Render Runner for 60 Couple Paper Chat Clips:
- GOO01: GOOJODOQ Capsule Powerbank (20 clips)
- HAT01: Hatari 16" Table Fan (20 clips)
- RED01: Redmi Buds 8 Active (20 clips)

Uses GPU hardware acceleration (--gpu --browser-gpu + h264_nvenc)
Logs output cleanly to .tmp/master_render_60.log
"""
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / ".tmp" / "master_render_60.log"
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_script(script_path, label):
    log(f"==================================================")
    log(f"🚀 STARTING BATCH: {label}")
    log(f"   Script: {script_path}")
    log(f"==================================================")
    t0 = time.time()
    cmd = [str(PYTHON_EXE), "-u", str(script_path), "--workers", "2"]
    
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    for line in iter(proc.stdout.readline, ''):
        stripped = line.strip()
        if stripped:
            log(f"[{label}] {stripped}")
            
    proc.stdout.close()
    proc.wait()
    
    elapsed = round(time.time() - t0, 1)
    if proc.returncode == 0:
        log(f"✅ BATCH COMPLETED: {label} in {elapsed}s ({elapsed/60:.1f} mins)")
    else:
        log(f"❌ BATCH FAILED: {label} with exit code {proc.returncode} in {elapsed}s")
    return proc.returncode == 0

def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Master Render Log Started at {datetime.now().isoformat()}\n")

    log("🌟 MASTER OVERNIGHT RENDER LAUNCHED (60 CLIPS TOTAL)")
    log("   Hardware: RTX 4060 (NVENC) + 28 vCPU Hybrid")
    
    batches = [
        ("GOO01 (GOOJODOQ 20 clips)", ROOT / "tools" / "batch_render_goojodoq_20.py"),
        ("HAT01 (Hatari 16\" 20 clips)", ROOT / "tools" / "batch_render_hatari16_20.py"),
        ("RED01 (Redmi Buds 8 20 clips)", ROOT / "tools" / "batch_render_redmi_buds8_20.py"),
    ]
    
    total_start = time.time()
    results = {}
    
    for label, script in batches:
        ok = run_script(script, label)
        results[label] = ok
        
    total_time = round(time.time() - total_start, 1)
    log("==================================================")
    log(f"🏁 ALL BATCHES FINISHED in {total_time}s ({total_time/60:.1f} mins)")
    for label, ok in results.items():
        log(f"   {'✅' if ok else '❌'} {label}")
    log("==================================================")

if __name__ == "__main__":
    main()
