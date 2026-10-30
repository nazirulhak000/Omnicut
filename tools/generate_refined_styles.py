#!/usr/bin/env python3
"""Generate Refined Style 1 & Style 3 Layouts (Zero Emoji, Clean Human Agency Standard).
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
TMP_DIR = ROOT / ".tmp" / "multicolor_refined"
TMP_DIR.mkdir(parents=True, exist_ok=True)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CONV_ARTIFACTS = Path(r"C:\Users\nazir\AppData\Roaming\AntigravityProfiles\Profile3\.gemini\antigravity\brain\8e326dbb-3e6a-4ba6-b1c0-092b05fa7df4")

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
  position: absolute; top: 170px; left: 40px; right: 40px;
  text-align: center; z-index: 25;
}
.t-brand {
  font-family: "Kanit Black", sans-serif;
  font-size: 80px; line-height: 1.15;
  color: #1b1a17; text-align: center;
}
.hl {
  padding: 0 16px;
  background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
}
.t-sub {
  font-family: "Anuphan", sans-serif;
  font-weight: 700; font-size: 50px;
  color: #d90429; margin-top: 12px;
}
#cta-arrow {
  position: absolute; inset: 0; pointer-events: none; z-index: 30;
}
#cta-arrow path {
  fill: none; stroke: #d90429; stroke-width: 18;
  stroke-linecap: round; stroke-linejoin: round;
}
.bottom-info {
  position: absolute; bottom: 270px; left: 40px; right: 40px;
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  z-index: 25;
}
.color-row {
  display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
  max-width: 1000px;
}
.color-pill {
  font-family: "Anuphan", sans-serif;
  font-weight: 700; font-size: 24px;
  background: #ffffff; color: #1b1a17;
  border: 3px solid #1b1a17;
  padding: 5px 14px; border-radius: 20px;
  box-shadow: 3px 4px 0 #1b1a17;
  display: flex; align-items: center; gap: 7px;
}
.dot {
  width: 16px; height: 16px; border-radius: 50%; display: inline-block;
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
  background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.42) 0%, rgba(30, 20, 15, 0) 72%);
  border-radius: 50%;
  pointer-events: none;
}
"""

def generate_style_1_clean_nobadge():
    """Style 1A: 6-Color Arc - Ultra Clean (No top badge, zero emoji, pure color pills)"""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 380px; left: 0; right: 0; height: 960px; z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* Fan 1: Yellow (Far Left) */
.f1 {{ left: -30px; top: 220px; z-index: 3; }}
.f1 img {{ width: 350px; transform: rotate(-7deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.s1 {{ width: 230px; height: 32px; left: 30px; top: 760px; z-index: 2; }}

/* Fan 2: Mint (Mid Left) */
.f2 {{ left: 130px; top: 150px; z-index: 6; }}
.f2 img {{ width: 420px; transform: rotate(-3deg); filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22)); }}
.s2 {{ width: 270px; height: 36px; left: 200px; top: 775px; z-index: 5; }}

/* Fan 3: White (Hero Center) */
.f3 {{ left: 310px; top: 90px; z-index: 12; }}
.f3 img {{ width: 500px; filter: drop-shadow(0 18px 24px rgba(0,0,0,0.26)); }}
.s3 {{ width: 330px; height: 42px; left: 395px; top: 810px; z-index: 11; }}

/* Fan 4: Blue (Mid Right) */
.f4 {{ left: 510px; top: 125px; z-index: 9; }}
.f4 img {{ width: 440px; transform: rotate(2deg); filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22)); }}
.s4 {{ width: 280px; height: 38px; left: 590px; top: 785px; z-index: 8; }}

/* Fan 5: Pink (Outer Right) */
.f5 {{ left: 660px; top: 170px; z-index: 6; }}
.f5 img {{ width: 410px; transform: rotate(5deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.s5 {{ width: 260px; height: 34px; left: 730px; top: 770px; z-index: 5; }}

/* Fan 6: Purple (Far Right) */
.f6 {{ left: 770px; top: 230px; z-index: 3; }}
.f6 img {{ width: 350px; transform: rotate(8deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.s6 {{ width: 230px; height: 32px; left: 830px; top: 765px; z-index: 2; }}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <h1 class="t-brand">Hatari · <span class="hl">พัดลม 16 นิ้ว</span></h1>
  <p class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</p>
</div>

<div id="showcase">
  <div class="contact-shadow s1"></div>
  <div class="fan-wrap f1"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_yellow.png"></div>

  <div class="contact-shadow s2"></div>
  <div class="fan-wrap f2"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow s3"></div>
  <div class="fan-wrap f3"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>

  <div class="contact-shadow s4"></div>
  <div class="fan-wrap f4"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_blue.png"></div>

  <div class="contact-shadow s5"></div>
  <div class="fan-wrap f5"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow s6"></div>
  <div class="fan-wrap f6"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_purple.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 730 C 70 920, 50 1260, 95 1530" />
  <path d="M 25 1445 L 95 1530 L 190 1480" />
</svg>

<div class="bottom-info">
  <div class="color-row">
    <div class="color-pill"><span class="dot" style="background:#ffffff"></span>ขาว</div>
    <div class="color-pill"><span class="dot" style="background:#b8e0c8"></span>มิ้นท์</div>
    <div class="color-pill"><span class="dot" style="background:#f7c8d0"></span>ชมพู</div>
    <div class="color-pill"><span class="dot" style="background:#b8d8ea"></span>ฟ้า</div>
    <div class="color-pill"><span class="dot" style="background:#faeec2"></span>เหลือง</div>
    <div class="color-pill"><span class="dot" style="background:#d9c5ea"></span>ม่วง</div>
  </div>
  <div class="spec-row">
    <div class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</div>
    <div class="spec-tag">มอเตอร์ Ball Bearing</div>
    <div class="spec-tag">ระบบ Thermal Fuse</div>
    <div class="spec-tag">ประหยัดไฟเบอร์ 5</div>
  </div>
</div>
</body>
</html>"""

def generate_style_1_clean_tag():
    """Style 1B: 6-Color Arc with Clean Minimal Tag (No Emoji, e.g. '6 เฉดสีพาสเทล')"""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 380px; left: 0; right: 0; height: 960px; z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* Fan 1: Yellow (Far Left) */
.f1 {{ left: -30px; top: 220px; z-index: 3; }}
.f1 img {{ width: 350px; transform: rotate(-7deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.s1 {{ width: 230px; height: 32px; left: 30px; top: 760px; z-index: 2; }}

/* Fan 2: Mint (Mid Left) */
.f2 {{ left: 130px; top: 150px; z-index: 6; }}
.f2 img {{ width: 420px; transform: rotate(-3deg); filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22)); }}
.s2 {{ width: 270px; height: 36px; left: 200px; top: 775px; z-index: 5; }}

/* Fan 3: White (Hero Center) */
.f3 {{ left: 310px; top: 90px; z-index: 12; }}
.f3 img {{ width: 500px; filter: drop-shadow(0 18px 24px rgba(0,0,0,0.26)); }}
.s3 {{ width: 330px; height: 42px; left: 395px; top: 810px; z-index: 11; }}

/* Fan 4: Blue (Mid Right) */
.f4 {{ left: 510px; top: 125px; z-index: 9; }}
.f4 img {{ width: 440px; transform: rotate(2deg); filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22)); }}
.s4 {{ width: 280px; height: 38px; left: 590px; top: 785px; z-index: 8; }}

/* Fan 5: Pink (Outer Right) */
.f5 {{ left: 660px; top: 170px; z-index: 6; }}
.f5 img {{ width: 410px; transform: rotate(5deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.s5 {{ width: 260px; height: 34px; left: 730px; top: 770px; z-index: 5; }}

/* Fan 6: Purple (Far Right) */
.f6 {{ left: 770px; top: 230px; z-index: 3; }}
.f6 img {{ width: 350px; transform: rotate(8deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.s6 {{ width: 230px; height: 32px; left: 830px; top: 765px; z-index: 2; }}

.clean-title {{
  font-family: "Kanit Black", sans-serif;
  font-size: 28px;
  background: #1b1a17;
  color: #ffffff;
  padding: 6px 22px;
  border-radius: 20px;
  letter-spacing: 0.5px;
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <h1 class="t-brand">Hatari · <span class="hl">พัดลม 16 นิ้ว</span></h1>
  <p class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</p>
</div>

<div id="showcase">
  <div class="contact-shadow s1"></div>
  <div class="fan-wrap f1"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_yellow.png"></div>

  <div class="contact-shadow s2"></div>
  <div class="fan-wrap f2"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow s3"></div>
  <div class="fan-wrap f3"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>

  <div class="contact-shadow s4"></div>
  <div class="fan-wrap f4"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_blue.png"></div>

  <div class="contact-shadow s5"></div>
  <div class="fan-wrap f5"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow s6"></div>
  <div class="fan-wrap f6"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_purple.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 730 C 70 920, 50 1260, 95 1530" />
  <path d="M 25 1445 L 95 1530 L 190 1480" />
</svg>

<div class="bottom-info">
  <div class="clean-title">6 เฉดสีพาสเทลยอดฮิต</div>
  <div class="color-row">
    <div class="color-pill"><span class="dot" style="background:#ffffff"></span>ขาว</div>
    <div class="color-pill"><span class="dot" style="background:#b8e0c8"></span>มิ้นท์</div>
    <div class="color-pill"><span class="dot" style="background:#f7c8d0"></span>ชมพู</div>
    <div class="color-pill"><span class="dot" style="background:#b8d8ea"></span>ฟ้า</div>
    <div class="color-pill"><span class="dot" style="background:#faeec2"></span>เหลือง</div>
    <div class="color-pill"><span class="dot" style="background:#d9c5ea"></span>ม่วง</div>
  </div>
  <div class="spec-row">
    <div class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</div>
    <div class="spec-tag">มอเตอร์ Ball Bearing</div>
    <div class="spec-tag">ระบบ Thermal Fuse</div>
    <div class="spec-tag">ประหยัดไฟเบอร์ 5</div>
  </div>
</div>
</body>
</html>"""

def generate_style_3_minimal_full():
    """Style 3A: Trio Hero + Clean Swatch Strip (Zero Emoji, 'มีให้เลือกครบ 6 โทนสีพาสเทล')"""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 400px; left: 0; right: 0; height: 950px; z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* Mint */
.fan-left {{ left: 80px; top: 80px; z-index: 5; }}
.fan-left img {{ width: 490px; transform: rotate(-3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.22)); }}
.shadow-left {{ width: 320px; height: 42px; left: 165px; top: 790px; z-index: 4; }}

/* Pink */
.fan-right {{ right: 80px; top: 80px; z-index: 5; }}
.fan-right img {{ width: 490px; transform: rotate(3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.22)); }}
.shadow-right {{ width: 320px; height: 42px; right: 165px; top: 790px; z-index: 4; }}

/* White Hero Center */
.fan-center {{ left: 245px; top: 10px; z-index: 10; }}
.fan-center img {{ width: 590px; filter: drop-shadow(0 22px 28px rgba(0,0,0,0.28)); }}
.shadow-center {{ width: 380px; height: 48px; left: 350px; top: 830px; z-index: 9; }}

/* Swatch Strip Container - Zero Emoji, Pure Human Design */
.swatch-card {{
  background: #ffffff;
  border: 3.5px solid #1b1a17;
  border-radius: 26px;
  box-shadow: 5px 7px 0 #1b1a17;
  padding: 14px 28px;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}}
.swatch-title {{
  font-family: "Kanit Black", sans-serif;
  font-size: 26px; color: #1b1a17;
  letter-spacing: 0.5px;
}}
.chips-grid {{
  display: flex; gap: 14px; justify-content: center;
}}
.chip-item {{
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  font-size: 22px; font-weight: 700; color: #1b1a17;
}}
.chip-dot {{
  width: 38px; height: 38px; border-radius: 50%;
  border: 2.5px solid #1b1a17; box-shadow: 2px 3px 0 rgba(0,0,0,0.15);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <h1 class="t-brand">Hatari · <span class="hl">พัดลม 16 นิ้ว</span></h1>
  <p class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</p>
</div>

<div id="showcase">
  <div class="contact-shadow shadow-left"></div>
  <div class="fan-wrap fan-left"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow shadow-right"></div>
  <div class="fan-wrap fan-right"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow shadow-center"></div>
  <div class="fan-wrap fan-center"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 730 C 70 920, 50 1260, 95 1530" />
  <path d="M 25 1445 L 95 1530 L 190 1480" />
</svg>

<div class="bottom-info">
  <div class="swatch-card">
    <div class="swatch-title">มีให้เลือกครบ 6 โทนสีพาสเทล</div>
    <div class="chips-grid">
      <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว</div>
      <div class="chip-item"><div class="chip-dot" style="background:#b8e0c8"></div>มิ้นท์</div>
      <div class="chip-item"><div class="chip-dot" style="background:#f7c8d0"></div>ชมพู</div>
      <div class="chip-item"><div class="chip-dot" style="background:#b8d8ea"></div>ฟ้า</div>
      <div class="chip-item"><div class="chip-dot" style="background:#faeec2"></div>เหลือง</div>
      <div class="chip-item"><div class="chip-dot" style="background:#d9c5ea"></div>ม่วง</div>
    </div>
  </div>
  <div class="spec-row">
    <div class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</div>
    <div class="spec-tag">มอเตอร์ Ball Bearing</div>
    <div class="spec-tag">ระบบ Thermal Fuse</div>
    <div class="spec-tag">ประหยัดไฟเบอร์ 5</div>
  </div>
</div>
</body>
</html>"""

def generate_style_3_minimal_short():
    """Style 3B: Trio Hero + Ultra-Minimal Swatch Strip ('6 โทนสีพาสเทล')"""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<style>
{CSS_BASE}
#showcase {{
  position: absolute; top: 400px; left: 0; right: 0; height: 950px; z-index: 10;
}}
.fan-wrap {{
  position: absolute; display: flex; flex-direction: column; align-items: center;
}}
/* Mint */
.fan-left {{ left: 80px; top: 80px; z-index: 5; }}
.fan-left img {{ width: 490px; transform: rotate(-3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.22)); }}
.shadow-left {{ width: 320px; height: 42px; left: 165px; top: 790px; z-index: 4; }}

/* Pink */
.fan-right {{ right: 80px; top: 80px; z-index: 5; }}
.fan-right img {{ width: 490px; transform: rotate(3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.22)); }}
.shadow-right {{ width: 320px; height: 42px; right: 165px; top: 790px; z-index: 4; }}

/* White Hero Center */
.fan-center {{ left: 245px; top: 10px; z-index: 10; }}
.fan-center img {{ width: 590px; filter: drop-shadow(0 22px 28px rgba(0,0,0,0.28)); }}
.shadow-center {{ width: 380px; height: 48px; left: 350px; top: 830px; z-index: 9; }}

/* Ultra-Clean Swatch Card */
.swatch-card {{
  background: #ffffff;
  border: 3.5px solid #1b1a17;
  border-radius: 26px;
  box-shadow: 5px 7px 0 #1b1a17;
  padding: 12px 28px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}}
.swatch-title {{
  font-family: "Kanit Black", sans-serif;
  font-size: 26px; color: #1b1a17;
  letter-spacing: 0.5px;
}}
.chips-grid {{
  display: flex; gap: 14px; justify-content: center;
}}
.chip-item {{
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  font-size: 22px; font-weight: 700; color: #1b1a17;
}}
.chip-dot {{
  width: 38px; height: 38px; border-radius: 50%;
  border: 2.5px solid #1b1a17; box-shadow: 2px 3px 0 rgba(0,0,0,0.15);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <h1 class="t-brand">Hatari · <span class="hl">พัดลม 16 นิ้ว</span></h1>
  <p class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</p>
</div>

<div id="showcase">
  <div class="contact-shadow shadow-left"></div>
  <div class="fan-wrap fan-left"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow shadow-right"></div>
  <div class="fan-wrap fan-right"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow shadow-center"></div>
  <div class="fan-wrap fan-center"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 730 C 70 920, 50 1260, 95 1530" />
  <path d="M 25 1445 L 95 1530 L 190 1480" />
</svg>

<div class="bottom-info">
  <div class="swatch-card">
    <div class="swatch-title">6 โทนสีพาสเทล</div>
    <div class="chips-grid">
      <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว</div>
      <div class="chip-item"><div class="chip-dot" style="background:#b8e0c8"></div>มิ้นท์</div>
      <div class="chip-item"><div class="chip-dot" style="background:#f7c8d0"></div>ชมพู</div>
      <div class="chip-item"><div class="chip-dot" style="background:#b8d8ea"></div>ฟ้า</div>
      <div class="chip-item"><div class="chip-dot" style="background:#faeec2"></div>เหลือง</div>
      <div class="chip-item"><div class="chip-dot" style="background:#d9c5ea"></div>ม่วง</div>
    </div>
  </div>
  <div class="spec-row">
    <div class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</div>
    <div class="spec-tag">มอเตอร์ Ball Bearing</div>
    <div class="spec-tag">ระบบ Thermal Fuse</div>
    <div class="spec-tag">ประหยัดไฟเบอร์ 5</div>
  </div>
</div>
</body>
</html>"""

def main():
    styles = [
        ("style_1_clean_nobadge", generate_style_1_clean_nobadge()),
        ("style_1_clean_tag", generate_style_1_clean_tag()),
        ("style_3_minimal_full", generate_style_3_minimal_full()),
        ("style_3_minimal_short", generate_style_3_minimal_short()),
        ("style_1_no_arrow", generate_style_1_clean_nobadge().replace('<svg id="cta-arrow"', '<!-- <svg id="cta-arrow"').replace('</svg>', '</svg> -->')),
        ("style_3_no_arrow", generate_style_3_minimal_short().replace('<svg id="cta-arrow"', '<!-- <svg id="cta-arrow"').replace('</svg>', '</svg> -->')),
    ]

    for name, html in styles:
        html_file = TMP_DIR / f"{name}.html"
        out_png = OUT_DIR / f"{name}.png"
        html_file.write_text(html, encoding="utf-8")
        print(f"Wrote HTML: {html_file.name}")

        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--allow-file-access-from-files",
            f"--window-size=1080,1920",
            f"--screenshot={out_png}",
            str(html_file.resolve()),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_png.exists():
            print(f"Generated {out_png.name} ({out_png.stat().st_size} bytes)")
            art_file = CONV_ARTIFACTS / f"hat01_{name}.png"
            shutil.copy2(out_png, art_file)
            print(f"Copied to Artifacts: {art_file.name}")
        else:
            print(f"Error generating {name}: {res.stderr}")

if __name__ == "__main__":
    main()
