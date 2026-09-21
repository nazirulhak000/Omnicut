"""
Reorganize .tmp into a spotless Product-Centric structure:
.tmp/Products/<Product_Name>/
    01_Raw/
        videos/
        photos/
        metadata/
    02_Workspace/
        audio/
        subtitles/
        temp_cuts/
        qa_frames/
        draft_versions/
    03_Export/
        <Product_Name>_60s_Master.mp4
        thumbnail_cover.jpg
        export_summary.json
"""
import os
import shutil
import json
from pathlib import Path

PROJECT_ROOT = Path("d:/Winona/Programmer/Capcut")
TMP = PROJECT_ROOT / ".tmp"

PRODUCT_NAME = "Xiaomi_MIX_Flip"
PRODUCT_DIR = TMP / "Products" / PRODUCT_NAME

DIR_RAW = PRODUCT_DIR / "01_Raw"
DIR_RAW_VIDEOS = DIR_RAW / "videos"
DIR_RAW_PHOTOS = DIR_RAW / "photos"
DIR_RAW_META = DIR_RAW / "metadata"

DIR_WORKSPACE = PRODUCT_DIR / "02_Workspace"
DIR_AUDIO = DIR_WORKSPACE / "audio"
DIR_SUBS = DIR_WORKSPACE / "subtitles"
DIR_CUTS = DIR_WORKSPACE / "temp_cuts"
DIR_QA = DIR_WORKSPACE / "qa_frames"
DIR_DRAFTS = DIR_WORKSPACE / "draft_versions"

DIR_EXPORT = PRODUCT_DIR / "03_Export"

def main():
    print("--- Starting Product-Centric Reorganization ---")
    
    # 1. Create target directories
    for d in [DIR_RAW_VIDEOS, DIR_RAW_PHOTOS, DIR_RAW_META,
             DIR_AUDIO, DIR_SUBS, DIR_CUTS, DIR_QA, DIR_DRAFTS,
             DIR_EXPORT]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 2. Migrate Raw Assets from .tmp/01_Products/Xiaomi_Models/Xiaomi_xiaomi_mix_flip
    old_raw_dir = TMP / "01_Products" / "Xiaomi_Models" / "Xiaomi_xiaomi_mix_flip"
    if old_raw_dir.exists():
        print(f"Migrating raw assets from {old_raw_dir}...")
        # Photos
        old_photos = old_raw_dir / "photos"
        if old_photos.exists():
            for f in old_photos.glob("*"):
                if f.is_file():
                    shutil.copy2(f, DIR_RAW_PHOTOS / f.name)
        
        # Videos & Inserts
        old_video_clean = old_raw_dir / "video_clean_1080p.mp4"
        if old_video_clean.exists():
            shutil.copy2(old_video_clean, DIR_RAW_VIDEOS / "video_clean_1080p.mp4")
            
        old_inserts = old_raw_dir / "inserts"
        if old_inserts.exists():
            for f in old_inserts.glob("*"):
                if f.is_file():
                    shutil.copy2(f, DIR_RAW_VIDEOS / f.name)
                    
        old_videos = old_raw_dir / "video"
        if old_videos.exists():
            for f in old_videos.glob("*"):
                if f.is_file():
                    shutil.copy2(f, DIR_RAW_VIDEOS / f.name)
                    
        # Metadata
        for meta_file in ["info.json", "sources_manifest.json"]:
            p = old_raw_dir / meta_file
            if p.exists():
                shutil.copy2(p, DIR_RAW_META / meta_file)
        print("Raw assets migrated successfully.")

    # 3. Categorize & Migrate files from .tmp/03_Outputs/Master_Clips_and_Previews
    old_outputs = TMP / "03_Outputs" / "Master_Clips_and_Previews"
    if old_outputs.exists():
        print(f"Migrating files from {old_outputs}...")
        
        # Master Video to 03_Export
        master_src = old_outputs / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
        if master_src.exists():
            target_master = DIR_EXPORT / "Xiaomi_MIX_Flip_60s_Master.mp4"
            shutil.copy2(master_src, target_master)
            print(f"  -> [03_Export] {target_master.name} ({target_master.stat().st_size / (1024*1024):.2f} MB)")
            
            # Create thumbnail cover
            cover_src = old_outputs / "shot01_hook_intro_purple.jpg"
            if cover_src.exists():
                shutil.copy2(cover_src, DIR_EXPORT / "thumbnail_cover.jpg")
                
            # Create export summary json
            summary = {
                "product_name": "Xiaomi MIX Flip",
                "export_filename": "Xiaomi_MIX_Flip_60s_Master.mp4",
                "format": "9:16 (1080x1920)",
                "fps": 30.0,
                "duration_seconds": 60.0,
                "subtitle_font": "Mali-Bold 88px",
                "bgm": "tiktok_upbeat_bgm.wav",
                "voice": "Fenrir (commercial_premium)",
                "status": "APPROVED_MASTER"
            }
            with open(DIR_EXPORT / "export_summary.json", "w", encoding="utf-8") as sf:
                json.dump(summary, sf, indent=2, ensure_ascii=False)
                
        # Move all other files into 02_Workspace
        for item in old_outputs.iterdir():
            name = item.name
            
            # Skip if it's the master itself (we already copied it as Master.mp4, but we can also archive original name in drafts)
            if name == "demo_xiaomi_mix_flip_cinematic_60s.mp4":
                shutil.move(str(item), str(DIR_DRAFTS / name))
                continue
                
            # Draft versions
            if name in ["demo_xiaomi_mix_flip_60s_review.mp4",
                        "demo_xiaomi_mix_flip_character_bounce.mp4",
                        "demo_xiaomi_mix_flip_techmx.mp4"]:
                shutil.move(str(item), str(DIR_DRAFTS / name))
                print(f"  -> [draft_versions] {name}")
                continue
                
            # Audio
            if item.suffix.lower() in [".wav", ".mp3", ".aac"] or "voice" in name.lower():
                shutil.move(str(item), str(DIR_AUDIO / name))
                print(f"  -> [audio] {name}")
                continue
                
            # Subtitles & Timings
            if item.suffix.lower() == ".ass" or "whisper" in name.lower() or "timing" in name.lower():
                shutil.move(str(item), str(DIR_SUBS / name))
                print(f"  -> [subtitles] {name}")
                continue
                
            # Video segments / cuts
            if name.startswith("seg") or name in ["montage_60s_raw.mp4", "test_blur_bg.mp4", "concat_master.txt", "hyperframes_spec_card.webm", "test_kinetic_callout.webm"]:
                shutil.move(str(item), str(DIR_CUTS / name))
                print(f"  -> [temp_cuts] {name}")
                continue
                
            # QA Frames & Directories
            if item.is_dir():
                if name in ["hf_card_build"]:
                    shutil.move(str(item), str(DIR_CUTS / name))
                else:
                    shutil.move(str(item), str(DIR_QA / name))
                print(f"  -> [qa_frames/dir] {name}")
                continue
                
            if item.suffix.lower() in [".jpg", ".png", ".webp"]:
                shutil.move(str(item), str(DIR_QA / name))
                print(f"  -> [qa_frames] {name}")
                continue
                
            # Any remaining file
            shutil.move(str(item), str(DIR_WORKSPACE / name))
            print(f"  -> [workspace_misc] {name}")
            
    # 4. Remove empty old_outputs directory
    if old_outputs.exists() and not any(old_outputs.iterdir()):
        old_outputs.rmdir()
        print(f"Cleaned up empty directory: {old_outputs}")
        
    parent_03 = TMP / "03_Outputs"
    if parent_03.exists() and not any(parent_03.iterdir()):
        parent_03.rmdir()
        print(f"Cleaned up empty directory: {parent_03}")
        
    # Also clean up old .tmp/01_Products if we want it completely moved
    old_xiaomi_models = TMP / "01_Products" / "Xiaomi_Models" / "Xiaomi_xiaomi_mix_flip"
    if old_xiaomi_models.exists():
        shutil.rmtree(old_xiaomi_models)
        print(f"Cleaned up old raw folder: {old_xiaomi_models}")
    if (TMP / "01_Products" / "Xiaomi_Models").exists() and not any((TMP / "01_Products" / "Xiaomi_Models").iterdir()):
        (TMP / "01_Products" / "Xiaomi_Models").rmdir()
    if (TMP / "01_Products").exists() and not any((TMP / "01_Products").iterdir()):
        (TMP / "01_Products").rmdir()

    print("\n--- Reorganization Completed Successfully ---")

if __name__ == "__main__":
    main()
