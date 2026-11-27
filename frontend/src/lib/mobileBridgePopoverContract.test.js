import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8');

const apiSource = read('../api.js');
const popoverSource = read('../components/MobileBridgePopover.jsx');
const topbarSource = read('../components/Topbar.jsx');
const statusBarSource = read('../components/StatusBar.jsx');
const appSource = read('../App.jsx');

test('api.js exports all Mobile HTTPS Bridge helpers', () => {
  for (const fn of [
    'getMobileBridgeStatus',
    'toggleMobileBridge',
    'getMobileBridgePassword',
    'rotateMobileBridgePassword',
  ]) {
    assert.ok(
      new RegExp(`export\\s+const\\s+${fn}\\s*=`).test(apiSource),
      `api.js must export ${fn}`
    );
  }
  assert.ok(apiSource.includes('/mobile-bridge/status'));
  assert.ok(apiSource.includes('/mobile-bridge/toggle'));
  assert.ok(apiSource.includes('/mobile-bridge/password'));
  assert.ok(apiSource.includes('/mobile-bridge/password/rotate'));
});

test('MobileBridgePopover uses PopoverPanel, Matte-Dark tokens, zero transition-all, and no custom document listeners', () => {
  assert.ok(popoverSource.includes("from './ui/PopoverPanel'"), 'Must use ui/PopoverPanel');
  assert.ok(popoverSource.includes('<PopoverPanel'), 'Must render PopoverPanel');
  assert.ok(!/document\.addEventListener/.test(popoverSource), 'Must not attach custom document listeners (Rule 26)');
  assert.ok(!/onMouseDown|mousedown/.test(popoverSource), 'Must not attach custom mousedown listeners');
  assert.ok(!popoverSource.includes('transition-all'), 'Must not use transition-all');
  assert.ok(popoverSource.includes('bg-[#14161A]'), 'Must use Matte-Dark #14161A surface');
  assert.ok(popoverSource.includes('border-[#23262D]'), 'Must use 1px #23262D border');
});

test('MobileBridgePopover buttons follow verb-first hygiene without leading + or emoji', () => {
  const buttonTags = popoverSource.match(/<button[\s\S]*?<\/button>/g) || [];
  assert.ok(buttonTags.length >= 8, 'MobileBridgePopover should expose its interactive buttons');
  for (const btn of buttonTags) {
    const spanMatches = btn.match(/<span[^>]*>(.*?)<\/span>/g) || [];
    for (const span of spanMatches) {
      const text = span.replace(/<[^>]+>/g, '').trim();
      if (!text) continue;
      assert.ok(!text.startsWith('+'), `Button text must not start with '+': "${text}"`);
      assert.ok(
        !/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u.test(text),
        `Button text must not start with emoji: "${text}"`
      );
    }
  }
});

test('MobileBridgePopover includes mode switcher, QR, deep-link targets, password controls, iOS CA, warning, and USB footer', () => {
  for (const mode of ['lan_https', 'tailscale', 'public']) {
    assert.ok(popoverSource.includes(mode), `Missing mode ${mode}`);
  }
  assert.ok(popoverSource.includes('Wi-Fi HTTPS :8443'));
  assert.ok(popoverSource.includes('Tailscale HTTPS'));
  assert.ok(popoverSource.includes('Public URL'));

  assert.ok(popoverSource.includes('<QRCodeSVG'), 'Must render QRCodeSVG');
  assert.ok(popoverSource.includes('คัดลอกลิงก์'));
  assert.ok(popoverSource.includes('รีเฟรช IP'));

  assert.ok(popoverSource.includes('เปิดสตูดิโอ'));
  assert.ok(popoverSource.includes('ถ่ายทำล่าสุด'));
  assert.ok(popoverSource.includes('Quick-Ref'));
  assert.ok(popoverSource.includes('?film=1'));
  assert.ok(popoverSource.includes('?view=quick-ref'));

  assert.ok(popoverSource.includes('แสดงรหัสผ่าน'));
  assert.ok(popoverSource.includes('คัดลอกรหัส'));
  assert.ok(popoverSource.includes('ตั้งรหัสใหม่'));

  assert.ok(popoverSource.includes('/api/mobile-bridge/ca.crt'));
  assert.ok(popoverSource.includes('ดาวน์โหลดใบรับรอง CA'));
  assert.ok(popoverSource.includes('auth_disabled_warning'));
  assert.ok(popoverSource.includes('ดึงคลิปจาก iPhone (USB)'));
});

test('Topbar, StatusBar, and App wire Mobile Bridge trigger and live status', () => {
  assert.ok(topbarSource.includes('เชื่อมต่อมือถือ'), 'Topbar must render เชื่อมต่อมือถือ trigger');
  assert.ok(topbarSource.includes('<MobileBridgePopover'), 'Topbar must mount MobileBridgePopover');
  assert.ok(topbarSource.includes('mobileBridgeStatus'), 'Topbar must accept mobileBridgeStatus');

  assert.ok(statusBarSource.includes('mobileBridgeStatus'), 'StatusBar must accept mobileBridgeStatus');
  assert.ok(statusBarSource.includes('active_uploads'), 'StatusBar must display active_uploads');
  assert.ok(statusBarSource.includes('active_filming_sessions'), 'StatusBar must display active_filming_sessions');
  assert.ok(statusBarSource.includes('onOpenMobileBridge'), 'StatusBar pill must be clickable via onOpenMobileBridge');
  assert.ok(!statusBarSource.includes('transition-all'), 'StatusBar must not use transition-all');

  assert.ok(appSource.includes('getMobileBridgeStatus'), 'App.jsx must fetch getMobileBridgeStatus');
  assert.ok(appSource.includes('mobileBridgeStatus={mobileBridgeStatus}'), 'App.jsx must pass mobileBridgeStatus to Topbar and StatusBar');
});
