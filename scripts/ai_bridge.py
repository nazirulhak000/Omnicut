"""
AI Bridge — one seam for every LLM task in the studio.

Phase 1 runs in manual mode: the app builds a copy-ready prompt, the user pastes
it into Antigravity (or any chat), and pastes the JSON answer back. Dropping a
GEMINI_API_KEY into the environment flips the same task to an automatic call
without changing prompts, schemas, or any caller.
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_MODEL = "gemini-2.5-flash"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file() -> None:
    """Read .env into the environment without overriding anything already set."""
    if not ENV_FILE.exists():
        return
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


class ManualModeRequired(Exception):
    """Raised when no API key is configured. Carries the prompt for the user to paste."""

    def __init__(self, prompt: str, task: str):
        super().__init__(f"No API key configured — run task '{task}' manually.")
        self.prompt = prompt
        self.task = task


class AIBridge:
    """Builds prompts, validates answers, and optionally calls Gemini directly."""

    # ------------------------------------------------------------------
    # Task definitions — prompt + expected JSON shape
    # ------------------------------------------------------------------
    TASKS: Dict[str, Dict[str, Any]] = {
        "product_enrich": {
            "label": "สรุปสินค้าจากหน้าร้าน",
            "required_context": ["product_title", "raw_text"],
            "schema_hint": {
                "product_name": "ชื่อสินค้าแบบสั้นที่คนพูดกันจริง",
                "category": "หมวดย่อยของ IT เช่น หูฟัง / สายชาร์จ / powerbank",
                "specs": [{"label": "ชื่อสเปค", "value": "ตัวเลข+หน่วย"}],
                "pain_points": ["ปัญหาที่คนซื้อของแบบนี้เจอจริง"],
                "selling_points": ["จุดขายที่พูดแล้วคนอยากกด"],
                "target_buyer": "คนแบบไหนควรซื้อ",
                "price_note": "ราคา/โปรที่เห็นในหน้าร้าน ถ้าไม่มีให้ใส่ว่าง",
            },
        },
        "angles": {
            "label": "คิดมุมเล่า (content list)",
            "required_context": ["product_name", "specs", "pain_points", "angle_catalog"],
            "schema_hint": {
                "angles": [
                    {
                        "angle_key": "คีย์จาก angle_catalog ที่ให้มา",
                        "title": "ชื่อมุมแบบสั้น",
                        "hook": "ประโยคเปิด 3 วินาทีแรก พูดได้จริง ไม่เกิน 18 คำ",
                        "why_it_works": "เหตุผลสั้นๆ ว่าทำไมมุมนี้หยุดนิ้วคนได้",
                        "needs_own_footage": "true ถ้าต้องถ่ายเอง / false ถ้าใช้รูปจากร้านได้",
                        "priority": "1-10 ยิ่งสูงยิ่งควรทำก่อน",
                    }
                ]
            },
        },
        "script": {
            "label": "เขียนสคริปต์พากย์",
            "required_context": ["product_name", "angle_title", "hook", "specs", "price_deal"],
            "schema_hint": {
                "hook_title": "ข้อความแบนเนอร์บนจอ 3 วิแรก สั้นมาก",
                "lines": [
                    {
                        "text": "ประโยคพูด 1 บรรทัด ภาษาพูดจริง ไม่เกิน 15 คำ",
                        "on_screen": "ตัวเลข/สเปคที่ต้องขึ้นจอตอนพูดบรรทัดนี้ ถ้าไม่มีใส่ว่าง",
                        "sfx": "__SFX_NAME_LIST__",
                    }
                ],
            },
        },
        "caption": {
            "label": "เขียน caption + hashtag",
            "required_context": ["product_name", "angle_title", "hook", "price_deal"],
            "schema_hint": {
                "caption": "แคปชั่น TikTok ไม่เกิน 150 ตัวอักษร มี CTA ชี้ตะกร้า",
                "hashtags": ["#แฮชแท็ก 8-12 อัน ผสมกว้าง+เฉพาะสินค้า"],
                "cover_text": "ข้อความบนภาพปก สั้นมาก อ่านออกในครึ่งวินาที",
            },
        },
    }

    STYLE_RULES = """กติกาการเขียน (ห้ามข้าม):
- ภาษาพูดไทยแบบรีวิวจริง ไม่ใช่ภาษาโฆษณาแข็งๆ
- สินค้า IT ต้องมีตัวเลขสเปคจริงเสมอ (W, mAh, ms, Hz, dB) ห้ามมั่วตัวเลข ถ้าไม่รู้ให้เว้น
- ห้ามเคลมเกินจริง ห้ามใช้คำว่า "ดีที่สุดในโลก" "รักษาโรค" หรือคำที่พิสูจน์ไม่ได้
- hook ต้องหยุดนิ้วใน 3 วินาที และห้ามขึ้นต้นด้วย "สวัสดีครับ/ค่ะ"
- ห้ามใส่อีโมจิเกิน 2 ตัวต่อประโยค"""

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------
    @classmethod
    def build_prompt(cls, task: str, context: Dict[str, Any]) -> str:
        """Return a copy-ready prompt for `task`, filled with `context`."""
        spec = cls.TASKS.get(task)
        if not spec:
            raise ValueError(f"Unknown task '{task}'. Known: {', '.join(cls.TASKS)}")

        missing = [k for k in spec["required_context"] if k not in context]
        if missing:
            raise ValueError(f"Task '{task}' missing context: {', '.join(missing)}")

        context_block = json.dumps(context, ensure_ascii=False, indent=2)

        # The "script" task's schema_hint carries a sentinel for the sfx
        # field instead of a hand-typed list, so it can never drift from
        # what SFXManager can actually play (28 sounds via AssetRegistry,
        # not the 5 legacy names this used to be hardcoded to).
        schema_block = json.dumps(spec["schema_hint"], ensure_ascii=False, indent=2)
        if "__SFX_NAME_LIST__" in schema_block:
            from scripts.asset_registry import AssetRegistry
            sfx_names = " | ".join(AssetRegistry.sfx_name_list())
            schema_block = schema_block.replace("__SFX_NAME_LIST__", sfx_names)

        return f"""คุณคือครีเอเตอร์ TikTok Shop สายสินค้า IT ที่ขายเก่งที่สุดในไทย
งาน: {spec['label']}

{cls.STYLE_RULES}

ข้อมูลที่มี:
{context_block}

ตอบกลับเป็น JSON อย่างเดียว ห้ามมีข้อความอื่นนอก JSON ห้ามใส่ ```
รูปแบบที่ต้องการ:
{schema_block}"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------
    @classmethod
    def parse_response(cls, task: str, raw_text: str) -> Dict[str, Any]:
        """Parse a pasted answer into a dict, tolerating code fences and stray prose."""
        if task not in cls.TASKS:
            raise ValueError(f"Unknown task '{task}'")
        if not raw_text or not raw_text.strip():
            raise ValueError("ยังไม่ได้วางคำตอบ")

        text = raw_text.strip()

        # Strip ``` / ```json fences the model may add despite instructions
        fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fall back to the outermost {...} block in case prose leaked in
            start, end = text.find("{"), text.rfind("}")
            if start == -1 or end <= start:
                raise ValueError("ไม่พบ JSON ในคำตอบที่วางมา — วางเฉพาะส่วน JSON")
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON ไม่ถูกรูปแบบ: {exc.msg} (บรรทัด {exc.lineno})")

        if not isinstance(data, dict):
            raise ValueError("คำตอบต้องเป็น JSON object ไม่ใช่ list หรือค่าเดี่ยว")

        cls._validate(task, data)
        return data

    @classmethod
    def _validate(cls, task: str, data: Dict[str, Any]) -> None:
        """Check the few keys downstream code actually depends on."""
        if task == "angles":
            angles = data.get("angles")
            if not isinstance(angles, list) or not angles:
                raise ValueError("ต้องมี key 'angles' เป็น list และมีอย่างน้อย 1 มุม")
            for i, angle in enumerate(angles, 1):
                for key in ("angle_key", "title", "hook"):
                    if not angle.get(key):
                        raise ValueError(f"มุมที่ {i} ขาด '{key}'")

        elif task == "script":
            lines = data.get("lines")
            if not isinstance(lines, list) or not lines:
                raise ValueError("ต้องมี key 'lines' เป็น list และมีอย่างน้อย 1 บรรทัด")
            for i, line in enumerate(lines, 1):
                if not line.get("text"):
                    raise ValueError(f"บรรทัดที่ {i} ไม่มี 'text'")

        elif task == "caption":
            if not data.get("caption"):
                raise ValueError("ต้องมี key 'caption'")
            if not isinstance(data.get("hashtags"), list):
                raise ValueError("'hashtags' ต้องเป็น list")

        elif task == "product_enrich":
            if not data.get("product_name"):
                raise ValueError("ต้องมี key 'product_name'")

    # ------------------------------------------------------------------
    # Optional automatic mode
    # ------------------------------------------------------------------
    @classmethod
    def has_api_key(cls) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())

    @classmethod
    def generate(
        cls,
        task: str,
        context: Dict[str, Any],
        model: str = DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """
        Run `task` automatically when GEMINI_API_KEY is set.

        Raises ManualModeRequired (carrying the prompt) when it is not, so the
        caller can show the copy-paste panel instead.
        """
        prompt = cls.build_prompt(task, context)

        if not cls.has_api_key():
            raise ManualModeRequired(prompt, task)

        from google import genai  # imported lazily so manual mode needs no SDK

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
        response = client.models.generate_content(model=model, contents=prompt)
        return cls.parse_response(task, response.text or "")


if __name__ == "__main__":
    from scripts.it_angles import IT_ANGLE_CATALOG

    demo_prompt = AIBridge.build_prompt(
        "angles",
        {
            "product_name": "Esseger สายชาร์จแม่เหล็ก 3-in-1",
            "specs": [{"label": "กำลังชาร์จ", "value": "20W PD"}],
            "pain_points": ["สายพันกัน", "เสียบยากในที่มืด"],
            "angle_catalog": IT_ANGLE_CATALOG,
        },
    )
    print(demo_prompt)
