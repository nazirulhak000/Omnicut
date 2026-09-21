# 📊 แผนแม่บท: ระบบแสดงผลกราฟและแผนภาพสถิติ (Dynamic Charts & Visual Analytics Hub)

## 📌 บทนำและเป้าหมาย (Objective & Scope)
ผู้ใช้ต้องการให้วิเคราะห์แดชบอร์ดทั้งหมดของโปรแกรม และเปลี่ยนจุดที่เป็นเพียงตัวเลขหรือข้อความดิบ ให้แสดงผลเป็น **กราฟเส้น (Line/Area Graphs), กราฟวงกลม/โดนัท (Donut/Pie Charts), แผนภาพ Funnel การผลิต, และ Progress Ring เกจวัด** พร้อมจัดวางเลย์เอาท์สไตล์ **Dark Modern Glassmorphism** ให้สวยงาม มีมิติ ลึกซึ้ง และพรีเมียม โดยไม่พึ่งพา External Library ขนาดใหญ่ที่อาจขัดแย้งกับ React 19 แต่จะสร้างด้วย **Pure SVG React Components** ที่คมชัด ลื่นไหล รวดเร็ว และรองรับ Interactive Hover Tooltips 100%

---

## 🔍 1. การวิเคราะห์จุดแสดงผลกราฟในแต่ละแท็บ (Detailed Placement Analysis)

### 📊 แท็บ 1: การผลิต & ภาพรวมคลิป (`ProductionAnalyticsTab.jsx`)
1. **แผนภาพ Funnel การผลิต 4 ขั้นตอน (Funnel Pipeline Flow):**
   - *เดิม:* กล่องสี่เหลี่ยม 4 ช่องพร้อมแถบสีธรรมดา
   - *ใหม่:* **Interactive Funnel Flow Chart** — แผนภาพกรวยเชื่อมโยง 4 เฟส (สคริปต์พร้อม ➔ กำลังตัดต่อ ➔ ตัดต่อเสร็จ ➔ ลงโพสต์แล้ว) แสดงเส้นทางแปลงสภาพ (Conversion Rate), อัตราคงค้าง (WIP), และจุดคอขวดพร้อมแถบแสงนีออนเชื่อมต่อระหว่างเฟส
2. **สัดส่วนมุมมองคลิป (Content Angles Distribution):**
   - *เดิม:* รายการ Progress Bar ซ้อนกันหลายแถว
   - *ใหม่:* **Interactive Donut / Pie Chart** — กราฟโดนัทสีสันทันสมัย (นีออนไซอัน, ฟ้า, ม่วง, ส้ม, ชมพู) แสดงสัดส่วนประเภทคลิป (เช่น รีวิว, ป้ายยา, แกะกล่อง, ฮิตติดกระแส) เมื่อนำเมาส์ไปชี้จะไฮไลต์ชิ้นพาย และแสดงชื่อพร้อมจำนวนคลิปตรงกลางโดนัท
3. **KPI Card Published Rate:**
   - เติม **Circular Progress Ring** ข้างตัวเลขเปอร์เซ็นต์ (25%) เพิ่มความมีมิติ

---

### ⚡ แท็บ 2: โทเคน & ประสิทธิภาพ AI (`TokenDashboard.jsx`)
1. **ประวัติการใช้งานย้อนหลัง (Daily Token Volume):**
   - *เดิม:* กล่องการ์ดเล็กๆ เรียงกัน 7 วัน
   - *ใหม่:* **Interactive Curved Area / Line Chart (กราฟเส้นโค้งสมูท Bezier + Gradient Glow)**
     - เส้นกราฟความชันโค้งมนสีนีออนเขียว-ฟ้า สะท้อนปริมาณโทเคนในแต่ละวัน
     - พื้นหลังไล่เฉดเงา (Gradient Glow) สวยงาม
     - เส้นประกริดแนวนอน + ตัวเลขแกน Y (0k, 20k, 40k, 60k)
     - Interactive Hover: เมื่อเลื่อนเมาส์ผ่านจุดกราฟ จะแสดงเส้น Cursor แนวดิ่ง พร้อมกล่อง Tooltip หรูหรา บอกวันที่, โทเคน In/Out, ยอดเงินที่ประหยัดได้ (฿)
2. **สัดส่วนการใช้งานตามโมเดล (Models Distribution):**
   - *ใหม่:* **Donut Chart โมเดล AI** แยก Gemini 2.5 Flash, Gemini 2.0 Flash, Claude, TTS พร้อมสัดส่วน % ตรงกลาง
3. **สัดส่วนหมวดหมู่งาน (Tasks Distribution):**
   - *ใหม่:* **Donut Chart ประเภทงาน** แยก Script Gen, Vision Match, TTS Voice, Product Enrich

---

### 💾 แท็บ 3: พื้นที่จัดเก็บ & ระบบ (`StorageAnalyticsTab.jsx`)
1. **สัดส่วนพื้นที่โฟลเดอร์ระบบ 01-06 (Storage Distribution Donut):**
   - *เดิม:* ตารางการ์ด 6 โฟลเดอร์ธรรมดา
   - *ใหม่:* **Storage Multi-layer Donut Chart** — แสดงสัดส่วน `01_Raw` (52%), `04_Exports` (19%), `03_Projects` (15%), `02_Assets` (13%), `05_Covers` (2%), `06_Archive` ในกราฟวงแหวน เมื่อชี้จะแสดงขนาด GB/MB ตรงกลาง
2. **ความจุไดรฟ์ของคอมพิวเตอร์ (Drive Capacity Radial Gauge):**
   - *ใหม่:* **Semi-circular Radial Gauge (เกจวัดครึ่งวงกลม)** แสดงอัตราความจุไดรฟ์ (42.5%) พร้อมขีดเตือนระดับวิกฤต (Safe/Warning/Full)

---

### 📦 แท็บ 4: คลังเนื้อหา & วัตถุดิบ (`InventoryAnalyticsTab.jsx`)
1. **ความพร้อมของสินค้า (Inventory Readiness Donut):**
   - *ใหม่:* **Donut Chart 3 สถานะความพร้อม**:
     - 🟢 พร้อมตัดต่อทันที (Ready - มีทั้งรูปและคลิป)
     - 🟡 ขาดฟุตเทจวิดีโอ (Needs Media)
     - 🟣 ขาดสคริปต์ AI (Needs Script)
2. **มาตรวัดความสมบูรณ์วัตถุดิบ (Media Asset Radar/Gauge Rings):**
   - *เดิม:* 3 หลอดสี่เหลี่ยม
   - *ใหม่:* **Triple Concentric Rings (วงแหวน 3 ชั้นสไตล์ Apple Activity Ring)**
     - วงนอก (Cyan): รูปภาพสินค้า 100%
     - วงกลาง (Amber): วิดีโอ B-roll 80%
     - วงใน (Purple): สคริปต์ AI 60%

---

## 🎨 2. ดีไซน์คอมโพเนนต์ชาร์ตที่สร้างขึ้นใหม่ (`frontend/src/components/analytics/charts/`)

ทุกคอมโพเนนต์สร้างด้วย **Pure SVG + Tailwind CSS** ไร้ Dependencies เสริม เพื่อความเร็วสูงสุดและไม่มีปัญหา Compatibility กับ React 19:

1. `AreaLineChart.jsx` — กราฟเส้น Bezier โค้งเนียน + ไล่เฉดเงา + Tooltip Hover ลอยตัว
2. `DonutChart.jsx` — กราฟวงแหวนโดนัทหลายสี + ไฮไลต์ชิ้นเมื่อชี้ + ตัวเลขกลางวง + Legend คมชัด
3. `FunnelPipelineChart.jsx` — กรวยการผลิต 4 ขั้นตอนเชื่อมโยงด้วยแสง Gradient Glow
4. `ProgressRing.jsx` — วงแหวนเกจวัดความคืบหน้านีออนแบบเดี่ยวและแบบซ้อน 3 ชั้น

---

## 📂 3. รายการไฟล์ที่จะสร้างและแก้ไข (Proposed Changes)

### [NEW] Components
- `frontend/src/components/analytics/charts/AreaLineChart.jsx`
- `frontend/src/components/analytics/charts/DonutChart.jsx`
- `frontend/src/components/analytics/charts/FunnelPipelineChart.jsx`
- `frontend/src/components/analytics/charts/ProgressRing.jsx`

### [MODIFY] Tab Views
- `frontend/src/components/analytics/tabs/ProductionAnalyticsTab.jsx` — ฝัง FunnelChart และ DonutChart ของ Content Angles
- `frontend/src/components/TokenDashboard.jsx` — ฝัง AreaLineChart บน Daily Volume และ DonutChart บน Models/Tasks
- `frontend/src/components/analytics/tabs/StorageAnalyticsTab.jsx` — ฝัง DonutChart สัดส่วนพื้นที่โฟลเดอร์ 01-06 และ Disk Gauge
- `frontend/src/components/analytics/tabs/InventoryAnalyticsTab.jsx` — ฝัง DonutChart ความพร้อมสินค้า และ Concentric Rings

---

## 🧪 4. แผนการตรวจสอบความถูกต้อง (Verification Plan)

### Automated Tests:
- รัน `npm test -- --run` ให้ผ่าน 151/151 tests
- รัน `npm run build` ให้ผ่านสมบูรณ์ 0 errors
- รัน `pytest tests/test_analytics_hub.py` ให้ผ่าน 100%

### Visual & Interactive Verification:
- ตรวจสอบ Responsive Layout บน Desktop (1440px) และ Mobile (430px)
- ตรวจสอบว่า Tooltip กราฟเส้นขยับตามการลากเมาส์อย่างนุ่มนวล
- ตรวจสอบว่าชิ้นพายในกราฟโดนัทขยายเล็กน้อย (Active Scale) เมื่อ Hover
- ตรวจสอบตามกฎ UI Clean Standard (ไม่มีสัญลักษณ์หรืออีโมจิซ้ำซ้อน)
