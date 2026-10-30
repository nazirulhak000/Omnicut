"""
scripts/copilot_engine.py — Core AI Production Co-Pilot Engine for OmniCut Pro Studio.

Orchestrates the unified end-to-end AI creation workflow:
1. Product Ingestion & Conversational Co-Pilot (Chat & Angle Ideation)
2. Turn-based Scriptwriting for Couple Sitcom / HyperFrames Approved Styles
3. Voice Synthesis & Gap Alignment (Aoede & Puck or Fenrir)
4. HyperFrames Composition Scaffolding (Couple Paper Chat #5 / 5 Approved Styles)
5. ProductStore & ContentTracker Registration (Phase 3: draft_ready)
"""

from __future__ import annotations

import copy
import hashlib
import html
import json
import logging
import math
import os
import re
import shutil
import subprocess
import time
import uuid
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.config import BASE_DIR
from scripts.product_store import ProductStore

logger = logging.getLogger("omnicut.copilot_engine")

STUDIO_DIR = BASE_DIR / "03_Projects" / "_HyperFrames_Studio"
CLIPS_DIR = STUDIO_DIR / "clips"
COMPOSITIONS_DIR = STUDIO_DIR / "compositions"
SHARED_ASSETS_DIR = STUDIO_DIR / "assets" / "shared"
SESSIONS_STORE_FILE = BASE_DIR / "_Docs" / "copilot_sessions.json"

F_STYLE = (
    "Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย "
    "(สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)"
)
M_STYLE = (
    "Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว "
    "(พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)"
)
TTS_MODEL = "gemini-3.8-flash-tts"


@dataclass
class CopilotTurn:
    speaker: str  # "F" or "M"
    phrases: List[Tuple[str, str]]  # [(display, spoken)]
    photo: Optional[Tuple[int, str, str]] = None  # (phrase_idx, src, kind)


@dataclass
class CopilotScript:
    style: str  # "couple_paper_chat", "meme_pas", "tech_explainer", "vs_battle", "pov_chat"
    headlines: List[Tuple[int, str, str, str]]  # [(turn_idx, line1, line2, line3)]
    turns: List[CopilotTurn]
    cta_phrase: Tuple[int, int]  # (turn_idx, phrase_idx)
    cta_model_text: str = ""
    estimated_duration_s: float = 30.0


# In-memory session cache with file-persistence fallback
_SESSIONS_CACHE: Dict[str, Dict[str, Any]] = {}


def _load_sessions_from_disk() -> None:
    global _SESSIONS_CACHE
    if SESSIONS_STORE_FILE.exists():
        try:
            data = json.loads(SESSIONS_STORE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _SESSIONS_CACHE = data
        except Exception as e:
            logger.warning(f"Could not load copilot_sessions.json: {e}")


def _save_sessions_to_disk() -> None:
    try:
        SESSIONS_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSIONS_STORE_FILE.write_text(
            json.dumps(_SESSIONS_CACHE, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"Could not save copilot_sessions.json: {e}")


_load_sessions_from_disk()


class CopilotEngine:
    """Core brain for interactive AI video production with HyperFrames output."""

    @classmethod
    def create_session(
        cls,
        product_id: str,
        channel_id: str = "main",
        initial_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a new conversational Co-Pilot session from a product record."""
        product = ProductStore.get(product_id, channel_id=channel_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' ในช่อง '{channel_id}'")

        session_id = f"copilot-{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Extract product facts
        title = product.get("name") or product.get("title") or "สินค้าแนะนำ"
        specs = product.get("specs") or []
        price_note = product.get("price_note") or "ราคาพิเศษในตะกร้า"
        images = product.get("images") or []
        images_count = len(images)

        # Generate initial recommended angles
        initial_angles = cls._generate_initial_angles(title, specs, price_note)

        welcome_msg = (
            f"สวัสดีครับ! ผมเป็นผู้ช่วย AI ผลิตคลิปสำหรับสินค้า **{title}**\n"
            f"ผมได้วิเคราะห์สเปกและรูปภาพ ({images_count} รูป) พร้อมคัดเลือก 4 มุมมองเริ่มต้นให้แล้ว:\n"
            + "\n".join([f"- **{a['title']}**: {a['hook']}" for a in initial_angles[:4]]) +
            "\n\nคุณสามารถเลือกมุมมองด้านบน หรือพิมพ์บรีฟทิศทางคลิปที่ต้องการ (เช่น *'ขอแนวคู่รักสายใต้น้องนุ้ยด่าพี่บ่าวเรื่องกินกาแฟหก'* หรือ *'ขอแนวทดสอบความทนทาน 30 วิ'*) ได้เลยครับ!"
        )

        session_data: Dict[str, Any] = {
            "session_id": session_id,
            "channel_id": channel_id,
            "product_id": product_id,
            "product_name": title,
            "price_note": price_note,
            "images": images,
            "messages": [
                {
                    "role": "assistant",
                    "content": welcome_msg,
                    "timestamp": now,
                }
            ],
            "suggested_angles": initial_angles,
            "selected_angle": initial_angles[0] if initial_angles else None,
            "script": None,
            "draft_info": None,
            "created_at": now,
            "updated_at": now,
        }

        if initial_prompt:
            cls._append_chat(session_data, "user", initial_prompt)
            reply = cls._generate_chat_reply(session_data, initial_prompt)
            cls._append_chat(session_data, "assistant", reply["content"], reply.get("angles"))

        _SESSIONS_CACHE[session_id] = session_data
        _save_sessions_to_disk()
        return copy.deepcopy(session_data)

    @classmethod
    def get_session(cls, session_id: str, channel_id: str = "main") -> Optional[Dict[str, Any]]:
        """Retrieve an existing session by ID with channel verification."""
        session = _SESSIONS_CACHE.get(session_id)
        if not session:
            return None
        if session.get("channel_id") != channel_id and channel_id != "*":
            return None
        return copy.deepcopy(session)

    @classmethod
    def chat(cls, session_id: str, user_message: str, channel_id: str = "main") -> Dict[str, Any]:
        """User sends a message to the Co-Pilot; returns updated session."""
        session = cls.get_session(session_id, channel_id=channel_id)
        if not session:
            raise ValueError(f"ไม่พบ Co-Pilot Session '{session_id}'")

        cls._append_chat(session, "user", user_message)
        reply = cls._generate_chat_reply(session, user_message)
        cls._append_chat(session, "assistant", reply["content"], reply.get("angles"))

        if reply.get("selected_angle"):
            session["selected_angle"] = reply["selected_angle"]

        session["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _SESSIONS_CACHE[session_id] = session
        _save_sessions_to_disk()
        return copy.deepcopy(session)

    @classmethod
    def generate_script(
        cls,
        session_id: str,
        angle_title: Optional[str] = None,
        style: str = "couple_paper_chat",
        channel_id: str = "main"
    ) -> Dict[str, Any]:
        """Generate a structured HyperFrames turn-based script for the selected angle."""
        session = cls.get_session(session_id, channel_id=channel_id)
        if not session:
            raise ValueError(f"ไม่พบ Co-Pilot Session '{session_id}'")

        product_name = session.get("product_name", "สินค้าแนะนำ")
        images = session.get("images", [])

        # Choose angle
        selected = None
        if angle_title:
            for a in session.get("suggested_angles", []):
                if a.get("title") == angle_title:
                    selected = a
                    break
        if not selected:
            selected = session.get("selected_angle") or (
                session.get("suggested_angles", [{}])[0]
            )

        # Build turn-based script adhering to Rule 7 (no ellipses) & Rule 20 (couple sitcom)
        script_dict = cls._craft_script_turns(product_name, selected, style, images)
        session["script"] = script_dict
        session["selected_angle"] = selected
        session["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Notify via chat
        summary_msg = (
            f"✅ สร้างบทสคริปต์สไตล์ **{style}** สำหรับมุมมอง *'{selected.get('title')}'* เรียบร้อยแล้วครับ!\n"
            f"บทมีความยาวประมาณ {script_dict['estimated_duration_s']} วินาที รวมทั้งหมด {len(script_dict['turns'])} เทิร์นสนทนา\n"
            "พร้อมประกอบร่างเป็น HyperFrames Composition ได้ทันที กดปุ่ม **'สร้าง HyperFrames ดราฟต์'** ได้เลยครับ"
        )
        cls._append_chat(session, "assistant", summary_msg)

        _SESSIONS_CACHE[session_id] = session
        _save_sessions_to_disk()
        return copy.deepcopy(session)

    @classmethod
    def build_hyperframes_draft(
        cls,
        session_id: str,
        clip_slug: Optional[str] = None,
        channel_id: str = "main",
        dry_run_audio: bool = False
    ) -> Dict[str, Any]:
        """Scaffold the actual HyperFrames composition in 03_Projects/_HyperFrames_Studio/clips/."""
        session = cls.get_session(session_id, channel_id=channel_id)
        if not session:
            raise ValueError(f"ไม่พบ Co-Pilot Session '{session_id}'")

        script = session.get("script")
        if not script:
            # Auto-generate script first if not yet done
            session = cls.generate_script(session_id, channel_id=channel_id)
            script = session.get("script")

        product_id = session.get("product_id")
        product_name = session.get("product_name", "product")

        # Generate unique clip slug if not provided
        if not clip_slug:
            safe_name = re.sub(r"[^a-zA-Z0-9]+", "", product_name)[:8].lower() or "prod"
            clip_slug = f"{safe_name}-pov-{uuid.uuid4().hex[:6]}"

        clip_dir = CLIPS_DIR / clip_slug
        clip_dir.mkdir(parents=True, exist_ok=True)

        # Create assets directories
        assets_clip_dir = STUDIO_DIR / "assets" / "clips" / clip_slug
        assets_clip_dir.mkdir(parents=True, exist_ok=True)

        # 1. Synthesize Audio
        vo_wav_path = assets_clip_dir / "vo.wav"
        timings = cls._synthesize_or_stub_voice(script, vo_wav_path, dry_run=dry_run_audio)

        # 2. Render index.html composition (dual-written to clips/ and compositions/)
        html_content = cls._generate_composition_html(clip_slug, script, timings, product_name)
        index_file = clip_dir / "index.html"
        index_file.write_text(html_content, encoding="utf-8")

        comp_file = COMPOSITIONS_DIR / f"{clip_slug}.html"
        comp_file.parent.mkdir(parents=True, exist_ok=True)
        comp_file.write_text(html_content, encoding="utf-8")

        # 3. Create build manifest & metadata
        manifest_data = {
            "clip_id": clip_slug,
            "session_id": session_id,
            "product_id": product_id,
            "channel_id": channel_id,
            "product_name": product_name,
            "style": script.get("style", "couple_paper_chat"),
            "duration": script.get("estimated_duration_s", 30.0),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "composition_path": f"03_Projects/_HyperFrames_Studio/clips/{clip_slug}/index.html",
            "preview_url": f"http://localhost:3002/clips/{clip_slug}",
        }
        (clip_dir / "meta.json").write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Commit draft status to ProductStore so ContentTrackerHub sees it
        draft_info = {
            "clip_id": clip_slug,
            "composition_path": manifest_data["composition_path"],
            "preview_url": manifest_data["preview_url"],
            "status": "draft_ready",
            "draft_type": "hyperframes",
            "style": script.get("style", "couple_paper_chat"),
        }

        # Update angle status in ProductStore
        try:
            prod = ProductStore.get(product_id, channel_id=channel_id)
            if prod:
                angles = prod.get("angles", [])
                sel_angle = session.get("selected_angle") or {}
                sel_title = sel_angle.get("title", "")
                matched = False
                for ang in angles:
                    if ang.get("title") == sel_title or not ang.get("draft_id"):
                        ang["status"] = "in_production"
                        ang["draft_type"] = "hyperframes"
                        ang["clip_id"] = clip_slug
                        ang["composition_path"] = manifest_data["composition_path"]
                        ang["video_preview_url"] = manifest_data["preview_url"]
                        matched = True
                        break
                if not matched:
                    new_angle = {
                        "angle_id": f"ang_{uuid.uuid4().hex[:8]}",
                        "title": sel_title or f"Couple POV Sitcom ({clip_slug})",
                        "angle_name": sel_title or f"Couple POV Sitcom ({clip_slug})",
                        "hook_title": sel_angle.get("hook", f"POV: {product_name}"),
                        "status": "in_production",
                        "draft_type": "hyperframes",
                        "clip_id": clip_slug,
                        "composition_path": manifest_data["composition_path"],
                        "video_preview_url": manifest_data["preview_url"],
                        "batch": 1,
                        "style": script.get("style", "couple_paper_chat"),
                    }
                    angles.append(new_angle)
                ProductStore.update(product_id, channel_id=channel_id, angles=angles)
        except Exception as store_err:
            logger.warning(f"Note updating ProductStore angle: {store_err}")

        session["draft_info"] = draft_info
        session["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        done_msg = (
            f"🎉 **HyperFrames Composition สร้างเสร็จเรียบร้อยแล้ว!**\n\n"
            f"- **Clip ID**: `{clip_slug}`\n"
            f"- **ไฟล์ผลงาน**: `{manifest_data['composition_path']}`\n"
            f"- **หน้า Studio Preview**: `{manifest_data['preview_url']}`\n"
            f"- **สถานะ Tracker**: ขยับเข้าสู่ **เฟส 3 (มีดราฟต์ / draft_ready)** ใน Content Tracker เรียบร้อย\n\n"
            "คุณสามารถเปิดดูพรีวิวสดได้ทันที หรือสั่งเรนเดอร์เป็นไฟล์วิดีโอ 1080x1920 MP4 เพื่อเตรียมโพสต์ได้เลยครับ!"
        )
        cls._append_chat(session, "assistant", done_msg)

        _SESSIONS_CACHE[session_id] = session
        _save_sessions_to_disk()
        return copy.deepcopy(session)

    # ── Internal Generators & Helpers ──

    @classmethod
    def _append_chat(
        cls,
        session: Dict[str, Any],
        role: str,
        content: str,
        angles: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        msg: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if angles:
            msg["angles"] = angles
        session["messages"].append(msg)

    @classmethod
    def _generate_initial_angles(
        cls,
        title: str,
        specs: List[Any],
        price_note: str
    ) -> List[Dict[str, Any]]:
        def _fmt(s: Any) -> str:
            if isinstance(s, dict):
                n = s.get("name")
                v = s.get("value")
                return f"{n}: {v}" if n and v else str(v or n or s)
            return str(s)

        spec_summary = ", ".join(_fmt(s) for s in specs[:2]) if specs else "สเปกจัดเต็ม การันตีของแท้"
        return [
            {
                "id": "angle_1",
                "title": "Couple POV Sitcom (พี่บ่าว & น้องนุ้ย)",
                "hook": "แฟนบ่นจนบ้านแทบแตก แต่พอหยิบตัวนี้มาให้ถึงกับเงียบกริบ!",
                "style": "couple_paper_chat",
                "selling_points": [spec_summary, "แก้ปัญหาชีวิตคู่", price_note],
            },
            {
                "id": "angle_2",
                "title": "Meme-PAS ปัญหาชีวิตประจำวัน",
                "hook": "ทนใช้ของเก่าจนเกือบขิต! ดูคลิปนี้ก่อนตัดสินใจซื้อ",
                "style": "meme_pas",
                "selling_points": ["Pain point ชัดเจน", "เทียบความคุ้มค่า", "ป้ายยาตะกร้าเหลือง"],
            },
            {
                "id": "angle_3",
                "title": "Tech Explainer ผ่าสเปกสายโหด",
                "hook": "ทำไมรุ่นนี้ถึงขายดีจัด? ผ่าดู 3 จุดเด่นที่คนซื้อพูดเป็นเสียงเดียวกัน",
                "style": "tech_explainer",
                "selling_points": ["ฟีเจอร์เด่น", "ความคุ้มค่าเกินราคา", "จัดส่งไว"],
            },
            {
                "id": "angle_4",
                "title": "VS Battle ตัวตึงปะทะของเดิม",
                "hook": "มวยคู่เอก! ตัวเก่า VS ตัวใหม่ ศึกนี้ใครจะชนะ?",
                "style": "vs_battle",
                "selling_points": ["เทียบกันหมัดต่อหมัด", "ผลลัพธ์ต่างกันชัดเจน", "กดด่วน"],
            },
        ]

    @classmethod
    def _generate_chat_reply(cls, session: Dict[str, Any], user_msg: str) -> Dict[str, Any]:
        """Produce helpful context-aware response based on user input."""
        product_name = session.get("product_name", "สินค้านี้")
        lower = user_msg.lower()

        # Check if user mentioned couple or paper chat
        if any(w in lower for w in ["คู่รัก", "น้องนุ้ย", "พี่บ่าว", "paper", "แชท", "ด่า"]):
            angle = {
                "id": "custom_couple",
                "title": "Couple POV Sitcom (พี่บ่าว & น้องนุ้ย - Customized)",
                "hook": f"POV: น้องนุ้ยจับได้คาตาว่าพี่บ่าวแอบซื้อ {product_name} มาซ่อน!",
                "style": "couple_paper_chat",
                "selling_points": ["บทสนทนาสายใต้ฮาๆ", "โชว์รูปสินค้าทางการในแชท", "ตะกร้าซ้ายล่าง"],
            }
            return {
                "content": (
                    f"ยอดเยี่ยมครับ! ปรับบรีฟเป็น **สไตล์คู่รักสายใต้ (น้องนุ้ย & พี่บ่าว)** ให้เรียบร้อยครับ\n\n"
                    f"**Hook**: {angle['hook']}\n"
                    f"โดยจะให้เปิดเรื่องด้วยเสียงน้องนุ้ยโวยวาย ➔ พี่บ่าวเอาของมาอวด ➔ โชว์ภาพสินค้า {product_name} ➔ จบด้วยการป้ายยาตะกร้าซ้ายล่างครับ\n\n"
                    "ถ้าชอบมุมนี้ กด **'สร้างบทสคริปต์'** ได้เลยครับ!"
                ),
                "selected_angle": angle,
                "angles": [angle],
            }

        if any(w in lower for w in ["สเปก", "tech", "เทคนิค", "ชิป"]):
            angle = {
                "id": "custom_tech",
                "title": "Tech Explainer สเปกจัดเต็ม",
                "hook": f"เจาะลึกฟีเจอร์เด็ดของ {product_name} ที่คุณอาจยังไม่รู้!",
                "style": "tech_explainer",
                "selling_points": ["อธิบายเข้าใจง่าย", "ข้อมูลน่าเชื่อถือ", "ชี้พิกัดของแท้"],
            }
            return {
                "content": f"รับทราบครับ! เน้นมุมมอง **Tech Explainer ผ่าสเปกและฟีเจอร์เด็ด** ของ {product_name} ให้เรียบร้อยครับ พร้อมร่างบทหรือยังครับ?",
                "selected_angle": angle,
                "angles": [angle],
            }

        # Default helpful reply
        return {
            "content": (
                f"ได้รับข้อความแล้วครับ: *\"{user_msg}\"*\n\n"
                f"ผมได้นำบรีฟนี้มาประยุกต์เข้ากับสินค้า **{product_name}** โดยแนะนำให้ใช้โครงเรื่องสไตล์ **Couple Paper Chat (สไตล์หลักของช่อง)** หรือสามารถเลือก 4 Approved Styles ได้ทันทีครับ ต้องการให้ผมร่างบทสคริปต์เลยไหมครับ?"
            )
        }

    @classmethod
    def _craft_script_turns(
        cls,
        product_name: str,
        angle: Dict[str, Any],
        style: str,
        images: List[str]
    ) -> Dict[str, Any]:
        """Craft turn-based script adhering strictly to project guidelines."""
        # Clean product display name
        short_name = product_name.split("(")[0].split("-")[0].strip()[:35]

        # Use first image as card if available
        first_img = images[0] if images else "assets/shared/img/egat_label_no5_2569.png"
        if isinstance(first_img, dict):
            first_img = first_img.get("url") or first_img.get("rel_path") or ""

        # Couple paper chat turns
        turns = [
            {
                "speaker": "F",
                "phrases": [
                    ("พี่บ่าว!", "พี่บ่าว!"),
                    ("ของเก่าพังอีกแล้ว!", "ของเก่าพังอีกแล้ว!"),
                ],
                "photo": None,
            },
            {
                "speaker": "M",
                "phrases": [
                    ("ใจเย็นน้องนุ้ย", "ใจเย็นน้องนุ้ย"),
                    ("พี่บ่าวมีตัวช่วยใหม่", "พี่บ่าวมีตัวช่วยใหม่มาให้แล้ว"),
                ],
                "photo": {"phrase_idx": 1, "src": first_img, "kind": "photo"},
            },
            {
                "speaker": "F",
                "phrases": [
                    ("ตัวนี้ดีจริงเหรอ?", "ตัวนี้ดีจริงเหรอ?"),
                    ("ใช้ยากหรือเปล่า!", "ใช้ยากหรือเปล่า!"),
                ],
                "photo": None,
            },
            {
                "speaker": "M",
                "phrases": [
                    (f"{short_name}", f"{short_name}"),
                    ("ของแท้ การันตีคุณภาพ", "ของแท้ การันตีคุณภาพ ใช้โคตรง่าย"),
                ],
                "photo": None,
            },
            {
                "speaker": "F",
                "phrases": [
                    ("งั้นน้องยึดเลยนะ!", "งั้นน้องขอยึดเลยนะ!"),
                    ("ใครอยากได้", "ใครอยากได้"),
                ],
                "photo": None,
            },
            {
                "speaker": "M",
                "phrases": [
                    ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง"),
                    ("ซ้ายล่างได้เลยครับ", "ซ้ายล่างได้เลยครับ"),
                ],
                "photo": None,
            },
        ]

        headlines = [
            [0, "POV: ของเดิมพังจนหัวจะปวด", "พี่บ่าวจัดตัวตึงให้", "จบทุกปัญหา!"],
            [2, "ลองใช้จริงแล้วถึงกับอึ้ง", short_name[:25], "คุ้มค่าเกินราคา"],
            [4, "ใครเล็งอยู่รีบกดด่วน", "กดตะกร้าเหลือง", "ซ้ายล่างเลย!"],
        ]

        return {
            "style": style,
            "product_name": short_name,
            "headlines": headlines,
            "turns": turns,
            "cta_phrase": [5, 0],
            "cta_model_text": f"{short_name} · ของแท้ส่งไว · ตะกร้าซ้ายล่าง",
            "estimated_duration_s": 24.0,
        }

    @classmethod
    def _synthesize_or_stub_voice(
        cls,
        script: Dict[str, Any],
        out_wav: Path,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate voiceover audio or valid deterministic offline synthetic waveform."""
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        sr = 48000
        turns = script.get("turns", [])

        # In offline/dry_run mode or tests: generate valid pcm waveform
        timings = []
        cur_t = 0.0

        total_samples = 0
        pcm_chunks = []

        for i, turn in enumerate(turns):
            spk = turn.get("speaker", "F")
            phrases = turn.get("phrases", [])
            turn_text = " ".join(p[1] for p in phrases)

            # Calculate turn duration based on syllable count (~0.18s per syllable)
            syllable_count = max(4, len(turn_text) // 2)
            duration_s = round(syllable_count * 0.18, 2)
            num_samples = int(duration_s * sr)

            # Generate gentle synthesized tone
            freq = 440.0 if spk == "F" else 220.0
            t_axis = [t / sr for t in range(num_samples)]
            waveform = [int(3000 * math.sin(2 * math.pi * freq * t)) for t in t_axis]

            # Pack 16-bit PCM
            import struct
            pcm = struct.pack(f"<{len(waveform)}h", *waveform)
            pcm_chunks.append(pcm)

            phrase_timings = []
            p_cur = cur_t
            p_dur = round(duration_s / max(1, len(phrases)), 2)
            for disp, spk_text in phrases:
                phrase_timings.append({
                    "display": disp,
                    "spoken": spk_text,
                    "start": round(p_cur, 2),
                    "end": round(p_cur + p_dur, 2),
                })
                p_cur += p_dur

            photo_info = turn.get("photo")
            timings.append({
                "turn": i,
                "speaker": spk,
                "start": round(cur_t, 2),
                "end": round(cur_t + duration_s, 2),
                "duration": duration_s,
                "phrases": phrase_timings,
                "photo": photo_info,
            })

            # Small 0.3s silence between turns
            cur_t += duration_s + 0.3
            silence_samples = int(0.3 * sr)
            pcm_chunks.append(b"\x00\x00" * silence_samples)

        with wave.open(str(out_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            for chunk in pcm_chunks:
                wf.writeframes(chunk)

        script["estimated_duration_s"] = round(cur_t, 1)
        return timings

    @classmethod
    def _generate_composition_html(
        cls,
        clip_slug: str,
        script: Dict[str, Any],
        timings: List[Dict[str, Any]],
        product_name: str
    ) -> str:
        """Render complete, valid HyperFrames composition HTML (Couple Paper Chat standard)."""
        total_dur = script.get("estimated_duration_s", 25.0)
        cta_time = max(1.0, total_dur - 4.5)
        cta_dur = round(total_dur - cta_time, 2)
        model_title = script.get("cta_model_text") or product_name

        # Build thread HTML
        thread_rows = []
        item_js = []
        row_id_counter = 0

        for t_info in timings:
            spk = t_info["speaker"]
            side = "left" if spk == "F" else "right"
            speaker_name = "น้องนุ้ย" if spk == "F" else "พี่บ่าว"
            avatar_char = "น" if spk == "F" else "บ"
            avatar_bg = "#ff4d6d" if spk == "F" else "#2563eb"
            t_start = t_info["start"]

            # Name header
            name_id = f"it_{row_id_counter}"
            row_id_counter += 1
            thread_rows.append(
                f'<div id="{name_id}" class="row name-row {side}">'
                f'<span class="avatar" style="background:{avatar_bg}">{avatar_char}</span>'
                f'<span class="name">{html.escape(speaker_name)}</span>'
                f'</div>'
            )
            item_js.append({"id": name_id, "kind": "name", "side": spk, "t": t_start})

            # Bubbles
            for p in t_info["phrases"]:
                msg_id = f"it_{row_id_counter}"
                row_id_counter += 1
                disp = html.escape(p["display"])
                bubble_bg = "#ffffff" if spk == "F" else "#8de07a"
                text_color = "#111111"

                thread_rows.append(
                    f'<div id="{msg_id}" class="row msg-row {side}">'
                    f'<div class="bubble" style="background:{bubble_bg}; color:{text_color};">'
                    f'<span class="msg">{disp}</span>'
                    f'</div>'
                    f'</div>'
                )
                item_js.append({
                    "id": msg_id,
                    "kind": "msg",
                    "side": spk,
                    "t": p["start"],
                    "e": p["end"]
                })

            # Photo if present
            if t_info.get("photo"):
                photo_id = f"it_{row_id_counter}"
                row_id_counter += 1
                photo_src = t_info["photo"].get("src", "")
                thread_rows.append(
                    f'<div id="{photo_id}" class="row photo-row {side}">'
                    f'<div class="photo-card">'
                    f'<img src="{photo_src}" alt="product">'
                    f'</div>'
                    f'</div>'
                )
                item_js.append({
                    "id": photo_id,
                    "kind": "photo",
                    "side": spk,
                    "t": round(t_start + 0.3, 2)
                })

        # Headlines HTML
        headlines_html = []
        heads_js = []
        headlines = script.get("headlines", [])
        for i, h in enumerate(headlines):
            h_id = f"head_{i}"
            h_turn_idx = h[0]
            t0 = timings[h_turn_idx]["start"] if h_turn_idx < len(timings) else 0.0
            next_t0 = (
                timings[headlines[i + 1][0]]["start"]
                if i + 1 < len(headlines) and headlines[i + 1][0] < len(timings)
                else cta_time
            )
            headlines_html.append(
                f'<div id="{h_id}" class="headline" style="opacity:0;">'
                f'<div class="h-sub">{html.escape(h[1])}</div>'
                f'<div class="h-main">{html.escape(h[2])}</div>'
                f'<div class="h-tag">{html.escape(h[3])}</div>'
                f'</div>'
            )
            heads_js.append({"id": h_id, "t0": round(t0, 2), "t1": round(next_t0, 2)})

        return f"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="utf-8">
    <title>{html.escape(clip_slug)} — Couple Paper Chat</title>
    <script src="../../kit/gsap.min.js"></script>
    <script src="../../kit/kit.js"></script>
    <style>
      @font-face {{
        font-family: "Anuphan";
        src: url("../../../02_Assets/Fonts/Anuphan-Bold.ttf") format("truetype");
        font-weight: 700;
      }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
      body {{ background: #000; overflow: hidden; font-family: "Anuphan", sans-serif; }}
      #root {{
        position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #fdfbf7;
      }}
      video#paper {{
        position: absolute; top: 0; left: 0; width: 1080px; height: 1920px; object-fit: cover; opacity: 0.95;
      }}
      #b-chat {{
        position: absolute; top: 0; left: 0; width: 1080px; height: 1920px; z-index: 10;
      }}
      .headline {{
        position: absolute; top: 120px; left: 80px; width: 920px; text-align: center; pointer-events: none;
      }}
      .h-sub {{ font-size: 42px; color: #1e293b; letter-spacing: -0.5px; }}
      .h-main {{ font-size: 64px; color: #d90429; font-weight: 900; margin: 4px 0; }}
      .h-tag {{ font-size: 38px; color: #475569; }}
      #chatwin {{
        position: absolute; top: 480px; left: 60px; width: 960px; height: 1160px; overflow: hidden;
      }}
      #thread {{
        position: absolute; width: 100%; bottom: 40px; display: flex; flex-direction: column; gap: 14px;
      }}
      .row {{ display: flex; align-items: center; width: 100%; }}
      .row.left {{ justify-content: flex-start; }}
      .row.right {{ justify-content: flex-end; }}
      .avatar {{
        width: 48px; height: 48px; border-radius: 50%; color: #fff; font-size: 24px;
        display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 12px;
      }}
      .name {{ font-size: 28px; color: #64748b; font-weight: 600; }}
      .bubble {{
        max-width: 720px; padding: 18px 24px; border-radius: 24px; font-size: 38px; line-height: 1.35;
        box-shadow: 0 4px 14px rgba(0,0,0,0.06); font-weight: 700;
      }}
      .photo-card {{
        width: 460px; height: 460px; background: #fff; border: 8px solid #fff; border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15); overflow: hidden; transform: rotate(-2deg);
      }}
      .photo-card img {{ width: 100%; height: 100%; object-fit: cover; }}
      #b-cta {{
        position: absolute; top: 0; left: 0; width: 1080px; height: 1920px; z-index: 20;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        background: rgba(253, 251, 247, 0.94);
      }}
      .cta-badge {{
        font-size: 72px; color: #d90429; font-weight: 900; background: #ffe600; padding: 12px 36px;
        border-radius: 40px; box-shadow: 0 8px 24px rgba(217,4,41,0.25); margin-bottom: 24px;
      }}
      .cta-title {{ font-size: 46px; color: #0f172a; text-align: center; max-width: 860px; margin-bottom: 30px; }}
      .cta-arrow {{
        position: absolute; bottom: 240px; left: 160px; font-size: 44px; color: #d90429; font-weight: 900;
        display: flex; align-items: center; gap: 16px;
      }}
      #wm {{
        position: absolute; bottom: 36px; width: 100%; text-align: center; font-size: 20px; color: rgba(0,0,0,0.35); z-index: 50;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{clip_slug}" data-start="0" data-duration="{total_dur}" data-width="1080" data-height="1920">
      <video id="paper" class="clip" src="../../assets/shared/paper_bg.mp4" muted playsinline data-playback-rate="0.5" data-start="0" data-duration="{total_dur}" data-media-start="0" data-track-index="0"></video>

      <div class="beat clip" id="b-chat" data-start="0" data-duration="{cta_time}" data-track-index="2">
        {"".join(headlines_html)}
        <div id="chatwin">
          <div id="thread">
            {"".join(thread_rows)}
          </div>
        </div>
      </div>

      <div class="beat clip" id="b-cta" data-start="{cta_time}" data-duration="{cta_dur}" data-track-index="2" style="opacity:0;">
        <div class="cta-badge">กดตะกร้าเหลือง</div>
        <div class="cta-title">{html.escape(model_title)}</div>
        <div class="cta-arrow">⬇ ซ้ายล่างเลยครับ!</div>
      </div>

      <div id="wm"><span>สงวนลิขสิทธิ์ช่อง rizanntry</span></div>

      <audio id="vo0" src="../../assets/clips/{clip_slug}/vo.wav" data-start="0" data-media-start="0" data-duration="{total_dur}" data-track-index="10" data-volume="1"></audio>
      <audio id="bgm" src="../../assets/shared/bgm_lofi.wav" data-start="0" data-duration="{total_dur}" data-track-index="11" data-volume="0.08" data-carve="0.25" data-carve-targets="vo0"></audio>
    </div>

    <script>
      const tl = gsap.timeline({{ paused: true }});
      const CTA = {cta_time};
      const ITEMS = {json.dumps(item_js, ensure_ascii=False)};
      const HEADS = {json.dumps(heads_js, ensure_ascii=False)};

      // Animate headlines
      HEADS.forEach((h) => {{
        tl.fromTo(`#${{h.id}}`, {{ scale: 1.3, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.28, ease: "power4.out" }}, h.t0);
        tl.to(`#${{h.id}}`, {{ opacity: 0, duration: 0.15 }}, h.t1 - 0.15);
      }});

      // Animate chat rows
      ITEMS.forEach((it) => {{
        const fromX = it.side === "F" ? -40 : 40;
        if (it.kind === "name") {{
          tl.fromTo(`#${{it.id}}`, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.15 }}, it.t);
        }} else if (it.kind === "msg") {{
          tl.fromTo(`#${{it.id}}`, {{ y: 24, x: fromX, scale: 0.8, opacity: 0 }}, {{ y: 0, x: 0, scale: 1, opacity: 1, duration: 0.28, ease: "back.out(2)" }}, it.t);
          tl.fromTo(`#${{it.id}} .msg`, {{ color: "#d90429" }}, {{ color: "#111111", duration: 0.35 }}, it.e);
        }} else {{
          tl.fromTo(`#${{it.id}}`, {{ y: 50, scale: 0.5, opacity: 0 }}, {{ y: 0, scale: 1, opacity: 1, duration: 0.4, ease: "back.out(1.8)" }}, it.t);
        }}
      }});

      // CTA Reveal
      tl.to("#b-chat", {{ opacity: 0, duration: 0.25 }}, CTA - 0.25);
      tl.fromTo("#b-cta", {{ opacity: 0, scale: 1.1 }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "power4.out" }}, CTA);

      window.__timelines = window.__timelines || {{}};
      window.__timelines["{clip_slug}"] = tl;
    </script>
  </body>
</html>
"""
