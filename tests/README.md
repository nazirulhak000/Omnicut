# Automated Test Suites

รันจากรากโปรเจกต์:

```powershell
python -m pytest tests/ -q -p no:cacheprovider --tb=short
```

สถานะตรวจล่าสุด 2026-09-05: `336 passed, 5 warnings in 44.08s`

## ชุดหลัก

- `test_backend_api_contracts.py`: FastAPI route และ schema contracts
- `test_refactor_baseline_contracts.py`: manifest เก่า, Editor payload และ save/reload
- `test_pipeline_stages.py`: stage order, reroll reuse และ failure reporting
- `test_preview_render_parity.py`: source contracts ระหว่าง Canvas กับ Python renderer
- `test_preview_render_behavior.py`: render คลิปสังเคราะห์จริงใน temp directory
- `test_subtitle_snapshot.py`: ASS output และ Thai layout snapshots
- `test_keyframe_parity.py`: interpolation parity ระหว่าง Python/JavaScript
- `test_error_handling_recovery.py`: error mapping, atomic save และ recovery
- `test_final_compatibility_signoff.py`: compatibility/sign-off gate
- `test_phase1_smoke.py`: regression coverage ของ manifest, media, pipeline และ renderer

ไฟล์ใน `conftest.py` คือ manual diagnostics รุ่นเก่าที่ถูกกันออกจาก pytest เพราะบางไฟล์ render หรือเรียกบริการภายนอกตั้งแต่ import ห้ามเพิ่มรายชื่อใหม่เพื่อซ่อน test ที่ล้ม ให้ย้ายสคริปต์ทดลองใหม่ไป `tools/` แทน

Frontend tests รันแยก:

```powershell
Set-Location frontend
npm test
```

อ่านกฎเต็มที่ [.agents/rules/testing_standard.md](../.agents/rules/testing_standard.md)
