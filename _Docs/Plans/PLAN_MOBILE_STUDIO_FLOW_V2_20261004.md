# 📱 แผนงาน: OmniCut Mobile Studio Flow v2 (P0 — กันตัน + ยกเลิกงาน)

> **วันที่:** 2026-10-04
> **ดำเนินการโดย:** Cline (Claude Sonnet 4.5)
> **ที่มา:** ผู้ใช้สั่งตรวจโหมดมือถือทั้งสาย แล้ววางแผนโฟลว์ให้ "ทำงานได้จริง + สบายมือที่สุด"
> **เอกสารอ้างอิง:** [AGENTS.md](../../AGENTS.md) · [TODO.md](../../TODO.md) · [ARCHITECTURE.md](../../ARCHITECTURE.md)
> **สถานะ Jev:** รันด้วย python ระบบไม่ผ่าน (ต้อง `.venv`) → degrade เงียบ ๆ ตามกฎ Jev ข้อ 4 จะรันที่ 6 จุดบังคับในรอบลงมือ

---

## 1. บริบท — สิ่งที่ตรวจพบว่ามีอยู่จริง (Verified)

| ชิ้นส่วน | ไฟล์ | สถานะ |
|---|---|---|
| สลับโหมด/เส้นทาง | `frontend/src/App.jsx` (L23,38,59,69,431,453) | ✅ |
| หน้าหลัก 4 สเต็ป | `frontend/src/components/MobileQuickStudio.jsx` (1,173) | ✅ |
| หน้ากล้อง Guided Take | `frontend/src/components/MobileFilmingPage.jsx` (739) | ✅ |
| หน้าโพสต์จาก QR | `frontend/src/components/MobileQuickPostPage.jsx` (364) | ✅ |
| Flow lib + polling | `frontend/src/lib/mobileStudioFlow.js` (44) | ✅ |
| API มือถือ | `scripts/api_mobile_studio.py` (172) | ✅ 8 endpoint |
| Service ประกอบคลิป SOP | `scripts/mobile_quick_studio.py` (549) | ✅ |
| เทส | `test_mobile_quick_studio.py`, `test_mobile_studio_browser.py`, `mobileStudioFlow.test.js` | ✅ |

เส้นทางเข้า: `?mode=mobile`/`?quick=1` → Mobile Studio · `?film=1&session=` → หน้ากล้อง · `?quick_post=1` → หน้าโพสต์ · ไม่ระบุ → auto `innerWidth<768`

เบื้องหลัง Step 3 เรนเดอร์ตาม SOP แล้ว (Fenrir + `gemini_tts` + `Mali` + `ghost_reveal` + สเปกส้ม + BGM 0.14 + บันทึกดราฟต์ลง `03_Projects/`)

---

## 2. ปัญหาที่พบ (เรียงตามความสำคัญ)

| # | ปัญหา | หลักฐาน | ผล |
|---|---|---|---|
| F1🔴 | กดเรนเดอร์ทั้งที่ไม่มีคลิป → ไป Step 3 แล้วเซิร์ฟเวอร์ตีกลับ 400 เด้งกลับ Step 2 | FE เช็คแค่ product/angle (`MobileQuickStudio.jsx:291`) · BE บังคับ (`mobile_quick_studio.py:408-409`) | จอวูบ เสียเวลา |
| F2🔴 | ไม่มีปุ่มยกเลิกการเรนเดอร์ | ไม่มี endpoint cancel ใต้ `/api/mobile-studio`; backend มี `cancel_event` แล้ว | เรนเดอร์ยาวหยุดไม่ได้ |
| F3🟠 | มาร์ค "โพสต์แล้ว" ไม่ได้จาก Mobile Studio | `markPosted` เรียกแค่ Tracker/Gallery/PostPage | สถานะ 4 เฟสไม่ขยับ |
| F4🟠 | Safe-area เฮดเดอร์/ฟุตเตอร์หาย | `MobileQuickStudio.jsx:414` (`sticky top-0`) | รอยบากบังปุ่ม |
| F5🟠 | สลับโหมด/หมุนจอไม่รีเฟรช + สลับไปเดสก์ท็อปไม่จำ | `App.jsx:69-79`, L459 | รีเฟรชเด้งกลับ |
| F6🟡 | Step 1 ยุบทั้งลิสต์เป็นสปินเนอร์ | `setLoading(true)` L154 + L490 | จอกะพริบ |
| F7🟡 | โหลดแคตตาล็อกพังแล้วกู้ไม่ได้ | `loadCatalog` แสดง error เท่านั้น | ต้องรีเฟรชเอง |
| F8🟡 | ปุ่มมีอีโมจิซ้อนไอคอน | ปุ่ม "⚡ ถ่ายด่วน…" (L690) | ขัด `ui_clean_standard` |
| F9🟢 | อัปโหลดไม่ dedupe / SHA-256 | `mobile_quick_studio.py:255` | เสี่ยงไฟล์ซ้ำ |
| F10🟢 | ไม่มี PWA manifest | `index.html` | หน้ากล้องไม่เต็มจอ |

---

## 3. โฟลว์เป้าหมาย (To-Be)

หลักการ: (1) ปุ่มหลักล่าง จับมือเดียวถึง (2) งานยาวมียกเลิก/กลับ (3) ไม่มี dead-end (4) บอกว่าขาดอะไร (5) แตะน้อย + กันหลุดเน็ต

```
[PC] start_app.bat → URL HTTPS (Tailscale) + QR
   │
[มือถือ] สแกน QR → Mobile Studio อัตโนมัติ
   │
Step 1  เลือกสินค้า ▸ เลือกมุม (ตัดแล้ว/มีคลิป/รอถ่าย)
        ├─ ไม่มีมุม → [ถ่ายด่วนฟรีสไตล์] / [สร้างมุมเอง]  (ไม่บล็อก)
        └─ ไม่มีสินค้า → [เพิ่มสินค้า] วางลิงก์ TikTok
   │  [ยืนยันสคริปต์และไปหน้าถ่ายทำ]  (สปินเนอร์ที่ปุ่ม ไม่ยุบลิสต์)
Step 2  วัตถุดิบ (แบนเนอร์เขียว/ส้มชัด)
        ├─ A) [กดเปิดกล้องถ่ายทำ]  Guided Take
        ├─ B) [เลือกคลิปจากอัลบั้ม]
        ├─ [ฟังตัวอย่างเสียง Fenrir] + สวิตช์ BGM
        └─ [ประกอบคลิปและเรนเดอร์]  ← disable ถ้าไม่มีวัตถุดิบ (F1)
Step 3  กำลังประกอบ… % + ขั้น + [ยกเลิกการเรนเดอร์] (F2)
        └─ เน็ตหลุด → [ตรวจสถานะอีกครั้ง]
Step 4  พรีวิว 9:16 ▸ [แชร์ TikTok] [เซฟอัลบั้ม] [มาร์คโพสต์แล้ว] [ทำมุมถัดไป]
```

| สถานการณ์ | พฤติกรรม |
|---|---|
| สินค้าไม่มีมุม | สร้างมุมอัตโนมัติ ไม่บล็อก |
| ไม่มีคลิปแล้วกดเรนเดอร์ | disable ปุ่ม + บอกเหตุ (F1) |
| อัปโหลดหลุดกลางทาง | แสดง % + ลองใหม่ ไม่ค้างสปินเนอร์ |
| เรนเดอร์ล้มเหลว | กลับ Step 2 คงค่าที่เลือก |
| รีเฟรช/ปิดกลางคัน | กู้ session+task จาก `sessionStorage` |
| หมุนจอ | รีเฟรชเลย์เอาต์ ไม่เสีย session |
| เน็ตหลุดชั่วคราว | poll retry 3 ครั้ง + ปุ่มตรวจสถานะ |

---

## 4. แพ็กเกจงาน + Acceptance Criteria

### 🥇 P0 — กันตันให้ทำงานได้จริง (รอบนี้)
| WP | งาน | ไฟล์ | AC |
|---|---|---|---|
| P0-1 | Preflight ก่อนเรนเดอร์: disable ปุ่มเมื่อไม่มีวัตถุดิบ + hydrate session จากหน้ากล้อง + ข้อความบอกเหตุ | `MobileQuickStudio.jsx` | กดเรนเดอร์โดยไม่มีคลิปไม่ได้ |
| P0-2 | endpoint `POST /api/mobile-studio/cancel/{task_id}` + ปุ่มยกเลิก Step 3 (ConfirmModal) | `api_mobile_studio.py`, `api.js`, `MobileQuickStudio.jsx` | ยกเลิกได้เป็น `cancelled` |
| P0-3 | ปุ่ม "ลองใหม่" เมื่อโหลดแคตตาล็อก/เซสชันล้มเหลว | `MobileQuickStudio.jsx` | กู้ได้โดยไม่รีเฟรช |
| P0-4 | Loading ระดับปุ่ม (ไม่ยุบทั้งลิสต์ Step 1) | `MobileQuickStudio.jsx` | กดยืนยันแล้วลิสต์ไม่หาย |

### 🥈 P1 — สบายมือครบวง
| WP | งาน | ไฟล์ |
|---|---|---|
| P1-1 | resize/orientation + persist โหมด + `onSwitchToDesktop` ตั้ง `?mode=desktop` | `App.jsx` |
| P1-2 | Safe-area padding เฮดเดอร์/ฟุตเตอร์ | `MobileQuickStudio.jsx` |
| P1-3 | มาร์ค "โพสต์แล้ว" ใน Step 4 | `MobileQuickStudio.jsx` |
| P1-4 | เคลียร์สัญลักษณ์ซ้ำตาม ui_clean | `MobileQuickStudio.jsx` |

### 🥉 P2 — Polish
P2-1 PWA manifest + apple-touch-icon · P2-2 อัปโหลด dedupe SHA-256 · P2-3 Wake-Lock · P2-4 แบ่งหน้าแคตตาล็อก

---

## 5. แผนทดสอบ/ตรวจสอบ

| ระดับ | เพิ่ม | เกณฑ์ |
|---|---|---|
| Unit (JS) | `mobileStudioFlow.test.js` — preflight helper | เขียว |
| Unit (Py) | `test_mobile_quick_studio.py` — cancel endpoint | `cancelled` ถูก |
| Browser | `test_mobile_studio_browser.py` — บล็อกเรนเดอร์ไม่มีคลิป, ยกเลิก | headless ผ่าน |
| Build | `npm run build` + `python -m compileall -q scripts` | ผ่าน |
| เครื่องจริง | iPhone Safari + Android Chrome ผ่าน Tailscale HTTPS | จบ 1 คลิป |
| Cleanup | ลบไฟล์ทดสอบ 100% + ถอด `export_registry.json` | ไม่มีขยะ |

---

## 6. กฎที่ยึด
`ui_clean_standard` (ปุ่ม = ไอคอน + กริยา ไม่มีอีโมจิซ้อน) · `testing_standard` (temp storage, deterministic) · กฎ 11/15 (cleanup 100%) · กฎ 13 (dedupe) · Plan-Before-Code

---

## 7. รอบนี้ (P0) รายละเอียดการแก้
1. **P0-1** `MobileQuickStudio.jsx`: เพิ่ม `sessionFootageReady` + `refreshSessionFootage()` (เรียก `getRecordingSession`) → `hasFootage = uploadedVideoPath || selectedAngle.attached_raw || sessionFootageReady` → ปุ่มเรนเดอร์ `disabled={!hasFootage}` + ข้อความ + guard ใน `handleStartAssemble`
2. **P0-2** `api_mobile_studio.py`: `POST /cancel/{task_id}` ใช้ `TaskManager.cancel_task` + `render_jobs.request_cancel` · `api.js`: `cancelMobileTask` · `MobileQuickStudio.jsx`: ปุ่ม "ยกเลิกการเรนเดอร์" + `ConfirmModal`
3. **P0-3** ปุ่ม "ลองใหม่" ใน error/empty state ของ Step 1
4. **P0-4** แยก `confirming` state ใช้กับปุ่มยืนยัน Step 1 แทน global `loading`

| F10🟢 | ไม่มี PWA manifest | `index.html` | หน้ากล้องไม่เต็มจอ |
