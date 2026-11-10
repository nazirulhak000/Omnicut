#!/usr/bin/env node
'use strict';
// End-to-end test of the REAL side panel (the extension's own UI + service worker) in a
// real Chrome: loads the unpacked extension over CDP, opens sidepanel.html, presses the
// real batch button and watches the log. By default the final "post" click is stubbed
// (the post click itself is proven by the conductor), so nothing is published.
//
//   node tools/autopost_conductor/extension_e2e.js            # stubbed post (safe)
//   node tools/autopost_conductor/extension_e2e.js --real-post  # REALLY posts that clip
const fs = require('node:fs');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { createApi, readApiKey, ROOT } = require('./api');
const { pickClips } = require('./conductor');

const PORT = Number(process.env.OMNICUT_PORT || 9333);
const CHROME_EXE = process.env.OMNICUT_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PROFILE_DIR = path.join(ROOT, 'tools', 'tiktok_browser_profile');
const EXT_DIR = path.join(ROOT, 'tiktok_autopost_extension');
const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const portUp = async () => { try { return (await fetch(`http://127.0.0.1:${PORT}/json/version`)).ok; } catch (_) { return false; } };

function killConductorChrome() {
  spawnSync('powershell', ['-NoProfile', '-Command',
    `Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -like '*tiktok_browser_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`]);
}

async function launchChrome() {
  const child = spawn(CHROME_EXE, [
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE_DIR}`,
    '--enable-unsafe-extension-debugging', '--no-first-run', '--no-default-browser-check',
    '--lang=th-TH', '--window-size=1440,960',
    '--disable-session-crashed-bubble', '--hide-crash-restore-bubble', '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
    UPLOAD_URL,
  ], { detached: true, stdio: 'ignore' });
  child.unref();
  for (let i = 0; i < 40; i += 1) { if (await portUp()) return; await sleep(500); }
  throw new Error('Chrome ไม่เปิดพอร์ต debug');
}

class Cdp {
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); }
  async open() {
    this.ws = new WebSocket(this.url);
    await new Promise((res, rej) => { this.ws.addEventListener('open', res); this.ws.addEventListener('error', () => rej(new Error('ws error'))); });
    this.ws.addEventListener('message', e => {
      const m = JSON.parse(e.data);
      const w = m.id && this.pending.get(m.id);
      if (w) { this.pending.delete(m.id); m.error ? w.rej(new Error(m.error.message)) : w.res(m.result || {}); }
    });
    return this;
  }
  call(method, params = {}, timeout = 60000) {
    return new Promise((res, rej) => {
      const id = ++this.id;
      const t = setTimeout(() => { this.pending.delete(id); rej(new Error(`cdp_timeout ${method}`)); }, timeout);
      this.pending.set(id, { res: v => { clearTimeout(t); res(v); }, rej: e => { clearTimeout(t); rej(e); } });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async eval(expression, awaitPromise = true, timeout = 60000) {
    const r = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise }, timeout);
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result?.value;
  }
  close() { try { this.ws.close(); } catch (_) {} }
}

async function browser() {
  const v = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
  return new Cdp(v.webSocketDebuggerUrl).open();
}

// Chrome keeps the extension's service-worker script in the profile cache keyed by extension id +
// manifest version, so loading the SAME path again can silently run OLD worker code (seen: new
// functions missing from the live worker). Load a fresh copy from a new path => new id => no cache.
function freshExtensionCopy() {
  const root = path.join(ROOT, '.tmp', 'e2e_ext');
  fs.mkdirSync(root, { recursive: true });
  for (const old of fs.readdirSync(root)) fs.rmSync(path.join(root, old), { recursive: true, force: true });
  const dest = path.join(root, `run_${Date.now()}`);
  fs.cpSync(EXT_DIR, dest, { recursive: true });
  return dest;
}

async function loadExtension() {
  const extPath = freshExtensionCopy();
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const b = await browser();
    try {
      const { id } = await b.call('Extensions.loadUnpacked', { path: extPath });
      b.close();
      return id;
    } catch (error) {
      b.close();
      if (attempt) throw new Error(`โหลด extension ไม่ได้: ${error.message}`);
      console.log(`[info] loadUnpacked ไม่สำเร็จ (${error.message}) — เปิด Chrome ใหม่พร้อมแฟล็ก extension debugging`);
      killConductorChrome();
      await sleep(2500);
      await launchChrome();
      await sleep(3000);
    }
  }
}

async function pageTarget(urlPrefix) {
  for (let i = 0; i < 30; i += 1) {
    const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
    const t = list.find(x => x.type === 'page' && x.url.startsWith(urlPrefix));
    if (t) return t;
    await sleep(500);
  }
  throw new Error(`ไม่พบแท็บ ${urlPrefix}`);
}

async function main() {
  const realPost = process.argv.includes('--real-post');
  const verifyProbe = process.argv.includes('--verify-probe');
  const leaveProbe = process.argv.includes('--leave-probe');
  // --pick=N: tick N clips with the panel's own checkboxes (instead of search + count limit); only those may run.
  const pick = Number((process.argv.find(a => a.startsWith('--pick=')) || '').split('=')[1]) || 0;
  const clipCount = pick || Number((process.argv.find(a => a.startsWith('--clips=')) || '').split('=')[1]) || 1;
  const apiKey = readApiKey();
  const api = createApi({ apiKey, channelId: 'main' });
  const outDir = path.join(ROOT, '.tmp', 'extension_e2e', new Date().toISOString().replace(/[:.]/g, '-'));
  fs.mkdirSync(outDir, { recursive: true });
  const report = { steps: [], ok: false };
  const step = (name, detail = '') => { console.log(`[step] ${name} ${detail}`); report.steps.push({ name, detail }); };

  // 1) pick ONE eligible clip so the panel's search filter leaves exactly one
  const { clips } = await pickClips(api, { limit: clipCount });
  if (!verifyProbe && !process.argv.includes('--draft-probe') && !process.argv.includes('--quota-probe') && !process.argv.includes('--smart-overflow') && !clips.length) throw new Error('ไม่มีคลิปพร้อมโพสต์ในคิว (ตรวจเวลา/export)');
  const clip = clips[0] || { title: '' };
  step('clips eligible', `${clips.length} (asked ${clipCount})`);

  // 2) Chrome + extension
  // Always start from a fresh Chrome: loadUnpacked into a browser that already loaded this extension
  // keeps the OLD background.js, which would silently test stale code.
  if (!process.argv.includes('--keep-chrome')) {
    killConductorChrome();
    await sleep(2500);
  }
  if (!(await portUp())) await launchChrome();
  const extId = await loadExtension();
  step('extension loaded', extId);
  await sleep(1500);

  // 3) TikTok tab must be on the upload page
  const tiktok = await pageTarget('https://www.tiktok.com/tiktokstudio');
  const tt = await new Cdp(tiktok.webSocketDebuggerUrl).open();
  if (!/\/tiktokstudio\/upload/.test(tiktok.url)) await tt.call('Page.navigate', { url: UPLOAD_URL });
  await sleep(4000);

  // 4) the side panel, in its own window so the upload tab stays visible
  const b = await browser();
  await b.call('Target.createTarget', { url: `chrome-extension://${extId}/sidepanel.html`, newWindow: true, width: 520, height: 900 });
  b.close();
  const panelTarget = await pageTarget(`chrome-extension://${extId}/sidepanel.html`);
  const panel = await new Cdp(panelTarget.webSocketDebuggerUrl).open();
  await panel.call('Runtime.enable');
  await panel.eval(`new Promise(r => chrome.storage.local.set({omnicutApiKey: ${JSON.stringify(apiKey)}}, r))`);
  await panel.call('Page.reload');
  await sleep(4000);
  step('panel open');

  try {
    if (leaveProbe) {
      // Chrome's own "Leave site?" prompt: give the page a real beforeunload handler plus user
      // activation (as the automation's clicks do), then reset through the real worker action.
      await tt.eval(`window.__marker = 'alive'; window.addEventListener('beforeunload', e => { e.preventDefault(); e.returnValue = 'x'; }); true`, false);
      for (const type of ['mousePressed', 'mouseReleased']) await tt.call('Input.dispatchMouseEvent', { type, x: 300, y: 300, button: 'left', clickCount: 1 });
      if (process.argv.includes('--manual')) {
        // Same steps as the worker, one at a time, from an extension page: where does it go wrong?
        const src = fs.readFileSync(path.join(EXT_DIR, 'background.js'), 'utf8');
        const neutralizer = /const NEUTRALIZE_LEAVE_PROMPT = `([\s\S]*?)`;/.exec(src)[1];
        const steps = await panel.eval(`(async () => {
          const out = {};
          const [tab] = await chrome.tabs.query({url: '*://www.tiktok.com/*'});
          out.tabId = tab.id;
          try { await chrome.debugger.attach({tabId: tab.id}, '1.3'); out.attach = 'ok'; } catch (e) { out.attach = String(e.message || e); }
          try { out.evaluate = JSON.stringify(await chrome.debugger.sendCommand({tabId: tab.id}, 'Runtime.evaluate', {expression: ${JSON.stringify(neutralizer)}, returnByValue: true})); } catch (e) { out.evaluate = 'ERR ' + String(e.message || e); }
          try { await chrome.debugger.detach({tabId: tab.id}); out.detach = 'ok'; } catch (e) { out.detach = String(e.message || e); }
          try { await chrome.tabs.update(tab.id, {url: 'https://www.tiktok.com/tiktokstudio/upload?manual=' + Date.now()}); out.update = 'ok'; } catch (e) { out.update = 'ERR ' + String(e.message || e); }
          return out; })()`, true, 30000).catch(e => ({ error: e.message }));
        console.log('[leave] manual steps', JSON.stringify(steps));
        await sleep(6000);
        const tabs0 = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
        const page0 = tabs0.find(x => x.type === 'page' && /tiktok\.com/.test(x.url));
        const alive0 = await new Cdp(page0.webSocketDebuggerUrl).open().then(c => c.eval('typeof window.__marker', false, 3000).finally(() => c.close())).catch(() => 'HUNG');
        console.log(`[leave] manual result url=${page0.url.slice(0, 70)} marker=${alive0}`);
        report.ok = alive0 === 'undefined';
        console.log(report.ok ? '[E2E PASS] manual leave' : '[E2E FAIL] manual leave');
        process.exitCode = report.ok ? 0 : 1;
        return;
      }
      const t = Date.now();
      const pending = panel.eval(`new Promise(r => chrome.runtime.sendMessage({action: 'reset-upload-page'}, r))`, true, 90000).catch(e => ({ error: e.message }));
      // watch what the page does while the worker works (is it navigating, is it hung?)
      let settled = false;
      pending.then(() => { settled = true; });
      for (let i = 0; i < 12 && !settled; i += 1) {
        await sleep(3000);
        const tabs = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
        const page = tabs.find(x => x.type === 'page' && /tiktok\.com/.test(x.url));
        const alive = await new Cdp(page.webSocketDebuggerUrl).open().then(c => c.eval('typeof window.__marker + "|" + document.readyState', false, 2500).finally(() => c.close())).catch(() => 'HUNG');
        console.log(`[leave] +${(i + 1) * 3}s url=${page.url.slice(0, 60)} state=${alive}`);
      }
      const reply = await pending;
      const seconds = Math.round((Date.now() - t) / 1000);
      const marker = await tt.eval('typeof window.__marker', false, 15000).catch(() => 'UNRESPONSIVE');
      const ok = Boolean(reply?.success) && seconds < 45 && marker === 'undefined';
      console.log(`[leave] reply=${JSON.stringify(reply)} ${seconds}s page-marker=${marker}`);
      report.ok = ok;
      console.log(ok ? '[E2E PASS] leave probe: รีเซ็ตหน้าที่มี beforeunload ได้เองไม่ค้าง' : '[E2E FAIL] leave probe: หน้ายังค้าง/ไม่ได้นำทาง');
      process.exitCode = ok ? 0 : 1;
      return;
    }
    if (process.argv.includes('--smart-overflow')) {
      // Smart Queue at 29/30 scheduled: clip 1 takes the last schedule slot (the post click is stubbed: nothing is
      // published), clip 2 must switch to a REAL draft. Only the quota number is simulated; every other step is real.
      // --full: the schedule quota is 30/30 (clip 1 must already be a draft); one clip only, so the draft is queue-bound.
      const full = process.argv.includes('--full');
      let n = 0;
      for (let i = 0; i < 40 && n < 1; i += 1) { n = await panel.eval(`typeof allClips === 'undefined' ? -1 : allClips.length`, false).catch(() => -1); if (n < 1) await sleep(1500); }
      await panel.eval(`(() => {
        const set = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('change', {bubbles: true})); };
        set('batchModeSelect', 'smart');
        const cf = document.getElementById('coverFallbackToggle'); if (cf && cf.checked) cf.click();
        return true;
      })()`, false);
      const first = clips[0]?.title;
      const picked = await panel.eval(`(() => {
        const cards = [...document.querySelectorAll('#list .card')].filter(c => !c.classList.contains('blocked'));
        const hook = c => (c.querySelector('.card-hook')?.innerText || '').trim();
        const one = cards.find(c => hook(c) === ${JSON.stringify(first)});
        const wanted = ${JSON.stringify((process.argv.find(a => a.startsWith('--second=')) || '').slice('--second='.length))};
        const two = cards.find(c => c !== one && (!wanted || hook(c).includes(wanted)));
        if (!one || (!two && !${JSON.stringify(full)})) return {ok: false, cards: cards.length, matching: [...document.querySelectorAll('#list .card')].filter(c => wanted && hook(c).includes(wanted)).map(c => ({blocked: c.classList.contains('blocked'), note: c.querySelector('.card-blocked-note')?.innerText || '', hook: hook(c).slice(0, 50)}))};
        for (const c of [one, ...(${JSON.stringify(full)} ? [] : [two])]) { const box = c.querySelector('.card-check input'); if (box && !box.checked) box.click(); }
        return {ok: true, one: hook(one), two: two ? hook(two) : null};
      })()`, false);
      step('ticked 2 clips', JSON.stringify(picked));
      if (!picked.ok) throw new Error('ต้องมีคลิปที่ใช้ได้อย่างน้อย 2 คลิปในแผง');
      await panel.eval(`(() => {
        window.checkTikTokQuota = async () => { currentQuotaState = {scheduledCount: ${full ? 30 : 29}, scheduledAt: Date.now(), draftCount: 0, remainingSchedule: ${full ? 0 : 1}, remainingDraft: 30, maxSchedule: 30, maxDraft: 30}; updateQuotaUI(); };
        const original = chrome.runtime.sendMessage.bind(chrome.runtime);
        chrome.runtime.sendMessage = (message, cb) => {
          if (message && message.action === 'click-post-only') { setTimeout(() => cb && cb({ success: true, clicked: false, outcome: 'scheduled_on_platform', stubbed: true }), 300); return; }
          if (message && message.action === 'verify-post-content') { setTimeout(() => cb && cb({ success: true, verified: true, stubbed: true }), 300); return; }
          return original(message, cb);
        };
        return true;
      })()`, false);
      step('quota simulated 29/30; post click + post verify stubbed; save-draft-only is REAL');
      await panel.eval(`document.getElementById('batchStartBtn').click()`, false);
      await sleep(800);
      await panel.eval(`document.getElementById('confirmOkBtn').click()`, false);
      let log = '';
      for (let i = 0; i < 120; i += 1) {
        await sleep(4000);
        log = await panel.eval(`document.getElementById('batchLogBox')?.innerText || ''`, false).catch(() => '');
        if (/อัปโหลดครบชุด|สรุปผลลัพธ์|หยุดอัตโนมัติ|หยุดการทำงาน/.test(log)) break;
      }
      fs.writeFileSync(path.join(outDir, 'panel_log.txt'), log);
      console.log(log.split('\n').filter(l => /โหมด:|สำเร็จ|ล้มเหลว|หยุด|แบบร่าง|draft/i.test(l)).slice(-12).join('\n'));
      const modes = [...log.matchAll(/โหมด: (ตั้งเวลา|แบบร่าง)/g)].map(m => m[1]);
      report.modes = modes;
      report.ok = modes.join(',') === (full ? 'แบบร่าง' : 'ตั้งเวลา,แบบร่าง') && (log.match(/✅ \[/g) || []).length === (full ? 1 : 2);
      process.exitCode = report.ok ? 0 : 1;
      console.log(report.ok ? '[E2E PASS] smart overflow: schedule then draft' : '[E2E FAIL] smart overflow');
      return;
    }
    if (process.argv.includes('--draft-probe')) {
      // Second proof for drafts: the Drafts list must hold a row for this caption (true) and not for another (false).
      const q = await api.get('/api/schedule-queue');
      const drafted = (q.data.items || []).filter(i => i.status === 'draft_on_platform');
      let allGood = drafted.length > 0;
      for (const [label, caption, expect] of [...drafted.map(i => ['real draft', i.caption, true]), ['unknown caption', 'ข้อความที่ไม่เคยถูกบันทึกเป็นแบบร่างเลย', false]]) {
        const t0 = Date.now();
        const verdict = await panel.eval(`new Promise(r => chrome.runtime.sendMessage(${JSON.stringify({ action: 'verify-draft-content', caption })}, r))`, true, 5 * 60 * 1000);
        const good = Boolean(verdict?.verified) === expect;
        allGood = allGood && good;
        console.log(`[draft-verify] ${good ? 'OK ' : 'BAD'} ${label} expect=${expect} reply=${JSON.stringify(verdict)} (${Math.round((Date.now() - t0) / 1000)}s)`);
      }
      const quota = await panel.eval(`new Promise(r => chrome.runtime.sendMessage({action: 'detect-tiktok-quota', allowNavigate: true}, r))`, true, 5 * 60 * 1000);
      console.log('[draft-quota]', JSON.stringify({ scheduled: quota?.scheduledCount, draft: quota?.draftCount, remainingDraft: quota?.remainingDraft, source: quota?.source }));
      report.ok = allGood && quota?.draftCount === drafted.length;
      process.exitCode = report.ok ? 0 : 1;
      console.log(report.ok ? '[E2E PASS] draft probe' : '[E2E FAIL] draft probe');
      return;
    }
    if (process.argv.includes('--quota-probe')) {
      // The panel's own "check quota" button + the worker action: counts the future-dated rows of Studio > Content.
      const t0 = Date.now();
      const direct = await panel.eval(`new Promise(r => chrome.runtime.sendMessage({action: 'detect-tiktok-quota', allowNavigate: true}, r))`, true, 5 * 60 * 1000);
      step('worker detect-tiktok-quota', `${Math.round((Date.now() - t0) / 1000)}s ${JSON.stringify({ ok: direct?.success, scheduled: direct?.scheduledCount, draft: direct?.draftCount, remaining: direct?.remainingSchedule, source: direct?.source, err: direct?.countError })}`);
      await panel.eval(`document.getElementById('btnCheckQuota').click()`, false);
      let ui = {};
      for (let i = 0; i < 60; i += 1) {
        await sleep(3000);
        ui = await panel.eval(`({value: document.getElementById('quotaScheduleValue')?.innerText, remain: document.getElementById('quotaScheduleRemain')?.innerText, info: document.getElementById('batchLimitInfo')?.innerText, loading: document.getElementById('btnCheckQuota')?.classList.contains('loading')})`, false);
        if (!ui.loading && ui.value && !/--/.test(ui.value)) break;
      }
      step('panel quota UI', JSON.stringify(ui));
      report.quota = { direct: { scheduled: direct?.scheduledCount, remaining: direct?.remainingSchedule, source: direct?.source }, ui };
      report.ok = typeof direct?.scheduledCount === 'number' && Boolean(ui.value) && !/--/.test(ui.value);
      process.exitCode = report.ok ? 0 : 1;
      console.log(report.ok ? '[E2E PASS] quota probe' : '[E2E FAIL] quota probe');
      return;
    }
    if (process.argv.includes('--dropdown-probe')) {
      // No posting: only read what the panel WOULD do for each dropdown value (button label + info line).
      let count = 0;
      for (let i = 0; i < 40 && count < 1; i += 1) { count = await panel.eval(`typeof allClips === 'undefined' ? -1 : allClips.length`, false).catch(() => -1); if (count < 1) await sleep(1500); }
      await panel.eval(`checkTikTokQuota(false, true)`, true, 5 * 60 * 1000); // the quota button: counts the Content list
      const afterButton = await panel.eval(`({s: currentQuotaState.scheduledCount, r: currentQuotaState.remainingSchedule})`, false);
      await panel.eval(`checkTikTokQuota(true, false)`, true); // a silent refresh must NOT forget that count
      const afterSilent = await panel.eval(`({s: currentQuotaState.scheduledCount, r: currentQuotaState.remainingSchedule})`, false);
      console.log('[quota] after button', JSON.stringify(afterButton), 'after silent refresh', JSON.stringify(afterSilent));
      report.quota_kept = JSON.stringify(afterButton) === JSON.stringify(afterSilent);
      const rows = [];
      for (const mode of ['schedule_only', 'smart']) {
        for (const limit of ['auto_quota', '30', '20', '10', '5', 'all']) {
          const r = await panel.eval(`(() => {
            const set = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('change', {bubbles: true})); };
            set('batchModeSelect', ${JSON.stringify(mode)}); set('batchLimitSelect', ${JSON.stringify(limit)});
            return {mode: ${JSON.stringify(mode)}, limit: ${JSON.stringify(limit)}, button: document.getElementById('batchStartBtn').innerText.replace(/\s+/g, ' ').trim(), info: document.getElementById('batchLimitInfo').innerText, modeOptions: [...document.getElementById('batchModeSelect').options].map(o => o.value).join(',')};
          })()`, false);
          rows.push(r);
          console.log(`[dropdown] ${r.mode.padEnd(13)} ${String(r.limit).padEnd(10)} -> ${r.button} | ${r.info}`);
        }
      }
      report.dropdowns = rows;
      report.ok = rows.length === 12;
      process.exitCode = 0;
      console.log('[E2E PASS] dropdown probe');
      return;
    }
    if (verifyProbe) {
      // Real Content-page verification against clips that were really scheduled (must be true),
      // and against one that was never posted (must be false).
      const q = await api.get('/api/schedule-queue');
      const items = q.data.items || [];
      const cases = [
        ...items.filter(i => i.status === 'scheduled_on_platform').map(i => ({ i, expect: true })),
        ...items.filter(i => i.status === 'planned').slice(0, 1).map(i => ({ i, expect: false })),
      ];
      let allGood = cases.length > 0;
      for (const { i, expect } of cases) {
        const at = String(i.scheduled_at || '');
        const message = { action: 'verify-post-content', caption: i.caption || i.hook_title || '', scheduleDate: at.slice(0, 10), scheduleTime: (/T(\d{2}:\d{2})/.exec(at) || [])[1] || '' };
        const t = Date.now();
        const verdict = await panel.eval(`new Promise(r => chrome.runtime.sendMessage(${JSON.stringify(message)}, r))`, true, 6 * 60 * 1000);
        const good = Boolean(verdict?.verified) === expect;
        allGood = allGood && good;
        console.log(`[verify] ${good ? 'OK ' : 'BAD'} expect=${expect} reply=${JSON.stringify(verdict)} (${Math.round((Date.now() - t) / 1000)}s) @ ${at}`);
        step('verify probe', `${good ? 'ok' : 'BAD'} ${at}`);
      }
      report.ok = allGood;
      console.log(allGood ? '[E2E PASS] verify probe: ตรวจหน้า Content ถูกทั้งคลิปที่โพสต์แล้วและคลิปที่ยังไม่โพสต์' : '[E2E FAIL] verify probe');
      process.exitCode = allGood ? 0 : 1;
      return;
    }
    // 5) wait for the clip list, filter to the one clip, choose options
    let count = 0;
    for (let i = 0; i < 40 && count < 1; i += 1) {
      count = await panel.eval(`typeof allClips === 'undefined' ? -1 : allClips.length`, false).catch(() => -1);
      if (count < 1) await sleep(1500);
    }
    if (count < 1) throw new Error('แผงข้างโหลดรายการคลิปไม่ได้ (ตรวจ API key/Backend)');
    step('panel clips loaded', String(count));
    // --narrow=W: lay the TikTok tab out only W CSS px wide (docked side panel / OS scaling): the extension must cope
    const narrow = Number((process.argv.find(a => a.startsWith('--narrow=')) || '').split('=')[1]) || 0;
    if (narrow) { await tt.call('Emulation.setDeviceMetricsOverride', { width: narrow, height: 800, deviceScaleFactor: 0, mobile: false }); step('tiktok viewport narrowed', String(narrow)); }
    const title = clip.title.slice(0, 40);
    await panel.eval(`(() => {
      const set = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); };
      ${clipCount === 1 && !pick ? `set('clipSearchInput', ${JSON.stringify(title)});` : ''}
      set('batchModeSelect', ${JSON.stringify(process.argv.includes('--draft') ? 'draft_only' : 'schedule_only')});
      ${pick ? '' : `set('batchLimitSelect', ${JSON.stringify(['5', '10', '20', '30'].includes(String(clipCount)) ? String(clipCount) : 'all')});`}
      const cf = document.getElementById('coverFallbackToggle'); if (cf && !cf.checked) cf.click();
      return true;
    })()`, false);
    if (pick) {
      const titles = clips.slice(0, pick).map(c => c.title);
      const ticked = await panel.eval(`(() => {
        const wanted = ${JSON.stringify(titles)};
        let n = 0;
        for (const card of document.querySelectorAll('#list .card')) {
          const hook = (card.querySelector('.card-hook')?.innerText || '').trim();
          if (wanted.includes(hook)) { const box = card.querySelector('.card-check input'); if (box && !box.checked) { box.click(); n += 1; } }
        }
        return n;
      })()`, false);
      step('ticked via checkbox', `${ticked}/${pick}`);
      const ui = await panel.eval(`({info: document.getElementById('selectedInfo')?.innerText, capped: document.getElementById('batchCappedCount')?.innerText, limitDisabled: document.getElementById('batchLimitSelect')?.disabled, selected: document.querySelectorAll('#list .card.selected').length, blocked: document.querySelectorAll('#list .card.blocked').length, blockedBoxesDisabled: [...document.querySelectorAll('#list .card.blocked .card-check input')].every(b => b.disabled), note: document.querySelector('#list .card.blocked .card-blocked-note')?.innerText || ''})`, false);
      step('selection UI', JSON.stringify(ui));
      report.selection_ui = ui;
      if (ticked !== pick || String(ui.capped) !== String(pick) || !ui.limitDisabled || (ui.blocked > 0 && !ui.blockedBoxesDisabled)) throw new Error(`ติ๊กเลือกไม่ตรง: ${JSON.stringify({ ticked, ui })}`);
    }
    await sleep(800);
    const filtered = await panel.eval(`document.getElementById('batchCountBadge')?.innerText || ''`, false);
    step('filtered', filtered);

    if (!realPost) {
      // Stub ONLY the final post click; every other worker message is the real thing.
      await panel.eval(`(() => {
        const original = chrome.runtime.sendMessage.bind(chrome.runtime);
        chrome.runtime.sendMessage = (message, cb) => {
          if (message && message.action === 'click-post-only') {
            // --content-after-post: like a real post, TikTok sends the tab on to Studio > Content
            const leave = ${JSON.stringify(process.argv.includes('--content-after-post'))}
              ? chrome.tabs.query({ url: '*://www.tiktok.com/tiktokstudio/*' }).then(tabs => tabs[0] && chrome.tabs.update(tabs[0].id, { url: 'https://www.tiktok.com/tiktokstudio/content' })).then(() => new Promise(r => setTimeout(r, 4000)))
              : Promise.resolve();
            leave.catch(() => {}).then(() => setTimeout(() => cb && cb({ success: true, clicked: false, outcome: 'scheduled_on_platform', stubbed: true }), 300));
            return;
          }
          // nothing was really posted, so the Content-page check would (rightly) fail: stub it too
          if (message && message.action === 'verify-post-content') {
            setTimeout(() => cb && cb({ success: true, verified: true, stubbed: true }), 300);
            return;
          }
          return original(message, cb);
        };
        window.__e2eStubbed = true;
      })()`, false);
      step('post click + content verify stubbed');
    }

    // 6) press the REAL start button and confirm
    await panel.eval(`document.getElementById('batchStartBtn').click()`, false);
    await sleep(800);
    await panel.eval(`document.getElementById('confirmOkBtn').click()`, false);
    step('batch started');

    // optional fault: Chrome stops the MV3 service worker in the middle of the batch
    const killAt = Number((process.argv.find(a => a.startsWith('--kill-worker-at=')) || '').split('=')[1]) || 0;
    if (killAt) {
      setTimeout(async () => {
        try {
          const sw = await new Cdp((await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()).webSocketDebuggerUrl).open();
          const { targetInfos } = await sw.call('Target.getTargets');
          const workers = targetInfos.filter(t => t.type === 'service_worker' && t.url.startsWith(`chrome-extension://${extId}/`));
          console.log(`[fault] stopping ${workers.length} extension service worker(s) at t=${killAt}s`);
          await panel.call('ServiceWorker.enable').catch(() => {});
          await panel.call('ServiceWorker.stopAllWorkers').catch(e => console.log('[fault] stopAllWorkers:', e.message));
          for (const w of workers) await sw.call('Target.closeTarget', { targetId: w.targetId }).catch(() => {});
          sw.close();
        } catch (e) { console.log('[fault] failed:', e.message); }
      }, killAt * 1000);
    }

    // 7) wait for the panel's own log to finish
    const t0 = Date.now();
    let log = '';
    let printed = 0;
    while (Date.now() - t0 < Math.max(15, clipCount * 6) * 60 * 1000) {
      await sleep(5000);
      log = await panel.eval(`document.getElementById('batchLogBox')?.innerText || ''`, false).catch(() => '');
      // live progress: print each new panel log entry as it appears
      const entries = log.split(/(?=\[\d\d:\d\d:\d\d\])/).map(x => x.trim()).filter(Boolean);
      for (; printed < entries.length; printed += 1) console.log(`[panel] ${entries[printed].slice(0, 200)}`);
      if (/อัปโหลดครบชุด|สรุปผลลัพธ์|ระบบลูปหยุดทำงาน|หยุดลูป/.test(log)) break;
    }
    fs.writeFileSync(path.join(outDir, 'panel_log.txt'), log);
    await tt.call('Page.captureScreenshot', { format: 'png' }).then(r => fs.writeFileSync(path.join(outDir, 'upload_tab.png'), Buffer.from(r.data, 'base64'))).catch(() => {});
    const shot = await panel.call('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'panel.png'), Buffer.from(shot.data, 'base64'));
    console.log('---- panel log ----\n' + log.split('\n').slice(-14).join('\n'));
    const doneCount = (log.match(/✅ \[/g) || []).length;
    report.done = doneCount;
    report.ok = doneCount === Math.min(clipCount, clips.length) && !/ล้มเหลวที่ขั้น|หยุดอัตโนมัติ/.test(log);
    report.log_tail = log.split('\n').slice(-14);
  } finally {
    // 8) leave nothing claimed behind
    await panel.eval(`new Promise(r => chrome.runtime.sendMessage({action: 'release-posting-job', park: true}, r))`).catch(() => {});
    panel.close();
    tt.close();
    fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
  }
  console.log(report.ok ? '[E2E PASS] แผงข้างทำงานครบทั้งสาย' : '[E2E FAIL] ดู panel_log.txt');
  console.log(`evidence: ${outDir}`);
  process.exitCode = report.ok ? 0 : 1;
}

main().catch(error => { console.error('[E2E ERROR]', error.message); process.exitCode = 2; })
  .finally(() => setTimeout(() => process.exit(process.exitCode || 0), 300));
