#!/usr/bin/env python3
"""Generate Refined Master Cover Prototypes responding to user feedback:
1. Multi-color cable: Show multiple colors (Trio Coils & Quad Heads Lineup)
2. Single product scaling: Enlarge HOYAUP cooler and Essager charger so they are bold,
   punchy, and not too small.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
OUT_DIR = ROOT / "05_Covers_Thumbnails" / "product_cover_prototypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = ROOT / ".tmp" / "refined_covers"
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
  position: absolute; top: 165px; left: 40px; right: 40px;
  text-align: center; z-index: 25;
}
.t-brand {
  font-family: "Kanit Black", sans-serif;
  font-size: 86px; line-height: 1.15;
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
.contact-shadow {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
  z-index: 5;
  pointer-events: none;
}
.floating-badge {
  position: absolute;
  z-index: 22;
  font-family: "Anuphan", sans-serif;
  font-weight: 700;
  font-size: 25px;
  background: #ffffff;
  color: #1b1a17;
  border: 3px solid #1b1a17;
  padding: 8px 18px;
  border-radius: 20px;
  box-shadow: 3px 5px 0 #1b1a17;
  white-space: nowrap;
}
.bottom-info {
  position: absolute; bottom: 270px; left: 40px; right: 40px;
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  z-index: 25;
}
.spec-row {
  display: flex; flex-wrap: wrap; justify-content: center;
  max-width: 960px; gap: 10px; margin: 0 auto;
}
.spec-tag {
  font-family: "Anuphan", sans-serif;
  font-weight: 700; font-size: 26px;
  background: #ffffff; color: #1b1a17;
  border: 3px solid #1b1a17;
  padding: 6px 18px; border-radius: 12px;
  box-shadow: 3px 5px 0 #1b1a17;
}
.swatch-card {
  background: #ffffff;
  border: 3px solid #1b1a17;
  border-radius: 18px;
  box-shadow: 3px 5px 0 #1b1a17;
  padding: 10px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.swatch-title {
  font-family: "Anuphan", sans-serif;
  font-weight: 700;
  font-size: 25px;
  color: #1b1a17;
}
.swatch-dots {
  display: flex;
  align-items: center;
  gap: 14px;
}
.swatch-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: "Anuphan", sans-serif;
  font-weight: 700;
  font-size: 22px;
  color: #1b1a17;
}
.dot {
  width: 22px; height: 22px;
  border-radius: 50%;
  border: 2px solid #1b1a17;
  display: inline-block;
  box-shadow: 1px 2px 0 rgba(0,0,0,0.15);
}
"""

def generate_cable_trio_coils():
    """Design 1A: Orsen S6 Multi-Color Trio Coils (Black, Pink, Green) like Hatari Style 3B"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Orsen S6 Trio Coils</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 370px; left: 0; width: 1080px; height: 880px;
  z-index: 10;
}}
.coil-wrapper {{
  position: absolute;
  transition: transform 0.3s;
}}
.coil-img {{
  object-fit: contain;
  filter: drop-shadow(0 14px 28px rgba(0,0,0,0.20));
}}
/* Left Coil: Pink */
#w-pink {{
  top: 130px; left: 80px;
  transform: rotate(-7deg);
  z-index: 11;
}}
#w-pink .coil-img {{
  width: 480px; height: 480px;
}}
#cs-pink {{
  width: 420px; height: 70px;
  bottom: -20px; left: 30px;
}}

/* Right Coil: Green */
#w-green {{
  top: 130px; right: 80px;
  transform: rotate(7deg);
  z-index: 12;
}}
#w-green .coil-img {{
  width: 480px; height: 480px;
}}
#cs-green {{
  width: 420px; height: 70px;
  bottom: -20px; left: 30px;
}}

/* Center Hero: Black */
#w-black {{
  top: 40px; left: 50%;
  transform: translateX(-50%);
  z-index: 15;
}}
#w-black .coil-img {{
  width: 580px; height: 580px;
  filter: drop-shadow(0 20px 40px rgba(0,0,0,0.28));
}}
#cs-black {{
  width: 520px; height: 85px;
  bottom: -25px; left: 30px;
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">ORSEN · S6 240W</span></div>
  <div class="t-sub">สายถักทนทาน · มีครบทั้ง 4 สีพาสเทล</div>
</div>

<div id="stage">
  <!-- Left: Pink Coil -->
  <div class="coil-wrapper" id="w-pink">
    <div class="contact-shadow" id="cs-pink"></div>
    <img class="coil-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/coils/coil_pink.png">
  </div>

  <!-- Right: Green Coil -->
  <div class="coil-wrapper" id="w-green">
    <div class="contact-shadow" id="cs-green"></div>
    <img class="coil-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/coils/coil_green.png">
  </div>

  <!-- Center Hero: Black Coil -->
  <div class="coil-wrapper" id="w-black">
    <div class="contact-shadow" id="cs-black"></div>
    <img class="coil-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/cut_coil_240w.png">
  </div>
  
  <div class="floating-badge" style="top: 80px; right: 70px; transform: rotate(3deg);">
    หัวชาร์จ 5A อลูมิเนียม
  </div>
  <div class="floating-badge" style="bottom: 90px; left: 70px; transform: rotate(-3deg);">
    สายถักทนทาน ไม่หักงอง่าย
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card">
    <span class="swatch-title">มีให้เลือกครบ 4 สี :</span>
    <div class="swatch-dots">
      <div class="swatch-item"><span class="dot" style="background: #1f1f1f;"></span> ดำด้าน</div>
      <div class="swatch-item"><span class="dot" style="background: #fdfdfd;"></span> ขาวคลีน</div>
      <div class="swatch-item"><span class="dot" style="background: #a4c49f;"></span> เขียวเซจ</div>
      <div class="swatch-item"><span class="dot" style="background: #f4b6c6;"></span> ชมพูพาสเทล</div>
    </div>
  </div>

  <div class="spec-row">
    <div class="spec-tag">กำลังไฟสูงสุด 240W</div>
    <div class="spec-tag">ชิปอัจฉริยะ E-MARK</div>
    <div class="spec-tag">สายถักหนา 48 เส้น</div>
    <div class="spec-tag">ถ่ายโอนไว 480Mbps</div>
  </div>
</div>

</body>
</html>
"""
    return html


def generate_cable_quad_heads():
    """Design 1B: Hero 240W Coil + 4 Aluminum Heads Lineup (Black, White, Green, Pink)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Orsen S6 Quad Heads</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 370px; left: 0; width: 1080px; height: 880px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  z-index: 10;
}}
.coil-bg {{
  width: 610px; height: 610px;
  object-fit: contain;
  filter: drop-shadow(0 14px 28px rgba(0,0,0,0.18));
  position: absolute;
  top: 30px; left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  opacity: 0.95;
}}
#cs-coil {{
  width: 560px; height: 85px;
  bottom: 220px; left: 50%;
  transform: translateX(-50%);
}}
.heads-lineup {{
  position: absolute;
  bottom: 60px;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 36px;
  z-index: 20;
}}
.head-item {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}}
.head-img {{
  height: 380px;
  width: auto;
  object-fit: contain;
  filter: drop-shadow(0 10px 18px rgba(0,0,0,0.25));
}}
.head-label {{
  font-family: "Anuphan", sans-serif;
  font-weight: 700;
  font-size: 22px;
  background: #ffffff;
  color: #1b1a17;
  border: 2.5px solid #1b1a17;
  padding: 3px 12px;
  border-radius: 12px;
  box-shadow: 2px 3px 0 #1b1a17;
  white-space: nowrap;
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">ORSEN · S6 240W</span></div>
  <div class="t-sub">สายถักทนทาน · หัวชาร์จอลูมิเนียม 4 สี</div>
</div>

<div id="stage">
  <div class="contact-shadow" id="cs-coil"></div>
  <img class="coil-bg" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/cut_coil_240w.png">

  <!-- 4 Heads Lineup in Foreground -->
  <div class="heads-lineup">
    <div class="head-item" style="transform: rotate(-3deg);">
      <img class="head-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/head_black.png">
      <span class="head-label">ดำด้าน</span>
    </div>
    <div class="head-item" style="transform: rotate(-1deg); margin-bottom: 12px;">
      <img class="head-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/head_white.png">
      <span class="head-label">ขาวคลีน</span>
    </div>
    <div class="head-item" style="transform: rotate(1deg); margin-bottom: 12px;">
      <img class="head-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/head_green.png">
      <span class="head-label">เขียวเซจ</span>
    </div>
    <div class="head-item" style="transform: rotate(3deg);">
      <img class="head-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/head_pink.png">
      <span class="head-label">ชมพูพาสเทล</span>
    </div>
  </div>

  <div class="floating-badge" style="top: 40px; right: 90px; transform: rotate(3deg);">
    ชาร์จไวแรง 240W เต็มสปีด
  </div>
  <div class="floating-badge" style="top: 60px; left: 90px; transform: rotate(-3deg);">
    ยาว 1.5 เมตร สายถัก 48 เส้น
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card" style="padding: 8px 24px;">
    <span class="swatch-title">ดีไซน์พรีเมียม 4 สไตล์ เข้ากับทุกอุปกรณ์ Type-C</span>
  </div>

  <div class="spec-row">
    <div class="spec-tag">กำลังไฟสูงสุด 240W</div>
    <div class="spec-tag">ชิปอัจฉริยะ E-MARK</div>
    <div class="spec-tag">สายถักทนทาน 48 เส้น</div>
    <div class="spec-tag">ถ่ายโอนไว 480Mbps</div>
  </div>
</div>

</body>
</html>
"""
    return html


def generate_hoyaup_enlarged():
    """Design 2A: HOYAUP Cooler ENLARGED to 760px (Macro Punchy Hero, No Emptiness)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: HOYAUP Cooler Enlarged</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 350px; left: 0; width: 1080px; height: 910px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.cooler-img {{
  width: 780px; height: 780px;
  object-fit: contain;
  filter: drop-shadow(0 24px 48px rgba(0,0,0,0.30));
  z-index: 10;
}}
#cs-cooler {{
  width: 640px; height: 110px;
  bottom: 75px; left: 50%;
  transform: translateX(-50%);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">HOYAUP · พัดลมแม่เหล็ก</span></div>
  <div class="t-sub">ไอทีสายเกมตัวจบ · เย็นจัดติดลบ</div>
</div>

<div id="stage">
  <div class="contact-shadow" id="cs-cooler"></div>
  <img class="cooler-img" src="../../03_Projects/_HyperFrames_Studio/assets/hoy01/img/hoyaup_clean_cutout.png">
  
  <div class="floating-badge" style="top: 100px; left: 60px; transform: rotate(-3deg);">
    จอดิจิทัลบอกอุณหภูมิจริง
  </div>
  <div class="floating-badge" style="top: 140px; right: 60px; transform: rotate(3deg);">
    แม่เหล็ก MagSafe ดูดแน่น
  </div>
  <div class="floating-badge" style="bottom: 120px; right: 70px; transform: rotate(-2deg);">
    ไฟ RGB Gaming สวยงาม
  </div>
  <div class="floating-badge" style="bottom: 120px; left: 70px; transform: rotate(2deg);">
    เย็นเร็วทันใจใน 3 วิ
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card" style="padding: 9px 26px;">
    <span class="swatch-title">ลดความร้อนทันที เล่นเกมลื่น เฟรมเรตไม่ดรอป</span>
  </div>

  <div class="spec-row">
    <div class="spec-tag">ชิปเซมิคอนดักเตอร์ 24W</div>
    <div class="spec-tag">แผ่นความเย็นขนาดใหญ่</div>
    <div class="spec-tag">น้ำหนักเบาหวิวเพียง 83g</div>
    <div class="spec-tag">เสียงเงียบ ไม่เข้าไมค์</div>
  </div>
</div>

</body>
</html>
"""
    return html


def generate_charger_essager_enlarged():
    """Design 2B: Essager PD 30W ENLARGED to 720px (Bold 3D Perspective Hero)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Essager PD 30W Enlarged</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 350px; left: 0; width: 1080px; height: 910px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.charger-img {{
  width: 730px; height: 730px;
  object-fit: contain;
  filter: drop-shadow(0 22px 44px rgba(0,0,0,0.26));
  z-index: 10;
}}
#cs-charger {{
  width: 560px; height: 100px;
  bottom: 95px; left: 50%;
  transform: translateX(-50%);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">ESSAGER · PD 30W</span></div>
  <div class="t-sub">ไซส์มินิไม่ร้อน · ชาร์จไวตัวจบ</div>
</div>

<div id="stage">
  <div class="contact-shadow" id="cs-charger"></div>
  <img class="charger-img" src="../../03_Projects/_HyperFrames_Studio/assets/ess02/img/essager_clean_cutout.png">
  
  <div class="floating-badge" style="top: 110px; left: 60px; transform: rotate(-3deg);">
    ชิปคุมความร้อนอัจฉริยะ
  </div>
  <div class="floating-badge" style="top: 180px; right: 60px; transform: rotate(3deg);">
    แบต 0-60% ใน 30 นาที
  </div>
  <div class="floating-badge" style="bottom: 140px; left: 70px; transform: rotate(2deg);">
    ขาพับเก็บได้ พกพาสะดวก
  </div>
  <div class="floating-badge" style="bottom: 140px; right: 70px; transform: rotate(-2deg);">
    ขนาดจิ๋ว น้ำหนักเบา
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card">
    <span class="swatch-title">2 สีคลาสสิก :</span>
    <div class="swatch-dots">
      <div class="swatch-item"><span class="dot" style="background: #1a1a1a;"></span> ดำด้าน (Matte Black)</div>
      <div class="swatch-item"><span class="dot" style="background: #ffffff;"></span> ขาวเซรามิก (Ceramic White)</div>
    </div>
  </div>

  <div class="spec-row">
    <div class="spec-tag">เทคโนโลยี GaN ชาร์จไว</div>
    <div class="spec-tag">ระบบเซฟตี้ ปลอดภัย 6 ชั้น</div>
    <div class="spec-tag">พอร์ต Type-C ปากส้ม</div>
    <div class="spec-tag">รองรับ iPhone 8-16</div>
  </div>
</div>

</body>
</html>
"""
    return html


def render_html_to_png(html_content, out_png_path, tmp_html_name):
    tmp_html = TMP_DIR / tmp_html_name
    tmp_html.write_text(html_content, encoding="utf-8")
    
    file_url = f"file:///{str(tmp_html.resolve()).replace(os.sep, '/')}"
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--window-size=1080,1920",
        f"--screenshot={str(out_png_path)}",
        file_url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error rendering {tmp_html_name}: {res.stderr}")
        return False
    return True


def main():
    items = [
        ("refined_cable_1_trio_coils.png", "cable_trio.html", generate_cable_trio_coils, "refined_cable_1_trio_coils.png"),
        ("refined_cable_2_quad_heads.png", "cable_quad.html", generate_cable_quad_heads, "refined_cable_2_quad_heads.png"),
        ("refined_cooler_hoyaup_enlarged.png", "hoyaup_enlarged.html", generate_hoyaup_enlarged, "refined_cooler_hoyaup_enlarged.png"),
        ("refined_charger_essager_enlarged.png", "essager_enlarged.html", generate_charger_essager_enlarged, "refined_charger_essager_enlarged.png"),
    ]
    
    print("Generating Refined Master Cover Prototypes based on User Feedback...")
    for out_name, tmp_html_name, gen_fn, artifact_name in items:
        out_png = OUT_DIR / out_name
        html = gen_fn()
        ok = render_html_to_png(html, out_png, tmp_html_name)
        if ok and out_png.exists():
            size_kb = out_png.stat().st_size / 1024
            print(f"[OK] Rendered {out_name} ({size_kb:.1f} KB)")
            # Copy to artifacts
            art_dest = CONV_ARTIFACTS / artifact_name
            shutil.copy2(out_png, art_dest)
            print(f"  -> Copied to artifact: {artifact_name}")
        else:
            print(f"[FAIL] Failed {out_name}")

if __name__ == "__main__":
    main()
