# 🎯 กฎ Preview = Render (Canvas/ffmpeg Parity Standard)

กฎบังคับสำหรับ**ทุกฟีเจอร์ในหน้า Editor ที่มีผลต่อภาพในวิดีโอที่เรนเดอร์ออกมา**
(ข้อความ, ขนาด, สี, ตำแหน่ง, motion, เอฟเฟกต์, รูปทรงตกแต่ง, เงา, ซับไตเติล, สติกเกอร์)

งานที่แตะฟอนต์ ข้อความ ซับ Hook, font metrics, style/default, manifest หรือ dependency ที่มีผลต่อภาพ
ต้องอ่านและผ่าน [.agents/rules/font_text_visual_contract.md](file:///d:/Winona/Programmer/Capcut/.agents/rules/font_text_visual_contract.md) เพิ่มด้วย

---

## 1. ทำไมต้องมีกฎนี้

ระบบมี **2 engine ที่วาดภาพเดียวกันคนละทาง**:

| | Preview | Render |
|---|---|---|
| ไฟล์ | `frontend/src/components/SequencePlayer.jsx` | `scripts/subtitle_engine.py` → ASS → libass |
| กลไก | Canvas 2D API (JS) | ASS override tags (ffmpeg + libass) |

**เขียนข้างเดียว = พรีวิวโกหก** ผู้ใช้ตัดสินใจจากพรีวิว แล้วได้ไฟล์จริงคนละแบบ = เสียเวลาเรนเดอร์ใหม่ทั้งรอบ
เคสจริงที่เคยหลุด: ฟอนต์พรีวิวใหญ่กว่าจริง 31%, caption ใหญ่กว่าจริง 39%, badge ทึบผิด 2 เท่า,
กลิตช์หมุน 90° ในไฟล์จริงแต่พรีวิวปกติ, แสงกวาดเห็นข้อความซ้อน 2 ชุด

---

## 2. กฎเหล็ก (บังคับทุกครั้งที่แตะฟีเจอร์ที่ออกภาพ)

### 2.1 แก้ข้างเดียวไม่ได้ — ต้องแก้คู่เสมอ
เพิ่ม/แก้อะไรก็ตามที่เห็นในวิดีโอ **ต้องแก้ทั้ง `subtitle_engine.py` และ `SequencePlayer.jsx` ในคอมมิตเดียวกัน**
ห้ามทิ้งไว้ว่า "เดี๋ยวค่อยทำ preview ตาม"

### 2.2 ค่าคงที่ทุกตัวต้องเทียบได้เป็นตัวเลข
ห้ามใช้ "ตาดูแล้วใกล้เคียง" ทุกค่าที่กำหนดภาพ (ratio, ระยะเวลา ms, factor, องศา, ความทึบ)
ต้องเขียนให้ **ดึงมาเทียบกันได้** และเพิ่ม assertion ใน `tests/test_preview_render_parity.py`

### 2.0 ⚠️⚠️ ขนาดฟอนต์: ตัวเลขเดียวกัน = คนละขนาด (ข้อที่พลาดซ้ำมากที่สุด)
**libass ตีความ Fontsize = ความสูงบรรทัดของฟอนต์ (ascender + descender)**
ส่วน **canvas/CSS ตีความ = ขนาด em box** ฟอนต์ไทยมี line box สูงกว่า em มาก
(IBM Plex Sans Thai: 1650 units ต่อ em 1000) → ใส่เลขเดียวกันสองฝั่ง
**พรีวิวจะใหญ่กว่า render ~1.65 เท่า** ต่อให้ ratio ตรงกันเป๊ะทุกตัว

วัดจริง: libass Fontsize 100 = PIL/เบราว์เซอร์ ~60px (ฟอนต์เดียวกัน)

**ต้องแปลงเสมอ** ด้วยตัวคูณต่อฟอนต์:
```
factor = unitsPerEm / (usWinAscent + usWinDescent)
```
- Backend: `ass_glyph_scale()` ใน `subtitle_engine.py` — **ทุกอย่างที่วัดความกว้างไปวางของ**
  (เส้น accent, badge, clip ของ typewriter, แถบ lightsweep) ต้องวัดที่ `fontsize * factor`
- Canvas: `assGlyphScale()` ใน `SequencePlayer.jsx` อ่านจาก `TextMetrics.fontBoundingBoxAscent/Descent`
  → ทุก `ctx.font` ต้องคูณ `glyphK` ไม่มีข้อยกเว้น

**ระยะบรรทัดไม่ต้องคูณ** — libass เดินบรรทัด = Fontsize ดิบ (ข้อ 2.7)

### 2.0.1 ⚠️ เวลาเทสด้วย ffmpeg ต้องส่ง `fontsdir` เสมอ
ไม่ส่ง = libass fallback ไปฟอนต์ระบบ **ตัวเลขที่วัดได้เป็นโมฆะทั้งหมด**
(เคยทำให้สรุปผิดมาแล้วสองรอบ) ตัวอย่าง:
```
-vf "subtitles=x.ass:fontsdir=02_Assets/Fonts"
```

### 2.0.2 ⚠️ ห้ามรับรอง font metrics ด้วย Python คนละ environment

Backend จริงรันด้วย `.venv\Scripts\python.exe` ดังนั้น probe/test ต้องใช้ interpreter เดียวกัน
เคยเกิด regression จริง: system Python มี `fontTools` และคำนวณ IBM Plex ได้ `0.6060606`
จึงสร้าง ASS `Fontsize=82` แต่ `.venv` ไม่มี package แล้ว fallback เงียบเป็น `1.0`
ทำให้ live render ยังออก `Fontsize=50`

- metric ที่กำหนดภาพต้องอ่านจากไฟล์ฟอนต์จริงได้โดยไม่พึ่ง optional dependency แบบเงียบ
- dependency ที่ใช้ resolve font family ต้องประกาศใน `requirements.txt`
- ถ้า metric/physical face resolve ไม่ได้ ต้อง fail หรือแจ้งผู้ใช้ ห้าม render ต่อด้วยค่า `1.0`
- หลังแก้ backend visual contract ต้อง restart server แล้ว render artifact จริงใหม่ก่อนปิดงาน

### 2.3 หน่วยและระบบพิกัดต้องแปลง ไม่ใช่ก็อป
Canvas = **540×960**, Render = **1080×1920** (ต่างกัน 2 เท่าพอดี)
- ขนาดฟอนต์/ระยะ: เขียนเป็น **สัดส่วนของความกว้างเฟรม** ให้เหมือนกันทั้งสองฝั่ง
  (เช่น `hook_fs = video_width * 0.065` ↔ `CANVAS_W * 0.065`) ห้าม hardcode พิกเซลคนละชุด
- ตำแหน่ง: เทียบเป็น **% ของความสูงเฟรม** (เช่น MarginV 260/1920 ↔ y 130/960)

### 2.4 ⚠️ ALPHA: ASS นับ "ความโปร่ง" / Canvas นับ "ความทึบ" (กลับด้านกัน)
```
ASS  \alpha&H00& = ทึบสุด    \alpha&HFF& = ใสสุด
Canvas globalAlpha 1 = ทึบสุด        0 = ใสสุด
```
**ต้องแปลงเสมอ**: `opacity = 1 - (0xNN / 255)`
เขียนในโค้ดให้เห็นการแปลงชัดๆ (`1 - 0xB0 / 255`) ห้ามใส่เลขทศนิยมสำเร็จรูป เพราะกลับด้านแล้วดูไม่ออก

### 2.5 ⚠️ องศาหมุน: ห้ามใช้เลข wrap (357 แทน -3)
`\t` interpolate เชิงเส้นเข้าหาเป้าหมาย → `0 → 357` จะกวาดอ้อมผ่าน 180° ตัวอักษรตะแคง/กลับหัวกลางทาง
**ใช้เลขติดลบเสมอ**: `-3` ไม่ใช่ `357`

### 2.6 ⚠️ เส้นขอบ (Outline): ASS ขยายออกนอกอย่างเดียว / Canvas stroke อยู่กึ่งกลาง
`ctx.strokeText` วาดคร่อมเส้นขอบ ครึ่งเดียวที่โผล่ออกนอกตัวอักษร
→ `lineWidth = 2 × ความหนาที่ ASS ใช้` (หลังแปลงหน่วย canvas แล้ว)

### 2.7 ⚠️ ระยะบรรทัด: libass เดินบรรทัดละ 1.0 × font size ของ Style
วัดจริงแล้ว: style 72px เดินไป 72px พอดี **แม้บรรทัดนั้นจะย่อด้วย `\fscx68`**
→ Canvas ต้องใช้ `lineHeight = fontSize` ห้ามใส่ 1.15/1.25 ตามใจ

### 2.8 ⚠️ จุดยึดบล็อคข้อความ ต้องตรงกับ ASS Alignment
- Alignment 2 (bottom) → ยึด**ขอบล่าง**ของบล็อคที่ `frameH - MarginV`
- Alignment 8 (top) → ยึด**ขอบบน**
- Alignment 5 (middle) → ยึดกึ่งกลาง

ห้าม "จับกึ่งกลางทุกกรณี" เพราะบล็อคหลายบรรทัดจะเลื่อนไปครึ่งบล็อค

### 2.9 ⚠️ `\p` drawing ต้องใช้พิกัดบวกล้วน + `\an7`
libass วางรูปที่ใช้พิกัดติดลบผิดตำแหน่ง (ขอบขวาไปอยู่ที่จุด `\pos` แทนที่จะกึ่งกลาง)
→ วาดจาก `m 0 0 l w 0 l w h l 0 h` แล้ววาง `\pos` ที่ขอบซ้ายของรูป

### 2.10 รูปทรงตกแต่งต้องกินพื้นที่ layout
บรรทัดชิดกันพอดี (line factor 1.0) ไม่มีที่ว่างเหลือ → ถ้าเพิ่มเส้น/แถบ **ต้องจองระยะดันบรรทัดถัดไปลง**
ทั้งสองฝั่งด้วยตัวเลขเดียวกัน ไม่งั้นทับข้อความ

### 2.11 ลำดับชั้น (z-order) ต้องตรงกัน
ASS ใช้ `Layer` เลขน้อยวาดก่อน (อยู่หลัง) / Canvas วาดตามลำดับบรรทัดโค้ด
→ อะไรที่อยู่ **หลัง** ข้อความใน render ต้องวาด **ก่อน** ข้อความใน canvas
(รูปทรงตกแต่งอยู่หลังตัวอักษรเสมอ ห้ามบังคำ)

### 2.12 Layer ที่ซ้อนข้อความเดิม ต้องคัดลอก transform ให้ครบ
เอฟเฟกต์แบบซ้อนข้อความ (เช่น Light Sweep) ต้องใส่ `\fscx/\fscy` เท่าบรรทัดต้นฉบับ
ไม่งั้นเห็นเป็นข้อความผีคนละขนาดซ้อนกัน

### 2.13 อีโมจิ: render เป็นขาว / browser เป็นบิตแมปสี
เบราว์เซอร์วาดอีโมจิเป็นภาพสี ไม่สน `fillStyle`; libass วาดเป็น glyph สีข้อความ
→ Preview ต้องวาดอีโมจิผ่าน filter ลดสี ให้ออกมาขาวเหมือน render

---

## 3. ขั้นตอนบังคับก่อนบอกว่า "เสร็จ"

1. **แก้ทั้งสองฝั่ง** ในงานเดียวกัน
2. **เพิ่ม assertion** ใน `tests/test_preview_render_parity.py` สำหรับทุกค่าคงที่ที่เพิ่ม/แก้
3. **รันจริง**: `python -m pytest tests/test_preview_render_parity.py -q` ต้องเขียว
4. **เรนเดอร์จริงด้วย ffmpeg** แล้วดูภาพ — ห้ามสรุปจากโค้ดอย่างเดียว
   ```bash
   ffmpeg -y -f lavfi -i "color=c=0x222222:s=1080x1920:d=3.2" \
     -vf "subtitles=<ไฟล์.ass>" -ss <วินาที> -frames:v 1 -update 1 out.png -loglevel error
   ```
   Motion ต้องดึงหลายเฟรมตลอดช่วง (เข้า / ค้าง / ออก) ไม่ใช่เฟรมเดียว
5. **วัดด้วยพิกเซลเมื่อเป็นเรื่องตำแหน่ง/ขนาด** — สแกนแถบหมึกด้วย PIL แล้วเทียบตัวเลข
   ห้ามเดาค่า factor เอาเอง (ค่า `LINE_HEIGHT_FACTOR = 1.0` ได้มาจากการวัด ไม่ใช่การเดา)
6. **`npx vite build`** ต้องผ่าน

---

## 4. ตารางค่าที่ผูกกันอยู่แล้ว (แก้ตัวใดตัวหนึ่ง = ต้องแก้คู่)

| ค่า | `subtitle_engine.py` | `SequencePlayer.jsx` |
|---|---|---|
| ขนาดฟอนต์ Hook | `hook_fs = video_width * 0.065` | `baseFontSize = CANVAS_W * 0.065` |
| ขนาดฟอนต์ Caption | `base_fs = video_width * 0.0463` | `baseFs = CANVAS_W * 0.0463` |
| ระยะบรรทัด | `LINE_HEIGHT_FACTOR = 1.0` | `lineGap = 1.0`, `thaiLineH = fontSize` |
| จุดเริ่มบล็อค Hook | `cursor_y = 260` (/1920) | `y = 130` (/960) |
| สเกลแต่ละชั้น | `hook_tier_specs` 130/100/58 | `tierSpecs` sizePct |
| Stagger | `STAGGER_STEP_MS = 150` | `HOOK_STAGGER_STEP = 0.15` |
| ช่วง exit | `exit_end_ms - 150` | `hookDuration - 0.15` |
| In/Loop/Out presets | `HOOK_*_BUILDERS` | `HOOK_*_TRANSFORMS` |
| Outline Hook | Style `Outline=6.0` | `HOOK_OUTLINE_PX = 6` |
| Outline Caption | `front_outline = max(1.8, fs*0.040)` | `captionOutlineWidth()` |
| Accent/Badge | `_hook_accent_events()` | บล็อค accent ใน `drawHookHeader` |

| ค่าเสียง | ฝั่ง render | `SequencePlayer.jsx` |
|---|---|---|
| ระดับ voice/BGM/SFX | `config.py` BGM/VOICE/SFX_VOLUME | `AUDIO_MIX.*_GAIN` |
| pre-roll SFX | `pre_roll = 0.12` (sfx_manager) | `AUDIO_MIX.SFX_PRE_ROLL` |
| เวลาต่ำสุดของ SFX | `max(0.02, ...)` | `AUDIO_MIX.SFX_MIN_TIME` |
| fade ท้าย BGM | `afade=t=out:d=0.35` | `AUDIO_MIX.BGM_FADE_OUT` |
| tempo BGM | `BASELINE_CHARS_PER_SEC = 10.0` + clip 0.92–1.08 | `bgmTempoRatio()` |
| ducking | `sidechaincompress attack=20 release=300` | `AUDIO_MIX.BGM_DUCK_*` |
| alias SFX เก่า | `LEGACY_SFX_ALIASES` (asset_registry) | `LEGACY_SFX_ALIASES` (EditorShell) |
| BGM default | `resolve_bgm_path()` | `DEFAULT_BGM_FILE` (EditorShell) |

| ภาพ/สี | ฝั่ง render | ฝั่งพรีวิว |
|---|---|---|
| geometry ของ transition | `xfade=transition=...` | `clipIncomingRegion` / `slideOffsets` / `circleWeightAt` |
| สีคั่นของ fade | `fadeblack` / `fadewhite` | `FADE_BRIDGE_OUT` / `FADE_BRIDGE_IN` |
| LUT | `lut3d` + `resolve_lut_path()` | `lut3d.js` (`parseCube`/shader) + `grade` prop |
| ความเข้ม LUT | `blend=all_opacity=strength` | `mix(src, graded, uStrength)` |
| ลำดับเกรด | ก่อน sticker + ก่อน burn ซับ | `applyGrade` ก่อน `drawHookHeader` |
| เสียงในคลิป | `volume=` + `adelay=clip_starts[i]` | bus `clip` + `wireClipAudio` |

---

## 5. ข้อยกเว้นที่ยอมรับได้ (ต้องแจ้งผู้ใช้ตรงๆ ห้ามเงียบ)

- **Soft shadow**: render ใช้ dialogue เบลอแยกชั้น / preview ใช้ `ctx.shadowBlur` — คนละกลไก
  ทำให้เท่ากันเป๊ะไม่ได้โดยไม่ทำให้ preview กระตุก **ตำแหน่ง/ขนาด/สีต้องตรง** ต่างได้แค่ความฟุ้ง
- **ฟอนต์ fallback**: ถ้าเบราว์เซอร์ไม่มีฟอนต์เดียวกับที่ libass ใช้ ความกว้างจะต่างเล็กน้อย

พบข้อยกเว้นใหม่ = **เขียนเพิ่มในหัวข้อนี้ แล้วบอกผู้ใช้** ห้ามปล่อยผ่านเงียบๆ

---

## 6. เสียง: พรีวิวเล่น stem แยก / render มิกซ์ด้วย ffmpeg

กด 1 คลิกจะ **ไม่มิกซ์เสียง** (`pipeline.py` ข้ามเมื่อ `export_mp4=False`) พรีวิวเลยเล่น
**stem แยกกัน** ผ่าน WebAudio: voice บน `<audio>` (เป็นนาฬิกาหลัก) · BGM บน `<audio loop>` ·
SFX เป็น `AudioBufferSourceNode` ต่อจุด — เปลี่ยน BGM หรือใส่ SFX แล้วได้ยินทันที
ตอนกดเรนเดอร์จริง `SFXManager.mix_audio_track()` ค่อยรวมเป็นไฟล์เดียว

### 6.1 ⚠️ ระดับเสียงมีแหล่งเดียวคือ `scripts/config.py`

`BGM_VOLUME` / `VOICE_VOLUME` / `SFX_VOLUME` → `sfx_manager.py` ใช้เป็น default ของพารามิเตอร์
และ `AUDIO_MIX` ใน `SequencePlayer.jsx` ต้องมีค่าเท่ากัน (เทสยึดไว้แล้ว)
เคยพลาด: `config.py` เขียน 0.15/0.6 แต่ mix รัน 0.12/0.28 และ `AGENTS.md` เขียนตามเลขที่ไม่มีใครใช้

### 6.2 ⚠️ เวลา SFX ต้องคิดจาก **ชื่อไฟล์ที่ resolve แล้ว** ไม่ใช่ tag ใน cue

render เช็ค `whoosh/swish/swoosh/transition` จาก `sfx_file.name` แล้วยิงก่อนรอยต่อ 0.12s
cue ที่ tag ว่า `boom` resolve เป็น `sfx_vine_boom.wav` — เช็คจาก tag จะได้ผลต่าง
พรีวิวต้องได้ชื่อไฟล์ส่งมาด้วย (`name: entry.name`) และ **ปัดลงเป็นมิลลิวินาทีเต็ม**
เหมือน `adelay` ที่รับแต่ int (`int(secs * 1000)`)

### 6.3 ⚠️ id ของ asset ไม่ใช่ชื่อไฟล์

`AssetPanel` ส่ง `bgmName` เป็น registry id (`bgm_brass_funk`) แต่ `resolve_bgm_path()`
เริ่มจากชื่อไฟล์ → เคยตกไปไฟล์แรกในโฟลเดอร์ทุกครั้ง **ผู้ใช้เลือกเพลงหนึ่ง แต่ render อีกเพลง**
ทั้งสองฝั่งต้อง resolve id ได้ และ **fallback ต้องเหมือนกัน** (ไฟล์ default → ไฟล์แรก)
SFX ก็มี alias เก่า (`LEGACY_SFX_ALIASES`) ต้องมีทั้งสองฝั่ง

### 6.4 ⚠️ BGM ต้อง loop และเร่ง/หน่วงตาม `atempo`

render ใช้ `-stream_loop -1` + `atempo` จาก chars/sec ของสคริปต์ (คลิป ±8%)
`atempo` ทำงาน **ก่อน** `atrim` → วินาทีที่ `t` บนไทม์ไลน์ = `t * rate` ในไฟล์ต้นทาง

### ข้อยกเว้นด้านเสียง (แจ้งผู้ใช้ ห้ามเงียบ)

- **`atempo` vs `playbackRate`**: `atempo` รักษา pitch / `playbackRate` เปลี่ยน pitch ตามความเร็ว
  ที่ ±8% ฟังแทบไม่ออก แต่ไม่ใช่กลไกเดียวกัน
- **ducking**: render ใช้ `sidechaincompress` ซึ่ง WebAudio ไม่มี พรีวิวใช้ gain envelope คงที่
  ตามช่วง cue (ลด 13.7 dB ตามที่วัดไว้ใน `sfx_manager.py`, attack/release เท่าฟิลเตอร์)
  **วัดของจริงแล้ว**: การลดจริงแกว่าง 7.7–20.2 dB ตามระดับเสียงพากย์ขณะนั้น (มัธยฐาน ~14.9 dB
  บนงานจริง) — ค่าคงที่เดียวจึงไม่ตรงเป๊ะได้ ใช้บอกทิศทางว่า "เพลงจะหลบเสียงพูด" เท่านั้น
- **`loudnorm I=-14 TP=-1.0 LRA=8`**: two-pass ทำในเบราว์เซอร์ไม่ได้ →
  **ระดับเสียงรวมของพรีวิวจะไม่เท่าไฟล์จริง** สัดส่วนระหว่าง stem ตรง แต่ค่าสัมบูรณ์ไม่ตรง
- **`apad=pad_dur=1.0`** ต่อท้าย voice ในไฟล์มิกซ์: พรีวิวไม่ต้องทำ (ไม่มีเสียงให้ pad)

---

## 7. Transition: canvas ต้องทำตาม geometry จริงของ `xfade`

เคยพรีวิวเป็น crossfade ทุกแบบ → wipe/slide/circle ดูเหมือนกันหมดจนกว่าจะเรนเดอร์

**วิธีวัด (ทำซ้ำได้)**: สร้าง input 2 ตัวที่ **พกพิกัดตัวเอง** — A เก็บ x ไว้ในช่อง R,
B เก็บ y ไว้ในช่อง B แล้วยิง `xfade` → พิกเซลผลลัพธ์ทุกจุดบอกได้ว่า **มาจาก input ไหน
และมาจากตำแหน่งไหน** จึงแยก wipe (mask ไม่ขยับภาพ) ออกจาก slide (ขยับภาพ) ได้แน่นอน
สำหรับ fade/circle ใช้ input สีทึบ (แดง/น้ำเงิน) แล้วอ่านน้ำหนักผสมจากค่าช่องสี

### 7.1 ⚠️ progress ของเฟรมที่ดึงมา ไม่เท่ากับ progress ที่สั่ง

ffmpeg เลือกเฟรมเอง — ดึงที่ `-ss offset+0.25` ได้ progress จริง 0.263
**ต้อง calibrate จาก `fade`** (ซึ่ง linear เป๊ะ: น้ำหนัก B = progress) ก่อนเทียบตัวอื่น
ไม่ทำ = error จากการ sample จะดูเหมือน error ของสูตร (วัดได้ 2.5% กลายเป็น 0.83%)

### 7.2 สูตรที่วัดได้ (เฟรมทดสอบ 120×200 ที่ progress 0.5)

| transition | ผลที่วัด | สูตรในพรีวิว |
|---|---|---|
| `wipeleft` | B ครอง x ≥ 61 ไม่ขยับภาพ | `rect((1-p)*W, 0, W, H)` |
| `wiperight` | B ครอง x ≤ 60 | `rect(0, 0, p*W, H)` |
| `wipeup` | B ครอง y ≥ 101 | `rect(0, (1-p)*H, W, H)` |
| `wipedown` | B ครอง y ≤ 100 | `rect(0, 0, W, p*H)` |
| `slideleft` | A เลื่อน −60px (−p·W), B เข้าจากขวา | offset A `−p·W` / B `+(1−p)·W` |
| `slideright` | A เลื่อน +60px | offset A `+p·W` / B `−(1−p)·W` |
| `slideup` | B เลื่อน +100px (+(1−p)·H) | offset A `−p·H` / B `+(1−p)·H` |
| `slidedown` | B เลื่อน −100px | offset A `+p·H` / B `−(1−p)·H` |
| `circleopen` | น้ำหนัก B ลดตามรัศมี ตัด 0.5 ที่ r/z = 0.495 | `smoothstep((1−r/z) + 3(p−0.5))` |
| `circleclose` | กลับด้าน ตัด 0.5 ที่ r/z = 0.505 | `smoothstep(r/z + 3(p−0.5))` |
| `dissolve` | สัดส่วน = progress, per-pixel, ไม่ย้อนกลับ | threshold noise คงที่ `noise >= 1−p` |
| `fade` | crossfade เชิงเส้น | alpha = p |
| `fadeblack`/`fadewhite` | **ไม่ใช่ crossfade** — A ดำสนิทที่ p=0.167, B เริ่มโผล่ ~0.267 | 2 ช่วง + สีคั่น |

**ความแม่นที่วัดได้**: wipe ≤0.83% พิกเซลผิดฝั่ง · slide ≤1.8px · circle ≤0.017 น้ำหนัก ·
dissolve สัดส่วนต่าง ≤0.32% · fade ≤0.8%

### 7.3 ⚠️ alpha ของ draw plan คือ alpha ตามลำดับทับ ไม่ใช่สัดส่วนของแต่ละชั้น

ชั้นล่างต้องทึบ (alpha 1) แล้วชั้นบนค่อยผสม สำหรับ `fadeblack` ที่มี 3 ชั้น
(A + สีคั่น + B) ต้องแปลงเป็น alpha ตามลำดับ: สีคั่นทับ A ด้วย `bridge/(1−wB)`
แล้ว B ทับด้วย `wB` — ใส่ค่าดิบตรงๆ จะได้ภาพจางกว่าที่ควร

### 7.4 ไม่ต้องยิง clip+draw หลายรอบเพื่อทำ ramp ต่อพิกเซล

circle ใช้ **radial gradient + `destination-in`** บน canvas สำรอง (วาดเฟรม 1 ครั้ง)
ไม่ใช่ 24 วง clip (จะกิน 12M พิกเซล/เฟรม) · dissolve ใช้ mask canvas ที่ threshold
noise ทั้งภาพด้วย `Uint32Array` เขียนครั้งเดียวต่อพิกเซล

### ข้อยกเว้นด้าน transition

- **`dissolve` pattern**: PRNG ของ ffmpeg ไม่ใช่ sin-hash แบบ GLSL (ทดสอบแล้วตรงกัน 59%
  = เดาสุ่ม) → พรีวิวใช้ noise ของตัวเอง **ลักษณะ/สัดส่วน/ทิศทางตรง แต่พิกเซลไม่ตรง**
- **`fadeblack`/`fadewhite` easing**: รูปโค้งไม่ใช่ smoothstep แท้ ผิดสูงสุด **0.067 น้ำหนัก**
  (≈17/255) ช่วงกลางที่เป็นสีคั่นล้วนตรงอยู่แล้ว

---

## 8. LUT (ฟิลเตอร์สี): ต้องเห็นในพรีวิว

### 8.1 ⚠️ id ของ asset ไม่ใช่ชื่อไฟล์ (ซ้ำรอย BGM)

`AssetPanel` ส่ง `lutName` เป็น registry id (`lut_warm_cozy_lifestyle`) แต่ pipeline ทำ
`LUTS_DIR / lut_name` ซึ่งไม่มีไฟล์นั้น → `lut_path` ไม่ผ่าน `.exists()` →
**ข้ามการเกรดสีเงียบๆ ทุกครั้ง ฟิลเตอร์ที่เลือกไม่เคยมีผลเลย**
แก้ที่ `AssetRegistry.resolve_lut_path()` รับทั้ง id และชื่อไฟล์ ทั้งสองฝั่งใช้ตัวเดียวกัน
**บทเรียน**: asset ทุกชนิดที่ UI เลือกด้วย id ต้องมี resolver ที่รับ id — เจอแล้ว 2 ชนิด (BGM, LUT)

### 8.2 ⚠️ ต้องเกรด **จุดเดียวกันในลำดับ filter**

render: `lut3d` → sticker overlay → subtitle burn
พรีวิว: วาดชั้นวิดีโอ → **เกรด** → hook → caption → sticker → overlay
เกรดหลังจากนั้นจะทำให้ **สีป้ายแบรนด์และสีซับเปลี่ยนไปด้วย** ซึ่ง render ไม่ทำ

### 8.3 ⚠️ ครึ่งความเข้มต้องผสมแบบเดียวกัน

`blend=all_mode=normal:all_opacity=strength` → `out = strength·graded + (1−strength)·original`
= `mix(src, graded, strength)` ใน shader

### 8.4 ⚠️ 3D texture ต้อง inset ครึ่ง texel

ป้อน 0..1 ตรงๆ เข้า `sampler3D` จะไปโดนเขต clamp ทำให้ **ปลายสองข้างของเกรดแบน**
ต้อง `rgb * (n-1)/n + 1/(2n)` — ตรวจแล้วตรง ffmpeg **ภายใน 1/255** ทั้ง 4 LUT ที่ติดตั้ง

**ข้อยกเว้น**: ถ้าเบราว์เซอร์ไม่มี WebGL2 → พรีวิวไม่เกรด (ไม่ใช่จอดำ) และต้องบอกผู้ใช้

---

## 9. เสียงในตัวคลิป (per-clip volume)

### 9.1 ⚠️ เสียงต่อคลิปต้อง `adelay` ไปตำแหน่งจริง ไม่ใช่ `concat`

เดิม `concat` เสียงทุกคลิปต่อกันจาก 0 แต่ค่า default ของ `volume` คือ 0 →
เคสปกติที่สุด (เพิ่มเสียงคลิปกลางคลิปเดียว) ทำให้ **เสียงคลิปนั้นเล่นที่ต้นวิดีโอ**
วัดจริง: คลิปกลางช่วง 2.00–4.00s เสียงออกที่ **0.00–1.95s** (ผิด 2 วินาที) แก้แล้วออกที่ 2.00s เป๊ะ
`clip_starts` ต้องคิดจาก **เลขชุดเดียวกับ offset ของ xfade** ไม่งั้นเสียงกับภาพเหลื่อมทุกรอยต่อ

### 9.2 ⚠️ element วิดีโอในพรีวิวถูก mute ไว้

มันมีไว้ decode เฟรม → คลิปที่ตั้ง volume > 0 จึง **เงียบในพรีวิวแต่ดังในไฟล์จริง**
สไลเดอร์ขยับเลขที่ไม่มีใครได้ยิน ต้อง `muted={!(volume > 0)}` แล้วต่อเข้า bus เสียงคลิป

**ข้อยกเว้น**: พรีวิวปรับ `playbackRate` ±6% เพื่อแก้ drift ของภาพ → เสียงในคลิปเพี้ยน pitch
เล็กน้อยระหว่างชดเชย ต่างจาก `atempo` ของ render ที่รักษา pitch

---

## 10. Mute/Solo ต่อแทร็ก = Preview และ Render ต้องได้ยินชุดเดียวกัน

`trackMix` เก็บสถานะ Mute/Solo ที่ผู้ใช้ตั้งไว้ และ `effectiveAudioMutes` คำนวณแทร็กที่เงียบจริง เมื่อมี Solo ให้ปิดเสียงทุกแทร็กที่ไม่ได้ Solo ทั้งใน Preview และ Render
ต้องส่งผลลัพธ์นี้ใน `audio_mutes` เพื่อมิกซ์ Voice/BGM/SFX ใหม่ และปิดเสียงต้นฉบับของคลิปในขั้น Video Assembly โดยไม่แก้ค่าระดับเสียงที่บันทึกไว้บนคลิป
การเปลี่ยน Mute/Solo ต้องทำให้รอบ Export มิกซ์เสียงใหม่ ห้ามนำไฟล์มิกซ์เก่ากลับมาใช้จนเสียง Preview กับ Render ต่างกัน
