import sys
from pathlib import Path
import streamlit as st
import os
import glob
import time
import datetime
import subprocess

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    FONTS_DIR, SFX_DIR, MUSIC_DIR, PROJECTS_DIR,
    CAPCUT_DRAFT_DIR, VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.script_generator import ScriptGenerator
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.voice_engine import VoiceEngine

# ---------------------------------------------------------
# Page Configuration & Global Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="TikTok Auto-Cutter Pro Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# High-End UI Stylesheet (Glassmorphism + Neon TikTok Pro)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600;700;800;900&family=Prompt:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Prompt', 'Kanit', 'Inter', sans-serif;
    }

    /* Main background and layout */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(254, 44, 85, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 90% 80%, rgba(37, 244, 238, 0.05) 0%, transparent 40%),
                    #0B0E14;
        color: #E2E8F0;
    }

    /* Glass Cards */
    .pro-card {
        background: rgba(22, 27, 38, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .pro-card:hover {
        border-color: rgba(254, 44, 85, 0.3);
        box-shadow: 0 12px 35px rgba(254, 44, 85, 0.1);
    }

    .pro-card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 1.2rem;
        padding-bottom: 0.8rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .step-badge {
        background: linear-gradient(135deg, #FE2C55, #FF0050);
        color: white;
        font-weight: 800;
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 10px rgba(254, 44, 85, 0.4);
    }

    .step-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
        letter-spacing: -0.3px;
    }

    /* Top Brand Hero */
    .hero-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.2rem 2rem;
        background: rgba(16, 20, 29, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        margin-bottom: 1.8rem;
        backdrop-filter: blur(20px);
    }

    .hero-title {
        font-size: 1.9rem;
        font-weight: 900;
        font-family: 'Kanit', sans-serif;
        background: linear-gradient(90deg, #FE2C55 0%, #FF0050 40%, #25F4EE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }

    .hero-subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        margin: 4px 0 0 0;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background: rgba(37, 244, 238, 0.1);
        color: #25F4EE;
        border: 1px solid rgba(37, 244, 238, 0.25);
    }

    .status-pill.red {
        background: rgba(254, 44, 85, 0.1);
        color: #FE2C55;
        border-color: rgba(254, 44, 85, 0.25);
    }

    /* Script Preview Lines */
    .script-timeline-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: rgba(11, 14, 20, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 10px 14px;
        border-radius: 10px;
        margin-bottom: 8px;
    }
    .sfx-badge {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        background: #232A3B;
        color: #25F4EE;
        border: 1px solid rgba(37, 244, 238, 0.3);
        white-space: nowrap;
    }

    /* Hero CTA Button */
    .stButton>button[kind="primary"], .hero-btn>button {
        background: linear-gradient(90deg, #FE2C55 0%, #FF0050 50%, #E02449 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 1.25rem !important;
        height: 3.8rem !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 8px 25px rgba(254, 44, 85, 0.45) !important;
        transition: all 0.25s ease !important;
    }
    .stButton>button[kind="primary"]:hover, .hero-btn>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 30px rgba(254, 44, 85, 0.65) !important;
        background: linear-gradient(90deg, #FF0050 0%, #FE2C55 100%) !important;
    }

    /* Custom Form Fields */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #121620 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #F8FAFC !important;
        border-radius: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #FE2C55 !important;
        box-shadow: 0 0 0 2px rgba(254, 44, 85, 0.2) !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(16, 20, 29, 0.7);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
        color: #94A3B8;
        background: transparent;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: #212838 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }

    /* Video Gallery Card */
    .video-card {
        background: #141824;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    .video-card:hover {
        border-color: rgba(37, 244, 238, 0.4);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def scan_raw_videos():
    candidates = []
    for ext in ("*.mov", "*.mp4", "*.m4v", "*.MOV", "*.MP4"):
        candidates.extend(glob.glob(str(RAW_DIR / "**" / ext), recursive=True))
        candidates.extend(glob.glob(str(INBOX_DIR / "**" / ext), recursive=True))
    return sorted(list(set(candidates)), key=os.path.getmtime, reverse=True)

def scan_exports():
    return sorted(list(EXPORTS_DIR.glob("*.mp4")), key=os.path.getmtime, reverse=True)

def open_folder_in_explorer(folder_path: Path):
    try:
        if os.name == 'nt':
            os.startfile(str(folder_path))
    except Exception as e:
        st.toast(f"ไม่สามารถเปิดโฟลเดอร์ได้: {e}", icon="⚠️")

# ---------------------------------------------------------
# Top Brand Hero Bar
# ---------------------------------------------------------
capcut_ready = CAPCUT_DRAFT_DIR.exists()
raw_list = scan_raw_videos()
exports_list = scan_exports()

st.markdown(f"""
<div class="hero-container">
    <div>
        <div class="hero-title">⚡ TikTok Auto-Cutter Pro Studio</div>
        <div class="hero-subtitle">ระบบ AI ตัดต่อคลิปสินค้าไวรัลอัตโนมัติ — คิดบท • พากย์เสียง HD • ซอยคัตซูม • วิ่งซับ Kanit • SFX & BGM ครบวงจร</div>
    </div>
    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <span class="status-pill">🔥 FFmpeg Ready</span>
        <span class="status-pill {'red' if not capcut_ready else ''}">
            {'💻 CapCut PC Synced' if capcut_ready else '⚠️ CapCut Local Path'}
        </span>
        <span class="status-pill">🎬 {len(exports_list)} Exported</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Main Navigation Tabs
# ---------------------------------------------------------
tab_studio, tab_gallery, tab_script_lab, tab_assets = st.tabs([
    "🚀 1. Studio Creator (สร้างคลิปใหม่)",
    "📦 2. Export Gallery (คลังคลิปพร้อมโพสต์)",
    "💡 3. AI Script Lab & Hooks (คลังไอเดีย & แคปชั่น)",
    "⚙️ 4. System & Assets (จัดการโฟลเดอร์ & ทรัพยากร)"
])

# =========================================================
# TAB 1: STUDIO CREATOR (4 STEP WORKFLOW)
# =========================================================
with tab_studio:
    # Top Quick Presets Bar
    st.markdown("##### ⚡ Quick Preset Templates (เลือกหมวดหมู่สินค้าเพื่อกรอกข้อมูลด่วน)")
    preset_cols = st.columns(4)
    
    preset_gadget = preset_cols[0].button("🔌 อุปกรณ์ไอที / แกดเจ็ต", use_container_width=True)
    preset_home = preset_cols[1].button("🏠 ของใช้ในบ้าน / มินิมอล", use_container_width=True)
    preset_beauty = preset_cols[2].button("💄 สกินแคร์ / ความงาม", use_container_width=True)
    preset_deal = preset_cols[3].button("🔥 Flash Sale / ลดแหลก", use_container_width=True)

    # State management for presets
    if "prod_name" not in st.session_state:
        st.session_state.prod_name = "Esseger สายชาร์จแม่เหล็ก"
        st.session_state.pain = "สายชาร์จพังง่าย เสียบยากในที่มืด"
        st.session_state.deal = "ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง"
        st.session_state.features = "แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก"
        st.session_state.hook_title = "🔥 อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก"

    if preset_gadget:
        st.session_state.prod_name = "Esseger สายชาร์จแม่เหล็ก"
        st.session_state.pain = "สายชาร์จพันกัน เสียบยากในที่มืด"
        st.session_state.deal = "ลดพิเศษวันนี้ จิ้มตะกร้าซ้ายล่าง"
        st.session_state.features = "แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก"
        st.session_state.hook_title = "⚡ อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก"
        st.rerun()

    elif preset_home:
        st.session_state.prod_name = "เครื่องดูดฝุ่นไร้สายมินิมอล"
        st.session_state.pain = "ฝุ่นตามซอกทำความสะอาดยาก เครื่องใหญ่หนักมือ"
        st.session_state.deal = "ลด 50% วันนี้ ส่งฟรีถึงบ้าน"
        st.session_state.features = "พลังดูดแรงสูง ไร้สาย น้ำหนักเบา แบตอึด ดีไซน์สวยเข้ากับบ้าน"
        st.session_state.hook_title = "🏠 ของใช้ในบ้านที่ต้องมี! เครื่องดูดฝุ่นไร้สาย"
        st.rerun()

    elif preset_beauty:
        st.session_state.prod_name = "เซรั่มไฮยาหน้าฉ่ำโกลว์"
        st.session_state.pain = "หน้าแห้ง แต่งหน้าไม่ติด ผิวโทรมดูหมองคล้ำ"
        st.session_state.deal = "โปร 1 แถม 1 จัดในตะกร้าด่วน"
        st.session_state.features = "ซึมไวไม่เหนียวเหนอะ ล็อคความชุ่มชื้น 72 ชม. หน้าฉ่ำใส รูขุมขนกระชับ"
        st.session_state.hook_title = "✨ กู้ผิวโทรมด่วน! เซรั่มหน้าฉ่ำโกลว์"
        st.rerun()

    elif preset_deal:
        st.session_state.prod_name = "พาวเวอร์แบงค์ชาร์จไว 20000mAh"
        st.session_state.pain = "แบตมือถือหมดระหว่างวัน พกพาวเวอร์แบงค์หนักๆ"
        st.session_state.deal = "Flash Sale 199.- วันนี้วันเดียวเท่านั้น"
        st.session_state.features = "บางเบาพกง่าย ชาร์จเร็ว 22.5W มีสายในตัวไม่ต้องพกสายเพิ่ม"
        st.session_state.hook_title = "🔥 Flash Sale วันเดียว! พาวเวอร์แบงค์ชาร์จไว"
        st.rerun()

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # 2 Main Columns Layout
    col_left, col_right = st.columns([1.05, 0.95], gap="large")

    # ---------------------------------------------------------
    # LEFT COLUMN: STEP 1 (MEDIA) & STEP 2 (SCRIPT)
    # ---------------------------------------------------------
    with col_left:
        # STEP 1: RAW FOOTAGE
        st.markdown("""
        <div class="pro-card">
            <div class="pro-card-header">
                <span class="step-badge">STEP 1</span>
                <span class="step-title">📹 วัตถุดิบวิดีโอสินค้า (Raw Footage)</span>
            </div>
        """, unsafe_allow_html=True)

        video_source_mode = st.radio(
            "เลือกแหล่งที่มาของวิดีโอ:",
            ["📂 เลือกจากเครื่อง (00_Inbox / 01_Raw)", "⬆️ อัปโหลดไฟล์ใหม่ (.mp4, .mov)"],
            horizontal=True,
            label_visibility="collapsed"
        )

        selected_video_path = None
        if video_source_mode.startswith("📂"):
            if raw_list:
                rel_choices = [os.path.relpath(p, str(BASE_DIR)) for p in raw_list]
                selected_rel = st.selectbox("เลือกไฟล์วิดีโอที่ต้องการตัดต่อ:", rel_choices, index=0)
                selected_video_path = str(BASE_DIR / selected_rel)
            else:
                st.warning("⚠️ ยังไม่พบไฟล์วิดีโอใน 00_Inbox หรือ 01_Raw กรุณาวางไฟล์หรือเลือกอัปโหลด")
        else:
            uploaded_raw = st.file_uploader("ลากไฟล์วิดีโอมาวางที่นี่ (.mp4, .mov)", type=["mp4", "mov", "m4v"])
            if uploaded_raw:
                save_dest = INBOX_DIR / uploaded_raw.name
                with open(save_dest, "wb") as f:
                    f.write(uploaded_raw.getbuffer())
                selected_video_path = str(save_dest)
                st.success(f"✅ บันทึกไฟล์สำเร็จ: `{uploaded_raw.name}`")

        if selected_video_path and os.path.exists(selected_video_path):
            v_size_mb = os.path.getsize(selected_video_path) / (1024 * 1024)
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.3); padding: 8px 12px; border-radius: 8px; margin: 8px 0;">
                <span style="font-size: 0.85rem; color: #25F4EE;">📁 {os.path.basename(selected_video_path)}</span>
                <span style="font-size: 0.8rem; color: #94A3B8;">{v_size_mb:.1f} MB</span>
            </div>
            """, unsafe_allow_html=True)
            st.video(selected_video_path)

        st.markdown("</div>", unsafe_allow_html=True)

        # STEP 2: SCRIPT & STORYTELLING
        st.markdown("""
        <div class="pro-card">
            <div class="pro-card-header">
                <span class="step-badge">STEP 2</span>
                <span class="step-title">✍️ สคริปต์รีวิว & การป้ายยา (Copywriting)</span>
            </div>
        """, unsafe_allow_html=True)

        prod_name_input = st.text_input("📦 ชื่อสินค้า:", value=st.session_state.prod_name)
        hook_title_input = st.text_input("🔥 ข้อความพาดหัว Hook ด้านบนจอ:", value=st.session_state.hook_title)

        s_col1, s_col2 = st.columns(2)
        with s_col1:
            pain_input = st.text_input("😫 ปัญหาของคนดู (Pain Point):", value=st.session_state.pain)
        with s_col2:
            deal_input = st.text_input("🏷️ โปรโมชั่น / CTA (Deal):", value=st.session_state.deal)

        features_input = st.text_area(
            "✨ จุดเด่นสินค้า (Key Features):",
            value=st.session_state.features,
            height=70
        )

        use_custom_script = st.toggle("🛠️ เปิดโหมดปรับแต่งสคริปต์ละเอียดรายบรรทัด (Pro Script Editor)", value=False)
        custom_script_text = None

        if use_custom_script:
            default_custom_lines = (
                f"{hook_title_input}\n"
                f"{prod_name_input} ตัวเดียวจบทุกปัญหา\n"
                f"{features_input}\n"
                f"{deal_input}"
            )
            custom_script_text = st.text_area(
                "พิมพ์สคริปต์แยกบรรทัด (1 บรรทัด = 1 ท่อนซับ + ซอยคัตภาพ 1 ช็อต):",
                value=default_custom_lines,
                height=130
            )
        else:
            # Generate preview of AI lines
            demo_script = ScriptGenerator.generate(
                product_name=prod_name_input,
                key_features=features_input,
                pain_point=pain_input,
                price_deal=deal_input
            )
            st.markdown("<div style='margin-top: 10px; font-size: 0.85rem; color: #94A3B8;'>👀 ตัวอย่างสคริปต์อัตโนมัติ & ไทม์ไลน์ SFX:</div>", unsafe_allow_html=True)
            for idx, line in enumerate(demo_script["lines"]):
                sfx_tag = line.get("sfx", "pop")
                st.markdown(f"""
                <div class="script-timeline-item">
                    <span class="sfx-badge">🔊 {sfx_tag.upper()}</span>
                    <span style="font-size: 0.9rem; color: #F1F5F9;">{line['text']}</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # RIGHT COLUMN: STEP 3 (VOICE & AUDIO) & STEP 4 (RENDER)
    # ---------------------------------------------------------
    with col_right:
        # STEP 3: VOICE & AUDIO
        st.markdown("""
        <div class="pro-card">
            <div class="pro-card-header">
                <span class="step-badge">STEP 3</span>
                <span class="step-title">🎙️ เสียงพากย์ & เอฟเฟกต์เสียง (Audio Studio)</span>
            </div>
        """, unsafe_allow_html=True)

        voice_mode = st.radio(
            "เลือกสไตล์เสียงพากย์:",
            [
                "⚡ เสียงพากย์ TikTok HD พลังสูง (ชัด 100% + สปีด 1.2x แนะนำที่สุด!)",
                "🎙️ ใช้เสียงคนพูดจริง (อัปโหลดไฟล์เสียงพูดเอง / Voice Memo)",
                "📹 ดึงเสียงพูดจากคลิปวิดีโอสินค้า",
                "🤖 F5-TTS Thai (โคลนเสียง AI Local ~45 วิ)"
            ],
            index=0
        )

        voice_engine_selected = "edge_tts"
        f5_preset_choice = "tiktok_male_pro"
        f5_custom_audio = None
        f5_custom_text = None
        human_voice_file_path = None
        voice_key = "female"
        rate_val = "+20%"

        if voice_mode.startswith("⚡ เสียงพากย์ TikTok HD"):
            voice_engine_selected = "edge_tts"
            v_col1, v_col2 = st.columns(2)
            with v_col1:
                voice_gender_label = st.selectbox("โทนเสียง:", ["เสียงผู้หญิงสดใส (TikTok Pro)", "เสียงผู้ชายมั่นใจ (Standard)"])
                voice_key = "female" if "ผู้หญิง" in voice_gender_label else "male"
            with v_col2:
                voice_speed_label = st.select_slider(
                    "ความเร็วสปีดคำพูด:",
                    options=["1.1x (+10%)", "1.15x (+15%)", "1.2x (+20%)", "1.25x (+25%)"],
                    value="1.2x (+20%)"
                )
                rate_val = "+" + voice_speed_label.split("(")[1].replace(")", "").replace("+", "")

            # Quick audio tester
            test_voice_btn = st.button("🔊 ทดลองฟังตัวอย่างเสียงพากย์ (2 วิ)", use_container_width=True)
            if test_voice_btn:
                with st.spinner("กำลังสังเคราะห์ตัวอย่างเสียง..."):
                    test_sample_path = BASE_DIR / "test_voice.mp3"
                    try:
                        VoiceEngine.generate_crystal_voice(
                            text_or_lines=f"สวัสดีค่ะ นี่คือเสียงตัวอย่างสำหรับคลิป {prod_name_input}",
                            output_audio_path=str(test_sample_path),
                            speed=1.20
                        )
                        st.audio(str(test_sample_path))
                    except Exception as e:
                        st.error(f"ไม่สามารถสร้างตัวอย่างเสียงได้: {e}")

        elif voice_mode.startswith("🎙️ ใช้เสียงคนพูดจริง"):
            st.info("💡 นำไฟล์เสียงอัดจากมือถือ (Voice Memos) มาอัปโหลด ระบบจะซิงก์คัตให้พอดีอัตโนมัติ")
            uploaded_voice = st.file_uploader("เลือกไฟล์เสียง (.mp3, .wav, .m4a):", type=["mp3", "wav", "m4a"])
            if uploaded_voice:
                v_save = INBOX_DIR / uploaded_voice.name
                with open(v_save, "wb") as f:
                    f.write(uploaded_voice.getbuffer())
                human_voice_file_path = str(v_save)
                st.audio(human_voice_file_path)
                st.success(f"✅ โหลดไฟล์เสียงสำเร็จ: {uploaded_voice.name}")

        elif voice_mode.startswith("📹 ดึงเสียงพูดจากคลิปวิดีโอ"):
            if selected_video_path and os.path.exists(selected_video_path):
                st.info(f"💡 ระบบจะดึงแทร็กเสียงจากคลิป `{os.path.basename(selected_video_path)}` มาใช้งาน")
                human_voice_file_path = selected_video_path
            else:
                st.warning("กรุณาเลือกไฟล์วิดีโอใน Step 1 ก่อนครับ")

        elif voice_mode.startswith("🤖 F5-TTS Thai"):
            voice_engine_selected = "f5_tts"
            st.caption("โมเดลโคลนเสียงภาษาไทย Local AI รันบนเครื่อง ไม่ต้องต่อเน็ต")
            f5_tab1, f5_tab2 = st.tabs(["🎯 พรีเซ็ตสำเร็จรูป", "📁 อัปโหลดเสียงต้นแบบ"])
            with f5_tab1:
                f5_presets = {
                    "tiktok_male_pro": "🔥 TikTok Pro Male (เสียงผู้ชายสายขายของ)",
                    "tiktok_female_pro": "✨ TikTok Pro Female (เสียงผู้หญิงสดใส)",
                    "tiktok_hype_seller": "⚡ TikTok Hype Seller (เร่งปิดการขาย)"
                }
                f5_choice = st.selectbox("เลือกเสียงต้นแบบ:", list(f5_presets.values()))
                for k, v in f5_presets.items():
                    if v == f5_choice:
                        f5_preset_choice = k
                        break
            with f5_tab2:
                f5_up = st.file_uploader("ไฟล์เสียงพูด 5-10 วินาที (.wav, .mp3):", type=["wav", "mp3"])
                if f5_up:
                    f5_save = INBOX_DIR / f"ref_{f5_up.name}"
                    with open(f5_save, "wb") as f:
                        f.write(f5_up.getbuffer())
                    f5_custom_audio = str(f5_save)
                    f5_custom_text = st.text_input("คำที่คนในคลิปพูด (Reference Text):", value="")

        st.markdown("</div>", unsafe_allow_html=True)

        # STEP 4: RENDER & EXPORT
        st.markdown("""
        <div class="pro-card">
            <div class="pro-card-header">
                <span class="step-badge">STEP 4</span>
                <span class="step-title">🚀 ตัวเลือกการส่งออก (Render Hub)</span>
            </div>
        """, unsafe_allow_html=True)

        out_c1, out_c2 = st.columns(2)
        with out_c1:
            opt_mp4 = st.checkbox("🎬 เรนเดอร์เป็นไฟล์ .MP4 (9:16)", value=True)
        with out_c2:
            opt_capcut = st.checkbox("💻 สร้าง CapCut PC Project Draft", value=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # BIG HERO CTA BUTTON
        btn_start = st.button("⚡ เริ่มต้นตัดต่อวิดีโออัตโนมัติ (Start Auto-Cut)", type="primary", use_container_width=True)

        if btn_start:
            if not selected_video_path or not os.path.exists(selected_video_path):
                st.error("❌ กรุณาเลือกไฟล์วิดีโอสินค้าใน STEP 1 ก่อนครับ!")
            else:
                status_box = st.status("🚀 กำลังรัน Pipeline ตัดต่อวิดีโอ TikTok อัตโนมัติ...", expanded=True)
                prog_bar = st.progress(0, text="กำลังวิเคราะห์ข้อมูล...")

                def on_pipe_progress(msg: str, val: float):
                    prog_bar.progress(min(100, int(val * 100)), text=msg)
                    status_box.write(f"✅ {msg}")
                    status_box.update(label=f"⏳ {msg} ({int(val * 100)}%)", state="running")

                try:
                    res = TikTokAutoCutterPipeline.run(
                        product_name=prod_name_input,
                        raw_video_path=selected_video_path,
                        key_features=features_input,
                        pain_point=pain_input,
                        price_deal=deal_input,
                        custom_script=custom_script_text if use_custom_script else None,
                        voice=voice_key,
                        voice_rate=rate_val,
                        voice_engine_type=voice_engine_selected,
                        f5_ref_preset=f5_preset_choice,
                        f5_custom_ref_path=f5_custom_audio,
                        f5_custom_ref_text=f5_custom_text,
                        human_voice_audio_path=human_voice_file_path,
                        hook_title=hook_title_input,
                        export_mp4=opt_mp4,
                        export_capcut=opt_capcut,
                        progress_callback=on_pipe_progress
                    )

                    prog_bar.progress(100, text="🎉 ตัดต่อและเรนเดอร์เสร็จสมบูรณ์ 100%!")
                    status_box.update(label="🎉 ตัดต่อเสร็จสมบูรณ์ 100% พร้อมใช้งาน!", state="complete", expanded=False)
                    
                    st.balloons()
                    st.session_state.last_result = res

                except Exception as ex:
                    status_box.update(label=f"❌ เกิดข้อผิดพลาด: {ex}", state="error", expanded=True)
                    st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {ex}")

        # SHOW RENDERED RESULT IF AVAILABLE
        if "last_result" in st.session_state:
            res_obj = st.session_state.last_result
            st.markdown("---")
            st.markdown("#### 🎉 ผลงานวิดีโอที่ตัดต่อเสร็จแล้ว:")
            
            if res_obj.get("mp4_video") and os.path.exists(res_obj["mp4_video"]):
                st.video(res_obj["mp4_video"])
                
                with open(res_obj["mp4_video"], "rb") as vf:
                    st.download_button(
                        label="📥 ดาวน์โหลดไฟล์ .MP4 พร้อมโพสต์",
                        data=vf,
                        file_name=os.path.basename(res_obj["mp4_video"]),
                        mime="video/mp4",
                        use_container_width=True
                    )

            if res_obj.get("capcut_draft"):
                st.info(f"💻 ส่งเข้า CapCut PC Draft เรียบร้อยแล้วที่:\n`{res_obj['capcut_draft']}`\n\n*(สามารถเปิดโปรแกรม CapCut Desktop เพื่อเปิดดูและปรับแต่งต่อได้ทันที)*")

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# TAB 2: EXPORT GALLERY
# =========================================================
with tab_gallery:
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <div>
            <h3 style="margin: 0;">📦 คลังวิดีโอที่ตัดเสร็จแล้ว (Export Gallery)</h3>
            <p style="color: #94A3B8; margin: 4px 0 0 0; font-size: 0.9rem;">วิดีโอทั้งหมดถูกบันทึกใน <code>04_Exports/Ready_to_post</code></p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_open, _ = st.columns([0.3, 0.7])
    if c_open.button("📂 เปิดโฟลเดอร์ Exports ในเครื่อง"):
        open_folder_in_explorer(EXPORTS_DIR)

    all_exports = scan_exports()
    if all_exports:
        # Display in responsive 3-column grid
        cols_per_row = 3
        for i in range(0, len(all_exports), cols_per_row):
            row_files = all_exports[i:i + cols_per_row]
            grid_cols = st.columns(cols_per_row)
            for j, exp_file in enumerate(row_files):
                with grid_cols[j]:
                    st.markdown(f"""
                    <div class="video-card">
                        <div style="font-weight: 700; font-size: 0.95rem; color: #FFFFFF; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 6px;">
                            📹 {exp_file.name}
                        </div>
                        <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 10px;">
                            ขนาด: {exp_file.stat().st_size / (1024*1024):.1f} MB | {datetime.datetime.fromtimestamp(exp_file.stat().st_mtime).strftime('%d/%m/%Y %H:%M')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.video(str(exp_file))
                    
                    with open(exp_file, "rb") as f_down:
                        st.download_button(
                            label=f"📥 ดาวน์โหลด",
                            data=f_down,
                            file_name=exp_file.name,
                            mime="video/mp4",
                            key=f"gallery_dl_{i}_{j}",
                            use_container_width=True
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("ยังไม่มีวิดีโอในคลัง Exports — ลองสร้างคลิปแรกในแท็บ Studio Creator ได้เลยครับ!")

# =========================================================
# TAB 3: AI SCRIPT LAB & HOOKS
# =========================================================
with tab_script_lab:
    st.markdown("### 💡 คลังไอเดีย & สูตร Hook ไวรัลสไตล์ TikTok")
    st.markdown("สูตรประโยคเปิดคลิป 3 วินาทีแรกที่หยุดนิ้วคนดูได้ผลดีที่สุด:")

    hook_cards = [
        {"type": "🚫 เตือนห้ามซื้อ", "hook": "อย่าเพิ่งซื้อ {product_name} ถ้าคุณยังไม่รู้สิ่งนี้!", "desc": "สร้างความสงสัยและหยุดคนดูทันทีด้วยคำเตือน"},
        {"type": "😫 จี้ Pain Point", "hook": "ใครที่กำลังเจอปัญหา {pain_point} ดูคลิปนี้ด่วน!", "desc": "คัดกรองกลุ่มเป้าหมายที่มีปัญหาโดยตรง"},
        {"type": "👀 ความลับ / ของแปลก", "hook": "ทุกคนดูนี่! ทำไมคนใน TikTok สั่ง {product_name} ตัวนี้กันเยอะมาก?!", "desc": "ใช้พลัง Social Proof กระตุ้นความอยากรู้"},
        {"type": "⚡ เปรียบเทียบ ชัดเจน", "hook": "เลิกใช้แบบเดิมๆ ได้แล้ว! พอเปลี่ยนมาใช้ {product_name} ชีวิตดีขึ้นเยอะ", "desc": "กระตุ้นให้เกิดการเปรียบเทียบและการตัดสินใจ"},
        {"type": "🔥 โปรด่วนจำกัดเวลา", "hook": "ราคาหลุดหรือเปล่าไม่รู้ แต่ตอนนี้ {product_name} จัดโปร {price_deal} จิ้มด่วน!", "desc": "สร้างความเร่งด่วน (FOMO)"}
    ]

    for item in hook_cards:
        st.markdown(f"""
        <div class="pro-card" style="padding: 1rem 1.2rem; margin-bottom: 0.8rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="status-pill" style="font-size: 0.75rem;">{item['type']}</span>
                <span style="font-size: 0.8rem; color: #94A3B8;">{item['desc']}</span>
            </div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-top: 8px;">
                "{item['hook']}"
            </div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# TAB 4: SYSTEM & ASSETS
# =========================================================
with tab_assets:
    st.markdown("### ⚙️ จัดการระบบ โฟลเดอร์ และทรัพยากร (System & Assets)")
    
    a_col1, a_col2 = st.columns(2, gap="large")
    
    with a_col1:
        st.markdown("""
        <div class="pro-card">
            <h4 style="margin-top: 0;">📁 ไดเรกทอรีจัดเก็บข้อมูล</h4>
        """, unsafe_allow_html=True)
        
        st.write(f"• **Inbox (พักไฟล์ดิบ):** `{INBOX_DIR}`")
        st.write(f"• **Raw (ฟุตเทจจัดเก็บ):** `{RAW_DIR}`")
        st.write(f"• **Assets (เพลง/SFX/ฟอนต์):** `{ASSETS_DIR}`")
        st.write(f"• **Exports (วิดีโอพร้อมโพสต์):** `{EXPORTS_DIR}`")
        st.write(f"• **CapCut Drafts:** `{CAPCUT_DRAFT_DIR}`")
        
        if st.button("📂 เปิดโฟลเดอร์โปรเจกต์ทั้งหมด (Project Root)"):
            open_folder_in_explorer(BASE_DIR)
            
        st.markdown("</div>", unsafe_allow_html=True)

    with a_col2:
        st.markdown("""
        <div class="pro-card">
            <h4 style="margin-top: 0;">🔊 คลังเสียงเอฟเฟกต์ (SFX & Music)</h4>
        """, unsafe_allow_html=True)
        
        sfx_files = list(SFX_DIR.glob("*.wav"))
        for sf_file in sfx_files:
            s_c1, s_c2 = st.columns([0.4, 0.6])
            s_c1.markdown(f"**{sf_file.name}**")
            s_c2.audio(str(sf_file))

        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-top: 2rem; text-align: center; color: #64748B; font-size: 0.85rem;'>⚡ TikTok Auto-Cutter Pro Studio • Built for Creators & Affiliates • Powered by FFmpeg, Edge-TTS & CapCut Engine</div>", unsafe_allow_html=True)
