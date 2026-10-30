// OmniCut Pro Studio — Lightweight App Shell Service Worker
const CACHE_NAME = 'omnicut-shell-v1';
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/favicon.svg',
];

const BYPASS_PREFIXES = ['/api/', '/api', '/ws', '/terminal'];

const OFFLINE_FALLBACK_HTML = `<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>OmniCut — เซิร์ฟเวอร์หรือ Colab กำลังหลับ</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background: #07090E;
      color: #F8FAFC;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .card {
      width: 100%;
      max-width: 400px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 20px;
      padding: 28px 24px;
      text-align: center;
    }
    h1 {
      font-size: 20px;
      line-height: 1.4;
      margin: 0 0 12px;
      color: #FFFFFF;
    }
    p {
      font-size: 14px;
      line-height: 1.6;
      color: #94A3B8;
      margin: 0 0 24px;
    }
    button {
      width: 100%;
      min-height: 48px;
      border: 0;
      border-radius: 14px;
      background: linear-gradient(90deg, #FE2C55, #25F4EE);
      color: #07090E;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <main class="card" role="alert">
    <h1>เซิร์ฟเวอร์หรือ Colab กำลังหลับ</h1>
    <p>ไม่สามารถติดต่อเซิร์ฟเวอร์ OmniCut ได้ในขณะนี้ กรุณาตรวจสอบว่า Colab Runner หรือเซิร์ฟเวอร์เปิดอยู่ แล้วกดลองเชื่อมต่อใหม่</p>
    <button type="button" onclick="window.location.reload()">ลองเชื่อมต่อใหม่</button>
  </main>
</body>
</html>`;

function shouldBypassCache(url) {
  const pathname = url.pathname || '';
  return BYPASS_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL_URLS))
      .catch(() => {
        // Ignore individual precache failures in dev/offline environments
      })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  let url;
  try {
    url = new URL(request.url);
  } catch {
    return;
  }

  if (url.origin !== self.location.origin) return;
  if (shouldBypassCache(url)) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches
              .open(CACHE_NAME)
              .then((cache) => cache.put('/index.html', copy))
              .catch(() => {});
          }
          if (response && response.status >= 502 && response.status <= 504) {
            return caches.match('/index.html').then(
              (cached) =>
                cached ||
                new Response(OFFLINE_FALLBACK_HTML, {
                  status: 503,
                  headers: { 'Content-Type': 'text/html; charset=utf-8' },
                })
            );
          }
          return response;
        })
        .catch(() =>
          caches.match('/index.html').then(
            (cached) =>
              cached ||
              new Response(OFFLINE_FALLBACK_HTML, {
                status: 503,
                headers: { 'Content-Type': 'text/html; charset=utf-8' },
              })
          )
        )
    );
    return;
  }

  if (APP_SHELL_URLS.includes(url.pathname)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches
              .open(CACHE_NAME)
              .then((cache) => cache.put(request, copy))
              .catch(() => {});
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
  }
});
