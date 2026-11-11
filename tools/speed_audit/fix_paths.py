"""Point the TEMP copy of a manifest at the real (read-only) raw files in this checkout."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
pj = Path(__file__).resolve().parents[2] / ".tmp" / "speed_audit" / "data" / "03_Projects" / sys.argv[1] / "project.json"
d = json.loads(pj.read_text(encoding="utf-8"))
count = [0]
PATTERN = re.compile(r"^(?:[A-Za-z]:.*?[\\/])?01_Raw[\\/](.*)$")


def fix(v):
    if isinstance(v, dict):
        return {k: fix(x) for k, x in v.items()}
    if isinstance(v, list):
        return [fix(x) for x in v]
    if isinstance(v, str):
        m = PATTERN.match(v)
        if m:
            count[0] += 1
            return str(REPO / "01_Raw" / m.group(1))
    return v


d = fix(d)
# Strict reuse fingerprints store the artifact's absolute path and mtime, so they can never
# match inside a copied data root. Without them the manifest takes the legacy reuse path;
# with them the voice stage re-synthesizes (a paid TTS call) on every "re-render".
if d.pop("incremental_render", None) is not None:
    print("dropped incremental_render (temp copy only)")
pj.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("fixed", count[0])
for c in d["render_params"]["clip_list"]:
    print(Path(c["source_path"]).exists(), c.get("trim_start"), c.get("trim_end"), c.get("duration"))
