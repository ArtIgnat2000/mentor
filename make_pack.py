#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакет для GitHub Pages: иконки, manifest.webmanifest, sw.js (офлайн-кэш),
архив всего комплекта для передачи в новый чат.

Запускать ПОСЛЕ build_site.py — версия офлайн-кэша считается из содержимого
docs/index.html, поэтому после любой правки контента она поднимается сама
и телефон не показывает старую копию.

    python3 build_site.py && python3 make_pack.py
"""
from pathlib import Path
import hashlib
import json
import zipfile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "docs"

BG = (22, 48, 43)      # #16302b
GOLD = (181, 138, 43)  # #b58a2b
CREAM = (244, 241, 234)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.22)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)
    # «корешок книги» — золотая полоса
    bw = max(3, int(size * 0.055))
    x0 = int(size * 0.24)
    d.rounded_rectangle([x0, int(size * 0.24), x0 + bw, int(size * 0.76)],
                        radius=bw // 2, fill=GOLD)
    # три строки — ритм / пауза / поступок
    lh = max(4, int(size * 0.075))
    x1 = int(size * 0.38)
    widths = (0.38, 0.30, 0.22)
    ys = (0.30, 0.465, 0.63)
    for w, yy in zip(widths, ys):
        d.rounded_rectangle([x1, int(size * yy), x1 + int(size * w), int(size * yy) + lh],
                            radius=lh // 2, fill=CREAM)
    return img


MANIFEST = {
    "name": "Наставник — карманный свод",
    "short_name": "Наставник",
    "description": "Правила, протоколы и план на 90 дней для наставника двух братьев (8 и 10 лет)",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f4f1ea",
    "theme_color": "#16302b",
    "lang": "ru",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

SW = """/* Офлайн-кэш карманного свода.
   Версия подставляется make_pack.py из хэша docs/index.html — вручную не править. */
const CACHE = '__CACHE__';
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
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match('./index.html')))
  );
});
"""


# закрытый раздел в архив не кладём: он не для передачи
SKIP_FROM_PACK = {"semya.html"}


def cache_version() -> str:
    index = SITE / "index.html"
    if not index.exists():
        raise SystemExit("нет docs/index.html — сначала запустите: python3 build_site.py")
    digest = hashlib.sha256(index.read_bytes())
    mobile = SITE / "mobile"
    if mobile.exists():
        for path in sorted(mobile.glob("*.html")):
            digest.update(path.read_bytes())
    return f"nastavnik-{digest.hexdigest()[:10]}"


def main():
    SITE.mkdir(exist_ok=True)
    for size, name in [(180, "icon-180.png"), (192, "icon-192.png"), (512, "icon-512.png")]:
        make_icon(size).save(SITE / name)
    (SITE / "manifest.webmanifest").write_text(
        json.dumps(MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8")
    version = cache_version()
    (SITE / "sw.js").write_text(SW.replace("__CACHE__", version), encoding="utf-8")

    # полный комплект для передачи в новый чат / бэкапа
    pack = ROOT / "nastavnik_pack.zip"
    files = [
        "HANDOFF.md", "README.md", "00_README.md",
        "koncepciya_nastavnichestva_v1.md", "01_pravila_nastavnika.md",
        "02_protokoly_tipovyh_situaciy.md", "03_plan_90_dney.md",
        "build_site.py", "make_pack.py", "build_print.py", "requirements.txt",
        "nastavnik.html",
    ]
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if (ROOT / f).exists():
                z.write(ROOT / f, f)
        for folder in ("docs", "print"):
            d = ROOT / folder
            if not d.exists():
                continue
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.name not in SKIP_FROM_PACK:
                    z.write(f, f"{folder}/{f.relative_to(d)}")
    print("site files:", sorted(p.name for p in SITE.iterdir()))
    print("cache version:", version)
    print("pack:", pack.name, round(pack.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
