import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = BASE_DIR / "00_Inbox"
RAW_DIR = BASE_DIR / "01_Raw"
ASSETS_DIR = BASE_DIR / "02_Assets"
PROJECTS_DIR = BASE_DIR / "03_Projects"
EXPORTS_DIR = BASE_DIR / "04_Exports" / "Ready_to_post"
ARCHIVE_DIR = BASE_DIR / "06_Archive"

FONTS_DIR = ASSETS_DIR / "Fonts"
SFX_DIR = ASSETS_DIR / "SFX"
MUSIC_DIR = ASSETS_DIR / "Music"
STICKERS_DIR = ASSETS_DIR / "Stickers_Memes"
LUTS_DIR = ASSETS_DIR / "LUTs_ColorPresets"

# Ensure directories exist
for p in [INBOX_DIR, RAW_DIR, ASSETS_DIR, PROJECTS_DIR, EXPORTS_DIR, ARCHIVE_DIR, FONTS_DIR, SFX_DIR, MUSIC_DIR, STICKERS_DIR, LUTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# CapCut Draft Directory on Windows
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
CAPCUT_DRAFT_DIR = Path(LOCALAPPDATA) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"

# Video Settings (TikTok Standard 9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
MIN_SHOT_DURATION = 1.5  # seconds per cut
MAX_SHOT_DURATION = 2.5  # seconds per cut

# Subtitle & Font Settings (TikTok Standard)
DEFAULT_FONT_PATH = FONTS_DIR / "Kanit-Black.ttf"
DEFAULT_FONT_NAME = "Kanit"

# Edge-TTS Voices
VOICES = {
    "female": "th-TH-PremwadeeNeural",  # เสียงผู้หญิงรีวิว สดใส
    "male": "th-TH-NiwatNeural",        # เสียงผู้ชาย มั่นใจ เป็นทางการ/น่าเชื่อถือ
}
DEFAULT_VOICE = "female"
DEFAULT_VOICE_RATE = "+15%" # TikTok fast-paced speaking rate
DEFAULT_VOICE_PITCH = "+0Hz"

# Audio Settings
BGM_VOLUME = 0.15 # -16dB
VOICE_VOLUME = 1.0
SFX_VOLUME = 0.6
