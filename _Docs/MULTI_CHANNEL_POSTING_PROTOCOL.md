# Multi-channel posting protocol

ดำเนินการโดย: Codex (GPT-6)

Prepare สร้าง durable job ของ channel/export เดิม; Extension claim lease แล้วตรวจบัญชีและ tab ให้ตรงก่อนทุก action. หลัง await network/storage ต้องอ่าน account และคลิก final action ใน DOM evaluation เดียวกันเพื่อปิดช่องว่างระหว่างตรวจและกด. Unknown/wrong account หยุดทันที.

Confirmation ต้องเกิดใหม่จาก attempt นี้; toast เก่าที่ค้างไม่พิสูจน์ผลโพสต์. Platform schedule accepted แยกจาก published. เมื่อ outcome กำกวม เก็บ unknown และตรวจ/ซ่อมผลก่อน ไม่ publish ซ้ำ. Lease-fenced release ใช้สำหรับ prepublish เท่านั้น ไม่ discard attempted job เพื่อเริ่มใหม่.

Callback ที่ platform published แล้วแต่ local save ล้มเหลวสามารถ retry receipt repair ได้. Repair ผูก exact export/job/channel และ queue row; ไม่แตะคิวใหม่ของ angle เดียวกัน. Export/PostLog ซ่อมได้เมื่อมี verified receipt แต่ mutable current angle ต้องผ่าน transaction CAS ตรวจ competing export ทั้ง link, mtime และ created_at. ลำดับเท่ากัน/หาย/เปรียบเทียบไม่ได้จะข้าม angle mutation อย่างปลอดภัย. ย้ายเฉพาะ companions ชื่อ export เดียวกัน; ไม่ autoarchive current project ที่ job ไม่ได้ freeze owner ไว้.

Stats ที่ไม่รู้ account อยู่ quarantine พร้อม provenance; attach/ignore/restore ไม่ย้ายข้ามช่อง. Live selector และบัญชีจริงต้องตรวจ read-only ใน cutover checklist ก่อนเปิด posting; offline tests ไม่ยืนยัน DOM ปัจจุบันของ TikTok.

อ้างอิง: [แผน](Plans/PLAN_MULTI_CHANNEL_20261010.md), [รายงาน posting](Reports/CODEX_AUDIT_POSTING_20261011.md), [รายงานรวม](Reports/CODEX_GEMINI_MULTI_CHANNEL_AUDIT_20261011.md).
