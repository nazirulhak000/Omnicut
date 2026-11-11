"""End-to-end run of the two-pass subtitle prototype on a captured encode command.

Usage: python second_pass.py <label>
Runs, in .tmp/speed_audit/replay/second_pass/ only:
  1. cold      pass 1 + pass 2
  2. caption   the .ass is edited (copy; the project's own file is not touched) -> pass 2 only
  3. timeline  one clip trim changes -> new key -> pass 1 + pass 2
and prints the time of each, plus which intermediates prune() would drop.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
from scripts import subtitle_second_pass as sp  # noqa: E402

HERE = REPO / ".tmp" / "speed_audit"
WORK = HERE / "replay" / "second_pass"
WORK.mkdir(parents=True, exist_ok=True)
label = sys.argv[1]
ARGV = json.loads((HERE / "out" / f"{label}.encode_argv.json").read_text(encoding="utf-8"))

gi = ARGV.index("-filter_complex")
first_in = ARGV.index("-ss") if "-ss" in ARGV[:gi] else ARGV.index("-i")
INPUTS = ARGV[first_in:gi]
GRAPH = ARGV[gi + 1]
CODEC = ARGV[ARGV.index("-c:v"):ARGV.index("-r")]
DUR = ARGV[ARGV.index("-movflags") + 3]
AUDIO_MAP = ARGV[ARGV.index("-map", ARGV.index("-map") + 1) + 1]
HEAD = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-threads", "0", "-filter_complex_threads", "0"]
MEDIA = [Path(INPUTS[i + 1]) for i, a in enumerate(INPUTS) if a == "-i" and Path(INPUTS[i + 1]).is_file()]


def run(cmd):
    started = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if proc.returncode != 0:
        raise SystemExit(proc.stderr[-800:])
    return time.perf_counter() - started


def unescape(ffmpeg_path):
    return Path(ffmpeg_path.replace("\\:", ":"))


def escape(path):
    return str(path).replace("\\", "/").replace(":", "\\:")


def render(name, graph):
    split = sp.split_graph(graph)
    small = [unescape(m) for m in re.findall(r"(?:subtitles|lut3d)=(?:file=)?'((?:[^'\\]|\\.)*)'", split.pre_graph)]
    key = sp.intermediate_key(HEAD + INPUTS + ["-filter_complex", split.pre_graph] + CODEC + [DUR], MEDIA, small)
    seconds = {"pass1": 0.0}
    intermediate = sp.find_reusable(WORK, key)
    if intermediate is None:
        intermediate = sp.intermediate_path(WORK, key)
        partial = intermediate.with_suffix(".partial.mp4")
        seconds["pass1"] = run(sp.build_pass1_cmd(HEAD, INPUTS, split.pre_graph, AUDIO_MAP, CODEC,
                                                  ["-c:a", "aac", "-b:a", "192k"], "30", DUR, partial))
        partial.replace(intermediate)
    out = WORK / f"{name}.mp4"
    seconds["pass2"] = run(sp.build_pass2_cmd(HEAD, intermediate, split.burn_chain, True, CODEC, "30", out))
    total = seconds["pass1"] + seconds["pass2"]
    print(f"{name:10s} key={key[:10]} pass1={seconds['pass1']:6.2f}s pass2={seconds['pass2']:6.2f}s total={total:6.2f}s"
          f" {'(intermediate reused)' if not seconds['pass1'] else ''}", flush=True)
    return key


for stale in WORK.glob("pre_subtitles_*.mp4"):
    # keep cold runs cold without deleting anything
    stale.rename(stale.with_name(f"old_{int(time.time())}_{stale.name}"))

single = run(HEAD + INPUTS + ["-filter_complex", GRAPH, "-map", "[v_final]", "-map", AUDIO_MAP] + CODEC
             + ["-r", "30", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-t", DUR, str(WORK / "single_pass.mp4")])
print(f"single     pass total={single:6.2f}s")

cold_key = render("cold", GRAPH)

ass = unescape(sp.split_graph(GRAPH).ass_path)
edited = WORK / "subtitles_edited.ass"
text = ass.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
last_dialogue = max(i for i, ln in enumerate(lines) if ln.startswith("Dialogue:"))
del lines[last_dialogue]  # the edit: one caption event removed
edited.write_text("".join(lines), encoding="utf-8")
caption_key = render("caption", GRAPH.replace(sp.split_graph(GRAPH).ass_path, escape(edited)))
assert caption_key == cold_key, "a caption-only edit must reuse the intermediate"

timeline_key = render("timeline", re.sub(r"trim=start=0:duration=([\d.]+)", lambda m: f"trim=start=0.2:duration={m.group(1)}", GRAPH, count=1))
assert timeline_key != cold_key, "a timeline change must not reuse the intermediate"

print("prune(keep=1) would drop:", [p.name for p in sp.prune(WORK, keep=1)])
