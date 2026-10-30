#!/usr/bin/env python3
"""Generate Master Cover Prototypes (1080x1920) for various product categories
using the Master Style 3B Golden Formula (Zero-Emoji, Zero-Arrow, 3-Tier Layout,
Realistic Contact Shadow, Adaptive Product Strategy).

Products:
1. สายชาร์จ: Orsen by Eloop S6 240W (Multi-Color Cable with Swatch Strip)
2. หัวชาร์จ: Essager PD 30W (Single Hero 3D Perspective + Floating Feature Badges)
3. หัวชาร์จคู่: Essager PD 30W Duo (Dual-Color Black & White Showcase)
4. พัดลมตั้งโต๊ะ: Hatari Cyclone Max 8 นิ้ว PS8M1 (Modern Desk Fan)
5. พัดลมแม่เหล็กไอที: HOYAUP Magnetic Gaming Cooler (Tech Gadget Cooler)
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
PAPER_BG = STUDIO / "assets" / "shared" / "paper_bg_frame0.jpg"
OUT_DIR = ROOT / "05_Covers_Thumbnails" / "product_cover_prototypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = ROOT / ".tmp" / "cover_prototypes"
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
  font-size: 84px; line-height: 1.15;
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
  z-index: 20;
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
  position: absolute; bottom: 275px; left: 40px; right: 40px;
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

def generate_cover_1_cable():
    """1. Orsen S6 240W Braided Cable (Multi-Color Cable with Swatch Strip)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Orsen S6 240W Cable</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 380px; left: 0; width: 1080px; height: 860px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.cable-img {{
  width: 660px; height: 660px;
  object-fit: contain;
  filter: drop-shadow(0 14px 28px rgba(0,0,0,0.18));
  z-index: 10;
}}
#cs-cable {{
  width: 580px; height: 95px;
  bottom: 80px; left: 50%;
  transform: translateX(-50%);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">ORSEN · S6 240W</span></div>
  <div class="t-sub">สายถักทนทาน · ชาร์จเร็วตัวจบ</div>
</div>

<div id="stage">
  <div class="contact-shadow" id="cs-cable"></div>
  <img class="cable-img" src="../../03_Projects/_HyperFrames_Studio/assets/ors01/img/cut_coil_240w.png">
  
  <div class="floating-badge" style="top: 140px; right: 80px; transform: rotate(3deg);">
    หัวชาร์จ 5A อลูมิเนียม
  </div>
  <div class="floating-badge" style="bottom: 150px; left: 80px; transform: rotate(-3deg);">
    ความยาว 1.5 เมตรพอดีมือ
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


def generate_cover_2_charger_single():
    """2. Essager PD 30W Single Hero (3D Perspective + Floating Feature Badges)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Essager PD 30W Single</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 380px; left: 0; width: 1080px; height: 860px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.charger-img {{
  width: 580px; height: 580px;
  object-fit: contain;
  filter: drop-shadow(0 16px 32px rgba(0,0,0,0.22));
  z-index: 10;
}}
#cs-charger {{
  width: 440px; height: 85px;
  bottom: 120px; left: 50%;
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
  
  <div class="floating-badge" style="top: 150px; left: 70px; transform: rotate(-3deg);">
    ชิปคุมความร้อนอัจฉริยะ
  </div>
  <div class="floating-badge" style="top: 220px; right: 70px; transform: rotate(3deg);">
    แบต 0-60% ใน 30 นาที
  </div>
  <div class="floating-badge" style="bottom: 180px; left: 80px; transform: rotate(2deg);">
    ขาพับเก็บได้ พกพาสะดวก
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


def generate_cover_3_charger_duo():
    """3. Essager PD 30W Duo (Dual-Color Black & White Showcase)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Essager PD 30W Duo</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 370px; left: 0; width: 1080px; height: 880px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.duo-img {{
  width: 680px; height: 680px;
  object-fit: contain;
  filter: drop-shadow(0 16px 32px rgba(0,0,0,0.20));
  z-index: 10;
}}
#cs-duo {{
  width: 620px; height: 95px;
  bottom: 85px; left: 50%;
  transform: translateX(-50%);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">ESSAGER · PD 30W</span></div>
  <div class="t-sub">มินิฟาสต์ชาร์จ · มีครบทั้ง 2 สี</div>
</div>

<div id="stage">
  <div class="contact-shadow" id="cs-duo"></div>
  <img class="duo-img" src="../../03_Projects/_HyperFrames_Studio/assets/ess02/img/essager_cutout_both.png">
  
  <div class="floating-badge" style="top: 130px; left: 80px; transform: rotate(-2deg);">
    ชาร์จไวไม่ทำร้ายแบต
  </div>
  <div class="floating-badge" style="top: 140px; right: 80px; transform: rotate(2deg);">
    ขนาดจิ๋ว เล็กกว่าบัตรเครดิต
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card">
    <span class="swatch-title">คู่สีพรีเมียม :</span>
    <div class="swatch-dots">
      <div class="swatch-item"><span class="dot" style="background: #1a1a1a;"></span> ดำมิดไนท์</div>
      <div class="swatch-item"><span class="dot" style="background: #ffffff;"></span> ขาวเพิร์ล</div>
    </div>
  </div>

  <div class="spec-row">
    <div class="spec-tag">จ่ายไฟเต็มสปีด 30W</div>
    <div class="spec-tag">ชิป GaN อุณหภูมิต่ำ</div>
    <div class="spec-tag">ไฟ LED สีฟ้าสถานะ</div>
    <div class="spec-tag">รองรับ iPad และมือถือทุกรุ่น</div>
  </div>
</div>

</body>
</html>
"""
    return html


def generate_cover_4_fan_cyclone():
    """4. Hatari Cyclone Max 8 นิ้ว PS8M1 (Modern Desk Fan)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: Hatari Cyclone Max Fan</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 380px; left: 0; width: 1080px; height: 860px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.fan-img {{
  width: 630px; height: 630px;
  object-fit: contain;
  filter: drop-shadow(0 18px 36px rgba(0,0,0,0.22));
  z-index: 10;
}}
#cs-fan {{
  width: 520px; height: 90px;
  bottom: 100px; left: 50%;
  transform: translateX(-50%);
}}
</style>
</head>
<body>
<img id="paper" src="../../03_Projects/_HyperFrames_Studio/assets/shared/paper_bg_frame0.jpg">

<div id="top-header">
  <div class="t-brand"><span class="hl">HATARI · CYCLONE MAX</span></div>
  <div class="t-sub">พลังลมเทอร์โบ · สวยมินิมอลสายแต่งห้อง</div>
</div>

<div id="stage">
  <div class="contact-shadow" id="cs-fan"></div>
  <img class="fan-img" src="../../03_Projects/_HyperFrames_Studio/assets/hatari02/img/hatari_cyclone_clean_cutout.png">
  
  <div class="floating-badge" style="top: 150px; left: 60px; transform: rotate(-3deg);">
    ลมแรงพุ่งไกล 5 เมตร
  </div>
  <div class="floating-badge" style="top: 200px; right: 60px; transform: rotate(3deg);">
    ปรับก้มเงยได้ 90 องศา
  </div>
  <div class="floating-badge" style="bottom: 170px; left: 80px; transform: rotate(2deg);">
    เงียบสนิท ไม่กวนสมาธิ
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card" style="padding: 9px 24px;">
    <span class="swatch-title">ดีไซน์มินิมอลโมเดิร์น วางมุมไหนของโต๊ะก็สวย</span>
  </div>

  <div class="spec-row">
    <div class="spec-tag">ใบพัดไซโคลน 8 นิ้ว</div>
    <div class="spec-tag">ปรับแรงลมได้ 3 ระดับ</div>
    <div class="spec-tag">มอเตอร์บอลแบริ่งทนทาน</div>
    <div class="spec-tag">รับประกันมอเตอร์ 3 ปี</div>
  </div>
</div>

</body>
</html>
"""
    return html


def generate_cover_5_cooler_hoyaup():
    """5. HOYAUP Magnetic Phone Cooler (Gaming Tech Gadget)"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cover: HOYAUP Magnetic Phone Cooler</title>
<style>
{CSS_BASE}
#stage {{
  position: absolute; top: 380px; left: 0; width: 1080px; height: 860px;
  display: flex; justify-content: center; align-items: center;
  z-index: 10;
}}
.cooler-img {{
  width: 600px; height: 600px;
  object-fit: contain;
  filter: drop-shadow(0 18px 36px rgba(0,0,0,0.25));
  z-index: 10;
}}
#cs-cooler {{
  width: 480px; height: 85px;
  bottom: 110px; left: 50%;
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
  
  <div class="floating-badge" style="top: 150px; left: 60px; transform: rotate(-3deg);">
    จอดิจิทัลบอกอุณหภูมิจริง
  </div>
  <div class="floating-badge" style="top: 200px; right: 60px; transform: rotate(3deg);">
    แม่เหล็ก MagSafe ดูดแน่น
  </div>
  <div class="floating-badge" style="bottom: 170px; right: 80px; transform: rotate(-2deg);">
    ไฟ RGB Gaming สวยงาม
  </div>
</div>

<div class="bottom-info">
  <div class="swatch-card" style="padding: 9px 24px;">
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
        ("cover_cable_orsen_s6.png", "orsen_s6.html", generate_cover_1_cable, "cover_1_cable_orsen_s6.png"),
        ("cover_charger_essager_single.png", "essager_single.html", generate_cover_2_charger_single, "cover_2_charger_essager_single.png"),
        ("cover_charger_essager_duo.png", "essager_duo.html", generate_cover_3_charger_duo, "cover_3_charger_essager_duo.png"),
        ("cover_fan_hatari_cyclone.png", "hatari_cyclone.html", generate_cover_4_fan_cyclone, "cover_4_fan_hatari_cyclone.png"),
        ("cover_cooler_hoyaup.png", "hoyaup_cooler.html", generate_cover_5_cooler_hoyaup, "cover_5_cooler_hoyaup.png"),
    ]
    
    print("Generating Master Style 3B Cover Prototypes for Various Products...")
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
