const CACHE = "family-public-300371f0488e";
const FILES = ["./", "./index.html", "./static/app.css", "./static/app.js", "./static/kids-hero.svg", "./manifest.webmanifest", "./static/icons/icon-192.png", "./static/icons/icon-512.png", "./nashi-pravila.html", "./print-nashi-pravila.html", "./kak-polzovatsya.html", "./print-kak-polzovatsya.html"];
const BASE = new URL('./', location);
const INDEX = new URL('./index.html', BASE).href;
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("family-public-") && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  e.respondWith(caches.open(CACHE).then(cache => cache.match(e.request).then(hit => {
    if (hit) return hit;
    if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return fetch(e.request);
    return fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); cache.put(e.request, copy); }
      return res;
    }).catch(() => e.request.mode === 'navigate' ? cache.match(INDEX) : Response.error());
  })));
});
