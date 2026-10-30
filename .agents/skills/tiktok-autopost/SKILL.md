---
name: tiktok-autopost
description: Automate batch uploading, scheduling, and draft saving of video clips directly to TikTok Studio via Chrome CDP / Open-Browser-Use. Supports Showcase affiliate product linking, 3:4 custom cover upload, caption & hashtag insertion, scheduled date/time picker, and auto-dismiss of copyright/Post now modals without crashing.
---

# tiktok-autopost

ระบบอัปโหลดวิดีโอแบบกลุ่ม (Batch Auto-Post & Schedule) ขึ้น **TikTok Studio** (`https://www.tiktok.com/tiktokstudio/upload`) โดยตรงผ่านเบราว์เซอร์จริงของผู้ใช้ (Real Chrome User Session) ด้วยโปรโตคอล Chrome DevTools Protocol (CDP) ผ่าน `open-browser-use` CLI หรือ `tiktok_autopost_extension`

---

## 🎯 ความสามารถหลัก (Core Capabilities)

1. **โควตาและกลยุทธ์การโพสต์ (Quota & Strategy Management):**
   - **โหมดตั้งเวลา (Schedule Mode):** ตั้งเวลาล่วงหน้าได้สูงสุด 30 คลิปแรกตามข้อจำกัดของระบบ TikTok Studio
   - **โหมดบันทึกแบบร่าง (Draft Mode):** คลิปถัดไปที่เกินโควตา 30 คลิปแรก จะบันทึกเป็นแบบร่าง (Save draft) เพื่อรอเปิดโพสต์ในวันถัดไป
   - **โหมดพักคิว (Planned / Untouched):** คลิปที่เหลือคงสถานะ `planned` ในฐานข้อมูล `ScheduleQueueStore` โดยไม่แตะต้อง
2. **แนบลิงก์สินค้า TikTok Shop Affiliate (Showcase Product Linking):**
   - ค้นหาด้วย Product ID หรือชื่อสินค้าในหมวด Showcase
   - ตรวจจับ Radio row และเลือกแถวที่ตรงกันอัตโนมัติ
   - ตั้งชื่อสินค้าสำหรับตะกร้า (Cart Display Name) 30 ตัวอักษรตามที่ระบุในคิว
3. **อัปโหลดภาพปกกำหนดเอง (Custom 3:4 Cover Upload):**
   - เปิดหน้าต่างแก้ไขภาพปก (Cover Editor Modal)
   - สลับแท็บ "อัปโหลดภาพปก" (Upload Cover Tab)
   - ส่งพาธไฟล์ปกผ่าน `DOM.setFileInputFiles` พร้อม Trigger React Event เพื่อแสดงผลตัวอย่าง
   - ยืนยันบันทึกปก (Save/Confirm) ปิดหน้าต่าง Modal อัตโนมัติ
4. **ตั้งวันและเวลาแม่นยำ (5-Minute Increment Schedule Picker):**
   - สวิตช์ปุ่มวิทยุ "กำหนดเวลา" (Schedule Radio)
   - ป้อนวันที่ (YYYY-MM-DD) และเลือกเวลาจากดรอปดาวน์ที่ปัดเศษเป็นช่วงละ 5 นาที
5. **จัดการป๊อปอัปและคำถามยืนยันอัตโนมัติ 100% (Zero-Friction Modal Handling):**
   - **Discard Modal:** กด "ละทิ้ง" (Discard) อัตโนมัติหากมีคลิปค้างจากเซสชันก่อนหน้า
   - **Post Now Copyright Modal:** กดคลิกปุ่ม "โพสต์เลย" / "Post now" อัตโนมัติเมื่อ TikTok แสดงหน้าต่างเตือนการตรวจสอบลิขสิทธิ์
   - **Leave Site Modal:** กด "ออก" / "Leave" อัตโนมัติหากเบราว์เซอร์แสดง Navigation Guard
6. **อัปเดตสถานะและเก็บบันทึก Real-time:**
   - ซิงค์สถานะลง `ScheduleQueueStore` ทันทีที่โพสต์สำเร็จ (`status: 'posted'` หรือ `status: 'draft'`)
   - ระบบพักคูลดาวน์ (Cooldown 20 วินาที) ระหว่างคลิปเพื่อความปลอดภัยและป้องกัน Rate Limiting

---

## 📁 ไฟล์ระบบและโครงสร้างโค้ด (Components)

- **`tools/batch_tiktok_uploader.py`**:
  ไลบรารีฟังก์ชัน CDP หลัก รวบรวมคำสั่ง JavaScript และ CDP Events ทั้งหมด:
  - `navigate_to_upload(tab_id)`: เปิดหน้าอัปโหลดและเคลียร์ดราฟต์ค้าง
  - `wait_for_file_input(tab_id)`: ค้นหาโหนด `input[type="file"]`
  - `wait_for_upload_badge(tab_id)`: รอจนวิดีโออัปโหลดครบ 100%
  - `type_caption(caption, hashtags, tab_id)`: พิมพ์แคปชันและแฮชแท็กลงใน `contenteditable`
  - `attach_product_link(product_id, cart_name, tab_id)`: เปิด Showcase, ค้นหาสินค้า, เลือก และกดยืนยัน
  - `upload_cover(cover_path, tab_id)`: อัปโหลดปก 3:4 และกดยืนยันบันทึก
  - `switch_to_schedule_mode(date_str, time_str, tab_id)`: ตั้งวันและเวลาโพสต์
  - `submit_clip(mode, tab_id)`: กด Schedule / Save draft พร้อมตัวดักกด `Post now` และยืนยันผล
  - `process_single_clip(clip_item, mode, tab_id)`: ไปป์ไลน์ครบวงจร 1 คลิป
- **`tools/run_batch_upload.py`**:
  สคริปต์รันเนอร์ที่ควบคุมโควตา แบ่งแบตช์ (Schedule 30 / Draft 30 / Untouched) และเว้นระยะ Cooldown
- **`tiktok_autopost_extension/`**:
  Chrome Extension ต้นฉบับที่บรรจุ DOM Selectors ที่ผ่านการทดสอบจริง (`automation.js` และ `background.js`)
- **`scripts/schedule_store.py`**:
  Persistent JSON Store ที่จัดเก็บตารางคิวและสถานะของแต่ละคลิป

---

## 🚀 วิธีการเรียกใช้งาน (Execution Guide)

### 1. ตรวจสอบแท็บ Chrome ของผู้ใช้
ตรวจสอบว่าผู้ใช้เปิดแท็บ TikTok Studio ไว้อยู่แล้วหรือไม่ โดยรัน:
```bash
node "C:\Users\nazir\AppData\Roaming\npm\node_modules\open-browser-use\cli\open-browser-use.js" user-tabs
```
จดจำ Tab ID (เช่น `1319910107`) หาก Tab ID เปลี่ยน ให้กำหนดลงใน `DEFAULT_TAB_ID` ของสคริปต์

### 2. รัน Batch Automation
รันสคริปต์ประมวลผลแบตช์ผ่านสภาพแวดล้อม Python venv ของโปรเจกต์:
```bash
.venv\Scripts\python.exe -u tools/run_batch_upload.py
```

### 3. ตรวจสอบ Log และสถานะการทำงาน
ดูความคืบหน้าแบบ Real-time จากหน้าต่าง Terminal หรือตรวจสอบสถานะในคิว:
```python
from scripts.schedule_store import ScheduleQueueStore
items = ScheduleQueueStore.list_items()
print("Posted:", len([c for c in items if c.get('status') == 'posted']))
print("Draft:", len([c for c in items if c.get('status') == 'draft']))
print("Planned:", len([c for c in items if c.get('status') == 'planned']))
```

---

## ⚠️ กฎเหล็กและข้อควรระวัง (Strict Operational Rules)

1. **React Synthetic Events Requirement:**
   ปุ่มสำคัญบน TikTok Studio (เช่น ปุ่ม Next ใน Showcase, ปุ่ม Schedule, ปุ่ม Post now) ฟังอีเวนต์จาก React SyntheticEvent โดยตรง หากส่งเพียง `.click()` ธรรมดา บางครั้งระบบ TikTok จะไม่ตอบสนอง ต้องใช้ Native CDP Mouse Events เสมอ:
   ```python
   run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
   run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': x, 'y': y})
   run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': x, 'y': y})
   ```
2. **Strict Universal Popup Detection:**
   การดักจับปุ่ม `Post now` / `โพสต์เลย` ห้ามผูกติดกับ `role="dialog"` เพียงอย่างเดียว เนื่องจาก TikTok มีการเปลี่ยนแปลงคลาสครอบคลุม ให้ค้นหาจากทุก `button` หรือ `div[role="button"]` ที่แสดงผลอยู่บนหน้าจอ
3. **No Duplicate Scheduling:**
   ระบบจะตรวจสอบสถานะจาก `ScheduleQueueStore` ทุกครั้งก่อนเริ่มทำงาน คลิปที่มีสถานะเป็น `posted` หรือ `draft` จะถูกข้ามโดยอัตโนมัติ เพื่อป้องกันการอัปโหลดซ้ำซ้อน
4. **Encoding Guard บน Windows:**
   บนระบบปฏิบัติการ Windows ในโหมด CLI หรือ PowerShell ให้ระบุ `sys.stdout.reconfigure(encoding='utf-8')` ทุกครั้งที่สคริปต์เริ่มทำงาน เพื่อป้องกัน `UnicodeEncodeError (cp1252)` เมื่อแสดงผลข้อความภาษาไทย
5. **Strict Zero-Missing Product Link Guard (Stock & Radio Validation):**
   การค้นหาสินค้าต้องค้นหาด้วย **Product ID (ตัวเลขล้วน)** เท่านั้น และระบบต้องตรวจสอบผลลัพธ์ในตาราง หากสินค้าแสดงสถานะเป็น **`Unavailable` / `ไม่พร้อมจำหน่าย` / `สินค้าหมด (Stock 0)`** หรือปุ่มวิทยุถูก disable ไม่สามารถติ๊กได้ ระบบจะ **ยกเลิก (Abort) การอัปโหลดคลิปนั้นทันที** และรีเซ็ตหน้าจอ ห้ามกดโพสต์หรือตั้งเวลาคลิปโดยไม่มีตะกร้าสินค้าเด็ดขาด
