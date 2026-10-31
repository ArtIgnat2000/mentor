import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse

from family.build_public import build, build_all
from family.content import load_contour

ROOT = Path(__file__).resolve().parents[1]


class PublicFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.docs = Path(cls.tmp.name) / "docs"
        cls.docs.mkdir()
        (cls.docs / "index.html").write_text("<!doctype html><title>Наставник</title>", encoding="utf-8")
        # В модульном тесте PDF заменяются заглушками; наличие настоящих файлов
        # проверяется отдельно в test_published_resources_exist.
        for contour in ("children", "family", "parents"):
            for page in load_contour(contour)["pages"]:
                for resource in page["resources"]:
                    target = cls.docs / contour / resource["href"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"%PDF-1.4\n")
        build_all(cls.docs)
        cls.children = cls.docs / "children"
        cls.family = cls.docs / "family"
        cls.parents = cls.docs / "parents"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _text(self, out):
        return "\n".join(
            p.read_text(encoding="utf-8")
            for p in out.rglob("*")
            if p.suffix in {".html", ".js", ".json", ".webmanifest", ".css", ".svg"}
        )

    def _check_links_and_cache(self, out, prefix):
        manifest = json.loads((out / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["scope"], "./")
        self.assertEqual(manifest["start_url"], "./")
        sw = (out / "sw.js").read_text(encoding="utf-8")
        self.assertIn(f'const CACHE = "{prefix}', sw)
        self.assertIn(f'k.startsWith("{prefix}")', sw)
        files = json.loads(re.search(r"const FILES = (\[.*?\]);", sw).group(1))
        for name in files:
            self.assertTrue((out / name).exists(), name)
        for page in out.glob("*.html"):
            for href in re.findall(r'(?:href|src)="([^"]+)"', page.read_text(encoding="utf-8")):
                if href.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = unquote(urlparse(href).path)
                self.assertTrue((page.parent / path).exists(), (page.name, href))

    def test_children_section_is_separate_and_child_friendly(self):
        text = self._text(self.children)
        self.assertIn("Мой раздел", text)
        self.assertIn("Наши правила", text)
        self.assertIn("Если трудно", text)
        self.assertIn("Мои листы", text)
        self.assertIn("kids-hero.svg", text)
        self.assertNotIn("metodika-pylesos", text)
        self.assertNotIn("отказывается пылесосить", text)
        self.assertNotIn("content/parents", text)
        self.assertNotIn('type="password"', text)
        self._check_links_and_cache(self.children, "children-public-")

    def test_family_export_links_to_children_and_parents(self):
        text = self._text(self.family)
        self.assertIn("Семейный справочник", text)
        self.assertIn("../children/", text)
        self.assertIn("../parents/", text)
        self.assertNotIn("metodika-pylesos", text)
        self._check_links_and_cache(self.family, "family-public-")

    def test_parents_export_is_open_complete_and_searchable(self):
        text = self._text(self.parents)
        for expected in (
            "Общие правила для взрослых", "Правила для папы", "Правила для мамы",
            "Правила для детей", "Типовые ситуации", "Печатные формы",
            "Ежедневные дела", "Добрые дела", "Зарядка и подтягивания",
            "Карта утра", "Пауза и шкала 1–5", "Итоги недели", "Самопроверка взрослого",
            "Методика: отказ пылесосить", "Пример заполнения", "Пример анализа",
            'data-search', 'data-filter', "17_ezhednevny_list_del.pdf",
        ):
            self.assertIn(expected, text)
        self.assertNotIn('type="password"', text)
        self.assertNotIn('action="/login"', text)
        self.assertNotIn("_template-metodika", text)
        self.assertEqual(len(load_contour("parents")["pages"]), 15)
        situations = next(p for p in load_contour("parents")["pages"] if p["slug"] == "situacii")
        self.assertGreaterEqual(len(situations["entries"]), 12)
        for name in (
            "index.html", "situacii.html", "pechatnye-formy.html",
            "forma-ezhednevnye-dela.html", "print-forma-ezhednevnye-dela.html",
            "pravila-papy.html", "pravila-mamy.html", "pravila-detey.html",
            "metodika-pylesos.html",
        ):
            self.assertTrue((self.parents / name).is_file(), name)
        self._check_links_and_cache(self.parents, "parents-public-")

    def test_public_caches_are_isolated_by_contour(self):
        for contour, out in (("children", self.children), ("family", self.family), ("parents", self.parents)):
            sw = (out / "sw.js").read_text(encoding="utf-8")
            self.assertIn(f'k.startsWith("{contour}-public-")', sw)
            for other in ("children", "family", "parents"):
                if other != contour:
                    self.assertNotIn(f'k.startsWith("{other}-public-")', sw)

    def test_published_resources_exist(self):
        docs = ROOT / "docs"
        for contour in ("children", "family", "parents"):
            for page in load_contour(contour)["pages"]:
                for resource in page["resources"]:
                    target = docs / contour / resource["href"]
                    self.assertTrue(target.is_file(), f"{contour}: {resource['href']}")

    def test_build_rejects_unknown_contour(self):
        with self.assertRaises(ValueError):
            build(self.docs / "unknown", "unknown")


if __name__ == "__main__":
    unittest.main()
