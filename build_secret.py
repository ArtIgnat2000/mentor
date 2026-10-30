#!/usr/bin/env python3
"""Закрытый раздел «Родителям» — docs/semya.html.

Текст лежит в secret_roditeli.md и в репозиторий не попадает (.gitignore).
На сайте остаётся только шифротекст: AES-256-GCM, ключ из кода через
PBKDF2-SHA256 (310 000 итераций). Расшифровка — в браузере, через WebCrypto.
Без кода страница показывает форму ввода и больше ничего.

Собрать (код спросит):

    python3 build_secret.py

Собрать с готовым кодом и сразу получить ссылку:

    PARENTS_CODE='nash-kod-47' python3 build_secret.py
"""

from __future__ import annotations

import base64
import getpass
import hmac
import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import build_site

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "secret_roditeli.md"
OUT = ROOT / "docs" / "semya.html"
PAGE_URL = build_site.PAGES_URL + "semya.html"

ITERATIONS = 310_000
SALT_LEN, IV_LEN = 16, 12

GATE_CSS = """
.gate{max-width:440px;margin:8vh auto 0;padding:26px 22px}
.gate h1{font-size:1.35rem;margin:0 0 6px}
.gate p{color:#5c655f;font-size:.92rem;line-height:1.5;margin:0 0 14px}
.gate label{display:block;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;
  color:#5c655f;margin-bottom:6px}
.gate-row{display:flex;gap:8px}
.gate input{flex:1;min-width:0;font:inherit;font-size:1rem;padding:11px 12px;border-radius:10px;
  border:1px solid #ddd6c8;background:#fffdf8;color:#1c2321}
.gate input:focus{outline:2px solid #b58a2b;outline-offset:1px;border-color:#b58a2b}
.gate button{font:inherit;font-size:.95rem;padding:11px 16px;border-radius:10px;border:0;
  background:#16302b;color:#fffdf8;cursor:pointer}
.gate button:disabled{opacity:.55;cursor:default}
.gate .err{color:#8a3b2b;font-size:.86rem;min-height:1.2em;margin:10px 0 0}
.gate .hint{color:#8a9088;font-size:.78rem;margin:14px 0 0;line-height:1.45}
.secret{max-width:46rem;margin:0 auto}
.secret .bar{display:flex;justify-content:space-between;align-items:center;gap:12px;
  margin:0 0 14px;font-size:.82rem;color:#5c655f}
.secret .bar button{font:inherit;font-size:.82rem;padding:7px 12px;border-radius:8px;
  border:1px solid #ddd6c8;background:#fffdf8;color:#2f6b5b;cursor:pointer}
@media print{.secret .bar,.gate{display:none}}
"""

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#16302b">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="referrer" content="no-referrer">
<title>Родителям</title>
<style>__CSS__</style>
<style>__GATE_CSS__</style>
</head>
<body>
<a id="top"></a>
<main>
  <section class="card gate" id="gate">
    <h1>Родителям</h1>
    <p>Раздел открывается кодом. Код знают только папа и мама.</p>
    <form id="f" autocomplete="off">
      <label for="c">Код</label>
      <div class="gate-row">
        <input id="c" type="password" inputmode="text" autocapitalize="off"
               autocorrect="off" spellcheck="false" enterkeyhint="go">
        <button id="b" type="submit">Открыть</button>
      </div>
      <p class="err" id="e"></p>
    </form>
    <p class="hint">Если код не подходит — проверьте раскладку и дефисы.
      Раздел закроется сам через 15 минут без действий.</p>
    <noscript><p class="err">Для этого раздела нужен включённый JavaScript.</p></noscript>
  </section>

  <article class="card secret" id="out" hidden>
    <div class="bar">
      <span>Открыто · закроется через 15 минут без действий</span>
      <button id="lock" type="button">Запереть</button>
    </div>
    <div id="body"></div>
  </article>
</main>
<script>
(function () {
  var PAYLOAD = "__PAYLOAD__", ITER = __ITER__;
  var gate = document.getElementById('gate'), out = document.getElementById('out');
  var body = document.getElementById('body'), input = document.getElementById('c');
  var btn = document.getElementById('b'), err = document.getElementById('e');
  var KEY = 'semya-open', timer = null;

  function bytes(s) {
    var bin = atob(s), u = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return u;
  }

  var AAD = new TextEncoder().encode('semya');

  function decrypt(code) {
    var raw = bytes(PAYLOAD);
    var salt = raw.subarray(0, 16), iv = raw.subarray(16, 28), data = raw.subarray(28);
    var enc = new TextEncoder().encode(
      code.trim().replace(/\s+/g, ' ').toLowerCase().normalize('NFKC'));
    return crypto.subtle.importKey('raw', enc, 'PBKDF2', false, ['deriveKey'])
      .then(function (base) {
        return crypto.subtle.deriveKey(
          { name: 'PBKDF2', salt: salt, iterations: ITER, hash: 'SHA-256' },
          base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
      })
      .then(function (key) {
        return crypto.subtle.decrypt(
          { name: 'AES-GCM', iv: iv, additionalData: AAD }, key, data);
      })
      .then(function (buf) { return new TextDecoder().decode(buf); });
  }

  function lock() {
    sessionStorage.removeItem(KEY);
    body.textContent = '';
    out.hidden = true;
    gate.hidden = false;
    input.value = '';
    err.textContent = '';
    clearTimeout(timer);
  }

  function arm() {
    clearTimeout(timer);
    timer = setTimeout(lock, 15 * 60 * 1000);
  }

  function show(text) {
    body.innerHTML = text;
    gate.hidden = true;
    out.hidden = false;
    arm();
    window.scrollTo(0, 0);
  }

  document.addEventListener('touchstart', arm, { passive: true });
  document.addEventListener('keydown', arm);
  document.addEventListener('mousedown', arm);
  document.getElementById('lock').addEventListener('click', lock);

  document.getElementById('f').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var code = input.value;
    if (!code) return;
    btn.disabled = true;
    err.textContent = 'Проверяем…';
    decrypt(code).then(function (text) {
      sessionStorage.setItem(KEY, text);
      err.textContent = '';
      history.replaceState(null, '', location.pathname + location.search);
      show(text);
    }).catch(function () {
      err.textContent = 'Код не подошёл.';
      input.select();
    }).then(function () {
      setTimeout(function () { btn.disabled = false; }, 900);
    });
  });

  var cached = null;
  try { cached = sessionStorage.getItem(KEY); } catch (e) {}
  if (cached) { show(cached); return; }

  var m = /[#&]k=([^&]+)/.exec(location.hash);
  if (m) {
    decrypt(decodeURIComponent(m[1])).then(function (text) {
      sessionStorage.setItem(KEY, text);
      history.replaceState(null, '', location.pathname + location.search);
      show(text);
    }).catch(function () {
      err.textContent = 'Ссылка устарела — введите код.';
    });
  }
})();
</script>
</body>
</html>
"""


def site_css() -> str:
    """Стили берём из собранного свода — один дизайн на весь сайт."""
    index = ROOT / "docs" / "index.html"
    if not index.exists():
        raise SystemExit("нет docs/index.html — сначала запустите: python3 build_site.py")
    m = re.search(r"<style>(.*?)</style>", index.read_text(encoding="utf-8"), re.S)
    if not m:
        raise SystemExit("в docs/index.html не нашлись стили")
    return m.group(1)


def normalize(code: str) -> str:
    """Код не зависит от регистра и лишних пробелов — на телефоне так проще."""
    return " ".join(code.split()).lower()


def encrypt(text: str, code: str) -> str:
    salt = secrets.token_bytes(SALT_LEN)
    iv = secrets.token_bytes(IV_LEN)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=ITERATIONS).derive(normalize(code).encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, text.encode("utf-8"), b"semya")
    return base64.b64encode(salt + iv + ct).decode("ascii")


def build(code: str) -> Path:
    if not SOURCE.exists():
        raise SystemExit(f"нет {SOURCE.name} — положите рядом текст раздела")
    md = SOURCE.read_text(encoding="utf-8")
    inner = build_site.md_to_html(md)
    payload = encrypt(inner, code)

    page = (PAGE.replace("__CSS__", site_css())
                .replace("__GATE_CSS__", GATE_CSS)
                .replace("__ITER__", str(ITERATIONS))
                .replace("__PAYLOAD__", payload))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    return OUT


def main() -> None:
    code = os.environ.get("PARENTS_CODE", "").strip()
    if not code:
        code = getpass.getpass("Код для раздела «Родителям»: ").strip()
        if not code:
            raise SystemExit("пустой код — раздел не собран")
        again = getpass.getpass("Повторите код: ").strip()
        if not hmac.compare_digest(code, again):
            raise SystemExit("коды не совпали")
    path = build(code)
    print(f"ok: {path.relative_to(ROOT)} = {path.stat().st_size} байт")
    print(f"ссылка с кодом: {PAGE_URL}#k={quote(normalize(code))}")


if __name__ == "__main__":
    main()
