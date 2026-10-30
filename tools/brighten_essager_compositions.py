#!/usr/bin/env python3
"""Brighten all 20 archived Essager compositions.
Removes <div id="paper-tint"></div> and adds filter: brightness(1.02); to #paper.
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
ARCHIVE_COMPS_DIR = ROOT / "06_Archive" / "HyperFrames_Studio" / "compositions"


def brighten_composition(html_path: Path) -> bool:
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
    content = re.sub(
        r'#paper-tint\s*\{[^}]*\}',
        '/* #paper-tint removed */',
        content,
    )

    # 3. Add filter: brightness(1.02); to #paper
    def repl_paper(m):
        css_body = m.group(1)
        if "brightness" not in css_body:
            css_body = css_body.rstrip() + "\n        filter: brightness(1.02);"
        return f"#paper {{{css_body}\n      }}"

    content = re.sub(r'#paper\s*\{([^}]+)\}', repl_paper, content)

    if content != orig:
        html_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    print("=== Brightening all 20 Essager Compositions ===")
    comps = sorted(ARCHIVE_COMPS_DIR.glob("ess02-pov-s*.html"))
    if not comps:
        print("No ess02-pov-s*.html compositions found in archive!")
        return

    updated = 0
    for p in comps:
        changed = brighten_composition(p)
        print(f"[{p.name}] {'UPDATED' if changed else 'ALREADY BRIGHT'}")
        if changed:
            updated += 1
    print(f"\nDone! Brightened {updated}/{len(comps)} Essager compositions.")


if __name__ == "__main__":
    main()
