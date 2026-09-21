import os
import stat
import subprocess
import shutil
from pathlib import Path

tmp_dir = Path(r'd:\Winona\Programmer\Capcut\.tmp')

def remove_readonly(func, path, exc_info):
    # Clear read-only bit and retry
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def delete_dir_safely(dir_path):
    if not dir_path.exists():
        return 0
    size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
    # Try rmdir /s /q first for speed and handling read-only git files
    cmd = f'cmd /c rmdir /s /q "{dir_path}"'
    res = subprocess.run(cmd, shell=True, capture_output=True)
    if dir_path.exists():
        shutil.rmtree(dir_path, onerror=remove_readonly)
    return size

# 1. Junk directories to delete completely
junk_dirs = [
    tmp_dir / 'full-gate-20260915',
    tmp_dir / 'full-gate-20260915-v2',
    tmp_dir / 'gadget_review_roughcuts_20260919',
]

deleted_dir_count = 0
deleted_dir_bytes = 0

for jd in junk_dirs:
    if jd.exists():
        sz = delete_dir_safely(jd)
        deleted_dir_bytes += sz
        deleted_dir_count += 1
        print(f"[DELETED DIR] {jd.name} ({sz / (1024*1024):.2f} MB)")

# 2. Junk files to delete in .tmp root
junk_file_patterns = [
    'alphaextract-', 'scrim-', 'parity-', 'cutout_', 'font_debug',
    'frame_rendered', 'backfill_', 'hist_', 'open_', 'round_',
    'todo_', 'verify_', 'all_fonts', 'prompt-emoji', 'test_',
    'thai_stacked', 'bilibili_su7', 'xiaomi_17t_1080p', 'clean_grid_composite',
    'mix_flip_frame_10s', 'mix_flip_frame_25s'
]

deleted_file_count = 0
deleted_file_bytes = 0

for item in list(tmp_dir.iterdir()):
    if item.is_file():
        is_junk = any(pat in item.name for pat in junk_file_patterns) or item.name == 'test.png'
        if is_junk:
            sz = item.stat().st_size
            deleted_file_bytes += sz
            item.unlink()
            deleted_file_count += 1
            print(f"[DELETED FILE] {item.name}")

# Move remaining loose video if needed
mix_flip_loose = tmp_dir / 'xiaomi_mix_flip_1080p.mp4'
if mix_flip_loose.exists():
    target_dest = tmp_dir / 'gadget_products' / 'Xiaomi_xiaomi_mix_flip' / 'video' / 'xiaomi_mix_flip_1080p.mp4'
    if not target_dest.exists():
        target_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(mix_flip_loose), str(target_dest))
        print("[MOVED] xiaomi_mix_flip_1080p.mp4 -> gadget_products/.../video/")
    else:
        mix_flip_loose.unlink()
        print("[CLEANED DUPLICATE] xiaomi_mix_flip_1080p.mp4")

# 3. Create categorized subfolders in .tmp
cat_products = tmp_dir / '01_Products'
cat_sources = tmp_dir / '02_Sources'
cat_outputs = tmp_dir / '03_Outputs'
cat_sandbox = tmp_dir / '04_Sandbox'

for c in [cat_products, cat_sources, cat_outputs, cat_sandbox]:
    c.mkdir(parents=True, exist_ok=True)

# Map existing folders to categories
moves = [
    (tmp_dir / 'gadget_products', cat_products / 'Xiaomi_Models'),
    (tmp_dir / 'gadget_native_sources_20260919', cat_sources / 'Native_1080p_Sources'),
    (tmp_dir / 'gadget_news_sources_20260919', cat_sources / 'News_Sources'),
    (tmp_dir / 'gadget_product_segments_20260919', cat_sources / 'Product_Segments'),
    (tmp_dir / 'gadget_source_slices_20260919', cat_sources / 'Source_Slices'),
    (tmp_dir / 'gadget_demo', cat_outputs / 'Master_Clips_and_Previews'),
    (tmp_dir / 'hf_test', cat_sandbox / 'Hyperframes_Test'),
    (tmp_dir / 'remix_xiaomi_20260919', cat_sandbox / 'Remix_Prototype'),
    (tmp_dir / 'bg-isolation-investigation', cat_sandbox / 'BG_Isolation_Investigation'),
]

for src, dst in moves:
    if src.exists() and src.is_dir():
        if dst.exists():
            shutil.rmtree(dst, onerror=remove_readonly)
        shutil.move(str(src), str(dst))
        print(f"[CATEGORIZED] {src.name} -> {dst.parent.name}/{dst.name}")

total_freed = (deleted_dir_bytes + deleted_file_bytes) / (1024 * 1024)
print(f"\nSummary: Deleted {deleted_dir_count} junk directories and {deleted_file_count} junk files.")
print(f"Total space freed: {total_freed:.2f} MB.")
