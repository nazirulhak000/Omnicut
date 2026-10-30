# 📱 TikTok Studio Batch Auto-Post SOP & Automation Architecture

> **คู่มือมาตรฐานการปฏิบัติงาน (Standard Operating Procedure)** สำหรับการอัปโหลดวิดีโอแบบกลุ่มอัตโนมัติบน TikTok Studio ผ่าน CDP Automation

---

## 📌 1. ภาพรวมระบบ (Architecture Overview)

ระบบ Batch TikTok Uploader ออกแบบมาเพื่อจัดการคิววิดีโอใน `scripts.schedule_store` และดำเนินการอัปโหลดบนเบราว์เซอร์ Google Chrome ของผู้ใช้โดยตรง (Real User Session) เพื่อหลีกเลี่ยงระบบ Captcha และการยืนยันตัวตนซ้ำซ้อน

```
[scripts.schedule_store (Queue DB)]
                 │
                 ▼
     [tools/run_batch_upload.py]
      (Quota Allocator & Rate Limiting)
                 │
                 ▼
    [tools/batch_tiktok_uploader.py]
     (CDP Automation & Event Bridge)
                 │ (Chrome DevTools Protocol via open-browser-use)
                 ▼
      [Google Chrome User Tab]
    https://www.tiktok.com/tiktokstudio/upload
```

---

## 🎯 2. กฎการจัดสรรโควตา (Quota Allocation Rules)

| แบตช์ | โหมด | จำนวน | เงื่อนไข / พฤติกรรม |
|---|---|---|---|
| **Batch 1** | **Schedule** (ตั้งเวลา) | 30 คลิปแรก | ตั้งเวลาโพสต์ตามวันและเวลาที่กำหนดในคิว (ปัดเศษ 5 นาที)<br>TikTok Studio รองรับสูงสุด 30 รายการ |
| **Batch 2** | **Save Draft** (แบบร่าง) | 30 คลิปถัดไป | อัปโหลดคลิป, พิมพ์แคปชัน, แนบสินค้า, ใส่ปก และกด **บันทึกเป็นแบบร่าง** |
| **Batch 3** | **Untouched** (พักคิว) | คลิปที่เหลือ | คงสถานะ `status: 'planned'` ในฐานข้อมูล ไม่ดำเนินการใดๆ |

---

## ⚙️ 3. กลไกการทำงานระดับ Low-Level (Step-by-Step Flow)

1. **เตรียมหน้าอัปโหลด (`navigate_to_upload`)**:
   - นำทางไปที่ `https://www.tiktok.com/tiktokstudio/upload`
   - ตรวจจับปุ่ม **`Discard` / `ละทิ้ง`** เพื่อเคลียร์ดราฟต์ที่ยังบันทึกไม่เสร็จจากรอบก่อนหน้า
2. **ส่งไฟล์วิดีโอ (`DOM.setFileInputFiles`)**:
   - สแกนหาโหนด `input[type="file"]` จาก Document Root และส่ง Absolute Path ของไฟล์ MP4
   - รอจนกระทั่ง Badge ข้อความเปลี่ยนเป็น **`Uploaded` / `100%`**
3. **กรอกข้อมูลและแฮชแท็ก (`type_caption`)**:
   - แทรกข้อความลงใน `[contenteditable="true"]`
   - กระตุ้นอีเวนต์ `Input.insertText` เพื่อให้ React State อัปเดตสมบูรณ์
4. **ผูกสินค้า Affiliate ตะกร้าส้ม (`attach_product_link`)**:
   - คลิกเลือกหมวดหมู่ **Showcase** (สินค้าในตู้โชว์)
   - ค้นหาด้วย **Product ID** (19 หลัก)
   - เลือก Radio row และกด Next
   - ตั้งชื่อสินค้าสำหรับตะกร้า (Cart Display Name) 30 ตัวอักษร
   - กดยืนยันบันทึกสินค้า
5. **อัปโหลดภาพปกกำหนดเอง (`upload_cover`)**:
   - เปิดหน้าต่าง Cover Editor
   - คลิกแท็บ "อัปโหลดภาพปก"
   - ส่งภาพปก 3:4 ผ่าน `DOM.setFileInputFiles`
   - รอ Preview Canvas โหลด และกดปุ่ม **`บันทึก` / `ยืนยัน`**
6. **ตั้งเวลาโพสต์ (`switch_to_schedule_mode`)**:
   - เลือกเรดิโอ Schedule
   - ใส่ วันที่ และเลือก เวลา (ช่วงละ 5 นาที)
7. **ส่งแบบฟอร์มและดักจับ Popups (`submit_clip`)**:
   - คลิกปุ่ม Schedule หรือ Save draft ด้วย Native CDP Mouse Event
   - ดักจับป๊อปอัป **`Post now` / `โพสต์เลย`** (Copyright / Check Confirmation) และกดยืนยันอัตโนมัติ
   - ดักจับ Navigation Guard **`Leave` / `ออก`**
   - รอจนหน้าต่างนำทางไปที่ `tiktokstudio/content` หรือแสดง Platform Success Toast

---

## 🛠️ 4. คำสั่งปฏิบัติงาน (Operator Commands)

### ตรวจสอบแท็บ Chrome
```bash
node "C:\Users\nazir\AppData\Roaming\npm\node_modules\open-browser-use\cli\open-browser-use.js" user-tabs
```

### เริ่มทำงาน Batch Runner
```bash
.venv\Scripts\python.exe -u tools/run_batch_upload.py
```

### ตรวจสอบคิวในระบบ
```bash
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, '.'); from scripts.schedule_store import ScheduleQueueStore; items = ScheduleQueueStore.list_items(); print('Posted:', len([c for c in items if c.get('status') == 'posted'])); print('Draft:', len([c for c in items if c.get('status') == 'draft'])); print('Planned:', len([c for c in items if c.get('status') == 'planned']))"
```

---

## 🛡️ 5. กฎเหล็กด้านความปลอดภัย (Safety & Stability Guards)

- **ห้ามส่ง `.click()` ลอยๆ**: ต้องใช้ `Input.dispatchMouseEvent` สำหรับปุ่มที่เป็น React Component
- **ห้ามข้าม Cooldown**: ต้องเว้นระยะอย่างน้อย 20 วินาทีระหว่างแต่ละคลิป เพื่อให้ TikTok ประมวลผลและเคลียร์ Background Web Worker
- **ห้ามรันขนานกันหลายโพรเซสบนแท็บเดียวกัน**: 1 แท็บ Chrome รองรับการทำงานแบบ Sequential 1 คลิปต่อรอบเท่านั้น
