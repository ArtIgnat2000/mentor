import json
import re
import tempfile
import unittest
from pathlib import Path

from family.build_public import build, build_all


class PublicFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.docs = Path(cls.tmp.name) / "docs"
        build_all(cls.docs)
        cls.family = cls.docs / "family"
        cls.parents = cls.docs / "parents"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _text(self, out):
        return "\n".join(
            p.read_text(encoding="utf-8")
            for p in out.rglob("*")
            if p.suffix in {".html", ".js", ".json", ".webmanifest", ".css"}
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
            for href in re.findall(r'(?:href|src)="([^"#]+)"', page.read_text(encoding="utf-8")):
                if href.startswith(("http://", "https://", "mailto:")):
                    continue
                self.assertTrue((page.parent / href).exists(), (page.name, href))

    def test_family_export_does_not_include_parent_methods(self):
        text = self._text(self.family)
        self.assertIn("Наши правила", text)
        self.assertNotIn("metodika-pylesos", text)
        self.assertNotIn("отказывается пылесосить", text)
        self.assertNotIn("content/parents", text)
        self._check_links_and_cache(self.family, "family-public-")

    def test_parents_export_is_open_and_complete(self):
        text = self._text(self.parents)
        self.assertIn("Правила для папы", text)
        self.assertIn("Правила для мамы", text)
        self.assertIn("Методика: отказ пылесосить", text)
        self.assertIn("отказывается пылесосить", text)
        self.assertIn("Раздел открытый", text)
        self.assertNotIn('type="password"', text)
        self.assertNotIn('action="/login"', text)
        self.assertNotIn("_template-metodika", text)
        for name in (
            "index.html",
            "pravila-papy.html",
            "pravila-mamy.html",
            "metodika-pylesos.html",
            "print-pravila-papy.html",
            "print-pravila-mamy.html",
            "print-metodika-pylesos.html",
        ):
            self.assertTrue((self.parents / name).is_file(), name)
        self._check_links_and_cache(self.parents, "parents-public-")

    def test_public_caches_are_isolated_by_contour(self):
        family_sw = (self.family / "sw.js").read_text(encoding="utf-8")
        parents_sw = (self.parents / "sw.js").read_text(encoding="utf-8")
        self.assertIn('k.startsWith("family-public-")', family_sw)
        self.assertIn('k.startsWith("parents-public-")', parents_sw)
        self.assertNotIn('k.startsWith("parents-public-")', family_sw)
        self.assertNotIn('k.startsWith("family-public-")', parents_sw)

    def test_build_rejects_unknown_contour(self):
        with self.assertRaises(ValueError):
            build(self.docs / "unknown", "unknown")


if __name__ == "__main__":
    unittest.main()
