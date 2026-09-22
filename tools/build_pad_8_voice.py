"""Generate 60-second voiceover for Xiaomi Pad 8 using Gemini Flash TTS (Fenrir).
"""

import sys
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gemini_tts_engine import GeminiFlashTTSEngine

PRODUCT_DIR = PROJECT_ROOT / ".tmp" / "Products" / "Xiaomi_Pad_8"
WORKSPACE_DIR = PRODUCT_DIR / "02_Workspace"
AUDIO_DIR = WORKSPACE_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

wav_path = AUDIO_DIR / "voice_pad_8_60s.wav"

SCRIPT_60S = (
    "นี่คือแท็บเล็ตสายโปรตัวจริง ที่บางเบาจนน่าตกใจ! Xiaomi Pad 8 จัดเต็มสเปกระดับท็อปในร่างโลหะ Unibody บางเพียง 5.75 มิลลิเมตร "
    "หน้าจอขนาดใหญ่ 11.2 นิ้ว คมชัดสะใจระดับ 3.2K รีเฟรชเรตลื่นไหล 144Hz อัตราส่วน 3 ต่อ 2 อ่านสบายตา พร้อมลำโพงสเตอริโอ 4 ตัวกระหึ่มระบบ Dolby Atmos "
    "ทำงานระดับ PC ได้ทันที ด้วยเคสคีย์บอร์ดแม่เหล็กตอบสนองไว และปากกา Focus Pen Pro รองรับแรงกด 8,192 ระดับ เขียนลื่นไม่มีดีเลย์ แถมยังเชื่อมต่อเป็นจอแยกให้แล็ปท็อปได้แบบไร้สาย "
    "ขับเคลื่อนด้วยขุมพลัง Snapdragon 8s Gen 4 บนระบบปฏิบัติการ Xiaomi HyperOS 3 เปิดแอปทำงานพร้อมกันหลายหน้าต่างลื่นไหลไม่มีสะดุด รองรับฟีเจอร์อัจฉริยะ HyperAI ครบครัน "
    "แบตเตอรี่ไซส์ยักษ์ 9,200 มิลลิแอมป์ ใช้งานยาวนานข้ามวัน พร้อมเทคโนโลยีชาร์จไว 45W Turbo Charge เสียบชาร์จแปบเดียวพร้อมลุยงานต่อทันที "
    "ใครมองหาแท็บเล็ตที่ทั้งสวย แรง ทำงานจบในเครื่องเดียว Xiaomi Pad 8 คือคำตอบที่คุ้มค่าที่สุดใน พ.ศ. นี้เลยครับ"
)

print(f"Generating 60s voiceover for Xiaomi Pad 8 with Gemini Flash TTS (Fenrir)...")
print(f"Script length: {len(SCRIPT_60S)} characters")

GeminiFlashTTSEngine.generate_speech(
    text=SCRIPT_60S,
    output_path=str(wav_path),
    voice_preset="gemini_fenrir_male_strong",
    ad_tone="commercial_premium",
    speed=1.05
)

with wave.open(str(wav_path), "r") as f:
    dur = f.getnframes() / float(f.getframerate())

print(f"[OK] Generated Audio Duration: {dur:.2f} seconds at {wav_path}")
