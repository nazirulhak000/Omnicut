# 🤖 แผน: TikTok Auto-Post Extension (Round POST-2)

แผนยาวของงานเสี่ยง — เหตุผล หลักฐาน และการตัดสินใจ
รายการงานจริงอยู่ที่ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md)

## Context

Round POST-1 (ดู `TODO.md`) แก้ friction ฝั่งไม่เสี่ยงหมดแล้ว: ปกเป็น jpg ใช้ได้จริง, reveal ไฟล์ใน Explorer,
แผง Post Studio, ปิดวงจร Posted/ พี่ยังต้องลากไฟล์เอง 1 ครั้งและกด paste แคปชั่นเอง

พี่ถามต่อว่าทำ extension ให้อัปโหลดอัตโนมัติได้ไหม คำตอบทางเทคนิคคือ **ไม่มีทางลัดที่ปลอดภัยกว่า** — เบราว์เซอร์บล็อกไม่ให้ JS
(ทั้งหน้าเว็บและ extension) ตั้งค่า `<input type=file>` ได้เอง ยืนยันจาก error ของ Chrome เอง:
"This input element accepts a filename, which may only be programmatically set to the empty string"
([Chromium mailing list](https://groups.google.com/a/chromium.org/g/chromium-html5/c/MzEmEG01N4Y))

ช่องโหว่เดียวที่มีคือ `chrome.debugger` + คำสั่ง CDP `DOM.setFileInputFiles` — **กลไกเดียวกับที่ Playwright/Puppeteer
ใช้ทำระบบทดสอบอัตโนมัติ** ([puppeteer#6688](https://github.com/puppeteer/puppeteer/issues/6688),
[chrome.debugger API](https://developer.chrome.com/docs/extensions/reference/api/debugger)) — Chrome จะโชว์แถบ
"เริ่ม debug เบราว์เซอร์นี้" ค้างตลอดเวลาที่ทำงาน ซ่อนไม่ได้

**พี่ยืนยันแล้วว่ายอมรับความเสี่ยงนี้** (2026-09-05) — แผนนี้ออกแบบให้เสี่ยงน้อยที่สุดเท่าที่ยังทำงานได้จริง

---

## 1. ความเสี่ยงจริง — แยก 2 เรื่องให้ชัด ห้ามปนกัน

### 1.1 ความเสี่ยงจากวิธีอัตโนมัติ (เรื่องที่คุยกันวันนี้)

หลักฐานที่เจอ ([instantdm.com](https://instantdm.com/blog/is-tiktok-automation-allowed),
[openhosst.com](https://openhosst.com/blog/tiktok-automation)):

> "There is no ban on 'automation' as a word — the ban is on a method: software that acts like a fake human
> instead of going through TikTok's front door. Official TikTok automation is allowed (Business Suite,
> Content Posting API). Unofficial bots are NOT: follow/unfollow scripts, auto-likes, mass comments,
> cold DM blasters, and scrapers violate ToS."

→ สิ่งที่โดนแบนคือ**พฤติกรรมปลอมเป็นหลายคน/สแปม/เก็บข้อมูลหมู่** ไม่ใช่ "มีสคริปต์ช่วยกดปุ่ม" ตรงๆ
คลิปพี่คือคลิปจริง 1 อัน โพสต์ทีละอันโดยพี่กดเอง — คนละรูปแบบกับที่นโยบายพูดถึง

**แต่ library สำเร็จรูปที่เจอ** (`tiktok-uploader`, `TikTokAutoUploader` บน PyPI/GitHub) **ต้องพึ่ง stealth plugin
ปลอมลายนิ้วมือเบราว์เซอร์** เพราะเปิด Chromium แยกต่างหากแล้วเสียบคุกกี้เข้าไป — นี่คือรูปแบบที่ระบบตรวจจับบอทของ
แพลตฟอร์มถูกออกแบบมาจับจริงๆ (ถึงต้องมี stealth plugin)

**ดีไซน์ที่เลือกในแผนนี้ต่างจากนั้น:** ใช้เบราว์เซอร์จริงของพี่ที่ **login ค้างอยู่แล้ว** ไม่เปิดแยก ไม่ import คุกกี้
ไม่ปลอมลายนิ้วมือใดๆ กดปุ่มครั้งเดียวต่อโพสต์ ไม่มีอะไรรันเองแบบไม่มีคนกด (ไม่ schedule ไม่ headless)
→ เป็น session จริง คุกกี้จริง IP จริง เครื่องจริงเหมือนพี่กดเองทุกประการ ต่างแค่ตรงจุดที่เมาส์ไม่ต้องลาก

### 1.2 ความเสี่ยงจากเนื้อหา AI (เรื่องแยกต่างหาก ไม่เกี่ยวกับวันนี้)

เจอนโยบายเปิดเผยเนื้อหา AI ของ TikTok ที่มีบทลงโทษเป็นขั้น
([auditsocials.com](https://www.auditsocials.com/blog/tiktok-ai-content-disclosure-rules-2026)) —
เตือน → ลบ+ห้ามโพสต์ 7 วัน → ระงับบัญชี 30 วัน → แบนถาวร

**คลิปของพี่มีเสียงพากย์ AI (edge-tts/Gemini) อยู่แล้ว** — เรื่องนี้มีผล**ไม่ว่าจะโพสต์ด้วยมือหรือสคริปต์**
เป็นคนละนโยบายกับเรื่องอัตโนมัติ พี่ควรเช็คว่าเนื้อหาที่ทำอยู่เข้าเกณฑ์ต้องติดป้าย AI-generated ไหม
**แผนนี้ไม่ได้แก้ปัญหานี้ให้** เขียนไว้ให้พี่รู้เฉยๆ

---

## 2. สถาปัตยกรรม

```
[Post Studio panel ในแอป]
   กด "โพสต์ TikTok อัตโนมัติ"
        │
        ▼
[Local server ในแอป]  POST /api/tiktok-autopost/prepare
   ส่ง: mp4 path (absolute), cover jpg path, caption+hashtags
        │
        ▼
[Chrome extension — background service worker]
   1. หา tab ที่เปิด tiktok.com/tiktokstudio/upload อยู่ (ต้อง login ไว้ก่อนแล้ว)
   2. chrome.debugger.attach(tab)  <- แถบ "กำลัง debug" ขึ้นตรงนี้ ห้ามซ่อน
   3. DOM.setFileInputFiles(mp4_path)  <- ตัวเดียวที่ browser อนุญาตให้ตั้งไฟล์ได้จริง
   4. รอ TikTok ประมวลผลวิดีโอเสร็จ (poll DOM)
   5. ถ้าเจอช่องอัปโหลดปกเอง -> DOM.setFileInputFiles(cover_jpg_path) ด้วย
      (ถ้า TikTok เปิดให้อัปปกเอง = ไม่ต้องพึ่ง Cover Studio ของ POST-1 เลยสำหรับทางนี้)
   6. ใส่แคปชั่นใน contenteditable ผ่าน CDP Input.insertText
   7. รอพี่กดยืนยันเอง หรือกด Post ให้ (เลือกได้ในตั้งค่า)
   8. chrome.debugger.detach(tab)
        │
        ▼
[Local server]  POST /api/exports/mark-posted
   status -> posted, ย้าย mp4+cover ไป 04_Exports/Posted/
```

**หลักการออกแบบ:** ทำเฉพาะสิ่งที่พี่จะกดเองอยู่แล้ว เร็วขึ้น — ไม่เพิ่มพฤติกรรมใหม่ที่พี่ไม่เคยทำ
ไม่มี stealth, ไม่มี fingerprint spoofing, ไม่มี schedule, ไม่มี headless

---

## 3. สิ่งที่ยังไม่รู้ — ต้องพี่ทดสอบเอง (login ด้วยบัญชีจริง ผมทำแทนไม่ได้)

- [ ] TikTok Studio อัปโหลดตอนนี้ (ก.ย. 2026) มีให้ **อัปโหลดปกเองเป็นรูป** ไหม หรือเลือกได้แค่เฟรมจากวิดีโอ
      (ถ้าอัปเองได้ = ปัญหาปก .webp แก้จบในเส้นทางนี้เส้นทางเดียว ไม่ต้องพึ่ง Cover Studio)
- [ ] โครงสร้างหน้าเว็บจริง ปุ่ม/ช่องต่างๆ ยังตรงกับที่ community เขียนไว้ไหม (TikTok เปลี่ยน UI บ่อย)
      อ้างอิงคร่าวๆที่เจอ: ปุ่มโพสต์ `.btn-post:not(.disabled)`, ช่องแคปชั่นเป็น `contenteditable="true"`
- [ ] มี captcha/verification คั่นระหว่างอัปโหลดไหม (ถ้ามี = อัตโนมัติเต็มรูปทำไม่ได้ ต้องหยุดรอพี่ทุกครั้ง)
- [ ] `DOM.setFileInputFiles` ใช้ได้จริงกับ input ของ TikTok ไหม (บางเว็บซ่อน input ไว้ลึกใน component)

---

## 4. Gate ก่อนใช้งานจริง

- [ ] **ปิดไว้เป็นค่าเริ่มต้น** เปิดใช้ผ่าน toggle ใน `SystemSettings.jsx` เท่านั้น
- [ ] ทดสอบกับคลิปทดลอง/บัญชีที่ไม่ใช่บัญชีหลักก่อน ถ้ามี
- [ ] มีปุ่ม "โพสต์เองแบบ manual" (Round POST-1) อยู่คู่กันเสมอ — ปิด auto-post ได้ทุกเมื่อโดยไม่กระทบ flow อื่น
- [ ] แถบ "กำลัง debug" ต้องเห็นได้ชัดเจนทุกครั้งที่ทำงาน — ไม่พยายามซ่อนหรือลดความสังเกตเห็น
- [ ] โพสต์ 3-5 คลิปแรกแล้วสังเกตบัญชี (การมองเห็น, engagement, ข้อความเตือนจาก TikTok) ก่อนใช้เป็นประจำ

---

## 5. ตัดใจไม่ทำ

- ❌ เปิด Chromium แยกด้วย Playwright/Puppeteer ต่างหาก + stealth plugin — เสี่ยงสุดในทุกทางเลือก
- ❌ import คุกกี้/token ล็อกอินแทนการ login จริง — เพิ่มความเสี่ยงโดยไม่ได้อะไรเพิ่ม
- ❌ ตั้ง schedule/headless ให้รันเองโดยไม่มีคนกด — นี่คือเส้นที่ทำให้กลายเป็น "บอท" ตามคำจำกัดความที่เจอ
- ❌ TikTok Content Posting API — ทางถูกกฎแต่โพสต์ได้แค่ draft/private ก่อนผ่าน audit ใช้เวลาเป็นสัปดาห์

## Sources

- [Chromium: input.files restriction](https://groups.google.com/a/chromium.org/g/chromium-html5/c/MzEmEG01N4Y)
- [chrome.debugger API](https://developer.chrome.com/docs/extensions/reference/api/debugger)
- [Puppeteer DOM.setFileInputFiles issue](https://github.com/puppeteer/puppeteer/issues/6688)
- [ClipboardToFileInput extension (paste-file prior art)](https://github.com/GooglyBlox/ClipboardToFileInput)
- [web.dev: paste files pattern](https://web.dev/patterns/clipboard/paste-files)
- [Is TikTok Automation Allowed? (2026)](https://instantdm.com/blog/is-tiktok-automation-allowed)
- [TikTok Automation 2026: What Gets You Banned](https://openhosst.com/blog/tiktok-automation)
- [TikTok AI Content Policy 2026: 4-Tier Labels & Penalties](https://www.auditsocials.com/blog/tiktok-ai-content-disclosure-rules-2026)
- [tiktok-uploader (prior art, uses stealth)](https://github.com/polvallverdu/tiktok-uploader)
- [TikTokAutoUploader (prior art, uses stealth)](https://github.com/haziq-exe/TikTokAutoUploader)
