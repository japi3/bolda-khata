// Service worker: makes the app installable and lets the screen open without a connection.
// App files are network-first (always fresh when online, last copy when offline).
// The ledger API (/api/) is never cached, so no customer data is stored by the browser here.
const CACHE = 'bolda-khata-v5';
const SHELL = ['/', '/static/app.css', '/static/app.js', '/static/recorder.js', '/manifest.webmanifest',
  '/static/icons/icon-192.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match('/'))),
  );
});
