# แผนเปลี่ยนช็อต HOY01 หลังตรวจภาพจริง
ดำเนินการโดย: Codex (GPT-6)
Round: CODEX-HOY01-MODEL-AND-SHOT-PLAN-20261004
วันที่: 2026-10-04
สถานะ: เตรียม candidate แล้ว; รอยืนยัน exact variant/วิธีติดตั้งก่อนนำไปใช้

## ปัญหาและผลที่ต้องการ
ช็อต3ในสองโปรเจกต์ใช้ภาพถาด/กล่องระหว่างบทแนะนำการติดหลังมือถือ แผนนี้เสนอภาพการใช้กับมือถือจากไฟล์เดิม โดยรักษาความเร็ว ความยาว transition และเสียงเดิม แต่การเห็นอุปกรณ์หนีบทำให้ยังไม่ยืนยันคำว่าแม่เหล็ก ห้าม applyอัตโนมัติ

## Candidate ที่มีข้อมูลครบสำหรับทดลอง
| โปรเจกต์ | ช็อต | Source เดิม | Source candidate | Speed เดิม | ความยาวภาพตามspeed | Frame-grid timeline end ก่อน/หลัง |
|---|---|---|---|---|---|---|
| HOY01-รีวิวสเปก_1 | 3 | 0–6.692s | 180.0–186.692s | 1.121 | 5.96967s | 35.200000s = 35.200000s |
| HOY01-เทียบของเดิม_1 | 3 | 0–6.673s | 169.75–176.423s | 1.0662 | 6.258676s | 27.233333s = 27.233333s |

Source: `01_Raw/673882d55bd84c57ba805000a910c466/Hoyaup.mov`
สองcandidateไม่ทับช่วงsourceที่ช็อตอื่นใช้ในโปรเจกต์ของตัวเอง ตรวจด้วยการคำนวณช่วงในmanifest ไม่อ้างว่าภาพทุกช่วงไม่ซ้ำในเชิงการเคลื่อนไหว

## สิ่งที่ภาพ candidate รองรับ
ภาพ coolerอยู่หลังโทรศัพท์ มีRGBและdisplayให้เห็น sampledทุก0.75sในช่วง169–175.75และ180–186.75 ไม่ใช้ภาพนี้พิสูจน์magnetic retention, airflow direction, AI control, wattage, weightหรือความเงียบ

## ลำดับนำไปใช้เมื่อข้อมูลรุ่นชัด
1. ยืนยัน variant/mountingและกำลังไฟจากหลักฐานตรงเครื่อง แยกseller claimออกจากผลวัด
2. ถ้าบทแม่เหล็กตรงรุ่นจริง เลือกภาพที่สาธิตวิธีติดตรงคำพูด ถ้าภาพcandidateมีแต่แขนหนีบ ต้องใช้ภาพอื่นที่ตรงหรือแก้บทเป็นงานแยก ไม่หลบแขนหนีบด้วยcropเพื่อทำให้ดูเป็นmagnetic demo
3. ตรวจsourcecandidateครบทุกเฟรมรวมscene cut/ต่างชาติฝัง/action และsampleที่head/tail handleของtransition ไม่อ้างว่าsample0.75sแทนcontinuous acceptanceได้
4. ทดลองในพื้นที่ชั่วคราว ใช้hash/revision guardก่อนนำmetadataเข้า editor รักษาspeed/duration/keyframes/transitions/audio/fontทั้งหมด; ตรวจtransformเดิมกับตำแหน่งสินค้าใหม่และsource handlesก่อนapply
5. ตรวจproduction Preview/Renderคู่กันทั้งช่วงบทและรอยต่อ เฟรม/เสียง/การค้างภาพถูกต้อง แล้วนำผลที่ผ่านไปแก้manual timelineภายใต้ขอบเขตที่ผู้ใช้สั่ง

## ขอบเขตที่ยังไม่ได้ทำ
ไม่แก้ภาพhookที่พูดพัดลมแบบเก่า: ต้องมีภาพตัวเก่าที่ถูกประเภทและไม่สับสนรุ่น ไม่ใช้ภาพHOYAUPใหม่แทนของเก่า
ไม่เปลี่ยนบท24Wเป็น20Wอัตโนมัติ เพราะรูปแนบร้านขัดกันเอง
ไม่เพิ่มcallout/เปลี่ยนฟอนต์หรือเสียงเพื่อกลบภาพไม่ตรงบท

## การตรวจแผน
JSONคู่กันเก็บexpected_manifest_sha256, source_sha256, original/proposedspans, speed, endpointก่อน/หลัง, unsupported_claimsและapply=false เปลี่ยนtrimในdeepcopyแล้วเรียกproduction `audit_manifest()` ตรวจendpointเท่ากัน2โปรเจกต์; ไม่สร้างprojectcopyหรือrenderและไม่แก้ข้อมูลจริง
ดูหลักฐานรุ่นและURLภาพร้านที่ `_Docs/Reports/HOY01_MODEL_VERIFICATION_20261004.md`

## Execution 2026-10-04 ? Codex (GPT-6)

Applied both clip3 candidates after user confirmation of matching variant, dual mounting,24W and AI. Original findings remain historical; confirmation is not an independent measurement. Backups and final verification: `_Docs/Reports/HOY01_PHONE_SHOTS_APPLIED_20261004.md`. JSON apply flags remain false to prevent accidental replay.
