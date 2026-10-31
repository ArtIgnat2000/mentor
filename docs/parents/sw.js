const CACHE = "parents-public-705847e57480";
const FILES = ["./", "./index.html", "./static/app.css", "./static/app.js", "./static/kids-hero.svg", "./manifest.webmanifest", "./static/icons/icon-192.png", "./static/icons/icon-512.png", "./kak-polzovatsya.html", "./print-kak-polzovatsya.html", "./pravila-vzroslyh.html", "./print-pravila-vzroslyh.html", "../print/16_pravila_semyi_3xA4.pdf", "../print/01_na_holodilnik_A4.pdf", "./pravila-papy.html", "./print-pravila-papy.html", "../print/14_pravila_papy_A4.pdf", "../print/14m_pravila_papy_mobile.pdf", "../print/08_pamyatka_pape.pdf", "./pravila-mamy.html", "./print-pravila-mamy.html", "../print/15_pravila_mamy_A4.pdf", "../print/15m_pravila_mamy_mobile.pdf", "../print/09_pamyatka_mame.pdf", "./pravila-detey.html", "./print-pravila-detey.html", "../print/13_pravila_detey_A4.pdf", "../print/13m_pravila_detey_mobile.pdf", "./situacii.html", "./print-situacii.html", "./metodika-pylesos.html", "./print-metodika-pylesos.html", "./pechatnye-formy.html", "./print-pechatnye-formy.html", "../print/00_komplekt_na_pechat.pdf", "./forma-ezhednevnye-dela.html", "./print-forma-ezhednevnye-dela.html", "../print/17_ezhednevny_list_del.pdf", "../print/12_listy_poleznyh_del.pdf", "./forma-dobrye-dela.html", "./print-forma-dobrye-dela.html", "../print/06_kopilka_dobryh_del.pdf", "./forma-turnik-zaryadka.html", "./print-forma-turnik-zaryadka.html", "../print/10_dnevnik_sily.pdf", "./forma-utro.html", "./print-forma-utro.html", "../print/02_karta_utra.pdf", "./forma-pauza.html", "./print-forma-pauza.html", "../print/03_karta_pauzy.pdf", "../print/04_shkala_1_5.pdf", "./forma-itogi-nedeli.html", "./print-forma-itogi-nedeli.html", "../print/11_itogi_nedeli.pdf", "./forma-samoproverka.html", "./print-forma-samoproverka.html", "../print/07_proverka_ya_sbilsya.pdf"];
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
  e.respondWith(caches.open(CACHE).then(cache => cache.match(e.request).then(hit => {
    if (hit) return hit;
    if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return fetch(e.request);
    return fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); cache.put(e.request, copy); }
      return res;
    }).catch(() => e.request.mode === 'navigate' ? cache.match(INDEX) : Response.error());
  })));
});
