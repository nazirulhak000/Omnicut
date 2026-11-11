"""Experiment: stop computing the hook scrim (geq) once it is fully transparent.

Compares every output frame (framemd5 of the filter graph output, before any
encoder) between the unchanged graph and the shortened-scrim graph.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
HERE = Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit"
OUTDIR = HERE / "replay"
OUTDIR.mkdir(exist_ok=True)
label = sys.argv[1]
ARGV = json.loads((HERE / "out" / f"{label}.encode_argv.json").read_text(encoding="utf-8"))
gi = ARGV.index("-filter_complex")
GRAPH = ARGV[gi + 1]
first_in = ARGV.index("-ss") if "-ss" in ARGV[:gi] else ARGV.index("-i")
INPUTS = ARGV[first_in:gi]
DUR = sys.argv[2] if len(sys.argv) > 2 else ARGV[ARGV.index("-movflags") + 3]

m = re.search(r"color=c=black:s=(\d+x\d+):d=([\d.]+)\[(grad_src_\d+)\]", GRAPH)
ends = [float(a) + float(b) for a, b in re.findall(r"max\(0\\,1-\(T-([\d.]+)\)/([\d.]+)\)", GRAPH)]
print("scrim source duration", m.group(2), "fade ends at", ends)
end = max(ends) + 2 / 30  # two frames of margin past full transparency
short = GRAPH.replace(m.group(0), f"color=c=black:s={m.group(1)}:d={end:.6f}[{m.group(3)}]")
short = re.sub(r"(\[grad_alpha_\d+\]overlay=x=0:y=0:format=auto)", r"\1:eof_action=pass", short)


def run(name, graph):
    out = OUTDIR / f"{name}.framemd5"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-threads", "0", "-filter_complex_threads", "0",
           *INPUTS, "-filter_complex", graph, "-map", "[v_final]", "-r", "30", "-pix_fmt", "yuv420p",
           "-t", DUR, "-f", "framemd5", str(out)]
    started = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    secs = time.perf_counter() - started
    if proc.returncode != 0:
        print(name, "FAILED", proc.stderr[-500:])
    lines = [l for l in out.read_text().splitlines() if l and not l.startswith("#")]
    print(f"{name}: {secs:.2f}s frames={len(lines)}")
    return lines


a = run("grad_orig", GRAPH)
b = run("grad_short", short) if len(sys.argv) < 4 else run("grad_orig2", GRAPH)
diff = [i for i, (x, y) in enumerate(zip(a, b)) if x.split(",")[-1] != y.split(",")[-1]]
print("frame count equal:", len(a) == len(b), "differing frames:", len(diff), diff[:20])
