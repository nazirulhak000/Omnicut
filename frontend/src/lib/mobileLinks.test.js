import test from 'node:test';
import assert from 'node:assert/strict';
import { isLocalHostname, publicAppOrigin, reachableStudioUrl } from './mobileLinks.js';

const loc = (href) => { const u = new URL(href); return { origin: u.origin, hostname: u.hostname }; };

test('phone on the public tunnel gets the tunnel origin, never a LAN IP', () => {
  assert.equal(publicAppOrigin('https://192.168.1.5:5173', loc('https://studio.nazirulhak.com/?mode=mobile')), 'https://studio.nazirulhak.com');
});

test('desktop on localhost uses the backend public url, falling back to its own origin', () => {
  assert.equal(publicAppOrigin('https://studio.nazirulhak.com/', loc('http://localhost:5173/')), 'https://studio.nazirulhak.com');
  assert.equal(publicAppOrigin('', loc('http://127.0.0.1:5173/')), 'http://127.0.0.1:5173');
});

test('localhost studio links are hidden off-localhost, kept on localhost', () => {
  assert.equal(reachableStudioUrl('http://localhost:3002/clips/a', loc('https://studio.nazirulhak.com/')), null);
  assert.equal(reachableStudioUrl('http://127.0.0.1:3002/x', loc('https://studio.nazirulhak.com/')), null);
  assert.equal(reachableStudioUrl('http://localhost:3002/clips/a', loc('http://localhost:5173/')), 'http://localhost:3002/clips/a');
  assert.equal(reachableStudioUrl('/api/media/clip.mp4', loc('https://studio.nazirulhak.com/')), 'https://studio.nazirulhak.com/api/media/clip.mp4');
  assert.equal(reachableStudioUrl('', loc('https://studio.nazirulhak.com/')), null);
});

test('local hostname detection', () => {
  assert.equal(isLocalHostname('localhost'), true);
  assert.equal(isLocalHostname('[::1]'), true);
  assert.equal(isLocalHostname('studio.nazirulhak.com'), false);
});
