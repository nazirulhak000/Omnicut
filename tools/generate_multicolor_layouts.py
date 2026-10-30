#!/usr/bin/env python3
"""Generate 3 Multi-Color Product Layout Options for Hatari 16" (HAT01).
Snapshots via Chrome Headless at 1080x1920.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CUTOUTS = STUDIO / "assets" / "hatari01" / "cutouts"
PAPER_BG = STUDIO / "assets" / "shared" / "paper_bg_frame0.jpg"
OUT_DIR = ROOT / "05_Covers_Thumbnails" / "multi_color_prototypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = ROOT / ".tmp" / "multicolor"
TMP_DIR.mkdir(parents=True, exist_ok=True)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CONV_ARTIFACTS = Path(r"C:\Users\nazir\AppData\Roaming\AntigravityProfiles\Profile3\.gemini\antigravity\brain\8e326dbb-3e6a-4ba6-b1c0-092b05fa7df4")

# CSS Base Template
CSS_BASE = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  width: 1080px; height: 1920px;
  background: #efece6;
  font-family: 'Anuphan', sans-serif;
  overflow: hidden;
  position: relative;
  color: #1b1a17;
  -webkit-font-smoothing: antialiased;
}
@font-face {
  font-family: "Kanit Black";
  src: url("../../03_Projects/_HyperFrames_Studio/kit/fonts/Kanit-Black.ttf") format("truetype");
  font-weight: 900;
}
@font-face {
  font-family: "Anuphan";
  src: url("../../03_Projects/_HyperFrames_Studio/kit/fonts/Anuphan-Bold.ttf") format("truetype");
  font-weight: 700;
}
#paper {
  position: absolute; inset: 0; width: 1080px; height: 1920px;
  object-fit: cover; z-index: 1; pointer-events: none;
  filter: brightness(1.02);
}
#top-header {
  position: absolute; top: 180px; left: 40px; right: 40px;
  text-align: center; z-index: 10;
}
.t-brand {
  font-family: "Kanit Black", sans-serif;
  font-size: 82px; line-height: 1.15;
  color: #1b1a17; text-align: center;
}
.hl {
  padding: 0 16px;
  background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
}
.t-sub {
  font-family: "Anuphan", sans-serif;
  font-weight: 700; font-size: 52px;
  color: #d90429; margin-top: 14px;
}
#cta-arrow {
  position: absolute; inset: 0; pointer-events: none; z-index: 20;
}
#cta-arrow path {
  fill: none; stroke: #d90429; stroke-width: 18;
  stroke-linecap: round; stroke-linejoin: round;
}
.bottom-info {
  position: absolute; bottom: 310px; left: 40px; right: 40px;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  z-index: 15;
}
.color-row {
  display: flex; gap: 14px; justify-content: center; flex-wrap: wrap;
}
.color-pill {
  font-family: "Anuphan", sans-serif;
  font-weight: 700; font-size: 30px;
  background: #ffffff; color: #1b1a17;
  border: 4px solid #1b1a17;
  padding: 6px 20px; border-radius: 26px;
  box-shadow: 4px 6px 0 #1b1a17;
  display: flex; align-items: center; gap: 10px;
}
.dot {
  width: 20px; height: 20px; border-radius: 50%; display: inline-block;
  border: 2px solid #1b1a17;
}
.spec-row {
  display: flex; flex-wrap: wrap; justify-content: center;
  max-width: 960px; gap: 10px; margin: 0 auto;
}
.spec-tag {
  font-family: "Anuphan", sans-serif;
  font-weight: 700; font-size: 26px;
  background: #fff; border: 3px solid #1b1a17;
  padding: 6px 16px; border-radius: 18px;
  box-shadow: 3px 5px 0 #1b1a17;
  color: #111111; white-space: nowrap;
}
.contact-shadow {
  position: absolute;
  background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.38) 0%, rgba(30, 20, 15, 0) 72%);
  border-radius: 50%;
  pointer-events: none;
}
"""

def generate_layout_1():
    """Trio Hero Fan-Out: White in center, Mint on left, Pink on right."""
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 400px; left: 0; right: 0; height: 950px;
  z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* Left Fan: Mint */
.fan-left {{
  left: 90px; top: 90px; z-index: 3;
}}
.fan-left img {{
  width: 480px; height: auto;
  filter: drop-shadow(0 14px 18px rgba(0,0,0,0.20));
  transform: rotate(-3deg);
}}
.shadow-left {{
  width: 320px; height: 42px; left: 170px; top: 790px; z-index: 2;
}}

/* Right Fan: Pink */
.fan-right {{
  right: 90px; top: 90px; z-index: 3;
}}
.fan-right img {{
  width: 480px; height: auto;
  filter: drop-shadow(0 14px 18px rgba(0,0,0,0.20));
  transform: rotate(3deg);
}}
.shadow-right {{
  width: 320px; height: 42px; right: 170px; top: 790px; z-index: 2;
}}

/* Center Fan: White (HERO) */
.fan-center {{
  left: 50%; transform: translateX(-50%);
  top: 30px; z-index: 5;
}}
.fan-center img {{
  width: 590px; height: auto;
  filter: drop-shadow(0 20px 28px rgba(0,0,0,0.28));
}}
.shadow-center {{
  width: 410px; height: 50px; left: 50%; transform: translateX(-50%); top: 820px; z-index: 4;
}}
.hero-badge {{
  position: absolute; top: -15px; right: 20px;
  background: #ffe600; color: #1b1a17;
  font-family: 'Kanit Black', sans-serif; font-size: 24px;
  padding: 4px 16px; border-radius: 20px;
  border: 3px solid #1b1a17; box-shadow: 3px 4px 0 #1b1a17;
  transform: rotate(6deg); z-index: 6;
}}
</style>
</head>
<body>
  <img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">
  
  <div id="top-header">
    <div class="t-brand"><span class="hl">Hatari · พัดลม 16 นิ้ว</span></div>
    <div class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</div>
  </div>

  <div id="showcase">
    <!-- Left Fan: Mint -->
    <div class="fan-wrap fan-left">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png">
    </div>
    <div class="contact-shadow shadow-left"></div>

    <!-- Right Fan: Pink -->
    <div class="fan-wrap fan-right">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png">
    </div>
    <div class="contact-shadow shadow-right"></div>

    <!-- Center Fan: White (HERO) -->
    <div class="fan-wrap fan-center">
      <div class="hero-badge">สียอดฮิต ⭐</div>
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png">
    </div>
    <div class="contact-shadow shadow-center"></div>
  </div>

  <div class="bottom-info">
    <div class="color-row">
      <span class="color-pill"><span class="dot" style="background: #ffffff;"></span> สีขาวมินิมอล</span>
      <span class="color-pill"><span class="dot" style="background: #a8e6cf;"></span> สีเขียวมิ้นท์</span>
      <span class="color-pill"><span class="dot" style="background: #ffb6c1;"></span> สีชมพูพาสเทล</span>
    </div>
    <div class="spec-row">
      <span class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</span>
      <span class="spec-tag">มอเตอร์ Ball Bearing</span>
      <span class="spec-tag">ระบบ Thermal Fuse</span>
      <span class="spec-tag">ประหยัดไฟเบอร์ 5</span>
    </div>
  </div>

  <svg id="cta-arrow" viewBox="0 0 1080 1920">
    <path d="M 220 740 C 120 940 80 1220 140 1480" />
    <path d="M 60 1400 L 140 1490 L 230 1410" />
  </svg>
</body>
</html>
"""
    return html_content

def generate_layout_2():
    """5-Color Pastel Fan Arc: Yellow, Mint, White (center), Blue, Pink."""
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 410px; left: 0; right: 0; height: 950px;
  z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* 1. Far Left: Yellow */
.fan-yellow {{
  left: 20px; top: 170px; z-index: 3;
}}
.fan-yellow img {{
  width: 360px; height: auto;
  filter: drop-shadow(0 10px 14px rgba(0,0,0,0.18));
  transform: rotate(-6deg);
}}
.shadow-yellow {{
  width: 240px; height: 32px; left: 80px; top: 700px; z-index: 2;
}}

/* 2. Inner Left: Mint */
.fan-mint {{
  left: 170px; top: 90px; z-index: 4;
}}
.fan-mint img {{
  width: 440px; height: auto;
  filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22));
  transform: rotate(-3deg);
}}
.shadow-mint {{
  width: 290px; height: 38px; left: 245px; top: 740px; z-index: 3;
}}

/* 3. Center: White (HERO) */
.fan-white {{
  left: 50%; transform: translateX(-50%);
  top: 15px; z-index: 6;
}}
.fan-white img {{
  width: 530px; height: auto;
  filter: drop-shadow(0 22px 30px rgba(0,0,0,0.30));
}}
.shadow-white {{
  width: 370px; height: 46px; left: 50%; transform: translateX(-50%); top: 790px; z-index: 5;
}}

/* 4. Inner Right: Blue */
.fan-blue {{
  right: 170px; top: 90px; z-index: 4;
}}
.fan-blue img {{
  width: 440px; height: auto;
  filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22));
  transform: rotate(3deg);
}}
.shadow-blue {{
  width: 290px; height: 38px; right: 245px; top: 740px; z-index: 3;
}}

/* 5. Far Right: Pink */
.fan-pink {{
  right: 20px; top: 170px; z-index: 3;
}}
.fan-pink img {{
  width: 360px; height: auto;
  filter: drop-shadow(0 10px 14px rgba(0,0,0,0.18));
  transform: rotate(6deg);
}}
.shadow-pink {{
  width: 240px; height: 32px; right: 80px; top: 700px; z-index: 2;
}}
.title-chip {{
  background: #1b1a17; color: #ffe600;
  font-family: 'Kanit Black', sans-serif; font-size: 28px;
  padding: 6px 26px; border-radius: 30px;
  box-shadow: 4px 6px 0 rgba(27,26,23,0.3);
  letter-spacing: 1px;
}}
</style>
</head>
<body>
  <img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">
  
  <div id="top-header">
    <div class="t-brand"><span class="hl">Hatari · พัดลม 16 นิ้ว</span></div>
    <div class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</div>
  </div>

  <div id="showcase">
    <!-- Far Left: Yellow -->
    <div class="fan-wrap fan-yellow">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_yellow.png">
    </div>
    <div class="contact-shadow shadow-yellow"></div>

    <!-- Inner Left: Mint -->
    <div class="fan-wrap fan-mint">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png">
    </div>
    <div class="contact-shadow shadow-mint"></div>

    <!-- Inner Right: Blue -->
    <div class="fan-wrap fan-blue">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_blue.png">
    </div>
    <div class="contact-shadow shadow-blue"></div>

    <!-- Far Right: Pink -->
    <div class="fan-wrap fan-pink">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png">
    </div>
    <div class="contact-shadow shadow-pink"></div>

    <!-- Center: White (HERO) -->
    <div class="fan-wrap fan-white">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png">
    </div>
    <div class="contact-shadow shadow-white"></div>
  </div>

  <div class="bottom-info">
    <div class="title-chip">🎨 มีให้เลือกครบ 5 สีพาสเทล</div>
    <div class="color-row">
      <span class="color-pill"><span class="dot" style="background: #ffffff;"></span> ขาว</span>
      <span class="color-pill"><span class="dot" style="background: #a8e6cf;"></span> มิ้นท์</span>
      <span class="color-pill"><span class="dot" style="background: #90caf9;"></span> ฟ้า</span>
      <span class="color-pill"><span class="dot" style="background: #ffb6c1;"></span> ชมพู</span>
      <span class="color-pill"><span class="dot" style="background: #fff59d;"></span> เหลือง</span>
    </div>
    <div class="spec-row">
      <span class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</span>
      <span class="spec-tag">มอเตอร์ Ball Bearing</span>
      <span class="spec-tag">ระบบ Thermal Fuse</span>
      <span class="spec-tag">ประหยัดไฟเบอร์ 5</span>
    </div>
  </div>

  <svg id="cta-arrow" viewBox="0 0 1080 1920">
    <path d="M 220 740 C 120 940 80 1220 140 1480" />
    <path d="M 60 1400 L 140 1490 L 230 1410" />
  </svg>
</body>
</html>
"""
    return html_content

def generate_layout_3():
    """Duo Hero Staggered (White + Mint) with Color Swatch Card."""
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 420px; left: 0; right: 0; height: 950px;
  z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* Back Fan: Mint Green */
.fan-mint {{
  left: 140px; top: 70px; z-index: 3;
}}
.fan-mint img {{
  width: 530px; height: auto;
  filter: drop-shadow(0 14px 20px rgba(0,0,0,0.22));
}}
.shadow-mint {{
  width: 360px; height: 44px; left: 220px; top: 780px; z-index: 2;
}}

/* Front Fan: White */
.fan-white {{
  right: 130px; top: 20px; z-index: 5;
}}
.fan-white img {{
  width: 580px; height: auto;
  filter: drop-shadow(0 22px 30px rgba(0,0,0,0.28));
}}
.shadow-white {{
  width: 400px; height: 48px; right: 220px; top: 830px; z-index: 4;
}}

/* Floating Color Palette Card */
.swatch-card {{
  position: absolute; left: 80px; top: 120px; z-index: 7;
  background: #ffffff; border: 4px solid #1b1a17;
  border-radius: 24px; padding: 14px 20px;
  box-shadow: 5px 7px 0 #1b1a17;
  display: flex; flex-direction: column; gap: 8px;
  transform: rotate(-5deg);
}}
.swatch-card .sw-title {{
  font-family: 'Kanit Black', sans-serif; font-size: 24px; color: #1b1a17;
}}
.swatch-dots {{
  display: flex; gap: 10px;
}}
.swatch-dot {{
  width: 32px; height: 32px; border-radius: 50%;
  border: 3px solid #1b1a17;
}}
</style>
</head>
<body>
  <img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">
  
  <div id="top-header">
    <div class="t-brand"><span class="hl">Hatari · พัดลม 16 นิ้ว</span></div>
    <div class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</div>
  </div>

  <div id="showcase">
    <!-- Floating Color Palette -->
    <div class="swatch-card">
      <div class="sw-title">🎨 มี 5 โทนสีพาสเทล</div>
      <div class="swatch-dots">
        <div class="swatch-dot" style="background: #ffffff;"></div>
        <div class="swatch-dot" style="background: #a8e6cf;"></div>
        <div class="swatch-dot" style="background: #90caf9;"></div>
        <div class="swatch-dot" style="background: #ffb6c1;"></div>
        <div class="swatch-dot" style="background: #fff59d;"></div>
      </div>
    </div>

    <!-- Back Fan: Mint -->
    <div class="fan-wrap fan-mint">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png">
    </div>
    <div class="contact-shadow shadow-mint"></div>

    <!-- Front Fan: White -->
    <div class="fan-wrap fan-white">
      <img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png">
    </div>
    <div class="contact-shadow shadow-white"></div>
  </div>

  <div class="bottom-info">
    <div class="color-row">
      <span class="color-pill"><span class="dot" style="background: #ffffff;"></span> สีขาวมินิมอล</span>
      <span class="color-pill"><span class="dot" style="background: #a8e6cf;"></span> สีเขียวมิ้นท์</span>
      <span class="color-pill"><span class="dot" style="background: #90caf9;"></span> สีฟ้าพาสเทล</span>
    </div>
    <div class="spec-row">
      <span class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</span>
      <span class="spec-tag">มอเตอร์ Ball Bearing</span>
      <span class="spec-tag">ระบบ Thermal Fuse</span>
      <span class="spec-tag">ประหยัดไฟเบอร์ 5</span>
    </div>
  </div>

  <svg id="cta-arrow" viewBox="0 0 1080 1920">
    <path d="M 220 740 C 120 940 80 1220 140 1480" />
    <path d="M 60 1400 L 140 1490 L 230 1410" />
  </svg>
</body>
</html>
"""
    return html_content

def main():
    layouts = {
        "layout_1_trio": generate_layout_1(),
        "layout_2_five_colors": generate_layout_2(),
        "layout_3_duo_swatch": generate_layout_3(),
    }

    generated_images = []

    for name, content in layouts.items():
        html_path = TMP_DIR / f"{name}.html"
        html_path.write_text(content, encoding="utf-8")
        out_png = OUT_DIR / f"hat01_multicolor_{name}.png"

        print(f"Rendering {name} via Chrome Headless...")
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--force-device-scale-factor=1",
            f"--window-size=1080,1920",
            f"--screenshot={out_png}",
            str(html_path.resolve())
        ]
        subprocess.run(cmd, check=True)
        print(f"  -> Saved {out_png.name} ({out_png.stat().st_size} bytes)")

        # Copy to conversation artifacts directory for direct user viewing
        conv_dest = CONV_ARTIFACTS / out_png.name
        shutil.copy2(out_png, conv_dest)
        print(f"  -> Copied to conversation artifact: {conv_dest.name}")
        generated_images.append(conv_dest)

    print("\nAll 3 layouts generated successfully!")

if __name__ == "__main__":
    main()
