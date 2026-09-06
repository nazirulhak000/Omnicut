# กฎการเขียนและรัน Test

กฎนี้ใช้กับทุกการเปลี่ยนโค้ดใน OmniCut Pro Studio และใช้ร่วมกับ `work_loop.md`

## หลักการ

1. Test ต้องพิสูจน์พฤติกรรมที่ผู้ใช้หรือโมดูลอื่นพึ่งพา ห้ามเขียน test ที่ทำซ้ำ implementation โดยไม่มี contract เพิ่ม
2. Test ต้อง deterministic, offline และไม่เรียก Gemini, Marketplace หรือบริการภายนอกจริง
3. Test ห้ามอ่าน/เขียน `01_Raw/`, `02_Assets/`, `03_Projects/` หรือ `_Docs/post_log.json` ของจริง ให้ใช้ `tmp_path` และ `monkeypatch`
4. ห้ามวางสคริปต์ทดลองที่มี side effect ตอน import เป็น `tests/test_*.py` หากเป็น manual diagnostic ให้เก็บใต้ `tools/` หรือป้องกันด้วย `if __name__ == "__main__"`
5. Source-text assertion ใช้ได้เฉพาะ contract ที่ต้อง mirror ข้ามภาษาและยังเรียก implementation ร่วมกันไม่ได้ ต้องมี behavioral test คู่กันเมื่อความเสียหายเกิดกับ output จริง

## Gate ตามชนิดงาน

| งานที่แก้ | Test ขั้นต่ำ |
| :--- | :--- |
| Python module | `python -m compileall -q scripts` และ pytest ที่เกี่ยวข้อง |
| FastAPI route/schema | `test_backend_api_contracts.py`, `test_refactor_baseline_contracts.py` และ full pytest |
| Frontend state/math/hook | เพิ่ม Node test ใน `frontend/src/lib/*.test.js`, `npm test`, `npm run build` |
| Editor save/load | ทดสอบ legacy migration, serialize, rapid edits, switch project และ reload |
| Timeline/keyframe | ทดสอบ start/middle/end, clamp, duplicate timestamps, undo/redo และ parity Python/JS |
| ภาพ/ซับ/overlay/motion | source parity + FFmpeg render + ดึงเฟรมช่วงเข้า/ค้าง/ออกมาดูหรือวัดพิกเซล |
| Audio mix | ตรวจ Voice/BGM/SFX/clip gain, mute และ artifact reuse |
| Subprocess | ทดสอบ exit code, timeout, stderr ที่จำกัดขนาด และข้อความแก้ปัญหา |

## คำสั่งมาตรฐาน

```powershell
python -m compileall -q scripts
python -c "import scripts.api_server as app; print(len(app.app.routes))"
python -m pytest tests/ -q -p no:cacheprovider --tb=short
Set-Location frontend
npm test
npm run build
```

ก่อนปิดรอบให้รัน `git diff --check` และบันทึกจำนวน pass/fail/skip/warning จริงลง `TODO.md`

## โครงสร้างชุดทดสอบ

- `tests/test_backend_api_contracts.py`: route/method/request/response contracts
- `tests/test_pipeline_stages.py`: stage orchestration, reuse และ failure reporting
- `tests/test_preview_render_parity.py`: cross-language source contracts
- `tests/test_preview_render_behavior.py`: black-box FFmpeg output
- `tests/test_subtitle_snapshot.py`: ASS/subtitle snapshots
- `tests/test_keyframe_parity.py`: Python/JavaScript interpolation parity
- `tests/test_error_handling_recovery.py`: failure categories และ recovery
- `tests/test_final_compatibility_signoff.py`: compatibility gate รวม
- `frontend/src/lib/*.test.js`: pure frontend behavior ผ่าน Node test runner

Warning ที่รู้จักยังไม่ถือเป็น failure แต่ต้องบันทึกไว้ ห้ามเพิ่ม warning ใหม่โดยไม่อธิบาย ปัจจุบันมี Starlette TestClient deprecation 1 รายการ และ audioread/librosa fallback/deprecation 4 รายการ
