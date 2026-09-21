import json
from pathlib import Path

with open('.tmp/gadget_demo/whisper_timing.json', encoding='utf-8') as f:
    data = json.load(f)

# Define our clean script phrases corresponding exactly to the 10 speech segments:
script_phrases = [
    ["นี่คือ", "Xiaomi", "MIX Flip"],
    ["สมาร์ทโฟน", "จอพับรุ่นแรก", "จากทาง Xiaomi"],
    ["ที่พัฒนาขึ้น", "อย่างประณีต"],
    ["โดดเด่นด้วย", "จอด้านนอก", "ขนาด 4.01 นิ้ว"],
    ["ออกแบบให้", "ใช้งานแอปพลิเคชัน", "ได้ครบถ้วน"],
    ["ผสานระบบ", "กล้องคู่ระดับโปร", "ร่วมกับ Leica"],
    ["เพื่อมิติภาพ", "ที่คมชัด", "เป็นธรรมชาติ"],
    ["และขับเคลื่อน", "ด้วยขุมพลัง", "Snapdragon"],
    ["8 Gen 3", "มอบประสบการณ์", "ที่ราบรื่น"],
    ["และนิ่งสงบ", "ในทุกมิติ", "การใช้งานครับ"]
]

print(f"Segments count: {len(data)}, Script phrases count: {len(script_phrases)}")

timed_phrases = []
for i, s in enumerate(data):
    words = script_phrases[i]
    start = s["start"]
    end = s["end"]
    duration = end - start
    w_dur = duration / len(words)
    
    word_timings = []
    for w_idx, w in enumerate(words):
        w_start = start + (w_idx * w_dur)
        w_end = start + ((w_idx + 1) * w_dur) if w_idx < len(words) - 1 else end
        word_timings.append({
            "word": w,
            "start": round(w_start, 2),
            "end": round(w_end, 2)
        })
    timed_phrases.append({
        "phrase": " ".join(words),
        "start": round(start, 2),
        "end": round(end, 2),
        "words": word_timings
    })

with open('.tmp/gadget_demo/exact_karaoke_timing.json', 'w', encoding='utf-8') as f:
    json.dump(timed_phrases, f, ensure_ascii=False, indent=2)

print("Generated exact_karaoke_timing.json successfully!")
