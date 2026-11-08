# 📋 แผนปฏิบัติการลูปตรวจเช็ก 10 รอบ (OmniCut Pro Studio 10-Round Unslop Audit Pass 2)

> **วันที่จัดทำ:** 2026-11-09  
> **ดำเนินการโดย:** Antigravity (Gemini 2.5 Pro)  
> **อ้างอิงมาตรฐาน:** `/unslop` Skill (Damir Sokolovsky, CC-BY-4.0)  
> **ขอบเขต:** ตรวจสอบความประณีตระดับงานฝีมือ (Craft & Visual Integrity) ขจัด Vibecoded Slop ที่ยังหลงเหลืออยู่ใน Modals, Secondary Hubs, Typography, Emojis, และ Spacing ทั่วทั้งระบบ

---

## 🎯 1. ทิศทางการออกแบบ 5 บรรทัด (Design Direction)

- **Product:** OmniCut Pro Studio — ระบบอัตโนมัติผลิตคลิปวิดีโอ 9:16 (1080x1920) สำหรับครีเอเตอร์และนายหน้า Affiliate TikTok
- **Character:** `exact, technical, calm` (ไม่อนุญาตคำว่า clean/modern/sleek/premium ตามกฎเกณฑ์ของสกิล)
- **World:** Broadcast editing suite & dark post-production studio (DaVinci Resolve / Baselight), พื้นผิว graphite neutral (#0A0D14), ขอบ hairline บางเบา, ปราศจากหมอกแสงเรือง
- **Moments:** จอแสดงผลวิดีโอ 9:16 พร้อมเส้น Safe Zone ชัดเจน และไทม์ไลน์คลื่นเสียง Multi-Track Waveform
- **Signature:** ป้ายสัดส่วนกรอบวิดีโอ 9:16 และตัวเลขอ่านรหัสเวลา (Timecode) ระดับมิลลิวินาที

---

## 🔍 2. สรุปผลการสแกนเบื้องต้น (Signs of Slop Found)
- **Emoji ใน UI Text:** ตรวจพบ 189 จุด (เช่น `🔥 คลิปปัง`, `✨ AI Studio`, `🎉 QC ผ่าน`)
- **Gradients ฉูดฉาด:** ตรวจพบ 177 จุด (ส่วนใหญ่ใน Modals และ Activity Center)
- **Neon Glow Shadows:** ตรวจพบ 46 จุด (`shadow-[0_0_20px_...]`, `shadow-[0_0_5px_currentColor]`)
- **Odd Pixel Spacings:** ตรวจพบ 3 จุด (ที่ไม่ได้ลงสเกล 4px)

---

## 🔄 3. รายละเอียดแผนลูปตรวจเช็ก 10 รอบ (The 10-Round Audit Loop)

### 🔹 Round 01: Modals & Dialogs Deep Clean
- **เป้าหมาย:** ทำความสะอาด Modal หน้าต่างย่อยทั้งหมด
- **ไฟล์เป้าหมาย:** `HookVariationModal.jsx`, `CloudArchiveModal.jsx`, `ProductMetadataModal.jsx`, `SceneCatalogModal.jsx`, `ShotListModal.jsx`
- **การดำเนินการ:** ลบ `shadow-[0_0_20px...]`, ถอด gradients แปลกปลอม, ปรับพื้นหลังเป็น `#0A0D14` ขอบ `border-white/[0.08]`

### 🔹 Round 02: Studio Agenda & Schedule Hub
- **เป้าหมาย:** ยกระดับหน้าตารางโพสต์และปฏิทินงาน
- **ไฟล์เป้าหมาย:** `ScheduleAgenda.jsx`, `ScheduleDetailModal.jsx`
- **การดำเนินการ:** ลบไฟเรืองแสง `shadow-[0_0_5px_currentColor]`, ปรับจุดแสดงสถานะเวลาให้คมชัดสไตล์ห้องออกอากาศ

### 🔹 Round 03: Activity Center & Notification Stream
- **เป้าหมาย:** ลบ Gradient หลายเฉดและ Emoji ในศูนย์กิจกรรม
- **ไฟล์เป้าหมาย:** `ActivityCenter.jsx`
- **การดำเนินการ:** เปลี่ยนแถบสีรุ้ง `from-[#D97757] via-[#FF8A65] to-[#25F4EE]` เป็น Pro Accent, เปลี่ยน `🔥 คลิปปัง` เป็นชิปกรองข้อความ `Viral`

### 🔹 Round 04: Cover Studio & Thumbnail Lab
- **เป้าหมาย:** ปรับสตูดิโอทำปก 9:16 ให้มีความคมชัด
- **ไฟล์เป้าหมาย:** `CoverStudioModal.jsx`
- **การดำเนินการ:** ถอด `✨` ออกจากป้าย AI, ปรับตัวเลือกแม่แบบปกและปุ่ม Generate ให้เป็น Solid Accent

### 🔹 Round 05: Typography & Tabular Numbers
- **เป้าหมาย:** จัดการขนาดฟอนต์ น้ำหนัก และตัวเลขตาราง
- **การดำเนินการ:** ลบ `uppercase tracking-wider` ในข้อความยาว, ปรับตัวเลขเวลา ความยาวคลิป และจำนวนนับให้ใช้ `tabular-nums` เพื่อไม่ให้ตัวเลขขยับสั่น

### 🔹 Round 06: Emoji-to-Icon Sanitation Pass
- **เป้าหมาย:** กวาดล้าง Emoji ที่ใช้ตกแต่งปุ่มและหัวข้อ (189 จุด)
- **การดำเนินการ:** แปลง Emoji เป็นไอคอนเส้นตรงชุดเดียวกัน (Lucide Icons ขนาด 16px/18px stroke 1.5) เพื่อความเป็นมืออาชีพ

### 🔹 Round 07: 4px Spacing Grid Alignment
- **เป้าหมาย:** จัดระยะห่างให้อยู่บนระบบ 4px Grid
- **การดำเนินการ:** กำจัดค่ามาร์จิ้น/แพดดิ้งเศษแปลกๆ ปรับความสูงแถวและการ์ดให้เท่ากัน (16/20/24px)

### 🔹 Round 08: Micro-Interactions & Animation Pruning
- **เป้าหมาย:** ขจัดแอนิเมชันวูบวาบส่วนเกิน
- **การดำเนินการ:** ถอด `animate-ping` และ `animate-bounce` ที่ไม่จำเป็น เปลี่ยนเป็น Transition สีเรียบเนียน 150ms

### 🔹 Round 09: Toast & Feedback System Sanitation
- **เป้าหมาย:** ปรับสำนวนข้อความแจ้งเตือนและกล่องยืนยัน
- **การดำเนินการ:** ลบคำโฆษณาชวนเชื่อ (Hype Words) และ Emoji ออกจากข้อความแจ้งเตือน ให้กระชับ สุภาพ ตรงไปตรงมา

### 🔹 Round 10: Full Regression & Visual Diff Sign-Off
- **เป้าหมาย:** ตรวจสอบความถูกต้องทั้งระบบ
- **การดำเนินการ:** รัน Vitest unit tests (1,222+ tests), Production build, Parity tests (212 tests), บันทึกภาพถ่ายหน้าจอจริงส่งมอบ
