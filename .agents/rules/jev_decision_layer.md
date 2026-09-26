# 🧭 กฎ Jev Decision Layer — ให้ AI ทุกตัวใช้ตัดสินใจร่วมกับ Jev

> บังคับใช้กับ **ทุก AI agent ที่ทำงานในโปรเจกต์นี้** (Cline / Codex / Claude Code / Antigravity / Cursor)
> หลักการเดียวของทั้งระบบ: **โค้ดเป็นเจ้าของ workflow · Jev จ่าย "common sense" ที่มีความน่าจะเป็น · มนุษย์ตัดสินใจเมื่อ Jev ไม่มั่นใจ**

Jev คือ **TypeSafe System One** — โมเดลที่ตอบคำถามแบบมีโครงสร้างด้วย **ความน่าจะเป็นที่ calibrate แล้ว** ไม่ใช่ LLM ที่เขียนข้อความ
สถานะจริง ณ 2026-09-26: `typesafe-sdk 0.7.1` ใน `.venv` · `TYPESAFE_API_KEY` ตั้งใน `.env` แล้ว · เรียกจริงผ่าน `scripts/typesafe_bridge.py`

---

## 1. Jev ทำอะไรได้ / ไม่ได้

| ✅ ทำได้ | ❌ ทำไม่ได้ |
| :--- | :--- |
| อ่าน **ข้อความ** แล้วตอบเป็นตัวเลข 0–1 พร้อม confidence | เห็น **ภาพ / วิดีโอ / เสียง** — รับได้แค่ text เท่านั้น |
| เลือก 1 จากหลายตัวเลือก (`choice`) | เขียนโค้ด / อธิบายเหตุผล / generate ข้อความ |
| ให้คะแนนบนแกน 0–N (`score`) | รันคำสั่ง / แก้ไฟล์ / เรียกโมเดลอื่น |
| ตอบว่า "เงื่อนไขนี้จริงไหม" (`noul`) | สลับโมเดลที่ user กำลังคุยด้วย (user ต้องเปลี่ยนเอง) |
| ตอบ **ทุกคำถามใน 1 call** — ถาม 10 ข้อราคาเท่ากับข้อเดียว | รับประกันว่าถูก — calibration ≠ ถูกทุกครั้ง |

> **ข้อจำกัดสำคัญที่ห้ามลืม:** Jev เห็นแค่ `state` ที่ agent ส่งให้ — มัน **ไม่ได้อ่านโค้ดหรือ diff เอง**
> ถ้าจะให้ตรวจ diff ต้องย่อยเนื้อหาส่งเข้า `state` เสมอ และต้องบอกผู้ใช้ว่า "ตรวจจากสรุป ไม่ได้อ่านไฟล์เอง"

---

## 2. Primitive 3 ตัว — ถามได้เท่านี้

| Primitive | ถามว่า | คืนค่า |
| :--- | :--- | :--- |
| `choice` | "เอา A หรือ B?" จากชุดที่กำหนด | `choice` + `confidence` |
| `score` | "เสี่ยง/ดีแค่ไหนบนแกน 0–N?" | `score` (float) + `confidence` |
| `noul` | "เงื่อนไขนี้เป็นจริงไหม?" | `noul` (0–1) |

**กติกาการเขียนคำถาม:**
- `state` = ข้อมูลดิบที่ต้องตัดสินใจ (โค้ด/สคริปต์/ชื่อไฟล์/ตัวเลข) — ใช้ **JSON field ที่มีชื่อ** เมื่อมีหลายส่วน
- `instructions` = คำถามเดียว จบใจความเดียว
- `criteria` (choice) / `levels` (score) = ตัวเลือกที่อธิบายตัวเองพอจะตัดสิน ไม่ใช่แค่ชื่อย่อ
- ถามหลายข้อ **รวม call เดียวเสมอ** (fan-out) ไม่ต้องประหยัดเรียกทีละข้อ

---

## 3. เมื่อไหร่ต้องถาม Jev (6 จุดมาตรฐาน)

| # | จุด | Primitive | ตัวอย่างคำถาม |
| :-- | :--- | :--- | :--- |
| 1 | **ก่อนเริ่มงานใหม่** | `noul` + `score` | "งานนี้ควรทำต่อไหม" · "ความเสี่ยง 0–4?" |
| 2 | **เจอทางเลือก 3–7 อัน** | `choice` + `score` | "วิธีไหนดีสุด/เสี่ยงต่ำสุด" |
| 3 | **ก่อน commit** | `noul` | "diff นี้แตะ `01_Raw/` `02_Assets/` หรือ hardcode path ไหม" |
| 4 | **ก่อนรัน FFmpeg/งานยาว** | `score` | "ความเสี่ยงที่จะรันผิดคำสั่ง 0–4?" |
| 5 | **เขียนสคริปต์/เอกสารเสร็จ** | `score` | "คุณภาพ 0–4?" · "ตรงกฎข้อ 7 (ไม่มีจุดไข่ปลา) ไหม" |
| 6 | **เปรียบเทียบก่อน/หลัง** | `noul` | "งานนี้ดีขึ้นจริงไหม" |

**ไม่ต้องถาม** เมื่อ: คำตอบชัดเจนจากกฎ/เทสแล้ว · เป็นงานซ้ำ ๆ ที่ทำแล้วหลายครั้ง · จะเพิ่มแค่ต้นทุนโทเคนโดยไม่เปลี่ยนการตัดสินใจ

---

## 4. เกณฑ์ Confidence — หัวใจของกฎนี้

| confidence | verdict | agent ต้องทำ |
| :--- | :--- | :--- |
| `>= 0.80` | `proceed` | ทำตามได้ แต่**รายงานตัวเลขให้ผู้ใช้เห็น** |
| `0.50 – 0.79` | `escalate` | **หยุดถามผู้ใช้** ห้ามตัดสินใจแทนเงียบ ๆ |
| `< 0.50` | `escalate` | อย่าใช้คำตอบ · ถามผู้ใช้ · บันทึกว่า Jev ไม่ช่วย |
| `null` / ขาด | `escalate` | ถือว่าไม่มั่นใจ (SDK อาจไม่คืนค่า field นี้) |

> 🚫 **ห้ามเด็ดขาด:** ห้ามอ้างผล Jev เป็น "หลักฐาน" หรือ "การยืนยันว่าถูกต้อง"
> ต้องเขียนลงรายงาน/บล็อกรอบว่า *"Jev ให้คะแนน X, confidence Y"* เสมอ เพื่อให้สืบย้อนได้ว่าใครตัดสินใจและบนพื้นฐานอะไร


---

## 5. วิธีเรียกใช้ (CLI กลาง — ทุก agent ใช้ตัวเดียวกัน)

ใช้ `tools/jev_advisor.py` **ห้ามเขียน one-off script ใหม่ใน `.tmp/`** เพราะจะได้ state shape ไม่เหมือนกันและไม่มี verdict gate

```bash
# ตั้งค่า path (ทุก session)
cd d:/Winona/Programmer/Capcut
PY=".venv/Scripts/python.exe"     # macOS/Linux ใช้ .venv/bin/python

# 0) เช็คว่าใช้ได้ไหม (ไม่ยิงเครือข่าย)
& $PY tools/jev_advisor.py --check

# 1) noul — ใช่ไหม
& $PY tools/jev_advisor.py noul --state .tmp/jev_state.json `
  --instructions "diff นี้แตะไฟล์ใน 01_Raw/ หรือ 02_Assets/ ไหม"

# 2) choice — เลือก 1 จากหลาย
& $PY tools/jev_advisor.py choice --state .tmp/jev_state.json `
  --instructions "ควรปิดก้อนงานไหนก่อน" `
  --option "A=cutout pipeline" --option "B=beat sync" --option "C=storage cleaner"

# 3) score — ให้คะแนนบนแกน
& $PY tools/jev_advisor.py score --state .tmp/jev_state.json `
  --instructions "ความเสี่ยงตอน commit ตอนนี้" --levels "ปลอดภัย,ต่ำ,กลาง,สูง,วิกฤต"

# 4) fanout — หลายคำถาม 1 call (ค่าเดียวที่แนะนำ)
& $PY tools/jev_advisor.py fanout --spec .tmp/jev_spec.json
```

`--state` รับได้ทั้ง path ไฟล์ `.json` และ JSON inline · ใช้ `--confidence 0.8` เพื่อเปลี่ยนเกณฑ์ verdict (ค่าเริ่มต้น `0.80`)

**ตัวอย่างไฟล์ spec สำหรับ fanout** (`.tmp/jev_spec.json`):
```json
{
  "state": { "pending_files": ["scripts/cutout_temporal.py", "scripts/beat_sync.py"] },
  "questions": {
    "close_first":    { "type": "choice", "instructions": "ปิดก้อนไหนก่อน",
                        "criteria": { "cutout": "pipeline ใหม่ 8 โมดูล", "beat": "beat grid" } },
    "safe_to_commit": { "type": "noul",   "instructions": "commit รวมตอนนี้ปลอดภัยไหม" },
    "commit_risk":    { "type": "score",  "instructions": "ความเสี่ยงตอน commit",
                        "levels": ["ต่ำ", "กลาง", "สูง"] }
  }
}
```

**ผลลัพธ์ (JSON บน stdout)** — อ่าน `verdict` เป็นอันดับแรก:
```json
{ "ok": true, "latency_ms": 526.6, "confidence_threshold": 0.8,
  "verdict": "escalate",
  "results": { "commit_risk": { "kind": "score", "score": 2.92, "confidence": 0.9 } } }
```

**Exit code:** `0` = ทำต่อได้ · `1` = verdict `escalate` · `2` = Jev ใช้ไม่ได้ (ไม่มี key / SDK ไม่ติดตั้ง / เรียกไม่สำเร็จ)

---

## 6. กติกาความปลอดภัยและค่าใช้จ่าย

- [ ] **Jev คิดต่อโทเคน** — ใช้เมื่อ "ผิดแล้วแพง" เท่านั้น ห้ามถามทุกจังหวะ ให้ถามที่จุดตัดสินใจตามหัวข้อ 3
- [ ] **ห้ามส่งข้อมูลลับหรือข้อมูลส่วนบุคคล** (ชื่อลูกค้า เบอร์โทร API key path จริงของเครื่อง) เข้า `state`
- [ ] **`state` ต้องสรุปให้เข้าใจได้** — ถ้ายาวเกินจำเป็นให้ย่อยเป็นส่วน ๆ ถามทีละส่วน แล้วรวมคะแนนเองในโค้ด
- [ ] **ถ้า Jev ล่ม/ไม่มี key → ทำงานต่อแบบ degrade เงียบ ๆ** ห้ามบล็อกงาน และห้ามเดาแทน Jev โดยไม่บอก
- [ ] **ห้ามใช้ Jev ตรวจสิ่งที่มันมองไม่เห็น** — เฟรมวิดีโอ ซับจริง ฟอนต์เรนเดอร์ safe zone ต้องใช้ FFmpeg probe / Gemini vision ตามกฎเดิม
- [ ] **คำตอบ Jev ไม่ใช่สิทธิ์อนุมัติ** — ถ้า Jev ไม่พบปัญหา ไม่ได้แปลว่าอนุญาตให้ละเมิดกฎข้อ 1–18 ของ `AGENTS.md`

---

## 7. Gate ของรอบที่แตะกฎนี้

| สิ่งที่เปลี่ยน | ต้องผ่าน |
| :--- | :--- |
| `tools/jev_advisor.py` | `python -m compileall -q tools` + `pytest tests/test_jev_advisor.py -q` |
| เอกสารกฎ | ไม่มี hardcode path (ใช้ relative ทั้งหมด) · ลิงก์กฎนี้จาก `AGENTS.md` แล้ว |
| ยืนยันว่าวางใช้จริง | `--check` ผ่าน + live call 1 ครั้งผ่าน `.venv` แล้ว **ลบไฟล์ชั่วคราว 100%** (กฎข้อ 15) |

> เอกสารชุดเต็มของ TypeSafe อยู่ที่ `.agents/skills/typesafe-ai/SKILL.md` — อ่านเมื่อต้องการรายละเอียด primitive ลึกกว่านี้
> เอกสารสด: <https://docs.typesafe.ai/llms.txt>
