# 🎬 แผน: ยกระดับ motion ข้อความให้ระดับ CapCut

แผนยาวของงาน Round 3–7 — **เหตุผล ตัวเลขที่วัดมา และข้อตัดสินใจ**
รายการงานจริงพร้อมช่องติ๊กอยู่ที่ [TODO.md](file:///d:/Winona/Programmer/Capcut/TODO.md) · รอบที่ปิดแล้วอยู่ที่ [HISTORY.md](file:///d:/Winona/Programmer/Capcut/HISTORY.md)

| รอบ | งาน | สถานะ |
| :--- | :--- | :--- |
| Round 3 | ซ่อมฐาน + รวม writer + easing | ✅ ปิดแล้ว |
| Round 4 | per-word layout (static) | ✅ ปิดแล้ว |
| Round 5 | per-word animation | ✅ ปิดแล้ว |
| Round 6 | ช่องใหม่ที่ mirror ได้เป๊ะ | ✅ ปิดแล้ว |
| Round 7 | template v2 + แกลเลอรีขยับได้ | ✅ ปิดแล้ว |

---

## 1. โจทย์

เทมเพลตข้อความ "เหมือนเอาตัวอักษรมาแปะ" ไม่มีโมชั่นแบบ CapCut ไม่พอจะทำให้คลิปไวรัล

**สำรวจแล้วพบว่าสาเหตุไม่ใช่เพดานของ libass — เพดานกว้างกว่าที่ใช้อยู่มาก**

ของที่ libass 0.17.4 ทำได้แต่ **ไม่เคยแตะเลยสักตัว**:
`\frx` `\fry` 3D · `\fsp` ระยะตัวอักษร · `\fax` `\fay` เอียง · `\xshad` `\yshad` · `\xbord` `\ybord` · `\k` `\kf` karaoke
และ `\t` มี **accel exponent** (`pow(p, accel)`) ให้ใช้ แต่ทั้งโปรเจกต์ใช้ linear ล้วน 38 จุด

---

## 2. ข้อจำกัดจริง 3 ข้อ

1. animation เป็น **per-line** นาฬิกาเป็น **per-tier** (3 ช่องเท่านั้น: brand/model/label) — ไม่มีทางทำคำทยอยเข้าทีละคำ
2. **linear ล้วน** — ไม่มี easing ที่ไหนเลย
3. **text overlay ฝั่ง render อ่านแค่ `anim.in`** — `loop`/`out`/`accent`/`stagger` ถูกทิ้งเงียบ ทั้งที่ canvas ทำได้หมด

## 3. ตัวบล็อกจริงคือโครงสร้าง ไม่ใช่ความสามารถ

- ASS writer เคยมี **2 ตัวแยกกัน** — hook loop กับ text-overlay block ที่เขียน preset ซ้ำเป็น literal — ชนกับ canvas ตัวเดียว `drawOneOverlay`
- **wrapper 2 ตัวตัดบรรทัดไม่ตรงกัน** — `wrap_text_for_ass` นับตัวอักษรด้วย newmm vs `wrapCanvasText` วัดพิกเซลด้วย `Intl.Segmenter`
  → per-word x ไม่มีความหมายถ้าสองฝั่งยังเห็นคำอยู่คนละบรรทัด

## 4. บั๊กความกว้าง 3 ตัวที่วัดเจอ (ทำให้พรีวิว ≠ render อยู่แล้ววันนี้)

| # | บั๊ก | ผลที่วัดได้ |
| :--- | :--- | :--- |
| 1 | `Spacing: 0.5` ใน Style ทั้ง 11 ตัว libass ใช้จริง แต่ไม่มี engine ไหน model | +13px บนบรรทัด 27 cluster ที่ Fontsize 75 (~2%) |
| 2 | `_measure_text_width_px` คืน **ink bbox** ไม่ใช่ advance | บวกรายคำเกินจริง 447 vs 442 |
| 3 | `FONT_WEIGHTS` โกหก — `\fn Kanit`+`Bold=1` ได้ **Kanit-Bold (700)** ไม่ใช่ Black เพราะ "Kanit Black" เป็นคนละ family | **2.94% — drift ใหญ่สุด** · `Anuphan-Bold` ประกาศ `usWeightClass 400` ด้วย |

ทั้งสามซ่อมแล้วใน Round 3 — ยืนยันด้วยการเรนเดอร์จริง: `Spacing=0.5` ยืดเกินไป **24px (666 vs 642)** และ `Spacing=0` ตรงกับ Canvas advance

---

## 5. ข้อตัดสินใจหลัก

### 5.1 Python คำนวณ layout ทีเดียว ส่งให้ canvas ใช้

`scripts/subtitle/word_layout.py` เป็นแหล่งเดียวของตำแหน่งคำ — ASS writer ใช้ตรง, API ส่งติดมากับ overlay, canvas คูณ `CANVAS_W` เอา

**เหตุผล:** ทำให้ drift เป็นศูนย์ **โดยโครงสร้าง** ไม่ใช่โดยจูนให้ใกล้ และแก้ปัญหา wrapper ไม่ตรงกันไปด้วย เพราะ backend คืน *บรรทัด* ไม่ใช่แค่รายการคำ

repo เคยเรียนบทเรียนรูปเดียวกันนี้มาแล้ว 2 ครั้ง (BGM/LUT resolver ที่ UI เลือกด้วย id แต่ backend เริ่มจากชื่อไฟล์) — text layout คือครั้งที่ 3

**ต้นทุน:** round-trip ตอนพิมพ์ (debounce 120ms + cache) ตอนยังไม่มี layout ต้องแสดงว่าเป็นค่าชั่วคราว

### 5.2 จัด technique ตาม failure mode ไม่ใช่ตามความสามารถ

| Tier | คือ | ความเสี่ยง | ตัดสิน |
| :--- | :--- | :--- | :--- |
| **A** | ไม่ขยับ advance: `\1c` `\3c` `\alpha` `\blur` `\bord` `\shad` `\fax` `\k` `\kf` | **ศูนย์** — layout ไม่เปลี่ยน ไม่มีอะไร drift ได้ | ✅ ทำก่อน ความว้าวส่วนใหญ่อยู่ตรงนี้ |
| **B** | mid-line `\fscx`/`\fsp` แบบยอม reflow | reflow คำนวณโดย shaper คนละตัวสองฝั่ง **ต่อเฟรม** — assert ไม่ได้เลย | ❌ ตัดทิ้ง |
| **C** | 1 Dialogue ต่อคำ + `\pos` | ต้องรู้ x ทุกคำ แต่ **พอทุกคำมี `\pos` แล้ว libass ไม่ทำ layout เอง** → error สะสมหายไป เหลือแค่ error ต่อคำ | ✅ ใช้กับ position/rotation |

> Tier C **ปลอดภัยกว่า** Tier B ไม่ใช่เสี่ยงกว่า — และ Tier C คือสิ่งที่ปลดล็อกให้ `\fsp` ใช้ได้อย่างปลอดภัยทีหลัง

### 5.3 ตัด 3D ออก

`cos θ` ไม่ใช่ข้อยกเว้นที่ parity rule §5 ครอบ — §5 อนุญาตเมื่อ**กลไก**ต่างแต่ตำแหน่ง/ขนาด/สียังลงที่เดิม (soft shadow เข้าเกณฑ์เพราะกล่องเท่ากัน ต่างแค่ความฟุ้ง)
แต่ `\fry θ` เป็น perspective projection — ขอบใกล้ใหญ่ ขอบไกลเล็ก ส่วน `cos θ` บีบสมมาตรและไม่มี trapezoid เลย = **ขนาดและตำแหน่งผิด**

ถ้าจะเอาจริงต้องวาดแต่ละคำลง offscreen canvas แล้วฉายเป็น projective quad ตาม focal length ของ libass (repo มี WebGL path ของ LUT อยู่แล้ว) — ไว้หลัง per-word นิ่ง

> ของแถม: ข้อจำกัด "`\org` เป็น event-level ทุก span เลยหมุนรอบจุดเดียวกัน" **หายไปเองเมื่อแตกเป็น 1 event ต่อคำ** — แต่ละคำได้จุดหมุนของตัวเอง

### 5.4 easing เป็นช่องใหม่ ไม่ทับของเดิม

- `accel = 1.0` ต้องได้ ASS **byte-identical กับเดิม** (assert ไว้แล้ว)
- preset ใหม่ `bounce_soft` / `pop_soft` — ของเดิมไม่แตะ ตาม precedent ของ `LEGACY_TEXT_ANIM`
- **ห้ามตั้งชื่อ `ease_out`** — ชนกับ `keyframe_engine.py` ที่นิยาม `t*(2-t)` ไว้แล้ว (ที่ `t=0.5` ได้ 0.75 vs libass 0.707) และมีเทสล็อกอยู่

---

## 6. ผล Spike libass (Round 3, 8/8 ข้อ)

| คำถาม | ผล |
| :--- | :--- |
| mid-line `\t` สอง window ต่างกัน | ✅ ทำงาน — แต่ tag override **ไหลไปข้างหน้า** ต้อง reset ก่อนคำถัดไป |
| `accel` exponent | ✅ `pow(p, accel)` ตรงกับ `Math.pow(p, accel)` ของ JS |
| `Spacing` คิดต่อ glyph หรือ cluster | ต่อ **glyph** → วรรณยุกต์ไทยโดนแทรก spacing จนเพี้ยน · `Spacing: 0` แก้ได้ 100% |
| span `{\1c}` ตรงรอยต่อคำ ทำลาย HarfBuzz cluster ไหม | ✅ ไม่ทำลาย → **Tier A ใช้ได้ฟรีจริง** |
| `\pos` ยัง wrap ที่ Margin ไหม | ใช่ → ต้องใส่ `\q2` ทุก Dialogue |
| libass เลือก face ไหนสำหรับ `\fn Kanit`+`\b1` | `Kanit-Bold.ttf` (700) ไม่ใช่ Black (900) |

---

## 7. Gate ที่สำคัญที่สุด — invariant ของ Round 4

> **ปิด animation หมด → per-word render ต้องเท่ากับ un-split render เกือบทุกพิกเซล**

split → place → render → diff PNG นับพิกเซลที่ต่าง
ผ่าน/ไม่ผ่านตัดสินด้วยพิกเซล **ไม่ต้องใช้รสนิยม** — ถ้าไทยพังจะรู้ตั้งแต่รอบ 4 ไม่ใช่รอบ 7

budget: word-start error ≤ 1 render px · ink-extent error ≤ 2 render px

**ทางถอย:** ถ้าไทยแตกแล้ววรรณยุกต์เพี้ยนหนักกว่าเดิม → หยุด เปลี่ยนไปใช้ per-word เฉพาะ Latin/ตัวเลข ส่วนไทยใช้ Tier A ทั้งบรรทัด แล้วบันทึกเหตุผล

---

## 8. ข้อควรระวังตอนทดสอบ

- ทุกคำสั่ง ffmpeg ต้องมี `fontsdir=02_Assets/Fonts` — ไม่งั้น libass fallback ไปฟอนต์ระบบและ **ตัวเลขเป็นโมฆะทั้งหมด** (เคยทำให้สรุปผิดมาแล้ว 2 รอบ)
- `.ass` ต้องอ้างด้วย **relative path** — drive-letter colon ทำ filter arg พัง
- motion ต้องดึง**หลายเฟรม** ตลอดช่วง เข้า/ค้าง/ออก ไม่ใช่เฟรมเดียว
- shadow layer ต้อง duplicate ต่อคำ ไม่งั้นผิด parity rule 2.12 แบบเดียวกับที่ Light Sweep เคยพลาด

## 9. พฤติกรรมที่เปลี่ยนและแจ้งแล้ว

ซ่อม Spacing/advance/FONT_WEIGHTS ทำให้คลิปเก่าที่ re-render ต่างจากเดิม ~2-3%
**render ขยับเข้าหาพรีวิว = แก้บั๊ก ไม่ใช่ regression**
