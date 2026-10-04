import argparse
import os
import stat
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TMP_DIR = PROJECT_ROOT / '.tmp'


def remove_readonly(func, path, exc_info):
    """Clear read-only bit and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def delete_dir_safely(dir_path: Path, dry_run: bool = False) -> int:
    if not dir_path.exists():
        return 0
    size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
    if dry_run:
        return size
    cmd = f'cmd /c rmdir /s /q "{dir_path}"'
    subprocess.run(cmd, shell=True, capture_output=True)
    if dir_path.exists():
        shutil.rmtree(dir_path, onerror=remove_readonly)
    return size


def clean_and_organize_tmp(tmp_dir: Path = None, dry_run: bool = False) -> dict:
    if tmp_dir is None:
        tmp_dir = DEFAULT_TMP_DIR

    if not tmp_dir.exists():
        print(f"[INFO] .tmp directory not found: {tmp_dir}")
        return {"deleted_dir_count": 0, "deleted_file_count": 0, "freed_bytes": 0}

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
            sz = delete_dir_safely(jd, dry_run=dry_run)
            deleted_dir_bytes += sz
            deleted_dir_count += 1
            prefix = "[DRY-RUN WOULD DELETE DIR]" if dry_run else "[DELETED DIR]"
            print(f"{prefix} {jd.name} ({sz / (1024*1024):.2f} MB)")

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
                deleted_file_count += 1
                if not dry_run:
                    item.unlink()
                prefix = "[DRY-RUN WOULD DELETE FILE]" if dry_run else "[DELETED FILE]"
                print(f"{prefix} {item.name}")

    # Move remaining loose video if needed
    mix_flip_loose = tmp_dir / 'xiaomi_mix_flip_1080p.mp4'
    if mix_flip_loose.exists():
        target_dest = tmp_dir / 'gadget_products' / 'Xiaomi_xiaomi_mix_flip' / 'video' / 'xiaomi_mix_flip_1080p.mp4'
        if not target_dest.exists():
            if not dry_run:
                target_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(mix_flip_loose), str(target_dest))
            prefix = "[DRY-RUN WOULD MOVE]" if dry_run else "[MOVED]"
            print(f"{prefix} xiaomi_mix_flip_1080p.mp4 -> gadget_products/.../video/")
        else:
            if not dry_run:
                mix_flip_loose.unlink()
            prefix = "[DRY-RUN WOULD CLEAN DUPLICATE]" if dry_run else "[CLEANED DUPLICATE]"
            print(f"{prefix} xiaomi_mix_flip_1080p.mp4")

    # 3. Create categorized subfolders in .tmp
    cat_products = tmp_dir / '01_Products'
    cat_sources = tmp_dir / '02_Sources'
    cat_outputs = tmp_dir / '03_Outputs'
    cat_sandbox = tmp_dir / '04_Sandbox'

    if not dry_run:
        for c in [cat_products, cat_sources, cat_outputs, cat_sandbox]:
            c.mkdir(parents=True, exist_ok=True)

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
            if not dry_run:
                if dst.exists():
                    shutil.rmtree(dst, onerror=remove_readonly)
                shutil.move(str(src), str(dst))
            prefix = "[DRY-RUN WOULD CATEGORIZE]" if dry_run else "[CATEGORIZED]"
            print(f"{prefix} {src.name} -> {dst.parent.name}/{dst.name}")

    total_freed_mb = (deleted_dir_bytes + deleted_file_bytes) / (1024 * 1024)
    mode_str = " (DRY-RUN)" if dry_run else ""
    print(f"\nSummary{mode_str}: Found {deleted_dir_count} junk directories and {deleted_file_count} junk files.")
    print(f"Total space freed: {total_freed_mb:.2f} MB.")

    return {
        "deleted_dir_count": deleted_dir_count,
        "deleted_file_count": deleted_file_count,
        "freed_bytes": deleted_dir_bytes + deleted_file_bytes,
    }


def main():
    parser = argparse.ArgumentParser(description="Clean and organize OmniCut .tmp folder")
    parser.add_argument("--execute", action="store_true", help="Perform real deletion/moves (default is dry-run)")
    parser.add_argument("--tmp-dir", type=str, default=None, help="Custom .tmp directory path")
    args = parser.parse_args()

    tmp_path = Path(args.tmp_dir) if args.tmp_dir else DEFAULT_TMP_DIR
    dry_run = not args.execute
    clean_and_organize_tmp(tmp_dir=tmp_path, dry_run=dry_run)


if __name__ == '__main__':
    main()
