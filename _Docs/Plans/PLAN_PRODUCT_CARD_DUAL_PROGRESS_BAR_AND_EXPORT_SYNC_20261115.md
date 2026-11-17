# 📋 แผนงาน: ปรับปรุงหลอดความคืบหน้าสินค้าแบบ 2 สี (Green=Program Native, Blue=HyperFrames) และซิงก์ข้อมูลคลิปที่เรนเดอร์แล้วเข้า ProductCard

**วันที่:** 2026-11-15  
**ผู้ดำเนินการ:** Antigravity (Gemini 3.8 Flash High)  
**อ้างอิงคำขอ:** ผู้ใช้รายงานว่าสินค้าเช่น HOY01, HAT01, HAT02, ORS01 มีการเจนคลิปแล้วแต่แถบบาร์ขึ้น 0/20 ไม่กระดิก และต้องการแยกสีในหลอดเดียวกัน (HyperFrames = หลอดสีฟ้า, โปรแกรม Native = หลอดสีเขียว)

---

## 🎯 1. สาเหตุของปัญหา (Root Cause Analysis)

1. **แถบบาร์ใน `ProductCard` คำนวณจาก `product.angles` เพียงอย่างเดียว:**
   ```javascript
   const pAngles = product.angles || [];
   const pDone = pAngles.filter(a => a.status === 'posted' || a.status === 'rendered').length;
   const total = pAngles.length || 4;
   ```
2. **สถานะใน `products.json` ของสินค้ากลุ่ม 20 มุมยังค้างเป็น `"status": "scripted"`:**
   - เมื่อรัน `tools/sync_scripts_to_products.py` ข้อมูลมุม 20 ตอนถูกเขียนทับด้วย `status: "scripted"` โดยไม่ได้เทียบกับ `_Docs/export_registry.json`
   - ในขณะที่ `export_registry.json` มีการบันทึกคลิปเรนเดอร์จริงแล้วทั้งหมด:
     - `HOY01`: Native 8 คลิป, HyperFrames 20 คลิป (รวม 28 คลิป)
     - `HAT01`: Native 11 คลิป, HyperFrames 28 คลิป (รวม 39 คลิป)
     - `HAT02`: Native 0 คลิป, HyperFrames 20 คลิป (รวม 20 คลิป)
     - `ORS01`: Native 7 คลิป, HyperFrames 20 คลิป (รวม 27 คลิป)
     - `RED01`: Native 0 คลิป, HyperFrames 28 คลิป (รวม 28 คลิป)
     - `GOO01`: Native 1 คลิป, HyperFrames 35 คลิป (รวม 36 คลิป)
     - `ESS02`: Native 23 คลิป, HyperFrames 22 คลิป (รวม 45 คลิป)
3. **ระบบเดิมไม่มีการแยกแยะสัดส่วน Native Program vs HyperFrames บน Progress Bar:**
   - หลอดสีเดิมเป็นสีเดียว (`bg-[#25F4EE]` หรือ `bg-emerald-400` เมื่อครบ 100%)

---

## 🛠️ 2. แผนการแก้ไข (Action Plan)

### เฟส 1: Backend Reconcile & Export Stats Injection (`scripts/product_store.py`)
1. **อัปเกรด `ProductStore.reconcile_existing_projects()`:**
   - นอกจากการสแกน `03_Projects/` แล้ว ให้สแกน `ExportRegistry` โดยตรงด้วย `product_id`
   - จับคู่คลิปใน `ExportRegistry` เข้ากับ `angles` ของสินค้า:
     - Direct `angle_id` match
     - HyperFrames episode pattern: `r'-pov-s(\d+)'` หรือ `r'ang_.*?_(\d+)'` -> `ang_{ep:02d}`
     - เมื่อจับคู่เจอ ให้อัปเดต `angle.status = exp.status` (`'rendered'` / `'posted'`), `angle.video_url = exp.path`, `angle.project_name = exp.project_name`
2. **คำนวณและแนบ `export_stats` ลงใน Product Object ทุกตัวใน `ProductStore.list()` และ `ProductStore._to_lite_product()`:**
   ```python
   export_stats = {
       "native_count": native_count,
       "hyperframes_count": hf_count,
       "total_rendered": native_count + hf_count,
   }
   ```
3. **ซิงก์ฐานข้อมูลและไฟล์ `products.json` / `products_seed.json` ให้สมบูรณ์ 100%**

### เฟส 2: Frontend Multi-Segment Progress Bar (`frontend/src/components/ProductToClip.jsx`)
1. **อัปเดตฟังก์ชัน `ProductCard` (Horizontal Carousel Item) & Catalog Modal Cards:**
   - ดึง `nativeCount` และ `hfCount` จาก `product.export_stats` (พร้อม fallback ไปยัง `pAngles` filter)
   - คำนวณความกว้างหลอดสีเขียว (Program/Native) และหลอดสีฟ้า (HyperFrames):
     - หลอดสีเขียว: `bg-emerald-400` (`#34D399` / `#10B981`)
     - หลอดสีฟ้า: `bg-sky-400` (`#38BDF8`)
     - หลอดพื้นหลัง: `bg-slate-800/80`
   - วางอยู่ในหลอดแคปซูลเดียวกัน (`flex h-1.5 rounded-full overflow-hidden`)
   - แสดงตัวเลข `{totalDone}/{total}` พร้อม tooltip บอกรายละเอียดชัดเจน
2. **ทดสอบ Build & Preview:**
   - `npm --prefix frontend test`
   - `npm --prefix frontend run build`
   - Backend `pytest`

---

## 🔒 3. เกณฑ์ความสำเร็จ (Verification Gate)
1. การ์ดสินค้าทุกตัวใน Carousel (เช่น HOY01, HAT01, HAT02, ORS01, RED01, GOO01, ESS02) หลอดบาร์แสดงผลความคืบหน้าตามจริง ไม่ค้าง 0/20
2. สีบนหลอดแยกชัดเจน: สีเขียว = Program Native, สีฟ้า = HyperFrames อยู่ในหลอดเดียวกัน
3. การคลิกดูรายการมุม (Angle List) ด้านล่างแสดงสถานะ "เรนเดอร์แล้ว" สอดคล้องกับคลิปจริง
4. Unit tests ทั้ง Frontend และ Backend ผ่าน 100% ไม่มี regression
