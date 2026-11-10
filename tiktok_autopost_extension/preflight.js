// Pre-run readiness verdict (pure: it only reads what the panel and the worker collected, so it is unit-testable).
// A blocker stops the run before anything is typed or clicked; a warning is shown and the run may go on.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniPreflight = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const EXPECTED_PROTOCOL = 2;
  const MIN_WIDTH = 1000;

  const handleOf = (raw) => {
    const value = String(raw || '').trim().toLowerCase();
    const at = value.match(/@([a-z0-9._]+)/);                       // "@name", "https://www.tiktok.com/@name"
    if (at) return '@' + at[1];
    return /^[a-z0-9._]+$/.test(value) ? '@' + value : '';          // a bare "name"; anything else is unreadable
  };

  // input: {
  //   backend:   {ok, status, protocol_version, error}        -- GET /api/tiktok-autopost/capabilities
  //   channel:   {id, handle}                                   -- the channel the panel will post to
  //   worker:    {success, error, loggedIn, uploadInput, handle, viewport:{w,h}, quota, extensionVersion}
  //   mode:      'smart' | 'schedule_only' | 'draft_only'
  //   clipCount: number
  // }
  function evaluatePreflight({ backend = {}, channel = {}, worker = {}, mode = 'smart', clipCount = 0 } = {}) {
    const checks = [];
    const add = (id, label, status, detail = '') => checks.push({ id, label, status, detail });

    // backend + protocol
    if (!backend.ok) {
      const why = backend.status === 401 || backend.status === 403 ? 'API key ผิดหรือไม่มี' : (backend.error || `HTTP ${backend.status || '?'}`);
      add('backend', 'Backend ตอบ', 'fail', why);
    } else if (backend.protocol_version !== EXPECTED_PROTOCOL) {
      add('backend', 'Backend ตอบ', 'fail', `protocol ${backend.protocol_version ?? '?'} แต่ extension ต้องการ ${EXPECTED_PROTOCOL} — อัปเดตให้ตรงกัน`);
    } else {
      add('backend', 'Backend ตอบ', 'ok', `protocol ${backend.protocol_version}`);
    }

    // page reachable at all
    if (!worker || worker.success === false || worker.error) {
      add('page', 'อ่านหน้า TikTok Studio', 'fail', worker?.error || 'ไม่ได้รับคำตอบจาก worker');
    } else {
      add('page', 'อ่านหน้า TikTok Studio', 'ok', worker.url || '');
      add('login', 'login TikTok', worker.loggedIn ? 'ok' : 'fail', worker.loggedIn ? '' : 'ยังไม่ login — login ในแท็บ TikTok Studio ก่อน');
      add('upload_input', 'หน้าอัปโหลดพร้อม (มีช่องเลือกไฟล์)', worker.uploadInput ? 'ok' : 'fail',
        worker.uploadInput ? '' : 'ไม่พบช่องเลือกไฟล์ — เปิด tiktok.com/tiktokstudio/upload (TikTok อาจเปลี่ยนหน้า หรือมี dialog ค้าง)');

      // the logged-in account must be the channel's account
      const seen = handleOf(worker.handle);
      const expected = handleOf(channel.handle);
      if (!expected) add('account', 'บัญชีตรงกับช่อง', 'warn', 'ช่องนี้ไม่มี handle ในระบบ จึงเทียบบัญชีไม่ได้');
      else if (!seen) add('account', 'บัญชีตรงกับช่อง', 'warn', 'อ่านบัญชีที่ login อยู่ไม่ได้ (จะตรวจอีกครั้งก่อนกดโพสต์ทุกคลิป)');
      else if (seen !== expected) add('account', 'บัญชีตรงกับช่อง', 'fail', `login อยู่เป็น ${seen} แต่ช่องนี้คือ ${expected}`);
      else add('account', 'บัญชีตรงกับช่อง', 'ok', seen);

      const width = Number(worker.viewport?.w || 0);
      if (width && width < MIN_WIDTH) add('viewport', 'ขนาดหน้าต่าง', 'warn', `กว้าง ${Math.round(width)}px — extension จะจำลองเป็น 1440px ระหว่างรัน แต่ควรขยายหน้าต่าง`);
      else add('viewport', 'ขนาดหน้าต่าง', 'ok', width ? `${Math.round(width)}px` : '');

      // quota for the mode that will be used
      if (mode === 'publish_now') {
        add('quota', 'โควตา', 'ok', 'โพสต์ตอนนี้ ไม่ใช้ช่องตั้งเวลา');
      } else {
      const q = worker.quota || {};
      const remS = typeof q.remainingSchedule === 'number' ? q.remainingSchedule : null;
      const remD = typeof q.remainingDraft === 'number' ? q.remainingDraft : null;
      const needsSchedule = mode !== 'draft_only';
      const needsDraft = mode === 'draft_only';
      if (needsSchedule && remS === 0) add('quota', 'โควตา', 'fail', 'โควตาตั้งเวลาเต็ม — รอคลิปเผยแพร่หรือลบรายการเดิมก่อน');
      else if (needsDraft && remD === 0) add('quota', 'โควตา', 'fail', 'โควตาแบบร่างเต็ม — ลบแบบร่างเก่าก่อน');
      else if ((needsSchedule && remS == null) || (needsDraft && remD == null)) add('quota', 'โควตา', 'warn', 'ยังอ่านโควตาไม่ได้ — ระบบจะนับสดอีกครั้งตอนเริ่มรอบ');
      else {
        const left = needsDraft ? remD : remS;
        add('quota', 'โควตา', clipCount > left ? 'warn' : 'ok', `เหลือ ${left}${clipCount > left ? ` (คลิปที่เลือก ${clipCount} — จะรันเฉพาะ ${left} คลิปแรก)` : ''}`);
      }
      }
    }

    const blockers = checks.filter((c) => c.status === 'fail');
    const warnings = checks.filter((c) => c.status === 'warn');
    return { ok: blockers.length === 0, blockers, warnings, checks };
  }

  function formatPreflight(result) {
    const mark = { ok: 'ผ่าน', warn: 'เตือน', fail: 'ไม่ผ่าน' };
    return result.checks.map((c) => `${mark[c.status]} · ${c.label}${c.detail ? ` — ${c.detail}` : ''}`).join('\n');
  }

  return { EXPECTED_PROTOCOL, evaluatePreflight, formatPreflight, handleOf };
});
