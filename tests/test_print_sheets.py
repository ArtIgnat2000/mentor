"""Проверки новых листов и сборки PDF: python -m unittest discover -s tests -v."""
import contextlib
import io
from pathlib import Path
import re
import tempfile
import unittest

from reportlab.pdfgen import canvas

import build_print as bp
import build_site as bs
from printkit import A4H, A4W, MM


def pdf_page_count(data):
    # ReportLab оставляет объекты страниц несжатыми; потоки содержимого сжаты.
    return len(re.findall(rb"/Type\s*/Page\b", data))


class UsefulDeedsTests(unittest.TestCase):
    def test_seven_habits_and_separate_exercise_and_bar(self):
        self.assertEqual(len(bp.DEED_COLUMNS), 7)
        self.assertEqual(bp.DEED_COLUMNS[0][0], "Зарядка")
        self.assertEqual(bp.DEED_COLUMNS[1][0], "Турник")
        self.assertEqual(bp.DEED_COLUMNS[1][3], "reps")
        self.assertEqual(bp.DEED_COLUMNS[-1][0], "Свой пункт")

    def test_columns_fill_page_without_empty_strip(self):
        available = A4W - 2 * bp.M
        for weekly in (True, False):
            with self.subTest(weekly=weekly):
                cols, widths = bp._deeds_columns(weekly, available)
                self.assertEqual(len(cols), len(widths))
                self.assertAlmostEqual(sum(widths), available)
                self.assertTrue(all(w > 10 * MM for w in widths))
                self.assertEqual(len(cols), 8 if weekly else 9)
                if weekly:
                    self.assertAlmostEqual(widths[1], widths[-1])
                    self.assertGreaterEqual(widths[1], 23 * MM)

    def test_two_portrait_a4_pages_render(self):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(A4W, A4H))
        bp.useful_deeds(c)
        c.save()
        data = buf.getvalue()
        self.assertEqual(pdf_page_count(data), 2)
        boxes = re.findall(rb"/MediaBox\s*\[([^\]]+)\]", data)
        self.assertEqual(len(boxes), 2)
        for box in boxes:
            x0, y0, x1, y1 = map(float, box.split())
            self.assertAlmostEqual(x1 - x0, A4W, places=3)
            self.assertAlmostEqual(y1 - y0, A4H, places=3)
            self.assertLess(x1, y1)

    def test_build_copies_and_full_pack(self):
        old_out, old_docs = bp.OUT, bp.DOCS_PRINT
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bp.OUT = root / "print"
            bp.DOCS_PRINT = root / "docs" / "print"
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    bp.main()
            finally:
                bp.OUT, bp.DOCS_PRINT = old_out, old_docs

            for name, _, _, _, _ in bp.DOCUMENTS:
                self.assertEqual((bp.OUT / name).read_bytes(),
                                 (bp.DOCS_PRINT / name).read_bytes())
            sheets = (bp.OUT / "12_listy_poleznyh_del.pdf").read_bytes()
            self.assertEqual(pdf_page_count(sheets), 2)
            pack = (bp.OUT / "00_komplekt_na_pechat.pdf").read_bytes()
            expected = 1 + sum(2 if name == "12_listy_poleznyh_del.pdf" else 1
                               for name, _, _, _, _ in bp.DOCUMENTS
                               if not name.startswith("01b"))
            self.assertEqual(pdf_page_count(pack), expected)
            self.assertEqual(expected, 17)
            readme = (bp.OUT / "README.md").read_text(encoding="utf-8")
            self.assertIn("12_listy_poleznyh_del.pdf", readme)
            self.assertIn("17 страниц", readme)
            rules = (bp.OUT / "16_pravila_semyi_3xA4.pdf").read_bytes()
            self.assertEqual(pdf_page_count(rules), 3)
            self.assertEqual(rules, (bp.DOCS_PRINT / "16_pravila_semyi_3xA4.pdf").read_bytes())
            for name in ("13m_pravila_detey_mobile.pdf", "14m_pravila_papy_mobile.pdf",
                         "15m_pravila_mamy_mobile.pdf", "16m_pravila_semyi_mobile.pdf"):
                data = (bp.OUT / name).read_bytes()
                self.assertGreater(pdf_page_count(data), 0)
                self.assertEqual(data, (bp.DOCS_PRINT / name).read_bytes())
                boxes = re.findall(rb"/MediaBox\s*\[([^\]]+)\]", data)
                for box in boxes:
                    x0, y0, x1, y1 = map(float, box.split())
                    self.assertLess(x1 - x0, y1 - y0)
                    self.assertLessEqual(x1 - x0, bp.MOBILE_W + 1)


class FamilyRulesTests(unittest.TestCase):
    def test_children_rules_have_can_and_cannot(self):
        self.assertEqual(len(bp.CHILDREN_RULES), 6)
        for rule, can, cannot in bp.CHILDREN_RULES:
            self.assertTrue(rule and can and cannot)

    def test_adult_rules_have_need_can_cannot(self):
        for data in (bp.DAD_RULES, bp.MOM_RULES):
            self.assertEqual(set(data), {"need", "can", "cannot", "phrases"})
            for key in ("need", "can", "cannot"):
                self.assertGreaterEqual(len(data[key]), 4)

    def test_three_portrait_a4_pages_render(self):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(A4W, A4H))
        bp.family_rules_children(c)
        bp.family_rules_dad(c)
        bp.family_rules_mom(c)
        c.save()
        data = buf.getvalue()
        self.assertEqual(pdf_page_count(data), 3)
        boxes = re.findall(rb"/MediaBox\s*\[([^\]]+)\]", data)
        self.assertEqual(len(boxes), 3)
        for box in boxes:
            x0, y0, x1, y1 = map(float, box.split())
            self.assertAlmostEqual(x1 - x0, A4W, places=3)
            self.assertAlmostEqual(y1 - y0, A4H, places=3)
            self.assertLess(x1, y1)


class MobileRulesTests(unittest.TestCase):
    def test_mobile_html_pages_are_generated(self):
        old_out = bs.OUT
        with tempfile.TemporaryDirectory() as tmp:
            bs.OUT = Path(tmp) / "docs"
            try:
                mobile = bs.build_mobile_rules()
            finally:
                bs.OUT = old_out
            for name in ("index.html", "detyam.html", "pape.html", "mame.html"):
                page = (mobile / name).read_text(encoding="utf-8")
                self.assertIn('name="viewport"', page)
                self.assertIn("<h1>", page)
            children = (mobile / "detyam.html").read_text(encoding="utf-8")
            self.assertIn("Можно:", children)
            self.assertIn("Нельзя:", children)
            dad = (mobile / "pape.html").read_text(encoding="utf-8")
            self.assertIn("НУЖНО", dad)
            self.assertIn("НЕЛЬЗЯ", dad)


if __name__ == "__main__":
    unittest.main()
