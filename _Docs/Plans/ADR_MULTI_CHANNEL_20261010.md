# ADR — Multi-channel P1: Registry & scope foundation

- **ดำเนินการโดย:** Claude Code (Claude Opus 5.5) — agent P1
- **วันที่:** 2026-10-10
- **อ้างอิง:** `_Docs/Plans/PLAN_MULTI_CHANNEL_20261010.md` §3, §4.1, §4.4, §5.1, §9 (P1), §10 (AC15), §11 · P0: `_Docs/Reports/MULTI_CHANNEL_P0_*_20261010.*`
- **สถานะ:** ใช้งานแล้วใน single-channel compatibility mode (strict ปิดเป็นค่าเริ่มต้น จะเปิดใน P8)
- **ผู้อ่านหลัก:** agent ของ P2–P8 — ส่วนที่ 1–6 คือ contract ที่ต้องยึด ห้ามเปลี่ยนโดยไม่แก้ ADR นี้

## 1. Request scope contract

| เรื่อง | กติกา |
|---|---|
| Header | `X-OmniCut-Channel: <channel_id>` (slug ตัวพิมพ์เล็กเท่านั้น; `Main` = invalid ไม่ lowercase ให้) — เป็น routing context ไม่ใช่ authentication |
| Query | `?channel=<id>` รับ **เฉพาะ** route ที่ policy ตั้ง `allow_query_scope: true` (GET ที่ `<img>/<video>` ใช้เป็น src): `/api/media/{file_path:path}`, `/api/editor/filmstrip`, `/api/producer/ref-media/{filename}`, background-isolation `cutout.webm` / `preview.webm` / `frames/{frame_index}` (3 ตัวหลังเป็น `shared` — flag ไว้ล่วงหน้าเผื่อถูกจัดเป็น channel) |
| `?channel=` บน channel route ที่ไม่ flag | 422 `channel_query_not_allowed` (ไม่เมิน เพราะเมินแล้ว compatibility mode จะ fallback ไป main เงียบ ๆ ขัดเจตนา client) |
| header + query ไม่ตรงกัน / header ซ้ำหลายค่าไม่ตรงกัน | 422 `channel_scope_conflict` |
| header/query ระบุ id ผิดรูปแบบ (รวมค่าว่าง) | 422 `channel_scope_invalid` — **เสมอ** ทั้ง strict on/off |
| header/query ระบุ id ที่ไม่มีใน registry | 422 `channel_scope_unknown` — **เสมอ** ไม่ fallback |
| channel route ไม่มี scope | strict **off** → implicit `main` (lazy: ไม่อ่าน registry เลย พฤติกรรมเดิม 100%) · strict **on** → 422 `channel_scope_missing` |
| shared / global route | ไม่บังคับ scope; ถ้าส่ง header มาจะถูก validate (ผิด → 422) และเก็บไว้ใน `request.state.channel_scope` |
| `ignore_scope_header` | ใช้กับ `/api/channels*` เท่านั้น: เมิน header ทั้งหมด เพื่อให้ client ที่ถือ id ช่องเก่าเรียกรายการช่องมาเลือกใหม่ได้เสมอ |
| `channel_id` ใน body/JSON | ไม่มีผลต่อ scope เด็ดขาด (middleware ไม่อ่าน body) — P2+ ต้อง reject เมื่อไม่ตรง header (409/422 ตามกรณี) |
| Response | scope ที่ client ส่งมาเองจะถูก echo กลับใน header `X-OmniCut-Channel` (implicit default ไม่ echo เพื่อให้ response เดิม byte-identical); CORS `expose_headers` มี header นี้ |

ลำดับ middleware (นอก → ใน): `CORSMiddleware` → `api_key_gate` (auth) → `ChannelScopeMiddleware` → router. auth จึงตัดสินก่อน (ไม่มี key = 401 แม้ header ช่องผิด) และ 422 ของ scope ได้ CORS header ครบ. `OPTIONS`, websocket, lifespan, path ที่ไม่ match route (404/405) ผ่านโดยไม่แตะ

## 2. Error contract

รูปแบบ JSON เดิมของโปรเจกต์ + ฟิลด์เสริม: `{"detail": "<ข้อความไทยสั้น>", "code": "<machine code>", ...extra}` และ header `X-OmniCut-Error-Code: <code>` (`detail` ยังเป็น string เสมอ → `frontend/src/api.js` แสดงได้ทันที)

| HTTP | ใช้เมื่อ | codes ที่มีแล้ว |
|---|---|---|
| 422 | scope หาย/ผิด/ไม่รู้จัก/ขัดกัน, input ไม่ผ่าน validation | `channel_scope_missing` `channel_scope_invalid` `channel_scope_unknown` `channel_scope_conflict` `channel_query_not_allowed` `channel_id_invalid` `channel_id_immutable` `field_not_editable` `payload_invalid` `expected_revision_required` `expected_revision_invalid` `display_name_required` `text_*` `handle_<reason>` `timezone_invalid` `avatar_path_invalid` `overrides_invalid` `posting_enabled_invalid` + `*_missing` (ช่อง active ห้ามลบข้อมูลจำเป็น) |
| 404 | resource ของอีกช่อง (ทำให้ดูเหมือนไม่มีอยู่) / channel id ใน path ไม่มี | `resource_not_found` `channel_not_found` |
| 409 | revision ไม่ตรง, ซ้ำ, สถานะไม่อนุญาต | `revision_conflict` (+`current_revision`) `channel_exists` `handle_conflict` (+`conflicting_channel_id`) `channel_archived` `channel_not_active` (+`channel_status`) `channel_not_ready` (+`issues[]`) `posting_not_allowed` (+`issues[]`) `account_handle_mismatch` `default_channel_protected` `channel_registry_busy` |
| 500 | `_Docs/channels.json` อ่าน/parse/โครงสร้างผิด | `channel_registry_invalid` (กระทบเฉพาะ request ที่ระบุช่องเอง; compatibility mode ไม่อ่านไฟล์) |

ข้อความสถานะระบุชื่อสถานะเสมอ เช่น `ช่อง x อยู่ในสถานะฉบับร่าง (draft) ยังเริ่มงานใหม่ไม่ได้`

## 3. Strict flag

- env `OMNICUT_MULTI_CHANNEL_STRICT` ∈ {`1`,`true`,`yes`,`on`} (ไม่สนตัวพิมพ์/ช่องว่าง) = strict; อย่างอื่น/ไม่ตั้ง = compatibility
- อ่านผ่าน `scripts.config.is_multi_channel_strict()` **ทุกครั้งที่เรียก** (ไม่ cache) → test ใช้ `monkeypatch.setenv/delenv` ได้; `.env` ก็ตั้งได้ (config โหลด .env ตอน import)
- `GET /api/channels` คืน `strict_mode` ให้ frontend แสดงโหมด

## 4. Registry `_Docs/channels.json`

```json
{"schema_version": 1, "revision": 3, "channels": [{
  "id": "main", "display_name": "rizannTry", "handle": "@rizanntry",
  "watermark_text": "…", "avatar_asset_path": "03_Projects/_HyperFrames_Studio/assets/shared/img/channel_avatar.jpg",
  "follow_title": "กดติดตามด้วยนะ", "timezone": "Asia/Bangkok", "status": "active",
  "posting_enabled": false,
  "account_binding": {"status": "unverified", "verified_handle": null, "verified_at": null},
  "overrides": {}, "created_at": "2026-10-10T00:00:00Z", "updated_at": "…",
  "revision": 1, "identity_hash": "<sha256 hex>"}]}
```

- **อ่านไม่มี side effect:** ไฟล์ไม่มี → registry ในหน่วยความจำที่มีแค่ `main` (revision 0, `created_at: null`). ไฟล์ไม่มี `main` → เติม `main` ในหน่วยความจำ (persist ตอนเขียนครั้งถัดไป). field ที่ไม่รู้จักถูกเก็บไว้ตอนเขียน (forward compatible). schema ใหม่กว่า/ JSON เสีย/ id ซ้ำ/ id หรือ status ผิด → 500 และ**ไม่เขียนทับ**
- **เขียนได้เฉพาะ** `seed / create / update / activate / archive / set_account_binding`: validate → lock (thread `RLock` ต่อ path + OS lock `msvcrt/fcntl` ที่ `channels.json.lock`) → อ่านใหม่ใต้ lock → ตรวจ `expected_revision` → temp file + `fsync` + `os.replace` (retry เมื่อ Windows ล็อกไฟล์ชั่วคราว). การอ่านใน process เดียวกันทำใต้ lock เดียวกันเพื่อไม่ให้ handle ของ reader ไปขวาง `os.replace` บน Windows. ทดสอบแล้วทั้งหลาย thread และหลาย process (ไม่มี lost update)
- **revision:** `revision` ระดับไฟล์ +1 ทุกการเขียนที่เปลี่ยนจริง; `channels[].revision` +1 เมื่อช่องนั้นเปลี่ยน; no-op ไม่ bump. `PATCH` **ต้อง** ส่ง `expected_revision` (= revision ของช่อง); activate/archive/binding รับแบบ optional; create รับ `expected_registry_revision` แบบ optional
- **ไม่มี delete.** id ใช้ซ้ำไม่ได้แม้ช่องถูก archive
- ไม่เก็บ cookie/API key/ข้อมูลล็อกอิน: ฟิลด์นอก allowlist ถูก reject 422 (`field_not_editable`)

### 4.1 ฟิลด์และกฎ

| ฟิลด์ | กฎ |
|---|---|
| `id` | `^[a-z][a-z0-9_-]{1,31}$`, เปลี่ยนไม่ได้ |
| `display_name` | บังคับมี; NFC + trim; ≤40 ตัวอักษร และกว้าง ≤446px (Anuphan-Bold 40px = กล่อง `.fl-who b` ของ follow card); ไม่ใช้จับคู่ใด ๆ |
| `handle` | `normalize_handle` (ข้อ 5); ว่างได้เฉพาะ draft; ห้ามซ้ำกับช่องที่ไม่ใช่ archived (draft+active) → 409 |
| `watermark_text` | ≤64 ตัวอักษร และ ≤600px ที่ Anuphan-Bold 26px (ค่าเดิม 503px; เผื่อ Global Editor ที่วาด ~41px กึ่งกลาง y=0.72H) |
| `follow_title` | ≤24 ตัวอักษร และ ≤960px ที่ Kanit-Black 124px (`#fl-title` กึ่งกลางเฟรม 1080, ห่างขอบ 60px; ค่าเดิม 908px) |
| ข้อความทุกช่อง | NFC; ตัด whitespace ชุดเดียวกับ handle; reject อักขระ Cc/Cf (ยกเว้น ZWJ)/Cs/Zl/Zp (รวม zero-width space); reject glyph ที่ฟอนต์ไม่มี (อีโมจิ ฯลฯ, ตรวจ cmap ด้วย fontTools); **reject ไม่ตัดทอน** |
| `avatar_asset_path` | path สัมพัทธ์จาก project root (`config.CHANNELS_PROJECT_ROOT`), `\`→`/`, ห้าม absolute/drive/`..`/`//`, ต้อง `.jpg/.jpeg/.png/.webp`, resolve แล้วต้องอยู่ใน root; ไฟล์หาย = readiness issue ไม่ crash |
| `timezone` | ค่าเริ่ม `Asia/Bangkok`, ตรวจด้วย `zoneinfo` |
| `status` | `draft → active` (activate: ต้องไม่มี profile issue + handle ไม่ชน) · `draft/active → archived` · `archived → active` (activate ซ้ำ) · ไม่มี `active → draft` · `main` archive ไม่ได้ |
| `posting_enabled` | ตั้ง true ได้เมื่อ active + readiness ครบ + `account_binding` verified และ `verified_handle == handle`; ตรวจเฉพาะตอนเปลี่ยน false→true; archive หรือเปลี่ยน handle → false อัตโนมัติ |
| `account_binding` | ตั้งผ่าน `ChannelStore.set_account_binding()` เท่านั้น (ไม่มี HTTP ใน P1; P5 เรียกหลังตรวจบัญชีจริง); เปลี่ยน handle → reset เป็น unverified |
| `overrides` | dict JSON ธรรมดา ≤16KB เก็บไว้เฉย ๆ (AI/TTS/BGM ต่อช่องในอนาคต) ยังไม่มีโค้ดใช้ |
| ช่อง active | แก้ได้แต่ห้ามทำให้ฟิลด์จำเป็นว่าง (display_name/handle/watermark/follow/avatar) |
| ช่อง archived | อ่านได้; `PATCH` → 409 `channel_archived` |

### 4.2 Identity hash (P4 จะ snapshot)

`identity_hash = sha256_hex(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))` โดย
`payload = {"display_name", "handle", "watermark_text", "follow_title", "avatar": {"path": <rel posix>, "sha256": <sha256 ของไฟล์ | null>}}` — ไม่รวม id/status/timezone/binding. ค่าที่เก็บในไฟล์คำนวณตอนเขียน; ถ้าเปลี่ยนไฟล์รูปในที่เดิม ให้ `PATCH {}` (พร้อม expected_revision) เพื่อ refresh hash/revision. คำนวณสดด้วย `compute_identity_hash(channel, project_root=…)`

### 4.3 Seed `main` (ที่มาของค่า)

ทุกค่าคัดลอกจาก `03_Projects/_HyperFrames_Studio/kit/channels.js` (`window.HF_CHANNELS.main`) ณ 2026-10-10: name/handle/watermark/followTitle/avatar (แปลง `assets/shared/img/channel_avatar.jpg` เป็น path จาก project root). `watermark_text` ตรงกับ `scripts/subtitle_engine.py` `WATERMARK_TEXT` (มีเทสยืนยัน). โค้ด**ไม่**อ่านโฟลเดอร์ studio (gitignored) ตอน runtime. `posting_enabled=false`, binding `unverified` — การโพสต์เดิมยังไม่อ่านค่านี้

## 5. Handle normalization (Python = JS)

`scripts/channel_store.normalize_handle(raw) -> str` (raise `HandleError`, `.reason`) และ `frontend/src/lib/channelHandle.js` `normalizeHandle(raw) -> {ok, value} | {ok:false, code, message}`. ลำดับ: type → trim ชุดอักขระที่ระบุชัด (space, \t\n\r\f\v, NBSP, U+1680, U+2000–200A, U+2028/2029, U+202F, U+205F, U+3000, U+FEFF, U+200B) → empty → ถ้าเป็น URL: ต้องเป็น `http(s)://` + host `*.tiktok.com` (port ได้) แล้วเอา path segment แรกที่ขึ้นต้น `@` (ตัด `?#`) → ตัด `@` นำหน้า 1 ตัว → `[A-Za-z0-9._]+` → lowercase แบบ ASCII → ยาว 2–24 → ห้าม `..` → ห้ามลงท้าย `.` → คืน `@handle`. รหัส error: `invalid_type empty not_tiktok_url url_without_handle invalid_chars too_short too_long consecutive_dots trailing_dot`. Vectors 54 ชุดที่ `tests/fixtures/channel_handle_cases.json` — ทั้งสองภาษาอ่านไฟล์เดียวกัน; แก้กฎต้องแก้สองไฟล์ + fixture พร้อมกัน

## 6. Route policy (กันไม่ให้ route ไหน bypass guard)

- ไฟล์ `scripts/channel_route_policy.json` (1 แถว/route): `method, path, scope (channel|shared|global), allow_query_scope, access (read|write|read_write), risk, resource_params[], module, ignore_scope_header?` — สร้างจาก P0 matrix (228 แถว, scope ตรง P0 ทุกแถว มีเทสยืนยัน) + `/api/channels` 7 แถว = **235** (channel 164 / shared 38 / global 33)
- loader `scripts/channel_route_policy.py` validate ทุกแถว (`allow_query_scope` เฉพาะ GET, `ignore_scope_header` เฉพาะ global, ห้ามซ้ำ)
- middleware หา route ด้วย router จริง (`route.matches(scope)` ตามลำดับลงทะเบียน → path template) แล้ว lookup policy; ปัจจุบัน route ทั้งหมดไม่รับ HEAD จึงได้ 405 จาก router (loader มี fallback HEAD→แถว GET ไว้ถ้าอนาคตเปิด HEAD); APIRoute ที่**ไม่มีแถว = channel (fail closed)**; ผล match cache ต่อ (method, path) สูงสุด 4096 รายการ
- `tests/test_channel_scope.py::test_every_live_route_has_exactly_one_policy_row` **fail** เมื่อมี route ใหม่ไม่มีแถวหรือมีแถวค้าง → ทุกเฟสที่เพิ่ม/แก้ route ต้องแก้ JSON นี้ในคอมมิตเดียวกัน; และ `test_every_channel_route_rejects_missing_scope_in_strict_mode` ยิงทุก channel route ด้วย strict on ต้องได้ 422 ก่อนถึง handler

## 7. Python API สำหรับ P2–P8

```python
from scripts.config import CHANNELS_FILE, CHANNELS_PROJECT_ROOT, DEFAULT_CHANNEL_ID, is_multi_channel_strict
from scripts.channel_store import (
    ChannelStore, get_default_store, ChannelError, HandleError, ReadinessIssue,
    normalize_handle, is_valid_channel_id, compute_identity_hash,
    readiness, profile_issues, posting_issues,
    STATUS_DRAFT, STATUS_ACTIVE, STATUS_ARCHIVED,
)
from scripts.channel_scope import (
    CHANNEL_HEADER, ChannelScope, get_channel_scope, get_optional_channel_scope,
    require_writable, require_active_for_new_work, require_final_ready, ensure_same_channel,
    resolve_scope, install_channel_scope,
)
```

| API | สัญญา |
|---|---|
| `get_default_store() -> ChannelStore` | ผูก `config.CHANNELS_FILE` + `config.CHANNELS_PROJECT_ROOT` ตอนเรียก (monkeypatch ได้) |
| `ChannelStore(path=None, *, project_root=None, metrics=None, clock=None)` | `load()`, `revision()`, `list_channels(include_archived=True)`, `find(id) -> dict|None`, `get(id)` (404), `readiness(id)`, `posting_issues(id)`, `seed()`, `create(data, *, expected_registry_revision=None)`, `update(id, changes, *, expected_revision)`, `activate(id, *, expected_revision=None)`, `archive(id, *, expected_revision=None)`, `set_account_binding(id, *, status, verified_handle=None, verified_at=None, expected_revision=None)` — คืน deep copy เสมอ |
| `readiness(channel, *, channels=(), project_root=None, metrics=None) -> list[ReadinessIssue]` | ว่าง = พร้อม final render; รวม `channel_draft`/`channel_archived` + profile issues (`*_missing`, `avatar_file_missing`, `avatar_path_invalid`, `handle_invalid`, `handle_duplicate`, `text_*`, `timezone_invalid`) |
| `posting_issues(...)` | readiness + `account_unverified` / `account_handle_mismatch` (P5 ใช้ก่อน prepare/claim) |
| `ChannelScope` | `.channel_id`, `.source` (`header`/`query`/`default`), `.strict`, `.is_implicit_default`, `.channel` (snapshot deep copy; default โหลดแบบ lazy), `.status`, `.revision`, `.identity_hash`, `.to_dict()` |
| `Depends(get_channel_scope)` | สำหรับ handler ของ channel route; คืน scope เสมอหรือ 422 (ถ้าไม่มี middleware เช่น mini app ใน test ก็ resolve เองจาก header) |
| `Depends(get_optional_channel_scope)` | สำหรับ shared/global; `None` ถ้า client ไม่ส่ง |
| `require_writable(scope)` | archived → 409 `channel_archived` |
| `require_active_for_new_work(scope)` | ไม่ใช่ active → 409 `channel_not_active` (ใช้กับสร้าง job/claim/batch ใหม่) |
| `require_final_ready(scope, *, store=None)` | active + readiness ว่าง ไม่งั้น 409 `channel_not_ready` + `issues[]` (AC15: final render/export/post) |
| `ensure_same_channel(scope, owner_channel_id, *, resource_label="ข้อมูล", allow_legacy_main=False)` | ไม่ตรง → 404 `resource_not_found`; `owner=None` ผ่านได้เฉพาะ `allow_legacy_main=True` และ scope = main (ใช้กับ migration cohort ที่ตรวจแล้วเท่านั้น) |

### 7.1 วิธีประกาศ ownership ใน P2+

1. route: ตั้ง `scope` ในแถว policy (แก้ JSON); ถ้าเป็น media GET ที่ต้องใช้ใน `src` ให้ `allow_query_scope: true` + ตรวจ ownership ของ path ใน handler
2. handler: `scope: ChannelScope = Depends(get_channel_scope)` → ส่ง `scope.channel_id` ลง service/store; **ห้าม**อ่าน channel จาก body/query เอง
3. record ใหม่: บันทึก `channel_id = scope.channel_id` ตอนสร้าง (ห้ามเชื่อ `channel_id` จาก client); record ลูกตรวจกับ parent
4. อ่าน/แก้ตาม ID: โหลด record → `ensure_same_channel(scope, record.get("channel_id"), resource_label=…)`
5. สร้างงานใหม่ → `require_active_for_new_work`; แก้ข้อมูล → `require_writable`; final render/export/post → `require_final_ready`
6. งาน background/worker: เก็บ `scope.channel_id` + `scope.revision` + `scope.identity_hash` ลง job ตอนสร้าง ห้ามอ่าน active channel ใหม่กลางงาน

## 8. HTTP API `/api/channels` (global, ignore_scope_header)

`GET /api/channels?include_archived=true` → `{channels, revision, schema_version, default_channel_id, strict_mode, registry_exists}` · `GET /api/channels/{id}` → `{channel, registry_revision}` · `POST /api/channels` (201, draft) → `{channel}` · `PATCH /api/channels/{id}` body = ฟิลด์ที่แก้ + `expected_revision` (บังคับ) · `POST /{id}/activate` / `POST /{id}/archive` body `{expected_revision?}` · `GET /{id}/readiness` → `{channel_id, status, revision, identity_hash, ready, issues[], posting_ready, posting_issues[]}`. ไม่มี DELETE (405)

## 9. Kit sync

`tools/sync_channels.py` (default dry-run แสดง unified diff; `--apply` เขียน atomic + เก็บ `channels.js.bak`; idempotent; รักษา CRLF/LF เดิม; exit 2 เมื่อไม่มีโฟลเดอร์ kit / registry เสีย / avatar อยู่นอก `_HyperFrames_Studio` / ฟิลด์ไม่ใช่ข้อความ) สร้าง `window.HF_CHANNELS = {<id>: {name, handle, avatar, watermark, followTitle}}` ตามที่ `HF.applyChannel()` ใช้ (avatar เป็น path จาก studio root). emit ทุกช่องรวม draft/archived เพื่อให้ composition เก่าที่อ้างช่องนั้นยังหาเจอ; ช่องที่ไม่ active มี comment `// status: …`; readiness gap พิมพ์เป็นคำเตือน. dry-run กับ kit จริง ณ วันนี้: ข้อมูล `main` ตรงทุกค่า ต่างเฉพาะ comment

## 10. การตัดสินใจที่แผนไม่ได้กำหนด (พร้อมเหตุผล)

1. **Global route เมิน header เฉพาะ `/api/channels*`** (`ignore_scope_header`) — นอกนั้น header ผิด = 422 เสมอ; เพื่อให้มีทางกู้เมื่อ client ถือ id ที่ไม่มีแล้ว
2. **`?channel=` บน channel route ที่ไม่ flag → 422** แทนการเมิน — กัน fallback ไป main เงียบ ๆ
3. **Implicit default scope เป็น lazy** — compatibility mode ไม่อ่าน registry เลย ไฟล์เสียก็ไม่กระทบ route เดิม
4. **Middleware ไม่บล็อก write ของช่อง archived แบบเหมารวม** — บาง write ต้องทำได้หลัง archive (บันทึกผลโพสต์ที่ค้าง, stats) จึงให้ handler เรียก helper ตามกรณี
5. **handle ห้ามซ้ำกับ draft ด้วย** (แผนระบุแค่ active) — จับปัญหาตั้งแต่ตอนกรอก ไม่ต้องรอ activate
6. **activate ต้องไม่มี profile issue** — `active` จึงหมายถึงตัวตนครบ ณ ตอน activate; final render ยังตรวจซ้ำ
7. **`main` archive ไม่ได้** — ป้องกัน default scope กลายเป็น read-only ใน compatibility mode
8. **ความยาวข้อความวัดเป็น px ด้วยฟอนต์จริง** (Pillow `getlength` + fontTools cmap จาก `02_Assets/Fonts` ซึ่ง sha256 ตรงกับ `kit/fonts`) + เพดานจำนวนตัวอักษร; ไม่มีไฟล์ฟอนต์ → ใช้แค่เพดานตัวอักษรและ heuristic อีโมจิ; ตัวเลขดูตาราง 4.1
9. **เปลี่ยน handle → binding reset + posting ปิด** — binding เดิมพิสูจน์บัญชีเก่าเท่านั้น
10. **posting gate ตรวจเฉพาะตอนเปิด** — การแก้ฟิลด์อื่นไม่ถูกบล็อกเพราะรูปหาย; P5 ต้องตรวจ `posting_issues` ทุกครั้งก่อนโพสต์
11. **ไฟล์ lock `_Docs/channels.json.lock`** เกิดเมื่อเขียนครั้งแรก (OS ปล่อย lock เองถ้า process ตาย) — ควรเพิ่มใน `.gitignore` (ยังไม่ได้แก้เพราะอยู่นอก scope)
12. **error มี `code` + header `X-OmniCut-Error-Code`** โดย `detail` ยังเป็น string ไทย — เข้ากับ client เดิม
13. **sync emit ช่อง archived/draft ด้วย** — composition เก่าไม่หลุดเป็น "unknown channel" ระหว่างที่ P4 ยังไม่มี frozen snapshot
14. **ไม่สร้าง `_Docs/channels.json` จริงในรอบนี้** — ระบบทำงานด้วย implicit main; seed ทำเมื่อเจ้าของสั่ง (`get_default_store().seed()` หรือ `POST /api/channels` ครั้งแรก)

## 11. ข้อจำกัด / งานที่ส่งต่อ

- `/api/media/{file_path:path}` เป็น channel route แต่เสิร์ฟ shared asset ด้วย (ฟอนต์ `@font-face`, สติกเกอร์, effects ใน `02_Assets`); เมื่อเปิด strict ใน P8 คำขอที่ไม่มี scope จะได้ 422 — P6/P7 ต้องต่อ `?channel=` ทุก URL หรือทำ policy แบบแยกตาม path prefix ก่อนเปิด strict
- QR/mobile recording token และ extension ยังไม่ส่ง header (P5/P7)
- P4: Global Editor watermark (`subtitle_engine.py` / `SequencePlayer.jsx`) ยังเป็นค่าคงที่ ต้องย้ายมาใช้ snapshot และ verify เฟรมจริงกับข้อความยาวสุดที่ limit อนุญาต

## 12. P2 store contract (เพิ่ม 2026-10-10 โดย Claude Code (Claude Opus 5.5) — agent P2.1)

สัญญาที่ P2.2 (Export/Post/Schedule) และ P2.3 (migration tool) ต้องใช้ — โค้ดอ้างอิง: `scripts/db.py`, `scripts/channel_ownership.py`, `scripts/product_store.py`, `scripts/api_products.py`; เทส: `tests/test_channel_store_primitives.py`, `tests/test_channel_products.py`

### 12.1 Ownership ระดับ record

- record ของงานช่องมี key บนสุด `channel_id` (slug); ไม่มี key หรือเป็น `None` = **legacy**
- legacy นับเป็น `main` **เฉพาะ strict ปิด** (compat); strict เปิด → scoped read มองไม่เห็น และเขียนไม่ได้ (ต้องให้ P2.3 กำหนดเจ้าของ)
- record ลูกที่อยู่ในเอกสารเดียวกัน (angles/batches ใน product) ไม่ต้องมี `channel_id`; ถ้ามีต้องเท่ากับของ parent ไม่งั้น 422 `channel_child_mismatch`
- record ใหม่ stamp `channel_id` ที่ server จาก scope เสมอ; การเขียนผ่าน scope ปกติเพิ่ม/แก้/ลบ `channel_id` ไม่ได้ (legacy → main ก็ไม่ได้ — นั่นคืองาน migration)

### 12.2 Scope ของ store method (`scripts/channel_ownership.py`)

```python
from scripts.channel_ownership import (
    OWNER_KEY, StoreScope, resolve_store_scope, owner_for_new_record,
    reject_owner_change, reject_foreign_body_channel, ALL_CHANNELS_ALLOWED_MODULES,
)
resolve_store_scope(channel_id: str | None = None, *, all_channels: bool = False) -> StoreScope
#  "a"               -> StoreScope("a", include_legacy=(a == "main" and not strict))
#  None (compat)     -> unscoped = ทุกแถว (พฤติกรรมเดิม); record ใหม่เป็นของ main
#  None (strict)     -> ChannelError 422 channel_scope_missing
#  all_channels=True -> unscoped ทุกโหมด (maintenance/migration เท่านั้น); สร้าง record ใหม่ไม่ได้
#  slug ผิดรูป       -> 422 channel_scope_invalid ; ส่งทั้ง channel_id และ all_channels -> ValueError
StoreScope.owns(record) -> bool ; .unscoped ; .effective_owner
owner_for_new_record(scope, client_value=None) -> str   # client_value ไม่ตรง -> 422 channel_scope_conflict
reject_owner_change(current_record, requested)          # ไม่ตรง -> 422 channel_id_immutable
reject_foreign_body_channel(payload, channel_id)        # body.channel_id ไม่ตรง header -> 422 channel_scope_conflict
```

- ทุก public method ของ store ที่อ่าน/เขียนข้อมูลช่อง รับ keyword `channel_id: str | None = None` และ `all_channels: bool = False`
- `all_channels=True` ใช้ได้เฉพาะโมดูลใน `ALL_CHANNELS_ALLOWED_MODULES` (เทส `test_all_channels_only_in_allowlisted_modules` สแกน `scripts/` + `tools/`; `scripts/api_*.py` ห้ามอยู่ใน allowlist). P2.2/P2.3 ที่เพิ่มโมดูล maintenance ใหม่ต้องเพิ่มชื่อใน allowlist ในคอมมิตเดียวกัน (จองไว้แล้ว: `export_registry.py`, `post_log.py`, `schedule_store.py`, `migrate_compound_angle_ids.py`, `tools/migrate_channels.py`)

### 12.3 Primitive ใน `scripts/db.py`

```python
DocumentTable.scoped_mutate(channel_id: str, *, include_legacy: bool = False, owner_key: str = "channel_id")
    # context manager -> ScopedRecords (list ของแถวใน scope; .out_of_scope = สำเนาแถวอื่น อ่านอย่างเดียว)
DocumentTable.scoped_load(channel_id: str, *, include_legacy: bool = False, owner_key: str = "channel_id") -> list[dict]
class ChannelIsolationError(RuntimeError)      # .code = "channel_isolation_violation", .record_ids
class NestedTransactionError(sqlite3.OperationalError)
```

- transaction เดียวกับ `mutate()` (`BEGIN IMMEDIATE` ตลอด block) → ตรวจ + เขียนใน transaction เดียว ไม่มี TOCTOU
- ตอน commit ตรวจทุกแถวที่ เพิ่ม/แก้/ลบ: แถวใหม่ต้อง `owner_key == channel_id` และ id ต้องไม่ซ้ำแถวใดในตาราง; แถวที่แก้ต้องคง owner เดิม (รวมการมี/ไม่มี key); แถวที่จะ UPDATE/DELETE ถูกอ่านซ้ำจาก DB ใน transaction และต้องยังอยู่ใน scope — ผิดข้อใด = `ChannelIsolationError` + ROLLBACK ทั้ง block (0 แถว, ไม่เขียน JSON mirror)
- batch: ทำทุก item ใน block เดียว → item ต่างช่องตัวเดียวทำให้ทั้ง batch ไม่ถูกเขียน (AC03)
- JSON mirror ยังเขียนจาก SELECT ทั้งตาราง (ทุกช่อง) หลัง commit; `out_of_scope` ใช้ตรวจ uniqueness ระดับ global เท่านั้น (แก้แล้วไม่ถูกบันทึก)
- **ห้ามเรียก store อื่นที่เขียนจากใน `mutate()/scoped_mutate()`** (ทุกตารางใน `store.db` ใช้ connection เดียวกันต่อ thread): ตอนนี้ `mutate()/scoped_mutate()/save()` ซ้อนได้ `NestedTransactionError` ทันที (subclass ของ `OperationalError` → handler เดิมยังจับได้) ส่วน `load()` ซ้อนยังอ่านได้แต่ข้ามการ import mirror. แก้ด้วย staged work (เก็บงานไว้ทำหลัง commit แบบ idempotent) หรืออ่านก่อนเปิด block — ตัวอย่าง `ProductStore._invalidate_shot_lists()`
- ห้ามเปลี่ยน `_load()` ให้คืนแถวที่กรองแล้วไป `_save()` (จะลบแถวช่องอื่น); `_load/_save/_mutate` = internal full-table เท่านั้น

### 12.4 ProductStore (public; ทุกตัวรับ `*, channel_id=None, all_channels=False`)

| method | หมายเหตุ |
|---|---|
| `add(name, url="", …, canonical_product_key=None, source_product_id=None, *, channel_id, all_channels)` | stamp owner; URL dedup ต่อ `(channel, url)` (compat `None` = dedup ใน main+legacy เท่านั้น); `product_code` unique ทุกช่อง+legacy; `all_channels` สร้างไม่ได้ |
| `update(product_id, *, channel_id, all_channels, **fields)` | `channel_id` เป็น scope ไม่ใช่ field (เปลี่ยนเจ้าของไม่ได้); shot list ที่บทเปลี่ยนถูกลบ**หลัง** commit |
| `get / list(status) / get_all / summary / find_by_project / get_product_videos` | อ่านใน scope; id ของช่องอื่น = ไม่พบ (`None`/ValueError) |
| `update_angle_status / replace_angle_content / append_angles / add_single_angle / update_angle_cover / update_angle_videos / update_angle_voice / update_angle_manual_shot_map / batch_update_manual_shot_maps / set_default_videos_for_all_angles / add_video_to_product / remove_video_from_product / remove_angle / attach_project / delete / rollback_by_video_or_project / reconcile_existing_projects` | แก้เฉพาะ product ใน scope; การ "ปลด angle ที่ชนไฟล์/โปรเจกต์" อยู่ในช่องเดียวกันเท่านั้น; `remove_angle` ตรวจ+เขียนใน transaction เดียว |
| `snapshot()` / `find(product_id)` | อ่านตรงไม่ reconcile (แทน `_load()` ภายนอก) |
| `owner_of(product_id) -> (exists, channel_id)` | system read ข้ามช่อง สำหรับ guard 404 |
| `has_posted_angle_for_project(project_name)` | guard ห้ามเรนเดอร์ทับคลิปที่โพสต์แล้ว |
| `rename_video_references(*, old_abs, old_rel, old_name, new_info, product_id=None)` / `remove_video_references(matches)` | อัปเดต `videos[]` เมื่อไฟล์ raw (shared) ถูกเปลี่ยนชื่อ/ลบ |
| `backfill_missing_product_codes(*, dry_run=False)` / `apply_to_each_product(fn, *, dry_run=False)` | maintenance ใน transaction เดียว; `apply_to_each_product` ห้าม fn เปลี่ยน `channel_id` |

- angle อ้างด้วย `(product_id, angle_id[, batch])` เสมอ (angle_id ซ้ำข้ามสินค้าได้)
- **บทเรียนสำหรับ P2.2:** call แบบ unscoped (`None`/`all_channels`) ต้องวิ่งผ่าน `cls._mutate()`/`cls._load()` เดิมของ store (ไม่เรียก `_TABLE` ตรง) — เทสเดิมหลายไฟล์ patch จุดนี้เพื่อฉีดข้อมูล; ถ้าข้ามไป เทสจะวิ่งเข้าฐานจริง (`ProductStore._scoped_mutate/_scoped_load` เป็นตัวอย่าง)
- product ไม่มี revision protocol ฝั่ง client → ไม่สร้าง 409 revision ใหม่ใน P2.1 (P3 จัดการ revision ของ editor)

### 12.5 API (`scripts/api_products.py`)

- ทุก handler ของ channel route: `scope: ChannelScope = Depends(get_channel_scope)` → ส่ง `scope.channel_id` ลง store; worker เบื้องหลังรับ `channel_id` ที่ตรึงไว้ตอนรับ request
- route ที่มี `{product_id}`: เมื่อ lookup/เขียนแบบ scoped แล้ว "ไม่พบ" → `_raise_if_foreign()` (`owner_of` + `find`) → สินค้าช่องอื่น (หรือ legacy ที่ strict ซ่อน) = 404 `resource_not_found`; id ที่ไม่มีเลยยังได้ response เดิมของแต่ละ route. ไม่มี side effect ต่อสินค้าช่องอื่นเพราะ store แบบ scoped ไม่เห็นแถวนั้น; route ที่มี side effect ก่อนเรียก store (`DELETE …/videos` ย้ายไฟล์ raw) ตรวจการมองเห็นก่อนย้ายไฟล์; route ที่ต้องสร้าง task/เรียก AI ทำ `get` (scoped) ก่อนเสมอ. ลำดับนี้คง patch point เดิมของเทส (`ProductStore.get/_load/_mutate`) ไว้
- สร้างงานใหม่ (`scrape-and-plan[-async]`, `generate-batch`, `POST …/angles`) → `require_active_for_new_work` (draft/archived → 409 `channel_not_active`); แก้ข้อมูล → `require_writable` (archived → 409 `channel_archived`); **implicit default scope (compat ไม่มี header) ข้ามการตรวจสถานะ** เพื่อไม่อ่าน registry (ADR §10.3) — ปลอดภัยเพราะ `main` archive ไม่ได้
- body `channel_id` ไม่ตรง header → 422 `channel_scope_conflict`; angle ใน body ระบุช่องอื่น → 422 `channel_child_mismatch`
- compat ไม่มี header + ข้อมูล legacy: response เท่ากับก่อนแก้ (พิสูจน์บนสำเนาฐานจริง 27 สินค้า/274 angles) ยกเว้น record ที่สร้างใหม่มี `channel_id: "main"`
- ไม่ได้แก้ `scripts/channel_route_policy.json` (การจัดประเภท route ไม่เปลี่ยน)

### 12.6 ช่องว่างที่ส่งต่อ (ยังไม่ทำใน P2.1)

- `GET/POST/PATCH/DELETE /api/products` และ route อื่นใน `api_phase1.py`, `api_videos.py`, `api_render.py` ยังเรียก store ด้วย `channel_id=None` (compat = เห็นทุกช่อง; strict = 422 fail-closed) มี marker `# TODO(P3 channel scope)` ที่จุดที่แก้ — **ก่อนเปิดช่องรองต้องให้ P3 ผูก scope** ไม่งั้น list สินค้าแบบไม่มี header จะรวมทุกช่อง
- caller อื่นของ ProductStore (mobile_quick_studio, api_shot_lists, batch_render, api_exports, api_covers, api_analytics, task_manager, …) ยังเป็น compat `None`
- `update_angle_status(export_id=…)` ยังไม่ตรวจว่า export เป็นของช่องเดียวกัน (รอ ExportRegistry แบบ scoped ใน P2.2)
- `scripts/tiktok_pending.py:129` ยังอ่าน `_IGNORED_TABLE` ซ้อนใน `_TABLE.mutate()` (P3) — `load()` ซ้อนไม่ crash แล้วแต่ข้าม import mirror

## 13. P2.2 store contract — Export / PostLog / Schedule (เพิ่ม 2026-10-10 โดย Claude Code (Claude Opus 5.5) — agent P2.2)

ต่อยอด §12 (ใช้ `resolve_store_scope` / `DocumentTable.scoped_mutate` / `owner_for_new_record` เดิม) — โค้ด: `scripts/export_registry.py`, `scripts/post_log.py`, `scripts/schedule_store.py`, `scripts/api_exports.py`, `scripts/api_posts.py`, `scripts/api_schedule_queue.py`; เทส: `tests/test_channel_exports_posts.py`, `tests/test_channel_schedule.py`

### 13.1 กติการ่วม

- ทุก public method รับ `*, channel_id: str | None = None, all_channels: bool = False` ตาม §12.2 (None ใน compat = พฤติกรรมเดิมทุกแถว, strict = 422 `channel_scope_missing`; `all_channels` สร้างแถวใหม่ไม่ได้)
- call แบบ unscoped วิ่งผ่าน `cls._load()` / `cls._mutate()` เดิม (patch point ของเทสเดิม); scoped write ใช้ `scoped_mutate` → แถวช่องอื่นไม่ถูกเปิดเผย/เขียน และตรวจซ้ำตอน commit
- record ใหม่ทุกตัว (export row, post, queue row, template) มี `channel_id` บนสุดจาก scope; legacy (ไม่มี key) แก้ได้เฉพาะ main ใน compat และ**ยังคง legacy** (ไม่ stamp) — P2.3 เป็นคนกำหนดเจ้าของ
- `ChannelError` เป็น **Starlette** `HTTPException` ไม่ใช่ subclass ของ `fastapi.HTTPException` → โค้ดที่ `except HTTPException` (fastapi) จะจับไม่ได้ ต้องจับ `(HTTPException, ChannelError)` หรือ `except ChannelError: raise` ก่อน `except Exception` (เจอจริงใน auto-fill preview แล้วแก้)
- system read ข้ามช่องสำหรับ guard 404 เท่านั้น: `ExportRegistry.owner_of / path_owners / out_of_scope_paths`, `PostLog.owner_of`, `ScheduleQueueStore.owner_of`
- ไม่แก้ `ALL_CHANNELS_ALLOWED_MODULES` (ใช้ `all_channels=True` เฉพาะใน `product_store.py` และ `migrate_compound_angle_ids.py` ที่อยู่ใน allowlist แล้ว) และไม่แก้ `channel_route_policy.json` (ทุก route ยังเป็น `channel`)

### 13.2 ExportRegistry

```python
all(*, channel_id, all_channels) -> list            # สำเนาแถวใน scope
path_index(*, channel_id, all_channels) -> {path_key: export_id}   # cache ทุกแถวครั้งเดียวต่อการเปลี่ยน แล้วกรองต่อ scope
get(export_id, *, ...) ; find_by_path(path, *, ...) ; find_for_angle(pid, aid, *, status, ...) ; latest_for_angle(pid, aid, *, ...)
lookup(*, export_id=None, path=None, channel_id, all_channels) -> row | None
    # None = ไม่มีลงทะเบียนเลย (route ใช้ response เดิม); ลงทะเบียนอยู่นอก scope -> ChannelError 404 resource_not_found
ensure(path, *, product_id, angle_id, project_name, status, posted_at, channel_id, all_channels)
ensure_many(entries, *, channel_id, all_channels)
move_and_mark_posted(export_id, path, *, posted_at, channel_id, all_channels)
update_path(export_id, path, *, ...) ; remove(export_id, *, ...)
apply_to_each(fn, *, channel_id, all_channels) -> int   # maintenance; fn ห้ามเปลี่ยน channel_id
owner_of(export_id) -> (exists, channel_id) ; path_owners(path) -> [(export_id, channel_id)] ; out_of_scope_paths(*, channel_id) -> [path]
```

- identity = `export_id`; path เป็นตำแหน่งเท่านั้น. basename/path เดียวกันใน A และ B = คนละแถว ไม่ merge/ไม่คืนข้ามช่อง
- path ที่ลงทะเบียนเป็นของช่องอื่น (หรือ legacy ที่ strict ซ่อน): `ensure/ensure_many` → 404 ทั้งชุด (ไม่ claim ไฟล์ของอีกช่อง); `move_and_mark_posted/update_path` ไปทับ path นั้น → 409 `export_path_conflict`
- parent product: call แบบ scoped ตรวจ `ProductStore.owner_of(product_id)` **ก่อน**เปิด transaction → สินค้าช่องอื่น = 409 `channel_child_mismatch` (product id ที่ไม่มีอยู่เลยไม่ตรวจ = เหมือนเดิม; compat None ไม่ตรวจ — ดู 13.7)
- `ProductStore.update_angle_status(export_id=…)`: อ่าน export แบบข้ามช่องแล้วเทียบเจ้าของกับสินค้าใน transaction → ไม่ตรง 409 `channel_child_mismatch` (scoped: export ต้องอยู่ใน scope เดียวกัน; unscoped: legacy = main); `reconcile_existing_projects` ใช้ export ของ scope เดียวกับสินค้า

### 13.3 PostLog

```python
add_post(..., *, channel_id, all_channels) ; update_metrics(post_id, metrics, *, ...)   # id ช่องอื่น = ValueError ไม่พบ
record_posted_export(product_name, clip_file, export_id="", ..., *, channel_id, all_channels)
    -> {"status": "matched_export" | "matched_legacy" | "created" | "ambiguous",
        "post": dict | None, "candidate_post_ids": [str]}
register_posted_export(...same...) -> post | None        # wrapper เดิม; None = ambiguous (ไม่ได้เขียน)
upsert_tiktok_stats(rows, register_missing, clip_candidates, *, ...) ; attach_manual(row, post_id, candidate, *, ...)
list_posts / get_all(newest_first, *, ...) ; pending_metrics / angle_performance / summary(*, ...) ; owner_of(post_id)
```

- idempotency key = (channel, export_id). fallback basename (ไฟล์เดิม `post_log.py:~252/~371`) ทำในช่องเดียวกันเท่านั้น และนับเฉพาะแถวชื่อไฟล์ตรงที่ไม่มี export_id อื่น: **1 แถว** = ผูก (`matched_legacy`, เติม field ว่าง, แถว legacy ยังไม่มี channel_id); **≥2** = `ambiguous` ไม่เขียนอะไรเลย; **0** = สร้างใหม่. ชื่อกลาง (`clip.mp4`, `video.mp4`, ว่าง) ไม่เคยใช้จับคู่
- `upsert_tiktok_stats`: video id / fuzzy / basename เห็นเฉพาะโพสต์ของช่อง; basename ของ candidate ชน ≥2 โพสต์ → แถว Studio อยู่ใน `unmatched` พร้อม `ambiguous_post_ids` (ไม่ register ซ้ำ); โพสต์ที่ register ใหม่ stamp ช่อง
- `attach_manual`: candidate จับ clip_file ตรงตัวก่อน (ชื่อกลางไม่นับ) แล้วค่อย hook; ชน ≥2 → `ValueError` ให้เลือก `post_id` เอง
- mark-posted ที่ ambiguous: response เพิ่ม `post_log_warning: {"code": "post_log_ambiguous", "detail": <ไทย>, "candidate_post_ids": [...]}` (มีเฉพาะกรณีนี้)
- ข้อมูลจริง (สำเนา): 72 โพสต์, `clip.mp4` 7 แถว (ไม่จับคู่เด็ดขาด), basename ซ้ำ 3 ชื่อ → ทั้ง 3 ได้ `ambiguous` และไม่มีแถวถูกแก้

### 13.4 Schedule (`scripts/schedule_store.py`)

```python
ScheduleQueueStore.transaction(*, channel_id, all_channels)   # context manager: แถวของช่องเดียวใน write txn เดียว (bulk create/commit)
ScheduleQueueStore.new_owner(*, ...) -> str                  # owner ที่ต้อง stamp บนแถวใหม่
ScheduleQueueStore.list_items / get_item(item_id) / occupied_times(*, ...)
ScheduleQueueStore.update_item(item_id, fn(row, channel_rows), *, ...) -> row | None   # fn raise = ไม่เขียน; ห้ามเปลี่ยน channel_id
ScheduleQueueStore.remove_item(item_id, guard(row)=None, *, ...) -> row | None
ScheduleQueueStore.owner_of(item_id) -> (exists, channel_id)
ScheduleTemplateStore.template_id(channel_id, week_key=None)   # "<ch>:default" / "<ch>:week:YYYY-MM-DD"
ScheduleTemplateStore.legacy_template_id(week_key=None)        # "default" / "week:YYYY-MM-DD"
ScheduleTemplateStore.list_templates / find_template(week_key, *, ...) / upsert_template(week_key, days, *, timezone, updated_at, ...) / delete_template(week_key, *, ...)
schedule_state_revision(queue_rows, template_rows, post_rows) -> "sq1:<sha256 hex>"
```

- item อ้างด้วย (channel, id) เสมอ — ห้าม lookup ด้วย id อย่างเดียว; id ช่องอื่น = 404 `resource_not_found` (id ที่ไม่มีเลย = 404 เดิม `{"detail": "ไม่พบรายการในคิว"}`)
- เวลาที่ถูกใช้/ชน คิดต่อช่อง: เวลาเดียวกันใน A และ B ได้; ในช่องเดียวกฎเดิมทุกข้อ (create/commit นับแถว posted ด้วย, PATCH ย้ายเวลาไม่นับ posted); กฎรายวัน (สินค้า/สี Hook ซ้ำวันเดียว) และ analytics ใช้โพสต์ของช่องนั้น
- template: ช่องที่ไม่ใช่ main ใช้ id ใหม่เท่านั้น; main (compat) อ่าน id ใหม่ก่อน แล้ว fallback id legacy ที่ไม่มี channel_id; แก้ legacy = แก้ในที่เดิม (id/ไม่มี owner คงเดิม); reset ลบทั้ง id ใหม่และ legacy ของช่องนั้น; strict ไม่เห็น legacy. response ยังเป็นรูปเดิม (`id` = `default` / `week:<date>` แบบ local ของช่อง ไม่มี `channel_id`); `timezone: "Asia/Bangkok"` คงเดิม ไม่เปลี่ยน time format
- auto-fill: preview คืน `preview_revision` (= hash ของ queue rows + template rows ของช่อง + field โพสต์ที่กฎใช้ `id, posted_at, product_id, product_name, style_preset, hook_color, clip_file, metrics, metrics_history`). commit body รับ `preview_revision`: ส่งมาแล้วไม่ตรง (คำนวณ queue ส่วนใน transaction เดียวกับการเขียน) → 409 `revision_conflict` + `current_revision`; ไม่ส่ง → compat ทำแบบเดิม (ยังตรวจชน/กฎรายวันแบบ atomic), strict → 422 `expected_revision_required`. การเปลี่ยนในช่องอื่นไม่ทำให้ token ของช่องนี้ stale

### 13.5 API

- ทุก handler ใน 3 router: `scope: ChannelScope = Depends(get_channel_scope)`; handler ที่ถูกเรียกตรง (ไม่ผ่าน FastAPI, เช่นเทสเดิม `list_exports()`) ได้ `None` = compat unscoped
- สร้างงานใหม่ (POST queue, auto-fill commit, prepare, POST post-log) → `require_active_for_new_work`; แก้ (PATCH/DELETE queue, template PUT/copy/DELETE, link-angle) → `require_writable`; implicit default ข้ามการตรวจสถานะ (§12.5). **mark-posted และ metrics** อนุญาตช่อง archived (บันทึกผลโพสต์ที่เกิดแล้ว ADR §10.4)
- ไฟล์ export: id/ไฟล์ที่ลงทะเบียนเป็นของช่องอื่น → 404 ก่อนย้ายไฟล์/เขียนใด ๆ; ไฟล์ที่**ยังไม่ลงทะเบียน**ใช้ได้เฉพาะ scope ที่ legacy เป็นของตน (compat main) เพราะ 04_Exports ยังแบน (P6) — ช่องอื่น/strict = 404 `resource_not_found`. mark-posted ตรวจว่าปลายทาง `Posted/<name>` ไม่ใช่ path ของแถวช่องอื่น (409 `export_path_conflict`) ก่อนย้าย; คิวที่ปิดตอน mark-posted หาในช่องเดียวกัน และ fallback ชื่อไฟล์ต้องได้แถวเดียว
- `GET /api/exports`: แสดงเฉพาะไฟล์ที่ลงทะเบียนในช่อง (+ไฟล์ไม่ลงทะเบียนเมื่อ compat main) จับคู่กับสินค้าของช่อง; ไม่ claim ไฟล์ให้ช่องอื่น
- bulk (`POST /api/schedule-queue` แบบ items, `POST /auto-fill`): ตรวจทุก item ก่อน; item ช่องอื่น/ไม่ลงทะเบียน → 404 `resource_not_found` + `foreign_items: [{index, video_path, export_id}]` ไม่เขียนสักแถว; error อื่นเป็นแบบเดิม (item แรกที่ผิด)
- body `channel_id` ไม่ตรง header ใน `POST /api/post-log` → 422 `channel_scope_conflict`

### 13.6 Compat (พิสูจน์บนสำเนา `store_copy2.db`: export 212 / posts 72 / queue 156 / template 1)

HEAD code vs code ใหม่บนสำเนาแยกกัน: อ่านแบบ `channel_id="main"` = อ่าน legacy เดิมทุกตัว (ids/bytes); `GET` 12 URL ของ post-log/schedule-queue/template ไม่มี header และ header `main` ได้ bytes เท่ากับ HEAD; scoped no-op write ไม่เปลี่ยน byte ของ 4 ตาราง; ผล 49/49. สิ่งที่เพิ่มใน response: แถวใหม่มี `channel_id`, preview มี `preview_revision`, `post_log_warning` / `ambiguous_post_ids` เฉพาะกรณีกำกวม

### 13.7 ส่งต่อ (ยังเป็น compat `None` — strict = 422 fail-closed)

- **P3:** `scripts/stages/video_assembly_stage.py` (`ExportRegistry.ensure` ตอนเรนเดอร์ — compat None stamp `main` แม้สินค้าเป็นของช่องอื่น และไม่ตรวจ parent; P3 ต้องส่ง channel ของงาน), `scripts/api_videos.py` (`find_by_path/update_path/remove/get` ใน rename/delete-file), `scripts/api_hyperframes.py` (`ensure_many`), `scripts/api_phase1.py` (`PostLog.*` ของ `/api/phase1`-style routes)
- **P5:** `scripts/api_tiktok_autopost.py` (`prepare()` ใช้ ExportRegistry unscoped + `_pending` กลาง + อัปเดตคิวด้วย `update_item(channel_id=None)`), `scripts/api_tiktok_stats.py` (PostLog ทุก call + candidates จากคิวทุกช่อง) — มี marker `TODO(P5 channel scope)`; `prepare_queue_item` เรียก `prepare()` หลังหา item ในช่องแล้ว
- **P6:** 04_Exports/Posted/05_Covers ยังแบน — cover/companion หาโดย stem (`_find_cover_by_stem`, `_posted_companions`), `video_key = 04_exports/<basename>`; ไฟล์ไม่ลงทะเบียนใช้ได้แค่ compat main
- **P2.3:** rename template `default`→`main:default`, `week:<d>`→`main:week:<d>` (+`channel_id`); กำหนดเจ้าของ legacy rows ของ export_registry/posts/schedule_queue; ข้อมูลจริงมี export 2 แถว path เดียวกัน (`04_Exports/Ready_to_post/BCD01-POV_Chat_1_20261010_160500.mp4`) ต้องตัดสินก่อน migrate
