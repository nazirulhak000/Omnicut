"""
Hook Variation & A/B Generator Engine
Generates 5 distinct high-converting TikTok/Reels hook styles for products:
1. curiosity (กระตุ้นความสงสัย)
2. warning (เตือนภัย / หยุดก่อน)
3. social_proof (ผลลัพธ์จริง / สถิติ)
4. deal_promo (ห้ามพลาด / ของมันต้องมี -- no price/discount talk)
5. pain_point (แทงใจดำ / ขยี้ปัญหา)

Adheres strictly to project rules:
- Rule 7: NO ellipsis "..." or "…" in spoken text or titles.
- Rule 8: Clean UI compatibility.
- Rule 9: Strict English retention for brand names and specs.
- Zero-emoji on every field (hook_title included) and no price / exaggerated
  claim / filler opener -- enforced by scripts/compliance_lint.py.
"""

import re
import json
from typing import Any, Dict, List, Optional
from scripts.tts_sanitizer import TTSSanitizer
from scripts.compliance_lint import (
    format_violations_th,
    lint_hook_variant,
    strip_emoji,
)

HOOK_STYLES: List[Dict[str, str]] = [
    {
        "style_id": "curiosity",
        "style_name": "กระตุ้นความสงสัย",
        "tag": "ยอดนิยม",
        "description": "เปิดหัวด้วยคำถามหรือความจริงที่คนไม่เคยรู้ ดึงดูดให้อยากดูต่อจนจบ",
    },
    {
        "style_id": "warning",
        "style_name": "เตือนภัย / หยุดก่อน",
        "tag": "เปิดคลิปปัง",
        "description": "สร้างความเร่งด่วน เตือนข้อควรระวังก่อนตัดสินใจซื้อหรือทำอะไรผิดพลาด",
    },
    {
        "style_id": "social_proof",
        "style_name": "ผลลัพธ์จริง / สถิติ",
        "tag": "น่าเชื่อถือ",
        "description": "เน้นผลลัพธ์ที่เห็นได้ในคลิปและตัวเลขสเปกจริง ไม่แต่งยอดขายหรือระยะเวลาใช้งาน",
    },
    {
        "style_id": "deal_promo",
        "style_name": "ห้ามพลาด / ของมันต้องมี",
        "tag": "สายปิดการขาย",
        "description": "เร่งการตัดสินใจด้วยประโยชน์ใช้งานจริง ไม่พูดถึงราคา ส่วนลด หรือโปรโมชั่น",
    },
    {
        "style_id": "pain_point",
        "style_name": "แทงใจดำ / ขยี้ปัญหา",
        "tag": "ตรงกลุ่มเป้าหมาย",
        "description": "ตอกย้ำปัญหาที่ลูกค้าเผชิญอยู่ แล้วเปิดทางออกด้วยสินค้าตัวนี้",
    },
]


class HookVariationEngine:
    """Engine for generating and managing AI Hook variations for TikTok / Reels."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Strip ellipses and collapse excessive whitespace (Rule 7)."""
        if not text:
            return ""
        # Remove any ellipsis or multiple dots
        s = re.sub(r'[\.]{2,}|…', ' ', text)
        s = re.sub(r'\s+', ' ', s)
        return s.strip()

    @classmethod
    def sanitize_variant(cls, variant: Dict[str, Any], default_brand: str = "", default_model: str = "") -> Dict[str, Any]:
        """Ensure all fields in a hook variant strictly conform to project standards."""
        style_id = variant.get("style_id", "curiosity")
        meta = next((s for s in HOOK_STYLES if s["style_id"] == style_id), HOOK_STYLES[0])

        brand = cls.clean_text(strip_emoji(variant.get("hook_brand") or default_brand))
        model = cls.clean_text(strip_emoji(variant.get("hook_model") or default_model))
        label = cls.clean_text(strip_emoji(variant.get("hook_label", "")))
        # Banner title is on-screen text: zero-emoji like every other field.
        title = cls.clean_text(strip_emoji(variant.get("hook_title", "")))
        
        # Spoken opening line must not have emojis (Rule: no emojis in speech)
        raw_opening = variant.get("opening_line") or title
        clean_opening = cls.clean_text(TTSSanitizer.clean(raw_opening))

        return {
            "style_id": meta["style_id"],
            "style_name": meta["style_name"],
            "tag": meta["tag"],
            "description": meta["description"],
            "hook_brand": brand,
            "hook_model": model,
            "hook_label": label,
            "hook_title": title,
            "opening_line": clean_opening,
        }

    @classmethod
    def generate_offline_variations(
        cls,
        product_name: str,
        brand: str = "",
        model: str = "",
        pain_point: str = "",
        price_deal: str = "",
        angle_name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, zero-latency template fallback generator.
        Guarantees 5 high-CTR variations even without internet or LLM quota.
        """
        p_name = product_name.strip() or "สินค้านี้"
        display_name = f"{brand} {model}".strip() if (brand or model) else p_name
        b_val = brand or p_name.split()[0] if p_name else ""
        m_val = model or (" ".join(p_name.split()[1:]) if len(p_name.split()) > 1 else p_name)

        pain = pain_point.strip() or "เจอปัญหานี้ซ้ำๆ"

        raw_variants = [
            {
                "style_id": "curiosity",
                "hook_title": f"เพิ่งรู้ว่า {display_name} ทำแบบนี้ได้ด้วย",
                "hook_brand": b_val,
                "hook_model": m_val,
                "hook_label": "เพิ่งรู้ว่ามีแบบนี้ด้วย",
                "opening_line": f"{display_name} มีลูกเล่นหนึ่งที่คนใช้ส่วนใหญ่ไม่เคยรู้ เดี๋ยวให้ดูครับ",
            },
            {
                "style_id": "warning",
                "hook_title": f"อย่าเพิ่งซื้อ {display_name} ถ้ายังไม่รู้ข้อนี้",
                "hook_brand": b_val,
                "hook_model": m_val,
                "hook_label": "อย่าเพิ่งซื้อถ้าไม่รู้ข้อนี้",
                "opening_line": f"ก่อนเลือก {display_name} มีอยู่ 1 จุดที่ต้องเช็ค ไม่งั้นได้ของไม่ตรงใจครับ",
            },
            {
                "style_id": "social_proof",
                "hook_title": f"ลองให้ดูกับตา {display_name} ทำได้จริงไหม",
                "hook_brand": b_val,
                "hook_model": m_val,
                "hook_label": "ลองให้ดูกับตา",
                "opening_line": f"{display_name} ที่เขาว่ากัน ทำได้จริงไหม ลองให้ดูกับตาเลยครับ",
            },
            {
                "style_id": "deal_promo",
                "hook_title": f"ของมันต้องมี {display_name} ช่วยอะไรได้บ้าง",
                "hook_brand": b_val,
                "hook_model": m_val,
                "hook_label": "ของมันต้องมี",
                "opening_line": f"{display_name} ตัวเดียว ช่วยเรื่องไหนได้บ้างในแต่ละวัน เดี๋ยวไล่ให้ดูครับ",
            },
            {
                "style_id": "pain_point",
                "hook_title": f"จบปัญหา {pain} ด้วย {display_name}",
                "hook_brand": b_val,
                "hook_model": m_val,
                "hook_label": f"แก้ปัญหา {pain}",
                "opening_line": f"ใครที่กำลังปวดหัวกับปัญหา {pain} ตัวนี้ตอบโจทย์ตรงจุดเลยครับ",
            },
        ]

        return [cls.sanitize_variant(v, b_val, m_val) for v in raw_variants]

    @staticmethod
    def call_gemini_api(prompt: str) -> str:
        """Raw-text Gemini call through the API keys AIBridge manages.

        AIBridge has no raw-text direct-API method: `_generate_from_prompt`
        only serves its own TASKS and parses into a dict, while hooks come
        back as a JSON *array*. So this reuses AIBridge's pieces (key list,
        default model, request timeout, daily budget check) and rotates keys
        on failure. A quota error is re-raised; the caller falls back to the
        offline templates. Returns "" when no key produced text.
        """
        from scripts.ai_bridge import AIBridge, API_REQUEST_TIMEOUT_SECONDS, DEFAULT_MODEL
        from scripts.quota import check_budget, is_quota_error

        api_keys = AIBridge.get_api_keys()
        if not api_keys:
            return ""
        check_budget(task="hooks")

        from google import genai  # lazy: offline mode needs no SDK
        from google.genai import types as genai_types

        http_options = genai_types.HttpOptions(timeout=API_REQUEST_TIMEOUT_SECONDS * 1000)
        for key_idx, cur_key in enumerate(api_keys, 1):
            try:
                client = genai.Client(api_key=cur_key, http_options=http_options)
                response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
                text = (getattr(response, "text", "") or "").strip()
                if text:
                    return text
            except Exception as api_err:
                if is_quota_error(api_err):
                    raise
                print(f"⚠️ [HookVariationEngine] Gemini Key #{key_idx} error ({api_err}) — ลองคีย์ถัดไป")
        return ""

    @classmethod
    def generate_variations(
        cls,
        product_name: str,
        brand: str = "",
        model: str = "",
        description: str = "",
        pain_point: str = "",
        price_deal: str = "",
        angle_name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Generates 5 tailored hook variations using AIBridge (Antigravity Pro / Gemini),
        with seamless fallback to deterministic offline templates.
        """
        # Try calling AIBridge if available
        try:
            from scripts.ai_bridge import AIBridge
            if AIBridge.is_available():
                prompt = (
                    f"คุณคือผู้เชี่ยวชาญการทำวิดีโอ TikTok Affiliate และ Viral Shorts ระดับท็อป\n"
                    f"จงสร้างประโยคฮุกเปิดคลิป (Hook Variations) สำหรับสินค้าด้านล่างนี้ ให้ครบทั้ง 5 สไตล์การตลาด\n\n"
                    f"ข้อมูลสินค้า:\n"
                    f"- ชื่อสินค้า: {product_name}\n"
                    f"- แบรนด์ (ห้ามแปลทับศัพท์ ให้คงภาษาอังกฤษ): {brand}\n"
                    f"- รุ่น (ห้ามแปลทับศัพท์ ให้คงภาษาอังกฤษ): {model}\n"
                    f"- รายละเอียด/สรรพคุณ: {description}\n"
                    f"- Pain Point: {pain_point}\n"
                    f"- มุมเนื้อหา: {angle_name}\n\n"
                    f"กฎเหล็กสำคัญที่สุด:\n"
                    f"1. ห้ามใช้จุดไข่ปลา '...' หรือ '…' ในทุกข้อความโดยเด็ดขาด ให้เว้นวรรคปกติ (Strict No Ellipsis)\n"
                    f"2. ห้ามทับศัพท์ชื่อแบรนด์หรือรุ่นเป็นภาษาไทยเด็ดขาด เช่น Logitech ห้ามเขียน โลจิเทค (Strict English Retention)\n"
                    f"3. hook_label คือข้อความสั้นบนป้ายแบนเนอร์ (ความยาวไม่เกิน 15-25 ตัวอักษร)\n"
                    f"4. opening_line คือประโยคพูดเปิดคลิป ห้ามใส่อีโมจิใน opening_line เด็ดขาด\n"
                    f"5. hook_title คือพาดหัวรวม ห้ามใส่อีโมจิในทุกช่องเด็ดขาด (Zero-Emoji)\n"
                    f"6. ห้ามพูด/เขียนถึงราคา ตัวเลขเงิน ส่วนลด โปรโมชั่น Flash Sale คูปอง ส่งฟรี หรือการเดาราคา (เช่น หลักร้อย หลักพัน) ในทุกช่องเด็ดขาด (ผิดกฎ TikTok)\n"
                    f"7. ห้ามเคลมเกินจริงหรือแต่งข้อมูล เช่น ใช้จริงมา 3 เดือน, ยอดขายถล่มทลาย, อันดับ 1, ดีที่สุดในโลก, 100% ไม่พัง\n"
                    f"8. opening_line ประโยคแรกห้ามขอให้คนดูหยุดเลื่อน/หยุดดู/ดูให้จบ และห้ามมี CTA (ตะกร้า/กดซื้อ) ให้เปิดด้วยผลลัพธ์ ภาพที่เห็น หรือคำถามเฉพาะสินค้า\n\n"
                    f"สไตล์ทั้ง 5 แบบที่ต้องสร้าง:\n"
                    f"1. curiosity (กระตุ้นความสงสัยด้วยสิ่งที่คนไม่เคยรู้เกี่ยวกับสินค้า)\n"
                    f"2. warning (เตือนภัย หยุดก่อน อย่าเพิ่งซื้อ)\n"
                    f"3. social_proof (ผลลัพธ์ที่โชว์ให้เห็นได้ในคลิป ห้ามแต่งยอดขาย/ระยะเวลาใช้งาน)\n"
                    f"4. deal_promo (ห้ามพลาด ของมันต้องมี เร่งด้วยประโยชน์ใช้งานจริง ห้ามพูดราคา/ส่วนลด)\n"
                    f"5. pain_point (แทงใจดำ แก้ปัญหาตรงจุด)\n\n"
                    f"ส่งคำตอบกลับมาเป็น JSON อาเรย์เท่านั้น โดยมีรูปแบบดังนี้:\n"
                    f"[\n"
                    f'  {{"style_id": "curiosity", "hook_brand": "{brand}", "hook_model": "{model}", "hook_label": "...", "hook_title": "...", "opening_line": "..."}},\n'
                    f'  {{"style_id": "warning", "hook_brand": "{brand}", "hook_model": "{model}", "hook_label": "...", "hook_title": "...", "opening_line": "..."}},\n'
                    f'  {{"style_id": "social_proof", "hook_brand": "{brand}", "hook_model": "{model}", "hook_label": "...", "hook_title": "...", "opening_line": "..."}},\n'
                    f'  {{"style_id": "deal_promo", "hook_brand": "{brand}", "hook_model": "{model}", "hook_label": "...", "hook_title": "...", "opening_line": "..."}},\n'
                    f'  {{"style_id": "pain_point", "hook_brand": "{brand}", "hook_model": "{model}", "hook_label": "...", "hook_title": "...", "opening_line": "..."}}\n'
                    f"]"
                )

                raw_resp = ""
                if AIBridge.has_antigravity_cli():
                    try:
                        raw_resp = AIBridge.call_antigravity_cli(prompt)
                    except Exception as cli_err:
                        print(f"⚠️ [HookVariationEngine] Antigravity CLI error ({cli_err}) — ลองผ่าน Gemini API key")
                if not raw_resp and AIBridge.has_api_key():
                    raw_resp = cls.call_gemini_api(prompt)

                if raw_resp:
                    # Clean markdown fence if present
                    clean_json = re.sub(r'^```json\s*', '', raw_resp.strip())
                    clean_json = re.sub(r'\s*```$', '', clean_json.strip())
                    parsed = json.loads(clean_json)
                    if isinstance(parsed, list) and len(parsed) >= 3:
                        results = []
                        for item in parsed:
                            if isinstance(item, dict) and "style_id" in item:
                                clean = cls.sanitize_variant(item, brand, model)
                                hits = lint_hook_variant(clean)
                                if hits:
                                    # Rejected, not passed through: the
                                    # offline template for this style fills
                                    # the slot below.
                                    print(
                                        f"⚠️ [HookVariationEngine] ตัดฮุกสไตล์ '{clean['style_id']}' "
                                        f"ที่ผิดกฎ compliance ออก แล้วใช้เทมเพลตสำรองแทน:\n"
                                        f"{format_violations_th(hits)}"
                                    )
                                    continue
                                results.append(clean)
                        if len(results) >= 3:
                            # Fill any missing styles from offline generator
                            existing_ids = {r["style_id"] for r in results}
                            offline = cls.generate_offline_variations(product_name, brand, model, pain_point, price_deal, angle_name)
                            for off in offline:
                                if off["style_id"] not in existing_ids:
                                    results.append(off)
                            return results[:5]
        except Exception as err:
            print(f"[HookVariationEngine] AI generation fallback to offline templates: {err}")

        # Fallback to offline template engine
        return cls.generate_offline_variations(product_name, brand, model, pain_point, price_deal, angle_name)
