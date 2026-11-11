"""Save the final-encode ffmpeg argv of a harness run and print its shape."""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
here = Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit"
d = json.loads((here / "out" / f"{sys.argv[1]}.json").read_text(encoding="utf-8"))
enc = max((e for e in d["events"] if e["kind"] == "subprocess" and e["name"] == "ffmpeg"), key=lambda e: e["seconds"])
argv = enc["argv"]
(here / "out" / f"{sys.argv[1]}.encode_argv.json").write_text(json.dumps(argv, ensure_ascii=False, indent=1), encoding="utf-8")
graph = argv[argv.index("-filter_complex") + 1] if "-filter_complex" in argv else ""
print("seconds", enc["seconds"], "graph chars", len(graph))
print("non-graph argv:", [a if a != graph else "<GRAPH>" for a in argv])
names = re.findall(r"(?:^|[;,\]])\s*([a-z0-9_]+)=", graph)
count = {}
for n in names:
    count[n] = count.get(n, 0) + 1
print("filters:", dict(sorted(count.items(), key=lambda kv: -kv[1])))
for part in graph.split(";")[:4]:
    print("HEAD:", part[:600])
for part in graph.split(";")[-9:]:
    print("TAIL:", part[:400])
