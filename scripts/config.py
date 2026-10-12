import os
import re
from pathlib import Path
from typing import List

# Source and data roots are separate so tests can isolate storage before imports.
# With no override, the established single-workspace layout is unchanged.
SOURCE_ROOT = Path(__file__).resolve().parent.parent
_data_root_override = os.environ.get("OMNICUT_DATA_ROOT", "").strip()
BASE_DIR = Path(_data_root_override).expanduser().resolve() if _data_root_override else SOURCE_ROOT

# Load .env into os.environ if present
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    try:
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip()
                if _k and _k not in os.environ:
                    os.environ[_k] = _v
    except Exception:
        pass


def get_gemini_api_keys() -> List[str]:
    """
    Returns all configured Gemini API keys from environment and .env in priority order:
    1. GEMINI_API_KEY / GEMINI_API_KEY_1
    2. GEMINI_API_KEY_2
    3. GEMINI_API_KEY_3
    ...
    N. GEMINI_API_KEY_N
    followed by any other GEMINI_API_KEY* variables.
    """
    raw_candidates = {}

    # 1. Read from .env file directly (always up-to-date)
    if _env_file.exists():
        try:
            for line in _env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if "GEMINI_API_KEY" in k and v:
                        raw_candidates[k] = v
        except Exception:
            pass

    # 2. Read from os.environ (overrides .env)
    for k, v in os.environ.items():
        if "GEMINI_API_KEY" in k and v.strip():
            raw_candidates[k] = v.strip()

    def _key_sort_order(name: str) -> int:
        clean = name.upper()
        if clean in ("GEMINI_API_KEY", "GEMINI_API_KEY_1"):
            return 1
        m = re.match(r"GEMINI_API_KEY_(\d+)$", clean)
        if m:
            return int(m.group(1))
        return 9999

    sorted_names = sorted(raw_candidates.keys(), key=_key_sort_order)
    keys = []
    for name in sorted_names:
        val = raw_candidates[name]
        if val and val not in keys:
            keys.append(val)
    return keys


def get_typesafe_api_key() -> str:
    """Returns the configured TypeSafe API key from environment or .env."""
    return os.environ.get("TYPESAFE_API_KEY", "").strip()


INBOX_DIR = BASE_DIR / "00_Inbox"
RAW_DIR = BASE_DIR / "01_Raw"
ASSETS_DIR = BASE_DIR / "02_Assets"
PROJECTS_DIR = BASE_DIR / "03_Projects"
EXPORTS_DIR = BASE_DIR / "04_Exports" / "Ready_to_post"
COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"
ARCHIVE_DIR = BASE_DIR / "06_Archive"

FONTS_DIR = ASSETS_DIR / "Fonts"
SFX_DIR = ASSETS_DIR / "SFX"
MUSIC_DIR = ASSETS_DIR / "Music"
STICKERS_DIR = ASSETS_DIR / "Stickers_Memes"
LUTS_DIR = ASSETS_DIR / "LUTs_ColorPresets"
EFFECTS_DIR = ASSETS_DIR / "Effects"


def asset_relative_path(value: str | Path, *, data_assets_root: Path | None = None) -> Path:
    """Catalog URL path for data assets or read-only packaged source assets.

    Generated caches use BASE_DIR. Packaged bytes under SOURCE_ROOT/02_Assets
    can be read independently, while arbitrary external paths are rejected.
    """
    path = Path(value).resolve()
    assets = (data_assets_root or ASSETS_DIR).resolve()
    try:
        path.relative_to(assets)
        return path.relative_to(assets.parent)
    except ValueError:
        path.relative_to((SOURCE_ROOT / "02_Assets").resolve())
        return path.relative_to(SOURCE_ROOT.resolve())

# Ensure directories exist
for p in [INBOX_DIR, RAW_DIR, ASSETS_DIR, PROJECTS_DIR, EXPORTS_DIR, COVERS_DIR, ARCHIVE_DIR, FONTS_DIR, SFX_DIR, MUSIC_DIR, STICKERS_DIR, LUTS_DIR, EFFECTS_DIR]:
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
J_CUT_OFFSET_SECONDS = 0.18  # J-Cut timing: เสียงประโยคใหม่มาก่อนภาพ 180ms เพื่อความลื่นไหลและเร่ง Retention

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
# Mix levels. These are the values the render actually uses -- sfx_manager.py
# takes its defaults from here rather than repeating literals, and the preview
# mirrors them in SequencePlayer.jsx AUDIO_MIX (guarded by
# tests/test_preview_render_parity.py). They used to disagree: this file said
# 0.15/0.6 while the mix ran 0.12/0.28, and AGENTS.md documented the numbers
# nothing used.
BGM_VOLUME = 0.12    # -18dB, a bed under the voice
VOICE_VOLUME = 1.0
SFX_VOLUME = 0.28    # -11dB, present but not startling

# Multi-channel foundation (P1, see _Docs/Plans/ADR_MULTI_CHANNEL_20261010.md)
# The registry is the single source of truth for channel profiles.  Nothing
# here creates the file: reading a missing registry yields an in-memory
# registry holding only the implicit ``main`` channel.
CHANNELS_FILE = BASE_DIR / "_Docs" / "channels.json"
# Root that channel avatar_asset_path values are relative to (containment root).
CHANNELS_PROJECT_ROOT = BASE_DIR
DEFAULT_CHANNEL_ID = "main"
HYPERFRAMES_STUDIO_DIR = PROJECTS_DIR / "_HyperFrames_Studio"
MULTI_CHANNEL_STRICT_ENV = "OMNICUT_MULTI_CHANNEL_STRICT"
_TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}


def is_multi_channel_strict() -> bool:
    """Return whether strict multi-channel mode is on.

    Evaluated on every call (never cached at import) so tests and a restarted
    server pick up ``OMNICUT_MULTI_CHANNEL_STRICT`` changes.  Default: off =
    single-channel compatibility mode (requests without a channel header
    resolve to ``main``).
    """
    return os.environ.get(MULTI_CHANNEL_STRICT_ENV, "").strip().lower() in _TRUTHY_ENV_VALUES
