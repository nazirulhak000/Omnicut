// Links that must work on the owner's phone (app served through a public
// tunnel such as https://studio.nazirulhak.com). LAN `https://<ip>:5173` and
// `localhost` links are dead there.

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1', '::1', '[::1]', '0.0.0.0']);

export function isLocalHostname(hostname) {
  return LOCAL_HOSTNAMES.has(String(hostname || '').toLowerCase());
}

function currentLocation(loc) {
  if (loc) return loc;
  return typeof window !== 'undefined' ? window.location : null;
}

/**
 * Base URL to put in QR codes / "open on phone" links.
 * - Page opened on a real host (tunnel/LAN) -> that origin; it is what the
 *   phone already reaches.
 * - Page opened on localhost (desktop dev) -> the backend's public
 *   `mobile_url` (OMNICUT_PUBLIC_URL / forwarded host / LAN fallback).
 */
export function publicAppOrigin(serverMobileUrl = '', loc) {
  const l = currentLocation(loc);
  const origin = l?.origin || '';
  if (l && !isLocalHostname(l.hostname)) return origin;
  const server = String(serverMobileUrl || '').trim().replace(/\/+$/, '');
  return server || origin;
}

/**
 * Studio preview URL that is reachable from here, or null when it points at
 * a localhost-only service (e.g. HyperFrames Studio on :3002) while the page
 * itself is not on localhost.
 */
export function reachableStudioUrl(url, loc) {
  if (!url) return null;
  const l = currentLocation(loc);
  if (!l || isLocalHostname(l.hostname)) return url;
  try {
    const target = new URL(url, l.origin);
    return isLocalHostname(target.hostname) ? null : target.href;
  } catch {
    return null;
  }
}

export const LOCAL_STUDIO_HINT = 'เปิด Studio ได้เฉพาะบนคอมที่รันโปรแกรม';

/** Touch-first device (phone/tablet): QR codes are pointless there. */
export function isCoarsePointer() {
  try {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      && window.matchMedia('(pointer: coarse)').matches;
  } catch {
    return false;
  }
}
