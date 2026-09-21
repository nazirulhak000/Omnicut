import json

with open('.tmp/gadget_demo/whisper_timing.json', encoding='utf-8') as f:
    data = json.load(f)

for i, s in enumerate(data):
    print(f"Segment {i}: {s['start']:.2f} -> {s['end']:.2f} | {s['text']}")
