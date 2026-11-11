"""Replay the captured final-encode command with parts removed, to see where the time goes.

Never touches product code; every output goes to .tmp/speed_audit/replay/.
Usage: python replay.py <label> <rounds> <variant> [<variant> ...]
"""
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
HERE = Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit"
OUTDIR = HERE / "replay"
OUTDIR.mkdir(exist_ok=True)
label, rounds = sys.argv[1], int(sys.argv[2])
variants = sys.argv[3:]
ARGV = json.loads((HERE / "out" / f"{label}.encode_argv.json").read_text(encoding="utf-8"))


def split(argv):
    gi = argv.index("-filter_complex")
    graph = argv[gi + 1]
    first_in = argv.index("-ss") if "-ss" in argv[:gi] else argv.index("-i")
    inputs = argv[first_in:gi]
    return inputs, graph


INPUTS, GRAPH = split(ARGV)
CODEC = ARGV[ARGV.index("-c:v"):ARGV.index("-r")]
DUR = ARGV[ARGV.index("-movflags") + 3]
AUDIO_MAP = ARGV[ARGV.index("-map", ARGV.index("-map") + 1) + 1]


def no_subtitles(graph):
    return re.sub(r";\[([a-z0-9_]+)\]subtitles=.*?\[v_final\]$", lambda m: f";[{m.group(1)}]null[v_final]", graph)


def no_gradient(graph):
    # drop the geq scrim branch and wire its base straight through
    m = re.search(r"color=c=black:s=\d+x\d+:d=[\d.]+\[(grad_src_\d+)\];\[\1\]format=yuva420p,geq=.*?\[(grad_alpha_\d+)\];\[([a-z0-9_]+)\]\[\2\]overlay=[^\[]*\[(v_gradient_\d+)\];", graph)
    if not m:
        raise SystemExit("gradient branch not found")
    return graph.replace(m.group(0), f"[{m.group(3)}]null[{m.group(4)}];")


def build(variant):
    graph = GRAPH
    out = ["-f", "null", "-"]
    codec = []
    audio = []
    head = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-threads", "0", "-filter_complex_threads", "0"]
    parts = variant.split("+")
    if "nosub" in parts:
        graph = no_subtitles(graph)
    if "nograd" in parts:
        graph = no_gradient(graph)
    for p in parts:
        if p.startswith("fct"):
            head[head.index("-filter_complex_threads") + 1] = p[3:]
    if "decode" in parts:
        n = INPUTS.count("-i") - 1
        cmd = head + INPUTS
        for i in range(n):
            cmd += ["-map", f"{i}:v", "-f", "null", "-"]
        return cmd
    if "full" in parts:
        codec = CODEC + ["-r", "30", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        audio = ["-map", AUDIO_MAP]
        out = [str(OUTDIR / f"{variant.replace('+', '_')}.mp4")]
    elif "x264" in parts:
        codec = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.2", "-preset", "medium", "-crf", "18", "-r", "30", "-pix_fmt", "yuv420p"]
        out = [str(OUTDIR / f"{variant.replace('+', '_')}.mp4")]
    elif "amf" in parts:
        codec = CODEC + ["-r", "30", "-pix_fmt", "yuv420p"]
        out = [str(OUTDIR / f"{variant.replace('+', '_')}.mp4")]
    else:
        codec = ["-r", "30", "-pix_fmt", "yuv420p"]
    return head + INPUTS + ["-filter_complex", graph, "-map", "[v_final]"] + audio + codec + ["-t", DUR] + out


results = {}
for variant in variants:
    cmd = build(variant)
    times = []
    for _ in range(rounds):
        started = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        times.append(round(time.perf_counter() - started, 2))
        if proc.returncode != 0:
            print(variant, "FAILED", proc.stderr[-600:])
            break
    results[variant] = {"times": times, "median": statistics.median(times)}
    print(f"{variant:28s} median={statistics.median(times):7.2f}s runs={times}", flush=True)
(OUTDIR / f"{label}.{int(time.time())}.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
