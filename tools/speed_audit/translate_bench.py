"""Time SubtitleTranslator.translate_batch on a real project's micro-cue texts.

Read-only on the project; the translation cache is redirected to .tmp/speed_audit
through OMNICUT_DATA_ROOT so the real data root is never written.

Usage: python translate_bench.py <project folder name> <label> [--keep-cache]
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / ".tmp" / "speed_audit"
DATA = WORK / "translate_data"
if "--keep-cache" not in sys.argv:
    shutil.rmtree(DATA, ignore_errors=True)
DATA.mkdir(parents=True, exist_ok=True)
os.environ["OMNICUT_DATA_ROOT"] = str(DATA)
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

manifest = json.loads((REPO / "03_Projects" / sys.argv[1] / "project.json").read_text(encoding="utf-8"))
texts = [str(c.get("text") or "").strip() for c in manifest.get("micro_cues") or []]
texts = [t for t in texts if t]

from scripts.translator import SubtitleTranslator  # noqa: E402

started = time.perf_counter()
result = SubtitleTranslator.translate_batch(texts)
seconds = round(time.perf_counter() - started, 2)
out = {"label": sys.argv[2], "phrases": len(texts), "seconds": seconds,
       "empty": sum(1 for r in result if not r), "pairs": list(zip(texts, result))}
(WORK / "out").mkdir(parents=True, exist_ok=True)
(WORK / "out" / f"translate_{sys.argv[2]}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{sys.argv[2]}: {len(texts)} phrases in {seconds}s, empty={out['empty']}")
