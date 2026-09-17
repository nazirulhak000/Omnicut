---
target: ScheduleAgenda
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
timestamp: 2026-09-17T15-37-26Z
slug: frontend-src-components-scheduleagenda-jsx
---
โ⚠️ DEGRADED: single-context (ไม่มี sub-agent tool ใน session นี้)

## Design Health Score

| Heuristic | Score | Key issue |
|---|---:|---|
| Visibility of system status | 3/4 | มีวันปัจจุบัน จำนวนคิว และสถานะมุมมอง แต่สิ่งที่ต้องทำถัดไปยังไม่เด่น |
| Match with real world | 3/4 | มีคำว่า วันนี้/สัปดาห์/เวลาโพสต์ แต่โครงสร้างยังเหมือน tracker มากกว่ารันชีต |
| User control and freedom | 3/4 | มี list/calendar, เพิ่ม, ลากย้าย และ refresh แต่คำสั่งสำคัญกระจาย |
| Consistency and standards | 3/4 | ภาษาภาพรวมดี แต่ปุ่มจำนวนมากมีน้ำหนักเท่ากัน |
| Error prevention | 2/4 | backend มี guard ที่ดีแล้ว แต่ UI ยังไม่สรุปกติกาก่อนจัดคิวให้ชัด |
| Recognition rather than recall | 2/4 | ต้องจำความหมายของปุ่มและตัวกรองหลายชั้น |
| Flexibility and efficiency | 4/4 | มี automation, bulk, calendar และ template ครบ |
| Aesthetic and minimalist design | 2/4 | ข้อมูลชั้น tracker, filter และ queue แย่งพื้นที่/ความสนใจ |
| Error recovery | 2/4 | มี empty state แต่ยังไม่บอก action ที่เหมาะที่สุดจากสถานะนั้น |
| Help and documentation | 2/4 | มีคำอธิบายเล็กน้อย แต่กติกากันซ้ำ/สถิติยังอยู่ไกลจากจุดตัดสินใจ |
| **Total** | **26/40** | **Acceptable: โครงสร้างใช้งานได้ แต่ควรลด cognitive load ก่อนเพิ่มฟีเจอร์ต่อ** |

## Overall impression

หน้าปัจจุบันมีความสามารถครบ แต่ยังให้ความรู้สึกเป็น “หน้ารวมระบบผลิตคลิป” มากกว่า “โต๊ะทำงานสำหรับจัดคิววันนี้” จุดที่คุ้มที่สุดคือทำให้ Today เป็นศูนย์กลาง และย้ายรายละเอียดที่ไม่เกี่ยวกับการตัดสินใจรอบนั้นไปไว้ใน progressive disclosure.

## Priority issues

### [P1] สิ่งที่สำคัญที่สุดไม่เด่นพอ

จำนวน tracker 4 phase, search, product chips, filter, queue actions และ calendar ปรากฏพร้อมกัน ขณะที่ผู้ใช้ต้องตอบคำถามง่าย ๆ ว่า “วันนี้ต้องโพสต์อะไรบ้าง”

Fix: แยกหน้าเป็น 3 ระดับชัดเจน: Today summary, queue workspace, advanced filters. ให้ primary action เหลือ `จัดคิวอัตโนมัติ` และ secondary action เหลือ `เพิ่มคลิป`; ย้าย `เพิ่มเป็นชุด`, template, posted และ refresh เข้าเมนู `เพิ่มเติม`.

### [P1] มีตัวกรองสินค้าซ้ำซ้อนสองชุด

ด้านบนมี dropdown สินค้าและแถบ chip สินค้าจำนวนมาก ขณะเดียวกัน queue ยังมีตัวกรอง/มุมมองของตัวเอง ทำให้ผู้ใช้ไม่แน่ใจว่าตัวกรองไหนกำลังมีผล

Fix: ใช้ filter bar เดียว พร้อมแสดง active filter เป็น chip ที่ลบได้ และมีปุ่ม `ล้างตัวกรอง`. ถ้าต้องการเลือกสินค้าเป็นทางลัด ให้แสดง 5 อันดับล่าสุด/ใช้บ่อย แล้วซ่อนที่เหลือใน dropdown.

### [P1] Auto-fill ควรเป็น flow 2 ขั้นที่สั้นลง

modal ปัจจุบันมีช่วงวันที่, สินค้า, จำนวนคลิป, สถิติ, preview และเหตุผลอยู่ในพื้นที่เดียวกัน ทำให้การตัดสินใจหลักถูกกลบ

Fix: ขั้นที่ 1 เลือกขอบเขต (วันนี้/สัปดาห์นี้/กำหนดเอง) + จำนวนคลิป + toggle สถิติ; ขั้นที่ 2 แสดงผลลัพธ์พร้อม summary card: จัดได้กี่คลิป, ข้ามเพราะอะไร, เวลาเด่น, กติกาที่ใช้. แสดง rule chips ตั้งแต่ต้น เช่น `ไม่ซ้ำสินค้าในวันเดียวกัน` และ `ไม่ซ้ำสี Hook ในวันเดียวกัน`.

### [P2] Empty state ยังไม่ช่วยให้เริ่มงาน

ข้อความ “ยังไม่มีคลิป” บอกสถานะ แต่ไม่บอกว่าควรกดอะไรต่อ และไม่แสดงจำนวนคลิปที่พร้อมจัดคิว

Fix: เปลี่ยนเป็น `วันนี้ยังไม่มีคิว` พร้อม 2 CTA: `จัดคิวอัตโนมัติจากคลิปที่พร้อม` และ `เพิ่มคลิปเอง` พร้อมแสดง `มีคลิปพร้อมจัด X คลิป`.

### [P2] สีและปุ่มมีน้ำหนักมากเกินไป

เส้น cyan และปุ่มขอบจำนวนมากทำให้ทุกอย่างดูสำคัญเท่ากัน และ detector พบ gray-on-color warnings หลายจุดใน component เดิม

Fix: ใช้ cyan เฉพาะ primary action/current state, ใช้ neutral สำหรับ secondary, ใช้สี semantic เฉพาะ status. เพิ่ม contrast ของข้อความรองบนพื้นสี และลด border ที่ไม่จำเป็น.

## Recommended target layout

1. Header: `คิววันนี้` + วันที่ + จำนวนคลิป + ช่องถัดไป + สถานะความเสี่ยง
2. Action bar: `จัดคิวอัตโนมัติ` / `เพิ่มคลิป` / `เพิ่มเติม`
3. Workspace tabs: `วันนี้` / `สัปดาห์` / `รายการทั้งหมด`
4. One compact filter row: ค้นหา, สินค้า, สถานะ, ล้างตัวกรอง
5. Main queue: group by day, time เป็นจุดนำสายตา, product/hook/color/status เป็นข้อมูลรอง
6. Advanced drawer: stats, rules, weekly template, posted history

## Persona red flags

- Alex (power user): ทำงานได้หลายแบบ แต่ต้อง scan ปุ่มและ filter มากเกินไปก่อนเริ่ม automation; bulk/template ควรอยู่ในเมนูเดียวและมี shortcut ไป Today.
- Jordan (first-timer): `จัดคิวอัตโนมัติ`, `เพิ่มเป็นชุด`, `ตั้งค่าเวลารายสัปดาห์` ต่างกันอย่างไรยังไม่ชัดจากหน้าหลัก; ต้องมีคำอธิบายสั้นใต้เมนูหรือเมนูเพิ่มเติม.
- Sam (keyboard/accessibility): ความหมายของสี Hook และ status ไม่ควรพึ่งสีอย่างเดียว; ควรมีข้อความ badge, focus order เดียวกับ visual order และ live announcement หลังจัดคิวสำเร็จ.

## Questions to consider

- ถ้าเปิดหน้านี้ทุกเช้า สิ่งเดียวที่อยากเห็นใน 5 วินาทีแรกคือ “คิววันนี้” หรือ “คลิปที่พร้อมจัด”?
- ต้องการให้ระบบเลือกเวลา/สินค้าให้อัตโนมัติเป็นค่าเริ่มต้นเลย หรืออยากเห็นกติกาก่อนทุกครั้ง?
- `ตารางข้อมูล` จำเป็นต้องอยู่ในหน้าเดียวกับ run sheet หรือควรเป็นโหมด advanced?
