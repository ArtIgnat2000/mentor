"""Контент семейного справочника.

Семейный контур читает только content/family.
Родительский контур читает content/parents и выдаётся только после входа.
"""
from __future__ import annotations

import json
from pathlib import Path

from build_site import md_to_html
from family_rules import (
    CHILDREN_RULES, ADULT_CRISIS, ADULT_REPAIR, ADULT_RED_FLAGS, ROLE_META,
)

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"


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


def _render_source(contour: str, source: str) -> str:
    if source == "generated:children":
        return md_to_html(_children_md())
    if source == "generated:dad":
        return md_to_html(_adult_md("dad"))
    if source == "generated:mom":
        return md_to_html(_adult_md("mom"))
    path = CONTENT / contour / source
    if not path.is_file():
        raise FileNotFoundError(path)
    return md_to_html(path.read_text(encoding="utf-8"))


def load_contour(contour: str) -> dict:
    if contour not in ("family", "parents"):
        raise ValueError(contour)
    index_path = CONTENT / contour / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    pages = []
    for item in index["pages"]:
        pages.append({
            "slug": item["slug"],
            "title": item["title"],
            "summary": item.get("summary", ""),
            "tag": item.get("tag", ""),
            "html": _render_source(contour, item["source"]),
        })
    return {"title": index.get("title", contour), "pages": pages}


def find_page(contour: str, slug: str) -> dict | None:
    data = load_contour(contour)
    for page in data["pages"]:
        if page["slug"] == slug:
            return page
    return None
