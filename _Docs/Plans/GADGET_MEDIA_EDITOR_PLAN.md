# Gadget Media Product Video Studio — Implementation Plan

ดำเนินการโดย: Codex (GPT-5)

วันที่ยืนยันแผน: 2026-09-19

## 1. ผลลัพธ์ที่ต้องได้

เปลี่ยนเมนู `Gadget Media` จากหน้าจัด Campaign และ Content Slot ให้เป็น Product Video Studio ที่ผลิตงานได้ครบในเมนูเดียว:

> `1 สินค้า = 1 Product Video Project = 1 Approved Master Clip`

- คลิป Master ยาว 45–60 วินาที
- TikTok 9:16, 1080×1920, 30 FPS
- คนดูรู้ว่าสินค้าคืออะไร จุดเด่นมีผลต่อการใช้งานอย่างไร เหมาะกับใคร และข้อจำกัดคืออะไร
- สร้าง Purchase Intent ด้วยภาพสินค้า Benefit, Proof และ Use case โดยไม่ผูกตะกร้าหรือ Affiliate ใน workflow นี้
- ตัดต่อระดับ Official Product Film แต่ต้องเป็นงาน Editorial/Remix ของช่อง มี Commentary และ Evidence ไม่ใช่การนำ Official footage มาเรียงซ้ำ

## 2. ขอบเขตและสิ่งที่ไม่ทำ

### อยู่ในขอบเขต

- Product Library และ Product Workspace
- Source management, provenance, rights และ native-quality gate
- Research, Facts, Claims และ Evidence mapping
- Script, Story beats, Shot plan และ Edit Decision List
- Timeline แบบฝังอยู่ใน `Gadget Media`
- Gemini TTS, เสียงผู้สร้าง และ Presenter mode หลายแบบ
- Review, Quality Gate, Render Master, Cover และ Analytics หลังโพสต์

### ไม่อยู่ในขอบเขตรอบ implementation นี้

- ระบบดาวน์โหลด source จาก Internet
- การโพสต์ TikTok อัตโนมัติ
- ระบบตะกร้า Affiliate และ ProductStore เดิม
- คลิปรวมหลายสินค้าใน Master เดียว
- การ Publish อัตโนมัติโดยไม่มีคนอนุมัติ
- การใช้ AI สร้าง Claim, Test result หรือเหตุการณ์ปลอมแทน Evidence จริง

## 3. Product Model ใหม่

Campaign ยังอยู่เพื่อวางแผน 21 คลิปและวัดผล แต่ไม่เป็นเจ้าของไฟล์ตัดต่ออีกต่อไป แต่ละ Campaign Slot อ้าง `product_project_id` ไปยัง Product Video Project

### `ProductVideoProject`

```text
project_id
module = gadget_media
product_identity
  brand
  model
  category
  variant
audience
editorial_promise
status
source_assets[]
facts[]
story
presentation
edit
quality_report
artifacts
approved_master_id
metrics
created_at / updated_at
```

### กติกาหลัก

- `product_identity` ต้องระบุ Brand และ Model ก่อนสร้าง Timeline
- Source หลายไฟล์ได้ แต่ทุกไฟล์ต้องเกี่ยวกับสินค้าเดียวกัน
- Export หลาย version ได้ เช่น `v1`, `v2` แต่มี `approved_master_id` ได้หนึ่งรายการ
- Campaign Slot หนึ่งช่องอ้าง Product Video Project ได้หนึ่งรายการ
- Product Video Project ไม่สร้างหรือแก้ข้อมูลสินค้าใน ProductStore

## 4. State Machine

```text
brief
  → sourcing
  → source_ready
  → research_ready
  → script_ready
  → in_production
  → review_required
  → ready_to_render
  → rendered
  → approved
  → published
```

- `in_production` เริ่มเมื่อมี Timeline Document และ Project folder จริงแล้วเท่านั้น
- Blocker เป็น readiness result แยกจาก status เช่น `source_quality_failed`, `rights_review_required`, `claim_without_evidence`
- `ready_to_render` ต้องผ่าน Hard Gates ทุกข้อ
- `approved` ต้องมีคนเลือก Render หนึ่งรายการเป็น Approved Master
- `published` ต้องมี Approved Master และข้อมูลช่องทางเผยแพร่

## 5. Folder Contract และการแยกจากระบบเดิม

ใช้ top-level เดิมตามกฎโปรเจกต์ แต่แยก namespace `GadgetMedia/` ทุกจุด:

```text
01_Raw/
└── GadgetMedia/
    └── <product_id>/
        └── original/

02_Assets/
└── GadgetMedia/
    └── Shared/

03_Projects/
└── GadgetMedia/
    └── <project_id>/
        ├── project.json
        ├── product.json
        ├── sources.json
        ├── evidence.json
        ├── story.json
        ├── edl.json
        ├── timeline.json
        ├── media/
        │   ├── proxy/
        │   ├── selects/
        │   └── generated/
        ├── audio/
        │   ├── voice/
        │   ├── source/
        │   └── mix/
        └── review/

04_Exports/Ready_to_post/
└── GadgetMedia/
    └── <project_id>/
        ├── <date>_<brand-model>_master_v01.mp4
        └── export_manifest.json

05_Covers_Thumbnails/
└── GadgetMedia/
    └── <project_id>/

06_Archive/
└── GadgetMedia/
    └── <project_id>/

_Docs/gadget_media/
├── project_index.json
├── campaigns.json
└── analytics.json
```

### Path rules

- กำหนด path ผ่าน `scripts/config.py` และ `pathlib.Path` เท่านั้น
- API ทุกตัวรับ `project_id` แล้ว resolve ผ่าน Gadget Media repository ห้ามรับ absolute path จาก Client
- Save, Render, Cover และ Archive ต้องตรวจ path containment ภายใน namespace ของ Gadget Media
- Global Editor และ Project list เดิมไม่ scan `03_Projects/GadgetMedia/` โดยอัตโนมัติ
- Test ใช้ `tmp_path` และห้ามเขียน `01_Raw/`, `03_Projects/` หรือ `04_Exports/` จริง

## 6. สิ่งที่ใช้ร่วมและสิ่งที่ต้องแยก

| ส่วน | ใช้ร่วมได้ | ต้องแยก |
| :--- | :--- | :--- |
| Timeline math/schema | `timelineSchema`, trim, split, snap, ripple | Timeline document และ save path |
| Preview | `SequencePlayer` และ render parity contract | Workspace state และ selected project |
| Timeline UI | Track, ruler, inspector primitives | Gadget Media toolbar, stage rail และ project navigation |
| Render | FFmpeg stages และ subtitle engine | Render request, output path, registry namespace และ status |
| Assets | Renderer, font, SFX, LUT primitives | Gadget Media asset catalog และ project references |
| Analytics | สูตร completion/follows | Project metrics store และ campaign relation |

หลักการคือ reuse Engine แต่ไม่ reuse Ownership

## 7. Timeline Adapter

เพิ่ม `GadgetMediaTimelineAdapter` ระหว่าง Product Video Project กับ Timeline Document v2

### หน้าที่

1. แปลง `story.blocks` และ `edl.shots` เป็น Track/Clip เริ่มต้น
2. แนบ `source_id`, `evidence_id`, `claim_id` และ `story_block_id` กับ Timeline Clip
3. กำหนด `workspace_scope = gadget_media` และ `project_root`
4. Save กลับ `03_Projects/GadgetMedia/<project_id>/timeline.json`
5. ส่ง Render job ที่มี `module=gadget_media` และ output namespace ที่กำหนด

### ข้อห้าม

- ห้ามส่งผู้ใช้ไป tab Editor กลางเพื่อทำงานปกติ
- ห้ามใช้ `03_Projects/<project_name>/` ของ workflow เดิมเป็น fallback
- ห้ามให้ Global Editor เปลี่ยน status ของ Gadget Media Project
- ห้าม duplicate Timeline engine เป็นชุดใหม่ เพราะจะทำให้ Preview/Render drift

## 8. Information Architecture ของเมนู

Surface mode: `Operate` และสืบทอด visual system ปัจจุบันของ OmniCut Pro Studio

### ระดับที่ 1: Product Library

- รายการสินค้าแบบ Project ไม่ใช่ช่องว่าง 21 Slot
- แสดง Brand, Model, Category, Status, Master duration, Quality Gate และวันที่แก้ล่าสุด
- Filter ตาม Status, Brand, Category และ Blocker
- Primary action: `สร้าง Product Video`
- Campaign progress และ Analytics เป็นมุมมองรอง ไม่ครองพื้นที่ผลิตงาน

### ระดับที่ 2: Product Workspace

อยู่ในเมนู `Gadget Media` เดิมและไม่เปลี่ยน tab ออกไป Editor

```text
Header: Product identity | Status | Duration | Quality | Save | Validate | Render

Stage rail:
1. Brief
2. Sources
3. Evidence
4. Story
5. Cut
6. Review

Main canvas: เนื้อหาของ Stage ปัจจุบัน
Right inspector: Blockers, Evidence links, Quality checklist และ Version history
```

### พฤติกรรมสำคัญ

- Auto-save แบบมีสถานะ `กำลังบันทึก / บันทึกแล้ว / บันทึกไม่สำเร็จ`
- ปุ่มต้องขึ้นต้นด้วยกริยาและแสดงเฉพาะ action ที่ทำได้จริง
- Stage ที่ยังไม่พร้อมเปิดดูได้ แต่ action ถัดไปถูก disabled พร้อมเหตุผล
- Mobile/Narrow layout ยุบ Product list และ Inspector เป็น drawer แต่ Timeline ใช้ minimum working width และแสดงคำแนะนำเมื่อพื้นที่ไม่พอ
- Keyboard navigation, visible focus และ error summary ต้องมีตั้งแต่ Phase แรก

## 9. Workflow ผลิตหนึ่งคลิป

### Stage 1 — Brief

กำหนดสินค้าเดียว, กลุ่มผู้ชม, ปัญหาที่สินค้าแก้, Hero benefit, Caveat และเหตุผลที่คลิปนี้ควรมีอยู่

### Stage 2 — Sources

- เพิ่ม Original source, URL, Brand/Creator, Published date, rights basis และ checksum
- Probe Resolution, Codec, FPS, Duration, Audio และ corruption
- งานจริงต้องเป็น native 1920×1080 หรือสูงกว่า
- Source ที่ไม่ผ่านยังเก็บเป็น reference ได้ แต่ห้ามเข้า EDL สำหรับ Master

### Stage 3 — Evidence

แยกข้อมูลเป็น:

- `brand_claim` — ข้อมูลที่ Brand ระบุ
- `verified_fact` — ข้อมูลที่ตรวจจากเอกสารหรือการทดสอบ
- `opinion` — ความเห็นของช่อง
- `caveat` — ข้อจำกัดหรือสิ่งที่ต้องระวัง

ทุก Fact มี Evidence reference และ usage note

### Stage 4 — Story

โครงมาตรฐาน 45–60 วินาที:

| เวลา | หน้าที่ |
| :--- | :--- |
| 0–2s | Hook ด้วยปัญหา ผลลัพธ์ หรือภาพ Hero |
| 2–7s | บอกว่าสินค้าคืออะไรและทำมาเพื่อใคร |
| 7–20s | Hero feature พร้อมภาพ Proof |
| 20–35s | Benefit หรือ Use case เพิ่ม 2 ประเด็น |
| 35–45s | Caveat, Comparison หรือสิ่งที่คำโฆษณาไม่พูด |
| 45–55s | Verdict และเหมาะกับใคร |
| 55–60s | CTA ให้ติดตามหรือแสดงความคิดเห็น โดยไม่บังคับขาย |

Story block ทุกท่อนต้องมี `claim_ids`, `source_ids` และ visual intent

### Stage 5 — Cut

- สร้าง Selects และ EDL ก่อนเปิด Timeline
- แต่ละ Shot ระบุ Source timecode, Story block และเหตุผลที่เลือก
- Timeline เริ่มจาก Assembly Cut แล้วจึง Fine Cut, Audio, Caption และ Polish
- J-Cut 150–250ms, Caption Micro-Burst 2–4 คำ และ Safe Zone ตามกฎกลาง
- Shot ต้องตอบ Narration ภายในจังหวะเดียวกัน ไม่วางภาพสวยแต่ไม่เกี่ยวกับประโยค

### Stage 6 — Review

- เปรียบเทียบ Preview กับ Script, Evidence และ Quality Gate
- Render Review version ลง project review folder ก่อน
- Approved Master ต้องถูกเลือกโดยผู้ใช้
- เมื่อ Approve แล้ว Version เก่ายังเก็บเป็น history แต่ไม่ถือเป็น Master ปัจจุบัน

## 10. Presenter และ Voice Model

แยกเป็นสองแกนเพื่อรองรับหลายรูปแบบโดยไม่สร้าง preset ซ้ำ:

```text
presenter_mode = face | product_only | mixed
narration_mode = creator_voice | gemini_tts | source_audio
```

- `face + creator_voice`: ผู้สร้างพูดเอง
- `face + gemini_tts`: ใช้หน้าผู้สร้างประกอบ แต่ต้องไม่ทำให้เข้าใจว่าเป็นเสียงจริง
- `product_only + gemini_tts`: Product Film พร้อม Narration
- `mixed`: เปิดหรือปิดด้วยหน้าผู้สร้าง และใช้ Product footage เป็นเนื้อหาหลัก
- Source audio ใช้เป็น texture, demo หรือ transition ได้ แต่ไม่กลบ Narration
- TTS provider อยู่หลัง interface เพื่อเพิ่ม Gemini โดยไม่ผูก Timeline กับ provider รายเดียว

## 11. Official-Quality Editing Recipe

คลิปต้องให้ความรู้และกระตุ้นความสนใจซื้อผ่านลำดับนี้:

```text
Problem → Product Reveal → Benefit → Proof → Use Case → Honest Caveat → Verdict
```

### กติกาภาพ

- เห็น Brand/Model หรือรูปลักษณ์สินค้าชัดภายใน 3 วินาทีแรก
- Shot mix ต้องมี Hero, Detail, Interaction, UI/Result และ Context of use ตามที่ source รองรับ
- Reframe 16:9 เป็น 9:16 ราย Shot; ห้ามใช้ center crop เดียวทั้งคลิป
- ห้ามใช้ Shot ซ้ำเพื่อยืดเวลาเมื่อไม่มีสาระใหม่
- Motion, Zoom และ Transition ต้องช่วยชี้ Feature ไม่ใช้เพื่อกลบ Source ที่อ่อน
- Official footage เป็นหลักฐานภาพ ไม่ใช่เจ้าของโครงเรื่อง; โครงเรื่องและคำตัดสินต้องเป็นของช่อง

### กติกาความน่าซื้อ

- ทุก Feature ต้องแปลเป็น Benefit หรือ Use case
- มีหนึ่ง Hero benefit ที่ผู้ชมจำได้หลังจบคลิป
- มี Caveat อย่างน้อยหนึ่งข้อเมื่อข้อมูลรองรับ เพื่อเพิ่มความน่าเชื่อถือ
- ห้ามใช้คำรับประกัน เช่น “ดีที่สุด” หรือ “คุ้มที่สุด” หากไม่มีหลักฐานเปรียบเทียบ
- CTA หลักคือ Follow, Comment หรือ Save; Commerce link เป็น metadata ภายนอก workflow นี้

## 12. Quality Gate

### Hard Gates — ต้องผ่านทั้งหมด

1. **Product Purity:** มีสินค้าหลักหนึ่งรุ่น ไม่มี Footage ต่างรุ่นปนโดยไม่ระบุ
2. **Native Source:** Footage ที่ใช้ใน Master เป็น native 1920×1080 ขึ้นไป
3. **Rights:** Source ทุกตัวที่ใช้ผ่าน rights review หรือถูกจำกัดเป็น Private Cut
4. **Evidence:** Factual Claim ทุกข้อมี Evidence; Opinion ถูกระบุเป็น Opinion
5. **Story:** Hook, Hero benefit, Proof, Caveat และ Verdict ครบ
6. **Duration:** Master อยู่ระหว่าง 45–60 วินาที
7. **Technical:** 1080×1920, 30 FPS, Audio/Caption/Safe Zone ผ่าน
8. **Parity:** Preview และ Render ผ่าน parity checks

### Editorial Score — เป้าหมายอย่างน้อย 90/100

| หมวด | คะแนน |
| :--- | ---: |
| ความชัดของสินค้าและ Hook | 15 |
| ความรู้และ Evidence | 25 |
| Visual storytelling และ Pacing | 25 |
| Audio, Voice และ Caption | 15 |
| Purchase Intent ที่ซื่อสัตย์ | 15 |
| Finish และ Brand consistency | 5 |

คะแนนไม่สามารถลบล้าง Hard Gate ได้

## 13. Backend/API Plan

เพิ่มโมดูลแยกโดยไม่ขยาย `ContentSlot` จนกลายเป็น God object:

```text
scripts/gadget_media_paths.py
scripts/gadget_media_project.py
scripts/gadget_media_repository.py
scripts/gadget_media_timeline_adapter.py
scripts/gadget_media_quality.py
scripts/api_gadget_media_projects.py
```

API หลัก:

```text
GET    /api/gadget-media/projects
POST   /api/gadget-media/projects
GET    /api/gadget-media/projects/{id}
PATCH  /api/gadget-media/projects/{id}
POST   /api/gadget-media/projects/{id}/sources/probe
POST   /api/gadget-media/projects/{id}/timeline/build
POST   /api/gadget-media/projects/{id}/quality/validate
POST   /api/gadget-media/projects/{id}/renders
POST   /api/gadget-media/projects/{id}/renders/{render_id}/approve
```

Campaign API เดิมเพิ่มเพียง `product_project_id` และ migration compatibility

## 14. Frontend Plan

แยก `GadgetMediaHub.jsx` ที่ใหญ่เกินไปเป็น feature modules:

```text
frontend/src/components/gadget-media/
├── GadgetMediaStudio.jsx
├── ProductLibrary.jsx
├── ProductWorkspace.jsx
├── ProductHeader.jsx
├── StageRail.jsx
├── QualityInspector.jsx
├── stages/
│   ├── BriefStage.jsx
│   ├── SourcesStage.jsx
│   ├── EvidenceStage.jsx
│   ├── StoryStage.jsx
│   ├── CutStage.jsx
│   └── ReviewStage.jsx
└── timeline/
    └── GadgetMediaTimelineHost.jsx
```

State แบ่งเป็น Server state ของ Project, local draft ของ Stage และ Timeline state ของ Engine ห้ามเก็บทั้งหมดใน component เดียว

## 15. Migration จากของเดิม

1. เก็บ `_Docs/gadget_media_campaigns.json` และ API เดิมให้อ่านได้
2. เพิ่ม `product_project_id` แบบ optional ใน Content Slot
3. เพิ่ม action `สร้าง Product Project จาก Slot`
4. คัดลอก Hook, Series, Audience, Script และ Source refs ไปเป็น Project draft โดยไม่ลบ Slot เดิม
5. หลัง Product Project ผ่าน Gate ให้ Slot อ่าน Status และ Master link จาก Project
6. ไม่ migrate แบบ silent และไม่เขียนทับ Campaign เดิม

## 16. Implementation Phases

### Phase 1 — Domain and Storage Contract

- Path resolver และ containment tests
- Product Video Project model, repository และ state machine
- Existing Campaign compatibility

**Gate:** unit tests ครอบคลุม path escape, atomic save, invalid transition และ one-approved-master rule

### Phase 2 — Product Library and Sources

- Product Library, create/open project และ filter
- Brief, Sources, probe และ rights gate
- Folder creation หลังผู้ใช้ยืนยัน Project เท่านั้น

**Gate:** สร้าง Project แล้ว Artifact อยู่เฉพาะ namespace GadgetMedia

### Phase 3 — Evidence and Story

- Fact/Evidence model
- Script blocks, Gemini TTS configuration และ Story validation
- EDL/Shot plan generation

**Gate:** Claim ที่ไม่มี Evidence ทำให้ Ready to Render ไม่ผ่าน

### Phase 4 — Scoped Timeline

- Timeline adapter และ Gadget Media Timeline Host
- Save/Load explicit project path
- Preview/Render parity integration

**Gate:** ตัดและ Save ได้ในเมนู Gadget Media โดย Global Editor ไม่เห็น Project นี้

### Phase 5 — Review, Render and Master

- Quality report, Review render, Version history และ Approve Master
- Export/Cover namespace และ registry metadata

**Gate:** Render ไปที่ GadgetMedia path เท่านั้น และมี Approved Master หนึ่งรายการ

### Phase 6 — Campaign and Analytics

- เชื่อม Product Project กับ Campaign Slot
- Published metrics และ Series analytics
- ลด Campaign UI ให้เป็น Planning/Results view

**Gate:** Campaign แสดงสถานะจาก Project โดยไม่ duplicate production state

## 17. Test Strategy

- Domain tests: validation, transitions, evidence, rights และ master invariant
- Path tests: traversal, wrong namespace และ absolute-path rejection
- API tests: CRUD, conflict, atomic save, readiness และ approval
- Frontend tests: Stage navigation, disabled reasons, save errors, empty/loading/overflow states
- Timeline tests: adapter mapping, save isolation และ shared engine regression
- Parity tests: `test_preview_render_parity.py`
- Render smoke test: ใช้ source synthetic ใน `.tmp/` และ cleanup 100%
- Regression: workflow รีวิวปักตะกร้า, Global Editor, Gallery และ Export list เดิมต้องไม่เปลี่ยนพฤติกรรม

## 18. Acceptance Criteria

- ผู้ใช้สร้าง Product Video Project หนึ่งสินค้าและทำงานครบหก Stage โดยไม่ออกจากเมนู `Gadget Media`
- Timeline ใช้ Engine กลางแต่ Save/Render อยู่ใต้ namespace GadgetMedia เท่านั้น
- Product Project ไม่มี side effect ต่อ ProductStore หรือ workflow ปักตะกร้า
- Source ที่ต่ำกว่า native 1080p หรือสิทธิ์ไม่ผ่านไม่สามารถเข้าสู่ Approved Master
- Factual Claim ทุกข้อย้อนหา Evidence ได้
- คลิป Master มีความยาว 45–60 วินาทีและผ่านสเปก TikTok
- มี Export หลาย version ได้แต่มี Approved Master หนึ่งรายการ
- Campaign Slot อ้าง Project ได้โดยไม่ duplicate Source, Script, Timeline หรือ Status
- UI แสดงเหตุผลของ Blocker และสถานะ Save/Render ตามจริง
- Test artifacts ไม่หลุดเข้า `03_Projects/`, `04_Exports/` หรือ Export registry จริง

## 19. ลำดับการเริ่มพัฒนา

เริ่มจาก Phase 1 ก่อน UI เพราะ Folder ownership, Project identity และ state machine เป็นตัวกันไม่ให้งาน Gadget Media ปนกับโปรแกรมเดิม จากนั้นทำ Product Library และ Sources ก่อนเชื่อม Timeline เมื่อ Adapter contract และ Quality Gate ชัดแล้ว

## 20. Implementation Result — 2026-09-20

ดำเนินการโดย: Codex (GPT-5)

สถานะ: implemented ครบตามแกน Phase 1–6 สำหรับ Product Studio

- เพิ่ม Product Project domain, state machine, isolated repository/path contract และ one-approved-master invariant
- เพิ่ม Timeline adapter/host ที่ reuse `SequencePlayer`, `Timeline` และ render engine แต่ save/render เฉพาะ namespace GadgetMedia
- เพิ่ม Hard Gates สำหรับ product purity, Native 1080p, rights, evidence, story, 45–60 วินาที, 1080×1920/30 FPS, audio และ preview/render parity
- เพิ่ม Gemini TTS background job จาก Story พร้อม Voice, Tone, Speed, versioned WAV และผูก `audio_path` กลับ Project
- เพิ่ม Product Library, 6-stage Workspace, Quality Inspector, render version history และ approval
- Campaign Slot รองรับ `product_project_id` แบบ optional และสร้าง Product Project ต่อจาก Slot ได้โดยไม่ย้าย ownership
- ตรวจ UI desktop/mobile แบบ read-only แล้ว และล้าง artifact QA ใน `.tmp` 100%

ผลตรวจ:

- Targeted backend: `21 passed`
- Frontend: `290 passed`; production build ผ่าน `2,025 modules`; lint exit 0
- FastAPI import ผ่าน และพบ Gadget Media routes 20 รายการ
- Full backend: `1,666 passed, 9 skipped, 1 failed`; failure เดียวเป็น pre-existing dirty change ของ `tech_journalism_calm` ใน `scripts/gemini_tts_engine.py` ที่ยังไม่มี mapping ใน preview/render parity และไม่ใช่ไฟล์ของ implementation รอบนี้
