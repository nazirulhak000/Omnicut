"""Run N copies of the captured final encode at once; report wall time, CPU, RAM and (NVIDIA only) GPU load."""
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    import psutil
except ImportError:  # not in requirements.txt; fall back to the Win32 counters
    psutil = None

if psutil is None:
    import ctypes
    from ctypes import wintypes

    class _MemStatus(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64)]

    def _cpu_times():
        idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
        as_int = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime  # noqa: E731
        return as_int(idle), as_int(kernel) + as_int(user)  # kernel time already includes idle

    _last = [_cpu_times()]

    def cpu_percent():
        idle, total = _cpu_times()
        idle0, total0 = _last[0]
        _last[0] = (idle, total)
        return 100.0 * (1 - (idle - idle0) / max(1, total - total0))

    def ram_used_gb():
        status = _MemStatus()
        status.dwLength = ctypes.sizeof(status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return (status.ullTotalPhys - status.ullAvailPhys) / 2**30
else:
    def cpu_percent():
        return psutil.cpu_percent(None)

    def ram_used_gb():
        return psutil.virtual_memory().used / 2**30

HERE =Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit"
OUTDIR = HERE / "replay"
OUTDIR.mkdir(parents=True, exist_ok=True)
ARGV = json.loads((HERE / "out" / f"{sys.argv[1]}.encode_argv.json").read_text(encoding="utf-8"))
ARGV = [a for a in ARGV if a not in ("-nostats",)]
if "-progress" in ARGV:
    i = ARGV.index("-progress")
    del ARGV[i:i + 2]
NVIDIA_SMI = shutil.which("nvidia-smi")


def gpu_sample():
    """(VRAM used MiB, GPU util %, encoder util %) or None when there is no NVIDIA card."""
    if not NVIDIA_SMI:
        return None
    try:
        out = subprocess.run(
            [NVIDIA_SMI, "--query-gpu=memory.used,utilization.gpu,utilization.encoder", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5).stdout.strip().splitlines()[0]
        return tuple(float(x) for x in out.split(","))
    except Exception:  # noqa: BLE001
        return None


for n in [int(x) for x in sys.argv[2:]]:
    samples = []
    gpu = []
    stop = threading.Event()

    def sample():
        cpu_percent()
        while not stop.wait(1.0):
            samples.append((cpu_percent(), ram_used_gb()))
            g = gpu_sample()
            if g:
                gpu.append(g)

    t = threading.Thread(target=sample, daemon=True)
    t.start()
    started = time.perf_counter()
    procs = []
    for k in range(n):
        cmd = ARGV[:-1] + [str(OUTDIR / f"par_{n}_{k}.mp4")]
        log = open(OUTDIR / f"par_{n}_{k}.stderr.txt", "wb")
        procs.append((time.perf_counter(), subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log)))
        log.close()
    each = []
    for k, (s, p) in enumerate(procs):
        p.wait()
        each.append(round(time.perf_counter() - s, 1))
        if p.returncode:
            tail = (OUTDIR / f"par_{n}_{k}.stderr.txt").read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-3:]
            print(f"  job {k} failed rc={p.returncode}: {' | '.join(tail)}", flush=True)
    wall = time.perf_counter() - started
    stop.set()
    cpu = sorted(c for c, _ in samples)
    mem = [m for _, m in samples]
    gpu_text = ""
    if gpu:
        gpu_text = (f" vram_max={max(g[0] for g in gpu):.0f}MiB gpu_avg={sum(g[1] for g in gpu) / len(gpu):.0f}%"
                    f" enc_avg={sum(g[2] for g in gpu) / len(gpu):.0f}% enc_max={max(g[2] for g in gpu):.0f}%")
    print(f"workers={n} wall={wall:.1f}s per-job={each} clips/min={n / wall * 60:.2f} "
          f"cpu_avg={sum(cpu) / max(1, len(cpu)):.0f}% cpu_p90={cpu[int(len(cpu) * 0.9) - 1] if cpu else 0:.0f}% "
          f"ram_used_max={max(mem) if mem else 0:.1f}GB{gpu_text} rc={[p.returncode for _, p in procs]}", flush=True)
