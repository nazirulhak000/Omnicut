(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniPrepareForm = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const fields = ['caption', 'hashtags', 'intent', 'date', 'time'];
  function clean(values) {
    return Object.fromEntries(fields.map(key => [key, typeof values?.[key] === 'string' ? values[key] : '']));
  }
  function fillProductName(text, productName) {
    return typeof productName === 'string' && productName.trim() ? String(text || '').replace(/\{product_name\}/g, () => productName) : String(text || '');
  }
  function createStore(storage, scope) {
    if (!storage || !scope.channelId || !scope.clipId) throw new Error('ไม่พบที่เก็บข้อมูลของคลิปนี้ กรุณาโหลด extension ใหม่');
    const key = 'omnicutClipEdits:v1:' + [scope.channelId, scope.clipId, scope.queueId || ''].map(encodeURIComponent).join(':');
    let pending = Promise.resolve();
    return {
      key,
      async load() {
        await pending.catch(() => {});
        const entry = (await storage.get(key))[key];
        return entry?.version === 1 && entry.channelId === scope.channelId && entry.clipId === scope.clipId ? clean(entry.values) : null;
      },
      save(values) {
        const entry = {version: 1, channelId: scope.channelId, clipId: scope.clipId, values: clean(values), savedAt: Date.now()};
        const work = pending.catch(() => {}).then(() => storage.set({[key]: entry}));
        pending = work;
        return work;
      },
    };
  }
  function build(item, values, guard, record, now = Date.now(), exportsKnown = true) {
    if (!['schedule', 'draft'].includes(values.intent)) return {error: 'กรุณาเลือกตั้งเวลาหรือบันทึกแบบร่าง'};
    const next = {...item, tiktok_caption: values.caption.trim(), tiktok_hashtags: values.hashtags.trim(),
      prepare_intent: values.intent, schedule_date: values.intent === 'schedule' ? values.date : '', schedule_time: values.intent === 'schedule' ? values.time : ''};
    const code = guard.clipSkipReason(next, record, now, {exportsKnown, ignoreSlot: values.intent === 'draft', requireSchedule: values.intent === 'schedule'});
    return code ? {code} : {item: next};
  }
  function validate(item, values, guard, record, now = Date.now(), exportsKnown = true, reasons = {}) {
    const issues = [];
    for (const [key, field] of [['caption', 'Caption'], ['hashtags', 'Tags']]) {
      const unresolved = [...new Set(String(values[key] || '').match(/\{[^{}]+\}/g) || [])];
      if (unresolved.length) issues.push({field, message: `กรุณาแทน ${unresolved.join(', ')} ใน${field === 'Tags' ? 'แฮชแท็ก' : 'คำอธิบาย'}ด้วยข้อมูลสินค้าจริงก่อนเตรียมคลิป`});
    }
    if (values.intent === 'schedule') {
      if (!values.date) issues.push({field: 'Date', message: 'กรุณาเลือกวันที่โพสต์ หรือเปลี่ยนเป็นบันทึกแบบร่าง'});
      if (!values.time) issues.push({field: 'Time', message: 'กรุณาเลือกเวลาโพสต์'});
      else if (!/^\d{2}:\d{2}$/.test(values.time) || Number(values.time.split(':')[1]) % 5 !== 0) issues.push({field: 'Time', message: 'กรุณาเลือกเวลาเป็นช่วงละ 5 นาที เช่น 12:00 หรือ 12:05'});
    }
    const result = build(item, values, guard, record, now, exportsKnown);
    if (!result.item && !issues.length) issues.push({field: result.code === 'slot_passed_or_too_close' ? 'Date' : 'Caption', message: result.error || reasons[result.code] || result.code});
    return issues.length ? {issues} : {...result, issues: []};
  }
  async function open(item, {guard, record, exportsKnown = true, reasons = {}, channelId, storage = globalThis.chrome?.storage?.local}) {
    const store = createStore(storage, {channelId, clipId: item.export_id || item.id || item.rel_path, queueId: item.is_scheduled ? item.id : ''});
    const saved = await store.load();
    const initial = saved || {caption: item.tiktok_caption || item.caption || '', hashtags: item.tiktok_hashtags || item.hashtags || '',
      intent: item.prepare_intent || 'schedule', date: item.schedule_date || '', time: item.schedule_time || ''};
    initial.caption = fillProductName(initial.caption, item.product_name);
    initial.hashtags = fillProductName(initial.hashtags, item.product_name);
    return new Promise(resolve => {
      const dialog = document.createElement('dialog');
      dialog.className = 'app-dialog clip-setup-dialog';
      dialog.setAttribute('aria-labelledby', 'clipSetupTitle');
      dialog.innerHTML = `<form id="clipSetupForm" novalidate><h2 id="clipSetupTitle">เตรียมข้อมูลคลิป</h2>
        <p>บันทึกข้อมูลไว้ใน extension เครื่องนี้ได้แม้ยังกรอกไม่ครบ การเตรียมคลิปยังไม่อัปโหลดหรือเผยแพร่</p>
        <p id="clipSetupError" role="alert"></p>
        <label for="clipSetupCaption">คำอธิบายคลิป</label><textarea id="clipSetupCaption" rows="4" aria-describedby="clipSetupError"></textarea>
        <label for="clipSetupTags">แฮชแท็ก</label><input id="clipSetupTags" type="text" aria-describedby="clipSetupError">
        <label for="clipSetupIntent">รูปแบบการเตรียม</label><select id="clipSetupIntent"><option value="schedule">ตั้งเวลาโพสต์</option><option value="draft">บันทึกเป็นแบบร่างบน TikTok</option></select>
        <div id="clipSetupSlot"><label for="clipSetupDate">วันที่โพสต์</label><input id="clipSetupDate" type="date" aria-describedby="clipSetupError"><label for="clipSetupTime">เวลาโพสต์</label><input id="clipSetupTime" type="time" step="300" aria-describedby="clipSetupError"><p>เลือกเวลาอย่างน้อย 15 นาทีข้างหน้า</p></div>
        <p id="clipSetupSaveStatus" role="status"></p>
        <div class="row"><button id="clipSetupCancel" type="button">ปิด</button><button id="clipSetupSave" type="button">บันทึกข้อมูล</button><button class="btn-primary" type="submit">เตรียมคลิปต่อ</button></div></form>`;
      document.body.appendChild(dialog);
      const field = id => dialog.querySelector('#clipSetup' + id);
      field('Caption').value = initial.caption; field('Tags').value = initial.hashtags;
      field('Date').value = initial.date; field('Time').value = initial.time;
      field('Intent').value = initial.intent;
      if (saved) field('SaveStatus').textContent = 'โหลดข้อมูลที่บันทึกไว้ใน extension แล้ว';
      const values = () => ({caption: field('Caption').value, hashtags: field('Tags').value, intent: field('Intent').value, date: field('Date').value, time: field('Time').value});
      function sync() { field('Slot').hidden = field('Intent').value !== 'schedule'; }
      let sequence = 0;
      async function saveEdits() {
        const current = ++sequence;
        field('SaveStatus').textContent = 'กำลังบันทึกข้อมูล';
        try {
          await store.save(values());
          if (current === sequence) field('SaveStatus').textContent = 'บันทึกข้อมูลแล้วใน extension เปิดกลับมาแก้ต่อได้';
          return true;
        } catch (err) {
          if (current === sequence) field('SaveStatus').textContent = `บันทึกไม่สำเร็จ: ${err.message}`;
          return false;
        }
      }
      function clearErrors() {
        field('Error').textContent = '';
        for (const id of ['Caption', 'Tags', 'Date', 'Time']) field(id).removeAttribute('aria-invalid');
      }
      field('Form').addEventListener('input', () => { clearErrors(); saveEdits(); });
      field('Form').addEventListener('change', () => { sync(); clearErrors(); saveEdits(); });
      field('Save').onclick = saveEdits;
      let finished = false, submitting = false;
      async function finish(value) { if (finished) return; finished = true; await saveEdits(); dialog.close(); dialog.remove(); resolve(value); }
      field('Cancel').onclick = () => finish(null);
      dialog.addEventListener('cancel', event => { event.preventDefault(); finish(null); });
      field('Form').addEventListener('submit', async event => {
        event.preventDefault();
        if (submitting || finished) return;
        submitting = true;
        try {
        clearErrors();
        const submitted = values();
        const result = validate(item, submitted, guard, record, Date.now(), exportsKnown, reasons);
        if (!await saveEdits() || finished) return;
        if (JSON.stringify(submitted) !== JSON.stringify(values())) {field('Error').textContent = 'ข้อมูลเปลี่ยนระหว่างบันทึก กรุณากดเตรียมคลิปต่ออีกครั้ง'; return;}
        if (result.issues.length) {
          field('Error').textContent = result.issues.map(issue => issue.message).join(' · ');
          for (const issue of result.issues) field(issue.field).setAttribute('aria-invalid', 'true');
          field(result.issues[0].field).focus();
          return;
        }
        await finish(result.item);
        } finally { submitting = false; }
      });
      sync(); dialog.showModal(); field('Caption').focus();
    });
  }
  return {build, validate, fillProductName, createStore, open};
});
