/** Trusted, pinned SDK worker. Authored code runs only after HTTP request guards. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import * as engine from './hyperframes-runtime/node_modules/@hyperframes/engine/dist/index.js';
import { createFileServer } from './hyperframes-runtime/node_modules/@hyperframes/producer/dist/index.js';
import { validateApprovedMasterOverlay } from './hyperframes_overlay_guard.mjs';

const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const inside = (base, value) => { const relative = path.relative(base, value); return relative && !relative.startsWith('..') && !path.isAbsolute(relative); };

export async function renderGuarded(spec) {
  validateApprovedMasterOverlay(spec);
  for (const name of ['engine', 'producer']) {
    const installed = JSON.parse(await fs.readFile(new URL(`./hyperframes-runtime/node_modules/@hyperframes/${name}/package.json`, import.meta.url), 'utf8'));
    if (installed.version !== '0.8.143') throw new Error('Guarded worker requires SDK 0.8.143; reinstall the runtime lockfile');
  }
  const project = await fs.realpath(spec.project_dir);
  const output = path.resolve(spec.output_path);
  const work = path.dirname(output);
  if (!inside(work, project) || !output.endsWith('.mp4')) throw new Error('Worker requires a disposable composition inside its output directory');
  const allowed = new Set();
  for (const file of spec.files) {
    const relative = file.path.replaceAll('\\', '/');
    const actual = await fs.realpath(path.resolve(project, relative));
    if (!inside(project, actual) || sha(await fs.readFile(actual)) !== file.sha256) throw new Error('Snapshot dependency changed');
    allowed.add('/' + relative);
  }
  if (spec.entrypoint !== 'index.html' || !allowed.has('/index.html')) throw new Error('Canonical index.html required');
  const duration = Number(spec.duration_seconds);
  if (!Number.isFinite(duration) || duration <= 0 || duration > 300) throw new Error('Duration must be between 0 and 300 seconds');
  if (!['silent', 'narration', 'music_only'].includes(spec.audio_mode)) throw new Error('Unsupported audio mode');
  const audit = { policy: 'snapshot_http_allowlist_v1', sdk_version: '0.8.143', blocked: [], completed: false };
  const blocked = (kind, value) => {
    // Do not persist secret query values from authored requests.
    const text = String(value || '');
    let origin = ''; try { origin = new URL(text).origin; } catch { origin = text.slice(0, 100); }
    audit.blocked.push({ kind, origin, url_sha256: sha(text) });
  };
  const assertSafe = () => { if (audit.blocked.length) { const error = new Error('hyperframes_network_blocked: composition attempted prohibited network/execution; vendor dependencies and submit a new revision'); error.code = 'hyperframes_network_blocked'; throw error; } };
  let server, session, lookup;
  const config = { ...engine.DEFAULT_CONFIG, enableBrowserPool: false, forceScreenshot: true,
    staticFrameDedup: false, useDrawElement: false, enableDrawElementWorkerEncode: false,
    enablePageSideCompositing: false, disableGpu: true, playerReadyTimeout: 10000,
    pageNavigationTimeout: 15000, renderReadyTimeout: 10000, chromePath: spec.chrome_path };
  try {
    const html = await fs.readFile(path.join(project, 'index.html'), 'utf8');
    for (const file of spec.files.filter(file => /\.html?$/i.test(file.path) && file.path !== 'index.html')) {
      const nested = await fs.readFile(path.join(project, file.path), 'utf8');
      if (engine.parseVideoElements(nested).length || engine.parseAudioElements(nested).length) {
        throw new Error('hyperframes_nested_media_unsupported: keep audio and video tracks in root index.html; nested visual scenes remain supported');
      }
    }
    // FFmpeg runs outside Chrome: forbid URLs and files outside the frozen set.
    const validateMedia = (elements) => {
      for (const element of elements) {
        const source = element.src;
        if (!source || /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(source)) throw new Error('Media must be a frozen local file');
        const resolved = path.resolve(project, source.replace(/^\//, ''));
        const relative = '/' + path.relative(project, resolved).replaceAll('\\', '/');
        if (!inside(project, resolved) || !allowed.has(relative)) throw new Error('Media is outside the accepted snapshot');
      }
      return elements;
    };
    const videos = validateMedia(engine.parseVideoElements(html));
    const audio = validateMedia(engine.parseAudioElements(html));
    if (spec.audio_mode !== 'silent' && !audio.length) throw new Error('Declared audio mode requires an authored local audio track');
    const requiredAudio = spec.asset_contract?.required_audio || [];
    const requiredRole = spec.audio_mode === 'narration' ? 'voiceover' : 'music';
    if (spec.audio_mode !== 'silent' && !requiredAudio.some(asset => asset.role === requiredRole)) {
      throw new Error('hyperframes_audio_contract_missing: pin the required saved audio asset before rendering');
    }
    for (const asset of requiredAudio) {
      const audible = audio.some(element => {
        const relative = path.relative(project, path.resolve(project, element.src.replace(/^\//, ''))).replaceAll('\\', '/');
        const file = spec.files.find(candidate => candidate.path.replaceAll('\\', '/') === relative);
        if (file?.sha256 !== asset.sha256) return false;
        if (element.automation || element.groupAutomation || element.fxChain || element.groupFxChain || element.fadeIn || element.fadeOut) {
          throw new Error('hyperframes_audio_processing_unsupported: required tracks must use constant gain; fades, automation and FX require validated audibility support');
        }
        const volume = element.volume ?? 1;
        const groupVolume = element.groupVolume ?? 1;
        return Number.isFinite(volume) && volume > 0 && Number.isFinite(groupVolume) && groupVolume > 0 && (element.mediaStart ?? 0) === 0 &&
          element.start >= 0 && element.start < duration && (element.end === 0 || element.end > element.start);
      });
      if (!audible) throw new Error('hyperframes_audio_asset_unused: exact required saved audio hash must be an audible timeline track');
    }
    let hook = null;
    if (videos.length) {
      const extracted = await engine.extractAllVideoFrames(videos, project,
        { fps: 30, outputDir: path.join(work, 'video-frames'), format: 'png', timelineEnd: duration }, undefined, config);
      if (!extracted.success) throw new Error('Local video extraction failed: ' + JSON.stringify(extracted.errors));
      lookup = engine.createFrameLookupTable(videos, extracted.extracted, 30);
      hook = engine.createVideoFrameInjector(lookup, config);
    }
    const csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; font-src 'self' data:; connect-src 'self'; worker-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
    server = await createFileServer({ projectDir: project, port: 0, fps: { num: 30, den: 1 },
      preHeadScripts: [`document.head.appendChild(Object.assign(document.createElement('meta'), {httpEquiv:'Content-Security-Policy',content:${JSON.stringify(csp)}}));`] });
    const origin = new URL(server.url).origin;
    const frameDir = path.join(work, 'frames');
    await fs.mkdir(frameDir, { recursive: true });
    session = await engine.createCaptureSession(server.url, frameDir,
      { width: 1080, height: 1920, fps: { num: 30, den: 1 }, format: 'png', compositionDurationSeconds: duration, requiresWebGpu: false }, hook, config);
    const page = session.page;
    await page.setBypassServiceWorker(true);
    await page.setRequestInterception(true);
    page.on('request', request => {
      const url = request.url();
      let permit = false;
      try {
        const parsed = new URL(url);
        const pathname = decodeURIComponent(parsed.pathname);
        permit = parsed.origin === origin && ['GET', 'HEAD'].includes(request.method()) &&
          allowed.has(pathname === '/' ? '/index.html' : pathname) && !parsed.username && !parsed.password;
        // Raster frame injection is inert, and needed for seek-safe video frames.
        permit ||= request.resourceType() === 'image' && /^data:image\/(?:png|jpeg|webp);base64,/i.test(url);
        permit ||= request.resourceType() === 'font' && /^data:(?:font\/(?:woff2?|ttf|otf)|application\/(?:font-woff|x-font-ttf));base64,/i.test(url);
        if (parsed.origin === origin && pathname === '/favicon.ico') { request.respond({ status: 204 }).catch(() => {}); return; }
      } catch {}
      if (permit) request.continue().catch(() => {});
      else { blocked('request', url); request.abort('blockedbyclient').catch(() => {}); }
    });
    await page.exposeFunction('__omnicutBlocked', blocked);
    await page.evaluateOnNewDocument(() => {
      const bridge = window.__omnicutBlocked;
      const stringify = String;
      const report = (kind, url) => { bridge(kind, stringify(url)).catch(() => {}); };
      Object.defineProperty(window, '__omnicutBlocked', { configurable: false, writable: false, value: bridge });
      window.addEventListener('securitypolicyviolation', event => report('csp:' + event.violatedDirective, event.blockedURI), true);
      for (const name of ['Worker', 'SharedWorker', 'WebSocket', 'RTCPeerConnection', 'webkitRTCPeerConnection']) {
        try { Object.defineProperty(window, name, { configurable: false, writable: false,
          value: function(url) { report(name, url); throw new Error('Unsupported network execution in render worker'); } }); } catch {}
      }
      Object.defineProperty(window, 'open', { configurable: false, writable: false,
        value: (url) => { report('popup', url); return null; } });
    });
    // Pause every newly created target before scripts; close instead of resuming.
    // This also prevents links/forms from escaping into unguarded popup pages.
    const pageGuard = await page.createCDPSession();
    pageGuard.on('Audits.issueAdded', ({ issue }) => {
      const violation = issue.details?.contentSecurityPolicyIssueDetails;
      if (violation && !violation.isReportOnly) blocked('cdp-csp:' + violation.violatedDirective, violation.blockedURL);
    });
    await pageGuard.send('Audits.enable');
    const { targetInfo: mainTarget } = await pageGuard.send('Target.getTargetInfo');
    for (const initialPage of await session.browser.pages()) {
      if (initialPage !== page) await initialPage.close();
    }
    const browserGuard = await session.browser.target().createCDPSession();
    browserGuard.on('Target.attachedToTarget', async event => {
      if (event.targetInfo.targetId === mainTarget.targetId) return;
      blocked('target:' + event.targetInfo.type, event.targetInfo.url);
      await browserGuard.send('Target.closeTarget', { targetId: event.targetInfo.targetId }).catch(() => {});
    });
    await browserGuard.send('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true });
    await engine.initializeSession(session);
    assertSafe();
    const declaredDuration = await engine.getCompositionDuration(session);
    if (!Number.isFinite(declaredDuration) || Math.abs(declaredDuration - duration) > 1 / 30) {
      throw new Error('hyperframes_duration_mismatch: composition duration differs from the pinned project inputs');
    }
    for (let frame = 0; frame < Math.round(duration * 30); frame++) {
      const captured = await engine.captureFrameToBuffer(session, frame, frame / 30);
      await fs.writeFile(path.join(frameDir, `frame-${String(frame).padStart(6, '0')}.png`), captured.buffer);
      assertSafe();
    }
    const video = spec.audio_mode === 'silent' ? output : path.join(work, 'silent-video.mp4');
    const encoded = await engine.encodeFramesFromDir(frameDir, 'frame-%06d.png', video,
      { fps: { num: 30, den: 1 }, width: 1080, height: 1920, codec: 'h264', quality: 20, preset: 'fast', pixelFormat: 'yuv420p', useGpu: false }, undefined, config);
    if (!encoded.success) throw new Error(encoded.error || 'Video encode failed');
    if (spec.audio_mode !== 'silent') {
      const audioPath = path.join(work, 'audio.m4a');
      const mixed = await engine.processCompositionAudio(audio, project, path.join(work, 'audio-work'), audioPath, duration, undefined, config);
      if (!mixed.success || mixed.tracksProcessed < requiredAudio.length || mixed.failures?.length) throw new Error(mixed.error || 'Required audio mix failed');
      const muxed = await engine.muxVideoWithAudio(video, audioPath, output, undefined, config, { num: 30, den: 1 });
      if (!muxed.success) throw new Error(muxed.error || 'Audio mux failed');
    }
    assertSafe();
    audit.completed = true;
    return audit;
  } catch (error) {
    const match = error.message.match(/^(hyperframes_[a-z_]+):/);
    if (match) { error.code = match[1]; audit.error_code = error.code; audit.error_message = error.message; }
    throw error;
  } finally {
    if (session) await engine.closeCaptureSession(session).catch(() => {});
    if (server) await server.close();
    if (lookup) lookup.cleanup();
    await fs.writeFile(path.join(work, 'network-audit.json'), JSON.stringify(audit, null, 2));
    if (!audit.completed) await fs.unlink(output).catch(() => {});
    // These directories are exclusively allocated by this attempt, never source assets.
    for (const name of ['frames', 'video-frames', 'audio-work']) {
      const owned = path.resolve(work, name);
      if (inside(work, owned)) await fs.rm(owned, { recursive: true, force: true });
    }
    for (const name of ['audio.m4a', 'silent-video.mp4']) await fs.unlink(path.join(work, name)).catch(() => {});
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await renderGuarded(JSON.parse(await fs.readFile(process.argv[2], 'utf8'))); }
  catch (error) { console.error(JSON.stringify({ code: error.code || 'hyperframes_worker_failed', message: error.message })); process.exitCode = 1; }
}
