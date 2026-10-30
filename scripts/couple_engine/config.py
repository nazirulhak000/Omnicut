# -*- coding: utf-8 -*-
"""Configuration and canonical product definitions for the Couple Paper Chat (#5) engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.config import BASE_DIR

# Rule 20: Strict TTS model allowlist — NEVER allow gemini-2.5-flash-preview-tts
ALLOWED_TTS_MODELS: tuple[str, ...] = (
    "gemini-3.8-flash-tts",
    "gemini-3.1-flash-tts-preview",
)
DEFAULT_TTS_MODEL: str = "gemini-3.8-flash-tts"


def validate_tts_model(model: str) -> str:
    """Validate that the requested TTS model is in ALLOWED_TTS_MODELS."""
    cleaned = (model or "").strip()
    if cleaned not in ALLOWED_TTS_MODELS:
        raise ValueError(
            f"Forbidden TTS model '{cleaned}'. Allowed models per Rule 20: {ALLOWED_TTS_MODELS}"
        )
    return cleaned


NUI_VOICE_CONFIG: Dict[str, Any] = {
    "speaker": "F",
    "display_name": "น้องนุ้ย",
    "avatar_char": "น",
    "voice_name": "Aoede",
    "asetrate_factor": 1.10,
    "atempo": 1.20,
    "highpass_hz": 140,
    "eq_freq_hz": 3500,
    "eq_gain_db": 3.0,
    "style": (
        "น้ำเสียงเด็กสาวชาวใต้ (น้องนุ้ย) สดใส น่ารักแต่ดุ แก่นเซี้ยว ขี้บ่นกวนๆ จังหวะฉะฉาน "
        "อารมณ์เหวี่ยงๆ ขี้โวยวายแต่มีเสน่ห์ แฟนสาวจอมบงการประจำช่อง"
    ),
    "guard": (
        "STRICT MONOLITHIC ACTING & SASSY CONSISTENCY GUARD: "
        "Maintain the vibrant, sassy, energetic, sharp Southern Thai girl persona 100% "
        "across ALL turns without exception. Never drift into a flat or monotone announcer voice."
    ),
}

# Note: Explicitly avoids forbidden words ("Calm", "Serious", "Professional") per Rule 20
BAO_VOICE_CONFIG: Dict[str, Any] = {
    "speaker": "M",
    "display_name": "พี่บ่าว",
    "avatar_char": "บ",
    "voice_name": "Puck",
    "asetrate_factor": 1.0,
    "atempo": 1.32,
    "highpass_hz": 95,
    "style": (
        "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว "
        "(พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ อารมณ์ดี กวนประสาท ขี้เล่น พูดเร็ว คล่องแคล่ว มีจังหวะโบ๊ะบ๊ะ ไม่เก๊กหล่อ)"
    ),
    "guard": (
        "STRICT MONOLITHIC ACTING & PLAYFUL CONSISTENCY GUARD: "
        "Maintain high energy, playful, flustered, comedic boy-next-door persona 100% "
        "throughout every turn, including when reading technical specs, chip features, or safety layers. "
        "Never switch to a stiff, robotic, or academic announcer tone."
    ),
}


CANONICAL_PRODUCT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "RED01": {
        "product_code": "RED01",
        "product_id": "b0137078e2ff4c089b60131f60168b54",
        "title": "Redmi Buds 8 Active",
        "title_font_size": 66,
        "sub": "หูฟังบลูทูธไดรเวอร์ 14.2mm · กดตะกร้าเหลือง",
        "cta_stage_css": """
      .earbuds-wrap {
        position: absolute;
      }
      .earbuds-img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: contain;
        filter: drop-shadow(0 16px 28px rgba(0, 0, 0, 0.22));
      }
      #f-left {
        width: 450px;
        height: 487px;
        left: 80px;
        bottom: 35px;
        transform: rotate(-6deg);
        z-index: 2;
      }
      #f-right {
        width: 450px;
        height: 487px;
        right: 80px;
        bottom: 35px;
        transform: rotate(6deg);
        z-index: 2;
      }
      #f-center {
        width: 520px;
        height: 563px;
        left: 50%;
        margin-left: -260px;
        bottom: 15px;
        z-index: 5;
      }
      #cs-center {
        width: 440px;
        height: 55px;
        bottom: 12px;
        left: 50%;
        margin-left: -220px;
        z-index: 4;
      }
      #cs-left {
        width: 350px;
        height: 45px;
        bottom: 30px;
        left: 110px;
        z-index: 1;
      }
      #cs-right {
        width: 350px;
        height: 45px;
        bottom: 30px;
        right: 110px;
        z-index: 1;
      }
        """,
        "cta_stage_html": """
          <div class="contact-shadow" id="cs-left"></div>
          <div class="contact-shadow" id="cs-right"></div>
          <div class="contact-shadow" id="cs-center"></div>
          <div class="earbuds-wrap" id="f-left"><img class="earbuds-img" src="assets/red01/cutouts/redmi_black.png" alt="Black"></div>
          <div class="earbuds-wrap" id="f-right"><img class="earbuds-img" src="assets/red01/cutouts/redmi_blue.png" alt="Blue"></div>
          <div class="earbuds-wrap" id="f-center"><img class="earbuds-img" src="assets/red01/cutouts/redmi_white.png" alt="White"></div>
        """,
        "cta_gsap_timeline": """
      tl.fromTo(["#f-left", "#cs-left"], { opacity: 0, x: -50, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo(["#f-right", "#cs-right"], { opacity: 0, x: 50, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo(["#f-center", "#cs-center"], { opacity: 0, scale: 0.75 }, { opacity: 1, scale: 1, duration: 0.46, ease: "back.out(2)" }, CTA_T + 0.26);
        """,
        "bottom_info_html": """
          <div class="swatch-card">
            <span class="swatch-title">3 โทนสีโมเดิร์น :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว White</div>
              <div class="chip-item"><div class="chip-dot" style="background:#222222"></div>ดำ Black</div>
              <div class="chip-item"><div class="chip-dot" style="background:#5b9bd5"></div>ฟ้า Blue</div>
            </div>
          </div>
          <div class="spec-row">
            <span class="spec-tag">ไดรเวอร์ 14.2mm Titanium</span>
            <span class="spec-tag">กึ่งอินเอียร์ ไม่เจ็บหู</span>
            <span class="spec-tag">ไมค์คู่ Dual-Mic AI ENC</span>
            <span class="spec-tag">แบตเตอรี่รวมเคส 37 ชม.</span>
          </div>
        """,
        "scripts_file": "redmi_buds8_20_scripts.json",
        "clip_prefix": "red01-pov-s",
        "photos_dir": "assets/red01/img",
        "default_photos": [
            "assets/red01/img/red01_img_01.webp",
            "assets/red01/img/red01_img_02.webp",
            "assets/red01/img/red01_img_04.webp",
            "assets/red01/img/red01_img_05.webp",
        ],
    },
    "HAT01": {
        "product_code": "HAT01",
        "product_id": "hat01_16inch_fan",
        "title": "Hatari · พัดลมตั้งโต๊ะ 16 นิ้ว",
        "title_font_size": 60,
        "sub": "รุ่น T16M1 สไตล์มินิมอล · กดตะกร้าเหลือง",
        "cta_stage_css": """
      .hero-img {
        width: 680px;
        height: 680px;
        object-fit: contain;
        filter: drop-shadow(0 16px 30px rgba(0, 0, 0, 0.22));
        position: absolute;
        top: 30px;
        left: 50%;
        margin-left: -340px;
        z-index: 10;
      }
      #cs-hatari {
        width: 580px;
        height: 85px;
        bottom: 110px;
        left: 50%;
        margin-left: -290px;
        z-index: 5;
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: 'Anuphan', sans-serif;
        font-weight: 700;
        font-size: 24px;
        background: #ffffff;
        color: var(--ink);
        border: 3.5px solid var(--ink);
        padding: 7px 16px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        white-space: nowrap;
      }
      #fb-1 { top: 70px; left: 70px; rotate: -4deg; }
      #fb-2 { top: 60px; right: 70px; rotate: 4deg; }
      #fb-3 { bottom: 180px; left: 65px; rotate: 3deg; }
      #fb-4 { bottom: 190px; right: 65px; rotate: -3deg; }
        """,
        "cta_stage_html": """
          <div class="contact-shadow" id="cs-hatari"></div>
          <img class="hero-img" src="assets/hatari01/cutouts/hatari_sand_hi.png" alt="Hatari 16 Inch Fan">
          <div class="floating-badge" id="fb-1">ใบพัด 16 นิ้ว ลมแรง</div>
          <div class="floating-badge" id="fb-2">ปรับแรงลม 3 ระดับ</div>
          <div class="floating-badge" id="fb-3">มอเตอร์ Ball Bearing</div>
          <div class="floating-badge" id="fb-4">ระบบ Thermal Fuse</div>
        """,
        "cta_gsap_timeline": """
      tl.fromTo([".hero-img", "#cs-hatari"], { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.2);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.32, stagger: 0.08, ease: "back.out(2)" }, CTA_T + 0.28);
        """,
        "bottom_info_html": """
          <div class="swatch-card">
            <span class="swatch-title">6 โทนสีพาสเทล :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว</div>
              <div class="chip-item"><div class="chip-dot" style="background:#98d8c8"></div>มิ้นท์</div>
              <div class="chip-item"><div class="chip-dot" style="background:#f9c5d1"></div>ชมพู</div>
              <div class="chip-item"><div class="chip-dot" style="background:#dfd7ca"></div>ทราย</div>
              <div class="chip-item"><div class="chip-dot" style="background:#d4c4fb"></div>ม่วง</div>
              <div class="chip-item"><div class="chip-dot" style="background:#b3d9ff"></div>ฟ้า</div>
            </div>
          </div>
          <div class="spec-row">
            <span class="spec-tag">สไตล์มินิมอลโมเดิร์น</span>
            <span class="spec-tag">ประหยัดไฟเบอร์ 5</span>
            <span class="spec-tag">รับประกันมอเตอร์ 3 ปี</span>
            <span class="spec-tag">มาตรฐาน มอก. แท้ 100%</span>
          </div>
        """,
        "scripts_file": "hatari_16inch_20_scripts.json",
        "clip_prefix": "hat01-pov-s",
        "photos_dir": "assets/hatari01/img",
        "default_photos": [
            "assets/hatari01/img/hatari_clean_main.webp",
            "assets/hatari01/img/hatari_clean_angle.webp",
            "assets/hatari01/img/hatari_clean_side.webp",
            "assets/hatari01/img/hatari_clean_motor.webp",
        ],
    },
    "GOO01": {
        "product_code": "GOO01",
        "product_id": "goo01_5000mah",
        "title": "GOOJODOQ · พาวเวอร์แบงค์แคปซูล",
        "title_font_size": 54,
        "sub": "5000mAh มี 2 หัวในตัว · กดตะกร้าเหลือง",
        "cta_stage_css": """
      .hero-img {
        width: 680px;
        height: 680px;
        object-fit: contain;
        filter: drop-shadow(0 16px 30px rgba(0, 0, 0, 0.22));
        position: absolute;
        top: 30px;
        left: 50%;
        margin-left: -340px;
        z-index: 10;
      }
      #cs-goo {
        width: 580px;
        height: 85px;
        bottom: 110px;
        left: 50%;
        margin-left: -290px;
        z-index: 5;
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: 'Anuphan', sans-serif;
        font-weight: 700;
        font-size: 24px;
        background: #ffffff;
        color: var(--ink);
        border: 3.5px solid var(--ink);
        padding: 7px 16px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        white-space: nowrap;
      }
      #fb-1 { top: 70px; left: 70px; rotate: -4deg; }
      #fb-2 { top: 60px; right: 70px; rotate: 4deg; }
      #fb-3 { bottom: 180px; left: 65px; rotate: 3deg; }
      #fb-4 { bottom: 190px; right: 65px; rotate: -3deg; }
        """,
        "cta_stage_html": """
          <div class="contact-shadow" id="cs-goo"></div>
          <img class="hero-img" src="assets/goo01/img/hero_cutout.png" alt="GOOJODOQ 5000mAh">
          <div class="floating-badge" id="fb-1">2in1 iOS + Type-C</div>
          <div class="floating-badge" id="fb-2">5000mAh เต็มพลัง</div>
          <div class="floating-badge" id="fb-3">เบาแค่ 100 กรัม</div>
          <div class="floating-badge" id="fb-4">มีขาตั้ง + มอก. แท้</div>
        """,
        "cta_gsap_timeline": """
      tl.fromTo([".hero-img", "#cs-goo"], { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.2);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.32, stagger: 0.08, ease: "back.out(2)" }, CTA_T + 0.28);
        """,
        "bottom_info_html": """
          <div class="swatch-card">
            <span class="swatch-title">4 สีมินิมอล :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว White</div>
              <div class="chip-item"><div class="chip-dot" style="background:#ffccd5"></div>ชมพู Pink</div>
              <div class="chip-item"><div class="chip-dot" style="background:#e0bbf8"></div>ม่วง Purple</div>
              <div class="chip-item"><div class="chip-dot" style="background:#222222"></div>ดำ Black</div>
            </div>
          </div>
          <div class="spec-row">
            <span class="spec-tag">หัวชาร์จ 2in1 เสียบตรง</span>
            <span class="spec-tag">ไม่ต้องพกสายชาร์จ</span>
            <span class="spec-tag">หน้าจอดิจิทัล LED</span>
            <span class="spec-tag">มาตรฐาน มอก. แท้ 100%</span>
          </div>
        """,
        "scripts_file": "goojodoq_5000mah_20_scripts.json",
        "clip_prefix": "goo01-pov-s",
        "photos_dir": "assets/goo01/img",
        "default_photos": [
            "assets/goo01/img/goo01_img_01.webp",
            "assets/goo01/img/goo01_img_02.webp",
            "assets/goo01/img/goo01_img_03.webp",
            "assets/goo01/img/goo01_img_06.webp",
        ],
    },
}


def _build_default_cta_blocks(
    code: str,
    title: str,
    hero_src: str,
    badges: list[str],
    specs: list[str],
    swatches: Optional[list[dict[str, str]]] = None,
) -> Dict[str, str]:
    """Build Style 3B centered hero CTA CSS/HTML/GSAP blocks for a dynamic product."""
    cs_id = f"cs-{code.lower()}"
    cta_stage_css = f"""
      .hero-img {{
        width: 680px;
        height: 680px;
        object-fit: contain;
        filter: drop-shadow(0 16px 30px rgba(0, 0, 0, 0.22));
        position: absolute;
        top: 30px;
        left: 50%;
        margin-left: -340px;
        z-index: 10;
      }}
      #{cs_id} {{
        width: 580px;
        height: 85px;
        bottom: 110px;
        left: 50%;
        margin-left: -290px;
        z-index: 5;
      }}
      .floating-badge {{
        position: absolute;
        z-index: 22;
        font-family: 'Anuphan', sans-serif;
        font-weight: 700;
        font-size: 24px;
        background: #ffffff;
        color: var(--ink);
        border: 3.5px solid var(--ink);
        padding: 7px 16px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        white-space: nowrap;
      }}
      #fb-1 {{ top: 70px; left: 70px; rotate: -4deg; }}
      #fb-2 {{ top: 60px; right: 70px; rotate: 4deg; }}
      #fb-3 {{ bottom: 180px; left: 65px; rotate: 3deg; }}
      #fb-4 {{ bottom: 190px; right: 65px; rotate: -3deg; }}
    """
    padded_badges = (badges + ["ของแท้ 100%", "คุณภาพพรีเมียม", "ใช้งานง่าย", "คุ้มค่าแน่นอน"])[:4]
    badge_divs = "\n          ".join(
        f'<div class="floating-badge" id="fb-{i+1}">{b}</div>'
        for i, b in enumerate(padded_badges)
    )
    cta_stage_html = f"""
          <div class="contact-shadow" id="{cs_id}"></div>
          <img class="hero-img" src="{hero_src}" alt="{title}">
          {badge_divs}
    """
    cta_gsap_timeline = f"""
      tl.fromTo([".hero-img", "#{cs_id}"], {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }}, CTA_T + 0.2);
      tl.fromTo(".floating-badge", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.32, stagger: 0.08, ease: "back.out(2)" }}, CTA_T + 0.28);
    """
    swatch_html = ""
    if swatches:
        chips = "\n              ".join(
            f'<div class="chip-item"><div class="chip-dot" style="background:{s.get("color", "#ffffff")}"></div>{s.get("label", "")}</div>'
            for s in swatches
        )
        swatch_html = f"""
          <div class="swatch-card">
            <span class="swatch-title">โทนสีให้เลือก :</span>
            <div class="chips-grid">
              {chips}
            </div>
          </div>"""
    spec_tags = "\n            ".join(
        f'<span class="spec-tag">{sp}</span>' for sp in (specs or ["มาตรฐานของแท้ 100%"])[:4]
    )
    bottom_info_html = f"""{swatch_html}
          <div class="spec-row">
            {spec_tags}
          </div>
    """
    return {
        "cta_stage_css": cta_stage_css,
        "cta_stage_html": cta_stage_html,
        "cta_gsap_timeline": cta_gsap_timeline,
        "bottom_info_html": bottom_info_html,
    }


def load_couple_product_config(
    code: str, project_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Load Couple Paper Chat product configuration.

    Resolution order:
    1. `_Docs/couple_products/{CODE}.json` if present
    2. Built-in `CANONICAL_PRODUCT_CONFIGS` (`RED01`, `HAT01`, `GOO01`)
    3. Dynamic resolution from `_Docs/products.json` + `_Docs/*_20_scripts.json`
    """
    norm_code = (code or "").strip().upper()
    if not norm_code:
        raise ValueError("product code must not be empty")

    root = Path(project_root).resolve() if project_root else BASE_DIR
    docs_dir = root / "_Docs"

    # 1. Explicit per-product JSON in _Docs/couple_products/{CODE}.json
    couple_json = docs_dir / "couple_products" / f"{norm_code}.json"
    if couple_json.exists():
        cfg = json.loads(couple_json.read_text(encoding="utf-8"))
        cfg.setdefault("product_code", norm_code)
        cfg.setdefault("clip_prefix", f"{norm_code.lower()}-pov-s")
        if "scripts_file" in cfg and isinstance(cfg["scripts_file"], str):
            sf = Path(cfg["scripts_file"])
            if not sf.is_absolute():
                cfg["scripts_file"] = docs_dir / sf
        if "cta_stage_css" not in cfg:
            blocks = _build_default_cta_blocks(
                norm_code,
                cfg.get("title", norm_code),
                cfg.get("hero_cutout", f"assets/{norm_code.lower()}/img/hero_cutout.png"),
                cfg.get("floating_badges", []),
                cfg.get("spec_tags", []),
                cfg.get("swatches"),
            )
            cfg.update(blocks)
        return cfg

    # 2. Canonical built-in config
    if norm_code in CANONICAL_PRODUCT_CONFIGS:
        cfg = dict(CANONICAL_PRODUCT_CONFIGS[norm_code])
        sf_name = cfg["scripts_file"]
        cfg["scripts_file"] = docs_dir / sf_name if isinstance(sf_name, str) else sf_name
        return cfg

    # 3. Resolve from _Docs/products.json + _Docs/*_20_scripts.json
    products_file = docs_dir / "products.json"
    product_entry = None
    if products_file.exists():
        try:
            products = json.loads(products_file.read_text(encoding="utf-8"))
            if isinstance(products, list):
                product_entry = next(
                    (
                        p
                        for p in products
                        if str(p.get("product_code", "")).upper() == norm_code
                        or str(p.get("code", "")).upper() == norm_code
                        or str(p.get("id", "")).upper() == norm_code
                    ),
                    None,
                )
        except Exception:
            product_entry = None

    # Find matching scripts file
    scripts_file: Optional[Path] = None
    if docs_dir.exists():
        prefix_lower = norm_code.lower()
        candidates = sorted(docs_dir.glob("*_20_scripts.json"))
        for cand in candidates:
            if prefix_lower in cand.name.lower() or prefix_lower[:3] in cand.name.lower():
                scripts_file = cand
                break

    if not product_entry and not scripts_file:
        raise FileNotFoundError(
            f"Product config not found for code '{norm_code}' in {couple_json} or {products_file}"
        )

    title = (
        (product_entry or {}).get("name")
        or (product_entry or {}).get("title")
        or norm_code
    )
    sub = (product_entry or {}).get("subtitle") or "ชี้เป้าตัวจบ · กดตะกร้าเหลือง"
    hero_src = (
        (product_entry or {}).get("hero_cutout")
        or f"assets/{norm_code.lower()}/img/hero_cutout.png"
    )
    badges = (product_entry or {}).get("highlights") or []
    specs = (product_entry or {}).get("specs") or []
    blocks = _build_default_cta_blocks(norm_code, title, hero_src, badges, specs)

    return {
        "product_code": norm_code,
        "product_id": (product_entry or {}).get("id", norm_code.lower()),
        "title": title,
        "title_font_size": int((product_entry or {}).get("title_font_size", 58)),
        "sub": sub,
        "scripts_file": scripts_file,
        "clip_prefix": f"{norm_code.lower()}-pov-s",
        "photos_dir": f"assets/{norm_code.lower()}/img",
        "default_photos": (product_entry or {}).get("photos", []),
        **blocks,
    }
