"""Сборка открытых справочников для GitHub Pages.

Публикуются два раздела: «Семья» и «Родителям». Оба доступны без входа.
Не кладите в индексы этих контуров материалы, которые не должны быть публичными.

Запуск: python3 -m family.build_public
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path

from .content import load_contour

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / "docs"
DEFAULT_OUT = DOCS / "family"

PUBLIC_CONTOURS = {
    "family": {
        "brand": "Семья",
        "title": "Семейный справочник",
        "description": "Общие семейные правила и материалы, которые можно показывать детям.",
        "lead": "Общие правила и материалы, которые можно показывать детям. "
                "Без оценок, рейтингов и сравнения.",
        "theme": "#16302b",
        "manifest_name": "Семья — правила",
        "manifest_short": "Семья",
        "manifest_description": "Общие семейные правила и материалы для детей и родителей.",
        "other": ("parents", "Родителям"),
    },
    "parents": {
        "brand": "Родителям",
        "title": "Родителям",
        "description": "Открытый справочник для родителей: правила папы и мамы, методики и спокойные сценарии.",
        "lead": "Правила для папы и мамы, методики и спокойные сценарии. "
                "Раздел открытый: материалы можно читать и печатать без входа.",
        "theme": "#7a2e2e",
        "manifest_name": "Родителям — справочник",
        "manifest_short": "Родителям",
        "manifest_description": "Открытые правила для родителей и методики семейных ситуаций.",
        "other": ("family", "Семья"),
    },
}


def _shell(title: str, body: str, contour: str = "family") -> str:
    cfg = PUBLIC_CONTOURS[contour]
    other_slug, other_title = cfg["other"]
    nav = (f'<a href="./">Главная</a>'
           f'<a href="../{other_slug}/">{html.escape(other_title)}</a>'
           f'<a href="../">Наставник</a>')
    page_title = title if title == cfg["brand"] else f"{title} · {cfg['brand']}"
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{cfg['theme']}">
<meta name="description" content="{html.escape(cfg['description'], quote=True)}">
<title>{html.escape(page_title)}</title>
<link rel="stylesheet" href="./static/app.css">
<link rel="manifest" href="./manifest.webmanifest">
<link rel="apple-touch-icon" href="./static/icons/icon-180.png">
</head>
<body class="{contour}">
<header class="top"><a class="brand" href="./">{html.escape(cfg['brand'])}</a><nav>{nav}</nav></header>
<main class="wrap">
{body}
</main>
<script src="./static/app.js" defer></script>
</body>
</html>"""


def build(out_dir: Path | None = None, contour: str = "family") -> Path:
    if contour not in PUBLIC_CONTOURS:
        raise ValueError(f"Неизвестный открытый контур: {contour!r}")
    cfg = PUBLIC_CONTOURS[contour]
    out = Path(out_dir) if out_dir is not None else DOCS / contour
    data = load_contour(contour)
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
        tag = (f'<span class="tag">{html.escape(page["tag"])}</span>'
               if page.get("tag") else "")
        cards.append(
            f'<a class="card" href="./{file_name}">{tag}'
            f'<h2>{html.escape(page["title"])}</h2>'
            f'<p>{html.escape(page["summary"])}</p></a>'
        )
        article = f'<article class="content">{page["html"]}</article>'
        body = (f'<p><a href="./">← К списку</a></p>{article}'
                f'<p><a class="btn" href="./{print_name}">Версия для печати</a></p>')
        (out / file_name).write_text(_shell(page["title"], body, contour), encoding="utf-8")
        print_body = (f'<p class="no-print"><a href="./{file_name}">← К материалу</a></p>'
                      f'{article}<p class="no-print"><button class="btn" data-print type="button">Печать</button></p>')
        (out / print_name).write_text(_shell(page["title"] + " · печать", print_body, contour), encoding="utf-8")
        cached += [f"./{file_name}", f"./{print_name}"]

    home = (f"<h1>{html.escape(cfg['title'])}</h1>"
            f"<p class='lead'>{html.escape(cfg['lead'])}</p>"
            f"<div class='cards'>{''.join(cards)}</div>")
    (out / "index.html").write_text(_shell(cfg["title"], home, contour), encoding="utf-8")

    manifest = {
        "id": "./", "name": cfg["manifest_name"], "short_name": cfg["manifest_short"],
        "description": cfg["manifest_description"],
        "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": "#f4f1ea", "theme_color": cfg["theme"], "lang": "ru",
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
    cache_prefix = f"{contour}-public-"
    cache_name = cache_prefix + digest.hexdigest()[:12]
    sw = """const CACHE = __CACHE__;
const FILES = __FILES__;
const BASE = new URL('./', location);
const INDEX = new URL('./index.html', BASE).href;
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith(__PREFIX__) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
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
""".replace("__CACHE__", json.dumps(cache_name)).replace("__FILES__", json.dumps(cached)).replace("__PREFIX__", json.dumps(cache_prefix))
    (out / "sw.js").write_text(sw, encoding="utf-8")
    return out


def build_all(docs_dir: Path | None = None) -> list[Path]:
    docs = Path(docs_dir) if docs_dir is not None else DOCS
    return [build(docs / contour, contour) for contour in PUBLIC_CONTOURS]


if __name__ == "__main__":
    for path in build_all():
        print(f"Открытый справочник: {path}")
