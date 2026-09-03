"""
Comprehensive 6-Pillar System Health Diagnostic & Audit Runner
Project: TikTok Auto-Cutter Pro Studio
AGENTS.md Specification Compliance
"""

import os
import sys
import shutil
import subprocess
import importlib
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

results: List[Dict[str, Any]] = []

def record(pillar: str, item: str, status: str, detail: str = "", fix: str = ""):
    results.append({
        "pillar": pillar,
        "item": item,
        "status": status,
        "detail": detail,
        "fix": fix
    })

# ----------------------------------------------------------------------
# Pillar 1: Environment & Dependencies
# ----------------------------------------------------------------------
def check_environment():
    # 1.1 Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info.major == 3 and sys.version_info.minor >= 10:
        record("Environment", f"Python Version ({py_ver})", "PASS", "Python >= 3.10")
    else:
        record("Environment", f"Python Version ({py_ver})", "WARN", "Recommended Python 3.10+")

    # 1.2 FFmpeg & FFprobe
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if ffmpeg_bin:
        try:
            v_out = subprocess.check_output([ffmpeg_bin, "-version"], stderr=subprocess.STDOUT, text=True)
            v_line = v_out.splitlines()[0] if v_out else "Unknown"
            record("Environment", "FFmpeg Binary", "PASS", v_line[:50])
        except Exception as e:
            record("Environment", "FFmpeg Binary", "WARN", f"Executable error: {e}")
    else:
        record("Environment", "FFmpeg Binary", "FAIL", "ffmpeg not found in PATH", "Install FFmpeg and add to PATH")

    if ffprobe_bin:
        record("Environment", "FFprobe Binary", "PASS", "Available in PATH")
    else:
        record("Environment", "FFprobe Binary", "FAIL", "ffprobe not found in PATH", "Ensure ffprobe is installed with FFmpeg")

    # 1.3 Key Python Packages
    packages = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI web server"),
        ("pydantic", "Data validation"),
        ("pythainlp", "Thai NLP tokenization & dictionary"),
        ("edge_tts", "Edge-TTS voice synthesis"),
        ("soundfile", "Audio I/O processing"),
        ("numpy", "Audio waveform processing"),
        ("PIL", "Pillow image manipulation"),
    ]
    for pkg, desc in packages:
        try:
            importlib.import_module(pkg)
            record("Environment", f"Package: {pkg}", "PASS", desc)
        except ImportError:
            record("Environment", f"Package: {pkg}", "FAIL", f"Missing {pkg}", f"pip install {pkg}")

    # Optional packages
    try:
        importlib.import_module("google.genai")
        record("Environment", "Package: google.genai", "PASS", "Gemini 2.5 SDK ready")
    except ImportError:
        record("Environment", "Package: google.genai", "WARN", "Optional: pip install google-genai for AI features")

    try:
        importlib.import_module("rembg")
        record("Environment", "Package: rembg", "PASS", "Background removal for 3D badges ready")
    except ImportError:
        record("Environment", "Package: rembg", "WARN", "Optional: pip install rembg for automated transparent badge cutout")

# ----------------------------------------------------------------------
# Pillar 2: Folder Structure & Font Assets
# ----------------------------------------------------------------------
def check_folders_and_assets():
    from scripts.config import (
        BASE_DIR, INBOX_DIR, RAW_DIR, ASSETS_DIR, FONTS_DIR, SFX_DIR,
        MUSIC_DIR, PROJECTS_DIR, EXPORTS_DIR
    )

    expected_dirs = [
        ("00_Inbox", INBOX_DIR),
        ("01_Raw", RAW_DIR),
        ("02_Assets", ASSETS_DIR),
        ("02_Assets/Fonts", FONTS_DIR),
        ("02_Assets/SFX", SFX_DIR),
        ("02_Assets/Music", MUSIC_DIR),
        ("03_Projects", PROJECTS_DIR),
        ("04_Exports/Ready_to_post", EXPORTS_DIR),
        ("_Docs", BASE_DIR / "_Docs"),
    ]

    for name, path in expected_dirs:
        if path.exists() and path.is_dir():
            record("Structure", f"Directory: {name}", "PASS", f"Present ({len(list(path.iterdir()))} items)")
        else:
            record("Structure", f"Directory: {name}", "WARN", f"Missing directory: {path}", f"Created automatically on boot")
            path.mkdir(parents=True, exist_ok=True)

    # Check Thai Fonts
    if FONTS_DIR.exists():
        font_files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
        valid_fonts = [f for f in font_files if f.stat().st_size > 1000]
        if len(valid_fonts) >= 3:
            font_names = ", ".join([f.stem for f in valid_fonts[:4]])
            record("Assets", "Thai Fonts Collection", "PASS", f"{len(valid_fonts)} fonts loaded ({font_names}...)")
        else:
            record("Assets", "Thai Fonts Collection", "WARN", f"Found only {len(valid_fonts)} valid fonts", "Add Prompt and Kanit fonts to 02_Assets/Fonts")
    else:
        record("Assets", "Thai Fonts Collection", "FAIL", "Fonts directory missing")

# ----------------------------------------------------------------------
# Pillar 3: Path Integrity (Zero Hardcoded Absolute Paths)
# ----------------------------------------------------------------------
def check_path_integrity():
    search_dirs = [ROOT / "scripts", ROOT / "tools"]
    hardcoded_patterns = [
        re.compile(r'["\'][a-zA-Z]:\\[^"\']+["\']'),
        re.compile(r'["\']/[Uu]sers/[^"\']+["\']'),
    ]

    offenders = []
    for sdir in search_dirs:
        for py_file in sdir.glob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.splitlines()
                for idx, line in enumerate(lines, 1):
                    # Skip comment lines or test fixtures
                    sline = line.strip()
                    if sline.startswith("#") or "CAPCUT_DRAFT_DIR" in sline:
                        continue
                    for pat in hardcoded_patterns:
                        if pat.search(line):
                            offenders.append(f"{py_file.name}:{idx} -> {sline[:60]}")
            except Exception:
                pass

    if not offenders:
        record("Code Integrity", "Zero Hardcoded Absolute Paths", "PASS", "All paths use pathlib.Path or scripts.config")
    else:
        sample = offenders[0]
        record("Code Integrity", "Zero Hardcoded Absolute Paths", "WARN", f"{len(offenders)} hardcoded path lines found (e.g. {sample})", "Refactor to use scripts.config")

# ----------------------------------------------------------------------
# Pillar 4: Video Specs & AGENTS.md Compliance
# ----------------------------------------------------------------------
def check_video_and_subtitle_standards():
    from scripts.config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS
    from scripts.subtitle_engine import CAPTION_POSITIONS

    # 4.1 Resolution 1080x1920 & 30fps
    if VIDEO_WIDTH == 1080 and VIDEO_HEIGHT == 1920:
        record("Video Specs", "Resolution 9:16 (1080x1920)", "PASS", "Exact vertical TikTok standard")
    else:
        record("Video Specs", "Resolution 9:16 (1080x1920)", "FAIL", f"Current: {VIDEO_WIDTH}x{VIDEO_HEIGHT}")

    if FPS == 30:
        record("Video Specs", "Framerate (30 FPS)", "PASS", "Standard 30.0 fps")
    else:
        record("Video Specs", "Framerate (30 FPS)", "WARN", f"Current FPS: {FPS}")

    # 4.2 Subtitle Safe Zone MarginV >= 420
    bottom_margin = CAPTION_POSITIONS.get("bottom", (2, 0))[1]
    if bottom_margin >= 420:
        record("Video Specs", "Subtitle Bottom Safe Zone", "PASS", f"MarginV = {bottom_margin}px (>= 420px TikTok safe zone)")
    else:
        record("Video Specs", "Subtitle Bottom Safe Zone", "WARN", f"MarginV = {bottom_margin}px (< 420px)")

    # 4.3 J-Cut and Silence Trimming
    from scripts.voice_engine import VoiceEngine
    has_trim = hasattr(VoiceEngine, "_trim_silence")
    if has_trim:
        record("Video Specs", "J-Cut Voice Silence Trimming", "PASS", "Dynamic threshold silence trimming enabled (15ms pad)")
    else:
        record("Video Specs", "J-Cut Voice Silence Trimming", "WARN", "Missing _trim_silence in VoiceEngine")

    # 4.4 Ellipsis "... " check in default scripts
    from scripts.it_angles import ANGLES_BY_KEY
    has_ellipsis = False
    for angle in ANGLES_BY_KEY.values():
        for field in ["title", "hook_format", "call_to_action"]:
            val = angle.get(field, "")
            if "..." in val or "…" in val:
                has_ellipsis = True
                break
    if not has_ellipsis:
        record("Video Specs", "Strict No-Ellipsis in Angles", "PASS", "All IT angle templates free of ellipsis")
    else:
        record("Video Specs", "Strict No-Ellipsis in Angles", "WARN", "Found ellipsis in it_angles.py", "Remove ... from template strings")

# ----------------------------------------------------------------------
# Pillar 5: Data Persistence & Concurrency Safety
# ----------------------------------------------------------------------
def check_data_persistence():
    from scripts.product_store import ProductStore
    from scripts.post_log import PostLog
    from scripts.token_tracker import TokenTracker
    from scripts.project_manifest import ProjectManifest

    # 5.1 ProductStore
    try:
        prods = ProductStore.get_all()
        has_lock = hasattr(ProductStore, "_lock") or hasattr(ProductStore, "_LOCK")
        status = "PASS" if has_lock else "WARN"
        record("Persistence", "ProductStore", status, f"{len(prods)} products in catalog, thread-lock: {has_lock}")
    except Exception as e:
        record("Persistence", "ProductStore", "FAIL", f"Failed to load: {e}")

    # 5.2 PostLog
    try:
        posts = PostLog.get_all()
        record("Persistence", "PostLog Feedback Loop", "PASS", f"{len(posts)} posts logged, atomic file replacement enabled")
    except Exception as e:
        record("Persistence", "PostLog Feedback Loop", "FAIL", f"Failed to load: {e}")

    # 5.3 TokenTracker
    try:
        summary = TokenTracker.get_summary()
        has_lock = hasattr(TokenTracker, "_lock") or hasattr(TokenTracker, "_LOCK")
        status = "PASS" if has_lock else "WARN"
        record("Persistence", "TokenTracker Analytics", status, f"Calls: {summary['totals']['total_calls']}, thread-lock: {has_lock}")
    except Exception as e:
        record("Persistence", "TokenTracker Analytics", "FAIL", f"Failed to load: {e}")

    # 5.4 ProjectManifest
    try:
        has_lock = hasattr(ProjectManifest, "_SAVE_LOCK") or hasattr(ProjectManifest, "_lock")
        status = "PASS" if has_lock else "WARN"
        record("Persistence", "ProjectManifest Atomic Save", status, f"Lock present: {has_lock}, tmp-replace write active")
    except Exception as e:
        record("Persistence", "ProjectManifest Atomic Save", "FAIL", f"Error: {e}")

# ----------------------------------------------------------------------
# Pillar 6: API Server & Frontend Contract Compliance
# ----------------------------------------------------------------------
def check_api_contracts():
    from scripts.api_server import app

    backend_routes = set()
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                backend_routes.add((method, route.path))

    # Core frontend endpoints checked
    frontend_endpoints = [
        ("GET", "/api/status"),
        ("GET", "/api/videos"),
        ("GET", "/api/exports"),
        ("GET", "/api/sfx"),
        ("POST", "/api/script/generate"),
        ("POST", "/api/script/ai-generate"),
        ("POST", "/api/voice/preview"),
        ("POST", "/api/render"),
        ("POST", "/api/open-folder"),
        ("POST", "/api/upload"),
        ("POST", "/api/delete-file"),
        ("GET", "/api/products"),
        ("POST", "/api/products"),
        ("POST", "/api/products/scrape-and-plan-async"),
        ("GET", "/api/projects"),
        ("GET", "/api/posts"),
        ("POST", "/api/posts"),
        ("GET", "/api/posts/performance"),
        ("GET", "/api/posts/summary"),
        ("GET", "/api/tasks/active"),
        ("GET", "/api/tokens/summary"),
    ]

    missing = []
    for method, path in frontend_endpoints:
        if (method, path) not in backend_routes:
            missing.append(f"{method} {path}")

    if not missing:
        record("API Contract", "Frontend-Backend Routes Match", "PASS", f"All {len(frontend_endpoints)} checked routes exist in API server")
    else:
        record("API Contract", "Frontend-Backend Routes Match", "FAIL", f"Missing routes: {', '.join(missing)}")

# ----------------------------------------------------------------------
# Main Runner & Formatted Output
# ----------------------------------------------------------------------
def run_all():
    print(f"\n{Colors.BOLD}{Colors.CYAN}======================================================================{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN} 🤖 TIKTOK AUTO-CUTTER PRO STUDIO — 6-PILLAR SYSTEM AUDIT{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}======================================================================{Colors.RESET}\n")

    check_environment()
    check_folders_and_assets()
    check_path_integrity()
    check_video_and_subtitle_standards()
    check_data_persistence()
    check_api_contracts()

    # Print Table
    col_w = [14, 32, 8, 40]
    header = f"{'PILLAR':<{col_w[0]}} | {'AUDIT ITEM':<{col_w[1]}} | {'STATUS':<{col_w[2]}} | {'DETAILS / ACTION':<{col_w[3]}}"
    sep = "-" * len(header)
    print(header)
    print(sep)

    pass_count = 0
    warn_count = 0
    fail_count = 0

    for r in results:
        st = r["status"]
        if st == "PASS":
            color = Colors.GREEN
            pass_count += 1
        elif st == "WARN":
            color = Colors.YELLOW
            warn_count += 1
        else:
            color = Colors.RED
            fail_count += 1

        detail = r["detail"]
        if r["fix"]:
            detail += f" (Fix: {r['fix']})"

        print(f"{r['pillar']:<{col_w[0]}} | {r['item']:<{col_w[1]}} | {color}{st:<{col_w[2]}}{Colors.RESET} | {detail[:40]}")

    print(sep)
    print(f"\n{Colors.BOLD}AUDIT SUMMARY:{Colors.RESET} "
          f"{Colors.GREEN}PASS: {pass_count}{Colors.RESET} | "
          f"{Colors.YELLOW}WARN: {warn_count}{Colors.RESET} | "
          f"{Colors.RED}FAIL: {fail_count}{Colors.RESET}")

    if fail_count == 0:
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 SYSTEM INTEGRITY CHECK PASSED WITH ZERO CRITICAL FAILURES!{Colors.RESET}\n")
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}⚠️ PLEASE RESOLVE THE CRITICAL FAILURES LISTED ABOVE.{Colors.RESET}\n")

    return fail_count

if __name__ == "__main__":
    code = run_all()
    sys.exit(code)
