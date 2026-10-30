import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE = Path(r"D:\Programmer\All Project\Omnicut")
STUDIO_DIR = WORKSPACE / "03_Projects" / "_HyperFrames_Studio"
COMPS_DIR = STUDIO_DIR / "compositions"
CLIPS_DIR = STUDIO_DIR / "clips"

OLD_CSS = """      #cta-1 {
        position: absolute;
        top: 240px;
        font-size: 116px;
        line-height: 1.15;
      }
      #cta-model {
        position: absolute;
        top: 410px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 64px;
        color: #d90429;
      }"""

NEW_CSS = """      #cta-1 {
        position: absolute;
        top: 230px;
        font-size: 108px;
        line-height: 1.15;
      }
      #cta-model {
        position: absolute;
        top: 385px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 62px;
        color: #d90429;
      }"""

OLD_HTML = """        <div class="t center" id="cta-1"><span class="hl">กดตะกร้าเหลือง</span></div>
        <div class="t center" id="cta-model">Essager · PD 30W · ชาร์จเร็วตัวจบ</div>"""

NEW_HTML = """        <div class="t center" id="cta-1"><span class="hl">Essager · PD 30W</span></div>
        <div class="t center" id="cta-model">ชาร์จเร็วตัวจบ · กดตะกร้าเหลือง</div>"""

CTA2_HTML = '        <div class="t" id="cta-2">ซ้ายล่าง</div>\n'
CTA2_GSAP_REGEX = re.compile(r'\s*tl\.fromTo\("#cta-2",\s*\{[^}]*\},[^;]*\);\n')

def update_content(content: str) -> tuple[str, bool]:
    changed = False
    if OLD_CSS in content:
        content = content.replace(OLD_CSS, NEW_CSS)
        changed = True
    if OLD_HTML in content:
        content = content.replace(OLD_HTML, NEW_HTML)
        changed = True
    if CTA2_HTML in content:
        content = content.replace(CTA2_HTML, "")
        changed = True
    if CTA2_GSAP_REGEX.search(content):
        content = CTA2_GSAP_REGEX.sub("", content)
        changed = True
    return content, changed

def main():
    print("=" * 68)
    print("🚀 Applying Brand & Model First CTA + Removing 'ซ้ายล่าง' for Clips 01-20")
    print("=" * 68)

    updated_count = 0
    for idx in range(1, 21):
        cid = f"ess02-pov-s{idx:02d}"
        comp_file = COMPS_DIR / f"{cid}.html"
        clip_file = CLIPS_DIR / cid / "index.html"

        # Update composition
        if comp_file.exists():
            content = comp_file.read_text(encoding="utf-8")
            new_content, changed = update_content(content)
            if changed:
                comp_file.write_text(new_content, encoding="utf-8")
                print(f"  ✅ Updated composition: {cid}.html")
            else:
                print(f"  ℹ️ Composition already clean/updated: {cid}.html")
        else:
            print(f"  ⚠️ Missing composition: {comp_file}")

        # Update clip source
        if clip_file.exists():
            content = clip_file.read_text(encoding="utf-8")
            new_content, changed = update_content(content)
            if changed:
                clip_file.write_text(new_content, encoding="utf-8")
                print(f"  ✅ Updated clip source: clips/{cid}/index.html")
            else:
                print(f"  ℹ️ Clip source already clean/updated: clips/{cid}/index.html")
        else:
            print(f"  ⚠️ Missing clip file: {clip_file}")

        updated_count += 1

    print(f"\n🎉 Successfully processed all {updated_count} clips!")

if __name__ == "__main__":
    main()
