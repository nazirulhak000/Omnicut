# A3 Render preflight — CODEX-PARALLEL-EDITING-QUALITY-20261004

ดำเนินการโดย: Codex (GPT-6)

ผล: เพิ่มการตรวจข้อมูลแผนก่อนเรนเดอร์ พร้อมเวลา `MM:SS.cc`, หมายเลขช็อต และปุ่มดูช่วงนั้นในไทม์ไลน์ ไม่เพิ่มขั้นตอนยืนยันใหม่

ไฟล์ที่ A3 สร้าง:
- `frontend/src/lib/renderPreflight.js`: วิเคราะห์ข้อมูลคลิปและตำแหน่งจาก `buildSegments` ซึ่งใช้ frame-grid 30 FPS ของโปรเจกต์
- `frontend/src/components/editor/RenderPreflightNotice.jsx`: แสดงข้อผิดพลาด/ข้อสังเกตและ seek; รักษา `data-footage-coverage-notice` กับจำนวนวินาทีรวมสำหรับ regression เดิม
- `frontend/src/lib/renderPreflight.test.js`: synthetic fixtures แบบ offline ในหน่วยความจำ

Integration ที่ส่งให้ root ทำใน EditorShell (A3 ไม่แก้ไฟล์ร่วม): memo `analyzeRenderPreflight({ clips: clipList, durations, segments, expectedDuration: audioDuration })`; แทน FootageCoverageNotice ด้วย `RenderPreflightNotice report={renderPreflight} onSeek={seekPlayer}`; ก่อน handleApply เริ่มงาน ให้แสดง `preflightBlockingMessage(renderPreflight)` และ return เฉพาะ `canRender === false`

พฤติกรรม:
- บล็อกเฉพาะไทม์ไลน์ว่าง, ไม่มี source_path, trim ติดลบ/กลับช่วง/ไม่ใช่ตัวเลข หรือ speed ไม่เป็นบวก/ไม่ finite
- ภาพตรงบทไม่พอที่มี `source_window_exhausted` รายงานช่วง freeze_tail หลัง speed/transition และจำนวนวินาทีจริงที่ถูก clamp ไม่เกิน 10 วินาที ภาพค้างตามแผนยังผ่าน render
- ช่วงไม่มีคลิปภาพในโครงสร้างไทม์ไลน์และปลายเสียงที่เกินภาพเป็น advisory; ใช้ union ของช่วงภาพเพื่อไม่เตือนช่วง transition overlap และตรวจช่องว่างหนึ่งเฟรมได้
- ช่วง trim เกินความยาวไฟล์ที่ metadata รายงาน หรือเลย source_window เป็น advisory
- trim_end=null และยังไม่มี source duration เป็น pending advisory; ไม่สร้าง gap หรือเวลา shortage หลังคลิปที่ยังไม่ทราบความยาว
- รายงานปัญหาเวลาไม่ถูกต้องด้วยจุดเริ่มที่ยังทราบได้ ไม่สร้างเวลาจบของช่วงที่ invalid

หลักฐานการทดสอบ:
- `node --test frontend/src/lib/renderPreflight.test.js frontend/src/lib/footageCoverageSummary.test.js`: **16 passed, 0 failed, 0 skipped** (14 ใหม่ + 2 เดิม)
- ครอบคลุม speed=2 + fade=0.4 ได้ hold 03.60–06.60, hold cap=10, manual hold, source missing ที่ 02.00–04.00, invalid trims/speeds, pending metadata, source overrun, overlap union, trailing gap, ช่องว่างหนึ่งเฟรม และ timestamp carry
- `git diff --check`: ผ่าน; มี warning LF/CRLF ของ SequencePlayer/shot_source_window ที่เอเจนต์อื่นแก้ ไม่มี whitespace error
- Production build และ browser integration ให้ root ทำหนึ่งครั้งร่วมกับงาน A1/A2 ตาม ownership; A3 ยังไม่อ้างผล browser/build ในรายงานนี้

ข้อจำกัด: ตรวจ metadata เท่านั้น ไม่พิสูจน์ว่าไฟล์มีอยู่จริง เปิด decoder ได้ หรือมีเฟรมดำจริง; source duration อาจมาจาก fallback ของ player จึงไม่ใช้ overrun เป็น hard block ภาพ/ข้อความ/ฟอนต์/เสียงและการเรนเดอร์ไม่เปลี่ยน

Jev ผ่าน `tools/jev_advisor.py`: ก่อนงาน noul=0.74 confidence=null; เปรียบเทียบหลัง focused tests noul=0.66 confidence=null ทั้งคู่ verdict=escalate ใช้ regression gate ที่ผู้ใช้อนุญาตไว้ ค่า noul ไม่ใช่ confidence และ Jev ตรวจเพียงสรุปข้อความ ไม่ได้อ่าน diff เอง

Cleanup: ไม่สร้างสื่อทดสอบ ไม่อ่าน/เขียน Raw, Assets, Projects, Exports หรือ registry จริง; ลบ `.tmp/jev_render_preflight_state.json` แล้ว ไม่ commit/push/install/restart
