import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gemini_tts_engine import GeminiFlashTTSEngine
import wave

OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "gadget_demo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
wav_path = OUTPUT_DIR / "voice_mix_flip_60s.wav"

SCRIPT_60S = (
    "นี่คือ Xiaomi MIX Flip สมาร์ทโฟนจอพับรุ่นแรกจากทาง Xiaomi ที่พัฒนาขึ้นอย่างประณีต "
    "โดดเด่นด้วยจอด้านนอกขนาด 4.01 นิ้ว คมชัดระดับ 1.5K พร้อมรีเฟรชเรท 120Hz ออกแบบให้ใช้งานแอปพลิเคชันได้ครบถ้วนโดยไม่ต้องกางเครื่อง "
    "เมื่อกางออกจะพบกับหน้าจอหลัก OLED ขนาด 6.86 นิ้ว สว่างสูงสุดถึง 3,000 nits มอบภาพที่คมชัดและสบายตาในทุกสภาพแสง "
    "ด้านการถ่ายภาพ ผสานพลังกล้องคู่ระดับโปร 50 ล้านพิกเซลที่พัฒนาร่วมกับ Leica พร้อมเลนส์ Summilux ให้โทนภาพและมิติแสงเงาที่คมชัดเป็นธรรมชาติ "
    "ขับเคลื่อนด้วยขุมพลังเรือธง Snapdragon 8 Gen 3 เสริมด้วยระบบระบายความร้อน 3D Dual-Vapor Chamber มอบความลื่นไหลและประสิทธิภาพสูงสุดในทุกการประมวลผล "
    "และอัดแน่นด้วยแบตเตอรี่ความจุใหญ่ 4,780 mAh รองรับชาร์จไว 67W ตอบโจทย์การใช้งานระดับโปรได้อย่างมั่นใจตลอดทั้งวันครับ"
)

print(f"Generating 60s voiceover with Gemini Flash TTS (Fenrir)... Text length: {len(SCRIPT_60S)} chars")
GeminiFlashTTSEngine.generate_speech(
    text=SCRIPT_60S,
    output_path=str(wav_path),
    voice_preset="gemini_fenrir_male_strong",
    ad_tone="commercial_premium",
    speed=1.0
)

with wave.open(str(wav_path), "r") as f:
    dur = f.getnframes() / float(f.getframerate())
print(f"Generated Audio Duration: {dur:.2f} seconds")
