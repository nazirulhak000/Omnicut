// Persistent run history. The panel's log box is wiped when the panel closes; the history keeps the last runs
// (every line, the job id it belongs to, and a redacted snapshot of the page when a clip failed or was unconfirmed) in
// chrome.storage.local so a failure can still be diagnosed the next morning.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniRunHistory = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const KEY = 'omnicutRunHistory';

  // Evidence must not leak personal data: handles, e-mails, long digit runs (phones, ids) and URL query strings.
  function redact(text) {
    return String(text == null ? '' : text)
      .replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '[email]')
      .replace(/@[A-Za-z0-9._]{2,}/g, '@[handle]')
      .replace(/\?[^\s"'<>]*/g, '?[query]')
      .replace(/\d[\d\s().-]{6,}\d/g, '[number]');
  }

  function createRunRecorder({ storage, now = Date.now, maxRuns = 10, maxLines = 600, maxEvidence = 20, flushEvery = 12 } = {}) {
    let runs = [];
    let current = null;
    let sinceFlush = 0;
    let loaded = false;

    async function load() {
      if (loaded) return runs;
      try { runs = (await storage.get(KEY))[KEY] || []; } catch (_) { runs = []; }
      loaded = true;
      return runs;
    }
    async function flush() {
      sinceFlush = 0;
      const all = current ? [current, ...runs.filter((r) => r.id !== current.id)] : runs;
      try { await storage.set({ [KEY]: all.slice(0, maxRuns) }); } catch (_) { /* storage full / unavailable: history is best effort */ }
    }

    async function start(meta = {}) {
      await load();
      current = { id: `run-${now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`, startedAt: new Date(now()).toISOString(), meta, lines: [], jobs: [], evidence: [], summary: null };
      await flush();
      return current;
    }
    function log(kind, message) {
      if (!current) return;
      const job = current.jobs.length ? current.jobs[current.jobs.length - 1].jobId : null;
      current.lines.push({ t: new Date(now()).toISOString(), kind, message: String(message), ...(job ? { job } : {}) });
      if (current.lines.length > maxLines) current.lines.splice(20, current.lines.length - maxLines);   // keep the beginning and the newest
      sinceFlush += 1;
      if (sinceFlush >= flushEvery) flush();
    }
    function setJob(jobId, title = '') {
      if (!current || !jobId) return;
      current.jobs.push({ jobId, title, at: new Date(now()).toISOString() });
    }
    async function addEvidence(entry) {
      if (!current) return;
      const job = current.jobs.length ? current.jobs[current.jobs.length - 1].jobId : null;
      current.evidence.push({
        at: new Date(now()).toISOString(), job,
        kind: entry.kind || '', stage: entry.stage || '', error: redact(entry.error || ''),
        url: redact(entry.url || ''), title: redact(entry.title || ''), text: redact(String(entry.text || '').slice(0, 1800)),
      });
      if (current.evidence.length > maxEvidence) current.evidence.shift();
      await flush();
    }
    async function finish(summary = {}) {
      if (!current) return;
      current.summary = summary;
      current.finishedAt = new Date(now()).toISOString();
      await flush();
      runs = [current, ...runs.filter((r) => r.id !== current.id)].slice(0, maxRuns);
      current = null;
    }
    async function list() { await load(); return current ? [current, ...runs.filter((r) => r.id !== current.id)] : runs; }

    async function exportText(index = 0) {
      const run = (await list())[index];
      if (!run) return '';
      const head = [
        `รอบ ${run.id} เริ่ม ${run.startedAt}${run.finishedAt ? ` จบ ${run.finishedAt}` : ' (ยังไม่จบ/ถูกตัดกลางคัน)'}`,
        `ตั้งค่า: ${JSON.stringify(run.meta || {})}`,
        run.summary ? `สรุป: ${JSON.stringify(run.summary)}` : 'สรุป: -',
        `งาน: ${run.jobs.map((j) => `${j.jobId}${j.title ? ` (${j.title})` : ''}`).join(', ') || '-'}`,
        '--- log ---',
      ];
      const lines = run.lines.map((l) => `${l.t} [${l.kind}]${l.job ? ` {${l.job}}` : ''} ${l.message}`);
      const evidence = run.evidence.length ? ['--- หลักฐานตอนล้ม/ไม่แน่ใจ (ตัดข้อมูลส่วนตัวแล้ว) ---', ...run.evidence.map((e) => `${e.at} {${e.job || '-'}} ${e.kind}/${e.stage}: ${e.error}\n  ${e.url} | ${e.title}\n  ${e.text}`)] : [];
      return [...head, ...lines, ...evidence].join('\n');
    }

    return { start, log, setJob, addEvidence, finish, list, exportText, flush, load, get current() { return current; } };
  }

  return { KEY, redact, createRunRecorder };
});
