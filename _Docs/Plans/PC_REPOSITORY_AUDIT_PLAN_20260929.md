# แผนตรวจและยกระดับ OmniCut บน PC — 2026-09-29

ดำเนินการโดย: Codex (GPT-6) · ประเภท: ตรวจสถานะและวางแผน ยังไม่ติดตั้งโมเดลหรือเปลี่ยน pipeline

## ข้อสรุปสำหรับการตัดสินใจ

ให้ปิดงาน SAM 2 ที่กำลังทำอยู่และเก็บ baseline จริงก่อนเพิ่ม dependency ใหม่ จาก 6 กลุ่มในภาพ มีเพียง **SAM 2 ที่พร้อมเดินหน้าต่อจากของเดิม**; **BiRefNet และ DeepFilterNet เหมาะทำการทดลองแบบแยกส่วน**; **WhisperX ต้องพิสูจน์ตัว aligner ภาษาไทย**; **CapCut exporter ต้องตรวจ URL/เวอร์ชัน CapCut และสัญญาข้อมูลก่อน**; **Kokoro เป็นตัวเลือกภาษาอังกฤษ/จีนเฉพาะกรณี**. ไม่ควรดาวน์โหลดทั้งชุดทันที เพราะความแรงของ PC ไม่ได้ยืนยันว่าผลลัพธ์ตรงสคริปต์, ภาพตรง Preview, เปิด Draft ได้ หรือใช้เชิงพาณิชย์ได้

## หลักฐานสถานะปัจจุบัน

| หัวข้อ | ที่ตรวจพบ | ความหมาย |
| :--- | :--- | :--- |
| เครื่อง | RTX 4060 8 GB, i7-14700, RAM 32 GB; runtime `torch 2.6.0+cu124` เห็น CUDA; FFmpeg 8.1.1; D: ว่างราว 435 GiB | พอทำ spike ทีละโมเดล ควรกำหนดเพดาน VRAM/พื้นที่เมื่อรันร่วมกัน |
| SAM 2 | มี checkpoint และ benchmark 60 เฟรม: startup 1.871 s + tracking 7.777 s = 9.648 s; track throughput 7.71 FPS, peak allocated 1,396.88 MiB | ทดสอบสั้นสำเร็จแล้ว แต่ยังไม่วัด end-to-end รวม decode, alpha encode, preview และ final render; ไม่ใช่ real time |
| งานค้าง | `TODO.md` มีรอบ SAM2-DEPTH-TEXT-PIPELINE และรอบซับของ agent อื่น; working tree มีการแก้ backend/frontend พร้อมกัน | ห้ามเอาผลจากไฟล์ที่กำลังแก้ไปอ้างเป็น release gate และห้ามเขียนทับงานของ agent อื่น |
| ความพร้อม SAM 2 | backend เริ่มรับ `sam2`; `frontend/src/lib/backgroundIsolationPreview.js` เดิมรองรับ `rembg` อย่างเดียว (ระหว่างการตรวจมีการแก้ไฟล์อยู่); worker และ API ยังมี absolute path ไป checkpoint ภายนอก | ต้องทำ path resolution แบบอิงโปรเจกต์และยืนยัน Preview/Render parity ก่อนปล่อยใช้ |
| ระบบเสียง/ซับ | `voice_stage.py` จัด cue จาก RMS speech blocks และ fallback ตามสัดส่วนตัวอักษร; มี Faster-Whisper ในเครื่องมือเฉพาะงาน แต่ `requirements.txt` ไม่มี WhisperX | forced alignment เป็นช่องว่างจริง โดยเฉพาะไทย แต่ต้องใช้ script ทางการเป็นข้อความอ้างอิงและตรวจพยางค์ |
| CapCut | พบการอ้างโฟลเดอร์ Draft ใน UI แต่ไม่พบตัวเขียน `draft_content.json` ใน `scripts/` | exporter เป็นงานใหม่ ไม่ใช่การตั้งค่าเล็กน้อย |
| ผลทดสอบเก่า | log วันที่ 27 ก.ย.: backend 2,089 passed / 1 failed / 8 skipped; frontend 410 passed / 0 failed; เป็น snapshot ก่อนงาน SAM 2 รอบนี้ | ห้ามสรุปว่า current tree ผ่าน test ทั้งหมด; ต้องรันใหม่เมื่อ implementation หยุดนิ่ง |

**ข้อควรแก้ในแผน GPU เดิม:** ข้อความ “แม่นยำเท่ากัน 100%” อ้างจาก coverage mask เท่านั้น ไม่มี annotated ground truth; “7.78 s” เป็น tracking อย่างเดียว; การคาดเวลา 5–15 s เป็นการ extrapolate จากคลิป 2 s. ความเร็ว BiRefNet 0.08–0.15 s/ภาพยังไม่ใช่ตัวเลขของ RTX 4060/งานจริงในโปรเจกต์. อย่าใช้ตัวเลขเหล่านี้เป็นเกณฑ์รับงานจนวัดใหม่.

## ประเมิน repository ที่เสนอ

| ตัวเลือก | คำตัดสิน | ประโยชน์และเงื่อนไข |
| :--- | :--- | :--- |
| [facebookresearch/sam2](https://github.com/facebookresearch/sam2) | **ทำต่อของเดิม (P0)** | มี runtime/checkpoint/ผล spike แล้ว; upstream รองรับ video predictor และแนะนำ WSL บน Windows. ปิดการเชื่อม backend + UI + render ก่อนทดลองโมเดลใหญ่ขึ้น; ยืนยัน mask ของสินค้า/มือและฉากตัดหลายแบบ. ไม่ดาวน์โหลดซ้ำ |
| [ZhengPeng7/BiRefNet](https://github.com/ZhengPeng7/BiRefNet) | **spike ภาพนิ่ง (P2)** | มีรุ่นสำหรับ segmentation และ matting ต่างกัน; เลือกตามภาพสินค้า 10–20 ภาพที่มี ground truth/จุดตรวจขอบ แล้วเทียบ rembg ด้วยคุณภาพ, เวลา, VRAM และขนาดไฟล์. ตัวเลข upstream 3.45 GB เป็น RTX 4090 ที่ 1024² ไม่ใช่คำรับประกันบน 4060. ไม่แก้ badge 6 แบบหรือ assets จริงก่อนชนะ gate |
| [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) | **พักการใช้ใน workflow คลิปขาย (P3)** | model weights ให้ใช้แบบ non-commercial; ต้องมี commercial agreement หรือบริการที่มีสิทธิ์เหมาะสมก่อนใช้งานเชิงพาณิชย์. ไม่ปนกับคำว่า open-source แล้วถือว่าใช้ขายได้ |
| CapCut Draft: URL ในภาพ `A-Soul-Database/CapCut-API`, `Li-Zhaoxi/PyCapCut` | **ตรวจแหล่งอ้างอิงก่อน (P2)** | URL ทั้งสองตรวจยืนยันไม่ได้ในการสำรวจนี้. พบ [GuanYixuan/pyCapCut](https://github.com/GuanYixuan/pyCapCut) ซึ่งบอกเองว่ากำลังย้ายโค้ด และ template รับ Draft ที่ไม่เข้ารหัส; เริ่มจาก proof of concept กับ Draft สำเนาและเวอร์ชัน CapCut PC ที่ใช้จริง. พิจารณา FFmpeg render เป็น master ต่อไป |
| [m-bain/whisperX](https://github.com/m-bain/whisperX) | **spike เฉพาะ timing ไทย (P1)** | forced alignment ใช้ model แยกตามภาษา; เอกสาร upstream ให้หา model เองเมื่อไม่มี default และรายการ default ไม่รวมไทย. ทดลอง transcript ทางการ 5–10 คลิป ไทย/อังกฤษปน; วัด error เทียบ cue ที่คนตรวจ. ถ้า aligner ไทยไม่ผ่าน ไม่เพิ่มลง main pipeline |
| [Rikorose/DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) | **ตัวเลือกสำหรับเสียงพูดที่บันทึกเอง (P2)** | มี CLI/prebuilt และไลเซนส์ MIT/Apache; ทำ A/B เฉพาะ noisy narration หรือเสียงหน้างาน. ห้ามประมวลผลเสียง TTS ที่สะอาดทุกคลิป เพราะอาจทำเสียงแตก/ลดความชัดโดยไม่จำเป็น |
| [hexgrad/kokoro](https://github.com/hexgrad/kokoro) | **พักไว้ก่อน (P3)** | upstream ระบุภาษาอังกฤษ จีน และภาษาอื่น แต่ไม่มีไทยในรายการ; จุดแข็งคือ local offline voice ภาษาเหล่านั้น. ไม่ทดแทนเสียงไทย Fenrir/Edge-TTS ตาม SOP; ทดลองเฉพาะเมื่อมี use case voice ต่างภาษาจริง |

## แผนลงมือเรียงลำดับ

### P0 — ปิดฐานเดิมก่อน (เจ้าของงาน SAM 2 + รอบตรวจเสถียรภาพ)

1. ให้เจ้าของรอบ SAM 2 ปิด T1–T4 และ gate ที่เขียนใน `TODO.md`; แก้ absolute checkpoint paths ใน `scripts/api_background_isolation.py`, `background_isolation_video_worker.py`, `background_isolation_sam2_worker.py` ให้ใช้ root/config และไม่พึ่ง directory ภายนอกเครื่อง. ตรวจ `requirements.txt` ของ runtime เพราะยัง pin `torch==2.5.1+cpu` แต่ environment จริงเป็น `2.6.0+cu124`; lock/runtime ต้องสอดคล้องโดยไม่ลง global package.
2. ทำ benchmark end-to-end ด้วยช็อต 2, 10, 30 วินาทีที่มีมือ, ขอบใส, การบังวัตถุ, การเปลี่ยนฉาก. บันทึกเวลาขั้น decode/tracking/encode/render แยก, peak VRAM, ขนาด artifact; สร้างผลทดสอบใน `.tmp/` เท่านั้นและ cleanup หลังตรวจ. ตรวจ prompt วัตถุผิด/หายแล้วต้อง fail ชัดเจน.
3. เปรียบ Preview กับ FFmpeg final frames ที่ต้น/กลาง/ท้ายและช่วง scene cut. ตรวจ alpha ด้วย ffprobe/ดึงเฟรมจริง, safe zone, ซับ/ฟอนต์ golden master, save/reload, cache invalidation, CPU fallback. รัน targeted pytest + frontend tests/build; full suite เมื่อ code freeze. ห้ามติ๊กผ่านจาก contact sheet หรือ coverage เพียงอย่างเดียว.
4. ทำ baseline ก่อน/หลังด้วยช็อตเดียวกันและตั้ง release gate ที่วัดได้: render ไม่ล้ม, ไม่มี foreground หายต่อเนื่อง, ลำดับชั้น text/subject ถูก, preview/render ต่างกันภายใน tolerance ที่นิยามจากภาพจริง; เวลาต่อ 10 s และ VRAM ต้องบันทึก ไม่ตั้งค่าจากการเดา.

### P1 — คุณภาพซับและเสียงพากย์

5. สร้างชุด reference จากบทอนุมัติและเสียงจริง 5–10 คลิป มีไทยล้วนและไทยปนชื่อแบรนด์อังกฤษ; จดเวลาเริ่ม/จบระดับคำหรือพยางค์โดยคน. เทียบ RMS/proportional ปัจจุบันกับ WhisperX + aligner ไทยที่เลือก. Gate: timestamp median/p95 ดีขึ้นชัดเจน, ไม่ฉีกพยางค์, ไม่เปลี่ยนบท, Ghost Reveal และ Preview/Render เหมือนกัน. ถ้าไม่มี aligner ไทยที่พิสูจน์ได้ ให้ปรับ timing จาก transcript/เสียงเดิมแทนการติดตั้ง WhisperX เต็มระบบ.

### P2 — โมเดลเสริมแบบ opt-in

6. ทดลอง BiRefNet ภาพนิ่งใน isolated venv; ใช้ภาพสินค้าเดิมแบบ read-only และ output `.tmp/`. วัดขอบสาย/ผิวสะท้อน/รูโปร่งใสเทียบ rembg แบบ blind review และเกณฑ์ pixel ที่มี reference. ให้ default เดิมอยู่จนคุณภาพชนะและไม่มี regression.
7. ทดลอง DeepFilterNet เฉพาะ sample เสียงรบกวน: เปรียบ intelligibility, artifact, loudness/true peak และเวลาประมวลผล; ใส่ opt-in ก่อน voice mix ถ้าผ่าน.
8. ทำ CapCut exporter เป็น proof of concept ใน Draft สำเนาใหม่: ระบุเวอร์ชัน CapCut, schema และตำแหน่ง media, backup ก่อนเขียน, เปิด Draft ใน CapCut จริง, save/reopen, render เทียบกับ master. ครอบคลุม text/overlay/transition ที่ใช้งานจริง; ฟีเจอร์ที่ map ไม่ได้ต้องแจ้งผู้ใช้. ห้ามเขียนทับ Draft จริง.

### P3 — เฉพาะเมื่อมีความต้องการจริง

9. Kokoro สำหรับ voice ภาษาอังกฤษ/จีนที่ผ่านการฟังเทียบ; RMBG-2.0 เฉพาะเมื่อสิทธิ์เชิงพาณิชย์ชัดเจน. แยก optional runtime และบันทึก model version/checksum/license ทุกตัว.

## เกณฑ์ระดับระบบที่ควรเสริม

- **Reproducibility:** บันทึก Python, CUDA, Torch, FFmpeg, model revision/checksum, CapCut PC version และ FFmpeg command ใน artifact manifest; health screen ต้องแสดงสถานะจริง.
- **Resource scheduler:** จำกัดงาน GPU หนักให้รันทีละตัวบน VRAM 8 GB; จับ OOM แล้วคืน error ที่แก้ได้, ไม่ทำ fallback เงียบ ๆ จนคุณภาพเปลี่ยน.
- **Data safety:** cache key รวม engine/model/checkpoint/config/source hash; atomic publish และ revision guard; งานทดลองใช้ `.tmp/` และไม่แก้ `01_Raw/`, `02_Assets/`, `04_Exports/` หรือ Draft ต้นฉบับ.
- **Acceptance:** ทุกฟีเจอร์ต้องทดสอบ output จริง, preview/render parity, งานไทยตาม SOP, 9:16, และ regression ของ save/reload. เพิ่ม dependency หลัง spike ผ่าน ไม่ใช่ก่อน.

## ขอบเขตของการตรวจครั้งนี้

เป็น code/document/runtime audit ณ 29 ก.ย. 2026 ระหว่าง agent อื่นแก้ SAM 2 อยู่; ยังไม่รัน full test หรือ benchmark/visual QA ใหม่. ตัวเลข test ที่อ้างเป็น log เดิมวันที่ 27 ก.ย.; รายงาน GPU เป็นผลของ Antigravity จาก 60 เฟรม ไม่ใช่การวัดซ้ำในรอบนี้. URL CapCut สองรายการในภาพยังไม่ยืนยันว่าเป็น upstream ที่มีอยู่จริง. Jev `noul=0.91` แต่ `confidence=null` จึงไม่ใช้เป็นหลักฐานหรืออนุมัติการติดตั้ง; ข้อสรุปอิงโค้ด, runtime และเอกสาร upstream ที่ตรวจได้.
