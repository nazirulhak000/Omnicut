# 🔥 รายงานฉบับสมบูรณ์: Deep REA CapCut 7.1 Wave 2 Extraction (7 Unexplored Modules) & Full End-to-End UI, API, and FFmpeg Render Wiring

**วันที่:** 2026-11-01  
**ผู้ดำเนินการ:** Antigravity (Gemini 4 Argon)  
**สถานะ:** ผ่านการทดสอบครบ 100% (Vitest 1,186/1,186 · Parity 212/212 · Wave 1+2 Pytest 23/23 · Vite Build 497ms · Browser MCP Verified)

---

## 1. บทสรุปผู้บริหาร (Executive Summary)

ปฏิบัติการ **Master Directive Wave 2** ได้ดำเนินการเจาะลึกด้วยสกิล `/reverse-engineer-anything` (REA) ลงใน 7 โมดูลสำคัญของ **CapCut Desktop v7.1.0.2890** (`C:\Users\nazir\AppData\Local\CapCut\Apps\7.1.0.2890\Resources\`) ที่ยังไม่ถูกสำรวจในรอบแรก พร้อมทั้งเชื่อมระบบจากทั้ง **Wave 1** และ **Wave 2** เข้าสู่ **หน้าจอ React UI จริง (`Inspector`, `Toolbar`, `EditorHeader`, `Timeline`, `SequencePlayer`) + FastAPI Endpoint + ท่อเรนเดอร์จริง (`video_editor.py`, `sfx_manager.py`, `audio_mix_stage.py`, `shot_matching_stage.py`, `tiktok_enhancer.py`)** ครบวงจร 100% โดยไม่มีฟังก์ชันลอย (Zero Orphan Functions)

---

## 2. PART 1: การเชื่อมระบบ Wave 1 เข้าสู่ UI จริงและท่อ Render ครบวงจร (End-to-End Wiring)

| ลำดับ | ระบบที่เชื่อมต่อ | ไฟล์ที่แก้ไข | รายละเอียดการเชื่อมโยงและปุ่ม UI จริง |
| :--- | :--- | :--- | :--- |
| **1.1** | **Multi-LOD Waveform บนไทม์ไลน์จริง** | [`audioPeaks.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/lib/audioPeaks.js)<br>[`Timeline.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/Timeline.jsx) | เชื่อม `getAudioPeaksForZoom(url, pxPerSec)` และ `resolveWaveformLodColumns(pxPerSec)` เข้ากับ `Timeline.jsx` วาดกราฟคลื่นเสียงปรับความละเอียด 3 ระดับ (LOD 1x=600, LOD 4x=2,400, LOD 16x=9,600 จุด) ตามการซูมไทม์ไลน์แบบ Real-time |
| **1.2** | **Track Linkage ในทุกคำสั่งตัดต่อ** | [`useEditorCommands.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/hooks/useEditorCommands.js)<br>[`EditorShell.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/EditorShell.jsx) | เชื่อม `shiftLinkedItems` และสถานะ `trackLinkageEnabled` เข้ากับคำสั่ง `trimHeadAtPlayhead` (`Q`), `trimTailAtPlayhead` (`W`), และ `deleteSelected` (`Delete`) เพื่อให้ซับไตเติล ข้อความเสริม สติกเกอร์ และเอฟเฟกต์ขยับตามแทร็กวิดีโออัตโนมัติ |
| **1.3** | **Cubic-Bézier Curve & 9:16 Smart Camera Presets** | [`inspectorModel.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/lib/inspectorModel.js)<br>[`ClipInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/ClipInspector.jsx)<br>[`Inspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/Inspector.jsx) | เพิ่มปุ่ม `"ซูมเข้า 9:16"`, `"ซูมออก 9:16"`, `"แพนซ้าย 9:16"`, `"แพนขวา 9:16"` (`base_crop = 0.8 -> 1.25x`) และตัวเลือก `combobox "โค้งความเร็วคีย์เฟรม (Bezier Easing)"` (`Montage`, `Hero In`, `Bullet Stop`, `Jump Cut`) ใน `ClipInspector.jsx` |
| **1.4** | **Live -14 LUFS Readout & Normalization** | [`audioBusLevels.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/lib/audioBusLevels.js)<br>[`ProjectInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/ProjectInspector.jsx)<br>[`audio_mix_stage.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/stages/audio_mix_stage.py) | แสดงค่าประมาณความดังสด (`~ -14.7 LUFS / เป้า -14.0 LUFS`) และปุ่ม `"ปรับเสียงมาตรฐาน -14 LUFS"` ใน `ProjectInspector.jsx` พร้อมเชื่อมเข้า `AudioMixStage` ในท่อเรนเดอร์ |
| **1.5** | **ปุ่มส่งออกดราฟต์ CapCut 7.1 (1-Click)** | [`api_editor.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/api_editor.py)<br>[`api.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/api.js)<br>[`EditorHeader.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/EditorHeader.jsx) | สร้าง Endpoint `POST /api/editor/projects/{project_name}/export-capcut-draft` เรียก `CapCutDraftBuilder` (`version: 360000`, `new_version: "144.0.0"`) และเพิ่มปุ่ม `"ส่งออกดราฟต์ CapCut"` บน `EditorHeader.jsx` |

---

## 3. PART 2: ผลการแกะรอยเชิงลึก 7 โมดูลใหม่ของ CapCut 7.1 (W2.1–W2.7) และการนำไปใช้งานจริง

### 🔬 W2.1: AI Scene Edit Detection & Algorithm Cache
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\SceneEditDetection\config.json`: โมเดล `af39b08db9b1053fd6c3bb3fb14eb5fa`, sliding window `7` เฟรม (`in_out`), threshold `0.35`, blit size `96x96`
  - `Resources\AlgorithmCache\face_detect_cache.json`: pre-allocated GPU texture pool `360x640`
- **การนำไปใช้งานจริง:**
  - เพิ่ม `CAPCUT_SCENE_DETECT_WINDOW = 7`, `CAPCUT_SCENE_DETECT_THRESHOLD = 0.35`, และ `detect_scene_cuts()` ใน [`scripts/motion_analyzer.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/motion_analyzer.py) เพื่อคัดกรองแสงแฟลช 1 เฟรมออกจากการตัดซีนจริง และเชื่อมเข้ากับ [`scripts/stages/shot_matching_stage.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/stages/shot_matching_stage.py)

### 🔬 W2.2: Intelligent 9:16 Reframe & Object Rect Magnetic Snap Guides
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\lvop_intelligent_crop` & `Resources\video_template_ratio.json`: สัดส่วนมาตรฐาน `9:16` (`0.5625`), `1:1`, `16:9`, `4:3`, `3:4`
  - `Resources\DefaultAdjustBundle\merge_all_adjust\DefaultAdjustBundle\objectRect\xshader\gles2_fshader.frag`: เชเดอร์ `smoothstep(0.0, border, ...)` สำหรับวาดเส้น Snap guide ขอบคมชัดและโปร่งแสงตามระยะห่าง
- **การนำไปใช้งานจริง:**
  - เพิ่ม `SNAP_X_GUIDES_9_16 = [0.5, 0.333, 0.667, 0.889]`, `SNAP_Y_GUIDES_9_16 = [0.5, 0.2, 0.72, 0.333, 0.667, 0.781]`, และ `smoothstep()` ใน [`overlayBoxGeometry.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/lib/overlayBoxGeometry.js) พร้อมแสดงป้าย `"เส้นดูด 9:16"` บน [`SequencePlayer.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/SequencePlayer.jsx)

### 🔬 W2.3: Multi-Layer Blend Modes (`MixMode` GLSL Shaders)
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\MixMode\*\xshader\fshader.frag`: สกัดสมการเชเดอร์ GLSL ของโหมด `Screen`, `Multiply`, `Overlay`, `SoftLight`, `Lighten`, `Darken` โดยเฉพาะสมการ `SoftLight` แท้ของ CapCut:
    $$\text{res} = (1 - 2s) b^2 + 2 s b \quad (\text{เมื่อ } s < 0.5)$$
- **การนำไปใช้งานจริง:**
  - เพิ่ม `BLEND_MODE_OPTIONS`, `resolveCanvasCompositeOp`, `capcutSoftLightChannel` ใน [`stickerAnimation.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/lib/stickerAnimation.js), ตัวเลือกโหมดผสมสีใน [`OverlayInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/OverlayInspector.jsx) และ [`StickerInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/StickerInspector.jsx), วาดด้วย `ctx.globalCompositeOperation` ใน [`SequencePlayer.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/SequencePlayer.jsx), และแมปเข้ากับ `BLEND_MODE_FFMPEG_MAP` / `capcut_soft_light_channel` ใน [`scripts/video_editor.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/video_editor.py)

### 🔬 W2.4: Primary & Log Color Wheels (`PrimaryWheel` & `LogWheel`)
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\PrimaryWheel\primary_wheel_v0\Wheel\xshader\fshader.frag`: สมการ Lift/Gamma/Gain ต่อแชนแนล:
    $$\text{lift\_x} = \frac{\text{lift}}{\text{lift} - 0.5}, \quad \text{gain\_x} = \frac{1}{\text{gain}}, \quad \text{res} = \exp\left(\gamma \cdot \ln\left(\frac{s - \text{lift\_x}}{\text{gain\_x} - \text{lift\_x}}\right)\right)$$
  - `Resources\LogWheel\log_wheel_v0\Wheel\xshader\fshader.frag`: จุดตัดโซนแสง `RugDown = 0.333`, `RugUP = 0.555` และ BT.709 Luma `0.2126 R + 0.7152 G + 0.0722 B`
- **การนำไปใช้งานจริง:**
  - เพิ่มแถบเลื่อน `"อุณหภูมิสี (Warm/Cool)"` (`-0.30..0.30`) และ `"แกมม่า (Gamma / LogWheel)"` (`0.50..2.00`) ใน [`ClipInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/ClipInspector.jsx), พรีวิวสดใน [`SequencePlayer.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/SequencePlayer.jsx), และเรนเดอร์ผ่าน `eq=gamma=...` + `colorbalance=rs=...:bs=...` ใน [`scripts/video_editor.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/video_editor.py)

### 🔬 W2.5: RNNoise & SAMI Vocal Clarity / De-Esser Chain
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\rnnoise\rnnoise_data_24k_b1.bin` & `Resources\audiosami`: โมเดลตัดเสียงรบกวนความถี่ต่ำและกรองเสียงพูดความถี่ 24kHz/48kHz
- **การนำไปใช้งานจริง:**
  - สร้าง `VOICE_CLARITY_CHAIN = "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=2.5:attack=15:release=120,deesser=i=0.4"` และ `voice_clarity_filter()` ใน [`scripts/sfx_manager.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/sfx_manager.py), เชื่อมเข้า [`scripts/stages/audio_mix_stage.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/stages/audio_mix_stage.py), และเพิ่มปุ่มสลับ `"เปิดเสียงใสตัดนอยส์"` ใน [`ProjectInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/ProjectInspector.jsx)

### 🔬 W2.6: Sticker Spring & Elastic Physics (`template_sticker`)
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\template_sticker\js\template\template.js`: สกัดฟังก์ชัน `Easing.Elastic.Out` และ `Easing.Back.Out` (`s = 1.70158`) พร้อมสมการ Damped Harmonic Oscillator ($\omega = 18.0$, $\zeta = 0.45$)
- **การนำไปใช้งานจริง:**
  - เพิ่ม `capcutSpringScale`, `capcutElasticOut`, `capcutBackOut` ทั้งใน [`stickerAnimation.js`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/lib/stickerAnimation.js) และ [`scripts/video_editor.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/video_editor.py) พร้อมตัวเลือกอนิเมชันสติกเกอร์ใน [`StickerInspector.jsx`](file:///d:/Programmer/All%20Project/Omnicut/frontend/src/components/editor/inspector/StickerInspector.jsx)

### 🔬 W2.7: GPU Driver Bug List & Hardware Encode Fallback (`gpu_driver_bug_list.json`)
- **หลักฐานจริง (Observed Evidence):**
  - `Resources\gpu_driver_bug_list.json`: บัญชีดำการ์ดจอที่มีบั๊กไดรเวอร์ D3D11/Hardware Video Decoder/Encoder ได้แก่ Intel (`0x8086`: `0x041e`, `0x0412`, `0x0416`, `0x0a26`, `0x5912`, `0x591b`) และ NVIDIA (`0x10de`: `0x0f00`, `0x1cb6`)
- **การนำไปใช้งานจริง:**
  - เพิ่ม `CAPCUT_GPU_DRIVER_BUG_LIST` และ `is_gpu_driver_blacklisted(vendor_id, device_id)` ใน [`scripts/tiktok_enhancer.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/tiktok_enhancer.py) และ [`scripts/video_editor.py`](file:///d:/Programmer/All%20Project/Omnicut/scripts/video_editor.py) เพื่อสลับไปใช้ `libx264` บน CPU โดยอัตโนมัติ

---

## 4. สรุปผลการตรวจสอบผ่าน Verification Gates ทั้ง 6 ด่าน

| ด่านตรวจสอบ | คำสั่ง / วิธีตรวจ | ผลลัพธ์ | สถานะ |
| :--- | :--- | :--- | :---: |
| **Gate 1: Frontend Unit Tests** | `npm --prefix frontend test` | **1,186 / 1,186 passed (0 fail)** | ✅ PASS |
| **Gate 2: Preview = Render Parity** | `.venv\Scripts\pytest.exe tests/test_preview_render_parity.py` | **212 / 212 passed (0 fail)** | ✅ PASS |
| **Gate 3: Wave 1 & Wave 2 Pytest** | `.venv\Scripts\pytest.exe tests/test_capcut_7_1_wave2_parity.py ...` | **23 / 23 passed (0 fail)** | ✅ PASS |
| **Gate 4: Production Vite Build** | `npm --prefix frontend run build` | **✓ built in 497ms (0 errors)** | ✅ PASS |
| **Gate 5: Live Browser MCP Verification** | เปิด `http://127.0.0.1:8000/?tab=editor` กดทดสอบปุ่มจริงผ่าน `browsermcp` | ยืนยันปุ่ม `"ส่งออกดราฟต์ CapCut"`, `"ซูมเข้า 9:16"`, `"ปรับเสียงมาตรฐาน -14 LUFS"`, `"เปิดเสียงใสตัดนอยส์"`, `"อุณหภูมิสี"`, `"แกมม่า"` ทำงานครบถ้วน | ✅ PASS |
| **Gate 6: Clean UI & Zero Test Pollution** | ตรวจสอบฟอนต์ `Mali-Bold` 88px, ปุ่มภาษาไทยไร้ไอคอนซ้ำซ้อน, และ `.tmp/` | สะอาด 100% ตามกฎเหล็กข้อ 3.3, 3.8, 3.10, 3.11 | ✅ PASS |
