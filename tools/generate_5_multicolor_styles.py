#!/usr/bin/env python3
"""Generate 5 Distinct High-Aesthetic Multi-Color Layout Options for Hatari 16" (HAT01).
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
TMP_DIR = ROOT / ".tmp" / "multicolor_5styles"
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
  padding: 5px 13px; border-radius: 20px;
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
.badge-style {
  font-family: "Kanit Black", sans-serif;
  font-size: 32px;
  background: #1b1a17;
  color: #ffe600;
  padding: 8px 26px;
  border-radius: 28px;
  box-shadow: 0 8px 18px rgba(0,0,0,0.18);
  display: inline-block;
}
"""

def generate_style_1():
    """Style 1: The Grand 6-Color Panorama Arc (พัดโค้งอลังการ 6 สีหลักครบเซ็ต)"""
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
  <div class="badge-style">🎨 มีให้เลือกครบ 6 สีพาสเทล</div>
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

def generate_style_2():
    """Style 2: 2-Tier 3D Studio Showcase (เวที 2 ชั้น หน้า 3 หลัง 3 ลึกมีมิติ)"""
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
/* Back Tier: Yellow, Blue, Purple (elevated, smaller 380px, z=3) */
.b1 {{ left: 90px; top: 40px; z-index: 3; }}
.b1 img {{ width: 380px; filter: drop-shadow(0 10px 14px rgba(0,0,0,0.18)); }}
.sb1 {{ width: 240px; height: 32px; left: 160px; top: 580px; z-index: 2; }}

.b2 {{ left: 350px; top: 15px; z-index: 3; }}
.b2 img {{ width: 380px; filter: drop-shadow(0 10px 14px rgba(0,0,0,0.18)); }}
.sb2 {{ width: 240px; height: 32px; left: 420px; top: 555px; z-index: 2; }}

.b3 {{ right: 90px; top: 40px; z-index: 3; }}
.b3 img {{ width: 380px; filter: drop-shadow(0 10px 14px rgba(0,0,0,0.18)); }}
.sb3 {{ width: 240px; height: 32px; right: 160px; top: 580px; z-index: 2; }}

/* Front Tier: Mint, White Hero, Pink (z=10) */
.f-left {{ left: 70px; top: 220px; z-index: 10; }}
.f-left img {{ width: 470px; transform: rotate(-3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.24)); }}
.sf-left {{ width: 300px; height: 40px; left: 155px; top: 880px; z-index: 9; }}

.f-center {{ left: 290px; top: 160px; z-index: 15; }}
.f-center img {{ width: 530px; filter: drop-shadow(0 20px 26px rgba(0,0,0,0.28)); }}
.sf-center {{ width: 350px; height: 44px; left: 380px; top: 915px; z-index: 14; }}

.f-right {{ right: 70px; top: 220px; z-index: 10; }}
.f-right img {{ width: 470px; transform: rotate(3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.24)); }}
.sf-right {{ width: 300px; height: 40px; right: 155px; top: 880px; z-index: 9; }}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <h1 class="t-brand">Hatari · <span class="hl">พัดลม 16 นิ้ว</span></h1>
  <p class="t-sub">พลังลมตัวจบ · กดตะกร้าเหลือง</p>
</div>

<div id="showcase">
  <!-- Back Row -->
  <div class="contact-shadow sb1"></div>
  <div class="fan-wrap b1"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_yellow.png"></div>

  <div class="contact-shadow sb2"></div>
  <div class="fan-wrap b2"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_blue.png"></div>

  <div class="contact-shadow sb3"></div>
  <div class="fan-wrap b3"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_purple.png"></div>

  <!-- Front Row -->
  <div class="contact-shadow sf-left"></div>
  <div class="fan-wrap f-left"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow sf-right"></div>
  <div class="fan-wrap f-right"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow sf-center"></div>
  <div class="fan-wrap f-center"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 730 C 70 920, 50 1260, 95 1530" />
  <path d="M 25 1445 L 95 1530 L 190 1480" />
</svg>

<div class="bottom-info">
  <div class="badge-style">✨ 6 สีมินิมอล ดีไซน์แมทช์ได้ทุกห้อง</div>
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

def generate_style_3():
    """Style 3: Trio Hero + 6-Color Swatch Strip (3 ตัวหลักเด่นคมชัด + แถบพาเลตต์ 6 สีครบ)"""
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

/* Swatch Strip Container */
.swatch-card {{
  background: #ffffff;
  border: 4px solid #1b1a17;
  border-radius: 28px;
  box-shadow: 6px 8px 0 #1b1a17;
  padding: 14px 24px;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}}
.swatch-title {{
  font-family: "Kanit Black", sans-serif;
  font-size: 28px; color: #1b1a17;
}}
.chips-grid {{
  display: flex; gap: 10px; justify-content: center;
}}
.chip-item {{
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  font-size: 22px; font-weight: 700; color: #333;
}}
.chip-dot {{
  width: 36px; height: 36px; border-radius: 50%;
  border: 3px solid #1b1a17; box-shadow: 2px 3px 0 rgba(0,0,0,0.2);
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
    <div class="swatch-title">🎨 มีให้เลือกครบ 6 โทนสีพาสเทล</div>
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

def generate_style_4():
    """Style 4: Editorial Dynamic Cascade (ขั้นบันไดแคตตาล็อกสไตล์มินิมอลญี่ปุ่น MUJI)"""
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
/* Dynamic Diagonal Cascade from left-back to right-front */
.c1 {{ left: 20px; top: 40px; z-index: 2; }}
.c1 img {{ width: 350px; transform: rotate(-5deg); filter: drop-shadow(0 10px 14px rgba(0,0,0,0.18)); }}
.sc1 {{ width: 220px; height: 30px; left: 80px; top: 570px; z-index: 1; }}

.c2 {{ left: 130px; top: 80px; z-index: 4; }}
.c2 img {{ width: 380px; transform: rotate(-3deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.20)); }}
.sc2 {{ width: 240px; height: 32px; left: 200px; top: 640px; z-index: 3; }}

.c3 {{ left: 250px; top: 120px; z-index: 6; }}
.c3 img {{ width: 410px; transform: rotate(-1deg); filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22)); }}
.sc3 {{ width: 260px; height: 34px; left: 325px; top: 710px; z-index: 5; }}

.c4 {{ left: 370px; top: 160px; z-index: 8; }}
.c4 img {{ width: 440px; transform: rotate(1deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.24)); }}
.sc4 {{ width: 280px; height: 36px; left: 450px; top: 780px; z-index: 7; }}

.c5 {{ left: 490px; top: 200px; z-index: 10; }}
.c5 img {{ width: 470px; transform: rotate(3deg); filter: drop-shadow(0 18px 22px rgba(0,0,0,0.26)); }}
.sc5 {{ width: 300px; height: 38px; left: 575px; top: 850px; z-index: 9; }}

.c6 {{ left: 590px; top: 230px; z-index: 12; }}
.c6 img {{ width: 510px; transform: rotate(4deg); filter: drop-shadow(0 20px 26px rgba(0,0,0,0.28)); }}
.sc6 {{ width: 330px; height: 42px; left: 680px; top: 920px; z-index: 11; }}

/* Left Editorial Badge */
.editorial-badge {{
  position: absolute; left: 60px; top: 180px; z-index: 20;
  display: flex; flex-direction: column; gap: 8px;
}}
.tag-black {{
  font-family: "Kanit Black", sans-serif;
  font-size: 32px; background: #1b1a17; color: #ffe600;
  padding: 6px 20px; border-radius: 18px; box-shadow: 4px 6px 0 rgba(0,0,0,0.2);
}}
.tag-white {{
  font-family: "Anuphan", sans-serif; font-weight: 700;
  font-size: 26px; background: #ffffff; color: #1b1a17; border: 3px solid #1b1a17;
  padding: 4px 16px; border-radius: 14px; box-shadow: 3px 5px 0 #1b1a17;
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
  <div class="editorial-badge">
    <div class="tag-black">PASTEL SERIES</div>
    <div class="tag-white">6 เฉดสีพาสเทลยอดฮิต</div>
  </div>

  <!-- Cascade: Purple -> Yellow -> Blue -> Pink -> Mint -> White Hero -->
  <div class="contact-shadow sc1"></div>
  <div class="fan-wrap c1"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_purple.png"></div>

  <div class="contact-shadow sc2"></div>
  <div class="fan-wrap c2"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_yellow.png"></div>

  <div class="contact-shadow sc3"></div>
  <div class="fan-wrap c3"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_blue.png"></div>

  <div class="contact-shadow sc4"></div>
  <div class="fan-wrap c4"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow sc5"></div>
  <div class="fan-wrap c5"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow sc6"></div>
  <div class="fan-wrap c6"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 830 C 70 990, 50 1260, 95 1530" />
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

def generate_style_5():
    """Style 5: The All 7 Variants Ultimate Panoramic Lineup (รวมครบ 7 สีจริง รวมสีทราย/ครีม Sand)"""
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
/* 7 Fans Layered Symmetrically */
/* Far Left: Sand (Cream) */
.g1 {{ left: -60px; top: 250px; z-index: 2; }}
.g1 img {{ width: 330px; transform: rotate(-9deg); filter: drop-shadow(0 10px 14px rgba(0,0,0,0.20)); }}
.sg1 {{ width: 210px; height: 30px; left: 0px; top: 760px; z-index: 1; }}

/* Mid Left 1: Yellow */
.g2 {{ left: 80px; top: 190px; z-index: 4; }}
.g2 img {{ width: 380px; transform: rotate(-6deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.sg2 {{ width: 240px; height: 34px; left: 150px; top: 775px; z-index: 3; }}

/* Inner Left: Mint */
.g3 {{ left: 210px; top: 140px; z-index: 8; }}
.g3 img {{ width: 430px; transform: rotate(-3deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.24)); }}
.sg3 {{ width: 280px; height: 38px; left: 285px; top: 800px; z-index: 7; }}

/* Center: White Hero */
.g4 {{ left: 320px; top: 80px; z-index: 15; }}
.g4 img {{ width: 500px; filter: drop-shadow(0 20px 26px rgba(0,0,0,0.28)); }}
.sg4 {{ width: 330px; height: 42px; left: 405px; top: 815px; z-index: 14; }}

/* Inner Right: Blue */
.g5 {{ left: 490px; top: 130px; z-index: 9; }}
.g5 img {{ width: 440px; transform: rotate(2deg); filter: drop-shadow(0 16px 20px rgba(0,0,0,0.24)); }}
.sg5 {{ width: 280px; height: 38px; left: 570px; top: 795px; z-index: 8; }}

/* Mid Right 1: Pink */
.g6 {{ left: 630px; top: 180px; z-index: 6; }}
.g6 img {{ width: 390px; transform: rotate(5deg); filter: drop-shadow(0 12px 16px rgba(0,0,0,0.22)); }}
.sg6 {{ width: 250px; height: 34px; left: 700px; top: 775px; z-index: 5; }}

/* Far Right: Purple */
.g7 {{ left: 760px; top: 240px; z-index: 2; }}
.g7 img {{ width: 340px; transform: rotate(8deg); filter: drop-shadow(0 10px 14px rgba(0,0,0,0.20)); }}
.sg7 {{ width: 220px; height: 30px; left: 820px; top: 765px; z-index: 1; }}
.color-row .color-pill {{
  font-size: 21px; padding: 4px 10px; gap: 6px;
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
  <div class="contact-shadow sg1"></div>
  <div class="fan-wrap g1"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_sand_hi.png"></div>

  <div class="contact-shadow sg2"></div>
  <div class="fan-wrap g2"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_yellow.png"></div>

  <div class="contact-shadow sg3"></div>
  <div class="fan-wrap g3"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_mint.png"></div>

  <div class="contact-shadow sg4"></div>
  <div class="fan-wrap g4"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_white.png"></div>

  <div class="contact-shadow sg5"></div>
  <div class="fan-wrap g5"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_blue.png"></div>

  <div class="contact-shadow sg6"></div>
  <div class="fan-wrap g6"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_pink.png"></div>

  <div class="contact-shadow sg7"></div>
  <div class="fan-wrap g7"><img src="../../03_Projects/_HyperFrames_Studio/assets/hatari01/cutouts/hatari_purple.png"></div>
</div>

<svg id="cta-arrow" viewBox="0 0 1080 1920">
  <path d="M 180 730 C 70 920, 50 1260, 95 1530" />
  <path d="M 25 1445 L 95 1530 L 190 1480" />
</svg>

<div class="bottom-info">
  <div class="badge-style">👑 ครบจบทุก 7 เฉดสีจริง (รวมสีพิเศษทราย)</div>
  <div class="color-row">
    <div class="color-pill"><span class="dot" style="background:#ffffff"></span>ขาว</div>
    <div class="color-pill"><span class="dot" style="background:#b8e0c8"></span>มิ้นท์</div>
    <div class="color-pill"><span class="dot" style="background:#f7c8d0"></span>ชมพู</div>
    <div class="color-pill"><span class="dot" style="background:#b8d8ea"></span>ฟ้า</div>
    <div class="color-pill"><span class="dot" style="background:#faeec2"></span>เหลือง</div>
    <div class="color-pill"><span class="dot" style="background:#d9c5ea"></span>ม่วง</div>
    <div class="color-pill"><span class="dot" style="background:#d9cdb8"></span>ทราย</div>
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
        ("style_1_arc_6colors", generate_style_1()),
        ("style_2_twotier_showcase", generate_style_2()),
        ("style_3_trio_swatchstrip", generate_style_3()),
        ("style_4_catalog_cascade", generate_style_4()),
        ("style_5_all7_ultimate", generate_style_5()),
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
            # Copy to conversation artifacts
            art_file = CONV_ARTIFACTS / f"hat01_{name}.png"
            shutil.copy2(out_png, art_file)
            print(f"Copied to Artifacts: {art_file.name}")
        else:
            print(f"Error generating {name}: {res.stderr}")

if __name__ == "__main__":
    main()
