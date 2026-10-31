/* Офлайн-кэш карманного свода.
   Версия подставляется make_pack.py из хэша docs/index.html — вручную не править. */
const CACHE = 'nastavnik-1196b22d0e';
const FILES = [
  './', './index.html', './manifest.webmanifest',
  './icon-180.png', './icon-192.png', './icon-512.png',
  './mobile/index.html', './mobile/detyam.html', './mobile/pape.html', './mobile/mame.html'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith('nastavnik-') && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

const BASE = new URL('./', location);
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return;
  // У детского, семейного и родительского справочников собственные офлайн-кэши.
  if (url.pathname.startsWith(BASE.pathname + 'children/') ||
      url.pathname.startsWith(BASE.pathname + 'family/') ||
      url.pathname.startsWith(BASE.pathname + 'parents/')) return;
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match('./index.html')))
  );
});
