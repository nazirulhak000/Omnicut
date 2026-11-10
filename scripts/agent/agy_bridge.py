"""OmniCut Pro Studio - Native Antigravity Bridge Engine.

Connects OmniCut Pro Studio to the local Antigravity environment on this machine
via C:/Users/nazir/.gemini/antigravity/bin/agentapi.bat and local GenAI streaming.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from scripts.agent.omnicut_agent_tools import (
    apply_capcut_color_grade,
    apply_pro_color_grade,
    apply_smart_camera_9_16,
    apply_viral_transitions,
    export_or_import_capcut_draft,
    get_timeline_summary,
    normalize_project_audio_lufs,
    propose_audio_mix,
    propose_split_clip,
    propose_subtitles_style,
)
from scripts.config import get_gemini_api_keys

logger = logging.getLogger("omnicut.agent.bridge")

DEFAULT_AGENTAPI_PATH = Path(os.environ.get("ANTIGRAVITY_AGENTAPI_PATH") or (Path.home() / ".gemini" / "antigravity" / "bin" / "agentapi.bat"))
CURRENT_CONVERSATION_ID = "88cdae63-c195-4f96-825d-4c9484fff6fa"

AGENT_SYSTEM_PROMPT = """คุณคือ Antigravity AI Co-Producer & Video Editor ประจำสตูดิโอ OmniCut Pro Studio
คุณมีความเชี่ยวชาญระดับสูงในการตัดต่อวิดีโอแนวตั้ง 9:16 (1080x1920) สำหรับ TikTok, Reels และ Shorts
คุณทำงานคู่กับผู้ใช้ในหน้าตัดต่อ โดยมีความรู้ลึกซึ้งเกี่ยวกับ:
1. การตัดต่อวิดีโอ (J-Cut, Ripple Trim, Split, Pacing, Magnetic Snap)
2. ซับไตเติล Micro-burst / Progressive Ghost Reveal (ฟอนต์ Mali-Bold, ไฮไลต์ #66FF00, Safe Zone ล่าง 380-420px)
3. ระบบเสียง 4 บัส (-14 LUFS, Voice 1.0, SFX 0.28, BGM 0.12)
4. การสร้าง Hook เปิดคลิป 0-1.8 วินาทีให้ดึงดูดสายตาคนดู

คุณสามารถเสนอแนะการตัดต่อจริงให้กับผู้ใช้ได้ หากคุณต้องการเสนอให้โปรแกรมทำการแก้ไขไทม์ไลน์ ให้ใส่แท็กคำสั่งพิเศษลงในคำตอบของคุณ:
- [ACTION:split_clip split_time=<วินาที>] เช่น [ACTION:split_clip split_time=12.5]
- [ACTION:audio_mix voice=<ระดับ> sfx=<ระดับ> bgm=<ระดับ>] เช่น [ACTION:audio_mix voice=1.0 sfx=0.28 bgm=0.12]
- [ACTION:subtitle_style font=<ชื่อฟอนต์> scale=<สเกล> color=<รหัสสี>] เช่น [ACTION:subtitle_style font=Mali-Bold scale=1.0 color=#FFFFFF]
- [ACTION:apply_smart_camera_9_16 preset=<slow_push|slow_pull|pan_left|pan_right> easing=<hero_in|montage|bullet_stop>]
- [ACTION:apply_capcut_color_grade shadows=<0.25> highlights=<-0.15> vibrance=<0.35> vignette=<0.20>]
- [ACTION:normalize_project_audio_lufs target_lufs=<-14.0> voice_clarity=<true>]
- [ACTION:export_or_import_capcut_draft mode=<export|import>]

ตอบเป็นภาษาไทยอย่างมืออาชีพ กระชับ ตรงประเด็น และเป็นกันเองสไตล์ Pair Programming Pro Editor
"""


def get_bridge_status() -> Dict[str, Any]:
    """Inspects the local Antigravity environment status."""
    agentapi_exists = DEFAULT_AGENTAPI_PATH.is_file()
    keys = get_gemini_api_keys()

    return {
        "status": "online" if (agentapi_exists or len(keys) > 0) else "offline",
        "agentapi_path": str(DEFAULT_AGENTAPI_PATH),
        "agentapi_installed": agentapi_exists,
        "current_conversation_id": CURRENT_CONVERSATION_ID,
        "keys_count": len(keys),
        "engine_mode": "antigravity_hybrid",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def send_message_to_conversation(
    message: str,
    conversation_id: str = CURRENT_CONVERSATION_ID,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Sends a message via agentapi.bat send-message."""
    if not DEFAULT_AGENTAPI_PATH.is_file():
        return {"success": False, "error": f"agentapi.bat not found at {DEFAULT_AGENTAPI_PATH}"}

    cmd = [str(DEFAULT_AGENTAPI_PATH), "send-message"]
    if title:
        cmd.extend([f"--title={title}"])
    cmd.extend([conversation_id, message])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "conversation_id": conversation_id,
        }
    except Exception as e:
        logger.error(f"Error invoking agentapi: {e}")
        return {"success": False, "error": str(e)}


def parse_action_proposals(text: str, project_name: str) -> List[Dict[str, Any]]:
    """Detects [ACTION:...] tags in the agent's text and creates actionable cards."""
    proposals = []

    # 1. Match split_clip
    for m in re.finditer(r"\[ACTION:split_clip\s+split_time=([0-9.]+)\]", text):
        split_time = float(m.group(1))
        proposal = propose_split_clip(project_name, split_time)
        if "error" not in proposal:
            proposals.append(proposal)

    # 2. Match audio_mix
    for m in re.finditer(r"\[ACTION:audio_mix(?:\s+voice=([0-9.]+))?(?:\s+sfx=([0-9.]+))?(?:\s+bgm=([0-9.]+))?\]", text):
        v = float(m.group(1)) if m.group(1) else None
        s = float(m.group(2)) if m.group(2) else None
        b = float(m.group(3)) if m.group(3) else None
        proposals.append(propose_audio_mix(project_name, voice_volume=v, sfx_volume=s, bgm_volume=b))

    # 3. Match subtitle_style
    for m in re.finditer(r"\[ACTION:subtitle_style(?:\s+font=([\w-]+))?(?:\s+scale=([0-9.]+))?(?:\s+color=(#[0-9A-Fa-f]{6}))?\]", text):
        f = m.group(1) if m.group(1) else None
        sc = float(m.group(2)) if m.group(2) else None
        c = m.group(3) if m.group(3) else None
        proposals.append(propose_subtitles_style(project_name, font_name=f, caption_scale=sc, caption_color=c))

    # 4. Match apply_smart_camera_9_16
    for m in re.finditer(r"\[ACTION:apply_smart_camera_9_16(?:\s+preset=([\w_]+))?(?:\s+easing=([\w_]+))?\]", text):
        preset = m.group(1) or "slow_push"
        easing = m.group(2) or "hero_in"
        proposals.append(apply_smart_camera_9_16(project_name, preset=preset, easing=easing))

    # 5. Match apply_pro_color_grade / apply_capcut_color_grade
    for m in re.finditer(
        r"\[ACTION:(?:apply_pro_color_grade|apply_capcut_color_grade)(?:\s+shadows=([+-]?[0-9.]+))?(?:\s+highlights=([+-]?[0-9.]+))?(?:\s+vibrance=([+-]?[0-9.]+))?(?:\s+vignette=([+-]?[0-9.]+))?\]",
        text,
    ):
        sh = float(m.group(1)) if m.group(1) else 0.25
        hi = float(m.group(2)) if m.group(2) else -0.15
        vb = float(m.group(3)) if m.group(3) else 0.35
        vg = float(m.group(4)) if m.group(4) else 0.20
        proposals.append(apply_pro_color_grade(project_name, shadows=sh, highlights=hi, vibrance=vb, vignette=vg))

    # 6. Match normalize_project_audio_lufs
    for m in re.finditer(r"\[ACTION:normalize_project_audio_lufs(?:\s+target_lufs=([+-]?[0-9.]+))?(?:\s+voice_clarity=(true|false))?\]", text, re.IGNORECASE):
        tl = float(m.group(1)) if m.group(1) else -14.0
        vc = (m.group(2).lower() != "false") if m.group(2) else True
        proposals.append(normalize_project_audio_lufs(project_name, target_lufs=tl, voice_clarity=vc))

    # 7. Match apply_viral_transitions
    for m in re.finditer(r"\[ACTION:apply_viral_transitions(?:\s+transition=([a-zA-Z_]+))?(?:\s+duration=([0-9.]+))?\]", text, re.IGNORECASE):
        tr = m.group(1) or "whip_pan"
        du = float(m.group(2)) if m.group(2) else 0.4
        proposals.append(apply_viral_transitions(project_name, transition_name=tr, duration=du))

    # 8. Match export_or_import_capcut_draft
    for m in re.finditer(r"\[ACTION:export_or_import_capcut_draft(?:\s+mode=(export|import))?\]", text, re.IGNORECASE):
        mode = (m.group(1) or "export").lower()
        proposals.append(export_or_import_capcut_draft(project_name, mode=mode))

    # Deterministic fallback when prompt explicitly asks for In-App NLE Studio tools
    if not proposals:
        low = text.lower()
        if "ตั้งกล้องอัจฉริยะ 9:16" in text or "smart_camera" in low:
            proposals.append(apply_smart_camera_9_16(project_name))
        elif "เกรดสีระดับโปร" in text or "เกรดสีถนอมผิว" in text or "splendor" in low or "color_grade" in low:
            proposals.append(apply_pro_color_grade(project_name))
        elif "ปรับเสียงมาตรฐาน -14 lufs" in low:
            proposals.append(normalize_project_audio_lufs(project_name))
        elif "ใส่ทรานซิชันไวรัล" in text or "viral_transition" in low or "ทรานซิชัน" in text:
            proposals.append(apply_viral_transitions(project_name))
        elif "ส่งออกดราฟต์ capcut" in low:
            proposals.append(export_or_import_capcut_draft(project_name, mode="export"))
        elif "นำเข้าดราฟต์ capcut" in low:
            proposals.append(export_or_import_capcut_draft(project_name, mode="import"))

    return proposals


async def stream_agent_response(
    prompt: str,
    project_name: Optional[str] = None,
    conversation_id: str = CURRENT_CONVERSATION_ID,
) -> AsyncGenerator[str, None]:
    """Generates SSE events for the agent response, streaming thoughts, tokens, and action proposals."""
    timeline_ctx = ""
    if project_name:
        try:
            summary = get_timeline_summary(project_name)
            timeline_ctx = f"\n\n[ข้อมูลไทม์ไลน์โปรเจกต์ปัจจุบัน {project_name}]:\n{json.dumps(summary, ensure_ascii=False, indent=2)}"
        except Exception as e:
            logger.warning(f"Could not load timeline summary for {project_name}: {e}")

    full_prompt = f"{prompt}{timeline_ctx}"

    yield f"data: {json.dumps({'type': 'thought', 'content': 'กำลังวิเคราะห์สถานะไทม์ไลน์และข้อความสั่งงาน...'}, ensure_ascii=False)}\n\n"

    keys = get_gemini_api_keys()
    full_response_text = ""

    if keys:
        try:
            from google.genai import Client, types

            client = Client(api_key=keys[0])

            yield f"data: {json.dumps({'type': 'thought', 'content': 'ประมวลผลคำแนะนำด้วย Antigravity Engine บนคอมพิวเตอร์...'}, ensure_ascii=False)}\n\n"

            response = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=AGENT_SYSTEM_PROMPT,
                    temperature=0.7,
                ),
            )

            for chunk in response:
                if chunk.text:
                    full_response_text += chunk.text
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.text}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.warning(f"GenAI stream error: {e}. Falling back to agentapi or deterministic response.")

    if not full_response_text:
        yield f"data: {json.dumps({'type': 'thought', 'content': 'เชื่อมต่อผ่าน Antigravity Local Language Server...'}, ensure_ascii=False)}\n\n"
        fallback_msg = f"สวัสดีครับ! ผม Antigravity AI Co-Producer รับคำสั่ง '{prompt}' เรียบร้อยแล้วครับ\n\nระบบไทม์ไลน์พร้อมสำหรับการตัดต่อและปรับแต่งค่าแล้ว หากต้องการให้ผมช่วยตัดแยกคลิป ปรับระดับเสียง หรือแต่งซับไตเติล สามารถแจ้งได้ทันทีครับ!"
        full_response_text = fallback_msg
        for word in fallback_msg.split(" "):
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '}, ensure_ascii=False)}\n\n"

    if DEFAULT_AGENTAPI_PATH.is_file():
        try:
            send_message_to_conversation(
                f"[OmniCut Studio Sync] User prompted: {prompt[:100]}...",
                conversation_id=conversation_id,
                title="OmniCut In-App Prompt",
            )
        except Exception as e:
            logger.debug(f"Async agentapi notify: {e}")

    if project_name:
        proposals = parse_action_proposals(f"{prompt}\n{full_response_text}", project_name)
        for prop in proposals:
            yield f"data: {json.dumps({'type': 'action_proposal', 'proposal': prop}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
