# 🎬 แผนแม่บท: ยกระดับระบบตัดพื้นหลังสู่ Single Compressed Alpha Video (ตามแนวทาง CapCut)
## (Cutout Compressed Video Pipeline & Storage Reclamation Master Plan)

> **เอกสารอ้างอิง:** `_Docs/Plans/CUTOUT_COMPRESSED_VIDEO_PIPELINE_PLAN.md`  
> **สถานะ:** แผนงานพร้อมปฏิบัติการ (Approved Design)  
> **ผู้จัดทำ:** Antigravity (Gemini 3.8 Flash)  
> **เป้าหมายหลัก:** ลดการใช้พื้นที่แคชของระบบ Cutout จาก **1.3 GB เหลือ ~25 MB ต่อคลิป (ประหยัด 98%)** ป้องกันฮาร์ดดิสก์เต็มเมื่อผลิตคลิปจำนวนมาก (100 คลิปกินพื้นที่ไม่เกิน 2.5 GB) พร้อมเพิ่มความเร็วในการเรนเดอร์และพรีวิว

---

## 📌 1. บทนำและปัญหาที่ต้องแก้ไข (Problem Statement)

### 1.1 สภาพปัญหาปัจจุบัน (The 130 GB Problem)
ปัจจุบันระบบตัดพื้นหลังสินค้า (Background Isolation / Rembg Cutout) ใช้วิธีการแบบ **Loose PNG Frame Sequence**:
1. สกัดเฟรมต้นฉบับจากวิดีโอออกมาเป็นไฟล์รูปภาพ PNG แยกแต่ละเฟรม ลงใน `03_Projects/.cache/background-isolation-sequences/` (~950 MB ต่อคลิป 28 วินาที / 860 เฟรม)
2. ส่งเฟรมรูปภาพเข้าโมเดล Rembg แล้วบันทึกผลลัพธ์เป็นรูปภาพ PNG RGBA 1080x1920 ลงใน `03_Projects/.cache/background-isolation-foreground-sequences/` (~353 MB ต่อคลิป)
3. **ผลลัพธ์:** คลิป 28 วินาทีเพียง 1 คลิป กินพื้นที่ฮาร์ดดิสก์ไปถึง **1.3 GB (1,303 MB)** และสร้างไฟล์ภาพกระจัดกระจายกว่า **1,720 ไฟล์ต่อคลิป**
4. **หากตัดต่อ 100 คลิป:** จะกินพื้นที่ฮาร์ดดิสก์สูงถึง **130.3 GB** และสร้างไฟล์ภาพเกือบ **200,000 ไฟล์** ส่งผลให้:
   - ฮาร์ดดิสก์เต็มอย่างรวดเร็ว
   - Disk I/O ติดขัดอย่างรุนแรง (FFmpeg ต้องเปิด-ปิดไฟล์รูป 860 ครั้งระหว่างเรนเดอร์)
   - หน้าจอ Editor Preview หน่วง เพราะต้องดาวน์โหลดไฟล์ PNG ทีละภาพผ่าน HTTP ไปวาดลง Canvas

---

## 🔬 2. การวิเคราะห์แนวทางของ CapCut และมาตรฐานอุตสาหกรรม

โปรแกรมตัดต่อระดับสากล (CapCut, Premiere Pro, DaVinci Resolve) แก้ปัญหานี้ด้วยสถาปัตยกรรมที่แตกต่างกันอย่างสิ้นเชิง:

| คุณลักษณะ | OmniCut ปัจจุบัน (PNG Sequence) | CapCut / มาตรฐาน Pro (Compressed Mask Video) | ผลต่างและความคุ้มค่า |
| :--- | :--- | :--- | :--- |
| **โครงสร้างข้อมูล** | ไฟล์รูปภาพ PNG แยก 860 ไฟล์ | **ไฟล์วิดีโอเดี่ยว 1 ไฟล์ (`cutout.webm` หรือ `mask.mp4`)** | ลดจำนวนไฟล์จาก 860+ เหลือ **1 ไฟล์** |
| **ขนาดไฟล์เฉลี่ย (28 วิ)** | **~1,300 MB (1.3 GB)** | **~20 MB – 35 MB** | **ประหยัดพื้นที่ลง 97.5% – 98.5%** |
| **พื้นที่เมื่อผลิต 100 คลิป** | **~130 GB (เต็มฮาร์ดดิสก์)** | **~2.5 GB (กินพื้นที่น้อยมาก)** | ประหยัดเนื้อที่ไปกว่า **127.5 GB** |
| **I/O Overhead** | สูงมาก (เปิด/ปิด File Handle 860 ครั้ง) | ต่ำสุดขีด (เปิดไฟล์เดียวแบบ Streaming) | เรนเดอร์เร็วกว่าเดิม 2–3 เท่า |
| **การพรีวิวในเบราว์เซอร์** | Fetch PNG ทีละเฟรมเข้า Canvas | เล่นผ่านแท็ก `<video>` ซ้อนเลเยอร์ได้สด 60 FPS | พรีวิวเนียนตา ไม่กินแรม |
| **อายุการใช้งานข้อมูล** | ค้างเติ่งในฮาร์ดดิสก์จนกว่าจะลบเอง | **Transient / Auto-Purge หลัง Export สำเร็จ** | ขยะไม่สะสมในเครื่อง |

---

## 🏗️ 3. การเลือกรูปแบบวิดีโอ (Video Codec Architecture Comparison)

เราได้ศึกษาและเปรียบเทียบรูปแบบวิดีโอ 2 รูปแบบที่เหมาะสมที่สุดสำหรับ Pipeline:

```
ทางเลือกที่ 1: WebM Container + VP9 yuva420p (Single Transparent Video) ⭐️ [แนะนำเป็นแกนหลัก]
┌────────────────────────────────────────────────────────┐
│  cutout.webm (25 MB)                                   │
│  ├── วิดีโอ RGB สินค้า                                    │
│  └── Alpha Channel โปร่งใสในตัว (Native Transparency)     │
└────────────────────────────────────────────────────────┘
ข้อดี:
- เบราว์เซอร์ Chromium / Chrome / Edge รองรับ Native Transparency ในแท็ก <video> 100%
- FFmpeg รองรับการอ่านและถอดรหัสแบบ native ไม่ต้องเขียน filter graph ซับซ้อน
- สะดวกในการพรีวิวใน SequencePlayer.jsx เพียงใช้ <video src="...cutout.webm">

ทางเลือกที่ 2: MP4 Container + H.264 Greyscale Matte (Mask Video)
┌────────────────────────────────────────────────────────┐
│  cutout_mask.mp4 (15 MB)                               │
│  └── วิดีโอขาว-ดำ (Silhouette Mask: ขาว=สินค้า, ดำ=พื้นหลัง) │
└────────────────────────────────────────────────────────┘
ข้อดี:
- ขนาดเล็กที่สุด (~15 MB)
- ใช้ประโยชน์จาก Hardware Acceleration (NVENC / QSV) ในการเข้ารหัสรวดเร็วมาก
- FFmpeg ใช้วิดีโอต้นฉบับ 01_Raw ควบคู่กับ mask.mp4 ผ่านฟิลเตอร์ alphamerge
```

**ข้อสรุปเชิงสถาปัตยกรรม:**  
เราจะใช้ **WebM VP9 Alpha (yuva420p)** เป็นรูปแบบมาตรฐานหลักสำหรับการสร้าง Foreground Artifact เนื่องจากมอบความยืดหยุ่นสูงสุดทั้งฝั่ง Web Preview และ FFmpeg Renderer

---

## ⚡ 4. สถาปัตยกรรมระบบใหม่: Zero-PNG Direct Streaming Pipe

### 4.1 แผนผังเปรียบเทียบ Pipeline เก่า vs ใหม่

```
🔴 สถาปัตยกรรมเดิม (Legacy File-Spam Pipe):
source.mp4 ──► [FFmpeg Extract] ──► 860 Source PNGs (950 MB)
                                           │
                                           ▼
                                 [rembg Worker Process]
                                           │
                                           ▼
                                    860 RGBA PNGs (353 MB)
                                           │
                                           ▼
                                    [FFmpeg Render]
[ รวมขยะในดิสก์ = 1,303 MB / 1,720 ไฟล์ ]

---------------------------------------------------------------------------------

🟢 สถาปัตยกรรมใหม่ (Zero-PNG Direct Streaming Pipe):
source.mp4 ──► [FFmpeg Pipe in RAM] ──► [rembg Batch Inference] ──► [FFmpeg VP9 Encoder] ──► cutout.webm (25 MB)
                                                                                                  │
                                                                           ┌──────────────────────┴──────────────────────┐
                                                                           ▼                                             ▼
                                                                  [Editor Web Preview]                          [Final FFmpeg Render]
                                                                (HTML5 <video> 60 FPS)                        (overlay=format=auto)
[ รวมขยะในดิสก์ = 25 MB / 1 ไฟล์เดี่ยว — ลดพื้นที่ 98% ไร้ขยะชั่วคราว ]
```

---

## 🛠️ 5. รายละเอียดส่วนประกอบทางเทคนิค (Technical Components)

### 5.1 คอมโพเนนต์ที่ 1: Direct Video-to-Video Cutout Generator
* **ไฟล์:** `scripts/background_isolation_video_worker.py`
* **กลไกการทำงาน:**
  1. ดึงเฟรมจากคลิปต้นฉบับผ่าน `subprocess.Popen` ของ FFmpeg ออกมาเป็น Raw Video Pipe (BGR24 / RGB24) ตรงเข้าหน่วยความจำ (RAM) โดย**ไม่มีการบันทึกไฟล์ภาพลงดิสก์แม้แต่รูปเดียว**
  2. ส่งเฟรมเข้าโมเดล Rembg (ONNX Runtime / u2net / isnet) ประมวลผลสร้าง Alpha Mask
  3. นำ RGB ต้นฉบับรวมกับ Alpha Mask ได้ RGBA Buffer แล้ว Pipe ตรงเข้า FFmpeg Subprocess ตัวที่สองเพื่อบีบอัดเป็น WebM:
     ```bash
     ffmpeg -y -f rawvideo -vcodec rawvideo -s 1080x1920 -pix_fmt rgba -r 30 -i pipe:0 \
            -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 2M -crf 28 -deadline realtime -cpu-used 4 \
            03_Projects/.cache/background-isolation-videos/{artifact_id}/cutout.webm
     ```
  4. สร้าง `manifest.json` ระบุข้อมูล artifact, ความละเอียด, FPS, จำนวนเฟรม, และ path ไปยัง `cutout.webm`

### 5.2 คอมโพเนนต์ที่ 2: Backend FFmpeg Compositor Integration
* **ไฟล์:** `scripts/video_editor.py` & `scripts/background_isolation_compositor.py`
* **การเปลี่ยนแปลงใน Filter Graph:**
  - แทนที่จะใช้ Input แบบ Frame Pattern (`-start_number X -i frames/frame_%06d.png`)
  - เปลี่ยนมาใช้อินพุตแบบวิดีโอไฟล์เดียว:
    ```bash
    -ss {trim_start} -t {source_span} -i "path/to/cutout.webm"
    ```
  - ในฟิลเตอร์คอมโพสิต:
    ```
    [clip_{idx}_transformed][{fg_idx}:v]overlay=eof_action=pass:format=auto[clip_{idx}_composited]
    ```
  - **Backward Compatibility:** ตรวจสอบโครงสร้าง artifact หากโปรเจกต์เก่ายังมี `frames/` ให้ทำงานด้วย legacy path ต่อไปได้ 100%

### 5.3 คอมโพเนนต์ที่ 3: Frontend Video-Layer Preview
* **ไฟล์:** `frontend/src/components/editor/player/SequencePlayer.jsx`
* **การเปลี่ยนแปลง:**
  - เพิ่มแท็ก `<video>` เลเยอร์โปร่งใส (Alpha Layer) ด้านบนข้อความ:
    ```jsx
    {hasCutout && (
      <video
        ref={cutoutVideoRef}
        src={`/api/media/03_Projects/.cache/background-isolation-videos/${artifactId}/cutout.webm`}
        className="pointer-events-none absolute inset-0 h-full w-full object-contain"
        playsInline
        muted
      />
    )}
    ```
  - ซิงค์เวลา `currentTime` ระหว่าง Main Video Player กับ Cutout Video Player อัตโนมัติ

### 5.4 คอมโพเนนต์ที่ 4: วงจรบริหารพื้นที่และล้างแคชอัตโนมัติ (Storage Lifecycle Management)
* **ไฟล์:** `scripts/storage_cleaner.py` & `frontend/src/components/system/SystemSettings.jsx`
* **ฟีเจอร์ใหม่:**
  1. **สแกนและระบุขนาดแคช Cutout:** แสดงตัวเลขขนาดพื้นที่ `.cache` ชัดเจนในหน้า System Settings (เช่น `แคชการตัดพื้นหลัง (Cutout): 1.3 GB`)
  2. **ปุ่ม "ล้างแคช Cutout" (1-Click Purge):** ล้างโฟลเดอร์ `.cache` ได้ทันที คืนพื้นที่ให้เครื่องใน 1 วินาที โดยไม่กระทบฟุตเทจดิบและคลิปที่เรนเดอร์แล้ว
  3. **Auto-Purge Post-Render (ทางเลือกเปิด/ปิดได้):** เมื่อ Export คลิปเสร็จลง `04_Exports/` ระบบสามารถสั่งลบแคชของโปรเจกต์นั้นทิ้งอัตโนมัติ (หากผู้ใช้เปิดโปรเจกต์มาแก้ไขใหม่ ค่อยกดตัดใหม่เฉพาะตอนจำเป็น)
  4. **LRU Cache Cap (เพดานจำกัดความจุ):** ตั้งเพดานสูงสุด เช่น **10 GB** หากยอดรวมเกิน ระบบจะลบไฟล์แคชของโปรเจกต์ที่เก่าที่สุดออกก่อนอัตโนมัติ (FIFO / Least Recently Used)

---

## 🗺️ 6. แผนการดำเนินงานและขั้นตอนลงมือ (Implementation Phases)

### 🚀 Phase 1: มาตรการบรรเทาปัญหาทันที (Immediate Space Relief)
- [ ] เพิ่มการสแกนและล้าง `03_Projects/.cache` ใน `scripts/storage_cleaner.py`
- [ ] เพิ่มปุ่ม **"ล้างแคช Cutout ทันที"** ในหน้า System Settings (ล้าง 1.3 GB คืนเครื่องทันที)
- [ ] เพิ่มออปชัน Auto-Clean แคชหลังเรนเดอร์เสร็จ

### ⚙️ Phase 2: พัฒนา Video Worker Engine (Single Video Generator)
- [ ] สร้าง `scripts/background_isolation_video_worker.py` รัน rembg สตรีมตรงเข้า WebM VP9 Alpha
- [ ] ทดสอบความเร็วและขนาดไฟล์จริง เปรียบเทียบคุณภาพระหว่าง WebM VP9 vs PNG

### 🧩 Phase 3: เชื่อมต่อ Backend Render Engine
- [ ] ปรับปรุง `scripts/video_editor.py` ให้รับอินพุต `cutout.webm` และคง legacy fallback
- [ ] อัปเดตชุดทดสอบ `tests/test_background_isolation_render_integration.py` ให้ครอบคลุมวิดีโอ WebM

### 🖥️ Phase 4: เชื่อมต่อ Frontend Preview & Parity
- [ ] เพิ่ม Video Layer ใน `SequencePlayer.jsx`
- [ ] ทดสอบ Parity ระหว่างหน้าจอตัดต่อ (Preview) กับไฟล์ที่เรนเดอร์จริง (Render)

---

## 📊 7. ผลลัพธ์และตัวชี้วัดความสำเร็จ (Success Metrics)
1. **ขนาดพื้นที่:** ลดพื้นที่จัดเก็บจาก 1.3 GB เหลือต่ำกว่า 35 MB ต่อคลิป (ประหยัดอย่างน้อย **97%**)
2. **ความจุ 100 คลิป:** ใช้พื้นที่รวมไม่เกิน **3.5 GB** (จากเดิม 130 GB)
3. **ความเร็ว:** ประหยัดเวลา Disk I/O และทำให้การเรนเดอร์จบไวกว่าเดิมอย่างน้อย 25%
4. **ความปลอดภัย:** ไม่แตะต้อง `01_Raw` และ `02_Assets` 100% ตามกฎเหล็กข้อ 1
