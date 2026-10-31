"""Сборка открытых разделов для GitHub Pages.

Публикуются «Детям», «Семья» и «Родителям». Все разделы доступны без входа.
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
    "children": {
        "brand": "Детям",
        "title": "Мой раздел",
        "description": "Детский раздел: правила, подсказки на трудный день, ритм дня и материалы для печати.",
        "lead": "Привет! Здесь твои правила, дела и подсказки на трудный день. Можно читать с телефона, печатать листы и отмечать своё.",
        "theme": "#2563eb",
        "manifest_name": "Детям — мой раздел",
        "manifest_short": "Детям",
        "manifest_description": "Правила, подсказки и листы для детей.",
        "nav": (("parents", "Родителям"), ("family", "Семья")),
        "group_order": ["Правила", "Когда трудно", "Мой день", "Мои материалы"],
    },
    "family": {
        "brand": "Семья",
        "title": "Семейный справочник",
        "description": "Общие семейные правила и материалы, которые можно показывать детям.",
        "lead": "Общие правила и материалы, которые можно показывать детям. Без оценок, рейтингов и сравнения.",
        "theme": "#16302b",
        "manifest_name": "Семья — правила",
        "manifest_short": "Семья",
        "manifest_description": "Общие семейные правила и материалы для детей и родителей.",
        "nav": (("children", "Детям"), ("parents", "Родителям")),
        "group_order": ["Начало", "Правила"],
    },
    "parents": {
        "brand": "Родителям",
        "title": "Родителям",
        "description": "Справочник для родителей: правила, типовые ситуации, печатные формы, инструкции и примеры анализа.",
        "lead": "Правила, готовые фразы и листы на каждый день. Откройте нужное за пару секунд: ситуацию, правило или печатную форму.",
        "theme": "#7a2e2e",
        "manifest_name": "Родителям — справочник",
        "manifest_short": "Родителям",
        "manifest_description": "Правила, ситуации и печатные формы для родителей.",
        "nav": (("children", "Детям"), ("family", "Семья")),
        "group_order": ["Начало", "Правила", "Ситуации", "Печатные формы", "Методики"],
    },
}


def _esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def _shell(title: str, body: str, contour: str = "family") -> str:
    cfg = PUBLIC_CONTOURS[contour]
    nav = '<a href="./">Главная</a>' + "".join(
        f'<a href="../{slug}/">{_esc(label)}</a>' for slug, label in cfg["nav"]
    )
    page_title = title if title == cfg["brand"] else f"{title} · {cfg['brand']}"
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{cfg['theme']}">
<meta name="description" content="{_esc(cfg['description'])}">
<title>{_esc(page_title)}</title>
<link rel="stylesheet" href="./static/app.css">
<link rel="manifest" href="./manifest.webmanifest">
<link rel="apple-touch-icon" href="./static/icons/icon-180.png">
</head>
<body class="{contour}">
<a class="skip-link" href="#main">К содержанию</a>
<header class="top"><a class="brand" href="./">{_esc(cfg['brand'])}</a><nav aria-label="Разделы">{nav}</nav></header>
<main class="wrap" id="main">
{body}
</main>
<footer class="foot no-print"><a href="../">Наставник · полный свод</a></footer>
<script src="./static/app.js" defer></script>
</body>
</html>"""


def _resources_html(resources: list[dict]) -> str:
    if not resources:
        return ""
    items = []
    for item in resources:
        note = f'<span class="resource-note">{_esc(item["note"])}</span>' if item.get("note") else ""
        items.append(
            f'<a class="resource" href="{_esc(item["href"])}" target="_blank" rel="noopener">'
            f'<span class="resource-kind">{_esc(item.get("kind", "PDF"))}</span>'
            f'<span class="resource-label">{_esc(item["label"])}{note}</span>'
            f'<span class="resource-arrow" aria-hidden="true">↗</span></a>'
        )
    return f'<section class="resources no-print" aria-label="Материалы"><h2>Материалы</h2>{"".join(items)}</section>'


def _card(href: str, title: str, summary: str, icon: str = "📄", tag: str = "",
          group: str = "", keywords: list[str] | None = None, extra_class: str = "") -> str:
    tag_html = f'<span class="tag">{_esc(tag)}</span>' if tag else ""
    keys = " ".join(keywords or [])
    return (
        f'<a class="card search-item {extra_class}" href="{_esc(href)}" data-group="{_esc(group)}" data-keywords="{_esc(keys)}">'
        f'<span class="card-icon" aria-hidden="true">{_esc(icon)}</span>{tag_html}'
        f'<h3>{_esc(title)}</h3><p>{_esc(summary)}</p></a>'
    )


def _search_box(placeholder: str, target: str = ".search-item") -> str:
    return f"""
<div class="search-box no-print">
  <label class="sr-only" for="site-search">Поиск по разделу</label>
  <input id="site-search" type="search" data-search data-search-target="{target}" placeholder="{_esc(placeholder)}" autocomplete="off">
  <button class="search-clear" type="button" data-search-clear aria-label="Очистить поиск">×</button>
</div>
<p class="no-results" data-no-results hidden>Ничего не нашлось. Попробуйте другое слово: «истерика», «турник», «добрые дела».</p>
"""


def _filters(groups: list[str]) -> str:
    chips = ['<button class="chip is-active" type="button" data-filter="all">Все</button>']
    chips += [f'<button class="chip" type="button" data-filter="{_esc(g)}">{_esc(g)}</button>' for g in groups]
    return f'<div class="chips no-print" role="group" aria-label="Фильтр по темам">{"".join(chips)}</div>'


def _home(contour: str, data: dict) -> str:
    cfg = PUBLIC_CONTOURS[contour]
    parts = []
    if contour == "children":
        parts.append(f"""
<section class="hero hero-kids">
  <div class="hero-text"><p class="eyebrow">Твой раздел</p><h1>{_esc(cfg['title'])}</h1><p class="lead">{_esc(cfg['lead'])}</p></div>
  <img class="hero-art" src="./static/kids-hero.svg" alt="" width="220" height="160">
</section>
<div class="quick quick-kids">
  <a class="quick-card" href="./nashi-pravila.html"><span aria-hidden="true">📏</span><strong>Мои правила</strong></a>
  <a class="quick-card" href="./esli-trudno.html"><span aria-hidden="true">🌤️</span><strong>Если трудно</strong></a>
  <a class="quick-card" href="./moy-den.html"><span aria-hidden="true">🧭</span><strong>Мой день</strong></a>
  <a class="quick-card" href="./moi-listy.html"><span aria-hidden="true">✏️</span><strong>Мои листы</strong></a>
</div>
{_search_box('Найти: правила, пауза, турник, добрые дела')}
""")
    elif contour == "parents":
        parts.append(f"""
<section class="hero hero-parents"><p class="eyebrow">Семейный инструмент</p><h1>{_esc(cfg['title'])}</h1><p class="lead">{_esc(cfg['lead'])}</p></section>
<div class="quick quick-parents">
  <a class="quick-card urgent" href="./situacii.html"><span aria-hidden="true">💬</span><strong>Сложно прямо сейчас</strong><small>Шаги и фразы</small></a>
  <a class="quick-card" href="#rules"><span aria-hidden="true">📏</span><strong>Освежить правила</strong><small>Взрослым и детям</small></a>
  <a class="quick-card" href="./pechatnye-formy.html"><span aria-hidden="true">🖨️</span><strong>Распечатать лист</strong><small>Инструкция и пример</small></a>
</div>
{_search_box('Найти правило, ситуацию или форму: истерика, турник, добрые дела')}
""")
    else:
        parts.append(f"""
<section class="hero"><h1>{_esc(cfg['title'])}</h1><p class="lead">{_esc(cfg['lead'])}</p></section>
<div class="portal"><a class="portal-card" href="../children/"><span aria-hidden="true">🧒</span><strong>Детский раздел</strong><small>Правила, подсказки и листы</small></a><a class="portal-card" href="../parents/"><span aria-hidden="true">👪</span><strong>Родителям</strong><small>Правила, ситуации и формы</small></a></div>
""")

    groups = {g: [] for g in cfg["group_order"]}
    for page in data["pages"]:
        group = page["group"] if page["group"] in groups else cfg["group_order"][-1]
        groups[group].append(_card(
            f'./{page["slug"]}.html', page["title"], page["summary"],
            page["icon"], page["tag"], group, page["keywords"],
        ))
        if contour == "parents" and page["entries"]:
            for entry in page["entries"]:
                groups[group].append(_card(
                    f'./{page["slug"]}.html#{entry["id"]}', entry["title"], entry["summary"],
                    "💬", "Ситуация", group, [entry["title"], entry["text"]], "card-compact",
                ))

    if contour in ("parents", "children"):
        active_groups = [g for g in cfg["group_order"] if groups[g]]
        parts.append(_filters(active_groups))
    for idx, group in enumerate(cfg["group_order"], 1):
        if not groups[group]:
            continue
        gid = "rules" if group == "Правила" else f"group-{idx}"
        parts.append(f'<section class="group" data-group-section="{_esc(group)}" id="{gid}"><h2>{_esc(group)}</h2><div class="cards">{"".join(groups[group])}</div></section>')
    return "\n".join(parts)


def _page_body(page: dict, contour: str) -> str:
    back = '<p class="back no-print"><a href="./">← К списку</a></p>'
    chips = ""
    if page["entries"]:
        chips = '<nav class="chips no-print" aria-label="Ситуации">' + "".join(
            f'<a class="chip" href="#{_esc(e["id"])}">{_esc(e["title"])}</a>' for e in page["entries"]
        ) + "</nav>" + _search_box("Найти ситуацию: крик, ссора, отказ, гаджет", ".scenario")
    article = f'<article class="content">{page["html"]}</article>'
    resources = _resources_html(page["resources"])
    print_link = f'<p class="no-print"><a class="btn" href="./print-{_esc(page["slug"])}.html">Версия для печати</a></p>'
    return f"{back}{chips}{article}{resources}{print_link}"


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
    shutil.copyfile(ROOT / "static" / "app.js", static / "app.js")
    shutil.copyfile(ROOT / "static" / "kids-hero.svg", static / "kids-hero.svg")
    shutil.copytree(ROOT / "static" / "icons", static / "icons", dirs_exist_ok=True)

    cached = ["./", "./index.html", "./static/app.css", "./static/app.js",
              "./static/kids-hero.svg", "./manifest.webmanifest",
              "./static/icons/icon-192.png", "./static/icons/icon-512.png"]
    for page in data["pages"]:
        slug = page["slug"]
        file_name = f"{slug}.html"
        print_name = f"print-{slug}.html"
        (out / file_name).write_text(_shell(page["title"], _page_body(page, contour), contour), encoding="utf-8")
        printable = page["html"].replace("<details ", "<details open ")
        print_body = (f'<p class="no-print"><a href="./{file_name}">← К материалу</a></p>'
                      f'<article class="content">{printable}</article>'
                      f'<p class="no-print"><button class="btn" data-print type="button">Печать</button></p>')
        (out / print_name).write_text(_shell(page["title"] + " · печать", print_body, contour), encoding="utf-8")
        cached += [f"./{file_name}", f"./{print_name}"]
        for resource in page["resources"]:
            href = resource["href"]
            if href not in cached and (out / href).exists():
                cached.append(href)

    (out / "index.html").write_text(_shell(cfg["title"], _home(contour, data), contour), encoding="utf-8")

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

    digest = hashlib.sha256()
    for name in sorted(set(cached)):
        path = out / name
        if path.is_file() and path.name != "sw.js":
            digest.update(name.encode())
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
  e.respondWith(caches.open(CACHE).then(cache => cache.match(e.request).then(hit => {
    if (hit) return hit;
    if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return fetch(e.request);
    return fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); cache.put(e.request, copy); }
      return res;
    }).catch(() => e.request.mode === 'navigate' ? cache.match(INDEX) : Response.error());
  })));
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
