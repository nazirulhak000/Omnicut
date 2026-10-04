# HOY01 — Export ใหม่หลังเปลี่ยนช็อตติดมือถือ

Round CODEX-HOY01-FINAL-EXPORT-20261004 · ดำเนินการโดย: Codex (GPT-6)

ผู้ใช้อนุญาตให้เรนเดอร์ผลงานจริงต่อจากรอบเปลี่ยนช็อต 3 ทั้งสองโปรเจกต์ ใช้ manifest ล่าสุด เสียง mixed audio และ ASS ที่บันทึกไว้ ไม่มีการสร้างเสียงหรือซับใหม่

ส่งมอบใน `04_Exports/Ready_to_post/`:

- `20261004_HOY01_รีวิวสเปก_v1.mp4`
- `20261004_HOY01_เทียบของเดิม_v1.mp4`

แต่ละไฟล์มี thumbnail `.webp` ใช้ภาพสินค้าติดมือถือ ผูก export ID ใหม่ผ่าน ExportRegistry และอัปเดต artifact ใน manifest กับสถานะมุมสินค้าเป็น `rendered` ผ่าน ProductStore ตรวจ pointer ทั้งสามตรงกัน ไม่ทำเครื่องหมายว่ามนุษย์ตรวจ QC หรือโพสต์แล้ว

ตรวจ ffprobe: 1080×1920, 30 FPS มี video/audio stream ระยะเวลาต่างจาก manifest น้อยกว่า 0.06 s; decode ทั้งไฟล์ผ่าน ไม่พบช่วงดำ ≥0.1 s ด้วย blackdetect `pix_th=0.1,pic_th=0.98` ตรวจภาพต้นคลิป ช็อตติดมือถือสามช่วง และท้ายคลิปพร้อมซับไทย/อังกฤษจริง

เส้นทางที่ตรวจ: manifest → VideoEditor → ไฟล์ staged ใน `.tmp/` → ตรวจ decode/เฟรมจริง → ย้ายเป็นผลงานจริง → ExportRegistry → manifest artifact → ProductStore angle → อ่านตรวจ ID และสถานะกลับ ผลตรวจไม่ใช่การทดสอบแรงยึด กำลังไฟ AI หรือคำอ้างประสิทธิภาพสินค้า และ hook เดิมยังคงอยู่

สำรอง manifest ก่อนอัปเดตเป็น `project.json.before_codex_final_export_20261004.bak` ในแต่ละโปรเจกต์ พร้อม snapshot metadata ก่อนเปลี่ยนใน `HOY01_FINAL_EXPORT_METADATA_BEFORE_20261004.json` เก็บ Export เก่าไว้และตรวจ SHA-256 ไม่เปลี่ยน เสียงและ ASS hash ไม่เปลี่ยน ใช้ revision guard ก่อนผูก artifact ใหม่ อัปเดต fingerprint ของไฟล์ใหม่ให้ valid; ไม่สร้าง stage fingerprint จากข้อมูลที่ไม่ได้ผ่าน pipeline fingerprint builder

Jev ให้คะแนนความเสี่ยง 0.65/4, confidence 0.62; ใช้ measured gate ที่ผู้ใช้อนุญาตไว้สำหรับงาน HOY01 ผลนี้เป็นคำแนะนำจากสรุปข้อความ ไม่ใช่หลักฐานภาพ ไม่มีการแก้ production code หรือไฟล์ของเอเจนต์อื่น

ผลตรวจเป็นข้อมูลบันทึกด้านล่าง ภาพและไฟล์ตรวจชั่วคราวล้างออกหลังบันทึกผล เก็บเฉพาะผลงานจริง thumbnail และ backup ที่จำเป็น

## Verification records

```json
[
  {
    "project": "HOY01-รีวิวสเปก_1",
    "manifest": "03_Projects/HOY01-รีวิวสเปก_1/project.json",
    "hash": "ee58c000bcf0ee016fce538c724fb26e58b3032de615daa395b6d0fc056010b7",
    "backup": "03_Projects/HOY01-รีวิวสเปก_1/project.json.before_codex_final_export_20261004.bak",
    "old_export": "04_Exports/Ready_to_post/HOY01-รีวิวสเปก_1_20260927_202531.mp4",
    "old_export_sha256": "96f8f2848505d35faa634dffafbda329e4e8ff16854862de3528817efc6e340d",
    "product_id": "673882d55bd84c57ba805000a910c466",
    "angle_id": "spec_review",
    "angle_status": "rendered",
    "staging": ".tmp/hoy01_final_export_20261004/spec_review_final.mp4",
    "final_path": "04_Exports/Ready_to_post/20261004_HOY01_รีวิวสเปก_v1.mp4",
    "audio_ass_hashes": {
      "voice_audio": "a33fe43a16022d90ca91acb894bbfbaad47232a9f9c28c8bbf3f99982bfd614b",
      "mixed_audio": "bdd6a0c2aa2dd459ca0c3c6d87ce29a01e5d98a78c185c9ca9184f2787b5165e",
      "subtitles_ass": "5d4ade47e1c05e197e44040980bc0c71496a60c5371d6cf02743acbca3ae37da"
    },
    "render_seconds": 9.447,
    "validation": {
      "probe": {
        "programs": [],
        "stream_groups": [],
        "streams": [
          {
            "codec_name": "h264",
            "codec_type": "video",
            "width": 1080,
            "height": 1920,
            "r_frame_rate": "30/1"
          },
          {
            "codec_name": "aac",
            "codec_type": "audio",
            "r_frame_rate": "0/0"
          }
        ],
        "format": {
          "duration": "35.215011",
          "size": "69685246"
        }
      },
      "full_decode_ok": true,
      "black_intervals": [],
      "visual_sample_times": [
        0.5,
        11.9,
        14.5,
        16.2,
        34
      ]
    },
    "sha256": "37b9b610ca6015b222c31facea091558df34b3c5802ddf579c2b56bec5eee204",
    "export_id": "exp_f016509c6b7e48049d1c23d95bc6aec1",
    "thumbnail": "04_Exports/Ready_to_post/20261004_HOY01_รีวิวสเปก_v1.webp",
    "manifest_after_sha256": "ecd6ee6ec5916026adbdb716d05da9b0dcec757407528b5b70ac2955f775e378",
    "visual_review": "Product-on-phone frames and existing Thai/English captions checked at listed times; hook unchanged; no independent product-performance proof"
  },
  {
    "project": "HOY01-เทียบของเดิม_1",
    "manifest": "03_Projects/HOY01-เทียบของเดิม_1/project.json",
    "hash": "82be736b72273e07773a0cab522b5c3c65329e52abd022006925b56910f1b356",
    "backup": "03_Projects/HOY01-เทียบของเดิม_1/project.json.before_codex_final_export_20261004.bak",
    "old_export": "04_Exports/Ready_to_post/HOY01-เทียบของเดิม_1_20261004_151528.mp4",
    "old_export_sha256": "6b2e29c5ad2b7ea0046106e159cf00ca0125d29d85890f63a019fce9d0421e79",
    "product_id": "673882d55bd84c57ba805000a910c466",
    "angle_id": "comparison",
    "angle_status": "rendered",
    "staging": ".tmp/hoy01_final_export_20261004/comparison_final.mp4",
    "final_path": "04_Exports/Ready_to_post/20261004_HOY01_เทียบของเดิม_v1.mp4",
    "audio_ass_hashes": {
      "voice_audio": "6aa4067a802778c93b70b92c365e9222e9b93747cfb3fa0331fbbb71e4005f8b",
      "mixed_audio": "a2ee0c36493f9d73c5d17ec17124c0c507d27168ed965ce44968bc43fc63810e",
      "subtitles_ass": "17c039e74405ab730e3a4ba4243938355c32b811b4ef8e646035ab509cef4715"
    },
    "render_seconds": 19.582,
    "validation": {
      "probe": {
        "programs": [],
        "stream_groups": [],
        "streams": [
          {
            "codec_name": "h264",
            "codec_type": "video",
            "width": 1080,
            "height": 1920,
            "r_frame_rate": "30/1"
          },
          {
            "codec_name": "aac",
            "codec_type": "audio",
            "r_frame_rate": "0/0"
          }
        ],
        "format": {
          "duration": "27.237007",
          "size": "54045702"
        }
      },
      "full_decode_ok": true,
      "black_intervals": [],
      "visual_sample_times": [
        0.5,
        11,
        12,
        14,
        26
      ]
    },
    "sha256": "64e852e6fdbbbd85e341921b1b9ed2e7d39ee167fad3a1b0d6235a8eb6444616",
    "export_id": "exp_397071b4708a48d3a59c27a5659356ec",
    "thumbnail": "04_Exports/Ready_to_post/20261004_HOY01_เทียบของเดิม_v1.webp",
    "manifest_after_sha256": "5a15d72f8c563d068f0370a13664f3953d50b970eb1681818028e87a748eeceb",
    "visual_review": "Product-on-phone frames and existing Thai/English captions checked at listed times; hook unchanged; no independent product-performance proof"
  }
]
```

Final Jev report assessment: score3.53/4, confidence0.61 (escalate); retained the user-authorized measured gate, not treated as proof.
