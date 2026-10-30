#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified CLI entry point for the Parameterized Couple Paper Chat (#5) Production Engine.

Usage:
    python tools/couple_produce.py --product RED01 --clips 1..20 --workers 4 --dry-run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.couple_engine import (
    DEFAULT_MAX_WORKERS,
    DEFAULT_TTS_MODEL,
    generate_clip,
    load_couple_product_config,
    render_clip_parallel,
    validate_tts_model,
)


def parse_clip_selection(spec: str, max_clips: int = 20) -> List[int]:
    """Parse clip range specifications such as '1..20', '1-5', '1,3,7', or 'all'."""
    raw = (spec or "1..20").strip().lower()
    if raw in ("all", "*"):
        return list(range(1, max_clips + 1))

    selected: List[int] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if ".." in token:
            s_str, e_str = token.split("..", 1)
            start, end = int(s_str.strip()), int(e_str.strip())
            selected.extend(range(start, end + 1))
        elif "-" in token:
            s_str, e_str = token.split("-", 1)
            start, end = int(s_str.strip()), int(e_str.strip())
            selected.extend(range(start, end + 1))
        else:
            selected.append(int(token))

    deduped = []
    for idx in selected:
        if 1 <= idx <= max_clips and idx not in deduped:
            deduped.append(idx)
    if not deduped:
        raise ValueError(f"No valid clip indices parsed from '{spec}' (1..{max_clips})")
    return deduped


def run_couple_production(
    product_code: str,
    clips: str = "1..20",
    workers: int = DEFAULT_MAX_WORKERS,
    dry_run: bool = False,
    model: str = DEFAULT_TTS_MODEL,
    project_root: Optional[Path] = None,
    compose_only: bool = False,
) -> Dict[str, Any]:
    """Run Couple Paper Chat production for a given product code and clip range."""
    validate_tts_model(model)
    root = Path(project_root).resolve() if project_root else ROOT
    cfg = load_couple_product_config(product_code, project_root=root)

    scripts_file = cfg.get("scripts_file")
    max_clips = 20
    if scripts_file and Path(scripts_file).exists():
        try:
            scripts_data = json.loads(Path(scripts_file).read_text(encoding="utf-8"))
            if isinstance(scripts_data, list) and scripts_data:
                max_clips = len(scripts_data)
        except Exception:
            pass

    clip_indices = parse_clip_selection(clips, max_clips=max_clips)
    clip_ids = [f"{cfg['clip_prefix']}{idx:02d}" for idx in clip_indices]

    summary: Dict[str, Any] = {
        "product_code": cfg["product_code"],
        "title": cfg["title"],
        "clip_indices": clip_indices,
        "clip_ids": clip_ids,
        "workers": workers,
        "model": model,
        "dry_run": dry_run,
        "generated_htmls": [],
        "render_results": [],
    }

    if dry_run:
        return summary

    studio = root / "03_Projects" / "_HyperFrames_Studio"
    tasks = []
    for idx, cid in zip(clip_indices, clip_ids):
        html_path = generate_clip(cfg["product_code"], idx, project_root=root)
        summary["generated_htmls"].append(str(html_path))
        tasks.append({"clip_id": cid, "html_path": html_path, "clip_index": idx})

    if not compose_only:
        summary["render_results"] = render_clip_parallel(
            tasks,
            max_workers=workers,
            exports_dir=studio.parent.parent / "04_Exports" / "Ready_to_post",
        ) if False else render_clip_parallel(tasks, max_workers=workers)

    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified Couple Paper Chat (#5) Production CLI"
    )
    parser.add_argument(
        "--product",
        required=True,
        help="Product code (e.g., RED01, HAT01, GOO01, TTZ01)",
    )
    parser.add_argument(
        "--clips",
        default="1..20",
        help="Clip range specification (e.g., '1..20', '1-5', '1,3,5')",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help="Parallel render workers (Default: 4 per Rule 24)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_TTS_MODEL,
        help="Allowed Gemini TTS model ('gemini-3.8-flash-tts' or 'gemini-3.1-flash-tts-preview')",
    )
    parser.add_argument(
        "--compose-only",
        action="store_true",
        help="Generate HTML compositions without invoking video rendering",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and print planned clips without modifying files",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    summary = run_couple_production(
        product_code=args.product,
        clips=args.clips,
        workers=args.workers,
        dry_run=args.dry_run,
        model=args.model,
        compose_only=args.compose_only,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
