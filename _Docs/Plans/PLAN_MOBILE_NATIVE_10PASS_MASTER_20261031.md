# 📱✨ แผนแม่บทแปลงโฉมสู่ Native Mobile App 100% จากการสวมบทบาทผู้ใช้ 10 มิติ
## (10-Pass Real-User Scrutiny & Native Mobile App Masterplan — iPhone 15 Pro Max)

- **วันที่:** 2026-10-31
- **ดำเนินการโดย:** Antigravity (Gemini 3.8 Flash)
- **ทักษะกำกับ:** `/impeccable` (Peak visual craft), `/ui-ux-pro-max` (Apple HIG standards), `/scrutinize` (Outsider intent & reality tracing)
- **อุปกรณ์เป้าหมายหลัก:** iPhone 15 Pro Max (430 × 932 pt, 120Hz ProMotion, Dynamic Island 59pt, Home Bar 34pt, iOS Safari / PWA)

---

## 🎭 1. ผลการสวมบทบาทผู้ใช้งานจริง 10 รอบ (10-Pass Deep Scrutiny)

### Pass 1: First-Run & PWA Launch (เปิดแอปครั้งแรก / เข้าหน้าจอโฮม)
- **สถานการณ์:** แตะไอคอน OmniCut บนหน้าจอโฮมของ iPhone
- **สิ่งที่พบ:** ไม่มี Splash Screen นุ่มนวล, แถบสถานะด้านบนยังกลืนกับขอบจอไม่สนิท
- **การยกระดับ:** เพิ่ม Apple Touch Icon คมชัด 512px, ติดตั้ง Splash Screen สไตล์ Dark Frosted Glass, กำหนด `apple-mobile-web-app-status-bar-style: black-translucent`

### Pass 2: Thumb-Zone & Reachability (การถือมือเดียวด้วยนิ้วโป้ง)
- **สถานการณ์:** เดินถือโทรศัพท์มือเดียว นิ้วโป้งกวาดได้เฉพาะโซนล่าง 40%
- **สิ่งที่พบ:** ปุ่มบางอย่างยังอยู่ด้านบน เช่น ปุ่มปิด Modal หรือปุ่มย้อนกลับ
- **การยกระดับ:** ทำ Bottom Sheet ปัดลงปิดได้ (Swipe down to dismiss), ย้าย Action หลักมาเป็น Floating Thumb Bar เหนือ Tab bar

### Pass 3: Intake Journey (วางลิงก์สินค้า TikTok Shop)
- **สถานการณ์:** เจอสินค้าใน TikTok กด Share แล้วสลับมา OmniCut
- **สิ่งที่พบ:** ต้องกดแตะที่ช่องแล้วค่อย Paste เอง
- **การยกระดับ:** ทำปุ่มใหญ่เต็มมือนิ้วโป้ง `วางลิงก์จากคลิปบอร์ด` (ใช้ `navigator.clipboard.readText()`) แตะปุ๊บ สกัดชื่อสินค้าและรูป Hero อัตโนมัติใน 1 วินาที

### Pass 4: Script Review Deck (ตรวจสคริปต์ 20 บท)
- **สถานการณ์:** นอนตรวจบทบนเตียง ปัดอ่านทีละบท
- **สิ่งที่พบ:** การเลื่อนดู 20 บทยังเป็นลิสต์ยาว ต้องกวาดนิ้วเยอะ
- **การยกระดับ:** แปลงเป็นการ์ดเต็มจอ `100dvh` สไตล์ Stories/Tinder แตะ `อนุมัติ` แล้วเด้งไปบทถัดไปพร้อมแอนิเมชันสปริง และแถบ Undo 5 วินาที

### Pass 5: Production Job Tracking (สั่งผลิต 20 คลิป)
- **สถานการณ์:** กด "ผลิต 20 คลิป" แล้วพับหน้าจอไปคุย LINE
- **สิ่งที่พบ:** กังวลว่างานจะหลุด หรือไม่รู้ว่าถึงขั้นตอนไหน
- **การยกระดับ:** Realtime SSE Card แสดงสเตจ (พากย์เสียง -> ถอดคำ -> ประกอบร่าง -> เรนเดอร์) พร้อม ETA นาที และส่ง Notification แจ้งเตือนเมื่อเสร็จ

### Pass 6: Video QC & Preview Player (ตรวจคลิปก่อนเผยแพร่)
- **สถานการณ์:** ตรวจดูว่าซับขึ้นตรงไหม การ์ดท้ายคลิปสวยไหม
- **สิ่งที่พบ:** เครื่องเล่นวิดีโอต้องแตะหลายทอดกว่าจะเปิดดู
- **การยกระดับ:** ฝังวิดีโอ 540p Proxy เล่นทันทีเมื่อเลื่อนมาถึง (`playsInline`, `muted` autoplay loop แบบ TikTok), แสดงภาพเปรียบเทียบแชท + การ์ด CTA คู่กัน

### Pass 7: Mobile Clip Library (คลังคลิปแนวตั้ง)
- **สถานการณ์:** เปิดดูคลิปทั้งหมดในเครื่องที่พร้อมโพสต์
- **สิ่งที่พบ:** เลย์เอาต์ตารางแบบเดิมดูแน่นเกินไปบนจอมือถือ
- **การยกระดับ:** จัดกริด 3 คอลัมน์ อัตราส่วน 9:16 การ์ดขอบมน 2xl มีป้ายสถานะสีนีออนชัดเจน แตะค้างเพื่อเลือกหลายคลิปพร้อมกัน

### Pass 8: Save to Camera Roll (บันทึกลง Photos)
- **สถานการณ์:** อยากเซฟคลิปเข้าเครื่อง iPhone เพื่อดูในแอพ Photos
- **สิ่งที่พบ:** กดดาวน์โหลดแล้วบางครั้งติดหน้าต่าง Safari ถามว่าจะเปิดหรือโหลด
- **การยกระดับ:** ใช้ Web Share API (`navigator.share({ files })`) ยิงตรงเข้า iOS Share Sheet ให้ผู้ใช้แตะ "Save Video" เข้า Photos ได้ในเสี้ยววินาที

### Pass 9: TikTok 1-Click Posting (โพสต์คลิปตามตาราง)
- **สถานการณ์:** ถึงเวลา 18:00 น. ได้เวลาโพสต์คลิป
- **สิ่งที่พบ:** ต้องจำว่าสินค้าชื่ออะไร และติดแฮชแท็กอะไรบ้าง
- **การยกระดับ:** การ์ด "คลิปถัดไป" มีปุ่ม 1-Click: ก๊อปปี้แคปชัน + แฮชแท็กเข้าคลิปบอร์ดทันที พร้อมคัดลอกรหัสสินค้า TikTok Shop และเปิดแอป TikTok ให้ทันที

### Pass 10: Native Feel & Haptic Polish (สัมผัสระดับแอปแท้)
- **สถานการณ์:** ดีไซเนอร์ระดับรางวัลจับสัมผัสความรู้สึกลื่นไหล
- **สิ่งที่พบ:** ยังมีอาการกระตุกและขาดแรงสะท้อนเมื่อแตะปุ่ม
- **การยกระดับ:** ใส่ Haptic Feedback (`navigator.vibrate?.([10])`) ทุกครั้งที่กดปุ่มหลัก, ใส่ Elastic Spring Physics `cubic-bezier(0.34, 1.56, 0.64, 1)` และล็อกหน้าจอ 100dvh ไม่ให้เลื่อนหลุดขอบ

---

## 🛠️ 2. แผนแม่บทปรับปรุงสถาปัตยกรรม (Native Mobile App Architecture)

1. **Native Tab Bar (Frosted Glass Bottom Navigation):**
   * พื้นหลังโปร่งแสง `#07090E/85` เบลอ 24px (`backdrop-blur-2xl`)
   * ป้ายไฟนีออน Active Indicator สี Cyan `#25F4EE`
   * ระยะขอบล่างรับ Home Indicator ของ iPhone (`env(safe-area-inset-bottom)`)
2. **Floating Dynamic Toast Capsule:**
   * เลิกใช้ Toast ลอยล่างที่บังปุ่ม เปลี่ยนเป็น Dynamic Capsule เลื่อนลงมาจาก Dynamic Island ด้านบน (`top-[calc(env(safe-area-inset-top)+8px)]`)
3. **Bottom Sheets with Gesture Drag Handle:**
   * Modal ทุกอันกลายเป็น Bottom Sheet สไตล์ iOS มีขีดจับตรงกลาง (Drag Handle) รูดลงเพื่อปิดได้ทันที
4. **Input 16px Enforcement:**
   * ทุกช่อง Input มีขนาดฟอนต์ 16px ป้องกันไม่ให้ Safari ซูมหน้าจอเอง
