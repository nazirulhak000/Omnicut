# Pagination & Loading Audit Plan

วันที่ตรวจ: 2026-09-18  
ดำเนินการโดย: Codex (GPT-5)  
ขอบเขต: ตรวจจาก frontend components, data coordinator และ API routes ทั้งโปรเจกต์  
สถานะ: แผนงานเท่านั้น ยังไม่มีการแก้ production code

## สรุปผู้บริหาร

ปัญหาหลักไม่ได้มีแค่ตารางประวัติโทเคน แต่มี 2 ชั้น:

1. บางหน้ามีการตัดรายการฝั่ง UI แล้ว แต่ backend ยังส่งข้อมูลทั้งหมดมาก่อน ทำให้เสียเวลา/หน่วยความจำตั้งแต่ต้นทาง
2. บาง modal หรือ tab ยัง `map()` ข้อมูลทั้งก้อนโดยไม่มี window, `load more` หรือ loading state ที่แยกชัดเจน

จุดที่ควรทำก่อนมี 5 กลุ่ม:

- ประวัติโทเคน: ปัจจุบัน summary ส่ง recent events มา 50 รายการ และ `TokenDashboard` filter ฝั่ง client; ยังไม่ได้ใช้ endpoint history แบบแบ่งหน้า
- `AssetPanel`: library โดยเฉพาะ SFX จำนวนมากยังไม่มี pagination/window ในรายการที่แสดง
- `ContentTrackerHub`: Script Library, Posted Archive และ grouped scripted board ยัง render รายการทั้งกลุ่ม
- Inventory Analytics: ได้รายการ product health ทั้งหมดจาก backend และ render ทั้งหมด
- Shell/data loading: exports, raw videos, raw vault, assets, products และ schedule queue ยังมี endpoint ที่ส่งข้อมูลทั้งหมด แม้บางหน้าแสดงผลแบบ “โหลดเพิ่ม” แล้ว

## สถานะที่มีอยู่แล้ว

จุดเหล่านี้มีการจำกัด DOM หรือมี backend cap แล้ว จึงไม่ใช่ priority แรก:

| จุด | การป้องกันที่มีอยู่ | หมายเหตุ |
|---|---|---|
| Export Gallery | แสดงครั้งละ 24 | ยัง fetch exports ทั้งหมดจาก `/api/exports` |
| Media Assets Hub | แสดงครั้งละ 40 | `/api/assets/all` ยังส่งทุกหมวดพร้อมกัน |
| Media Picker | แสดงครั้งละ 40 | `/api/videos` ยังส่งวิดีโอทั้งหมด |
| Raw Vault | แสดงครั้งละ 40 + lazy image | `/api/raw-vault` ยังส่ง metadata ทั้งหมด |
| Content Tracker flat/table | 20 ต่อ phase และ 40 ต่อ table | grouped board และ modal บางตัวไม่มี cap |
| Schedule posted history | 50 ต่อรอบ | active queue ยังโหลดตาม query ที่ frontend ไม่ได้จำกัดช่วงเวลา |
| Performance table | 50 ต่อรอบ | KPI/chart ยังต้องใช้ aggregate ทั้งชุด |
| Active tasks | backend จำกัด default 50 | ยังไม่จำเป็นต้องทำ pagination ด่วน |
| Production analytics | recent productions จำกัด 15 | response เหมาะสมแล้ว |
| Storage analytics | heavy products จำกัด 10 | response เหมาะสมแล้ว |

## Audit รายจุด

| Priority | จุด | หลักฐานจากโค้ด | ปัญหา | แนวทาง |
|---|---|---|---|---|
| P0 | Token history | `TokenDashboard` ใช้ `getTokenSummary()` และ filter `recent_events` ฝั่ง client; backend มี `/api/tokens/history` แยกอยู่แล้ว | ผู้ใช้ดูประวัติได้แค่ preview 50 รายการ และไม่มี load more/filter ที่ server | เพิ่ม cursor pagination ตาม `timestamp + event id`; response มี `events`, `has_more`, `next_cursor`; เพิ่ม filter date/model/task และโหลดเต็มเมื่อเปิดส่วนประวัติ |
| P1 | Editor AssetPanel | `AssetPanel` มีหมายเหตุว่า SFX 1,800+ รายการทำให้ panel freeze แต่รายการหลักยังไม่มี window/load more | render รายการเพลง/SFX/sticker/effect มากเกินไป โดยเฉพาะเมื่อ search/filter คืนผลจำนวนมาก | ทำ shared list window 40 รายการต่อ tab + `loadingMore`; lazy-load แต่ละ asset category เมื่อเปิด tab |
| P1 | Content Tracker modals | Script Library และ Posted Archive ใช้ `filtered.map()` ใน modal; grouped scripted board map `grp.angles` ทั้งกลุ่ม | modal scroll ได้แต่ยัง mount DOM/video ทั้งหมด; product ที่มี angles มากจะช้า | เพิ่ม search/filter server-side ในระยะถัดไป; ระยะเร็วใช้ window 40 และ load more แยกต่อ modal/group |
| P1 | Inventory Analytics | `/analytics/inventory` คืน `products` ทั้งหมด; tab map `filteredProducts` ทั้งชุด | payload และ DOM โตตามจำนวนสินค้า | endpoint รับ `q`, readiness/status, `limit`, `offset` หรือ cursor; summary แยกจาก rows; UI มี table pagination + skeleton |
| P1 | App shell / exports | `App.refreshData()` โหลด shell และ exports แต่ไม่มี loading state ที่ส่งถึง gallery; errors ถูกจับแบบเงียบ | ผู้ใช้แยกไม่ออกระหว่างกำลังโหลด, ไม่มีข้อมูล, หรือโหลดล้มเหลว | แยก `initialLoading`, `refreshing`, `error`; คงข้อมูลเก่าระหว่าง refresh; เพิ่ม skeleton/retry |
| P1 | Raw videos / Raw Vault | `/api/videos` และ `/api/raw-vault` คืนข้อมูลทั้งหมด; UI ค่อย slice ฝั่ง client | network/memory ยังสูง แม้ DOM จะถูกจำกัด | เพิ่ม query ตาม product/search/page; โหลดรายการ metadataก่อน แล้วโหลด thumbnail/detail เมื่อจำเป็น |
| P1 | Assets all | `/api/assets/all` คืน sfx, music, fonts, stickers, luts, effects พร้อมกัน | เปิดหน้าเดียวแต่โหลดทุกหมวด รวมถึงรายการขนาดใหญ่ | แยก `/assets/{category}` หรือ `category`, `q`, `limit`, `cursor`; cache เป็นรายหมวด |
| P1 | Products | `/products` คืน products พร้อม nested angles ทั้งหมด | ทุกหน้าที่ต้องการแค่ product option รับข้อมูลละเอียดเกินจำเป็น | เพิ่ม lightweight `/products/options`; เพิ่ม product/angle query สำหรับ Content Tracker |
| P1 | Schedule queue | endpoint รองรับ `status`, `date_from`, `date_to` แต่ frontend เรียกโดยไม่จำกัด query | queue/history โตแล้ว response ใหญ่; bulk modal บางรายการ map ทั้งชุด | default โหลดช่วงวันที่ใช้งานจริง; history ใช้ page/cursor; bulk preview cap + search |
| P2 | TikTok/performance | table มี client window 50 แต่ endpoint latest ยังส่งชุดใหญ่ | ตารางปลอดภัยระดับ DOM แต่ payload ยังโต | แยก aggregate summary จาก paginated post rows; ใช้ server filter/sort |
| P2 | Pending metrics | `pendingRows.map()` ไม่มี visible cap | ถ้าคิว pending สะสมจะยาวผิดปกติ | cap 20 พร้อม “ดูทั้งหมด” หรือ endpoint page |
| P2 | Post log | `/api/post-log` คืน posts ทั้งหมด | ประวัติโพสต์เป็นข้อมูลสะสมระยะยาว | เพิ่ม cursor pagination และ date/status filter |
| P2 | Producer notes | `/producer/notes` คืน notes ทั้งหมดและอาจมีรูปใน payload | โหลดหน้า Producer Hub หนัก และรูปไม่จำเป็นสำหรับ list | list endpoint คืน metadata; detail endpoint โหลด body/image เมื่อเปิด note |
| P2 | Projects / Project Selector | `/projects` และ product selector มีแนวโน้มโหลดรายการทั้งหมด | project history โตแล้วจะกระทบ startup และ dropdown | เพิ่ม options/search endpoint; project list page/cursor |
| P2 | Producer Hub | โหลด products, exports, stats, notes, queue หลาย resource พร้อมกัน | burst ใหญ่และ loading state รวมไม่บอกว่าจุดไหนช้า | lazy-load ตาม panel/tab; loading/error แยกราย resource |
| P3 | Activity Center / tasks | active tasks ถูก backend cap 50 และ cache local เหลือ 20 | มีขอบเขตแล้ว ไม่ใช่คอขวดหลัก | เพิ่ม refresh/loading indicator และ retry เท่านั้น |
| P3 | Production/Storage analytics | server cap recent 15/heavy 10 อยู่แล้ว | response มีขนาดควบคุมได้ | ไม่ต้อง paginate ตอนนี้; รักษา cap และ loading state เดิม |
| P3 | Token model/task breakdown | เป็น aggregate ขนาดเล็ก | pagination จะเพิ่มความซับซ้อนโดยไม่ช่วย | คงเป็น aggregate |

## แผนดำเนินงานที่แนะนำ

### Phase 1 — แก้จุดที่ผู้ใช้เห็นชัดและลดการ render (P0/P1)

1. Token history
   - คง summary สำหรับ KPI/กราฟ และลด recent preview ให้เป็นข้อมูลสั้น ๆ
   - เพิ่ม history query แบบ cursor พร้อม reset เมื่อเปลี่ยน filter
   - UI แยกสถานะ `loading initial`, `loading more`, `refreshing`, `error`
   - เพิ่ม empty state และป้องกันการกด “โหลดเพิ่ม” ซ้ำ

2. AssetPanel
   - เพิ่ม list window 40 ต่อ category
   - แยก initial load ของ category ที่เปิดอยู่จาก category อื่น
   - รักษา search แต่ไม่ mount ผลลัพธ์ทั้งหมด

3. ContentTrackerHub
   - เพิ่ม window/load more ให้ Script Library และ Posted Archive
   - จำกัด grouped scripted cards ต่อ group และโหลดเพิ่มเมื่อผู้ใช้ขยาย
   - กำหนด cap ให้ bulk preview/autofill preview

4. Inventory Analytics
   - เพิ่ม server-side query/filter/page
   - ให้ summary/KPI ไม่ขึ้นกับจำนวนแถวที่โหลดมาในหน้านั้น
   - เพิ่ม table skeleton และ retry state

### Phase 2 — ลด network payload และ startup cost (P1)

1. แยก resource endpoint ของ assets และโหลดตาม category
2. เพิ่ม lightweight product options endpoint
3. เพิ่ม pagination/query ให้ raw videos, raw vault และ exports
4. จำกัด schedule queue ด้วย status/date window ตั้งแต่ frontend call แรก
5. นำ loading contract ไปใช้กับ App shell และ Producer Hub

### Phase 3 — ประวัติระยะยาวและ analytics (P2)

1. Paginate TikTok/performance rows แต่คง aggregate KPI/chart แยกต่างหาก
2. Paginate post log และ producer notes
3. Paginate projects และเปลี่ยน dropdown ให้อยู่บน search/options endpoint
4. เพิ่ม date range/downsampling ให้ token daily stats หากมีข้อมูลหลายเดือน/ปี
5. เพิ่ม page/search ให้ pending metrics และ bulk modal เมื่อข้อมูลจริงเริ่มโต

## Loading contract ที่ควรใช้ร่วมกัน

ทุก list ที่โหลดจาก API ควรมีสถานะมาตรฐาน:

```text
initialLoading  = ยังไม่มีข้อมูลและกำลังโหลดครั้งแรก
refreshing      = มีข้อมูลเดิมอยู่และกำลังดึงข้อมูลใหม่
loadingMore     = กำลังต่อ page/cursor ถัดไป
error           = โหลดไม่สำเร็จ พร้อม retry
hasMore         = server ยืนยันว่ามีข้อมูลต่อ
```

หลัก UX:

- refresh แล้วคงข้อมูลเดิมไว้ ไม่ทำให้จอว่าง
- ปุ่มโหลดเพิ่มต้อง disable ระหว่าง request
- เปลี่ยน search/filter ต้อง reset cursor และยกเลิกผลลัพธ์ request เก่า
- แยก “ไม่มีข้อมูล” ออกจาก “ยังโหลดไม่เสร็จ”
- tab ที่ยังไม่เปิดไม่ควรโหลด resource ขนาดใหญ่
- งาน scan/คำนวณนานควรแสดง stale data พร้อมสถานะกำลัง refresh แทนการ blank screen

## รูปแบบ API ที่แนะนำ

สำหรับข้อมูลที่มีการเพิ่มใหม่ระหว่างผู้ใช้เปิดหน้า ให้ใช้ cursor มากกว่า offset:

```json
{
  "items": [],
  "has_more": true,
  "next_cursor": "...",
  "total": null
}
```

ใช้ offset/page ได้กับข้อมูลที่ stable เช่น inventory snapshot หรือ table ที่มี total count ต้องแสดงชัดเจน:

```json
{
  "items": [],
  "page": 1,
  "page_size": 40,
  "total": 1234,
  "total_pages": 31
}
```

ข้อสำคัญ: อย่า paginate aggregate ที่ใช้ทำ KPI โดยตรง ให้ server ส่ง aggregate แยกจาก rows ที่ paginate แล้ว

## สิ่งที่ยังไม่ควร paginate

- model/task token breakdown ที่เป็น aggregate ขนาดเล็ก
- production recent ที่ server cap ไว้ 15
- storage directory cards และ heavy products ที่ cap ไว้ 10
- active tasks ที่ backend จำกัด 50 และใช้เป็น operational snapshot
- ตัวเลือกสินค้าจำนวนเล็กน้อยใน dropdown; หากโตมากให้เปลี่ยนเป็น options search แทนการทำ page แบบเต็ม

## แผนทดสอบและ acceptance criteria

- ตรวจ initial/refresh/load-more/error/empty state ของทุกจุดที่แก้
- เปลี่ยน search/filter ระหว่าง request แล้วต้องไม่ให้ผลลัพธ์เก่าทับผลลัพธ์ใหม่
- กดโหลดเพิ่มซ้ำเร็ว ๆ ต้องมี request เดียวและไม่มีรายการซ้ำ
- ตรวจว่า summary/KPI ไม่เปลี่ยนเพราะ table โหลดมาเพียงบาง page
- ทดสอบ dataset จำลองขนาดใหญ่โดยไม่สร้างไฟล์ทดสอบค้างใน `04_Exports/`
- ตรวจ browser จริงที่ Analytics Hub, Token Dashboard, AssetPanel, Content Tracker และ Inventory Analytics
- หลัง implement ให้รัน deterministic/offline tests ตาม testing standard และบันทึกผล verify แยกจากแผนนี้

## ไฟล์อ้างอิงหลัก

- `frontend/src/components/TokenDashboard.jsx`
- `scripts/api_tokens.py`
- `scripts/token_tracker.py`
- `frontend/src/components/editor/AssetPanel.jsx`
- `frontend/src/components/ContentTrackerHub.jsx`
- `frontend/src/components/analytics/tabs/InventoryAnalyticsTab.jsx`
- `frontend/src/App.jsx`
- `frontend/src/lib/workspaceData.js`
- `scripts/api_videos.py`
- `scripts/api_exports.py`
- `scripts/api_analytics.py`
- `scripts/api_schedule_queue.py`
- `PAGINATION_PLAN.md` (แผนเดิมที่มีรายการที่ทำไปแล้วบางส่วน)

