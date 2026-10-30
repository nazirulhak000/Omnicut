#!/usr/bin/env python3
"""Batch enhance brightness and eliminate dark vignette overlay across all 20 HOYAUP clips.

Resolves:
1. Removes <div id="paper-tint"></div> which dimmed the entire screen by 15-22% (radial gradient dark vignette)
2. Adds subtle natural paper brightness lift `filter: brightness(1.02);` to #paper
3. Updates batch builder template tools/batch_produce_hoyaup_20.py
"""
import glob
import re
import sys
from pathlib import Path

# UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
COMPS_DIR = ROOT / "03_Projects" / "_HyperFrames_Studio" / "compositions"
BATCH_SCRIPT = ROOT / "tools" / "batch_produce_hoyaup_20.py"


def brighten_composition(html_path: Path) -> bool:
    """Brighten a single composition HTML file."""
    content = html_path.read_text(encoding="utf-8")
    orig = content

    # 1. Remove <div id="paper-tint"></div>
    content = re.sub(r'\s*<div[^>]*id=["\']paper-tint["\'][^>]*></div>', '', content)

    # 2. Remove #paper-tint CSS
    content = re.sub(
        r'/\*\s*warm overlay on the paper\s*\*/\s*#paper-tint\s*\{[^}]*\}',
        '/* #paper-tint removed for clean bright presentation */',
        content,
    )
    # Fallback if comment differs
    content = re.sub(
        r'#paper-tint\s*\{[^}]*\}',
        '/* #paper-tint removed */',
        content,
    )

    # 3. Add filter: brightness(1.02); to #paper if not already present
    def repl_paper(m):
        css_body = m.group(1)
        if "brightness" not in css_body:
            # Add filter: brightness(1.02);
            css_body = css_body.rstrip() + "\n        filter: brightness(1.02);"
        return f"#paper {{{css_body}\n      }}"

    content = re.sub(r'#paper\s*\{([^}]+)\}', repl_paper, content)

    if content != orig:
        html_path.write_text(content, encoding="utf-8")
        return True
    return False


def update_batch_template():
    """Update tools/batch_produce_hoyaup_20.py template."""
    if not BATCH_SCRIPT.exists():
        return False
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    orig = content

    # 1. Update #paper in template
    content = re.sub(
        r'(#paper\s*\{[^}]*object-fit:\s*cover;)(?!\s*filter:)',
        r'\1\n        filter: brightness(1.02);',
        content,
    )

    # 2. Remove #paper-tint CSS block from template
    content = re.sub(
        r'/\*\s*warm overlay on the paper\s*\*/\s*#paper-tint\s*\{[^}]*\}',
        '/* paper overlay removed for clean bright presentation */',
        content,
    )

    # 3. Remove <div id="paper-tint"></div> from template
    content = re.sub(
        r'\s*<div id="paper-tint"></div>',
        '',
        content,
    )

    if content != orig:
        BATCH_SCRIPT.write_text(content, encoding="utf-8")
        print("  -> Updated batch_produce_hoyaup_20.py template")
        return True
    return False


def main():
    print("=" * 60)
    print("✨ ENHANCING BRIGHTNESS FOR ALL 20 HOYAUP COMPOSITIONS")
    print("=" * 60)

    update_batch_template()

    comps = sorted(COMPS_DIR.glob("hoy01-pov-s*.html"))
    if not comps:
        print("No hoy01-pov-s*.html compositions found!")
        return

    updated_count = 0
    for p in comps:
        changed = brighten_composition(p)
        status = "UPDATED (brightened)" if changed else "ALREADY BRIGHT"
        print(f"[{p.name}] {status}")
        if changed:
            updated_count += 1

    print(f"\nDone! Brightened {updated_count}/{len(comps)} compositions.")


if __name__ == "__main__":
    main()
