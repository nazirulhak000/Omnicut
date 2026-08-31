"""
AI Script & Hook Generator for TikTok Product Reviews (Authentic Human Reviewer Style)
Structured with 4-5 punchy beats, conversational spoken Thai, and micro-burst pacing.
"""

from typing import List, Dict

class ScriptGenerator:
    """Generates structured high-converting TikTok product review scripts in natural spoken Thai."""

    TEMPLATES = {
        "problem_solution": {
            "name": "เปิดด้วยปัญหา แล้วเฉลยทางออก (Problem-Solution Review)",
            "beats": [
                "ทุกคน! อย่าเพิ่งเลื่อนผ่านนะ ใครที่เบื่อกับปัญหา {pain_point} ดูคลิปนี้เลย",
                "บอกเลยว่า {product_name} ตัวนี้คือตอบโจทย์ชีวิตมากก",
                "{key_features} ใช้งานง่าย สะดวกสุดๆ ปึ้งเดียวติด",
                "หมดปัญหาแบบเดิมๆ ตอบโจทย์คนชอบความสะดวกสบายจริงๆ ครับ",
                "พิกัดราคาพิเศษ {price_deal} จิ้มในตะกร้าสีเหลืองซ้ายล่าง รีบกดก่อนของหมดนะ!"
            ]
        },
        "curiosity_tech": {
            "name": "เปิดด้วยความว้าว / แกดเจ็ตสุดล้ำ (Tech & Gadget Hype)",
            "beats": [
                "ทุกคนดูนี่! {product_name} ทำไมคนใน TikTok สั่งกันถล่มทลายขนาดนี้?!",
                "ของจริงคือสวยมากก {key_features}",
                "งานพรีเมียม แข็งแรงทนทาน ใช้แล้วชีวิตง่ายขึ้นสิบเท่า",
                "ใครกำลังมองหาของดีมีคุณภาพ บอกเลยว่าตัวนี้ไม่ผิดหวังแน่นอน",
                "คุ้มขนาดนี้ {price_deal} พิกัดในตะกร้าซ้ายล่าง กดสั่งตรงนี้ได้เลยครับ!"
            ]
        }
    }

    @classmethod
    def generate(
        cls,
        product_name: str,
        key_features: str = "แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต",
        pain_point: str = "สายชาร์จพันกัน เสียบยากในที่มืด",
        price_deal: str = "ลดราคาพิเศษวันนี้",
        template_key: str = "problem_solution"
    ) -> Dict[str, any]:
        """
        Generate multi-beat conversational review script in authentic spoken Thai.
        """
        tmpl = cls.TEMPLATES.get(template_key, cls.TEMPLATES["problem_solution"])
        raw_beats = tmpl["beats"]

        lines = []
        for idx, beat_tmpl in enumerate(raw_beats):
            text = beat_tmpl.format(
                product_name=product_name,
                pain_point=pain_point,
                key_features=key_features,
                price_deal=price_deal
            )
            sfx = "boom" if idx == 0 else ("cash" if idx == len(raw_beats) - 1 else "ding")
            lines.append({"index": idx + 1, "text": text, "sfx": sfx})

        full_text = "\n".join(l["text"] for l in lines)

        return {
            "hook": lines[0]["text"],
            "body": " ".join(l["text"] for l in lines[1:-1]),
            "cta": lines[-1]["text"],
            "full_text": full_text,
            "lines": lines
        }

if __name__ == "__main__":
    res = ScriptGenerator.generate("Esseger สายชาร์จแม่เหล็ก 3-in-1")
    print(res["full_text"])
