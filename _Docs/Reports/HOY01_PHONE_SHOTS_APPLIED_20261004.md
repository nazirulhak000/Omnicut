# HOY01 — เปลี่ยนช็อตติดมือถือ

ดำเนินการโดย: Codex (GPT-6) · 2026-10-04
Round: CODEX-HOY01-APPLY-PHONE-SHOTS-20261004

ผู้ใช้ยืนยันว่ารุ่นตรงกับวัตถุดิบ ติดได้ทั้งหนีบและแม่เหล็ก รองรับ 24W และ AI ข้อมูลนี้เป็นคำยืนยันผู้ใช้ ไม่ใช่ผลวัดกำลังไฟหรือทดสอบแรงยึดแม่เหล็ก

| โปรเจกต์ | ช็อต | ช่วง source เดิม → ใหม่ | Timeline end |
| --- | --- | --- | --- |
| HOY01-รีวิวสเปก_1 | 3 | 0–6.692 → 180–186.692 s | 35.2 s เท่าเดิม |
| HOY01-เทียบของเดิม_1 | 3 | 0–6.673 → 169.75–176.423 s | 27.233333 s เท่าเดิม |

แก้ `clip_list` และสำเนาใน `render_params` พร้อม invalidate video fingerprint อัปเดต revision และเวลา เสียง บท ซับ ฟอนต์ transitions camera keyframes และช็อตอื่นคงเดิม สำรอง manifest แบบ byte-exact เป็น `project.json.before_codex_phone_shots_20261004.bak` ในแต่ละโฟลเดอร์

## Cutout และการตรวจเส้นทางจริง

เป้าหมายคือแทนภาพถาดด้วยภาพสินค้าติดมือถือ การแก้ข้อมูลช็อตใช้ระบบเดิมและเล็กกว่าการเปลี่ยนตัวเลือกช็อตทั้งระบบ ไม่มีการแก้ production code

ตรวจ `project.json` → `resolve_background_isolation_config` → `_read_ready_background_sequence` → `VideoEditor.assemble_tiktok_video` และ production SequencePlayer ใน motion fixture พบสองจุดที่ต้องแก้ก่อนส่ง:

- หน้ากากที่ใช้ prompt ใหม่เฉพาะคลิปขัดกับ prompt ของทั้งโปรเจกต์ จึงไม่ผ่าน resolver และคืน manifest ก่อนลองใหม่
- หน้ากากที่ derive seed อัตโนมัติตาม shared prompt จับฉากหลังผิด แม้เรนเดอร์สำเร็จ จึงปฏิเสธผลหลังดู alpha จริงและคืน manifest

ผลที่ใช้จริง: `bgseq1-fb7e8ecdd9dda464`, SAM2 200 frames สำหรับช่วงใหม่ ระบุ positive seed (0.53, 0.62) และ negative seed (0, 0.99948) ของเฟรมเริ่มช่วงใหม่ ผ่าน operator override เฉพาะ process เดียวของ worker เดิม คง shared prompt context เพื่อชี้ subject เดิม; worker version แยก `-hoy01-reviewed-point-map-20261004` และบันทึก seed จริงใน sequence manifest ไม่ได้แก้ algorithm หรือปลอม cache เดิม ตรวจ alpha 0.2/2.9/5.8 s เห็นตัวพัดลมและสายไฟ ไม่ใช่พื้นหลัง และ resolver ยอมรับ artifact

เก็บเฉพาะ mask ที่ manifest อ้างอิงเป็น production derivative; ลบสองผลทดลองที่ไม่ได้ใช้หลังตรวจว่าไม่มี reference

## การตรวจผลและข้อจำกัด

- Preview/Render geometry 6 จุดผ่านที่ 540×960: รีวิวสเปก mask IoU 0.9991348/0.9999749/0.9993436; เทียบของเดิม **ผลสุดท้าย** 0.9989889/0.9996553/0.9989410; bbox edge delta 0 ทุกจุด ผลเปรียบเทียบเป็นภาพ ไม่มีซับและใช้เสียงเงียบ จึงไม่ได้อ้าง caption pixel parity จาก fixture นี้
- ทั้งสองโปรเจกต์เรนเดอร์เต็มด้วยเสียงและ ASS ที่บันทึกอยู่จริงใน `.tmp/` ได้ 1080×1920, 30 FPS ตรวจเฟรมช็อตใหม่พร้อมซับไทย/อังกฤษจริงและ decode ทั้งไฟล์ผ่าน ไม่พบช่วงดำ ≥0.1 s ที่ blackdetect `pix_th=0.1,pic_th=0.98` ระยะ container 35.215011 และ 27.237007 s; timeline endpoint ไม่เปลี่ยน
- SHA-256 วัตถุดิบ เสียงพากย์ mixed audio และ ASS ทั้งสองโปรเจกต์ไม่เปลี่ยน manifest backup ตรง hash ก่อนแก้ ช็อตอื่นและ unrelated fields คงเดิม
- ภาพแสดงสินค้าติดหลังมือถือและอุปกรณ์หนีบ ไม่พิสูจน์แรงยึดแม่เหล็ก กำลังไฟ หรือ AI ด้วยภาพ รายงานตรวจรุ่นก่อนหน้านี้คงเป็นหลักฐานความไม่แน่นอน ณ เวลาตรวจ
- งานนี้เปลี่ยนเฉพาะช็อต 3; hook เทียบของเก่าและคำอ้างอื่นไม่ได้ถูกแก้หรือประกาศว่าผ่านแล้ว
- Export เดิมยังเป็นฉบับเก่า ต้องเรนเดอร์ใหม่ก่อนใช้งานจริง ผลเรนเดอร์ตรวจทั้งหมดลบทิ้ง ไม่มีไฟล์ทดสอบในโฟลเดอร์ส่งออก ไม่มีการแก้ export registry

Verdict: ส่งต่อโปรเจกต์ที่แก้แล้วได้สำหรับการเรนเดอร์ใหม่ โดยจำกัดผลสำเร็จอยู่ที่การแทนช็อตและหน้ากากที่ตรวจจริง

## Preservation evidence

```json
{
  "manifests": [
    {
      "project": "HOY01-รีวิวสเปก_1",
      "path": "03_Projects/HOY01-รีวิวสเปก_1/project.json",
      "backup": "03_Projects\\HOY01-รีวิวสเปก_1\\project.json.before_codex_phone_shots_20261004.bak",
      "before_hash": "64f2bfbb5fd12613fb3c23dfa8506b0a32dcc8af08f350ee1cdd38f588725556",
      "after_hash": "ee58c000bcf0ee016fce538c724fb26e58b3032de615daa395b6d0fc056010b7",
      "source_span": [
        180.0,
        186.692
      ],
      "timeline_end": 35.2,
      "changed_clip": 3,
      "cutout_artifact": null
    },
    {
      "project": "HOY01-เทียบของเดิม_1",
      "path": "03_Projects/HOY01-เทียบของเดิม_1/project.json",
      "backup": "03_Projects\\HOY01-เทียบของเดิม_1\\project.json.before_codex_phone_shots_20261004.bak",
      "before_hash": "45b7d46a8bc1db7af0541daca8bf115a9f6ddfaf0742207e17c969f798d11d42",
      "after_hash": "82be736b72273e07773a0cab522b5c3c65329e52abd022006925b56910f1b356",
      "source_span": [
        169.75,
        176.423
      ],
      "timeline_end": 27.233333333333334,
      "changed_clip": 3,
      "cutout_artifact": "bgseq1-fb7e8ecdd9dda464"
    }
  ],
  "validation": {
    "source_audio_subtitle_hashes_unchanged": true,
    "results": [
      {
        "project": "HOY01-รีวิวสเปก_1",
        "probe": {
          "programs": [],
          "stream_groups": [],
          "streams": [
            {
              "codec_type": "video",
              "width": 1080,
              "height": 1920,
              "r_frame_rate": "30/1"
            },
            {
              "codec_type": "audio",
              "r_frame_rate": "0/0"
            }
          ],
          "format": {
            "duration": "35.215011"
          }
        },
        "full_decode_ok": true,
        "black_intervals": []
      },
      {
        "project": "HOY01-เทียบของเดิม_1",
        "probe": {
          "programs": [],
          "stream_groups": [],
          "streams": [
            {
              "codec_type": "video",
              "width": 1080,
              "height": 1920,
              "r_frame_rate": "30/1"
            },
            {
              "codec_type": "audio",
              "r_frame_rate": "0/0"
            }
          ],
          "format": {
            "duration": "27.237007"
          }
        },
        "full_decode_ok": true,
        "black_intervals": []
      }
    ]
  },
  "final_cutout_geometry": [
    {
      "width": 540,
      "height": 960,
      "mean_abs_error": 0.026480455196481886,
      "raw_mask_iou": 0.99633140956818,
      "mask_iou": 0.9989889010666708,
      "bbox_edge_delta_px": 0,
      "centroid_delta_px": 0.0,
      "passed": true,
      "exact_pixel_match": false,
      "reason": ""
    },
    {
      "width": 540,
      "height": 960,
      "mean_abs_error": 0.025204387053175178,
      "raw_mask_iou": 0.9963226495601772,
      "mask_iou": 0.9996552892762043,
      "bbox_edge_delta_px": 0,
      "centroid_delta_px": 0.0,
      "passed": true,
      "exact_pixel_match": false,
      "reason": ""
    },
    {
      "width": 540,
      "height": 960,
      "mean_abs_error": 0.05178895848462842,
      "raw_mask_iou": 0.9589608820185878,
      "mask_iou": 0.9989409722222222,
      "bbox_edge_delta_px": 0,
      "centroid_delta_px": 0.0,
      "passed": true,
      "exact_pixel_match": false,
      "reason": ""
    }
  ]
}
```

Jev: initial confidence 0.60; intermediate confidence 0.62 (below gate). Used the explicitly user-authorized measured gate for this HOY01 work. Final CLI call returned JSONDecodeError (no decision), so degraded under the project outage rule. These results are advice, not product evidence.
