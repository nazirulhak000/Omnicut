import json
from pathlib import Path

with open('.tmp/gadget_demo/whisper_60s.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

lines = []
for i, s in enumerate(data):
    lines.append(f"SEG {i:02d}: [{s['start']:.2f}s -> {s['end']:.2f}s] {s['text']}")

Path('.tmp/gadget_demo/whisper_60s_segments.txt').write_text("\n".join(lines), encoding='utf-8')
print(f"Total segments: {len(data)}")
