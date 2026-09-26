# แผนพัฒนาคุณภาพและความลื่น Cutout

วันที่: 2026-09-26 · ดำเนินการโดย: Codex (GPT-6)
สถานะ: แผนสำหรับลงมือเป็นขั้น; ยังไม่มีผล benchmark ของวิธีใหม่
ติดตาม: `TODO.md` รอบ `CUTOUT-TEMPORAL-QUALITY-PLAN-20260926`

## 1. ผลลัพธ์ที่ต้องการและหลักฐานปัจจุบัน

เป้าหมายคือวัตถุที่เลือกอยู่ครบ ขอบไม่สั่นหรือมีเงาตาม การเล่น/ลาก Timeline ต่อเนื่อง และภาพ Export ตรงกับ Preview. ใช้ CapCut เป็นตัวเทียบจากผลภาพเมื่อมี reference คลิปเดียวกัน ไม่สมมติว่าเรารู้โมเดลภายใน CapCut หรือรับรองความเท่ากันก่อนวัด.

ระบบปัจจุบันมี WebM alpha แล้ว; การเก็บวิดีโอช่วยเรื่องจำนวนไฟล์และพื้นที่ แต่ไม่รับประกันคุณภาพ mask หรือ playback. รายงานเดิมยืนยัน BLU01 4 artifacts / 5 clips / 848 frames / 7.90 MiB และทดลอง Preview ทุกช่วง; ยังไม่ได้วัด temporal quality หรือ playback benchmark ครบ.

| สิ่งที่พบจากโค้ด | ผลที่อาจเกิด | สิ่งที่ต้องพิสูจน์ |
| --- | --- | --- |
| worker ใช้ rembg แยกเฟรม แล้ว blend alpha ที่ตำแหน่งพิกเซลเดิมเมื่อค่าต่างกัน <24 | ขอบวัตถุยังสั่น; บางการเคลื่อนที่อาจมีเงาตาม | เปรียบเทียบไม่ smooth / smooth เดิม / ชดเชย motion |
| ไม่มี scene cut reset ใน temporal branch | mask จากฉากก่อนอาจรบกวนฉากใหม่ | hard cut, วัตถุหายแล้วกลับมา, frame discontinuity |
| video Cutout branch ไม่มีการตั้ง playbackRate ตาม clip; seek เมื่อคลาด >65 ms | คลิปเปลี่ยนความเร็วอาจต้อง seek บ่อยและแสดง pending | วัดจำนวน corrective seeks, drift, dropped/pending frames |
| โหลด alpha video 1080x1920 สำหรับ Preview | decode/composite อาจหนักบนเครื่องนี้ | เปรียบเทียบ master กับ proxy 540/720 โดยใช้ alpha เดียวกัน |
| ready video ตรวจ decode/count/alpha แต่ไม่ตรวจว่าตัดวัตถุที่ผู้ใช้ต้องการครบ | cooler ผ่าน แต่โทรศัพท์หรือมืออาจถูกเอาออก | ระบุวัตถุเป้าหมายและตรวจ mask ตามเป้าหมายนั้น |
| เคยมี project save เก่าทับ migration และ cache ถูกล้าง | config ready แต่ไฟล์หาย | revision conflict, scoped cache purge, restart/reload |

หลักฐานโค้ด: `scripts/background_isolation_video_worker.py`, `scripts/api_background_isolation.py`, `scripts/video_editor.py`, `frontend/src/components/SequencePlayer.jsx`, `frontend/src/lib/backgroundIsolationPreview.js`. รายงานเดิม: `_Docs/Reports/CUTOUT_VIDEO_PIPELINE_20260926.md`.

## 2. ข้อจำกัดเครื่องและแนวทางเลือกเทคโนโลยี

ตรวจแบบอ่านอย่างเดียว: AMD Ryzen 7 7735HS, AMD Radeon(TM) Graphics, RAM ระบบ 14,701,584,384 bytes (~13.69 GiB). ค่า AdapterRAM ที่ Windows รายงาน 2 GiB ไม่ใช่ข้อสรุปเรื่องหน่วยความจำ GPU ที่ใช้ได้จริง. ไม่พบ `nvidia-smi` ใน PATH; ONNX Runtime 1.30.0 รายงาน CPU/Azure providers ไม่ได้รายงาน GPU provider. `.venv` เป็น Python 3.14.2 และไม่มี torch/sam2.

ข้อเสนอคือเริ่ม Q0–Q2 บนเครื่องนี้ โดยเตรียม Cutout ล่วงหน้าและเล่น artifact ที่เสร็จแล้ว. Q3 เป็นการทดลองโมเดลแยก runtime; ไม่อ้างว่าจะประมวลผล AI 30 FPS บนเครื่องนี้. วัดเวลา inference แยกจาก playback 30 FPS. หากต้องใช้ GPU เครื่องอื่น ให้ระบุค่าใช้จ่าย/การส่งไฟล์และขอการตัดสินใจก่อนเชื่อมบริการนั้น.

| ตัวเลือก | บทบาทในแผน | เงื่อนไขตัดสิน |
| --- | --- | --- |
| rembg + motion compensation | ทางปรับปรุงบน CPU ที่มีอยู่ ใช้เป็น baseline และ fallback | ต้องลดขอบสั่นโดยไม่ทำให้ขอบล่าช้าหรือวัตถุหาย |
| SAM 2.1 tiny/small | ผู้สมัครหลักสำหรับทดลองติดตามวัตถุจากจุด/กรอบและแก้ mask ระหว่างวิดีโอ | แยก environment, ทดสอบ CPU feasibility ก่อน; ต้องผ่านคุณภาพ/หน่วยความจำบนงานจริง |
| Cutie | ผู้สมัครสำรองเมื่อ SAM 2.1 ไม่ผ่านข้อจำกัดหรือคุณภาพ | มี object memory แต่ต้องพิสูจน์ Windows/runtime และทรัพยากรแยก |
| SAM 3/3.1 | ตัวเลือกทดลองเมื่อมี CUDA worker ที่เหมาะสม | upstream ระบุ CUDA GPU; ไม่เลือกเป็นค่าเริ่มต้นของเครื่อง AMD นี้ |
| Robust Video Matting | พิจารณาเฉพาะงานคนภายหลัง | upstream ออกแบบสำหรับ human matting จึงไม่ใช้แทนตัวแยกสินค้าโดยอัตโนมัติ |

SAM 2 รองรับ video prompts/propagation และ checkpoints หลายขนาด; upstream ระบุ Python/PyTorch dependencies และแนะนำ WSL บน Windows. FPS ที่ upstream แสดงวัดบน A100 จึงใช้เป็นความเร็วของเครื่องนี้ไม่ได้. [SAM 2 official](https://github.com/facebookresearch/sam2)

Cutie เป็น video object segmentation ที่ใช้ memory; repository ระบุทดสอบ Ubuntu. [Cutie official](https://github.com/hkchengrex/Cutie) ส่วน SAM 3 repository ระบุ Python >=3.12, PyTorch >=2.7 และ CUDA >=12.6 พร้อม SAM License. [SAM 3 official](https://github.com/facebookresearch/sam3) RVM ระบุชัดว่าออกแบบสำหรับ human video matting. [RVM official](https://github.com/PeterL1n/RobustVideoMatting)

ตรวจ license ของ code/checkpoint และ pin revision/checksum ตอนเลือก engine จริง. โมเดล segmentation ให้ขอบวัตถุ; ยังต้องมีขั้น refine alpha เพื่อรองรับขอบนุ่มและ motion blur. ห้ามถือว่าแปลง binary mask เป็น RGBA แล้วได้คุณภาพ matting ครบ.

## 3. ลำดับส่งมอบ

### Q0 — เก็บ baseline และกำหนดว่าต้องเก็บวัตถุอะไร

- ใช้ช่วง BLU01 5.460–16.642, 22.000–26.720, 45.000–51.660, 65.000–70.700 วินาที และชุดสังเคราะห์ที่มี alpha/PTS รู้คำตอบ. ตรวจ source time ของแต่ละ clip รวม speed ที่บันทึกจริง.
- กำหนด subject set รายช็อต: cooler อย่างเดียว / cooler+โทรศัพท์ / รวมมือ. ตั้งต้นเป็นสินค้าหลัก แต่แสดงภาพ mask ให้ยืนยันเป้าหมายก่อนประกาศว่าวัตถุ “หาย”. มือและโทรศัพท์ไม่ควรถูกเพิ่มทุกฉากโดยเดา.
- ทำ reference masks อย่างน้อย 5 จุดต่อ window รวมจุดบัง/หมุนเร็วที่พบ และแยกเฟรม holdout สำหรับตรวจ. Synthetic เป็น exact alpha ground truth; คลิปจริงใช้ annotation เฉพาะวัตถุและขอบที่ตัดสินได้.
- เก็บ current baseline: processing sec/source-sec, peak RAM, disk, startup, seek p50/p95, presented-frame drift, dropped frames และช่วง pending. เก็บ benchmark metadata ของ browser/CPU/resolution/warm-cold state.
- หากมี CapCut reference ให้ตัดช่วง/เลือกวัตถุ/ตั้ง output 1080x1920 30 FPS เหมือนกันเพื่อ A/B. ถ้ายังไม่มี ให้สรุปเฉพาะว่าดีขึ้นจากระบบปัจจุบัน.
- ส่งมอบเครื่องมือวัด `tools/benchmark_cutout_quality.py` และรายงาน `_Docs/Reports/`; automated tests ใช้ temp fixtures เท่านั้น. การตรวจคลิปจริงเป็น manual diagnostic ที่อ่าน source และสร้างผลใน `.tmp/`, cleanup หลังตรวจตามกฎโปรเจกต์.

**Gate:** เก็บค่าตั้งต้นครบทั้ง 4 windows; ยังไม่เลือกโมเดลจากภาพนิ่งตัวอย่างเดียว.

### Q1 — แก้ความลื่นในการเล่นก่อนเปลี่ยนโมเดล

- แยก controller ของ alpha video ออกจากวงรอบ draw ใน `SequencePlayer.jsx`; กำหนด effective playbackRate จาก clip speed และ transport rate. ใช้ source-time mapping เดียวกับวิดีโอต้นฉบับ/เสียง รวม trim, split และ freeze.
- ปรับ drift เล็กน้อยด้วย playbackRate รอบค่าฐาน; hard seek เฉพาะ discontinuity หรือ drift ที่เกินเกณฑ์ที่วัดได้. ขณะ drag ยกเลิกคำขอ seek เก่าและนำเสนอเฟรมของคำขอล่าสุด. เลี่ยง seek ทุก draw tick.
- ใช้ requestVideoFrameCallback บันทึก mediaTime ที่แสดงจริง; รองรับ error/end/pause/loop และ fallback ที่ตรวจได้เมื่อ API นี้ไม่มี. ไม่ตีความ loadeddata ว่าเฟรมตรงเวลาแล้ว.
- predecode clip ถัดไปตามรอยต่อ; จำกัด decoder ตาม active/next/transition และคืนทรัพยากรเมื่อออกจาก window. หาก decode ไม่ทัน แสดง buffering ชัดเจน ไม่วางวัตถุคนละเวลากับพื้นหลัง.
- ทดลอง alpha preview proxy 540x960 และ 720x1280 ที่ย่อลงจาก master Cutout สำเร็จแล้ว ใช้ PTS/duration เดียวกัน. ทดสอบ VP9 keyframe interval 15/30/60 เฟรมต่อผล seek/ขนาด. เลือกจาก benchmark ไม่สมมติว่า WebM ได้ hardware acceleration.
- Render อ่าน master Cutout 1080p; มีปุ่มดูคุณภาพ master แบบ paused สำหรับตรวจขอบ. ไม่ทำ inference ใหม่แยกสำหรับ proxy เพราะ mask จะไม่ตรงกัน.
- ใช้ mapping/decode lifecycle ร่วมกับ Stage B ของ `_Docs/Plans/CAPCUT_PREMIERE_TECH_INTEGRATION_PLAN.md`; RGB H.264 proxy ไม่รองรับ alpha จึงไม่ใช้แทน alpha proxy โดยตรง. ล้างแคชต้องจำกัด namespace ไม่กวาด `.cache` ทั้งหมด.

**Gate:** benchmark เล่นต่อเนื่อง/seek ตามตารางข้อ 4 ผ่านบนเครื่องนี้; ภาพ foreground ไม่กระพริบเป็นช่องว่างเมื่อเล่นคลิปที่เตรียมครบแล้ว.

### Q2 — ลดขอบสั่นโดยชดเชยการเคลื่อนไหว

- เพิ่มโมดูล `scripts/cutout_temporal.py` ทดลอง optical flow ที่ความละเอียดเหมาะสม; warp alpha เฟรมก่อนเข้าตำแหน่งปัจจุบันก่อนพิจารณารวม. ประเมินทิศ forward/backward และ occlusion เพื่อไม่ใช้ mask เก่าทับส่วนที่เพิ่งเปิดเผย.
- จำกัดการปรับเฉพาะบริเวณขอบที่มีความมั่นใจ; ส่วน motion เร็ว/flow ไม่ตรงให้ใช้การคาดการณ์ปัจจุบัน. ทดลองน้ำหนักจากชุด Q0 ไม่ยึด threshold 24 และ blend 0.65 เดิมเป็นค่ามาตรฐาน.
- reset temporal state เมื่อ scene cut, source discontinuity หรือ prompt revision เปลี่ยน. ช่วงที่วัตถุออกนอกภาพอนุญาต mask ว่างได้ ไม่บังคับทุกเฟรมต้องมี opaque pixels; หากวัตถุควรอยู่แต่หายให้แจ้งคุณภาพไม่ผ่าน.
- ทดลอง edge-aware alpha refinement ในแถบขอบแคบ; รักษารูจริง ช่องกล้อง สายไฟ และ motion blur. ไม่แก้ความนิ่งด้วยการ blur/dilate ทั้ง mask จนรูปทรงผิด.
- ประเมิน halos บนพื้นดำ ขาว และลาย checkerboard รวมตรงขอบตัวหนังสือด้านหลัง; แก้ RGB spill/premultiplication เมื่อพิสูจน์ว่ามีปัญหาจริง.

**Gate:** temporal error ลดตามข้อ 4 และคุณภาพรูปร่าง/รายละเอียดไม่ถอย. หาก flow ทำให้ ghosting เพิ่ม ให้คง baseline และเดิน Q3 ไม่เพิ่ม smoothing เพื่อกลบปัญหา.

### Q3 — ทดลองโมเดลที่มีความจำข้ามเฟรม

- ทำ engine contract `initialize(source, prompts, frame_map) → propagate → refine → finalize` แยกจาก FFmpeg writer. rembg เดิมยังเป็น backend หนึ่ง; AI ใหม่ไม่บังคับติดตั้งใน runtime FastAPI หลัก.
- ทดลอง SAM 2.1 tiny ก่อน small บนคลิปสั้น 2–3 วินาที แล้วทดสอบครบหนึ่ง window. pin environment ที่ติดตั้ง dependency ได้จริง; ทดสอบ Python 3.12 แยกหากจำเป็น ไม่ลดเวอร์ชัน `.venv` หลักโดยไม่มีเหตุผล.
- ใช้จุด/กรอบหรือ mask seed เลือก subject; เก็บ object IDs ข้ามเฟรม และให้เพิ่ม/ลบวัตถุได้. เมื่อติดตามหลุด ให้แก้ที่เฟรมที่ผิดแล้ว propagate ใหม่เฉพาะช่วงที่เกี่ยวข้อง.
- ตรวจ RAM growth และ chunk boundary; หากต้องแบ่งช่วง ให้มี overlap/state handoff ที่วัดได้ ไม่ reset ทุก chunk จนขอบกระโดด. ภาพถอดเฟรมชั่วคราวใช้พื้นที่จำกัดและลบเสมอ; artifact สำเร็จยังเป็นวิดีโอ.
- เก็บผล A/B: rembg เดิม / Q2 / video tracker พร้อม alpha refinement; ใช้ object completeness, edge quality, temporal error, RAM และ processing time ตัดสิน. เลือก Cutie เป็นการทดลองสำรองเมื่อมีเหตุผลจากผลแรก.
- หาก CPU ไม่ถึงงบเวลา/หน่วยความจำ ให้รายงานขีดจำกัดและคงโหมด local ที่ผ่าน. ออกแบบช่องต่อ GPU worker ไว้ได้ แต่การซื้อเครื่อง/เช่าบริการ/ส่งวิดีโอออกนอกเครื่องเป็นการตัดสินใจเพิ่ม.

**Gate:** มีรายงาน engine ที่ผ่านหรือเหตุผลไม่ผ่านบน hardware ที่วัดจริง; การรันสำเร็จหนึ่งเฟรมไม่ถือว่า integrate โมเดลเสร็จ.

### Q4 — ให้แก้ช็อตยากได้โดยไม่ต้องเริ่มทั้งคลิป

- Inspector มี “เลือกวัตถุ”, “เพิ่มส่วนที่เก็บ”, “ลบส่วนที่เกิน”, “ปรับขอบ” และ “สร้างช่วงนี้ใหม่”; ไม่แสดงชื่อ engine เป็นทางเลือกหลักให้ผู้ใช้ทั่วไป.
- เก็บ positive/negative prompts, object set และ correction keyframes ด้วย source PTS และพิกัด normalized ก่อน transform ของ Timeline; ใช้ mapping กลับจาก zoom/pan/mirror/rotation ของ Preview เพื่อให้คลิกตรงวัตถุ.
- แสดงช่วงที่ต้องตรวจเมื่อวัตถุหลุด/บัง/กลับเข้าภาพ และให้ propagate correction ข้างหน้า/ข้างหลังตามขอบเขต scene. วัตถุหลายชิ้นเลือก union แบบชัดเจน.
- Undo/Redo, Save/Reload และ project switch ต้องรักษา prompts/mask revision. สร้าง artifact ใหม่ให้พร้อมก่อนเปลี่ยน reference; ไม่แทน master ที่ใช้งานอยู่ด้วยไฟล์ครึ่งงาน.

**Gate:** แก้ช็อตที่ตัด cooler/โทรศัพท์ผิดหนึ่งครั้งแล้วติดตามต่อได้; reload/undo ไม่ทำให้ตัวเลือกหรือ Timeline เปลี่ยน.

### Q5 — รวมระบบและย้ายข้อมูลอย่างตรวจสอบได้

- Manifest revision ใหม่ระบุ source fingerprint, frame-map/PTS, subject/prompt revision, engine/checkpoint hash, refinement settings, quality report, master/proxy relation และ checksums. Cache key เปลี่ยนตามค่าที่มีผลต่อ mask; โหลด WebM schema 2 เดิมได้.
- แยกสถานะ media ready, quality review required และ failure; mask ที่ decode ได้ไม่เท่ากับเลือกวัตถุครบ. เก็บเหตุผล failure ให้ผู้ใช้แก้ต่อได้.
- เพิ่ม optimistic revision check ใน project save/migration และ job result apply: ถ้า project/source/prompt เปลี่ยนให้แจ้ง conflict และ rebase เฉพาะ reference ที่ยังตรง ไม่เขียน snapshot เก่าทับงานผู้ใช้.
- cache purge ระบุชนิด artifact และ reference ที่ได้รับผลกระทบ; ไม่ลบ RGB proxies/แคชงานอื่นพร้อม Cutout โดยไม่ตั้งใจ. ปุ่มเตรียมใหม่ต้องฟื้นสถานะและใช้ผลล่าสุดได้.
- ตรวจ Canvas/FFmpeg ที่ source PTS เดียวกัน พร้อม hook หลังสินค้าและ captions ด้านหน้า; ครอบคลุม speed, trim, split, scene cut, transitions, freeze, mirror, rotation, zoom/pan, VFR และ reopen.
- ปิด full gate ตาม `.agents/rules/testing_standard.md`; tracking ปัญหา accessibility ของ Inspector ที่ยังค้างแยกชัดเจน และไม่เรียก suite ที่ exclude module ว่า full pass.

**Gate:** ทุกข้อที่จำเป็นผ่านและ cleanup 100%; จึงเปลี่ยน default engine/quality และย้ายบล็อกรอบงานเข้า HISTORY.

## 4. เกณฑ์วัดที่เสนอให้ตรึงหลัง Q0

ตัวเลขต่อไปนี้เป็นเป้าหมายรับงาน ไม่ใช่ผลที่ทำได้แล้ว. ถ้าไม่ผ่านต้องปรับระบบหรือประกาศข้อจำกัด ไม่ลดเกณฑ์ย้อนหลังเพื่อให้ดูผ่าน.

| มิติ | วิธีวัดและเป้าหมาย |
| --- | --- |
| วัตถุครบ | selected-object IoU >=0.95 บน holdout ที่ขอบชัด; รายละเอียดสำคัญ เช่น สาย/ช่องกล้องต้องผ่าน checklist แยก เพราะ IoU รวมกลบข้อผิดพลาดเล็กได้ |
| ขอบนิ่ง | motion-compensated alpha MAE ใน boundary band บน non-occluded pixels ลด >=30% เทียบ baseline ที่มี error; รายงาน valid-pixel coverage และผลรายช็อต, ถ้า baseline ใกล้ศูนย์ใช้ no-regression |
| ไม่มีเงาตาม | ตรวจ frame sequence บนพื้นดำ/ขาว; ไม่เหลือขอบวัตถุที่ตำแหน่งเก่า และ boundary F-score tolerance 2px ที่ 1080p ไม่ลด >1 percentage point บน holdout |
| จังหวะภาพ | presented source-time drift p95 <=1 output frame (33.3ms ที่ 30 FPS); ไม่เกิด error >2 frames ต่อเนื่องขณะ steady playback |
| ความลื่น | หลัง warm-up เล่นจริง 3 รอบของ BLU01, dropped/pending presentations <1% ของ expected frames และไม่มี blank cutout ที่รอยต่อเมื่อ preload สำเร็จ |
| Seek | script ชุดเดิมอย่างน้อย 100 จุด forward/backward; warm seek p95 <=200ms และอย่างน้อยดีขึ้นจาก baseline เมื่อ baseline ไม่ถึงเกณฑ์; cold start แยกรายงาน |
| ความตรง | เทียบ master Canvas กับ FFmpeg source PTS เดียวกัน: alpha IoU >=0.99 หลัง normalize พิกัด/ขนาดและ threshold 0.5; soft-alpha/edge-band error รายงานแยก, RGB ไม่บังคับ bit-exact ข้าม codec |
| ทรัพยากร | ตั้งต้นงบ worker เพิ่มไม่เกิน 4 GiB RSS บนเครื่องนี้; ตรวจร่วมกับ editor เปิดอยู่และไม่มี memory โตตามคลิปไม่สิ้นสุด; หากโมเดลเกินงบต้องเปลี่ยน config/engine |
| ประมวลผล | รายงาน sec/source-sec, startup, peak memory และ storage ต่อ engine; ยังไม่กำหนดเปอร์เซ็นต์เร็วขึ้นจนมี Q0 |

ใช้ frame callback และ PTS ตรวจ presentation จริง ไม่ใช้จำนวน requestAnimationFrame แทนเฟรมวิดีโอ. ทดสอบ speed 0.5/1/1.3155/2 และค่าขอบเขตที่ UI รองรับ รวม paused seek และ loop. ลด error temporal ต้องไม่เกิดจาก mask ว่างหรือหยุดภาพ; ใช้ spatial/subject gates ประกบเสมอ.

## 5. งานชุดแรกที่พร้อมนำไปทำ

1. Q0 benchmark/ground truth และเก็บขอบเขต subject ของ BLU01.
2. Q1 playbackRate/controller พร้อม regression ที่จับ repeated-seek และ wrong-time foreground.
3. Q1 alpha proxy จาก master พร้อมตรวจ frame mapping และ scoped cleanup; ประสาน source-proxy plan ที่มีอยู่.
4. Q2 motion compensation/scene reset A/B แล้วส่งรายงานก่อนเปลี่ยนค่า default.
5. Q3 engine spike → เลือกจากผลจริง → Q4 correction workflow → Q5 rollout.

โมดูลใหม่ที่เสนอให้แยกตามหน้าที่: `frontend/src/lib/cutoutVideoPlayback.js`, `scripts/cutout_temporal.py`, `scripts/cutout_quality.py`, `scripts/cutout_engines/`. อ่านกฎและการแก้ไขร่วมปัจจุบันอีกครั้งก่อนสร้างไฟล์จริง; รอบนี้เป็นเอกสารแผนและไม่ได้ติดตั้งโมเดล แก้โค้ด หรือย้าย BLU01 เพิ่ม.
