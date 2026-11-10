#!/usr/bin/env node
'use strict';
// Unattended TikTok auto-post runner.
//   node tools/autopost_conductor/run.js --channel main --limit 5 --dry-run
//   node tools/autopost_conductor/run.js --health
// Exit codes: 0 ok · 1 some clips failed · 2 aborted (needs a human) · 3 login/browser problem
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { createChromeShim } = require('./chrome_shim');
const { loadWorker } = require('./host');
const { createApi, readApiKey, ROOT } = require('./api');
const { pickClips, runBatch, rowMatchesClip } = require('./conductor');
const { acquireProcessLock } = require('./process_lock');

const MIN_WIDTH = 1280;
const MIN_HEIGHT = 650;
const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload';
const CHROME_EXE = process.env.OMNICUT_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PROFILE_DIR = path.join(ROOT, 'tools', 'tiktok_browser_profile');

function parseArgs(argv) {
  const args = { channel: 'main', limit: 10, port: 9333, dryRun: false, health: false, noLaunch: false, queueId: null, coverFallback: false, viewport: null, net: null, clipBudgetMin: require('../../tiktok_autopost_extension/limits.js').CLIP_BUDGET_MIN, mode: 'schedule' };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--health') args.health = true;
    else if (a === '--no-launch') args.noLaunch = true;
    else if (a === '--cover-fallback') args.coverFallback = true;
    else if (a === '--mode') args.mode = argv[++i];
    else if (a === '--viewport') args.viewport = argv[++i];
    else if (a === '--net') args.net = argv[++i];
    else if (a === '--clip-budget-min') args.clipBudgetMin = Number(argv[++i]);
    else if (a === '--channel') args.channel = argv[++i];
    else if (a === '--limit') args.limit = Number(argv[++i]);
    else if (a === '--port') args.port = Number(argv[++i]);
    else if (a === '--queue-id') args.queueId = argv[++i];
    else throw new Error(`unknown argument: ${a}`);
  }
  if (!Number.isInteger(args.limit) || args.limit < 1) throw new Error('--limit ต้องเป็นจำนวนเต็ม >= 1');
  if (!['schedule', 'draft'].includes(args.mode)) throw new Error('--mode ต้องเป็น schedule | draft');
  if (args.viewport && !/^\d{3,4}x\d{3,4}$/.test(args.viewport)) throw new Error('--viewport ต้องเป็นรูปแบบ 1366x768');
  if (args.net && !['slow', 'blip', 'offline'].includes(args.net)) throw new Error('--net ต้องเป็น slow | blip | offline');
  if (!(args.clipBudgetMin > 0)) throw new Error('--clip-budget-min ต้องมากกว่า 0');
  return args;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function portUp(port) {
  try { return (await fetch(`http://127.0.0.1:${port}/json/version`)).ok; } catch (_) { return false; }
}

async function ensureChrome({ port, noLaunch }) {
  if (await portUp(port)) return 'attached';
  if (noLaunch) throw Object.assign(new Error(`ไม่พบ Chrome ที่พอร์ต ${port}`), { exitCode: 3 });
  const child = spawn(CHROME_EXE, [
    `--remote-debugging-port=${port}`, `--user-data-dir=${PROFILE_DIR}`,
    '--no-first-run', '--no-default-browser-check', '--lang=th-TH', '--window-size=1280,1000',
    '--disable-session-crashed-bubble', '--hide-crash-restore-bubble', '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
    UPLOAD_URL,
  ], { detached: true, stdio: 'ignore' });
  child.unref();
  for (let i = 0; i < 40; i += 1) {
    if (await portUp(port)) return 'launched';
    await sleep(500);
  }
  throw Object.assign(new Error('เปิด Chrome พร้อมพอร์ต debug ไม่สำเร็จ — ปิด Chrome ที่ใช้โปรไฟล์ tools/tiktok_browser_profile ก่อน แล้วรันใหม่'), { exitCode: 3 });
}

// Prevents Windows sleep while the run is alive (child dies with us).
function keepAwake() {
  if (process.platform !== 'win32') return () => {};
  const script = `$sig='[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);';` +
    `Add-Type -MemberDefinition $sig -Name K -Namespace W;` +
    `while (Get-Process -Id ${process.pid} -ErrorAction SilentlyContinue) { [W.K]::SetThreadExecutionState(0x80000001) | Out-Null; Start-Sleep 30 }`;
  const child = spawn('powershell', ['-NoProfile', '-WindowStyle', 'Hidden', '-Command', script], { stdio: 'ignore' });
  return () => { try { child.kill(); } catch (_) {} };
}

async function findStudioTab(shim) {
  const tabs = await shim.chrome.tabs.query({ url: '*://www.tiktok.com/*' });
  return tabs.find(t => /\/tiktokstudio/.test(t.url)) || tabs[0] || null;
}

// `worker` is optional: with it, a page left in a half-filled state by an earlier
// run is reset through the extension's own dialog-aware reset before checking.
async function checkStudioReady(shim, worker) {
  let tab = await findStudioTab(shim);
  // A tab whose renderer hung does not answer CDP at all: replace it instead of waiting forever.
  if (tab) {
    const alive = await shim.evaluate(tab.id, '1').then(() => true).catch(() => false);
    if (!alive) tab = await shim.replaceTab(tab.id, UPLOAD_URL);
  }
  if (!tab) tab = await shim.chrome.tabs.create({ url: UPLOAD_URL });
  else if (!/\/tiktokstudio\/upload/.test(tab.url)) tab = await shim.chrome.tabs.update(tab.id, { url: UPLOAD_URL, active: true });
  const checks = { login: false, file_input: false, url: '' };
  let reset = false;
  for (let i = 0; i < 40; i += 1) {
    await sleep(1000);
    const now = await shim.chrome.tabs.get(tab.id);
    checks.url = now.url;
    if (/login|passport/.test(now.url)) break;
    if (!/\/tiktokstudio/.test(now.url)) continue;
    checks.login = true;
    checks.file_input = Boolean(await shim.evaluate(tab.id, `!!document.querySelector('input[type="file"]')`).catch(() => false));
    if (checks.file_input) break;
    if (worker && !reset && i >= 6) {
      reset = true;
      await worker.send('reset-upload-page').catch(() => {});
    }
  }
  return { tab, checks: { ...checks, reset } };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const runId = new Date().toISOString().replace(/[:.]/g, '-');
  const runDir = path.join(ROOT, '.tmp', 'autopost_runs', runId);
  fs.mkdirSync(runDir, { recursive: true });
  const logFile = path.join(runDir, 'run.jsonl');
  const log = (level, message) => {
    console.log(`[${level}] ${message}`);
    fs.appendFileSync(logFile, JSON.stringify({ t: new Date().toISOString(), level, message }) + '\n');
  };
  const alert = message => {
    fs.writeFileSync(path.join(runDir, 'ALERT.txt'), message);
    fs.writeFileSync(path.join(ROOT, '.tmp', 'autopost_ALERT.txt'), `${runId}\n${message}\n`);
    log('error', `ต้องมีคนช่วย: ${message}`);
  };

  const apiKey = readApiKey();
  const api = createApi({ apiKey, channelId: args.channel });
  const caps = await api.get('/api/tiktok-autopost/capabilities').catch(() => ({ ok: false }));
  if (!caps.ok) { alert('Backend (127.0.0.1:8000) ไม่ตอบหรือ API key ผิด'); process.exit(3); }

  // One conductor at a time (a second run would fight over the same Chrome/tab). Health checks only attach, so skip them.
  let processLock = null;
  if (!args.health) {
    processLock = acquireProcessLock(path.join(ROOT, '.tmp', 'autopost_conductor.lock'));
    if (!processLock.ok) {
      alert(`มี conductor อีกตัวกำลังรันอยู่ (pid ${processLock.owner?.pid ?? '?'}, เริ่ม ${processLock.owner?.startedAt ?? '?'}) — รอให้จบก่อน หรือปิดตัวนั้นก่อน`);
      process.exit(3);
    }
  }
  const stopAwake = keepAwake();
  const holds = []; // network / viewport emulation sessions: must be released or the process never exits
  try {
    log('info', `Chrome: ${await ensureChrome(args)}`);
    const shim = createChromeShim({
      port: args.port, storageFile: path.join(ROOT, '.tmp', 'autopost_state.json'),
      secrets: { omnicutApiKey: apiKey },
    });
    // `current` is replaced after a clip timeout so a stuck (zombie) action cannot block the next clip.
    let current = loadWorker({ shim });
    const worker = { send: (action, payload) => current.send(action, payload) };
    const recover = async () => {
      log('warn', 'เกินเวลา — ตัดการเชื่อมต่อ debugger ที่ค้างและสร้าง worker ใหม่');
      shim.abortAll();
      current = loadWorker({ shim });
    };
    let { tab, checks } = await checkStudioReady(shim, worker);
    const healthy = checks.login && checks.file_input;
    fs.writeFileSync(path.join(ROOT, '.tmp', 'autopost_health.json'),
      JSON.stringify({ ok: healthy, checked_at: new Date().toISOString(), checks }, null, 2));
    if (!checks.login) {
      alert(`TikTok Studio ยังไม่พร้อม (url=${checks.url}) — login มือในหน้าต่าง Chrome นี้หนึ่งครั้ง แล้วรันใหม่`);
      throw Object.assign(new Error('login_required'), { exitCode: 3, alerted: true });   // finally still runs
    }
    if (!healthy) {
      alert(`login แล้วแต่ไม่พบช่องเลือกไฟล์บนหน้าอัปโหลด (url=${checks.url}) — TikTok อาจเปลี่ยนหน้า หรือมี dialog ค้าง`);
      throw Object.assign(new Error('upload_input_missing'), { exitCode: 3, alerted: true });
    }
    log('info', 'TikTok Studio พร้อม (login แล้ว, พบ input อัปโหลดไฟล์)');
    if (args.health) { log('info', 'health ok'); return; }

    if (args.viewport) {
      const [w, h] = args.viewport.split('x').map(Number);
      await shim.setWindowSize(tab.id, w, h);
      log('info', `ขนาดหน้าต่าง Chrome: ${w}x${h}`);
      await sleep(1500);
    }
    // TikTok's modals clip below ~1200 px wide: make the run independent of the real
    // window size, monitor and Windows DPI scaling.
    const preflightViewport = async () => {
      const measure = async () => shim.evaluate(tab.id, '({w: window.innerWidth, h: window.innerHeight})').catch(() => ({ w: 0, h: 0 }));
      let size = await measure();
      if ((size.w < MIN_WIDTH || size.h < MIN_HEIGHT) && !process.env.OMNICUT_FORCE_VIEWPORT_EMULATION) {
        await shim.setWindowSize(tab.id, 1440, 960).catch(() => {});
        await sleep(1200);
        size = await measure();
      }
      if (size.w < MIN_WIDTH || size.h < MIN_HEIGHT) {
        holds.push(await shim.holdViewport(tab.id, { width: 1440, height: 900 }));
        await sleep(800);
        log('warn', `หน้าต่างเล็ก (${size.w}x${size.h}) — จำลอง viewport 1440x900 ตลอดรอบ`);
      } else {
        log('info', `viewport ${size.w}x${size.h} ใช้ได้`);
      }
    };
    await preflightViewport();
    let netHold = null;
    if (args.net) {
      const SLOW = { latency: 300, down: 200 * 1024, up: 60 * 1024 };
      netHold = await shim.holdNetwork(tab.id, args.net === 'offline' ? { offline: true } : args.net === 'slow' ? SLOW : {});
      holds.push(netHold);
      log('info', `จำลองเครือข่าย: ${args.net}`);
      if (args.net === 'blip') {
        setTimeout(async () => { log('warn', 'จำลองเน็ตหลุด 30 วินาที'); await netHold.set({ offline: true }); }, 40_000);
        setTimeout(async () => { log('warn', 'เน็ตกลับมา'); await netHold.set({}); }, 70_000);
      }
    }

    const { clips, skipped } = await pickClips(api, args);
    skipped.forEach(s => log('warn', `ข้าม ${s.title}: ${s.reason}`));
    if (!clips.length) { log('info', 'ไม่มีคลิปพร้อมโพสต์ในคิว'); return; }

    let stopRequested = false;
    process.on('SIGINT', () => {
      if (stopRequested) {
        log('error', 'รับสัญญาณหยุดครั้งที่สอง — ออกทันที (คลิปที่กำลังทำอาจค้าง ตรวจที่ TikTok Studio)');
        processLock?.release();
        process.exit(130);
      }
      stopRequested = true;
      log('warn', 'รับสัญญาณหยุด — จบคลิปปัจจุบันแล้วหยุด (กดอีกครั้งเพื่อออกทันที)');
    });
    const tabId = async () => (await findStudioTab(shim))?.id ?? tab.id;
    const shot = async label => shim.screenshot(await tabId(), path.join(runDir, `${label}.png`)).catch(e => log('warn', `screenshot: ${e.message}`));
    const deps = {
      worker, api, log, sleep, recover,
      // Live TikTok quota (scheduled posts / drafts, 30 each): runBatch never plans more than what is left.
      quota: () => worker.send('detect-tiktok-quota', { allowNavigate: true }),
      // Chrome crashed / was closed / its tab hung between clips: relaunch, re-check login, redo viewport.
      ensureBrowser: async () => {
        const alive = await portUp(args.port) && await shim.evaluate(await tabId(), '1').then(() => true).catch(() => false);
        if (alive) return;
        log('warn', 'Chrome หรือแท็บ TikTok ไม่ตอบ — เปิดใหม่และตรวจ login');
        shim.abortAll();
        for (const hold of holds.splice(0)) await hold.release().catch(() => {});
        await ensureChrome(args);
        current = loadWorker({ shim });
        const ready = await checkStudioReady(shim, worker);
        if (!ready.checks.login) throw new Error(`login_required: TikTok Studio ไม่พร้อมหลังเปิด Chrome ใหม่ (${ready.checks.url})`);
        if (!ready.checks.file_input) throw new Error('ไม่พบช่องเลือกไฟล์หลังเปิด Chrome ใหม่');
        tab = ready.tab;
        await preflightViewport();
      },
      // Independent check after the post click: open Studio > Content and find this clip's row.
      verifyOnContentPage: async clip => {
        const id = await tabId();
        // TikTok's Content list lags the success toast by several seconds, so reload
        // and look again (up to ~90 s) before concluding the row is missing.
        let verdict = { ok: false, reason: 'row_not_found' };
        for (let attempt = 0; attempt < 6 && !verdict.ok; attempt += 1) {
          if (attempt) await sleep(8000);
          await shim.chrome.tabs.update(id, { url: 'https://www.tiktok.com/tiktokstudio/content', active: true });
          let text = '';
          for (let i = 0; i < 10; i += 1) {
            await sleep(1500);
            text = await shim.evaluate(id, 'document.body ? document.body.innerText : ""').catch(() => '');
            if (/\d{2}:\d{2}\n/.test(text)) break;
          }
          // Each post row starts with its video duration (mm:ss) on its own line.
          const rows = String(text).split(/\n(?=\d{2}:\d{2}\n)/).slice(0, 15);
          verdict = { ok: false, reason: 'row_not_found' };
          for (const row of rows) {
            const r = rowMatchesClip(row, clip);
            if (r.ok) { verdict = r; break; }
            if (r.reason === 'schedule_badge_mismatch') verdict = r;
          }
        }
        await shot(`${clip.id}_content`);
        await shim.chrome.tabs.update(id, { url: UPLOAD_URL, active: true }); // reset needs an upload tab
        await sleep(2500);
        return verdict;
      },
      // Closes the "Edit cover" modal (Cancel) when no custom-cover upload exists.
      dismissCoverModal: async () => {
        await shim.evaluate(await tabId(), `(() => {
          const dialogs = [...document.querySelectorAll('[role="dialog"],[aria-modal="true"]')];
          const d = dialogs.find(x => /Edit cover|แก้ไขหน้าปก|แก้ไขปก/.test(x.innerText || ''));
          const b = d && [...d.querySelectorAll('button,[role="button"]')].find(x => ['Cancel', 'ยกเลิก'].includes((x.innerText || '').trim()));
          if (b) b.click();
          return !!b;
        })()`).catch(() => false);
        await sleep(900);
        // TikTok then asks "Discard this edit?" — confirm, or it blocks the post button.
        await shim.evaluate(await tabId(), `(() => {
          const dialogs = [...document.querySelectorAll('[role="dialog"],[aria-modal="true"]')];
          const d = dialogs.find(x => /Discard this edit|ละทิ้งการแก้ไข|ทิ้งการแก้ไข/.test(x.innerText || ''));
          const b = d && [...d.querySelectorAll('button,[role="button"]')].find(x => ['Discard', 'ละทิ้ง', 'ทิ้ง'].includes((x.innerText || '').trim()));
          if (b) b.click();
          return !!b;
        })()`).catch(() => false);
        await sleep(900);
      },
      shot,
      dumpDom: async label => {
        const html = await shim.evaluate(await tabId(), 'document.documentElement.outerHTML').catch(() => '');
        if (html) {
          const dir = path.join(ROOT, '.tmp', 'autopost_dom');
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, `${label}.html`), html);
        }
      },
    };
    const summary = await runBatch(deps, { clips, dryRun: args.dryRun, channelId: args.channel, coverFallback: args.coverFallback, mode: args.mode, clipBudgetMs: args.clipBudgetMin * 60000, shouldStop: () => stopRequested });
    fs.writeFileSync(path.join(runDir, 'summary.json'), JSON.stringify(summary, null, 2));
    log('info', `สรุป: โพสต์ ${summary.posted} · ตั้งเวลา ${summary.scheduled} · แบบร่าง ${summary.drafted} · dry-run ${summary.dry_run_ok} · ข้าม ${summary.skipped} · ล้ม ${summary.failed} · ไม่ชัด ${summary.unknown}`);
    if (summary.aborted) { alert(summary.aborted); process.exitCode = 2; }
    else if (summary.failed || summary.unknown) process.exitCode = 1;
  } catch (error) {
    if (!error.alerted) alert(error.message);
    process.exitCode = error.exitCode || 2;
  } finally {
    for (const hold of holds) await hold.release().catch(() => {});
    stopAwake();
    processLock?.release();
  }
}

if (require.main === module) {
  // Always exit by ourselves: a stray CDP socket or child process must never keep an
  // unattended (scheduled) run alive after it has finished.
  main().catch(error => { console.error(error); process.exitCode = process.exitCode || 2; })
    .finally(() => setTimeout(() => process.exit(process.exitCode || 0), 300));
}

module.exports = { parseArgs };
