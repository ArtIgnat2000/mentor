const CACHE = "parents-public-b03c74fe09d0";
const FILES = ["./", "./index.html", "./static/app.css", "./static/app.js", "./manifest.webmanifest", "./static/icons/icon-192.png", "./static/icons/icon-512.png", "./pravila-papy.html", "./print-pravila-papy.html", "./pravila-mamy.html", "./print-pravila-mamy.html", "./metodika-pylesos.html", "./print-metodika-pylesos.html"];
const BASE = new URL('./', location);
const INDEX = new URL('./index.html', BASE).href;
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("parents-public-") && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return;
  e.respondWith(caches.open(CACHE).then(cache => cache.match(e.request).then(hit => hit || fetch(e.request).then(res => {
    if (res.ok) { const copy = res.clone(); cache.put(e.request, copy); }
    return res;
  }).catch(() => e.request.mode === 'navigate' ? cache.match(INDEX) : Response.error()))));
});
