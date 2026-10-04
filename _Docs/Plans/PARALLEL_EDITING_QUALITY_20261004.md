# แผนรวมงานคุณภาพการตัดต่อ 3 เอเจนต์
ดำเนินการโดย: Codex (GPT-6) + 3 delegated agents (Codex GPT-6)
วันที่: 2026-10-04
Round: CODEX-PARALLEL-EDITING-QUALITY-20261004
สถานะ: ปิดรอบ — A1/A2/A3 และ root integration ผ่าน scoped tests/build/browser; รายงาน `_Docs/Reports/PARALLEL_EDITING_QUALITY_20261004.md`
Gate: ผู้ใช้อนุญาตให้ regression tests/ผลวัดจริงเป็นเกณฑ์ทั้ง confidence=null และ confidence<0.80 ในรอบนี้

| งาน | เจ้าของ | ขอบเขต | เกณฑ์ตรวจรับ |
|---|---|---|---|
| Source reuse | Codex (GPT-6), source_reuse | matcher/catalog/actual allocation | source เดิมเล่นต่อ ไม่กิน source ใน timeline gap; หมดแล้วถือเฟรม/pose ของ scene นั้น ไม่ย้อน/ไม่ใช้ pose คนละ topic; bounds และ duration ถูกต้อง |
| Preview performance | Codex (GPT-6), preview_performance | SequencePlayer และ scheduling helpers | measured baseline/after; output draw plan เทียบ production math; seek/backward/end/overlap/speed/freeze ไม่เปลี่ยน; ไม่อ้าง playback gain จาก CPU benchmark อย่างเดียว |
| Render preflight | Codex (GPT-6), render_preflight | analyzer/notice/tests | ชี้ตำแหน่งปัญหาและ seek ได้; approved shortage hold แจ้งแต่ไม่ block; unknown media duration ไม่ตีเป็นข้อมูลเสีย; ไม่มีคำอ้างตรวจ black pixels จาก metadata |
| Integration | Codex (GPT-6), root | wiring และ focused cross-feature checks | new source hold เข้า preflight ได้; preview indexed plan เลือกเฟรม/pose เดิม; reload/desktop/mobile UI ไม่ crash; runtime โหลดงานใหม่หลัง idle |

Root ดูแล TODO/HISTORY ของรอบนี้เพียงคนเดียว แต่แต่ละเอเจนต์บันทึกรายงานของตนเองใน `_Docs/Reports/` และรายงานตัวเลขจริง

Antigravity กำลังแก้ Keyframe/Trim/Transition ใน EditorShell/Inspector/Toolbar/TimelineClip/ClipInspector/timelineMath ทุกเอเจนต์ห้ามทับงานนั้น Root จะเชื่อม preflight ด้วย minimal patches ที่ไม่ทับฮังก์เดิมหลังประสาน API และตรวจไฟล์ล่าสุด

ไม่รัน full suite ทุกครั้งตามที่ผู้ใช้ขอ ใช้ focused regression, browser synthetic fixtures และ FFmpeg สั้นตามชนิดงาน; media อยู่ temporary storage และ cleanup100% เท่านั้น ไม่แก้ real production data ไม่ commit/push โดยอัตโนมัติ

Jev ก่อนเริ่ม root score0.77/confidence=null ใช้ measurement gate ตามอนุญาตเดิม คะแนนไม่ใช่ confidence แต่ละเอเจนต์ต้องบันทึก advisory ของตนและระบุหลักฐานจากเทสจริง
