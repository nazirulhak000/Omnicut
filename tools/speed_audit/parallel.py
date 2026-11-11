"""Run N copies of the captured final encode at once; report wall time, CPU and RAM."""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit"
OUTDIR = HERE / "replay"
OUTDIR.mkdir(parents=True, exist_ok=True)
ARGV = json.loads((HERE / "out" / f"{sys.argv[1]}.encode_argv.json").read_text(encoding="utf-8"))
ARGV = [a for a in ARGV if a not in ("-nostats",)]
if "-progress" in ARGV:
    i = ARGV.index("-progress")
    del ARGV[i:i + 2]

for n in [int(x) for x in sys.argv[2:]]:
    samples = []
    stop = threading.Event()

    def sample():
        psutil.cpu_percent(None)
        while not stop.wait(1.0):
            samples.append((psutil.cpu_percent(None), psutil.virtual_memory().used / 2**30))

    t = threading.Thread(target=sample, daemon=True)
    t.start()
    started = time.perf_counter()
    procs = []
    for k in range(n):
        cmd = ARGV[:-1] + [str(OUTDIR / f"par_{n}_{k}.mp4")]
        procs.append((time.perf_counter(), subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
    each = []
    for s, p in procs:
        p.wait()
        each.append(round(time.perf_counter() - s, 1))
    wall = time.perf_counter() - started
    stop.set()
    cpu = sorted(c for c, _ in samples)
    mem = [m for _, m in samples]
    print(f"workers={n} wall={wall:.1f}s per-job={each} clips/min={n / wall * 60:.2f} "
          f"cpu_avg={sum(cpu) / max(1, len(cpu)):.0f}% cpu_p90={cpu[int(len(cpu) * 0.9) - 1] if cpu else 0:.0f}% "
          f"ram_used_max={max(mem) if mem else 0:.1f}GB rc={[p.returncode for _, p in procs]}", flush=True)
