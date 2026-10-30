# 📖 คู่มือการใช้งาน: OmniCut Cloud Studio + AGY Cloud Terminal บน Google Colab

> **OmniCut Cloud Studio & AGY Autonomous Agent (Google Colab Edition)**  
> สั่งผลิตและเรนเดอร์คลิปวิดีโอ TikTok 9:16 สไตล์ **Couple Paper Chat (#5 น้องนุ้ย & พี่บ่าว)** บน Cloud 100% พร้อมหน้าต่าง **AGY Interactive Web Terminal (`/agy`)** ที่สั่งงาน AI เป็นภาษาคนหรือรันคำสั่งระบบได้ทุกอย่างผ่านเบราว์เซอร์และมือถือ โดยคอมพิวเตอร์ที่บ้านไม่ต้องออกแรง (0% PC Hardware Load)

---

## 🌟 จุดเด่นหลัก (Key Benefits)
1. 🖥️ **0% PC Hardware Load**: ทุกขั้นตอน (Single-Take TTS, Faster-Whisper GPU, HyperFrames Headless Chrome, FFmpeg Render) รันอยู่บนเซิร์ฟเวอร์ของ Google ไม่กิน CPU/RAM และไม่กินพื้นที่ฮาร์ดดิสก์ของเครื่องคุณ
2. 🤖 **AGY Interactive Web Terminal (`/agy` & `ttyd`)**: เปิดหน้าต่าง `https://studio.nazirulhak.com/agy` สั่งงาน `agy` เป็นภาษาไทย/อังกฤษได้อิสระ 100% ทั้งสั่งผลิตคลิป, แก้โค้ด, แก้บั๊ก, ดึง Git, เช็ก GPU หรือเปิดโหมดเป้าหมายอัตโนมัติ (`/goal`)
3. 🌐 **Permanent Cloudflare Domain**: เชื่อมต่อผ่าน `https://studio.nazirulhak.com` ถาวร พร้อมระบบสลับคีย์ Gemini 5 คีย์อัตโนมัติ (Auto-Rotate) และระบบ Watchdog Keepalive ป้องกัน Colab หลับ
4. 💾 **Google Drive Auto-Sync**: ซิงก์ไฟล์วิดีโอ MP4 คมชัด 1080x1920 30FPS จาก `04_Exports/Ready_to_post/` เข้า `Google Drive/MyDrive/Omnicut_Exports/` ได้ในคลิกเดียว

---

## 🚀 วิธีการเปิดใช้งานบน Google Colab (One-Click Runner)

### ขั้นตอนที่ 1: เปิดไฟล์ Notebook บน Google Colab
1. เข้าเว็บ [Google Colab](https://colab.research.google.com/)
2. เลือกแท็บ **GitHub**
3. ค้นหา Repository: `nazirulhak000/Omnicut` (Branch: `main`)
4. คลิกเปิดไฟล์ **`Omnicut_Cloud_Runner.ipynb`**
5. แนะนำให้ตั้งค่า **Runtime** > **Change runtime type** > เลือก **T4 GPU**

---

### ขั้นตอนที่ 2: คลิกปุ่ม ▶ (Play) เพียงปุ่มเดียว!
กดปุ่ม **Play (▶)** ที่เซลล์หลัก ระบบจะดำเนินการให้อัตโนมัติครบ 5 ขั้นตอนในรวดเดียว:
1. **ซิงก์โค้ดล่าสุดจาก GitHub (`origin/main`)** และซิงก์สคริปต์ 180 บทเข้าสู่ฐานข้อมูล
2. **ติดตั้งแพ็กเกจระบบ** (`FastAPI`, `faster-whisper`, `cloudflared`, `google-antigravity`, และ `ttyd` Web Terminal)
3. **โหลด Gemini API Keys ทั้ง 5 คีย์** พร้อมระบบสลับคีย์อัตโนมัติเมื่อโควตาเต็ม
4. **เปิดเซิร์ฟเวอร์ OmniCut Backend (พอร์ต 8000)** และ **AGY Terminal Daemon (พอร์ต 7681)**
5. **เปิดอุโมงค์ Cloudflare Tunnel** และแสดงปุ่มลัด 2 ปุ่มใหญ่:
   - **`✨ เปิด OmniCut Pro Studio`** (`https://studio.nazirulhak.com`)
   - **`🤖 เปิด AGY Cloud Terminal (/agy)`** (`https://studio.nazirulhak.com/agy`)

---

## 🤖 วิธีสั่งงาน AGY Cloud Terminal (`/agy`)

เมื่อเปิดหน้า **`https://studio.nazirulhak.com/agy`** (หรือพิมพ์คำสั่ง `agy` ใน Terminal) คุณสามารถสั่งงานได้ 3 รูปแบบ:

### 1. สั่งงานด้วยภาษาธรรมชาติ (Natural Language Commands)
พิมพ์คุยเป็นภาษาไทยหรืออังกฤษได้เหมือนแชทกับ AI Agent:
- *"ตรวจสอบสถานะ GPU, พื้นที่ดิสก์ และความพร้อมของระบบในตอนนี้ให้หน่อย"*
- *"แสดงรายการสินค้าทั้งหมดใน `_Docs/products.json` และดูว่ามีคลิปรุ่นไหนเรนเดอร์เสร็จแล้วบ้าง"*
- *"ช่วยตรวจสอบโค้ดใน `scripts/api_copilot.py` และรัน pytest ทดสอบให้ที"*
- *"ซิงก์ไฟล์คลิป MP4 ทั้งหมดใน `04_Exports/Ready_to_post/` เข้า Google Drive ให้หน่อย"*

### 2. โหมดเป้าหมายอัตโนมัติ (`/goal` — Autonomous Multi-Step Mode)
ติ๊กช่อง **"เปิดโหมดเป้าหมายอัตโนมัติ (/goal)"** หรือพิมพ์ขึ้นต้นด้วย `/goal`:
- `/goal ตรวจสอบสคริปต์ของสินค้า TTZ01 แล้วทดสอบเจนเสียงและเรนเดอร์คลิปที่ 1 จนเสร็จสมบูรณ์`
- Agent จะวางแผน เรียกใช้เครื่องมือ (`run_command`, `read_file`, `write_file`, `edit_file`, `sync_to_drive`) ตรวจสอบผลลัพธ์ และแก้ไขปัญหาเองต่อเนื่องสูงสุด 25 ขั้นตอนจนกว่างานจะสำเร็จ

### 3. โหมดรันคำสั่ง Linux Shell ด่วน (`!command`)
พิมพ์เครื่องหมายตกใจ `!` นำหน้าคำสั่งเพื่อรัน Bash command โดยตรง:
- `!nvidia-smi` — ดูสถานะการ์ดจอ T4 และ VRAM
- `!git status -s && git log -n 5 --oneline` — เช็กสถานะ Git ล่าสุด
- `!ls -lh 04_Exports/Ready_to_post/` — ดูไฟล์วิดีโอที่เรนเดอร์เสร็จแล้ว
