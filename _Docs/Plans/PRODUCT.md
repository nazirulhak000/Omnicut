# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- ผู้ใช้หลักคือเจ้าของช่องและผู้ตัดต่อภาษาไทยที่ผลิตวิดีโอแนวตั้งด้วย OmniCut Pro Studio บนเครื่องของตนเอง
- ใน `Gadget Media` ผู้ใช้ต้องการเปลี่ยน source จากหลายแหล่งให้เป็นคลิปความรู้เชิงรีวิวที่น่าเชื่อถือ โดยหนึ่งสินค้าจบเป็นหนึ่งคลิป Master

## Product Purpose

OmniCut Pro Studio เป็นระบบผลิตวิดีโอแนวตั้งที่รวมการเตรียมเนื้อหา การตัดต่อ Timeline การ Preview การ Render และการจัดการผลงานไว้ใน workspace เดียว

`Gadget Media` เป็น workflow แยกสำหรับสร้างคลิป Gadget แบบ Organic Growth โดยให้คนดูเข้าใจสินค้า ได้ข้อมูลที่มีหลักฐาน และเห็นคุณค่าของสินค้าจนสนใจซื้อ โดยไม่ผูก workflow นี้กับตะกร้า Affiliate

## Positioning

`Gadget Media` ทำงานแบบ `1 สินค้า = 1 โปรเจกต์ = 1 คลิป Master` และเชื่อมทุกข้อความในสคริปต์กับ Source, Evidence และ Shot บน Timeline ก่อนอนุญาตให้ Render หรือเผยแพร่

## Operating Context

- ผู้ใช้ทำงานกับ source วิดีโอ Official, Press kit, คลิปที่ได้รับอนุญาต และ footage ที่ถ่ายเอง
- คลิปเป้าหมายยาว 45–60 วินาที อัตราส่วน 9:16 ความละเอียด 1080×1920 ที่ 30 FPS
- ผู้ใช้สามารถใช้หน้าตนเอง, footage สินค้าล้วน หรือรูปแบบผสม และเลือกเสียงผู้สร้างหรือ Gemini TTS ได้
- Timeline engine, Preview และ Render engine ของโปรแกรมเดิมสามารถนำมาใช้ซ้ำผ่าน adapter ได้
- การสร้างและตัดต่อ Product Video ต้องจบภายในเมนู `Gadget Media` โดยไม่พาผู้ใช้ออกไป workflow Editor เดิม

## Capabilities and Constraints

- ข้อมูล Project, Status, Source, Export และ Folder ของ `Gadget Media` ต้องแยกจาก workflow รีวิวปักตะกร้าและโปรเจกต์ Timeline เดิม
- Namespace ที่ยืนยันแล้วคือ `01_Raw/GadgetMedia/`, `03_Projects/GadgetMedia/` และ `04_Exports/Ready_to_post/GadgetMedia/`
- Source วิดีโอสำหรับงานจริงต้องเป็น native 1920×1080 หรือสูงกว่า ห้ามนำ source ความละเอียดต่ำมา upscale แล้วระบุว่าเป็น Full HD
- ทุก Source ต้องมี provenance และ rights status; Source ที่ยังไม่ผ่านสิทธิ์ใช้ทำ Private Cut ได้ แต่ห้ามเป็น Ready to Publish
- ข้อมูลจากแบรนด์ ผลทดสอบ และความคิดเห็นต้องแยกประเภทและอ้าง Evidence ได้
- หนึ่งโปรเจกต์มี Export หลาย version ได้ แต่มี Approved Master ได้เพียงหนึ่งรายการในเวลาเดียวกัน
- ปุ่มและสถานะต้องสะท้อนของจริง เช่น `in_production` ใช้ได้เมื่อมี Timeline Project ถูกสร้างแล้วเท่านั้น
- ระบบต้องรักษา Preview/Render parity และกฎ Subtitle, J-Cut, Safe Zone และ Audio ของโปรเจกต์

## Brand Commitments

- ชื่อผลิตภัณฑ์คือ `OmniCut Pro Studio`; ชื่อ workflow คือ `Gadget Media`
- ภาษาหลักของ UI และเอกสารปฏิบัติงานคือภาษาไทย โดยคงชื่อ Brand, Model และศัพท์เทคนิคภาษาอังกฤษตามต้นฉบับ
- คำสัญญาของช่องคือ “เล่าเรื่อง Gadget ให้เข้าใจง่าย ก่อนคุณเสียเงินซื้อ”
- บุคลิกเนื้อหาคือเพื่อนที่ช่วยแปลสเปก ตรวจคำโฆษณา และสรุปว่าเหมาะกับใคร

## Evidence on Hand

- แผนช่องและซีรีส์: `TIKTOK_GADGET_MEDIA_PLAN.md`
- รายงานตรวจ Source native: `GADGET_NATIVE_SOURCE_VERIFY_20260919.md`
- รายงาน Agent ด้าน Product, Script, Editorial และ Rights: `GADGET_REVIEW_AGENT_REPORT_20260919.md`
- UI และ Domain รุ่นแรก: `frontend/src/components/GadgetMediaHub.jsx`, `frontend/src/lib/gadgetMedia.js`, `scripts/api_gadget_media.py`, `scripts/gadget_media_campaign.py`
- ระบบ Timeline กลาง: `frontend/src/components/editor/`, `frontend/src/components/SequencePlayer.jsx` และ `frontend/src/lib/timelineSchema.js`

## Product Principles

1. หนึ่งคลิปเล่าเรื่องสินค้าหนึ่งรุ่นให้จบ ไม่รวมหลายสินค้าใน Master เดียว
2. หลักฐานมาก่อนคำขาย ทุก Claim ต้องย้อนกลับไปหา Source หรือระบุว่าเป็นความคิดเห็นได้
3. ความน่าซื้อเกิดจาก Benefit, Proof, Use case และคำตัดสินที่ตรงไปตรงมา ไม่ใช่การกล่าวอ้างเกินจริง
4. ใช้ Engine ร่วมกันได้ แต่ข้อมูลและ Artifact ต้องมีเจ้าของและขอบเขตชัดเจน
5. Automation ช่วยเตรียมโครงและงานซ้ำ ส่วน Final Taste และการอนุมัติ Master เป็นหน้าที่ของผู้ใช้

## Accessibility & Inclusion

- UI ต้องรองรับการใช้งานด้วย Keyboard, Focus state ที่มองเห็น และข้อความสถานะที่ไม่พึ่งสีเพียงอย่างเดียว
- Caption ต้องอ่านได้บนหน้าจอมือถือและไม่ถูกปุ่ม TikTok บัง
- การใช้หน้าและเสียง AI ต้องไม่ทำให้ผู้ชมเข้าใจผิดว่าเป็นเสียงจริงหรือเหตุการณ์จริงของบุคคลอื่น
