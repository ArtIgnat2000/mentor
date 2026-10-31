import json
import re
import tempfile
import unittest
from pathlib import Path

from family.build_public import build


class PublicFamilyTests(unittest.TestCase):
    def test_public_export_contains_only_family_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build(Path(tmp) / "family")
            text = "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.suffix in {".html", ".js", ".json", ".webmanifest", ".css"})
            self.assertIn("Наши правила", text)
            self.assertNotIn("metodika-pylesos", text)
            self.assertNotIn("отказывается пылесосить", text)
            self.assertNotIn("content/parents", text)
            manifest = json.loads((out / "manifest.webmanifest").read_text(encoding="utf-8"))
            self.assertEqual(manifest["scope"], "./")
            self.assertEqual(manifest["start_url"], "./")
            sw = (out / "sw.js").read_text(encoding="utf-8")
            files = json.loads(re.search(r"const FILES = (\[.*?\]);", sw).group(1))
            for name in files:
                self.assertTrue((out / name).exists(), name)
            for page in out.glob("*.html"):
                for href in re.findall(r'(?:href|src)="(\./[^"#]+)"', page.read_text(encoding="utf-8")):
                    self.assertTrue((out / href).exists(), (page.name, href))


if __name__ == "__main__":
    unittest.main()
