import http.cookiejar
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from family.server import AppServer


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class FamilyAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.family = AppServer(("127.0.0.1", 0), "family", cls.tmp.name)
        cls.parents = AppServer(("127.0.0.1", 0), "parents", cls.tmp.name)
        cls.ft = threading.Thread(target=cls.family.serve_forever, daemon=True)
        cls.pt = threading.Thread(target=cls.parents.serve_forever, daemon=True)
        cls.ft.start()
        cls.pt.start()
        cls.fbase = f"http://127.0.0.1:{cls.family.server_port}"
        cls.pbase = f"http://127.0.0.1:{cls.parents.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.family.shutdown()
        cls.parents.shutdown()
        cls.tmp.cleanup()

    def _get(self, base, path, opener=None):
        op = opener or urllib.request.build_opener()
        try:
            with op.open(base + path, timeout=5) as r:
                return r.status, r.headers, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8")

    def test_family_does_not_leak_parent_method(self):
        status, headers, body = self._get(self.fbase, "/")
        self.assertEqual(status, 200)
        self.assertNotIn("отказывается пылесосить", body)
        self.assertNotIn("metodika-pylesos", body)
        status, _, body = self._get(self.fbase, "/p/metodika-pylesos")
        self.assertEqual(status, 404)

    def test_parent_requires_login_and_no_store(self):
        jar = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(jar))
        status, headers, body = self._get(self.pbase, "/p/metodika-pylesos", op)
        self.assertEqual(status, 303)
        self.assertEqual(headers.get("Location"), "/login")
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        token = self.parents.store.bootstrap_token(create=True)
        status, _, setup = self._get(self.pbase, "/setup", op)
        csrf = re.search(r'name="csrf" value="([^"]+)"', setup).group(1)
        data = f"csrf={csrf}&token={token}&name=Папа&username=papa&password=very-secret-password".encode()
        req = urllib.request.Request(self.pbase + "/setup", data=data, headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": self.pbase})
        with op.open(req, timeout=5) as r:
            self.assertEqual(r.status, 200)
        status, headers, body = self._get(self.pbase, "/p/metodika-pylesos", op)
        self.assertEqual(status, 200)
        self.assertIn("Пылесос", body)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        status, _, sw = self._get(self.pbase, "/sw.js", op)
        self.assertNotIn("/p/", sw)

    def test_parent_sw_does_not_precache_private_pages(self):
        status, _, sw = self._get(self.pbase, "/sw.js")
        self.assertNotIn("metodika-pylesos", sw)
        self.assertIn("/offline", sw)


if __name__ == "__main__":
    unittest.main()
