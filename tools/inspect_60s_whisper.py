import json

with open('.tmp/03_Outputs/Master_Clips_and_Previews/whisper_60s.json', encoding='utf-8') as f:
    data = json.load(f)

for i, s in enumerate(data):
    words_str = " ".join(w["word"] for w in s.get("words", []))
    print(f"Seg {i:02d}: {s['start']:05.2f} -> {s['end']:05.2f} | {s['text']} | WORDS: {words_str}")
