const CACHE = "children-public-aae0f9ce7530";
const FILES = ["./", "./index.html", "./static/app.css", "./static/app.js", "./static/kids-hero.svg", "./manifest.webmanifest", "./static/icons/icon-192.png", "./static/icons/icon-512.png", "./nashi-pravila.html", "./print-nashi-pravila.html", "../print/13_pravila_detey_A4.pdf", "../print/13m_pravila_detey_mobile.pdf", "./esli-trudno.html", "./print-esli-trudno.html", "../print/03_karta_pauzy.pdf", "../print/04_shkala_1_5.pdf", "./moy-den.html", "./print-moy-den.html", "../print/17_ezhednevny_list_del.pdf", "../print/02_karta_utra.pdf", "../print/12_listy_poleznyh_del.pdf", "./moi-listy.html", "./print-moi-listy.html", "../print/06_kopilka_dobryh_del.pdf", "../print/10_dnevnik_sily.pdf"];
const BASE = new URL('./', location);
const INDEX = new URL('./index.html', BASE).href;
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("children-public-") && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
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
