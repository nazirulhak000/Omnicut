"""Apply Proven Orsen-style CTA Cover & Audio Clipping Fix to all 20 Essager clips (s01-s20).
Matches the clean, high-performing layout from Orsen S6:
- Top: 'กดตะกร้าเหลือง' (Yellow marker highlight)
- Sub: 'Essager · PD 30W · ชาร์จเร็วตัวจบ' (Red bold)
- Center: Product hero image + color badges + spec badges
- Left: Curved red arrow swooping down to bottom-left
- Bottom-left: 'ซ้ายล่าง' (Kanit Black 120px)
- Audio: SFX headroom + 120ms cosine tail fade-out
"""
import re
import sys
import wave
from pathlib import Path
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO / "clips"
COMPS_DIR = STUDIO / "compositions"
ASSETS_DIR = STUDIO / "assets" / "clips"

ORSEN_STYLE_CSS = """      /* ==================== CTA OUTRO SHOT (PROVEN ORSEN STYLE) ==================== */
      #b-cta {
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
      }
      .t {
        font-family: "Kanit Black", sans-serif;
        color: var(--ink);
        text-align: center;
        line-height: 1.1;
      }
      .t.center {
        text-align: center;
        width: 100%;
        left: 0;
        right: 0;
      }
      #cta-1 {
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
      }
      #cta-hero {
        position: absolute;
        top: 470px;
        left: 0;
        right: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
      }
      #cta-hero img.coil {
        width: 630px;
        height: 630px;
        object-fit: contain;
        filter: drop-shadow(0 16px 24px rgba(27, 26, 23, 0.25));
      }
      .color-row {
        display: flex;
        gap: 16px;
      }
      .color-pill {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 34px;
        color: #111111;
        background: #ffffff;
        border: 4px solid var(--ink);
        padding: 6px 24px;
        border-radius: 24px;
        box-shadow: 4px 6px 0 var(--ink);
      }
      .color-pill.black {
        background: #1e1e1e;
        color: #ffffff;
      }
      .color-pill.white {
        background: #ffffff;
        color: #111111;
      }
      .spec-row {
        display: flex;
        gap: 14px;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 30px;
        background: #fff;
        border: 3px solid var(--ink);
        padding: 6px 20px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        color: #1b1a17;
      }
      #cta-arrow {
        position: absolute;
        inset: 0;
        pointer-events: none;
      }
      #cta-arrow path {
        fill: none;
        stroke: var(--line-red);
        stroke-width: 18;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      #cta-2 {
        position: absolute;
        left: 120px;
        bottom: 220px;
        font-size: 120px;
        color: var(--line-red);
      }"""

ORSEN_DOM_TEMPLATE = """      <div data-hf-id="hf-pdrw" class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">กดตะกร้าเหลือง</span></div>
        <div class="t center" id="cta-model">Essager · PD 30W · ชาร์จเร็วตัวจบ</div>
        <div id="cta-hero">
          <img class="coil" src="assets/ess02/img/essager_clean_cutout.png" alt="Essager PD 30W Fast Charger">
          <div class="color-row">
            <span class="color-pill black">สีดำ</span>
            <span class="color-pill white">สีขาว</span>
          </div>
          <div class="spec-row">
            <span class="spec-tag">PD 30W ชาร์จเร็ว</span>
            <span class="spec-tag">ชิปคุมอุณหภูมิ</span>
            <span class="spec-tag">ระบบเซฟตี้ 6 ชั้น</span>
          </div>
        </div>
        <svg class="fx" id="cta-arrow" viewBox="0 0 1080 1920">
          <path id="cta-shaft" d="M 220 700 C 120 900 80 1190 140 1460" stroke-dasharray="1000" stroke-dashoffset="1000" />
          <path id="cta-head" d="M 60 1380 L 140 1470 L 230 1390" stroke-dasharray="400" stroke-dashoffset="400" />
        </svg>
        <div class="t" id="cta-2">ซ้ายล่าง</div>
      </div>"""

ORSEN_GSAP = """      tl.to("#chatwin", { y: 140, opacity: 0, duration: 0.25, ease: "power2.in" }, CTA_T - 0.25);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.2, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { scale: 1.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "power4.out" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "power3.out" }, CTA_T + 0.22);
      tl.fromTo("#cta-hero img.coil", { scale: 0.4, rotation: -15, opacity: 0 }, { scale: 1, rotation: 0, opacity: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.30);
      tl.fromTo(".color-pill", { scale: 0, opacity: 0, y: 20 }, { scale: 1, opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)", stagger: 0.07 }, CTA_T + 0.48);
      tl.fromTo(".spec-tag", { scale: 0, opacity: 0, y: 15 }, { scale: 1, opacity: 1, y: 0, duration: 0.25, ease: "back.out(2)", stagger: 0.06 }, CTA_T + 0.62);
      tl.fromTo("#cta-shaft", { strokeDashoffset: 1000 }, { strokeDashoffset: 0, duration: 0.45, ease: "power2.inOut" }, CTA_T + 0.40);
      tl.fromTo("#cta-head", { strokeDashoffset: 400 }, { strokeDashoffset: 0, duration: 0.18, ease: "power2.out" }, CTA_T + 0.80);
      tl.fromTo("#cta-2", { x: -80, opacity: 0 }, { x: 0, opacity: 1, duration: 0.3, ease: "expo.out" }, CTA_T + 0.90);
      tl.to("#cta-arrow", { x: -18, y: 18, duration: 0.25, ease: "sine.inOut", yoyo: true, repeat: 3 }, CTA_T + 1.20);"""

def fix_vo_wav(vo_path: Path):
    """Apply a 120ms cosine fade-out at the end of vo.wav to prevent click/pop/abrupt cutoff."""
    if not vo_path.exists():
        return False
    with wave.open(str(vo_path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)
    
    pcm = np.frombuffer(data, dtype=np.int16).copy()
    fade_len = int(0.12 * framerate) * nchannels
    if len(pcm) > fade_len:
        fade_steps = fade_len // nchannels
        mono_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_steps)))
        if nchannels == 2:
            stereo_curve = np.repeat(mono_curve, 2)
            pcm[-fade_len:] = (pcm[-fade_len:] * stereo_curve).astype(np.int16)
        else:
            pcm[-fade_len:] = (pcm[-fade_len:] * mono_curve).astype(np.int16)
        
        with wave.open(str(vo_path), "wb") as wf:
            wf.setnchannels(nchannels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(framerate)
            wf.writeframes(pcm.tobytes())
        return True
    return False

def update_html_content(content: str) -> str:
    # 0. Ensure body & #root have explicit 1080x1920 sizing
    if '#root {' in content and 'height: 1920px;' not in content.split('#root {')[1].split('}')[0]:
        content = re.sub(
            r'#root\s*\{\s*background:\s*#efece6;\s*\}',
            '''body {
        margin: 0;
        padding: 0;
        background: #111111;
        display: flex;
        justify-content: center;
        align-items: center;
      }
      #root {
        position: relative;
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: #efece6;
        box-sizing: border-box;
      }''',
            content,
            count=1
        )

    # 1. Update CSS: replace old CTA CSS (or existing minimal) up to #wm {
    css_pattern = re.compile(
        r'(/\*\s*(?:CTA Outro|CTA card|==================== MINIMALIST CTA COVER POSTER ====================|==================== CTA OUTRO SHOT \(PROVEN ORSEN STYLE\) ====================)\s*\*/.*?)(?=\s*#wm\s*\{)',
        re.DOTALL
    )
    if not css_pattern.search(content):
        css_pattern = re.compile(r'(#b-cta\s*\{.*?)(?=\s*#wm\s*\{)', re.DOTALL)
    
    content = css_pattern.sub(ORSEN_STYLE_CSS, content, count=1)

    # 2. Update DOM: find #b-cta element and extract its data-start and data-duration
    dom_pattern = re.compile(
        r'<div[^>]*id="b-cta"[^>]*data-start="([^"]+)"[^>]*data-duration="([^"]+)"[^>]*>.*?</div>\s*(?=<div[^>]*id="paper-tint")',
        re.DOTALL
    )
    m = dom_pattern.search(content)
    if m:
        cta_start, cta_dur = m.group(1), m.group(2)
        new_dom = ORSEN_DOM_TEMPLATE.format(cta_start=cta_start, cta_dur=cta_dur)
        content = dom_pattern.sub(new_dom, content, count=1)
    else:
        dom_pattern2 = re.compile(
            r'<div[^>]*id="b-cta"[^>]*>.*?</div>\s*(?=<div[^>]*id="paper-tint")',
            re.DOTALL
        )
        sm = re.search(r'id="b-cta"[^>]*data-start="([^"]+)"', content)
        dm = re.search(r'id="b-cta"[^>]*data-duration="([^"]+)"', content)
        cta_start = sm.group(1) if sm else "50.0"
        cta_dur = dm.group(1) if dm else "6.0"
        new_dom = ORSEN_DOM_TEMPLATE.format(cta_start=cta_start, cta_dur=cta_dur)
        content = dom_pattern2.sub(new_dom, content, count=1)

    # 3. Update SFX volumes
    content = re.sub(r'(assets/shared/sfx/paper\.mp3"[^>]*data-volume=")[^"]+(")', r'\g<1>0.4\2', content)
    content = re.sub(r'(assets/shared/sfx/whoosh\.mp3"[^>]*data-volume=")[^"]+(")', r'\g<1>0.18\2', content)
    content = re.sub(r'(assets/shared/sfx/boom\.wav"[^>]*data-volume=")[^"]+(")', r'\g<1>0.15\2', content)
    content = re.sub(r'(assets/shared/sfx/cash_register\.mp3"[^>]*data-volume=")[^"]+(")', r'\g<1>0.20\2', content)

    # 4. Update GSAP animations: from tl.to("#chatwin"... or tl.fromTo("#b-chat"... down to window.__timelines
    gsap_pattern = re.compile(
        r'(?:tl\.to\("#chatwin",|tl\.fromTo\("#b-chat",).*?(?=window\.__timelines\s*=)',
        re.DOTALL
    )
    content = gsap_pattern.sub(ORSEN_GSAP + "\n\n      ", content, count=1)

    return content

def main():
    print("=" * 68)
    print("🚀 Applying Proven Orsen-Style CTA Cover to Clips 01-20")
    print("=" * 68)

    for idx in range(1, 21):
        cid = f"ess02-pov-s{idx:02d}"
        clip_dir = CLIPS_DIR / cid
        clip_html = clip_dir / "index.html"
        comp_html = COMPS_DIR / f"{cid}.html"
        vo_path = ASSETS_DIR / cid / "vo.wav"

        print(f"\nProcessing {cid}:")

        # 1. Audio Tail Fade
        if vo_path.exists():
            fixed = fix_vo_wav(vo_path)
            print(f"  🔊 vo.wav tail fade: {'OK' if fixed else 'SKIPPED'}")
        else:
            print(f"  ⚠️ vo.wav not found at {vo_path}")

        # 2. Update Clip HTML
        if clip_html.exists():
            txt = clip_html.read_text(encoding="utf-8")
            new_txt = update_html_content(txt)
            clip_html.write_text(new_txt, encoding="utf-8")
            print(f"  📄 clips/{cid}/index.html: Updated")

        # 3. Update Composition HTML
        if comp_html.exists():
            txt = comp_html.read_text(encoding="utf-8")
            new_txt = update_html_content(txt)
            comp_html.write_text(new_txt, encoding="utf-8")
            print(f"  📄 compositions/{cid}.html: Updated")

    print("\n✅ All 20 clips successfully updated to Proven Orsen-Style CTA!")

if __name__ == "__main__":
    main()
