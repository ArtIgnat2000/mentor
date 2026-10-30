#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Печатные материалы комплекта наставника.

    python3 build_print.py

Пишет PDF в print/ и копирует их в docs/print/ — чтобы их можно было открыть
с телефона по ссылке прямо со страницы (раздел «Печатные материалы»).

Форматы: всё A4 (кроме карточек: они A5, по две на листе A4, с метками для разреза).
Печатать без масштабирования (100 %, «реальный размер»), поля — минимальные или «нет».

Содержание ниже — выжимка из markdown-документов. Меняете формулировки здесь
и пересобираете; markdown остаётся источником правды для сайта.
"""
from io import BytesIO
from pathlib import Path

import segno
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import os
def dbg(m):
    if os.environ.get("DBG"):
        print("  DBG", m)

from printkit import (
    A4H, A4W, A5H, A5W, DASH, MM, ACCENT, ACCENT2, BODY, BOLD, CREAM, GOLD, GOLD_BG,
    HOT, HOT_BG, INK, LINE, LINE_SOFT, MUTED, PAPER, SERIF_BOLD, TINT,
    Flow, cut_marks, dotted, draw_wrapped, hline, n_lines, panel, vline, wrap,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "print"
DOCS_PRINT = ROOT / "docs" / "print"

PAGES_URL = "https://artignat2000.github.io/mentor/"
PAGES_SHORT = "artignat2000.github.io/mentor"

M = 14 * MM          # поле страницы
HEAD_H = 13 * MM     # шапка документа

# ------------------------------------------------------------------ служебное


def qr_image(url: str = PAGES_URL, scale: int = 8) -> ImageReader:
    buf = BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=scale, border=1,
                                   dark="#16302b", light="#ffffff")
    buf.seek(0)
    return ImageReader(buf)


def qr_standalone(path: Path):
    """Отдельный файл QR — для распечатки/наклейки отдельно от листа."""
    segno.make(PAGES_URL, error="m").save(
        path, kind="png", scale=14, border=2, dark="#16302b", light="#ffffff")


def draw_qr_block(c, x, y_bottom, size, caption_lines=("Ссылка на свод", PAGES_SHORT)):
    """QR + подпись. y_bottom — низ блока."""
    c.drawImage(qr_image(), x, y_bottom, width=size, height=size, mask="auto")
    ty = y_bottom + size / 2 + 3
    for i, line in enumerate(caption_lines):
        c.setFont(BOLD if i == 0 else BODY, 6.3 if i == 0 else 6)
        c.setFillColor(MUTED if i else INK)
        c.drawString(x + size + 5, ty - i * 7.5, line)


def page_header(c, left, right, width=A4W, height=A4H, m=M):
    """Тонкая шапка: слева — документ, справа — серия. Возвращает верх контента."""
    y = height - m
    c.setFont(BOLD, 7)
    c.setFillColor(ACCENT)
    c.drawString(m, y - 7, left.upper())
    c.setFont(BODY, 7)
    c.setFillColor(MUTED)
    c.drawRightString(width - m, y - 7, right)
    hline(c, m, width - m, y - 13, ACCENT, 1.1)
    return y - 13 - 16


def page_footer(c, left, width=A4W, m=M, right=None, y=None):
    y = y if y is not None else m - 2
    hline(c, m, width - m, y + 9, LINE_SOFT, 0.7)
    c.setFont(BODY, 6.4)
    c.setFillColor(MUTED)
    c.drawString(m, y, left)
    if right:
        c.drawRightString(width - m, y, right)


def field_line(c, x, y, x_right, label, size=7.4, gap=3):
    """Подпись + пунктир до правого края x_right."""
    c.setFont(BODY, size)
    c.setFillColor(MUTED)
    c.drawString(x, y, label)
    lw = c.stringWidth(label, BODY, size)
    dotted(c, x + lw + gap, x_right, y, DASH, 0.7)


def checkbox(c, x, y, size=7.2, label=None, label_size=8.6, gap=3):
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.7)
    c.rect(x, y, size, size, stroke=1, fill=0)
    if label:
        c.setFont(BODY, label_size)
        c.setFillColor(INK)
        c.drawString(x + size + gap, y + 1.1, label)
        return x + size + gap + c.stringWidth(label, BODY, label_size)
    return x + size


# ------------------------------------------------------------------ 1. холодильник
RULES5 = [
    "Я никогда не сравниваю братьев — ни в минус, ни в плюс, даже в шутку.",
    "В момент аффекта я не воспитываю: только безопасность, присутствие, ровный голос.",
    "После срыва обязателен ремонт: вернуться, назвать, извиниться, договориться.",
    "У каждого мальчика есть нераздельное время со мной — и оно не отменяется.",
    "Моё слово — закон, потому что я его держу. Не могу — говорю заранее.",
]

STOP10 = [
    "Не кричать, не пугать, не унижать.",
    "Не наказывать и не отменять решения папы.",
    "Не сравнивать братьев.",
    "Не обманывать и не обещать зря.",
    "Не исчезать без предупреждения.",
    "Не стыдить за чувства и за маму.",
    "Не обсуждать одного брата с другим.",
    "Не занимать место папы.",
    "Не разбирать конфликт в момент аффекта.",
    "Не делать за ребёнка его работу.",
]

PHRASES3 = [
    ("«Я вижу, тебе сейчас очень плохо. Я никуда не ухожу.»", "вспышка, слёзы, «уйди» — П1"),
    ("«Я не разбираю, кто начал. Я помогаю закончить.»", "ссора братьев — П3"),
    ("«Злиться — нормально. Кричать на брата — нет. Это две разные вещи.»", "граница без стыда — П1"),
]

OPORY = [
    ("РИТМ", "порядок дня держит папа, я — свидетель и голос"),
    ("ПАУЗА", "эмоции законны, последствия — у поступков"),
    ("ПОСТУПОК", "«сделал сам, и это кому-то нужно»"),
]


def _qr_footer(c, x, right, y_top, qr_mm=26, size_title=7.4, size_line=6.6):
    """QR слева, подпись справа. y_top — верх блока, возвращает низ."""
    q = qr_mm * MM
    title = "Полный свод — правила, 13 протоколов, план на 90 дней"
    note = ("Работает без интернета и без JavaScript. В Safari: «Поделиться» → "
            "«На экран Домой» — свод останется в телефоне.")
    tx = x + q + 9
    tw = right - tx
    y_text = y_top - 7
    c.setFont(BOLD, size_title)
    c.setFillColor(INK)
    c.drawString(tx, y_text, title)
    c.setFont(BODY, size_line)
    c.setFillColor(ACCENT2)
    c.drawString(tx, y_text - 10, PAGES_SHORT)
    draw_wrapped(c, note, tx, y_text - 24, tw, 6.4, 8.2, BODY, BODY, MUTED)
    c.drawImage(qr_image(), x, y_top - q, width=q, height=q, mask="auto")
    return y_top - q


GAPS_FRIDGE = 4          # сколько «швов» между блоками плаката


def _fridge_layout(c, extra=0.0, commit=False, size_label="A4"):
    """Рисует плакат. `extra` — добавка к каждому межблочному отступу (заполнение листа).

    Возвращает y, на котором закончился контент: по нему считается заполнение.
    """
    W, H = A4W, A4H
    top = page_header(c, "Наставник · карманный свод",
                      f"плакат на холодильник · {size_label}")
    f = Flow(c, M, W - M, top, M)

    S_TITLE, L_TITLE = 18.5, 22
    S_SUB, L_SUB = 9.2, 12
    S_RULE, L_RULE, GAP_RULE = 13.4, 18.4, 9
    H_OPORY = 36
    S_STOP, L_STOP, GAP_STOP = 10.2, 13.6, 4.5
    S_PHR, L_PHR, GAP_PHR = 11.6, 15.6, 5
    S_HEAD, L_HEAD = 11.6, 15
    GAP = 11 + extra
    indent_rule = 23

    f.y = draw_wrapped(c, "Пять правил, которые важнее остальных", f.x, f.y,
                       f.w, S_TITLE, L_TITLE, SERIF_BOLD, BOLD, ACCENT)
    f.y -= 5
    f.y = draw_wrapped(c, "Если запомнится только это — работа уже пойдёт.", f.x, f.y,
                       f.w, S_SUB, L_SUB, BODY, BODY, MUTED)
    f.y -= GAP

    # --- пять правил
    for i, rule in enumerate(RULES5, 1):
        y0 = f.y
        c.setFont(SERIF_BOLD, 16.5)
        c.setFillColor(GOLD)
        c.drawString(f.x, y0 - S_RULE * 0.80, f"{i}")
        f.y = draw_wrapped(c, rule, f.x + indent_rule, y0,
                           f.w - indent_rule, S_RULE, L_RULE, BODY, BOLD, INK)
        f.y -= GAP_RULE
    f.y += GAP_RULE

    # --- три опоры
    f.y -= GAP
    ow = f.w / 3
    y0 = f.y
    for i, (name, text) in enumerate(OPORY):
        x = f.x + i * ow
        c.setFont(BOLD, 9)
        c.setFillColor(ACCENT2)
        c.drawString(x, y0 - 8, name)
        draw_wrapped(c, text, x, y0 - 14, ow - 12, 8.2, 10.4, BODY, BODY, MUTED)
    f.y = y0 - H_OPORY

    # --- стоп-лист
    f.y -= GAP
    hline(c, f.x, f.right, f.y + 9, LINE, 0.8)
    f.y = draw_wrapped(c, "Стоп-лист · никогда, ни при каких обстоятельствах",
                       f.x, f.y, f.w, S_HEAD, L_HEAD, BOLD, BOLD, HOT)
    f.y -= 7
    y_cols = f.y
    col_w = (f.w - 16) / 2
    half = (len(STOP10) + 1) // 2
    for col, items in enumerate((STOP10[:half], STOP10[half:])):
        yy = y_cols
        x = f.x + col * (col_w + 16)
        for item in items:
            c.setFont(BOLD, 8.6)
            c.setFillColor(HOT)
            c.drawString(x, yy - S_STOP * 0.80, "✕")
            yy = draw_wrapped(c, item, x + 14, yy, col_w - 14,
                              S_STOP, L_STOP, BODY, BOLD, INK)
            yy -= GAP_STOP
    f.y = y_cols - max(_stop_col_h(STOP10[:half], S_STOP, L_STOP, GAP_STOP, col_w - 14),
                       _stop_col_h(STOP10[half:], S_STOP, L_STOP, GAP_STOP, col_w - 14))

    # --- три фразы
    f.y -= GAP
    hline(c, f.x, f.right, f.y + 9, LINE, 0.8)
    f.y = draw_wrapped(c, "Три фразы-выручалочки", f.x, f.y, f.w,
                       S_HEAD, L_HEAD, BOLD, BOLD, ACCENT2)
    f.y = draw_wrapped(c, "В стрессе они не придумываются — их учат заранее.",
                       f.x, f.y, f.w, 8.4, 11, BODY, BODY, MUTED)
    f.y -= 7
    for text, where in PHRASES3:
        h = n_lines(text, S_PHR, f.w - 24) * L_PHR + 15
        panel(c, f.x, f.y - h, f.w, h, fill=GOLD_BG, radius=3)
        c.setFillColor(GOLD)
        c.rect(f.x, f.y - h, 2.6, h, stroke=0, fill=1)
        draw_wrapped(c, text, f.x + 12, f.y - 5, f.w - 24, S_PHR,
                     L_PHR, BODY, BOLD, ACCENT)
        c.setFont(BODY, 6.8)
        c.setFillColor(MUTED)
        c.drawRightString(f.x + f.w - 8, f.y - h + 4.8, where)
        f.y -= h + GAP_PHR

    # --- подвал
    f.y -= 10
    hline(c, f.x, f.right, f.y, LINE, 0.8)
    _qr_footer(c, f.x, f.right, f.y - 9)

    page_footer(c, "Печатать на A4, 100 %. Повесить туда, где смотришь каждый день.",
                right=f"версия {VERSION}")
    if commit:
        c.showPage()
    return f.y


def _stop_col_h(items, size, leading, gap, maxw):
    return sum(n_lines(i, size, maxw) * leading + gap for i in items) - gap


def fridge(c, commit=True):
    """Двухпроходная вёрстка: сначала меряем, сколько занял контент,
    потом распределяем остаток по отступам — плакат всегда заполняет лист."""
    target = M + 26 * MM + 20
    dry = canvas.Canvas(BytesIO(), pagesize=(A4W, A4H))
    end = _fridge_layout(dry, extra=0.0)
    slack = end - target
    extra = max(slack / GAPS_FRIDGE, 0.0)
    if slack < 0:
        raise SystemExit(f"плакат не влезает на A4: не хватает {-slack:.0f} pt")
    _fridge_layout(c, extra=extra, commit=commit)


def two_up(c, draw_card, label="разрезать"):
    """Две карточки A5 на листе A4 в альбомной ориентации.

    Карточки рисуются в системе координат A4 (портрет), затем уменьшаются
    до A5 — так вёрстка карточки пишется один раз и не дублируется.
    """
    s = A5W / A4W
    for i in range(2):
        c.saveState()
        c.translate(i * A5W, 0)
        c.scale(s, s)
        draw_card(c, A4W, A4H)
        c.restoreState()
    c.saveState()
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.4)
    c.setDash(2, 3)
    c.line(A5W, 0, A5W, A4H)
    c.restoreState()
    c.setFont(BODY, 5.6)
    c.setFillColor(MUTED)
    c.drawCentredString(A5W, 4 * MM, label)


def fridge_a5_2up(c):
    """Тот же плакат в размере A5: два экземпляра на альбомном A4."""
    target = M + 26 * MM + 20
    dry = canvas.Canvas(BytesIO(), pagesize=(A4W, A4H))
    extra = max((_fridge_layout(dry, 0.0, size_label="A5") - target) / GAPS_FRIDGE, 0.0)
    two_up(c, lambda cv, w, h: _fridge_layout(cv, extra=extra, size_label="A5"))
    c.showPage()


def _fridge_page(c):
    return fridge(c, commit=True)


# ------------------------------------------------------------------ 2. карта утра
def morning_card(c):
    top = page_header(c, "Инструмент 1 · карта утра", "ведёт папа · месяц")
    f = Flow(c, M, A4W - M, top)

    f.para("Карта утра", size=19, leading=22, color=ACCENT, font=SERIF_BOLD,
           space_after=1)
    f.para("Подъём → контрастный душ → зарядка с турником → завтрак → "
           "созидательное дело → доброе дело → вовремя отбой.",
           size=8.6, color=MUTED, space_after=9)

    # поля
    y0 = f.y
    field_line(c, f.x, y0 - 9, f.x + 95 * MM, "Имя:")
    field_line(c, f.x + 100 * MM, y0 - 9, f.right, "Месяц / год:")
    f.y = y0 - 16

    c.setFont(BODY, 7.4)
    c.setFillColor(MUTED)
    draw_wrapped(c, "Отмечает сам ребёнок. Взрослый спрашивает «как прошло?», "
                    "а не «сделал?». Строка без галочек — это данные, а не провал.",
                 f.x, f.y, f.w, 7.4, 9.6, BODY, BODY, MUTED)
    f.y -= 16

    # таблица
    cols = [
        ("День", 12),
        ("Душ", 15),
        ("Зарядка", 17),
        ("Турник, повторы", 24),
        ("Завтрак", 19),
        ("Созидательное\n(фортепиано / IT)", 41),
        ("Доброе дело\n(брату / родителям)", 40),
    ]
    total = sum(w for _, w in cols)
    avail = f.w / MM
    scale_k = avail / total
    widths = [w * scale_k * MM for _, w in cols]

    bottom = M + 12 * MM
    head_h = 13 * MM
    rows = 31
    row_h = min((f.y - head_h - bottom) / rows, 6.6 * MM)

    x = f.x
    table_top = f.y
    # шапка таблицы
    panel(c, f.x, table_top - head_h, f.w, head_h, fill=TINT, stroke=LINE, radius=0)
    xx = f.x
    c.setFillColor(ACCENT)
    for (title, _), w in zip(cols, widths):
        parts = title.split("\n")
        for k, part in enumerate(parts):
            c.setFont(BOLD if k == 0 else BODY, 6.6 if k == 0 else 5.4)
            c.setFillColor(ACCENT if k == 0 else MUTED)
            y_line = table_top - head_h / 2 + (3.2 if k == 0 and len(parts) > 1 else
                                                (0 if k == 0 else -4.2))
            c.drawCentredString(xx + w / 2, y_line, part)
        xx += w

    # строки
    y = table_top - head_h
    for day in range(1, rows + 1):
        y_next = y - row_h
        if day % 2 == 0:
            c.setFillColor(CREAM)
            c.rect(f.x, y_next, f.w, row_h, stroke=0, fill=1)
        c.setFont(BODY, 7)
        c.setFillColor(MUTED if day % 7 else INK)
        c.drawCentredString(f.x + widths[0] / 2, y_next + row_h / 2 - 2.4, str(day))
        xx = f.x
        for w in widths:
            c.setStrokeColor(LINE_SOFT)
            c.setLineWidth(0.5)
            c.line(xx, y_next, xx, y)
            xx += w
        c.setStrokeColor(LINE_SOFT)
        c.line(f.x, y_next, f.right, y_next)
        y = y_next

    # внешняя рамка
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.rect(f.x, y, f.w, table_top - y, stroke=1, fill=0)

    page_footer(c, "Одно правило: карту ведёт ребёнок, а не взрослый за него."
                   " Сравнивать листы братьев нельзя — они не в одном зачёте.",
                right=f"версия {VERSION}")
    c.showPage()


# ------------------------------------------------------------------ 3. карта паузы
def pause_cards(c):
    """Две карточки A5 на альбомном A4."""
    two_up(c, _pause_card)
    c.showPage()


def _pause_card(c, W, H, m=11 * MM):
    """Карточка «мои три способа разрядки» + место для своих фраз ремонта."""
    top = page_header(c, "Инструмент 3 · карта паузы", "мои три способа",
                      width=W, height=H, m=m)
    f = Flow(c, m, W - m, top, m)

    sub = "Когда закипаю — я не «успокаиваюсь», а делаю одно конкретное движение."
    chips = ("Из чего выбрать (подчеркнуть своё): вода · душ · движение · турник · "
             "отжимания · выйти · подышать 4-7-8 · сжать-разжать · посчитать")
    note = ("Карта — право, а не обязанность: «примени свою карту!» возвращает всё "
            "назад. Это подсказка для тебя, не команда взрослого.")
    h_sub = n_lines(sub, 8.4, f.w) * 11.5
    h_chips = n_lines(chips, 7.6, f.w) * 9.6
    h_note = n_lines(note, 7.2, f.w) * 9.4
    row_h = 44

    f.y = draw_wrapped(c, "Моя карта паузы", f.x, f.y, f.w, 18, 21,
                       SERIF_BOLD, BOLD, ACCENT)
    f.y = draw_wrapped(c, sub, f.x, f.y, f.w, 8.4, 11.5, BODY, BODY, MUTED)
    f.y -= 15
    field_line(c, f.x, f.y - 6, f.right, "Имя:")
    f.y -= 25

    def rows_group(title, count, numbered):
        nonlocal f
        f.y = draw_wrapped(c, title, f.x, f.y, f.w, 10.2, 13, BOLD, BOLD, ACCENT2)
        f.y -= 8
        for i in range(count):
            row_top = f.y
            if numbered:
                c.setFont(SERIF_BOLD, 13)
                c.setFillColor(GOLD)
                c.drawString(f.x, row_top - row_h + 7, f"{i + 1}")
                dotted(c, f.x + 16, f.right, row_top - row_h + 8, LINE, 0.9)
            else:
                dotted(c, f.x, f.right, row_top - row_h + 8, LINE, 0.9)
            f.y = row_top - row_h

    rows_group("Три способа, которые мои", 3, numbered=True)
    f.y -= 14
    f.y = draw_wrapped(c, chips, f.x, f.y, f.w, 7.6, 9.6, BODY, BOLD, MUTED)
    f.y -= 14
    rows_group("Перед вспышкой я замечаю у себя", 2, numbered=False)

    # --- блок «вышел — вернулся» занимает всё оставшееся место
    box_top = f.y - 14
    box_bottom = m + 16 + h_note + 30
    box_h = box_top - box_bottom
    if box_h < 120:
        raise SystemExit(f"карта паузы: блок ремонта {box_h:.0f} pt — слишком мало места")
    panel(c, f.x, box_bottom, f.w, box_h, fill=TINT, stroke=LINE, radius=5)
    c.setFillColor(GOLD)
    c.rect(f.x, box_bottom, 2.4, box_h, stroke=0, fill=1)

    yy = box_top - 17
    c.setFont(BOLD, 10)
    c.setFillColor(ACCENT)
    c.drawString(f.x + 11, yy, "Вышел — вернулся")
    yy -= 15
    for text in ("Выйти — право, и за него не наказывают.",
                 "Вернуться и починить — обязанность."):
        c.setFont(BOLD, 7)
        c.setFillColor(GOLD)
        c.drawString(f.x + 11, yy - 7.4, "—")
        yy = draw_wrapped(c, text, f.x + 20, yy, f.w - 34, 8.4, 11,
                          BODY, BODY, INK) - 2
    yy -= 8
    c.setFont(BODY, 7.4)
    c.setFillColor(MUTED)
    c.drawString(f.x + 11, yy, "Мои три предложения ремонта — назвать, извиниться, "
                                "договориться:")
    yy -= 16
    step = max((yy - box_bottom - 10) / 3, 16)
    for k in range(3):
        dotted(c, f.x + 11, f.right - 11, yy - step * (k + 1), LINE, 0.8)

    note_top = box_bottom - 18
    draw_wrapped(c, note, f.x, note_top, f.w, 7.2, 9.4, BODY, BODY, MUTED)
    field_line(c, f.x, note_top - h_note - 10, f.right, "Подписано моей рукой:")

    page_footer(c, "Инструмент 3. Репетируем в спокойствии — в стрессе не появится.",
                width=W, m=m)


# ------------------------------------------------------------------ 4. шкала 1-5
SCALE = [
    ("1", "Спокоен", "могу думать, слышу других"),
    ("2", "Напряжён", "говорю громче, тороплюсь"),
    ("3", "Закипаю", "хочу остановить всех вокруг"),
    ("4", "На грани", "тело напряжено, почти кричу"),
    ("5", "Взрыв", "кричу, слов почти не слышу"),
]


def scale_cards(c):
    """Шкала 1–5: две карточки A5 на альбомном A4."""
    two_up(c, _scale_card)
    c.showPage()


def _scale_card(c, W, H, m=11 * MM):
    """Шкала 1–5: пять уровней на всю высоту карточки."""
    top = page_header(c, "Инструмент 2 · шкала 1–5", "называет ребёнок",
                      width=W, height=H, m=m)
    f = Flow(c, m, W - m, top, m)

    sub = ("Состояние называет сам ребёнок. Взрослый не диагностирует за него "
           "и не спорит с цифрой.")
    note = ("Сначала называем — потом действуем. Взрослый спрашивает: «Где ты сейчас "
            "по шкале?» — и не спорит с ответом.")
    h_title, h_sub = 21, n_lines(sub, 8.4, f.w) * 11.5
    h_note = n_lines(note, 7.2, f.w) * 9.4

    header_block = h_title + h_sub + 20 + 12      # заголовок, подзаголовок, имя
    gap = 4 * MM
    rows_top = top - header_block
    rows_bottom = m + 34 + h_note + 14
    row_h = (rows_top - rows_bottom - gap * 4) / 5

    f.y = draw_wrapped(c, "Шкала 1–5", f.x, f.y, f.w, 18, 21, SERIF_BOLD, BOLD, ACCENT)
    f.y = draw_wrapped(c, sub, f.x, f.y, f.w, 8.4, 11.5, BODY, BODY, MUTED)
    f.y -= 20
    field_line(c, f.x, f.y - 8, f.right, "Имя:")
    f.y -= 26

    for num, name, hint in SCALE:
        hot = num in ("4", "5")
        panel(c, f.x, f.y - row_h, f.w, row_h,
              fill=HOT_BG if hot else TINT, stroke=LINE, radius=4)
        c.setFont(SERIF_BOLD, min(row_h * 0.55, 26))
        c.setFillColor(HOT if hot else ACCENT2)
        c.drawCentredString(f.x + 13 * MM, f.y - row_h / 2 - row_h * 0.18, num)
        c.setFont(BOLD, 10)
        c.setFillColor(ACCENT)
        c.drawString(f.x + 24 * MM, f.y - row_h / 2 + 4, name)
        c.setFont(BODY, 7.4)
        c.setFillColor(MUTED)
        c.drawString(f.x + 24 * MM, f.y - row_h / 2 - 7, hint)
        c.setFont(BODY, 7)
        c.setFillColor(MUTED)
        c.drawString(f.x + 24 * MM, f.y - row_h + 6, "что помогает:")
        hline(c, f.x + 43 * MM, f.right - 5 * MM, f.y - row_h + 5, DASH, 0.8)
        f.y -= row_h + gap

    draw_wrapped(c, note, f.x, m + 34 + h_note, f.w, 7.2, 9.4, BODY, BODY, MUTED)
    page_footer(c, "Инструмент 2. Вводить на нейтральных примерах: кино, история, свой день.",
                width=W, m=m)


# ------------------------------------------------------------------ 5. журнал
def mentor_journal(c):
    top = page_header(c, "Инструмент 5 · журнал наставника", "3 строки после встречи")
    f = Flow(c, M, A4W - M, top)

    f.para("Журнал наставника", size=19, leading=22, color=ACCENT, font=SERIF_BOLD,
           space_after=1)
    f.para("Две минуты после встречи. Через месяц это единственный честный "
           "источник динамики — память льстит.", size=8.6, color=MUTED, space_after=7)

    y0 = f.y
    field_line(c, f.x, y0 - 9, f.x + 105 * MM, "Месяц / год:")
    c.setFont(BODY, 7)
    c.setFillColor(MUTED)
    c.drawRightString(f.right, y0 - 9, "формат: 1:1 · двое · вчетвером · длинный")
    f.y = y0 - 18

    bottom = M + 16
    blocks = 12
    gap = 2.6 * MM
    block_h = (f.y - bottom - gap * (blocks - 1)) / blocks

    for n in range(1, blocks + 1):
        y_top = f.y
        y_bot = y_top - block_h
        panel(c, f.x, y_bot, f.w, block_h, fill=None, stroke=LINE, radius=2.5,
              line_w=0.6)
        # номер + дата + формат
        c.setFont(BOLD, 7.4)
        c.setFillColor(GOLD)
        c.drawString(f.x + 5, y_top - 9.5, f"{n:02d}")
        field_line(c, f.x + 17, y_top - 9.5, f.x + 62 * MM, "дата")
        yy = y_top - 9.5
        xx = f.x + 64 * MM
        for label in ("1:1", "двое", "вчетвером", "длинный"):
            xx = checkbox(c, xx, yy - 1, 6.4, label, 6.8) + 9
        c.setFont(BODY, 6.4)
        c.setFillColor(MUTED)
        c.drawRightString(f.right - 5, yy, "восстановление, мин  ______")
        # три строки
        labels = ("что видел", "что зацепило", "что сделаю иначе")
        step = (block_h - 14) / 3
        for k, label in enumerate(labels):
            ly = y_top - 17 - k * step
            c.setFont(BODY, 6.8)
            c.setFillColor(MUTED)
            c.drawString(f.x + 5, ly, label)
            dotted(c, f.x + 5 + c.stringWidth(label, BODY, 6.8) + 3, f.right - 5, ly, LINE_SOFT, 0.6)
        f.y = y_bot - gap

    page_footer(c, "Раз в две недели — бланк «я не сбился». Раз в месяц — 30 минут с папой.",
                right=f"версия {VERSION}")
    c.showPage()


# ------------------------------------------------------------------ 6. копилка
def good_deeds(c):
    top = page_header(c, "Инструмент 4 · копилка добрых дел", "без призов и рейтингов")
    f = Flow(c, M, A4W - M, top)

    f.para("Копилка добрых дел", size=19, leading=22, color=ACCENT, font=SERIF_BOLD,
           space_after=1)
    f.para("Ежедневное маленькое дело: брату и родителям. Небольшое, конкретное, "
           "регулярное. Без звёздочек, баллов и «кто больше».", size=8.6,
           color=MUTED, space_after=9)

    y0 = f.y
    field_line(c, f.x, y0 - 9, f.x + 95 * MM, "Имя:")
    field_line(c, f.x + 100 * MM, y0 - 9, f.right, "Месяц:")
    f.y = y0 - 17

    cols = [("День", 14), ("Что сделал для брата", 82), ("Что сделал для родителей", 84)]
    widths = [w * MM for _, w in cols]
    k = f.w / sum(widths)
    widths = [w * k for w in widths]

    bottom = M + 4 * MM
    head_h = 9 * MM
    rows = 31
    row_h = min((f.y - head_h - bottom) / rows, 6.4 * MM)
    table_top = f.y

    panel(c, f.x, table_top - head_h, f.w, head_h, fill=TINT, stroke=LINE, radius=0)
    xx = f.x
    for (title, _), w in zip(cols, widths):
        c.setFont(BOLD, 7)
        c.setFillColor(ACCENT)
        c.drawCentredString(xx + w / 2, table_top - head_h / 2 - 2.4, title)
        xx += w

    y = table_top - head_h
    for day in range(1, rows + 1):
        y_next = y - row_h
        if day % 2 == 0:
            c.setFillColor(CREAM)
            c.rect(f.x, y_next, f.w, row_h, stroke=0, fill=1)
        c.setFont(BODY, 7)
        c.setFillColor(MUTED if day % 7 else INK)
        c.drawCentredString(f.x + widths[0] / 2, y_next + row_h / 2 - 2.4, str(day))
        xx = f.x
        for w in widths:
            c.setStrokeColor(LINE_SOFT)
            c.setLineWidth(0.5)
            c.line(xx, y_next, xx, y)
            xx += w
        c.setStrokeColor(LINE_SOFT)
        c.line(f.x, y_next, f.right, y_next)
        y = y_next

    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.rect(f.x, y, f.w, table_top - y, stroke=1, fill=0)

    page_footer(c, "Хвалить за вклад, а не за объём: «это было для него важно».",
                right=f"версия {VERSION}")
    c.showPage()


# ------------------------------------------------------------------ 7. я не сбился
SELF_CHECK = [
    "Я больше говорю или слушаю?",
    "Дети идут на встречу охотно или «по обязанности»?",
    "Было ли у меня за две недели время 1:1 с каждым?",
    "Произносил ли я сравнение вслух — хоть раз?",
    "Повышал ли я голос?",
    "Папа чувствует поддержку или контроль?",
    "Что я сделал вместе с ними (не «для них») за эти две недели?",
]


def self_check(c):
    """7 вопросов: два бланка A5 на альбомном A4."""
    two_up(c, _self_check_form)
    c.showPage()


def _self_check_form(c, W, H, m=11 * MM):
    """Бланк «я не сбился?»: семь вопросов с местом для ответа."""
    top = page_header(c, "Проверка · я не сбился", "раз в две недели, 5 минут наедине",
                      width=W, height=H, m=m)
    f = Flow(c, m, W - m, top, m)

    sub = "Семь вопросов себе. Отвечать честно — читать будет только наставник."
    box_text = ("Значит, я сполз в роль инструктора или контролёра. Возврат: раздел 0 "
                "(кто я в этой системе), правила 5.1 и 7.5. Ничего не «перезапускать» — "
                "просто вернуться.")
    h_sub = n_lines(sub, 7.8, f.w) * 10
    box_h = n_lines(box_text, 7.6, f.w - 18) * 9.6 + 34

    q_top = top - 21 - h_sub - 24
    q_bottom = m + 18 + box_h + 12
    q_h = (q_top - q_bottom) / len(SELF_CHECK)

    f.y = draw_wrapped(c, "Я не сбился?", f.x, f.y, f.w, 17, 20, SERIF_BOLD, BOLD, ACCENT)
    f.y = draw_wrapped(c, sub, f.x, f.y, f.w, 7.8, 10, BODY, BODY, MUTED)
    f.y -= 8
    field_line(c, f.x, f.y - 6, f.x + 62 * MM, "Период:")
    c.setFont(BODY, 6.4)
    c.setFillColor(MUTED)
    c.drawRightString(f.right, f.y - 6, "нет · скорее нет · скорее да · да")

    for i, q in enumerate(SELF_CHECK, 1):
        y_top = q_top - (i - 1) * q_h
        c.setFont(BOLD, 8.6)
        c.setFillColor(GOLD)
        c.drawString(f.x, y_top - 7.2, f"{i}.")
        qy = draw_wrapped(c, q, f.x + 12, y_top, f.w - 12, 8.8, 11,
                          BODY, BOLD, INK)
        xx = f.x + 12
        for label in ("нет", "скорее нет", "скорее да", "да"):
            xx = checkbox(c, xx, qy - 9, 6.6, label, 6.8) + 9
        # место для заметки от руки
        note_top = qy - 16
        for k in range(2):
            ly = note_top - 13 * (k + 1)
            if ly > y_top - q_h + 4:
                dotted(c, f.x + 12, f.right, ly, LINE, 0.6)
        if i < len(SELF_CHECK):
            hline(c, f.x, f.right, y_top - q_h + 2, LINE_SOFT, 0.6)

    y_box = m + 18
    panel(c, f.x, y_box, f.w, box_h, fill=HOT_BG, stroke=LINE, radius=4)
    c.setFillColor(HOT)
    c.rect(f.x, y_box, 2.4, box_h, stroke=0, fill=1)
    yy = draw_wrapped(c, "Три и больше «неудобных» ответа", f.x + 9, y_box + box_h - 9,
                      f.w - 18, 8.6, 11, BOLD, BOLD, HOT)
    draw_wrapped(c, box_text, f.x + 9, yy - 4, f.w - 18, 7.6, 9.6, BODY, BODY, INK)

    page_footer(c, "Правила наставника, раздел 11.", width=W, m=m)


# ------------------------------------------------------------------ 8. памятка папе
def kv_panel(c, f, rows, label_w, fill=PAPER, pad=8, gap=6, space_after=10,
             size=8.4, leading=10.8):
    """Панель «название — пояснение». Высота считается по фактическому тексту."""
    label_w = min(label_w, f.w * 0.40)
    lw = label_w - 12
    tw = f.w - label_w - pad * 2
    hs = [max(n_lines(name, size, lw) * leading,
              n_lines(text, size, tw) * leading) for name, text in rows]
    h = sum(hs) + gap * (len(rows) - 1) + pad * 2
    panel(c, f.x, f.y - h, f.w, h, fill=fill, stroke=LINE, radius=4)
    y = f.y - pad
    for (name, text), hh in zip(rows, hs):
        draw_wrapped(c, name, f.x + pad, y, lw, size, leading, BODY, BOLD, ACCENT)
        draw_wrapped(c, text, f.x + label_w + pad, y, tw, size, leading,
                     BODY, BODY, MUTED)
        y -= hh + gap
    f.y -= h + space_after


def qr_stamp(c, x_right, y_top, size=22 * MM, title="Полный свод", url=PAGES_SHORT):
    """QR с подписью под ним; прижат к правому краю."""
    x = x_right - size
    c.drawImage(qr_image(), x, y_top - size, width=size, height=size, mask="auto")
    c.setFont(BOLD, 6.2)
    c.setFillColor(INK)
    c.drawRightString(x_right, y_top - size - 8, title)
    c.setFont(BODY, 5.8)
    c.setFillColor(ACCENT2)
    c.drawRightString(x_right, y_top - size - 15, url)
    return y_top - size - 18


def flags_panel(c, f, title, text, qr=True, height=None):
    """Красная рамка «красные флаги» + QR справа."""
    qr_w = 44 * MM if qr else 0
    body_w = f.w - qr_w - 16
    pad = 8
    h = max(height or 0,
            n_lines(title, 8.6, body_w) * 11 + 6
            + n_lines(text, 7.6, body_w) * 9.6 + pad * 2)
    h = max(h, 31 * MM if qr else 0)
    panel(c, f.x, f.y - h, f.w, h, fill=HOT_BG, stroke=LINE, radius=4)
    c.setFillColor(HOT)
    c.rect(f.x, f.y - h, 2.4, h, stroke=0, fill=1)
    yy = draw_wrapped(c, title, f.x + pad + 2, f.y - pad, body_w, 8.6, 11,
                      BOLD, BOLD, HOT)
    draw_wrapped(c, text, f.x + pad + 2, yy - 3, body_w, 7.6, 9.6, BODY, BODY, INK)
    if qr:
        qr_stamp(c, f.right - 12, f.y - pad, 20 * MM)
    f.y -= h + 10


def memo_dad(c):
    top = page_header(c, "Памятка · папе", "одна страница")
    f = Flow(c, M, A4W - M, top)

    f.para("Папе: что держит папа", size=20, leading=23, color=ACCENT,
           font=SERIF_BOLD, space_after=2)
    f.para("Не методичка. Одна страница на неделю: что моё, чего не делаю, "
           "о чём договариваемся с наставником.", size=8.8, color=MUTED,
           space_after=10)

    f.h2("Три результата за 90 дней — по ним и меряем", space_before=0)
    f.bullets([
        "Старший **выходит из вспышки с помощью**, а не до конца: 2–3 своих "
        "способа, время восстановления примерно вдвое короче.",
        "**Ссоры заканчиваются ремонтом**: кто-то из братьев возвращается и чинит сам.",
        "**Утренний ритм держится** большую часть недели — без ежедневного скандала.",
    ], size=9.4, marker_color=GOLD, gap=4)

    f.h2("Моя зона — здесь я не делегирую")
    kv_panel(c, f, [
        ("Режим, подъём, отбой, последствия",
         "держу я. Наставник спрашивает и поддерживает, а не проверяет."),
        ("Вспышка в моменте",
         "первая линия — я. Правило одно: безопасность, присутствие, ровный голос."),
        ("Ревность старшего",
         "согласую логику: нужно не убеждение, а гарантированное личное время с мамой."),
        ("Созидательное дело",
         "слежу за регулярностью. Содержание — не моя зона в первом цикле."),
        ("Добрые дела",
         "замечаю вслух: «это было для него важно»."),
    ], label_w=62 * MM, size=8.8, space_after=4)

    f.h2("Сверка с наставником: раз в неделю, 10–15 минут")
    f.para("Не отчёт о поведении и не разбор ребёнка. Четыре вопроса — по очереди:",
           size=8.8, color=MUTED, space_after=4)
    f.numbered([
        "Что изменилось за неделю — по фактам, а не по ощущению?",
        "Что мешает дома?",
        "Что нужно от наставника?",
        "Что меняем на следующей неделе?",
    ], size=9.4, gap=3)
    f.para("Просьба «повлияй на него» не работает — работает «побудь с ним в четверг». "
           "Расхождение в правилах решаем без детей, а не в моменте.",
           size=8.6, color=INK, space_before=3, space_after=4)

    f.h2("В момент вспышки — один порядок")
    steps = ["заметил", "назвал", "принял", "граница", "разбор позже", "ремонт"]
    x = f.x
    for i, step in enumerate(steps):
        w = c.stringWidth(step, BOLD, 8.4) + 13
        panel(c, x, f.y - 15, w, 14, fill=TINT, stroke=LINE, radius=7)
        c.setFont(BOLD, 8.4)
        c.setFillColor(ACCENT)
        c.drawString(x + 6.5, f.y - 10.6, step)
        x += w + 3
        if i < len(steps) - 1:
            c.setFont(BODY, 8)
            c.setFillColor(MUTED)
            c.drawString(x - 1, f.y - 10.6, "→")
            x += 9
    f.y -= 22
    f.para("Ремонт обязателен и со взрослым тоже: вернуться, назвать, извиниться, "
           "договориться. Это и есть воспитание, а не бонус за хорошее поведение.",
           size=8.6, color=INK, space_after=2)

    f.h2("Чего не делаю")
    f.bullets([
        "Не сравниваю братьев вслух — даже в шутку и даже «в пользу» младшего.",
        "Не выясняю при них, кто начал, и не назначаю виноватого в момент ссоры.",
        "Не отменяю решений наставника при детях и не прошу его быть «добрым полицейским».",
        "Не прошу маму меняться и не делаю её арбитром между сыновьями.",
        "Не ввожу всё сразу: один новый элемент в неделю — максимум.",
    ], size=9.2, marker_color=HOT, gap=3)

    flags_panel(c, f, "Красные флаги — не тянуть",
                "Вспышка дольше 30–40 минут · агрессия с повреждением вещей или себя · "
                "«я не хочу жить», «лучше бы меня не было» · частота растёт месяц к месяцу · "
                "звонки «плохой день» чаще двух раз в неделю. Это не про наказание, "
                "а повод обсудить специалиста. Наставничество при этом продолжается.")

    page_footer(c, "Составлено по комплекту: правила наставника, протоколы, план на 90 дней.",
                right=f"версия {VERSION}")
    c.showPage()


def memo_mom(c):
    top = page_header(c, "Памятка · маме", "одна страница")
    f = Flow(c, M, A4W - M, top)

    f.para("Маме: как не подпитывать ревность", size=20, leading=23, color=ACCENT,
           font=SERIF_BOLD, space_after=2)
    f.para("Это не оценка вашего воспитания. Это шпаргалка на момент ссоры — "
           "на пять минут, когда всё кипит.", size=8.8, color=MUTED, space_after=10)

    f.h2("Сначала главное", space_before=0)
    f.para("Ревность нельзя запретить — её можно «расколдовать». Старшему нужно "
           "не убеждение, что «люблю одинаково», а **гарантированное личное время** "
           "с вами: короткое, но своё — и не отменяемое за плохое поведение.",
           size=9.5, color=INK, space_after=5)
    f.para("Чувство, названное вслух, слабеет. Чувство, за которое стыдят, "
           "становится сильнее и скрытнее.", size=9.5, color=INK, space_after=2)

    f.h2("В момент ссоры — три шага и ни одного лишнего слова")
    f.numbered([
        "**Не искать виноватого.** «Я не разбираю, кто начал» снимает необходимость "
        "защищаться — и ссора теряет топливо.",
        "**Назвать чувство, не оценивая его.** «Тебе обидно. Это понятно.»",
        "**Разбор и ремонт — позже**, когда остынет. В кипящем состоянии любая "
        "воспитательная фраза работает как масло в огонь.",
    ], size=9.4, gap=3)

    f.h2("Чего не говорить — даже с благими намерениями")
    f.bullets([
        "«Не ревнуй», «что ты как маленький» — запрет чувства.",
        "«Ты же старший, ты должен уступать» — долг вместо чувства.",
        "«Неправда, я люблю вас одинаково» — спор о факте вместо признания чувства.",
        "«Будь как брат», «посмотри, он смог» — любое сравнение, вслух и в шутку.",
        "«Из-за тебя у меня…» — вина за вашу усталость.",
    ], size=9.2, marker="✕", marker_color=HOT, gap=2.5)

    f.h2("Что говорить вместо")
    for text in [
        "«Тебе мало меня — это не выдумка и не каприз.»",
        "«Ты можешь так чувствовать, даже если я люблю вас одинаково.»",
        "«Из-за этого ты не становишься плохим братом.»",
    ]:
        f.quote(text, size=9.8, space_after=4)

    f.h2("Два обещания, которые работают лучше слов")
    kv_panel(c, f, [
        ("Своё время с каждым",
         "отдельно и регулярно; не отменяется в наказание и не выдаётся "
         "за хорошее поведение"),
        ("Помощь — с благодарностью",
         "без «наконец-то» и без оценки качества: принял и сказал спасибо"),
    ], label_w=58 * MM, fill=GOLD_BG, size=8.8, space_after=4)

    f.h2("Что вне вашей зоны — и это нормально")
    f.bullets([
        "Правила и последствия держит папа. Наставник их усиливает, а не заменяет.",
        "Наставник не обсуждает вас и не оценивает родителей — это его рабочее "
        "правило, а не отношение к вам.",
        "Содержание разговоров с мальчиками остаётся между ними: он передаёт папе "
        "состояние, а не текст.",
    ], size=9.2, marker_color=ACCENT2, gap=3)

    flags_panel(c, f, "Когда нужен не разговор, а специалист",
                "«Я им не нужен», «лучше бы меня не было» · отказ от еды или сна · "
                "устойчивое самообесценивание · агрессия с повреждением вещей или себя. "
                "Это не про воспитание — это про помощь. Сказать папе сразу, без обёртки.")

    page_footer(c, "Составлено по комплекту: концепция, правила наставника, протоколы П2 и П4.",
                right=f"версия {VERSION}")
    c.showPage()



# ------------------------------------------------------------------ 10. дневник силы
DIARY_COLS = [
    ("День", 9),
    ("Душ,\nзарядка", 19),
    ("Турник,\nповторы", 22),
    ("Трени-\nровка", 17),
    ("Форте-\nпиано, мин.", 21),
    ("Доброе\nдело", 17),
    ("Отбой\nвовремя", 17),
    ("Заметка: что было трудно", 39),
]
CHECK_COLS = (1, 3, 5, 6)          # колонки с галочкой
WEEKS = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 31)]


def _col_title(c, x, w, y_center, title, box_h):
    """Заголовок колонки: до двух строк, блок выровнен по центру шапки."""
    parts = title.split("\n")[:2]
    lead = 6.6
    if len(parts) == 1:
        base = y_center - 2.2
    else:
        base = y_center + lead / 2 - 2.2
    for i, part in enumerate(parts):
        first = i == 0
        c.setFont(BOLD if first else BODY, 6.5 if first else 5.6)
        c.setFillColor(ACCENT if first else MUTED)
        c.drawCentredString(x + w / 2, base - i * lead, part)


def daily_diary(c):
    """«Дневник силы»: отметка за каждый день + итоги недели и месяца."""
    top = page_header(c, "Дневник силы · за каждый день", "заполняет сам ребёнок · месяц")
    f = Flow(c, M, A4W - M, top)

    f.para("Дневник силы", size=17, leading=20, color=ACCENT, font=SERIF_BOLD,
           space_after=1)
    f.para("Отметка — галочка, числа — числом. Планку ставит не взрослый, а вчерашний ты. "
           "День с ритмом — когда отмечены все четыре клетки.", size=8.4,
           color=MUTED, space_after=6)

    y0 = f.y
    field_line(c, f.x, y0 - 8, f.x + 92 * MM, "Имя:")
    field_line(c, f.x + 98 * MM, y0 - 8, f.right, "Месяц / год:")
    f.y = y0 - 16

    widths = [w * MM for _, w in DIARY_COLS]
    k = f.w / sum(widths)
    widths = [w * k for w in widths]

    bottom = 26 * MM                 # низ таблицы / блока итогов
    head_h = 13.5 * MM
    sum_h = 7.6 * MM
    n_rows = 31
    month_h = 13.5 * MM
    gap = 5 * MM

    space = f.y - bottom - head_h - sum_h * (len(WEEKS) - 1) - gap - month_h
    row_h = min(space / n_rows, 6.0 * MM)
    if row_h < 4.4 * MM:
        raise SystemExit(f"дневник не влезает: строка {row_h / MM:.1f} мм")
    print(f"  дневник: строка {row_h / MM:.2f} мм")

    table_top = f.y
    panel(c, f.x, table_top - head_h, f.w, head_h, fill=TINT, stroke=LINE, radius=0)
    xx = f.x
    for (title, _), w in zip(DIARY_COLS, widths):
        _col_title(c, xx, w, table_top - head_h / 2, title, head_h)
        xx += w

    y = table_top - head_h
    day = 1
    for week_no, (d_from, d_to) in enumerate(WEEKS, 1):
        for _ in range(d_to - d_from + 1):
            y_next = y - row_h
            if day % 2 == 0:
                c.setFillColor(CREAM)
                c.rect(f.x, y_next, f.w, row_h, stroke=0, fill=1)
            c.setFont(BODY, 6.6)
            c.setFillColor(INK if day % 7 == 0 else MUTED)
            c.drawCentredString(f.x + widths[0] / 2, y_next + row_h / 2 - 2.3, str(day))
            box = min(4.1 * MM, row_h - 1.8 * MM)
            xx = f.x
            for i, w in enumerate(widths):
                if i in CHECK_COLS:
                    c.setStrokeColor(DASH)
                    c.setLineWidth(0.6)
                    c.rect(xx + w / 2 - box / 2, y_next + (row_h - box) / 2,
                           box, box, stroke=1, fill=0)
                xx += w
            c.setStrokeColor(LINE_SOFT)
            c.setLineWidth(0.5)
            c.line(f.x, y_next, f.right, y_next)
            y = y_next
            day += 1

        if week_no < len(WEEKS):          # у последней недели итог входит в месяц
            yy = y - sum_h
            panel(c, f.x, yy, f.w, sum_h, fill=GOLD_BG, stroke=LINE, radius=0)
            label = f"Итог недели {week_no}"
            c.setFont(BOLD, 7.2)
            c.setFillColor(ACCENT)
            c.drawString(f.x + 4, yy + sum_h / 2 - 2.4, label)
            c.setFont(BODY, 6.6)
            c.setFillColor(MUTED)
            c.drawString(f.x + 4 + c.stringWidth(label, BOLD, 7.2) + 7,
                         yy + sum_h / 2 - 2.4,
                         "дней с ритмом ____ из 7   ·   подтягиваний всего ____   ·   "
                         "лучший результат ____   ·   фортепиано: ____ дней / ____ минут")
            y = yy

    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.rect(f.x, y, f.w, table_top - y, stroke=1, fill=0)

    # итог месяца
    yb = y - gap - month_h
    panel(c, f.x, yb, f.w, month_h, fill=TINT, stroke=LINE, radius=4)
    c.setFillColor(GOLD)
    c.rect(f.x, yb, 2.2, month_h, stroke=0, fill=1)
    c.setFont(BOLD, 8)
    c.setFillColor(ACCENT)
    c.drawString(f.x + 8, yb + month_h - 12, "ИТОГ МЕСЯЦА")
    c.setFont(BODY, 7)
    c.setFillColor(INK)
    c.drawString(f.x + 8 + c.stringWidth("ИТОГ МЕСЯЦА", BOLD, 8) + 6,
                 yb + month_h - 12,
                 "дней с ритмом ____ из 31   ·   подтягиваний всего ____   ·   "
                 "личный рекорд ____   ·   фортепиано: ____ дней / ____ минут")
    c.setFont(BODY, 6.4)
    c.setFillColor(MUTED)
    c.drawString(f.x + 8, yb + 5,
                 "Пустая клетка — это данные, а не провал: за срыв и за эмоции ничего "
                 "не вычитается. Своё дело (IT, проект) — запиши в заметку словом.")

    page_footer(c, "Отметки ставит сам ребёнок. Взрослый спрашивает «как прошло?», "
                   "а не «сделал?».", right=f"версия {VERSION}")
    c.showPage()


# ------------------------------------------------------------------ 11. итоги недели
DAYS_SHORT = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

REWARD_RULES = [
    ("5 дней из 7", "выбираешь ты, куда идём вдвоём в выходные"),
    ("меньше 5", "поощрения нет — и нет упрёков: смотрим, что мешало"),
    ("болел, дорога", "эти дни не считаются, порог пересчитываем вместе"),
]


def weekly_results(c):
    """Карточка разговора о неделе: цифры ребёнка и правило поощрения."""
    two_up(c, _weekly_card)
    c.showPage()


def _weekly_card(c, W, H, m=11 * MM):
    top = page_header(c, "Итоги недели", "разговор на 5 минут, вместе с ребёнком",
                      width=W, height=H, m=m)
    x, right = m, W - m
    width = right - x
    ROWS_GAP, LINE_GAP = 32, 24        # шаг строк с цифрами и линий разговора

    c.setFont(SERIF_BOLD, 25)
    c.setFillColor(ACCENT)
    c.drawString(x, top - 19, "Итоги недели")
    c.setFont(BODY, 10.4)
    c.setFillColor(MUTED)
    c.drawString(x, top - 35, "Цифры здесь — его собственные: с братом они "
                              "не сравниваются никогда.")
    y = top - 54

    field_line(c, x, y, x + 46 * MM, "Имя:", size=10.4)
    field_line(c, x + 53 * MM, y, right, "Неделя № / даты:", size=10.4)
    y -= 28

    # неделя целиком
    c.setFont(BOLD, 10)
    c.setFillColor(ACCENT2)
    c.drawString(x, y, "НЕДЕЛЯ ЦЕЛИКОМ — ГДЕ БЫЛ РИТМ")
    y -= 11
    cell_w = width / 7
    cell_bottom, cell_h = y - 38, 38
    for i, day in enumerate(DAYS_SHORT):
        cx = x + i * cell_w
        panel(c, cx + 1.5, cell_bottom, cell_w - 3, cell_h, fill=CREAM,
              stroke=LINE, radius=3)
        c.setFont(BODY, 8.4)
        c.setFillColor(MUTED)
        c.drawCentredString(cx + cell_w / 2, cell_bottom + cell_h - 13, day)
        c.setStrokeColor(DASH)
        c.setLineWidth(0.7)
        box = 13
        c.rect(cx + cell_w / 2 - box / 2, cell_bottom + 7, box, box, stroke=1, fill=0)
    y = cell_bottom - 14
    c.setFont(BODY, 8.4)
    c.setFillColor(MUTED)
    c.drawString(x, y, "Ритм — когда в «Дневнике силы» отмечены все четыре клетки.")
    y -= 24

    # цифры недели
    for name, blank in (("Дней с ритмом", "_____ из _____"),
                        ("Турник: было → стало", "_____ → _____     рекорд _____"),
                        ("Фортепиано", "_____ дней, _____ минут")):
        c.setFont(BOLD, 11.6)
        c.setFillColor(ACCENT)
        c.drawString(x, y, name)
        c.setFont(BODY, 11.2)
        c.setFillColor(MUTED)
        c.drawString(x + 58 * MM, y, blank)
        y -= ROWS_GAP
    y -= 4

    # разговор
    c.setFont(BOLD, 10)
    c.setFillColor(ACCENT2)
    c.drawString(x, y, "РАЗГОВОР")
    y -= 19
    for label in ("Что было труднее всего и как справился:",
                  "Что помогло:",
                  "На следующей неделе попробую:"):
        c.setFont(BOLD, 11.6)
        c.setFillColor(ACCENT)
        c.drawString(x, y, label)
        y -= 16
        for _ in range(2):
            dotted(c, x + 3, right, y, LINE, 0.8)
            y -= LINE_GAP
        y -= 5

    # договорённость о поощрении
    box_bottom = m + 27
    box_h = y - 3 - box_bottom
    panel(c, x, box_bottom, width, box_h, fill=GOLD_BG, stroke=LINE, radius=4)
    c.setFillColor(GOLD)
    c.rect(x, box_bottom, 2.8, box_h, stroke=0, fill=1)

    bi = box_bottom + box_h                     # верх блока, дальше идём вниз
    c.setFont(BOLD, 11.6)
    c.setFillColor(ACCENT)
    c.drawString(x + 13, bi - 20, "Договорённость о поощрении")

    rule_left = x + 13
    rule_val = x + 50 * MM
    ri = bi - 36
    for cond, what in REWARD_RULES:
        c.setFont(BOLD, 9.8)
        c.setFillColor(GOLD)
        c.drawString(rule_left, ri - 8, cond)
        draw_wrapped(c, what, rule_val, ri, right - 14 - rule_val, 9.6, 12,
                     BODY, BODY, INK)
        ri -= 34

    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(rule_left, ri + 8, right - 14, ri + 8)

    c.setFont(BODY, 9)
    c.setFillColor(MUTED)
    c.drawString(rule_left, ri - 8, "Не отменяется за плохой день и не уменьшается "
                                    "за срыв: эмоции вне счёта.")
    c.drawString(rule_left, ri - 22, "Поощрение — время вместе, а не покупка. "
                                     "Итог подписываем вдвоём.")

    field_line(c, rule_left, ri - 47, right - 14, "Порог на эту неделю:", size=9.4)
    field_line(c, rule_left, ri - 70, right - 14,
               "Поощрение, о котором договорились:", size=9.4)
    if ri - 70 < box_bottom + 8:
        raise SystemExit("карточка недели: блок правил не влезает")

    field_line(c, x, m + 12, x + 60 * MM, "Ребёнок:", size=9.6)
    field_line(c, x + 70 * MM, m + 12, right, "Взрослый:", size=9.6)
    page_footer(c, "Считается по отметкам «Дневника силы».", width=W, m=m)


# ------------------------------------------------------------------ обложка
PACK_CONTENTS = [
    ("Плакат на холодильник", "пять правил, стоп-лист, три фразы-выручалочки", "1 стр. A4"),
    ("Карта утра", "пять пунктов режима на каждый день месяца", "1 стр. A4 на ребёнка"),
    ("Карта паузы", "три своих способа разрядки + слова ремонта", "1 лист = 2 карточки A5"),
    ("Шкала 1–5", "«спокоен → взрыв», называет сам ребёнок", "1 лист = 2 карточки A5"),
    ("Журнал наставника", "три строки после каждой встречи", "1 стр. A4 на месяц"),
    ("Копилка добрых дел", "ежедневный вклад: брату и родителям", "1 стр. A4 на ребёнка"),
    ("Проверка «я не сбился»", "семь вопросов раз в две недели", "1 лист = 2 бланка A5"),
    ("Памятка папе", "зона папы, сверка, момент вспышки", "1 стр. A4"),
    ("Памятка маме", "что говорить и чего не говорить про ревность", "1 стр. A4"),
    ("Дневник силы", "отметка за каждый день + итоги недели и месяца", "1 стр. A4 на ребёнка"),
    ("Итоги недели", "разговор на 5 минут и договорённость о поощрении", "1 лист = 2 карточки A5"),
]


def cover(c):
    top = page_header(c, "Комплект наставника", "печатные материалы")
    f = Flow(c, M, A4W - M, top)

    f.para("Печатные материалы", size=22, leading=26, color=ACCENT,
           font=SERIF_BOLD, space_after=2)
    f.para("Двое братьев, 8 и 10 лет. Всё, что нужно распечатать, — в этом файле по порядку. "
           "Печатать на A4, масштаб 100 %, поля «нет» или 5 мм.", size=9,
           color=MUTED, space_after=12)

    y = f.y
    for i, (name, what, how) in enumerate(PACK_CONTENTS, 1):
        row_h = 34
        c.setFont(SERIF_BOLD, 13)
        c.setFillColor(GOLD)
        c.drawRightString(f.x + 15, y - 13, f"{i}")
        c.setFont(BOLD, 10.4)
        c.setFillColor(ACCENT)
        c.drawString(f.x + 24, y - 10, name)
        draw_wrapped(c, what, f.x + 24, y - 15, f.w - 24, 8.4, 10.4, BODY, BODY, MUTED)
        c.setFont(BODY, 7.6)
        c.setFillColor(MUTED)
        c.drawRightString(f.right, y - 10, how)
        y -= row_h
        if i < len(PACK_CONTENTS):
            hline(c, f.x + 24, f.right, y + 8, LINE_SOFT, 0.6)

    f.y = y - 12
    kv_panel(c, f, [
        ("Один набор правил",
         "у семьи один набор правил, его держит папа. Наставник усиливает, а не заменяет."),
        ("Без рейтингов",
         "нигде нет баллов, звёздочек и сравнений братьев — сознательно и навсегда."),
    ], label_w=52 * MM, fill=TINT, space_after=6)

    f.bullets([
        "**Плакат** — на холодильник, туда, где смотришь каждый день.",
        "**Бланки** — по одному комплекту в месяц на каждого мальчика: карта утра, "
        "копилка и дневник силы; журнал и проверка — у наставника.",
        "**Памятки** — отдать лично: папе рядом с плакатом, маме со словами "
        "«это шпаргалка, а не оценка».",
    ], size=8.6, marker_color=ACCENT2, gap=3)

    qr_stamp(c, f.right, M + 40 * MM, 22 * MM, "Полный свод в телефоне")
    c.setFont(BODY, 7.4)
    c.setFillColor(MUTED)
    draw_wrapped(c, "Правила, 13 протоколов и план на 90 дней — на странице свода. "
                    "Работает без интернета: на iPhone «Поделиться» → «На экран Домой».",
                 f.x, M + 30 * MM, f.w - 46 * MM, 7.4, 9.6, BODY, BODY, MUTED)

    page_footer(c, "Карманный свод: " + PAGES_URL, right=f"версия {VERSION}")
    c.showPage()


# ------------------------------------------------------------------ сборка
VERSION = "1.0 · 30.10.2026"

DOCUMENTS = [
    ("01_na_holodilnik_A4.pdf", "плакат на холодильник (A4)", A4W, A4H, _fridge_page),
    ("01b_na_holodilnik_A5_2up.pdf", "плакат на холодильник (A5 ×2)", A4H, A4W, fridge_a5_2up),
    ("02_karta_utra.pdf", "карта утра на месяц", A4W, A4H, morning_card),
    ("03_karta_pauzy.pdf", "карта паузы (2 шт. на листе)", A4H, A4W, pause_cards),
    ("04_shkala_1_5.pdf", "шкала 1–5 (2 шт. на листе)", A4H, A4W, scale_cards),
    ("05_zhurnal_nastavnika.pdf", "журнал наставника на месяц", A4W, A4H, mentor_journal),
    ("06_kopilka_dobryh_del.pdf", "копилка добрых дел на месяц", A4W, A4H, good_deeds),
    ("07_proverka_ya_sbilsya.pdf", "7 вопросов «я не сбился» (2 шт.)", A4H, A4W, self_check),
    ("08_pamyatka_pape.pdf", "памятка папе", A4W, A4H, memo_dad),
    ("09_pamyatka_mame.pdf", "памятка маме", A4W, A4H, memo_mom),
    ("10_dnevnik_sily.pdf", "дневник силы на месяц", A4W, A4H, daily_diary),
    ("11_itogi_nedeli.pdf", "итоги недели (2 шт. на листе)", A4H, A4W, weekly_results),
]


def main():
    OUT.mkdir(exist_ok=True)
    DOCS_PRINT.mkdir(parents=True, exist_ok=True)

    for name, title, w, h, fn in DOCUMENTS:
        path = OUT / name
        c = canvas.Canvas(str(path), pagesize=(w, h))
        c.setTitle(f"Наставник — {title}")
        c.setAuthor("Комплект наставника")
        c.setSubject("Печатные материалы к карманному своду наставника")
        fn(c)
        c.save()
        (DOCS_PRINT / name).write_bytes(path.read_bytes())
        print(f"  {name:34s} {path.stat().st_size // 1024:>3} KB  — {title}")

    # один файл на печать: обложка + все листы по порядку
    pack_path = OUT / "00_komplekt_na_pechat.pdf"
    pc = canvas.Canvas(str(pack_path), pagesize=(A4W, A4H))
    pc.setTitle("Наставник — печатные материалы (весь комплект)")
    cover(pc)
    for name, title, w, h, fn in DOCUMENTS:
        if name.startswith("01b"):
            continue          # A5-вариант плаката остаётся отдельным файлом
        pc.setPageSize((w, h))
        fn(pc)
    pc.save()
    (DOCS_PRINT / pack_path.name).write_bytes(pack_path.read_bytes())
    print(f"  {pack_path.name:34s} {pack_path.stat().st_size // 1024:>3} KB  — весь комплект одним файлом")

    qr_standalone(OUT / "qr_nastavnik.png")
    (DOCS_PRINT / "qr_nastavnik.png").write_bytes((OUT / "qr_nastavnik.png").read_bytes())

    (OUT / "README.md").write_text(PRINT_README, encoding="utf-8")
    print("готово: print/ и docs/print/")


PRINT_README = f"""# Печатные материалы

Собраны скриптом `build_print.py` из формулировок комплекта. Пересобрать:
`python3 build_print.py` (нужны `reportlab` и `segno`: `pip install -r requirements.txt`,
и шрифт DejaVu с кириллицей — в Linux ставится пакетом `fonts-dejavu-core`).

PDF продублированы в `docs/print/` — их можно открыть с телефона по ссылке
{PAGES_URL}print/...

## Что и сколько печатать

| Файл | Что это | Сколько | Как |
|---|---|---|---|
| `00_komplekt_na_pechat.pdf` | **весь комплект одним файлом**: обложка + все листы по порядку | 10 страниц | проще всего: печать «все страницы», дальше разрезать карточки |
| `01_na_holodilnik_A4.pdf` | пять правил + стоп-лист + три фразы | 1–2 | A4, 100 %. Один лист на кухню, второй — наставнику в папку |
| `01b_na_holodilnik_A5_2up.pdf` | то же в размере A5 | по желанию | A4, разрезать пополам: два маленьких плаката (холодильник + машина) |
| `02_karta_utra.pdf` | карта утра на месяц | по 1 на мальчика в месяц | A4. Имя вписать, остальное ребёнок отмечает сам |
| `03_karta_pauzy.pdf` | карта паузы, 2 шт. на листе | 1 лист (2 карточки) | A4, разрезать, лучше заламинировать: карточку носят с собой |
| `04_shkala_1_5.pdf` | шкала 1–5, 2 шт. на листе | 1 лист | A4, разрезать. Вводить на нейтральных примерах, а не в ссоре |
| `05_zhurnal_nastavnika.pdf` | журнал на месяц (12 встреч) | 1 в месяц | A4, двусторонняя печать не нужна |
| `06_kopilka_dobryh_del.pdf` | копилка добрых дел на месяц | по 1 на мальчика | A4 |
| `07_proverka_ya_sbilsya.pdf` | 7 вопросов, 2 бланка на листе | 1 лист на месяц | A4, разрезать: одна проверка на две недели |
| `08_pamyatka_pape.pdf` | памятка папе | 1 | A4. Повесить рядом с плакатом |
| `09_pamyatka_mame.pdf` | памятка маме | 1 | A4. Отдать лично и сказать: «это шпаргалка, а не оценка» |
| `10_dnevnik_sily.pdf` | дневник силы на месяц: отметка за каждый день + итоги недель и месяца | по 1 на мальчика в месяц | A4. Имя вписать, отметки ставит сам ребёнок |
| `11_itogi_nedeli.pdf` | итоги недели: разговор на 5 минут и договорённость о поощрении, 2 шт. на листе | 1 лист на мальчика в неделю | A4, разрезать: карточка на неделю каждому |
| `qr_nastavnik.png` | QR на свод | сколько нужно | Наклейка на папку, холодильник, бланки |

## Настройки принтера

- Масштаб **100 %** («реальный размер», не «по размеру страницы»).
- Поля: «нет» или минимальные 5 мм.
- Цветной вариант задуман так, чтобы читаться и в ч/б: всё важное различается
  толщиной линий и подписями, а не только цветом.
"""


if __name__ == "__main__":
    main()
