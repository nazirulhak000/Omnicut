"""Speed-audit harness. Scripts live in tools/speed_audit; all data and results go to .tmp/speed_audit.

Runs the real pipeline against an isolated data root and records:
  - per-stage seconds (ctx.stage_timings, already emitted by the pipeline)
  - every subprocess (ffmpeg/ffprobe/...) with wall time and argv
  - wall time of selected Python functions (wrapped here, product code untouched)

Usage:
  python harness.py rerender <project> <label> [--cold]
  python harness.py draft <label> --video <path> --script-file <txt> [--ai-script] [--cold]
"""
import argparse
import functools
import importlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WORK = REPO / ".tmp" / "speed_audit"
DATA = WORK / "data"
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)

assert ".tmp" in str(DATA), "refusing to run outside .tmp"
os.environ["OMNICUT_DATA_ROOT"] = str(DATA)
# API keys come from the real .env (read only); nothing is written back.
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
sys.path.insert(0, str(REPO))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

EVENTS = []
_lock = threading.Lock()
T0 = time.perf_counter()


def _log(kind, name, started, extra=None):
    with _lock:
        EVENTS.append({
            "kind": kind, "name": name,
            "t_start": round(started - T0, 3),
            "seconds": round(time.perf_counter() - started, 3),
            "thread": threading.current_thread().name,
            **(extra or {}),
        })


# ---- subprocess timing -------------------------------------------------
_RealPopen = subprocess.Popen


class TimedPopen(_RealPopen):
    def __init__(self, args, *a, **kw):
        self._sa_started = time.perf_counter()
        self._sa_logged = False
        argv = args if isinstance(args, (list, tuple)) else [str(args)]
        self._sa_argv = [str(x) for x in argv]
        super().__init__(args, *a, **kw)

    def _sa_done(self):
        if not self._sa_logged and self.returncode is not None:
            self._sa_logged = True
            argv = self._sa_argv
            _log("subprocess", Path(argv[0]).stem.lower(), self._sa_started,
                 {"rc": self.returncode, "argc": len(argv),
                  "argv": argv if len(" ".join(argv)) < 60000 else argv[:40]})

    def wait(self, *a, **kw):
        try:
            return super().wait(*a, **kw)
        finally:
            self._sa_done()

    def poll(self):
        rc = super().poll()
        self._sa_done()
        return rc


subprocess.Popen = TimedPopen


def wrap(module_name, qualname, label=None):
    """Time a function/classmethod in place; silently skip if it does not exist."""
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        print(f"[harness] cannot import {module_name}: {exc}")
        return
    parts = qualname.split(".")
    owner = mod
    for p in parts[:-1]:
        owner = getattr(owner, p, None)
        if owner is None:
            print(f"[harness] missing {module_name}.{qualname}")
            return
    raw = owner.__dict__.get(parts[-1]) if hasattr(owner, "__dict__") else None
    if raw is None:
        print(f"[harness] missing {module_name}.{qualname}")
        return
    kind = "plain"
    fn = raw
    if isinstance(raw, classmethod):
        kind, fn = "classmethod", raw.__func__
    elif isinstance(raw, staticmethod):
        kind, fn = "staticmethod", raw.__func__
    name = label or f"{module_name.split('.')[-1]}.{qualname}"

    @functools.wraps(fn)
    def timed(*a, **kw):
        started = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            _log("func", name, started)

    if kind == "classmethod":
        timed = classmethod(timed)
    elif kind == "staticmethod":
        timed = staticmethod(timed)
    setattr(owner, parts[-1], timed)


def load_wraps():
    spec = HERE / "wraps.json"
    if spec.exists():
        for module_name, qualname in json.loads(spec.read_text(encoding="utf-8")):
            wrap(module_name, qualname)


def summarize(label, stage_timings, total, extra=None):
    by = {}
    for e in EVENTS:
        key = f"{e['kind']}:{e['name']}"
        slot = by.setdefault(key, {"n": 0, "seconds": 0.0, "max": 0.0})
        slot["n"] += 1
        slot["seconds"] = round(slot["seconds"] + e["seconds"], 3)
        slot["max"] = max(slot["max"], e["seconds"])
    result = {"label": label, "total_s": round(total, 3), "stage_seconds": stage_timings,
              "aggregate": by, "events": EVENTS, **(extra or {})}
    path = OUT / f"{label}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[harness] {label}: total {total:.2f}s")
    for k, v in stage_timings.items():
        print(f"   stage {k:16s} {v:8.2f}s")
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]["seconds"])[:25]:
        print(f"   {k:44s} n={v['n']:3d} sum={v['seconds']:8.2f}s max={v['max']:7.2f}s")
    print(f"[harness] wrote {path}")


def run_pipeline(label, kwargs):
    import_started = time.perf_counter()
    from scripts.pipeline import TikTokAutoCutterPipeline
    from scripts import pipeline_context
    import_s = time.perf_counter() - import_started
    load_wraps()

    captured = {}
    real_init = pipeline_context.PipelineContext.__init__

    def init(self, *a, **kw):
        real_init(self, *a, **kw)
        captured["ctx"] = self

    pipeline_context.PipelineContext.__init__ = init
    started = time.perf_counter()
    error = None
    try:
        TikTokAutoCutterPipeline.run(**kwargs)
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        error = repr(exc)
    total = time.perf_counter() - started
    ctx = captured.get("ctx")
    extra = {"import_s": round(import_s, 3), "error": error}
    if ctx is not None:
        extra["total_duration"] = getattr(ctx, "total_duration", None)
        extra["result_paths"] = {k: str(v) for k, v in (ctx.result_paths or {}).items()
                                 if isinstance(v, (str, Path))}
    summarize(label, dict(ctx.stage_timings) if ctx else {}, total, extra)


def kwargs_from_manifest(project):
    import inspect
    from scripts.pipeline import TikTokAutoCutterPipeline
    manifest = json.loads((DATA / "03_Projects" / project / "project.json").read_text(encoding="utf-8"))
    rp = dict(manifest.get("render_params") or {})
    accepted = set(inspect.signature(TikTokAutoCutterPipeline.run).parameters)
    kwargs = {k: v for k, v in rp.items() if k in accepted}
    kwargs["project_name"] = project
    for key in ("overlays", "effects", "stickers", "color_theme", "spotlight", "background_isolation"):
        if key in manifest and key in accepted and manifest[key] is not None:
            kwargs[key] = manifest[key]
    return kwargs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["rerender", "draft"])
    ap.add_argument("a")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--video")
    ap.add_argument("--script-file")
    ap.add_argument("--project")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-vision", action="store_true")
    ap.add_argument("--no-bilingual", action="store_true")
    ap.add_argument("--resume-from")
    ap.add_argument("--target-duration", type=int, default=60)
    args = ap.parse_args()

    if args.mode == "rerender":
        project, label = args.a, args.b
        kwargs = kwargs_from_manifest(project)
        kwargs["export_mp4"] = not args.no_export
        if args.resume_from:
            kwargs["resume_from"] = args.resume_from
        run_pipeline(label, kwargs)
    else:
        label = args.a
        kwargs = dict(
            product_name="HOYAUP พัดลมแม่เหล็ก AI",
            raw_video_path=args.video,
            project_name=args.project or label,
            key_features="ทำความเย็นระบบเซมิคอนดักเตอร์ AI, กำลังไฟสูงสุด 24 วัตต์ เย็นลงถึง -9 องศา, น้ำหนักเบา 83 กรัม ไร้เสียงรบกวน, รองรับ iPhone และ Android",
            pain_point="โทรศัพท์ร้อนจัดขณะเล่นเกมหรือไลฟ์สด เฟรมเรตตก เครื่องกระตุก",
            target_duration=args.target_duration,
            use_ai_vision=not args.no_vision,
            export_mp4=not args.no_export,
        )
        if args.no_bilingual:
            kwargs["bilingual_subtitles"] = False
        if args.script_file:
            kwargs["custom_script"] = Path(args.script_file).read_text(encoding="utf-8").strip()
        run_pipeline(label, kwargs)


if __name__ == "__main__":
    main()
