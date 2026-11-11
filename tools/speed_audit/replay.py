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


def old_gradient(graph):
    # before phase 2 (2026-11-12) the scrim source ran for the whole clip
    out, n = re.subn(r"(color=c=black:s=\d+x\d+:d=)[\d.]+(\[grad_src_\d+\])",
                     lambda m: f"{m.group(1)}{float(DUR) + 0.5}{m.group(2)}", graph)
    if not n:
        raise SystemExit("gradient source not found")
    return out


def strip_gradient(graph):
    # The scrim alpha depends on the row and the time, never on the column: compute it on a
    # 2 px wide strip and repeat that strip across the frame.
    out, n = re.subn(r"(color=c=black:s=)(\d+)x(\d+)(:d=[\d.]+\[grad_src_\d+\];\[grad_src_\d+\]format=yuva420p,geq=[^;]*?)(\[grad_alpha_\d+\])",
                     lambda m: f"{m.group(1)}2x{m.group(3)}{m.group(4)},scale={m.group(2)}:{m.group(3)}:flags=neighbor{m.group(5)}", graph)
    if not n:
        raise SystemExit("gradient source not found")
    return out


def gradient_enable(graph):
    # Blend the scrim only while it can be visible; outside that window its alpha is 0.
    m = re.search(r"if\(lt\(T\\,([\d.]+)\)\\,0\\,if\(lt\(T\\,([\d.]+)\)\\,1\\,max\(0\\,1-\(T-[\d.]+\)/([\d.]+)\)", graph)
    if not m:
        raise SystemExit("scrim alpha expression not found")
    start, end = float(m.group(1)), float(m.group(2)) + float(m.group(3)) + 0.1
    out, n = re.subn(r"(\[grad_alpha_\d+\]overlay=x=0:y=0:format=auto)",
                     lambda k: f"{k.group(1)}:enable='between(t\\,{start:g}\\,{end:g})'", graph)
    if not n:
        raise SystemExit("scrim overlay not found")
    return out


def with_qa(graph):
    # B5 experiment: black/freeze detectors on a side branch of the same pass
    if not graph.endswith("[v_final]"):
        raise SystemExit("graph does not end in [v_final]")
    return (graph[:-len("[v_final]")] + "[v_pre_qa];[v_pre_qa]split[v_final][v_qa];"
            "[v_qa]blackdetect=d=0.3:pix_th=0.1,freezedetect=n=-60dB:d=1.5,nullsink")


PRE_FIT = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(iw-1080)/2:(ih-1920)/2"


def keyframed(graph, pattern, repl):
    # B4 experiment: rewrite only the clip chains that zoom/pan per frame
    out, n = re.subn(pattern, repl, graph)
    if not n:
        raise SystemExit("no keyframed clip chain matched")
    return out


def no_pre_fit(graph):
    # drop the fit-to-canvas scale+crop that runs before the per-frame zoom
    return keyframed(graph, re.escape(PRE_FIT) + r",(?=scale=ceil\()", "")


def no_zoom(graph):
    # drop the per-frame zoom scale and its animated crop: what the keyframes cost in total
    return keyframed(graph, "(" + re.escape(PRE_FIT) + r"),scale=ceil\([^;]*?,(setsar=1\[clip_\d+\])", r"\1,\2")


def zoom_flags(graph, flags):
    return keyframed(graph, r"(scale=ceil\([^;]*?:eval=frame)", rf"\1:flags={flags}")


def zoompan(graph):
    # B4 experiment: one resample per frame. Crop the zoomed window out of the source and
    # scale only that window, instead of enlarging the whole frame and cropping afterwards.
    def between(text, start, end):
        a = text.index(start) + len(start)
        return text[a:text.index(end, a)]

    def rewrite(m):
        body = m.group(1)
        zoom = between(body, "scale=ceil(1080*(", ")/2)*2:ceil(1920*(")
        pan_x = between(body, ")/2)*2-1080)/2)*(1+(", ")):((ceil(1920*(")
        pan_y = body[body.index(")/2)*2-1920)/2)*(1+(") + len(")/2)*2-1920)/2)*(1+("):-2]
        on_input_time = [re.sub(r"\bt\b", "it", e) for e in (zoom, pan_x, pan_y)]
        zoom, pan_x, pan_y = on_input_time
        return (f"zoompan=z={zoom}:x=(iw-iw/zoom)/2*(1+({pan_x})):y=(ih-ih/zoom)/2*(1+({pan_y}))"
                f":d=1:s=1080x1920:fps=30,{m.group(2)}")

    return keyframed(graph, re.escape(PRE_FIT) + r",(scale=ceil\([^;]*?),(setsar=1\[clip_\d+\])", rewrite)


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
    if "stripgrad" in parts:
        graph = strip_gradient(graph)
    if "gradenable" in parts:
        graph = gradient_enable(graph)
    if "oldgrad" in parts:
        graph = old_gradient(graph)
    if "qa" in parts:
        graph = with_qa(graph)
        head[head.index("-loglevel") + 1] = "info"
        head.insert(1, "-nostats")
    if "nopre" in parts:
        graph = no_pre_fit(graph)
    if "nozoom" in parts:
        graph = no_zoom(graph)
    if "zoompan" in parts:
        graph = zoompan(graph)
    for p in parts:
        if p.startswith("fct"):
            head[head.index("-filter_complex_threads") + 1] = p[3:]
        if p.startswith("zf_"):
            graph = zoom_flags(graph, p[3:])
    if "lossless" in parts:
        # exact frames on disk, for SSIM/PSNR between two graphs without encoder noise
        return head + INPUTS + ["-filter_complex", graph, "-map", "[v_final]", "-r", "30", "-pix_fmt", "yuv420p",
                                "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-t", DUR,
                                str(OUTDIR / f"{variant.replace('+', '_')}.mkv")]
    if "burn" in parts:
        # B6 experiment, second pass: burn subtitles onto an already encoded subtitle-free render.
        # "burn" reads full_nosub.mp4, "burn+hq" reads full_nosub_hq.mp4.
        sub = re.search(r";\[[a-z0-9_]+\](subtitles=.*?)\[v_final\]$", GRAPH).group(1)
        src = OUTDIR / ("full_nosub_hq.mp4" if "hq" in parts else "full_nosub.mp4")
        return head + ["-i", str(src), "-filter_complex", f"[0:v]{sub}[v_final]", "-map", "[v_final]",
                       "-map", "0:a", "-c:a", "copy"] + CODEC + ["-r", "30", "-pix_fmt", "yuv420p", "-movflags",
                                                                 "+faststart", str(OUTDIR / f"{variant.replace('+', '_')}.mp4")]
    if "md5" in parts:
        # hash of the raw filter output: proves two graphs produce identical frames
        return head + INPUTS + ["-filter_complex", graph, "-map", "[v_final]", "-r", "30",
                                "-pix_fmt", "yuv420p", "-t", DUR, "-f", "md5", "-"]
    if "decode" in parts:
        n = INPUTS.count("-i") - 1
        cmd = head + INPUTS
        for i in range(n):
            cmd += ["-map", f"{i}:v", "-f", "null", "-"]
        return cmd
    if "full" in parts:
        codec = CODEC + ["-r", "30", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        if "hq" in parts:
            # B6 experiment: a near-transparent intermediate for the second pass to read
            codec[codec.index("-cq") + 1] = "12"
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
    found = ""
    if "qa" in variant.split("+"):
        hits = [ln.strip() for ln in proc.stderr.splitlines() if "black_start" in ln or "freezedetect.freeze_" in ln]
        results[variant]["qa_lines"] = hits
        found = f" qa_lines={len(hits)}"
    if "md5" in variant.split("+"):
        results[variant]["md5"] = proc.stdout.strip()
        found = f" {proc.stdout.strip()}"
    print(f"{variant:28s} median={statistics.median(times):7.2f}s runs={times}{found}", flush=True)
(OUTDIR / f"{label}.{int(time.time())}.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
