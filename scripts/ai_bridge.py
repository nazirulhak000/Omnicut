"""
AI Bridge — one seam for every LLM task in the studio.

Phase 1 runs in manual mode: the app builds a copy-ready prompt, the user pastes
it into Antigravity (or any chat), and pastes the JSON answer back. Dropping a
GEMINI_API_KEY into the environment flips the same task to an automatic call
without changing prompts, schemas, or any caller.
"""

import os
import sys
import time
import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

DEFAULT_MODEL = "gemini-2.5-flash"
PRO_MODEL = "gemini-3.8-flash-high"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def get_agy_path() -> Optional[Path]:
    """Find the Antigravity CLI executable on this system."""
    default_path = Path.home() / ".gemini" / "bin" / "agy.exe"
    if default_path.exists():
        return default_path
    which_agy = shutil.which("agy") or shutil.which("agy.exe")
    if which_agy:
        return Path(which_agy)
    return None



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
            "label": "เขียนสคริปต์พากย์และซับไตเติลสองภาษา",
            "required_context": ["product_name", "angle_title", "hook", "specs", "price_deal"],
            "schema_hint": {
                "hook_title": "ข้อความแบนเนอร์บนจอ 3 วิแรก สั้นมาก (ไม่เกิน 5-7 คำ)",
                "lines": [
                    {
                        "text": "ประโยคพูดสั้นเป็นธรรมชาติ (เว้นวรรคระหว่างประโยคย่อย ประโยคสั้น <18 ตัวอักษรรวมกันได้ 2 ประโยค, ประโยคยาวแยก 1 บรรทัด)",
                        "translation": "คำแปลภาษาอังกฤษกระชับตรงตามประโยคนี้ (English translation matching this clause)",
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
- ชื่อแบรนด์, ชื่อรุ่นสินค้า, และคำศัพท์เฉพาะทางที่เป็นภาษาอังกฤษ (เช่น Logitech, Wave Keys, Logi Bolt, Bluetooth, USB-C, Type-C, ANC ฯลฯ) ให้คงรูปภาษาอังกฤษทางการไว้เสมอ ห้ามทับศัพท์เป็นคำไทยเพี้ยนๆ
- ห้ามใส่จุดไข่ปลา หรือ "..." หรือ "…" ในบทพูดหรือคำแปลโดยเด็ดขาด ให้ใช้การเว้นวรรคภาษาไทยธรรมดา เพื่อไม่ให้มีจุดติดไปที่ซับไตเติลบนหน้าจอ
- สินค้า IT ต้องมีตัวเลขสเปคจริงเสมอ (W, mAh, ms, Hz, dB) ห้ามมั่วตัวเลข ถ้าไม่รู้ให้เว้น
- ห้ามเคลมเกินจริง ห้ามใช้คำว่า "ดีที่สุดในโลก" "รักษาโรค" หรือคำที่พิสูจน์ไม่ได้
- ความยาวและโครงสร้างสคริปต์ (สำคัญมาก):
  * ถ้าต้องการคลิปมาตรฐาน 35–45 วินาที: ต้องเขียน 7–8 บรรทัด (ประมาณ 500–650 ตัวอักษร) ไล่สเต็ป: Hook หยุดนิ้ว (3 วิ) -> เปิด Pain Point คนใช้ -> เฉลยตัวช่วย/แกะกล่องสินค้า -> จุดเด่นที่ 1 พร้อมสเปกจริง -> จุดเด่นที่ 2 / ประสบการณ์สัมผัสจริง -> ความสะดวก/ความทนทาน -> ราคาโปรโมชั่น -> CTA ชี้พิกัดตะกร้า
  * ถ้าต้องการคลิปสั้นกระชับ 20–25 วินาที: ให้เขียน 5 บรรทัด (ประมาณ 300–380 ตัวอักษร)
- กฎการตัดประโยคคำบรรยาย:
  * แบ่งตามประโยคธรรมชาติที่ได้ใจความก่อนเว้นวรรค ห้ามตัดขาดกลางคำเดี่ยวๆ
  * ประโยคสั้น (<18 ตัวอักษร) รวมกันได้สูงสุด 2 ประโยคต่อ 1 บรรทัด (ไม่เกิน 34 ตัวอักษร)
  * ประโยคยาว (>=18 ตัวอักษร) ตัดเป็น 1 ประโยคเดี่ยวต่อ 1 บรรทัด
  * คำลงท้าย เช่น "ครับ", "ค่ะ", "บ้าง", "ๆ" ให้ต่อท้ายประโยคเดิมเสมอ
- ทุกบรรทัดต้องมี field "translation" เป็นคำแปลภาษาอังกฤษที่ตรงกับประโยคนั้นๆ 100%"""

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

        if task == "script":
            if "hook_title" in data and isinstance(data["hook_title"], str):
                data["hook_title"] = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', data["hook_title"])).strip()
            if "lines" in data and isinstance(data["lines"], list):
                for line in data["lines"]:
                    if "text" in line and isinstance(line["text"], str):
                        line["text"] = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', line["text"])).strip()
                    if "translation" in line and isinstance(line["translation"], str):
                        line["translation"] = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', line["translation"])).strip()

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
    # Execution modes: Antigravity Pro CLI & Google AI Studio API
    # ------------------------------------------------------------------
    @classmethod
    def has_antigravity_cli(cls) -> bool:
        """Check if the local Antigravity CLI (agy.exe) is installed and available."""
        if os.environ.get("DISABLE_ANTIGRAVITY", "").lower() in ("1", "true", "yes"):
            return False
        return get_agy_path() is not None

    @classmethod
    def get_api_keys(cls) -> List[str]:
        """Collect all Gemini API keys configured in environment and .env in order."""
        keys = []
        if ENV_FILE.exists():
            try:
                for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if "GEMINI_API_KEY" in k.strip() and v.strip() and v.strip() not in keys:
                            keys.append(v.strip())
            except Exception:
                pass
        for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_OLD"]:
            v = os.environ.get(k, "").strip()
            if v and v not in keys:
                keys.append(v)
        return keys

    @classmethod
    def has_api_key(cls) -> bool:
        """Check if any GEMINI_API_KEY is configured."""
        return len(cls.get_api_keys()) > 0

    @classmethod
    def is_available(cls) -> bool:
        """Available if either Antigravity CLI or any GEMINI_API_KEY exists."""
        return cls.has_antigravity_cli() or cls.has_api_key()

    @classmethod
    def call_antigravity_cli(
        cls,
        prompt: str,
        model: str = PRO_MODEL,
        timeout: int = 120,
    ) -> str:
        """
        Execute prompt via Antigravity CLI using the user's Pro account.
        Zero extra API fees, highly capable Gemini 3.8 Flash High reasoning.
        """
        agy_path = get_agy_path()
        if not agy_path:
            raise RuntimeError("Antigravity CLI (agy.exe) not found.")

        cmd = [
            str(agy_path),
            "-p",
            prompt,
            "--model",
            model,
            "--output-format",
            "text",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )

        if result.returncode != 0:
            err_msg = result.stderr.strip() or f"CLI exited with code {result.returncode}"
            raise RuntimeError(f"Antigravity CLI error: {err_msg}")

        return result.stdout.strip()

    @classmethod
    def generate(
        cls,
        task: str,
        context: Dict[str, Any],
        model: str = DEFAULT_MODEL,
        prefer_antigravity: bool = True,
    ) -> Dict[str, Any]:
        """
        Run `task` automatically:
        1. Try Antigravity Pro CLI (gemini-3.8-flash-high) first if available (uses Pro quota, zero extra cost).
        2. Fallback to Google AI Studio GEMINI_API_KEY if available.
        3. Fallback to ManualModeRequired (prompt for user to copy-paste).
        """
        prompt = cls.build_prompt(task, context)

        # 1. Preferred: Antigravity Pro (free with subscription, high reasoning)
        if prefer_antigravity and cls.has_antigravity_cli():
            t0 = time.time()
            try:
                print(f"✨ [AIBridge] Generating '{task}' via Antigravity Pro ({PRO_MODEL})...")
                raw_text = cls.call_antigravity_cli(prompt, model=PRO_MODEL)
                latency = time.time() - t0
                parsed = cls.parse_response(task, raw_text)
                try:
                    from scripts.token_tracker import TokenTracker
                    in_tok = max(100, len(prompt) // 2)
                    out_tok = max(50, len(raw_text) // 2)
                    think_tok = 1500  # High reasoning effort baseline
                    p_name = context.get("product_name", "") or context.get("product_title", "")
                    TokenTracker.record_event(
                        task=task,
                        model=PRO_MODEL,
                        provider="antigravity_pro",
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        latency_seconds=latency,
                        thinking_tokens=think_tok,
                        project_name=p_name
                    )
                except Exception:
                    pass
                return parsed
            except Exception as err:
                print(f"⚠️ [AIBridge] Antigravity Pro error ({err}) — attempting fallback to API Key...")

        # 2. Direct AI Studio API Key fallback (cycles through all configured keys)
        api_keys = cls.get_api_keys()
        if api_keys:
            from google import genai  # imported lazily so manual mode needs no SDK
            for key_idx, cur_key in enumerate(api_keys, 1):
                t0 = time.time()
                try:
                    print(f"⚡ [AIBridge] Generating '{task}' via Google AI Studio API ({model}) [Key #{key_idx}]...")
                    client = genai.Client(api_key=cur_key)
                    response = client.models.generate_content(model=model, contents=prompt)
                    latency = time.time() - t0
                    raw_text = response.text or ""
                    parsed = cls.parse_response(task, raw_text)
                    try:
                        from scripts.token_tracker import TokenTracker
                        in_tok = max(100, len(prompt) // 2)
                        out_tok = max(50, len(raw_text) // 2)
                        p_name = context.get("product_name", "") or context.get("product_title", "")
                        TokenTracker.record_event(
                            task=task,
                            model=model,
                            provider="gemini_api",
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            latency_seconds=latency,
                            project_name=p_name
                        )
                    except Exception:
                        pass
                    return parsed
                except Exception as api_err:
                    print(f"⚠️ [AIBridge] Key #{key_idx} error ({api_err}) — attempting next key...")
                    continue

        # 3. Manual copy-paste fallback
        raise ManualModeRequired(prompt, task)


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
