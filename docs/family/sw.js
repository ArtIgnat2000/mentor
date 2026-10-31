const CACHE = "family-public-4bd2b496c3a6";
const FILES = ["./", "./index.html", "./static/app.css", "./static/app.js", "./manifest.webmanifest", "./static/icons/icon-192.png", "./static/icons/icon-512.png", "./nashi-pravila.html", "./print-nashi-pravila.html", "./kak-polzovatsya.html", "./print-kak-polzovatsya.html"];
const BASE = new URL('./', location);
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('family-public-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
    return res;
  }).catch(() => e.request.mode === 'navigate' ? caches.match('./index.html') : Response.error())));
});
