"""Контент открытых справочников «Детям», «Семья», «Родителям».

Тексты лежат в markdown, списки страниц — в index.json. Правила детей и
взрослых собираются из family_rules.py, чтобы сайт и PDF не расходились.
Статическая публикация открыта; серверный режим родительского контура может
требовать входа, но не делает секретными уже опубликованные материалы.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from build_site import md_to_html, split_sections
from family_rules import (
    CHILDREN_RULES, ADULT_CRISIS, ADULT_REPAIR, ADULT_RED_FLAGS, ROLE_META,
)

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
CONTOURS = ("children", "family", "parents")


def _children_md() -> str:
    lines = ["# Наши правила", "", "Для всех детей в доме. Правило одно для всех; взрослый помогает его держать.", ""]
    for rule, can, cannot in CHILDREN_RULES:
        lines += [f"## {rule}", "", f"**Можно:** {can}", "", f"**Нельзя:** {cannot}", ""]
    lines += ["> Пропустил — вернись. Ошибка — повод исправить, а не повод стыдиться. Листы братьев не сравниваем.", ""]
    return "\n".join(lines)


def _adult_md(role: str) -> str:
    meta = ROLE_META[role]
    data = meta["data"]
    lines = [f"# {meta['title']}", "", meta["subtitle"], ""]
    for title, key in (("НУЖНО — держу постоянно", "need"),
                       ("МОЖНО — это не слабость", "can"),
                       ("НЕЛЬЗЯ — стоп-лист", "cannot")):
        lines += [f"## {title}", ""]
        lines += [f"- {item}" for item in data[key]]
        lines.append("")
    lines += ["## При вспышке — один порядок", "", ADULT_CRISIS, "",
              "## Короткие фразы", "", data["phrases"], "",
              "## Если сорвался взрослый", ""]
    lines += [f"- {item}" for item in ADULT_REPAIR]
    lines += ["", ADULT_RED_FLAGS, ""]
    return "\n".join(lines)


def _safe_source(source: str) -> str:
    if source.startswith("generated:"):
        return source
    path = Path(source)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
        raise ValueError(f"Небезопасный источник: {source!r}")
    return source


def _situations() -> tuple[str, list[dict]]:
    md = (CONTENT / "parents" / "situacii.md").read_text(encoding="utf-8")
    intro, sections = split_sections(md)
    parts = [f"<h1>Типовые ситуации</h1>{md_to_html(intro)}"]
    entries = []
    for idx, (title, body) in enumerate(sections, 1):
        match = re.match(r"[ПP](\d+)", title)
        sid = f"s{match.group(1)}" if match else f"s{idx}"
        body_html = md_to_html(body)
        plain = re.sub(r"<[^>]+>", " ", body_html)
        plain = re.sub(r"\s+", " ", plain).strip()
        summary = plain[:150].rsplit(" ", 1)[0] + "…" if len(plain) > 150 else plain
        parts.append(
            f'<details class="scenario" id="{sid}" data-scenario>'
            f'<summary><span>{html.escape(title)}</span><span class="chev" aria-hidden="true">⌄</span></summary>'
            f'<div class="scenario-body">{body_html}</div></details>'
        )
        entries.append({"id": sid, "title": title, "summary": summary, "text": plain.lower()})
    return "\n".join(parts), entries


def _render_source(contour: str, source: str) -> tuple[str, list[dict]]:
    source = _safe_source(source)
    if source == "generated:children":
        return md_to_html(_children_md()), []
    if source == "generated:dad":
        return md_to_html(_adult_md("dad")), []
    if source == "generated:mom":
        return md_to_html(_adult_md("mom")), []
    if source == "generated:situations":
        if contour != "parents":
            raise ValueError("Ситуации доступны только в родительском контуре")
        return _situations()
    path = CONTENT / contour / source
    if not path.is_file():
        raise FileNotFoundError(path)
    return md_to_html(path.read_text(encoding="utf-8")), []


def _resources(items: list[dict]) -> list[dict]:
    out = []
    for item in items or []:
        href = item.get("href", "")
        if not href or href.startswith(("/", "http:", "https:", "javascript:")) or "\\" in href:
            raise ValueError(f"Небезопасная ссылка на материал: {href!r}")
        out.append({
            "label": item.get("label", href),
            "href": href,
            "note": item.get("note", ""),
            "kind": item.get("kind", "Материал"),
        })
    return out


def load_contour(contour: str) -> dict:
    if contour not in CONTOURS:
        raise ValueError(contour)
    index_path = CONTENT / contour / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    pages = []
    seen = set()
    for item in index["pages"]:
        slug = item["slug"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug) or slug in seen:
            raise ValueError(f"Небезопасный или повторяющийся slug: {slug!r}")
        seen.add(slug)
        page_html, entries = _render_source(contour, item["source"])
        pages.append({
            "slug": slug,
            "title": item["title"],
            "summary": item.get("summary", ""),
            "tag": item.get("tag", ""),
            "group": item.get("group", "Материалы"),
            "icon": item.get("icon", "📄"),
            "keywords": item.get("keywords", []),
            "resources": _resources(item.get("resources", [])),
            "entries": entries,
            "html": page_html,
        })
    return {"title": index.get("title", contour), "pages": pages}


def find_page(contour: str, slug: str) -> dict | None:
    data = load_contour(contour)
    for page in data["pages"]:
        if page["slug"] == slug:
            return page
    return None
