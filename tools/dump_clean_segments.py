import json

with open('.tmp/03_Outputs/Master_Clips_and_Previews/whisper_60s.json', encoding='utf-8') as f:
    data = json.load(f)

lines = []
for i, s in enumerate(data):
    words = [w.get("word", "") for w in s.get("words", [])]
    lines.append(f"Seg {i:02d} ({s['start']:05.2f} - {s['end']:05.2f}): {s['text']}")

with open('.tmp/04_Sandbox/segments_clean.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(lines))
print(f"Saved {len(lines)} segments to .tmp/04_Sandbox/segments_clean.txt")
