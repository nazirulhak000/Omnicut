import json
from pathlib import Path

BURSTS = [
    {
        "words": [
            ("นี่คือ", 0.26, 1.20),
            ("Xiaomi", 1.20, 1.78),
            ("MIX Flip", 1.78, 2.32)
        ]
    },
    {
        "words": [
            ("สมาร์ทโฟน", 2.78, 3.52),
            ("จอพับรุ่นแรก", 3.52, 4.28),
            ("จากทาง Xiaomi", 4.28, 5.22)
        ]
    },
    {
        "words": [
            ("ที่พัฒนาขึ้น", 5.46, 6.36),
            ("อย่างประณีต", 6.36, 7.22)
        ]
    },
    {
        "words": [
            ("โดดเด่นด้วย", 7.64, 8.16),
            ("จอด้านนอก", 8.16, 8.86),
            ("ขนาด 4.01 นิ้ว", 8.86, 10.32)
        ]
    },
    {
        "words": [
            ("ออกแบบให้", 10.64, 11.28),
            ("ใช้งานแอปพลิเคชัน", 11.28, 12.38),
            ("ได้ครบถ้วน", 12.38, 13.14)
        ]
    },
    {
        "words": [
            ("ผสานระบบ", 13.42, 14.24),
            ("กล้องคู่ระดับโปร", 14.24, 15.14)
        ]
    },
    {
        "words": [
            ("ที่พัฒนาร่วมกับ", 15.14, 16.24),
            ("Leica", 16.24, 16.78)
        ]
    },
    {
        "words": [
            ("เพื่อมิติภาพ", 17.10, 17.88),
            ("ที่คมชัด", 17.88, 18.70),
            ("เป็นธรรมชาติ", 18.70, 19.82)
        ]
    },
    {
        "words": [
            ("และขับเคลื่อน", 20.22, 20.82),
            ("ด้วยขุมพลัง", 20.82, 21.52),
            ("Snapdragon", 21.52, 22.28)
        ]
    },
    {
        "words": [
            ("8 Gen 3", 22.28, 23.50),
            ("มอบประสบการณ์", 23.50, 24.30),
            ("ที่ราบรื่น", 24.30, 25.20)
        ]
    },
    {
        "words": [
            ("และนิ่งสงบ", 25.34, 25.92),
            ("ในทุกมิติ", 25.92, 26.84),
            ("การใช้งานครับ", 26.84, 27.70)
        ]
    }
]

def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

def build_ass(output_path, total_dur):
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Mali,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,20,20,380,1",
        "Style: SourceCredit,Prompt,26,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2.5,0,2,20,20,32,1",
        "Style: ChannelBadge,Prompt,28,&H0000E6FF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,2.5,0,9,40,40,55,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 1,0:00:00.00,{format_ass_time(total_dur)},ChannelBadge,,0,0,0,,TECH MX",
        f"Dialogue: 1,0:00:00.00,0:00:12.64,SourceCredit,,0,0,0,,Source : Weibo Xiaomi",
        f"Dialogue: 1,0:00:12.64,{format_ass_time(total_dur)},SourceCredit,,0,0,0,,Source : mi.com Official"
    ]

    for burst in BURSTS:
        word_items = burst["words"]
        n = len(word_items)
        for i in range(n):
            w_text, w_start, w_end = word_items[i]
            
            # Words 0..i-1: White
            # Word i: Neon Green (&H66FF00&)
            # Words i+1..n-1: Invisible (\alpha&HFF&) for locked alignment
            parts = []
            for j in range(n):
                txt = word_items[j][0]
                if j < i:
                    parts.append(r"{\c&HFFFFFF&}" + txt)
                elif j == i:
                    parts.append(r"{\c&H66FF00&}" + txt + r"{\r\c&HFFFFFF&}")
                else:
                    parts.append(r"{\alpha&HFF&}" + txt)
            
            full_line = " ".join(parts)
            lines.append(f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{full_line}")
    
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated precision ASS to {output_path}")

if __name__ == "__main__":
    build_ass(".tmp/gadget_demo/subtitles_mix_flip.ass", 28.07)
