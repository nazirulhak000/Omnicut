# แผนยกระดับคุณภาพการตัด หลังหยุดขยาย Cutout
ดำเนินการโดย: Codex (GPT-6)
วันที่: 2026-10-04
สถานะ: แก้ Cutout ที่บล็อกใช้งานแล้ว; เริ่มคุณภาพการเลือกภาพตามบท

## ความคืบหน้า 2026-10-04
- ข้อ 1: hotfix พรีวิวดำและ false-stale render เสร็จ; พักเพิ่มฟีเจอร์ Cutout
- ข้อ 2: ตรวจชุด R1/R2/R3 ที่เกี่ยวข้อง 131 passed; frontend 799 passed
- ข้อ 3 รอบแรกเสร็จ: แก้ rhythmic merge ที่ทำให้ภาพหัวข้อที่สองหายเมื่อบทสั้น พรีวิว/เรนเดอร์จริงเลือกช่วงภาพตรงกันใน 48 เฟรมภายใน 1 เฟรม; full Python 2888 passed/12 skipped/54 warnings; frontend 799 passed/build ผ่าน
- รอบ source window เสร็จ: จำกัดภาพตรงบท เล่นครั้งเดียวแล้วค้างพร้อมแจ้งภาพไม่พอ; full Python 2907 passed/12 skipped/54 warnings, frontend 804 passed/build และเรนเดอร์จริง 30/60 FPS ผ่าน
- ข้อถัดไป: จังหวะตัดตามจบความคิด/พักเสียง/การเคลื่อนไหว ตรวจรับ R2 ที่มีอยู่และวัดจุดตัดกลางคำก่อนแก้เพิ่ม; All-track silence ripple และ Clipboard เป็นงานขนานของ Antigravity ให้ตรวจของเดิมก่อนทำซ้ำ
- รอบจังหวะตัด: เพิ่ม speech guard ให้ beat/motion/quiet-voice อยู่ใน J-lead 150–250 ms และรักษา short-shot lead; focused 96 passed รวม FFmpeg/production preview ไม่รัน full suite ตามคำสั่งผู้ใช้ รายงาน `_Docs/Reports/NATURAL_CUT_SPEECH_GUARD_20261004.md`
- รอบเล่าประเด็นครบ: รวม rhythmic groups ของ AI merged shot เดียวจนถึง sentence/topic boundary และให้ line/parent metadata เหนือคำลงท้าย; ตัวอย่าง 8s จาก 4 clips เป็น 1 clip; focused 109 passed รวม render/preview สามกรณี 12s รายงาน `_Docs/Reports/COMPLETE_THOUGHT_SHOTS_20261004.md`
- Explicit editorial pacing ยังใช้แผนเดิม รอบแรกแก้เฉพาะ rhythmic grouping
- รอบความลื่น: เลื่อน camera keyframes ตาม transition head handles และส่ง transition_easing ถึง preview/manifest; focused 122 passed รวม real render; รายงาน `_Docs/Reports/CAMERA_SMOOTHNESS_20261004.md`
- รอบรักษาแผน: ไม่เติม transition ทับ authored/all-cut plan; existing clip metadata และ explicit arrays sync ถึง render/preview/manifest; focused 141 passed รวม real stage render/replay; รายงาน `_Docs/Reports/AUTHORED_TRANSITION_RESPECT_20261004.md`
- รอบคุณภาพการเลือกภาพ: จำกัด diversity ให้ใช้ภาพที่มีหลักฐานตรงฟีเจอร์ก่อน; cached catalog rematch ในเครื่อง; offline gate155 passed รวม render8s240frames; รายงาน `_Docs/Reports/FEATURE_FIRST_SHOT_SELECTION_20261004.md`
- ผู้ใช้อนุญาตให้ regression/measurement เป็น gate สำหรับแผนนี้เมื่อ Jev confidence=null

## รอบ source window สั้นกว่าบท (2026-10-04)
1. ตรวจทั้ง catalog matcher และ shot allocator: catalog ยังใช้ end_time=max(start+1.8,scene_end) จึงอาจขยายเลยฉากจริงก่อนถึง allocator ต้องรักษาขอบเขตฉากตั้งแต่ต้นทาง
2. เก็บ coverage ต่อช่วงบทและ source span ที่ใช้จริง หลัง J-lead/การขยับขอบตาม motion; ไม่วัดแค่ source_start
3. ผู้ใช้เลือกค้างภาพสุดท้ายของช็อตเดิมพร้อมแจ้งภาพไม่พอ ไม่ยืดเสียงหรือเปลี่ยน speed; ยังไม่เพิ่มการค้นหาช็อตทดแทนอัตโนมัติ
4. ลง logic source bounds/cache binding, เล่นภาพครั้งเดียวแล้วค้างต่อเนื่อง, camera pose เดิม, notice และ save/load แล้ว; transition ที่ไม่มีภาพพอใช้ hard cut และ final reconciliation รวม freeze_tail
5. Acceptance ที่วัดจริง: source 30 FPS ค้างเฟรม 119 และ source 60 FPS ค้าง 238 โดยไม่เข้าฟีเจอร์ถัดไป; 8/12 วินาทีและรอยต่อคลิปค้างผ่าน FFmpeg/production preview; browser desktop/mobile reload ผ่าน; full Python 2907 passed/12 skipped/54 warnings, frontend 804 passed/build
6. รายงาน `_Docs/Reports/SOURCE_WINDOW_COVERAGE_20261004.md`; semantic model accuracy และการประเมินคลิปจริงยังไม่ใช่สิ่งที่ผลนี้รับรอง

## เป้าหมาย
รอบตรวจตามผลจริงเสร็จ: read-only audit HOY01 สองแผน, browser3sources/masteraudio, preflight falsegap/metadata fixes; รายงาน `_Docs/Reports/EDITING_VALIDATION_20261004.md` ยังไม่ยืนยันความตรงหัวข้อหรือจบความคิดจากภาพจริงเพราะไม่มี semantic/sentence metadata ให้ตรวจ และไม่ rewrite manual shots
ความคืบหน้ารอบ 3 เอเจนต์: source reuse เล่นต่อ/หมดแล้ว hold scene เดิม, preview time index/active decoder scheduling, preflight timeline + seek + render gate เสร็จแล้ว ตรวจเฉพาะส่วนตามคำขอผู้ใช้ รายงาน `_Docs/Reports/PARALLEL_EDITING_QUALITY_20261004.md`; ขั้นถัดไปประเมินคลิปจริงและการแก้มือ ไม่ขยาย Cutout

ให้คลิปเล่าเรื่องตรงบท จังหวะเป็นธรรมชาติ ภาพ/เสียง/ซับตรงกัน และลดจำนวนครั้งที่ผู้ใช้ต้องแก้มือ ไม่ใช้จำนวนเอฟเฟกต์เป็นตัวชี้วัด

## ลำดับงาน
1. ปิดบั๊กพรีวิวดำเมื่อ decoder Cutout รอเฟรมที่รอยต่อ: ภาพต้นฉบับต้องยังแสดงได้ หน้ากากที่ไม่ตรงเฟรมต้องไม่ถูกซ้อน ทดสอบเล่น/หยุด/seek และหลายความเร็ว
2. ตรวจรับงาน R1/R2/R3 ที่มีอยู่ก่อนเริ่มฟีเจอร์ใหม่ เพื่อไม่ทำซ้ำและไม่ชนไฟล์เจ้าของงาน
3. ภาพตรงความคิด: ตรวจช็อตต้น/กลาง/ท้ายประโยค เลือกช็อตตามฟีเจอร์ที่พูด ลดช่วงซ้ำหรือภาพไม่เกี่ยว และค้างภาพจนสื่อประเด็นครบ
4. จังหวะตัด: ใช้จบประโยค ช่วงพักเสียง และการเคลื่อนไหวร่วมกัน จำกัดความยาวช็อตตามเนื้อหา/สไตล์ ใช้ beat เป็นตัวช่วยเมื่อไม่ขัดบทพูด
5. ตัดช่วงเงียบอย่างครบทุกเลน: ต่อจากเจ้าของ Ripple R3 ภาพ เสียง ซับ overlays และ SFX ขยับตรงกัน ย้อนกลับได้ และ Preview/Render ตรงกัน
6. เก็บความลื่น: ตรวจ J/L lead, camera easing และรอยต่อเมื่อภาพ/เสียง/เนื้อหาผ่านก่อน ไม่เติม transition ให้ทุกจุดตัดโดยอัตโนมัติ

## วิธีตรวจรับแต่ละรอบ
- เก็บ baseline และผลใหม่จากชุดสถานการณ์เดียวกันใต้ temp storage; ไม่เขียนทับวัตถุดิบหรือ export จริง
- วัดภาพผิดหัวข้อ/ช็อตซ้ำ จุดตัดกลางความคิด ความคลาดภาพกับเสียง เฟรมดำ และจำนวนการแก้มือ แยกค่าที่วัดจริงกับความชอบผู้ดู
- ตรวจคลิปครบต้น/กลาง/ท้าย รวมเร็ว/ช้า ช็อตยาว/สั้น และรอยต่อ ใช้ playback กับ render จริงประกอบ
- เลือกแก้หนึ่งปัญหาที่มีผลต่อทั้งคลิปต่อรอบ บันทึกผลก่อนเปิดงานถัดไป ไม่อ้างเปอร์เซ็นต์คุณภาพหรือ retention โดยไม่มีการทดลอง

## ขอบเขต Cutout หลัง hotfix
พักการเพิ่ม engine/ฟีเจอร์/การเก็บขอบเพิ่มเติม รับเฉพาะบั๊กที่ทำให้พรีวิวใช้ไม่ได้ บล็อก render หรือทำให้ข้อมูลผิด ไม่แตะฟอนต์ ข้อความ raw assets หรือข้อมูลผลงานจริง

## ค่าเสียโอกาส
20 วันที่ผ่านมาคือระยะปฏิทิน ไม่มีบันทึกชั่วโมงพอให้ตีเป็นต้นทุนจริง ลำดับข้างต้นพิจารณาความถี่ที่ส่งผลทั้งคลิปและการลดแก้มือ เทียบกับ Cutout ที่ใช้เฉพาะบางช็อต ต้องวัดผลจริงก่อนเพิ่มงบงานต่อรอบ
