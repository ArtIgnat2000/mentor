"""Сборка только открытого семейного контура для GitHub Pages.

Родительский контур сюда не экспортируется: статический хостинг не может
проверять вход. Запуск: python3 -m family.build_public
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path

from .content import load_contour

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT.parent / "docs" / "family"


def _shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#16302b">
<meta name="description" content="Общие семейные правила и материалы, которые можно показывать детям.">
<title>{html.escape(title)} · Семья</title>
<link rel="stylesheet" href="./static/app.css">
<link rel="manifest" href="./manifest.webmanifest">
<link rel="apple-touch-icon" href="./static/icons/icon-180.png">
</head>
<body class="family">
<header class="top"><a class="brand" href="./">Семья</a><nav><a href="./">Главная</a></nav></header>
<main class="wrap">
{body}
</main>
<script src="./static/app.js" defer></script>
</body>
</html>"""


def build(out_dir: Path = DEFAULT_OUT) -> Path:
    out = Path(out_dir)
    data = load_contour("family")  # намеренно только открытый контур
    out.mkdir(parents=True, exist_ok=True)
    static = out / "static"
    static.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "static" / "app.css", static / "app.css")
    shutil.copytree(ROOT / "static" / "icons", static / "icons", dirs_exist_ok=True)

    cards = []
    cached = ["./", "./index.html", "./static/app.css", "./static/app.js",
              "./manifest.webmanifest", "./static/icons/icon-192.png",
              "./static/icons/icon-512.png"]
    for page in data["pages"]:
        slug = page["slug"]
        if not slug or "/" in slug or "\\" in slug or slug.startswith("."):
            raise ValueError(f"Небезопасный slug: {slug!r}")
        file_name = f"{slug}.html"
        print_name = f"print-{slug}.html"
        cards.append(
            f'<a class="card" href="./{file_name}">'
            f'<h2>{html.escape(page["title"])}</h2>'
            f'<p>{html.escape(page["summary"])}</p></a>'
        )
        article = f'<article class="content">{page["html"]}</article>'
        body = (f'<p><a href="./">← К списку</a></p>{article}'
                f'<p><a class="btn" href="./{print_name}">Версия для печати</a></p>')
        (out / file_name).write_text(_shell(page["title"], body), encoding="utf-8")
        print_body = (f'<p class="no-print"><a href="./{file_name}">← К материалу</a></p>'
                      f'{article}<p class="no-print"><button class="btn" data-print type="button">Печать</button></p>')
        (out / print_name).write_text(_shell(page["title"] + " · печать", print_body), encoding="utf-8")
        cached += [f"./{file_name}", f"./{print_name}"]

    home = ("<h1>Семейный справочник</h1>"
            "<p class='lead'>Общие правила и материалы, которые можно показывать детям. "
            "Без оценок, рейтингов и сравнения.</p>"
            f"<div class='cards'>{''.join(cards)}</div>")
    (out / "index.html").write_text(_shell("Семейный справочник", home), encoding="utf-8")

    manifest = {
        "id": "./", "name": "Семья — правила", "short_name": "Семья",
        "description": "Общие семейные правила и материалы для детей и родителей.",
        "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": "#f4f1ea", "theme_color": "#16302b", "lang": "ru",
        "icons": [
            {"src": "./static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "./static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        ],
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (static / "app.js").write_text("""if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('./sw.js').catch(function () {});
  });
}
document.addEventListener('click', function (event) {
  if (event.target.closest('[data-print]')) window.print();
});
""", encoding="utf-8")

    digest = hashlib.sha256()
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "sw.js":
            digest.update(path.relative_to(out).as_posix().encode())
            digest.update(path.read_bytes())
    cache_name = "family-public-" + digest.hexdigest()[:12]
    sw = """const CACHE = __CACHE__;
const FILES = __FILES__;
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
""".replace("__CACHE__", json.dumps(cache_name)).replace("__FILES__", json.dumps(cached))
    (out / "sw.js").write_text(sw, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(f"Открытый семейный справочник: {build()}")
