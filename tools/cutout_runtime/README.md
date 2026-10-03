# SAM2 runtime แยกสำหรับ GPU Cutout

ดำเนินการโดย: Codex / sam2_integration (GPT-6) · 2026-10-03

`requirements.txt` และ `requirements.lock.txt` เดิมเป็น **CPU feasibility**
จึงไม่ใช่ชุดติดตั้งสำหรับ SAM2 GPU ในโปรแกรม ใช้ `requirements.gpu.txt`
สำหรับ runtime CUDA ที่ตรวจจริงกับ RTX 4060 / torch 2.6.0+cu124
แพ็กเกจ GPU อยู่ใน venv นี้ ไม่ต้องลง torch ใน venv ของ FastAPI

## ย้ายไปเครื่องใหม่

Git ไม่ส่ง venv และ checkpoint ให้ ต้องสร้าง venv บนเครื่องปลายทางใหม่
และวาง checkpoint ที่มีอยู่ให้ resolver พบ ไม่คัดลอก venv ข้ามเครื่อง
คำสั่งด้านล่างเป็นขั้นตอนติดตั้งบนเครื่องที่ยังไม่มี runtime เท่านั้น
งานตรวจครั้งนี้ใช้ runtime/checkpoint เดิม ไม่ติดตั้งหรือดาวน์โหลดเพิ่ม

จากรากโปรเจกต์ บน Windows และ Python 3.10 (runtime ที่ตรวจจริงคือ 3.10.11):

```powershell
py -3.10 -m venv tools/cutout_runtime/.venv
tools/cutout_runtime/.venv/Scripts/python.exe -m pip install -r tools/cutout_runtime/requirements.gpu.txt
$env:SAM2_BUILD_CUDA='0'
tools/cutout_runtime/.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation ../external_repos/sam2
```

SAM2 source ที่ตรวจจริงคือ commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`
ใน `../external_repos/sam2` ใช้ชุดเดียวกันเมื่อสร้าง runtime ใหม่
`SAM2_BUILD_CUDA=0` ปิดการ build extension เพิ่มบน Windows;
การอนุมานของ torch ยังทำงานบน CUDA และ worker ใช้ `apply_postprocessing=False`
Linux/macOS resolver เลือก `tools/cutout_runtime/.venv/bin/python` ตามระบบ
SAM2 worker นี้ต้องมี NVIDIA CUDA; CPU runtime จะถูก preflight ปฏิเสธ

## กำหนดตำแหน่งโดยไม่ผูกกับ drive

ตั้งใน environment หรือ `.env` ของโปรเจกต์ได้:

- `OMNICUT_SAM2_PYTHON`: interpreter ของ GPU venv เมื่ออยู่ตำแหน่งอื่น
- `OMNICUT_SAM2_CHECKPOINT_DIR`: โฟลเดอร์ checkpoint เมื่ออยู่ตำแหน่งอื่น

ค่า relative อ้างจากรากโปรเจกต์ ตัวอย่าง `OMNICUT_SAM2_CHECKPOINT_DIR=tools/local-models`
ถ้าไม่ตั้งค่า resolver หาโมเดลที่เลือกตามลำดับ:

1. โฟลเดอร์ override
2. โฟลเดอร์ `cutout-models` ข้าง cache ของงาน
3. `03_Projects/.cache/cutout-models`
4. `../external_repos/sam2/checkpoints`

ชื่อไฟล์ต้องตรงโมเดล: `sam2.1_hiera_tiny.pt`, `sam2.1_hiera_small.pt`,
`sam2.1_hiera_base_plus.pt` หรือ `sam2.1_hiera_large.pt`
ถ้าเลือก small/base/large แต่ไม่มีไฟล์ ระบบรายงาน error และไม่แอบใช้ tiny
ไม่มีการดาวน์โหลด checkpoint อัตโนมัติ

## ตรวจบนเครื่องปลายทาง

```powershell
.venv/Scripts/python.exe -c "from scripts.cutout_runtime import probe_sam2_runtime; print(probe_sam2_runtime())"
$env:OMNICUT_TEST_SAM2_GPU='1'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m pytest tests/test_sam2_gpu_api_integration.py -q -s -p no:cacheprovider
Remove-Item Env:OMNICUT_TEST_SAM2_GPU
```

GPU acceptance ส่ง positive/negative points รูปแบบเดียวกับ UI ผ่าน API, task,
worker และ CUDA จริง ตรวจ product mask/มือ/alpha ที่ 1080×1920,
proxy 540×960, cache reuse และ point invalidation ด้วยวัตถุดิบจำลองใน temp
พร้อม cleanup ทั้ง source/cache/task registry ทันที
ชุดเทสทั่วไปข้าม GPU acceptance เพื่อให้ deterministic/offline

Points เป็นพิกัด 0–1 บนเฟรม **fit/letterbox** ของ worker
`active_intervals` ใช้เวลาของ source, รวม begin และไม่รวม end
SAM2 ติดตามทั้งช่วงเพื่อคง temporal memory แล้วซ่อน alpha นอก interval
จึงไม่ใช่การลดจำนวนเฟรม inference บน GPU
เฟรม input 1024×1024 RGB float32 เก็บใน RAM (12 MiB/เฟรม)
เพื่อไม่ให้คลิปยาวกิน VRAM จนหมด การอนุมานและ state ยังอยู่บน CUDA
Preflight ประเมิน RAM เป็นจำนวนเฟรมทั้งช่วง × 12 MiB + overhead 1 GiB
ถ้า RAM ว่างไม่พอให้ตัดช่วง source ให้สั้นลง ตัวเลขนี้เป็น capacity estimate
และไม่ใช่ผลวัด peak RAM ของทั้งโปรเซส
ถ้าไม่ระบุ duration ใน API ระบบ probe ความยาว source จริงลบ start ก่อนประเมิน
ถ้าอ่านไม่ได้ preflight จะปฏิเสธและขอ duration; worker ตรวจ RAM ซ้ำตามจำนวน
เฟรมที่ decode จริงเพื่อครอบคลุมการเรียก `/process` โดยตรง
Master alpha นอก interval เป็น 0; proxy VP9 อาจปัดเศษ alpha เป็น 1/255
ผลความเร็ว/คุณภาพจากวัตถุดิบจำลองต้องไม่ใช้รับประกันทุกคลิปจริง
