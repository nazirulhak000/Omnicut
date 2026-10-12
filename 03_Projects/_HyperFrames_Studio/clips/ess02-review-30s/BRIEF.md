---
workflow: general-video
flow: automation
storyboard: no
message: "Essager PD 30W ชาร์จไว เล็ก ปลอดภัย กดตะกร้าเหลือง"
destination: tiktok
aspect: 1080x1920
language: th
length: 30s
---

## Intent

รีวิวหัวชาร์จ Essager PD 30W ลง TikTok ~30 วิ ให้ไวรัล ดูสนุก motion graphic สวย — ผู้ใช้ไม่เอาป้าย popup/pill แบบ AI และให้อิสระเต็มที่ ("นายจะตัดยังไงก็ได้ตามนายต้องการ").
Concept: ทุกจุดขายกระแทกเข้ามาเหมือนไฟช็อต — hook มืด/เบลอ (หัวชาร์จเก่าช้า) → สายฟ้าเผยของจริงคมชัด → kinetic type + data readouts ซิงก์คำพูด.

## Assets

- assets/footage.mp4 — 01_Raw/9505b042.../Essager 30w.mov, 1080x1920 30fps + lut_tech_cool_contrast.cube
- assets/voiceover.wav — Gemini Fenrir commercial_premium (03_Projects/ESS02-รีวิว30วิ_1/script.txt)
- whisper_words.json — faster_whisper large-v3-turbo timestamps → build_timing.py → assets/timing.js
- assets/img/hero_cutout.png — rembg u2net cutout of frame 3.6s

## Customizations

- Channel rules (Omnicut AGENTS): karaoke captions Anuphan-Bold yellow #FFE600 active word, no emoji, camera audio muted, BGM 0.12, red vertical watermark rizanntry.

## Notes

- No cyan pills, no AI-template popups.
