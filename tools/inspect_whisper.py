import json
from pathlib import Path

with open('.tmp/gadget_demo/whisper_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

out_lines = []
for i, s in enumerate(data):
    out_lines.append(f"SEG {i:02d}: {s['start']:.2f}s -> {s['end']:.2f}s | {s['text']}")
    for w in s.get('words', []):
        out_lines.append(f"   [{w['start']:.2f} - {w['end']:.2f}] {w['word']}")

Path('.tmp/gadget_demo/whisper_summary.txt').write_text("\n".join(out_lines), encoding='utf-8')
print("Written summary.")
