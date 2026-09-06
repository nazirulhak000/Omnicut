# OmniCut Frontend

React 19 + Vite frontend สำหรับ Product-to-Clip, Script Lab, Asset Library, Content Tracker, Export Gallery และ Editor แบบ multi-track

## รันระบบ

```powershell
npm install
npm run dev
```

Frontend ใช้ `/api` ไปยัง FastAPI ที่ port 8000 ผ่านค่าของ Vite ใน `vite.config.js`

## คำสั่งตรวจ

```powershell
npm test
npm run build
npm run lint
```

`npm test` ใช้ Node built-in test runner และเก็บ test ของ pure logic ไว้ที่ `src/lib/*.test.js` ไม่ต้องเพิ่ม Jest หรือ Vitest หากยังไม่มีเหตุผลที่ต้อง render component DOM

## โครงสร้าง Editor

- `components/editor/EditorShell.jsx`: ประกอบหน้าจอและเชื่อม state/hook
- `components/SequencePlayer.jsx`: Canvas preview และ audio preview
- `components/editor/Timeline.jsx`: timeline composition
- `components/editor/timeline/`: ruler, playhead, headers และ context menu
- `components/editor/inspector/`: inspector แยกตามชนิด selection
- `hooks/useProjectLoader.js`: โหลดโปรเจกต์และกัน stale response
- `hooks/useProjectAutosave.js`: debounce, flush และ page unload save
- `hooks/useRenderJob.js`: polling, resume และ cleanup งาน render
- `hooks/useEditorHistory.js`: undo/redo document state
- `lib/editorProjectState.js`: manifest migration และ save serializer
- `lib/timelineSchema.js`: Timeline Document v2 และ migration
- `lib/timelineMath.js`: เวลา, split, trim, transition, snap และ ripple
- `lib/overlayModel.js`: model สำหรับ hook/text overlay ที่ mirror กับ Python
- `lib/keyframeModel.js`: keyframe interpolation ที่ mirror กับ renderer

## กฎสำคัญ

- Manual Save, Autosave และ pre-render save ต้องใช้ `editorStateToSavePayload()` ชุดเดียว
- Logic ที่ทดสอบได้ให้แยกเป็น pure function ใน `src/lib/` แล้วเพิ่ม `.test.js`
- อย่าถือ copy ของ Editor document ใน Inspector; ทุก control ต้อง patch field ที่เลือกผ่าน command กลาง
- การเพิ่ม listener, interval หรือ timeout ต้องคืน cleanup ใน effect เสมอ
- การแก้ภาพใน `SequencePlayer.jsx` ต้องแก้ renderer คู่กันและทำตาม `../.agents/rules/preview_render_parity.md`
- ปุ่มต้องทำตาม `../.agents/rules/ui_clean_standard.md` ห้ามใส่สัญลักษณ์ซ้ำกับ icon

อ่านภาพรวมทั้งระบบที่ [ARCHITECTURE.md](../ARCHITECTURE.md) และสถานะงานล่าสุดที่ [TODO.md](../TODO.md)
