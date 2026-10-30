#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мини-набор для печатных материалов: шрифты с кириллицей, цвета, вёрстка текста.

Никакой магии: reportlab canvas + свой перенос строк, чтобы одинаково
считать высоту блоков (нужно, чтобы рамки и подложки не наезжали на текст).
"""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

MM = 72 / 25.4          # 1 мм в пунктах
A4W, A4H = A4            # 595.28 × 841.89
A5W, A5H = A4H / 2, A4W  # 420.94 × 595.28

# --------------------------------------------------------------- палитра сайта
INK      = HexColor("#1c2321")
MUTED    = HexColor("#6b7570")
ACCENT   = HexColor("#16302b")
ACCENT2  = HexColor("#2f6b5b")
GOLD     = HexColor("#b58a2b")
LINE     = HexColor("#ddd6c8")
LINE_SOFT= HexColor("#e9e3d5")
DASH     = HexColor("#c6bca7")   # пунктир для письма от руки
HOT      = HexColor("#b4472e")
HOT_BG   = HexColor("#fdf2ee")
GOLD_BG  = HexColor("#faf6ea")
CREAM    = HexColor("#fffdf8")
TINT     = HexColor("#f4f1ea")
PAPER    = HexColor("#ffffff")

# ------------------------------------------------------------------- шрифты
_FONT_CANDIDATES = [
    Path(__file__).resolve().parent / "fonts",
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/local/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/TTF"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    Path("C:/Windows/Fonts"),
]


def _find_font(filename: str) -> Path:
    for folder in _FONT_CANDIDATES:
        p = folder / filename
        if p.exists():
            return p
    raise SystemExit(
        f"Не найден шрифт {filename}. Поставьте пакет с DejaVu "
        f"(Debian/Ubuntu: sudo apt install fonts-dejavu-core) "
        f"или положите {filename} в папку fonts/ рядом с build_print.py."
    )


def register_fonts():
    """DejaVu — свободный шрифт с полной кириллицей, есть почти везде."""
    pairs = [
        ("DVS", "DejaVuSans.ttf"),
        ("DVS-Bold", "DejaVuSans-Bold.ttf"),
        ("DVSerif", "DejaVuSerif.ttf"),
        ("DVSerif-Bold", "DejaVuSerif-Bold.ttf"),
    ]
    for name, filename in pairs:
        if name in pdfmetrics.getRegisteredFontNames():
            continue
        pdfmetrics.registerFont(TTFont(name, str(_find_font(filename))))


register_fonts()

BODY = "DVS"
BOLD = "DVS-Bold"
SERIF = "DVSerif"
SERIF_BOLD = "DVSerif-Bold"


# ------------------------------------------------------------------- текст
def _tokens(text: str):
    """Разбирает **жирный** внутри строки."""
    out, bold = [], False
    for chunk in text.split("**"):
        if chunk:
            out.append((chunk, bold))
        bold = not bold
    return out


def _words(text: str):
    """Слова: (слово, жирность, приклеено_к_предыдущему).

    Приклеивание нужно в двух случаях: после **жирного** фрагмента сразу идёт
    запятая или точка («**позже**, когда»), либо жирность меняется внутри слова.
    Пробел ставится только там, где он есть в исходном тексте.
    """
    out, cur, cur_bold, glue = [], "", None, False

    def flush():
        nonlocal cur, glue
        if cur:
            out.append((cur, cur_bold, glue))
            cur = ""
            glue = False

    for chunk, is_bold in _tokens(text):
        for ch in chunk:
            if ch.isspace():
                flush()
            elif not cur:
                cur, cur_bold = ch, is_bold
            elif cur_bold != is_bold:
                out.append((cur, cur_bold, glue))
                cur, cur_bold, glue = ch, is_bold, True
            else:
                cur += ch
    flush()
    return out


def wrap(text: str, size: float, maxw: float, font: str = BODY, bold: str = BOLD):
    """Возвращает строки как списки (слово, жирность, приклеено)."""
    space_plain = pdfmetrics.stringWidth(" ", font, size)
    space_bold = pdfmetrics.stringWidth(" ", bold, size)
    lines, cur, curw = [], [], 0.0
    for word, is_bold, glue in _words(text):
        f = bold if is_bold else font
        ww = pdfmetrics.stringWidth(word, f, size)
        need_space = bool(cur) and not glue
        add = ww + ((space_bold if is_bold else space_plain) if need_space else 0)
        if cur and curw + add > maxw:
            lines.append(cur)
            cur, curw = [(word, is_bold, False)], ww
        else:
            cur.append((word, is_bold, glue))
            curw += add
    if cur:
        lines.append(cur)
    return lines


def line_width(line, size, font=BODY, bold=BOLD):
    total = 0.0
    for i, (word, is_bold, glue) in enumerate(line):
        f = bold if is_bold else font
        total += pdfmetrics.stringWidth(word, f, size)
        if i and not glue:
            total += pdfmetrics.stringWidth(" ", f, size)
    return total


def n_lines(text: str, size: float, maxw: float, font=BODY, bold=BOLD) -> int:
    return len(wrap(text, size, maxw, font, bold))


def draw_line(c, line, x, y, size, font=BODY, bold=BOLD, color=INK):
    c.setFillColor(color)
    cx = x
    for i, (word, is_bold, glue) in enumerate(line):
        f = bold if is_bold else font
        if i and not glue:
            cx += c.stringWidth(" ", f, size)
        c.setFont(f, size)
        c.drawString(cx, y, word)
        cx += c.stringWidth(word, f, size)
    return cx


def draw_wrapped(c, text, x, y_top, maxw, size, leading, font=BODY, bold=BOLD,
                 color=INK, align="left", first_indent=0.0):
    """Рисует абзац, начиная от ВЕРХА текстового блока.

    Высота блока ровно `строк × leading`, поэтому вёрстку можно считать заранее:
    `n_lines(...) * leading` и `draw_wrapped(...)` совпадают до пункта.
    Возвращает y под последней строкой (низ блока).
    """
    lines = wrap(text, size, maxw - first_indent, font, bold)
    baseline = y_top - size * 0.80
    for i, line in enumerate(lines):
        lw = line_width(line, size, font, bold)
        dx = x
        if align == "center":
            dx = x + (maxw - lw) / 2
        elif align == "right":
            dx = x + maxw - lw
        elif i == 0:
            dx = x + first_indent
        draw_line(c, line, dx, baseline, size, font, bold, color)
        baseline -= leading
    return y_top - len(lines) * leading


def block_h(text, size, maxw, leading):
    """Высота абзаца: столько же, сколько вернёт draw_wrapped."""
    return n_lines(text, size, maxw) * leading


# ------------------------------------------------------------------- фигуры
def panel(c, x, y, w, h, fill=None, stroke=None, radius=6, line_w=0.8):
    """Прямоугольник/скруглённый прямоугольник с координатой y как нижней."""
    c.saveState()
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(line_w)
    stroke_flag = 1 if stroke is not None else 0
    fill_flag = 1 if fill is not None else 0
    if radius:
        c.roundRect(x, y, w, h, radius, stroke=stroke_flag, fill=fill_flag)
    else:
        c.rect(x, y, w, h, stroke=stroke_flag, fill=fill_flag)
    c.restoreState()


def hline(c, x1, x2, y, color=LINE, width=0.8, dash=None):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    if dash:
        c.setDash(*dash)
    c.line(x1, y, x2, y)
    c.restoreState()


def vline(c, x, y1, y2, color=LINE, width=0.8, dash=None):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    if dash:
        c.setDash(*dash)
    c.line(x, y1, x, y2)
    c.restoreState()


def dotted(c, x1, x2, y, color=DASH, width=0.7):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setDash(1, 2.4)
    c.line(x1, y, x2, y)
    c.restoreState()


def cut_marks(c, page_w, page_h, x, y_top, y_bottom, length=6 * MM):
    """Пунктир для разрезания листа на две карточки."""
    c.saveState()
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.4)
    c.setDash(2, 3)
    c.line(x, y_bottom, x, y_bottom + length)
    c.line(x, y_top - length, x, y_top)
    c.restoreState()


# ------------------------------------------------------------------- поток
class Flow:
    """Последовательная вёрстка сверху вниз: следит за курсором y."""

    def __init__(self, c, x, right, top, bottom=0):
        self.c, self.x, self.right, self.top, self.bottom = c, x, right, top, bottom
        self.y = top

    @property
    def w(self):
        return self.right - self.x

    def space(self, h):
        self.y -= h

    def para(self, text, size=10, leading=None, color=INK, font=BODY, bold=BOLD,
             align="left", space_after=0, space_before=0):
        leading = leading or size * 1.35
        self.y -= space_before
        before = self.y
        self.y = draw_wrapped(self.c, text, self.x, self.y, self.w, size, leading,
                              font, bold, color, align)
        self.y -= space_after
        return before - self.y

    def measure(self, text, size=10, leading=None):
        leading = leading or size * 1.35
        return n_lines(text, size, self.w) * leading

    def kicker(self, text, size=7.6, color=MUTED, space_after=3):
        self.para(text.upper(), size=size, leading=size * 1.3, color=color,
                  font=BOLD, space_after=space_after)

    def h1(self, text, size=19, color=ACCENT, space_after=4):
        self.para(text, size=size, leading=size * 1.2, color=color,
                  font=SERIF_BOLD, space_after=space_after)

    def h2(self, text, size=11.5, color=ACCENT2, space_before=11, space_after=3):
        self.para(text, size=size, leading=size * 1.3, color=color,
                  font=BOLD, space_before=space_before, space_after=space_after)

    def rule(self, color=LINE, width=0.8, space_before=4, space_after=6):
        self.y -= space_before
        hline(self.c, self.x, self.right, self.y, color, width)
        self.y -= space_after

    def bullets(self, items, size=9.6, leading=None, gap=2.2, color=INK,
                marker="—", marker_color=None, indent=13, space_after=0):
        leading = leading or size * 1.35
        marker_color = marker_color or GOLD
        for item in items:
            self.c.setFont(BOLD, size)
            self.c.setFillColor(marker_color)
            self.c.drawString(self.x, self.y - size * 0.80, marker)
            self.y = draw_wrapped(self.c, item, self.x + indent, self.y,
                                  self.w - indent, size, leading, BODY, BOLD, color)
            self.y -= gap
        self.y -= space_after

    def numbered(self, items, size=10, leading=None, gap=3, color=INK,
                 num_color=GOLD, indent=16, space_after=0):
        leading = leading or size * 1.35
        for i, item in enumerate(items, 1):
            self.c.setFont(BOLD, size)
            self.c.setFillColor(num_color)
            self.c.drawString(self.x, self.y - size * 0.80, f"{i}.")
            self.y = draw_wrapped(self.c, item, self.x + indent, self.y,
                                  self.w - indent, size, leading, BODY, BOLD, color)
            self.y -= gap
        self.y -= space_after

    def quote(self, text, size=10, leading=None, color=ACCENT, fill=GOLD_BG,
              space_after=4, pad=7):
        leading = leading or size * 1.35
        h = n_lines(text, size, self.w - pad * 2 - 6) * leading + pad * 2 - 3
        panel(self.c, self.x, self.y - h, self.w, h, fill=fill, radius=3)
        self.c.setFillColor(GOLD)
        self.c.rect(self.x, self.y - h, 2.4, h, stroke=0, fill=1)
        draw_wrapped(self.c, text, self.x + pad + 3, self.y - pad,
                     self.w - pad * 2 - 6, size, leading, BODY, BOLD, color)
        self.y -= h + space_after
        return h
