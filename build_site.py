#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка карманного свода наставника — версия 2.
Главное отличие от v1: навигация и аккордеоны работают БЕЗ JavaScript
(CSS :target + нативные <details>), поэтому файл полноценно работает
на iPhone даже когда открыт через «Файлы» (там JS не выполняется).

JS остаётся только как улучшение: поиск + авто-раскрытие раздела по ссылке.

Выход:
  docs/index.html      — то, что публикуется на GitHub Pages (Settings → Pages → /docs)
  nastavnik.html       — та же страница одним файлом в корне (удобно переслать в «Файлы» на iPhone)
"""
import re
import html
import json
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"

# Адрес страницы на GitHub Pages. Нужен только для ссылок на печатные PDF:
# абсолютная ссылка работает и из одиночного файла nastavnik.html, открытого в «Файлах».
PAGES_URL = "https://artignat2000.github.io/mentor/"

# Печатные материалы: (файл в docs/print/, подпись). Собирает build_print.py.
PRINT_FILES = [
    ("00_komplekt_na_pechat.pdf", "Весь комплект одним файлом — обложка и все листы"),
    ("01_na_holodilnik_A4.pdf",  "Пять правил, стоп-лист, три фразы — на холодильник"),
    ("01b_na_holodilnik_A5_2up.pdf", "То же в размере A5 — два экземпляра на листе"),
    ("02_karta_utra.pdf",        "Карта утра — на месяц (по одной на каждого мальчика)"),
    ("03_karta_pauzy.pdf",       "Карта паузы — 2 карточки на лист"),
    ("04_shkala_1_5.pdf",        "Шкала 1–5 — 2 карточки на лист"),
    ("05_zhurnal_nastavnika.pdf", "Журнал наставника — на месяц встреч"),
    ("06_kopilka_dobryh_del.pdf", "Копилка добрых дел — на месяц"),
    ("07_proverka_ya_sbilsya.pdf", "7 вопросов «я не сбился» — на две недели"),
    ("08_pamyatka_pape.pdf",     "Памятка папе"),
    ("09_pamyatka_mame.pdf",     "Памятка маме"),
]

DOCS = [
    {"file": "01_pravila_nastavnika.md",      "tab": "Правила",     "icon": "📏", "prefix": "r",  "pane": "r",  "open": False},
    {"file": "02_protokoly_tipovyh_situaciy.md", "tab": "Протоколы", "icon": "🧭", "prefix": "p",  "pane": "p",  "open": True},
    {"file": "03_plan_90_dney.md",            "tab": "План 90 дней", "icon": "📅", "prefix": "pl", "pane": "pl", "open": False},
    {"file": "koncepciya_nastavnichestva_v1.md", "tab": "Концепция", "icon": "🎯", "prefix": "k",  "pane": "k",  "open": False},
]


# ------------------------------------------------------------------ inline md
def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?![\*\w])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r"(?<![=\"(>])(https?://[^\s<)]+)",
               r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)
    return t


# ------------------------------------------------------------------ block md
def md_to_html(md: str) -> str:
    lines, out, i = md.split("\n"), [], 0
    while i < len(lines):
        s = lines[i].strip()

        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            head = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</tbody></table>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", lines[i])
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
            i += 1
            continue

        if re.match(r"^-{3,}$", s):
            out.append("<hr>")
            i += 1
            continue

        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(buf))}</blockquote>")
            continue

        if re.match(r"^[-*]\s+", s):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue

        if re.match(r"^\d+\.\s+", s):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue

        if not s:
            i += 1
            continue

        buf = []
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^(#{1,6}\s|[-*]\s|\d+\.\s|>|\|)", lines[i].strip())
               and not re.match(r"^-{3,}$", lines[i].strip())):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")
    return "\n".join(out)


# ------------------------------------------------------------------ structure
def split_sections(md: str):
    lines = md.split("\n")
    intro, sections, cur_t, cur_l = [], [], None, []
    for line in lines:
        if line.startswith("## "):
            if cur_t is not None:
                sections.append((cur_t, "\n".join(cur_l)))
            elif cur_l:
                intro.append("\n".join(cur_l))
            cur_t, cur_l = line[3:].strip(), []
        elif line.startswith("# "):
            continue
        else:
            cur_l.append(line)
    if cur_t is not None:
        sections.append((cur_t, "\n".join(cur_l)))
    elif cur_l:
        intro.append("\n".join(cur_l))
    return "\n".join(intro).strip(), sections


def slug(title: str, prefix: str, idx: int, used: set) -> str:
    base = None
    m = re.match(r"[ПP](\d+)", title)
    if m:
        base = "p" + m.group(1)
    if base is None:
        m = re.match(r"Раздел\s+(\d+)", title)
        if m:
            base = prefix + m.group(1)
    if base is None:
        m = re.match(r"(\d+)\.", title)
        if m:
            base = prefix + m.group(1)
    if base is None:
        base = f"{prefix}-x{idx}"
    cand, n = base, 2
    while cand in used:
        cand, n = f"{base}-{n}", n + 1
    used.add(cand)
    return cand


def short_title(title: str) -> str:
    t = re.sub(r"^(Раздел|П)\s*", lambda m: "", title)
    return re.sub(r"^\d+\.\s*", "", t)


def refresh_sw_version(page: str):
    """Переписывает версию кэша в docs/sw.js под текущее содержимое страницы.

    Сам файл создаёт make_pack.py; здесь только поддерживается актуальная версия,
    чтобы сборку можно было повторять без Pillow (CI собирает страницу из markdown).
    """
    sw = OUT / "sw.js"
    if not sw.exists():
        return None
    version = "nastavnik-" + hashlib.sha256(page.encode("utf-8")).hexdigest()[:10]
    text = sw.read_text(encoding="utf-8")
    new = re.sub(r"const CACHE = '[^']*';", f"const CACHE = '{version}';", text, count=1)
    if new != text:
        sw.write_text(new, encoding="utf-8")
    return version if new != text else None


# ------------------------------------------------------------------ build
def build():
    used_ids = set()
    panes_html, tabs_html, toc_data, search_index = [], [], {}, []

    for d in DOCS:
        md = (ROOT / d["file"]).read_text(encoding="utf-8")
        intro_md, sections = split_sections(md)

        blocks, toc = [], []
        if intro_md:
            blocks.append(f'<section class="card card--intro">{md_to_html(intro_md)}</section>')

        for idx, (title, body) in enumerate(sections, start=1):
            sid = slug(title, d["prefix"], idx, used_ids)
            body_html = md_to_html(body)
            blocks.append(
                f'<details class="card card--fold" id="{sid}"' + (" open" if d["open"] else "") + ">"
                f'<summary><span class="sum-t">{inline(title)}</span><span class="chev" aria-hidden="true"></span></summary>'
                f'<div class="fold-body">{body_html}</div></details>'
            )
            toc.append((sid, title))
            search_index.append({
                "id": sid, "pane": d["pane"], "doc": d["tab"],
                "title": title,
                "text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_html)).strip().lower()[:1500],
            })

        if len(toc) > 1:
            chips = "".join(
                f'<a class="chip" href="#{sid}">{html.escape(short_title(t)[:44])}</a>'
                for sid, t in toc
            )
            blocks.insert(0, f'<nav class="toc"><span class="toc-h">Содержание</span>{chips}</nav>')

        panes_html.append(
            f'<section class="pane" id="{d["pane"]}">'
            f'<h1 class="doc-title">{d["icon"]} {d["tab"]}</h1>'
            + "\n".join(blocks)
            + '<p class="totop"><a href="#top">↑ Наверх</a></p></section>'
        )
        tabs_html.append(
            f'<a class="tab" href="#{d["pane"]}"><span class="tab-ico">{d["icon"]}</span>{d["tab"]}</a>'
        )

    tabs_html.insert(0, '<a class="tab" href="#home"><span class="tab-ico">⚡</span>Главное</a>')

    home = """
<section class="pane pane--home" id="home">
  <h1 class="doc-title">Моё главное</h1>
  <p class="lead">Карманный свод. Работает без интернета и без JavaScript — открывается даже из «Файлов» на iPhone.</p>

  <section class="card card--intro">
    <h2>Пять правил, которые важнее остальных</h2>
    <ol class="big-list">
      <li>Я никогда не сравниваю братьев — ни в минус, ни в плюс.</li>
      <li>В момент аффекта я не воспитываю: только безопасность, присутствие, ровный голос.</li>
      <li>После срыва обязателен ремонт: вернуться, назвать, извиниться, договориться.</li>
      <li>У каждого мальчика есть нераздельное время со мной — и оно не отменяется.</li>
      <li>Моё слово — закон, потому что я его держу.</li>
    </ol>
  </section>

  <h2 class="sect-h">Если прямо сейчас</h2>
  <div class="quick">
    <a class="q q--hot" href="#p1">😤 Истерика / вспышка старшего</a>
    <a class="q" href="#p2">💔 «Мама любит его больше»</a>
    <a class="q" href="#p3">⚔️ Ссора: «кто прав?»</a>
    <a class="q" href="#p4">📢 Младший подхватил крик</a>
    <a class="q" href="#p5">📉 «У меня не получится»</a>
    <a class="q" href="#p6">🙅 Отказ от дела</a>
    <a class="q" href="#p8">📚 Домашнее задание рядом</a>
    <a class="q" href="#p10">📞 Папа позвонил: «плохой день»</a>
    <a class="q" href="#p11">🪞 Я сам сорвался</a>
  </div>

  <h2 class="sect-h">Коротко о системе</h2>
  <div class="flow">
    <div class="flow-item"><b>РИТМ</b><span>порядок дня держит папа, я — свидетель и голос</span></div>
    <div class="flow-item"><b>ПАУЗА</b><span>эмоции законны, последствия — у поступков</span></div>
    <div class="flow-item"><b>ПОСТУПОК</b><span>«сделал сам, и это кому-то нужно»</span></div>
  </div>

  <h2 class="sect-h">Первый шаг на этой неделе</h2>
  <ol class="big-list">
    <li>Позвонить папе и договориться о разговоре в <b>спокойное</b> время: три результата, роли, конфиденциальность, день еженедельной сверки.</li>
    <li>Первая встреча с мальчиками — <b>просто хорошее время</b>, без воспитания. И один разговор о роли: «наши встречи — не занятия, я вас здесь не оцениваю».</li>
    <li>Завести журнал из трёх строк.</li>
  </ol>

  <div class="warn">
    <b>Стоп-лист (никогда):</b> не кричать · не наказывать · не сравнивать · не обещать зря ·
    не стыдить за чувства и за маму · не занимать место папы · не разбирать конфликт в момент аффекта ·
    не делать за ребёнка.
  </div>

  <h2 class="sect-h">Разделы</h2>
  <div class="quick">
    <a class="q" href="#r">📏 Правила наставника</a>
    <a class="q" href="#p">🧭 Протоколы ситуаций</a>
    <a class="q" href="#pl">📅 План на 90 дней</a>
    <a class="q" href="#k">🎯 Концепция</a>
  </div>

  __PRINT__
  <p class="totop"><a href="#top">↑ Наверх</a></p>
</section>
"""

    # печатные материалы — ссылки только на реально собранные файлы
    links = [
        (name, label) for name, label in PRINT_FILES
        if (OUT / "print" / name).exists()
    ]
    if links:
        print_block = (
            '<h2 class="sect-h">Печатные материалы</h2>'
            '<div class="print-list">'
            + "".join(
                f'<a class="pdf" href="{PAGES_URL}print/{name}">'
                f'<span class="pdf-ico" aria-hidden="true">🖨</span>'
                f'<span class="pdf-t">{html.escape(label)}</span></a>'
                for name, label in links
            )
            + "</div>"
            '<p class="pdf-note">Открываются в Safari, оттуда — «Печать» или сохранить в «Файлы». '
            'Печатать на A4, без масштабирования (100%).</p>'
        )
    else:
        print_block = ""

    home = home.replace("__PRINT__", print_block)

    CSS = """
  :root{--bg:#f4f1ea;--card:#fffdf8;--ink:#1c2321;--muted:#6b7570;--accent:#16302b;
        --accent2:#2f6b5b;--line:#ddd6c8;--hot:#b4472e;--gold:#b58a2b;--r:16px;}
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
  html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
       padding-bottom:calc(78px + env(safe-area-inset-bottom));}
  header{position:sticky;top:0;z-index:20;background:var(--accent);color:#f4f1ea;
         padding:10px 14px;box-shadow:0 2px 10px rgba(0,0,0,.18);}
  .hd-title{font-size:15px;font-weight:650;letter-spacing:.02em;}
  .hd-sub{font-size:11.5px;opacity:.62;margin-top:1px;}
  .search{margin-top:9px;position:relative;display:none;}
  html.js .search{display:block;}
  .search input{width:100%;padding:11px 38px 11px 13px;border-radius:11px;border:none;font-size:16px;
                background:#0e211d;color:#f4f1ea;outline:none;}
  .search input::placeholder{color:#8fa39c;}
  .search .x{position:absolute;right:6px;top:50%;transform:translateY(-50%);background:none;border:none;
             color:#8fa39c;font-size:20px;padding:6px 10px;cursor:pointer;display:none;}
  main{padding:14px 12px 30px;max-width:760px;margin:0 auto;}

  /* ---- навигация на чистом CSS ---- */
  .pane{display:none;scroll-margin-top:84px;}
  .pane:target{display:block;}
  #home{display:block;}
  body:has(#r :target) #home, body:has(#p :target) #home,
  body:has(#pl :target) #home, body:has(#k :target) #home,
  body:has(#r:target) #home, body:has(#p:target) #home,
  body:has(#pl:target) #home, body:has(#k:target) #home{display:none;}
  body:has(#r :target) #r, body:has(#r:target) #r,
  body:has(#p :target) #p, body:has(#p:target) #p,
  body:has(#pl :target) #pl, body:has(#pl:target) #pl,
  body:has(#k :target) #k, body:has(#k:target) #k{display:block;}
  #home:target{display:block;}

  .doc-title{font-size:22px;margin:6px 0 12px;letter-spacing:-.01em;}
  .lead{color:var(--muted);font-size:14.5px;margin:-4px 0 16px;}
  .sect-h{font-size:14px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
          margin:24px 0 10px;font-weight:700;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:14px 15px;
        margin:0 0 10px;box-shadow:0 1px 2px rgba(28,35,33,.04);}
  .card--intro{background:#fffefa;border-color:#cdbf9f;}
  details.card{padding:0;overflow:hidden;scroll-margin-top:78px;}
  details.card summary{list-style:none;cursor:pointer;padding:14px 44px 14px 15px;position:relative;
                       font-weight:650;font-size:16px;line-height:1.35;display:block;}
  details.card summary::-webkit-details-marker{display:none;}
  .chev{position:absolute;right:15px;top:50%;width:9px;height:9px;margin-top:-6px;
        border-right:2px solid var(--accent2);border-bottom:2px solid var(--accent2);
        transform:rotate(45deg);transition:transform .18s ease;}
  details[open] .chev{transform:rotate(-135deg);margin-top:-3px;}
  details[open] summary{background:#f7f3e9;border-bottom:1px solid var(--line);}
  details.card:target{box-shadow:0 0 0 3px rgba(181,138,43,.55);}
  .fold-body{padding:12px 15px 14px;}
  .fold-body>:first-child{margin-top:0;}
  .fold-body>:last-child{margin-bottom:0;}
  h2{font-size:18px;margin:0 0 8px;}
  h3{font-size:16px;margin:16px 0 6px;color:var(--accent2);}
  p{margin:0 0 10px;}
  ul,ol{margin:0 0 10px;padding-left:22px;}
  li{margin:0 0 5px;}
  .big-list li{margin-bottom:9px;}
  table{width:100%;border-collapse:collapse;font-size:14.5px;margin:6px 0 12px;}
  th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top;}
  th{background:#f2eee2;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);}
  blockquote{margin:10px 0;padding:10px 12px;border-left:3px solid var(--gold);background:#faf6ea;
             border-radius:0 8px 8px 0;font-size:15.5px;}
  code{background:#eee8db;padding:1px 5px;border-radius:5px;font-size:14px;}
  a{color:var(--accent2);}
  hr{border:none;border-top:1px solid var(--line);margin:16px 0;}

  .toc{background:#efeade;border:1px solid var(--line);border-radius:14px;padding:10px 11px;margin:0 0 12px;}
  .toc-h{display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.08em;
         color:var(--muted);font-weight:700;margin-bottom:7px;}
  .chip{display:inline-block;background:#fffdf8;border:1px solid var(--line);border-radius:20px;
        padding:6px 11px;margin:0 5px 5px 0;font-size:13.5px;color:var(--ink);text-decoration:none;}
  .chip:active{background:#e8e1d0;}

  .quick{display:grid;grid-template-columns:1fr;gap:8px;}
  .q{display:block;text-decoration:none;font-size:15.5px;font-weight:600;color:var(--ink);
     background:var(--card);border:1px solid var(--line);border-radius:13px;padding:14px;line-height:1.35;}
  .q:active{background:#f0ebdd;}
  .q--hot{border-color:#e0b6a8;background:#fdf2ee;color:#7d2c1a;}
  .flow{display:grid;gap:8px;}
  .flow-item{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent2);
             border-radius:10px;padding:10px 12px;font-size:15px;}
  .flow-item b{display:block;font-size:12px;letter-spacing:.09em;color:var(--accent2);}
  .flow-item span{color:var(--muted);}
  .warn{margin-top:16px;background:#fdf2ee;border:1px solid #e0b6a8;color:#7d2c1a;
        border-radius:13px;padding:12px 14px;font-size:15px;}
  .totop{margin:18px 0 4px;text-align:center;font-size:14px;}

  nav#nav{position:fixed;bottom:0;left:0;right:0;z-index:30;display:flex;background:#10312c;
          padding:6px 4px calc(6px + env(safe-area-inset-bottom));box-shadow:0 -2px 12px rgba(0,0,0,.22);}
  .tab{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;text-decoration:none;
       color:#9fb4ad;font-size:10.5px;font-weight:600;padding:6px 2px 4px;border-radius:10px;line-height:1.15;
       text-align:center;}
  .tab-ico{font-size:19px;line-height:1;}
  .tab:active{background:rgba(255,255,255,.10);}
  /* «Главное» активно по умолчанию */
  .tab[href="#home"]{color:#fff;background:rgba(255,255,255,.09);}
  /* активная вкладка текущего раздела */
  body:has(#r :target) .tab[href="#r"], body:has(#r:target) .tab[href="#r"],
  body:has(#p :target) .tab[href="#p"], body:has(#p:target) .tab[href="#p"],
  body:has(#pl :target) .tab[href="#pl"], body:has(#pl:target) .tab[href="#pl"],
  body:has(#k :target) .tab[href="#k"], body:has(#k:target) .tab[href="#k"],
  body:has(#home:target) .tab[href="#home"]{color:#fff;background:rgba(255,255,255,.09);}
  /* снимаем подсветку «Главное», когда открыт другой раздел */
  body:has(#r :target) .tab[href="#home"], body:has(#r:target) .tab[href="#home"],
  body:has(#p :target) .tab[href="#home"], body:has(#p:target) .tab[href="#home"],
  body:has(#pl :target) .tab[href="#home"], body:has(#pl:target) .tab[href="#home"],
  body:has(#k :target) .tab[href="#home"], body:has(#k:target) .tab[href="#home"]{color:#9fb4ad;background:none;}

  .print-list{display:grid;gap:8px;}
  .pdf{display:flex;align-items:flex-start;gap:10px;text-decoration:none;color:var(--ink);
       background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 13px;
       font-size:15px;line-height:1.35;}
  .pdf:active{background:#f0ebdd;}
  .pdf-ico{font-size:16px;line-height:1.3;}
  .pdf-t{flex:1;}
  .pdf-note{color:var(--muted);font-size:13.5px;margin:8px 0 0;}

  .nores{text-align:center;color:var(--muted);padding:30px 10px;display:none;}
  @media (min-width:700px){.quick{grid-template-columns:1fr 1fr;}.print-list{grid-template-columns:1fr 1fr;}}
"""

    JS = """
(function(){
  document.documentElement.classList.add('js');
  var SEARCH = __SEARCH__;
  var cards = function(){ return [].slice.call(document.querySelectorAll('details.card')); };
  var qInput = document.getElementById('q');
  var qx = document.getElementById('qx');
  var nores = document.getElementById('nores');
  var userOpened = {};

  // 1) авто-раскрытие раздела, на который пришли по ссылке
  function openHash(){
    var h = decodeURIComponent(location.hash.replace('#',''));
    if(!h) return;
    var el = document.getElementById(h);
    if(el && el.tagName === 'DETAILS'){ el.open = true; }
  }
  window.addEventListener('hashchange', openHash);
  openHash();

  // 2) поиск
  function reset(){
    qx.style.display='none'; nores.style.display='none';
    cards().forEach(function(c){
      c.style.display='';
      if(c.id && !userOpened[c.id]) c.open = false;
    });
    // вернуть протоколы в открытое состояние
    document.querySelectorAll('#p details.card').forEach(function(c){ c.open = true; });
  }
  function run(raw){
    var q = raw.trim().toLowerCase();
    qx.style.display = q ? 'block':'none';
    if(q.length < 2){ reset(); return; }
    var words = q.split(/\\s+/).filter(function(w){ return w.length>1; });
    var hits = 0;
    cards().forEach(function(c){
      var meta = null;
      for(var i=0;i<SEARCH.length;i++){ if(SEARCH[i].id === c.id){ meta = SEARCH[i]; break; } }
      var hay = ((meta ? meta.title+' '+meta.text : '')+' '+(c.dataset.title||'')).toLowerCase();
      var ok = words.every(function(w){ return hay.indexOf(w) >= 0; });
      c.style.display = ok ? '':'none';
      if(ok){ c.open = true; hits++; }
    });
    nores.style.display = hits ? 'none':'block';
    if(hits){ window.scrollTo({top:0}); }
  }
  var deb;
  qInput.addEventListener('input', function(e){
    clearTimeout(deb);
    deb = setTimeout(function(){ run(e.target.value); }, 140);
  });
  qx.addEventListener('click', function(){ qInput.value=''; reset(); qInput.blur(); });

  // 3) офлайн-кэш (только на хостинге, не мешает локальному файлу)
  if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
    window.addEventListener('load', function(){
      navigator.serviceWorker.register('sw.js').catch(function(){});
    });
  }

  document.addEventListener('toggle', function(e){
    var d = e.target;
    if(d.tagName === 'DETAILS' && d.id){ userOpened[d.id] = d.open; }
  }, true);
})();
"""

    page = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#16302b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Наставник">
<title>Наставник · карманный свод</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<style>__CSS__</style>
</head>
<body>
<a id="top"></a>
<header>
  <div class="hd-title">Наставник · карманный свод</div>
  <div class="hd-sub">8 и 10 лет · ритм — пауза — поступок</div>
  <div class="search">
    <input id="q" type="search" placeholder="Поиск: истерика, ревность, турник…" autocomplete="off">
    <button class="x" id="qx" aria-label="Очистить">×</button>
  </div>
</header>

<main>
__HOME__
__PANES__
<div class="nores" id="nores">Ничего не нашлось. Попробуйте другое слово.</div>
</main>

<nav id="nav">__TABS__</nav>
<script>__JS__</script>
</body>
</html>
"""
    page = (page.replace("__CSS__", CSS).replace("__HOME__", home)
                .replace("__PANES__", "\n".join(panes_html))
                .replace("__TABS__", "\n".join(tabs_html))
                .replace("__SEARCH__", json.dumps(search_index, ensure_ascii=False)))

    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copy(OUT / "index.html", ROOT / "nastavnik.html")
    # .nojekyll: без него GitHub Pages прогоняет файлы через Jekyll
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    # версия офлайн-кэша: обновляется здесь, чтобы страницу можно было пересобрать
    # без Pillow (например, в GitHub Actions) и телефон не показывал старую копию
    version = refresh_sw_version(page)
    extra = f", кэш {version}" if version else ""
    print(f"ok: docs/index.html = {len(page)} bytes, разделов: {len(search_index)}{extra}")


if __name__ == "__main__":
    build()
