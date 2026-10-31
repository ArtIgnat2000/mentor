"""Семейный справочник: два раздельных контура.

Запуск:
    python -m family.server --family-port 8000 --parents-port 8001

Семейный контур публичный и не содержит родительских методик.
Родительский контур требует серверного входа и не кэширует закрытые страницы.
"""
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .auth import ParentStore, make_session, read_session, session_secret, verify_password
from .content import find_page, load_contour

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"


def _headers(extra=None):
    h = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'self'; form-action 'self'",
    }
    if extra:
        h.update(extra)
    return h


def _shell(title: str, body: str, contour: str, user=None, noindex=False):
    nav = '<a href="/">Главная</a>'
    if contour == "parents":
        if user:
            nav += f' <span class="who">{html.escape(user.get("name", ""))}</span> <a href="/account">Аккаунт</a> <form method="post" action="/logout" class="inline"><button type="submit">Выйти</button></form>'
        else:
            nav += ' <a href="/login">Войти</a>'
    robots = '<meta name="robots" content="noindex,nofollow">' if noindex else ""
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="{'#7a2e2e' if contour == 'parents' else '#16302b'}">
{robots}
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="/static/app.css">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/static/icons/icon-180.png">
</head>
<body class="{contour}">
<header class="top"><div class="brand">{'Родителям' if contour == 'parents' else 'Семья'}</div><nav>{nav}</nav></header>
<main class="wrap">
{body}
</main>
<script src="/static/app.js" defer></script>
</body>
</html>"""


def _card_list(data, contour):
    cards = []
    for p in data["pages"]:
        tag = f'<span class="tag">{html.escape(p["tag"])}</span>' if p.get("tag") else ""
        cards.append(f'<a class="card" href="/p/{html.escape(p["slug"])}">{tag}<h2>{html.escape(p["title"])}</h2><p>{html.escape(p["summary"])}</p></a>')
    intro = ("<p class='lead'>Закрытый родительский справочник. Материалы не попадают в детский контур и не кэшируются офлайн.</p>"
             if contour == "parents" else
             "<p class='lead'>Общие семейные правила и материалы, которые можно показывать детям.</p>")
    return f"<h1>{html.escape(data['title'])}</h1>{intro}<div class='cards'>{''.join(cards)}</div>"


def _page_html(page, contour):
    back = '<p><a href="/">← К списку</a></p>'
    private = '<p class="private">Закрытый материал · только для родителей</p>' if contour == "parents" else ""
    print_link = f'<p><a class="btn" href="/print/{html.escape(page["slug"])}">Версия для печати</a></p>'
    return f"{back}{private}<article class='content'>{page['html']}</article>{print_link}"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "FamilyReference/1.0"

    @property
    def contour(self):
        return self.server.contour

    def log_message(self, fmt, *args):
        print(f"[{self.contour}] {self.address_string()} {fmt % args}")

    def _send(self, code, body=b"", content_type="text/html; charset=utf-8", extra=None, cache=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        headers = _headers(extra)
        headers["Content-Type"] = content_type
        if cache:
            headers["Cache-Control"] = cache
        elif self.contour == "parents":
            headers["Cache-Control"] = "no-store"
        self.send_response(code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _redirect(self, location, cookie=None):
        extra = {"Location": location}
        if cookie:
            extra["Set-Cookie"] = cookie
        self._send(303, b"", extra=extra, cache="no-store")

    def _session(self):
        cookie = SimpleCookie()
        raw = self.headers.get("Cookie", "")
        try:
            cookie.load(raw)
        except Exception:
            return None
        morsel = cookie.get("parents_session")
        return read_session(self.server.secret, morsel.value if morsel else None)

    def _require_parent(self):
        session = self._session()
        if not session:
            self._redirect("/login")
            return None
        return session

    def _form(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(min(length, 64 * 1024)).decode("utf-8", "replace")
        return {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}

    def _csrf_ok(self, form, session=None):
        origin = self.headers.get("Origin")
        referer = self.headers.get("Referer")
        host = self.headers.get("Host", "")
        source = origin or referer
        if source:
            parsed = urlparse(source)
            if parsed.netloc != host:
                return False
        token = form.get("csrf", "")
        if session:
            return secrets.compare_digest(token, session.get("csrf", ""))
        expected = self.server.login_csrf.get(self.client_address[0])
        return bool(expected and secrets.compare_digest(token, expected))

    def _login_csrf(self):
        token = secrets.token_urlsafe(24)
        self.server.login_csrf[self.client_address[0]] = token
        return token

    def _cookie(self, value, max_age):
        secure = self.server.production or self.headers.get("X-Forwarded-Proto") == "https"
        parts = [f"parents_session={value}", "Path=/", "HttpOnly", "SameSite=Lax", f"Max-Age={max_age}"]
        if secure:
            parts.append("Secure")
        return "; ".join(parts)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/static/"):
            return self._static(path)
        if path == "/manifest.webmanifest":
            return self._manifest()
        if path == "/sw.js":
            return self._sw()
        if path == "/offline":
            return self._send(200, _shell("Офлайн", "<h1>Нет сети</h1><p>Закрытые родительские материалы доступны только онлайн.</p>", self.contour), cache="no-store")
        if path == "/healthz":
            return self._send(200, json.dumps({"ok": True, "contour": self.contour}), "application/json", cache="no-store")

        if self.contour == "family":
            return self._family_get(path)
        return self._parents_get(path)

    def _family_get(self, path):
        if path == "/":
            data = load_contour("family")
            return self._send(200, _shell("Семья", _card_list(data, "family"), "family"))
        if path.startswith("/p/"):
            page = find_page("family", path[3:])
            if not page:
                return self._send(404, _shell("Не найдено", "<h1>Страница не найдена</h1>", "family"))
            return self._send(200, _shell(page["title"], _page_html(page, "family"), "family"))
        if path.startswith("/print/"):
            page = find_page("family", path[7:])
            if not page:
                return self._send(404, "Not found", "text/plain")
            return self._send(200, _shell(page["title"], f"<article class='content print'>{page['html']}</article>", "family"))
        return self._send(404, _shell("Не найдено", "<h1>Страница не найдена</h1>", "family"))

    def _parents_get(self, path):
        store = self.server.store
        if path == "/setup":
            token = store.bootstrap_token(create=True)
            if not token:
                return self._redirect("/login")
            csrf = self._login_csrf()
            body = f"""
<h1>Первичная настройка</h1>
<p>Создайте первого родителя. После создания вход будет только по паролю.</p>
<form method="post" action="/setup" class="auth">
<input type="hidden" name="csrf" value="{csrf}">
<label>Токен настройки<input name="token" required autocomplete="off"></label>
<label>Имя<input name="name" required autocomplete="name"></label>
<label>Логин<input name="username" required autocomplete="username"></label>
<label>Пароль<input name="password" type="password" required minlength="12" autocomplete="new-password"></label>
<button type="submit">Создать родителя</button>
</form>"""
            return self._send(200, _shell("Настройка", body, "parents", noindex=True), cache="no-store")
        if path == "/login":
            if not store.has_users():
                return self._redirect("/setup")
            csrf = self._login_csrf()
            body = f"""
<h1>Вход для родителей</h1>
<form method="post" action="/login" class="auth">
<input type="hidden" name="csrf" value="{csrf}">
<label>Логин<input name="username" required autocomplete="username"></label>
<label>Пароль<input name="password" type="password" required autocomplete="current-password"></label>
<button type="submit">Войти</button>
</form>"""
            return self._send(200, _shell("Вход", body, "parents", noindex=True), cache="no-store")
        session = self._require_parent()
        if not session:
            return
        if path == "/":
            data = load_contour("parents")
            return self._send(200, _shell("Родителям", _card_list(data, "parents"), "parents", session), cache="no-store")
        if path.startswith("/p/"):
            page = find_page("parents", path[3:])
            if not page:
                return self._send(404, _shell("Не найдено", "<h1>Страница не найдена</h1>", "parents", session), cache="no-store")
            return self._send(200, _shell(page["title"], _page_html(page, "parents"), "parents", session), cache="no-store")
        if path.startswith("/print/"):
            page = find_page("parents", path[7:])
            if not page:
                return self._send(404, "Not found", "text/plain", cache="no-store")
            return self._send(200, _shell(page["title"], f"<article class='content print'>{page['html']}</article>", "parents", session), cache="no-store")
        if path == "/account":
            csrf = session.get("csrf", "")
            body = f"""
<h1>Аккаунт</h1>
<p>Вы вошли как {html.escape(session.get('name', ''))}.</p>
<h2>Добавить родителя</h2>
<form method="post" action="/account/add" class="auth">
<input type="hidden" name="csrf" value="{csrf}">
<label>Имя<input name="name" required></label>
<label>Логин<input name="username" required></label>
<label>Пароль<input name="password" type="password" required minlength="12"></label>
<button type="submit">Добавить</button>
</form>"""
            return self._send(200, _shell("Аккаунт", body, "parents", session), cache="no-store")
        return self._send(404, _shell("Не найдено", "<h1>Страница не найдена</h1>", "parents", session), cache="no-store")

    def do_POST(self):
        path = urlparse(self.path).path
        if self.contour != "parents":
            return self._send(405, "Method not allowed", "text/plain")
        form = self._form()
        store = self.server.store
        if path == "/setup":
            token = store.bootstrap_token(create=False)
            if not token or not secrets.compare_digest(form.get("token", ""), token):
                return self._send(403, _shell("Ошибка", "<h1>Неверный токен настройки</h1>", "parents"), cache="no-store")
            if not self._csrf_ok(form):
                return self._send(403, "CSRF", "text/plain", cache="no-store")
            try:
                user = store.create_user(form.get("username", ""), form.get("name", ""), form.get("password", ""))
            except ValueError as e:
                return self._send(400, _shell("Ошибка", f"<h1>{html.escape(str(e))}</h1><p><a href='/setup'>Назад</a></p>", "parents"), cache="no-store")
            cookie, _ = make_session(self.server.secret, user)
            return self._redirect("/", self._cookie(cookie, 8 * 3600))
        if path == "/login":
            if not self._csrf_ok(form):
                return self._send(403, "CSRF", "text/plain", cache="no-store")
            username = form.get("username", "").strip().lower()
            key = (self.client_address[0], username)
            now = time.time()
            with self.server.rate_lock:
                count, reset = self.server.rate.get(key, (0, now + 300))
                if now > reset:
                    count, reset = 0, now + 300
                if count >= 8:
                    return self._send(429, _shell("Слишком много попыток", "<h1>Подождите несколько минут</h1>", "parents"), cache="no-store")
                self.server.rate[key] = (count + 1, reset)
            user = store.find(username)
            if not user or not verify_password(form.get("password", ""), user["password"]):
                return self._send(401, _shell("Вход", "<h1>Неверный логин или пароль</h1><p><a href='/login'>Попробовать снова</a></p>", "parents"), cache="no-store")
            with self.server.rate_lock:
                self.server.rate.pop(key, None)
            cookie, _ = make_session(self.server.secret, user)
            return self._redirect("/", self._cookie(cookie, 8 * 3600))
        session = self._require_parent()
        if not session:
            return
        if not self._csrf_ok(form, session):
            return self._send(403, "CSRF", "text/plain", cache="no-store")
        if path == "/logout":
            return self._redirect("/login", self._cookie("", 0))
        if path == "/account/add":
            try:
                store.create_user(form.get("username", ""), form.get("name", ""), form.get("password", ""))
            except ValueError as e:
                return self._send(400, _shell("Ошибка", f"<h1>{html.escape(str(e))}</h1><p><a href='/account'>Назад</a></p>", "parents", session), cache="no-store")
            return self._redirect("/account")
        return self._send(404, "Not found", "text/plain", cache="no-store")

    def _static(self, path):
        rel = path[len("/static/"):]
        file = (STATIC / rel).resolve()
        if not str(file).startswith(str(STATIC.resolve())) or not file.is_file():
            return self._send(404, "Not found", "text/plain")
        ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        self._send(200, file.read_bytes(), ctype, cache="public, max-age=3600")

    def _manifest(self):
        parents = self.contour == "parents"
        data = {
            "name": "Родителям — закрытый справочник" if parents else "Семья — правила",
            "short_name": "Родителям" if parents else "Семья",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f4f1ea",
            "theme_color": "#7a2e2e" if parents else "#16302b",
            "lang": "ru",
            "icons": [
                {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
        self._send(200, json.dumps(data, ensure_ascii=False), "application/manifest+json", cache="no-store" if parents else "public, max-age=3600")

    def _sw(self):
        if self.contour == "parents":
            js = """
const CACHE = 'parents-shell-v1';
const SHELL = ['/offline', '/static/app.css', '/static/app.js', '/manifest.webmanifest', '/static/icons/icon-192.png', '/static/icons/icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/static/') || SHELL.includes(url.pathname)) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
    return;
  }
  e.respondWith(fetch(e.request).catch(() => caches.match('/offline')));
});
"""
        else:
            js = """
const CACHE = 'family-v1';
const SHELL = ['/', '/static/app.css', '/static/app.js', '/manifest.webmanifest', '/static/icons/icon-192.png', '/static/icons/icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return res; }).catch(() => caches.match('/'))));
});
"""
        self._send(200, js, "application/javascript", cache="no-store")


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, contour, instance_dir, production=False):
        self.contour = contour
        self.production = production
        self.store = ParentStore(instance_dir) if contour == "parents" else None
        self.secret = session_secret(instance_dir, production) if contour == "parents" else ""
        self.login_csrf = {}
        self.rate = {}
        self.rate_lock = threading.Lock()
        super().__init__(addr, AppHandler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family-port", type=int, default=8000)
    parser.add_argument("--parents-port", type=int, default=8001)
    parser.add_argument("--instance", default=str(Path(__file__).resolve().parent.parent / "instance"))
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()

    family = AppServer(("0.0.0.0", args.family_port), "family", args.instance, args.production)
    parents = AppServer(("0.0.0.0", args.parents_port), "parents", args.instance, args.production)
    token = parents.store.bootstrap_token(create=True) if not args.production else parents.store.bootstrap_token(create=False)
    print(f"Семейный контур: http://0.0.0.0:{args.family_port}")
    print(f"Родительский контур: http://0.0.0.0:{args.parents_port}")
    if token and not parents.store.has_users():
        print(f"Первичная настройка родителя: /setup?token={token}")
    print("Закрытые родительские страницы не кэшируются. Для production нужен HTTPS и FAMILY_SESSION_SECRET.")
    threads = [threading.Thread(target=family.serve_forever, daemon=True), threading.Thread(target=parents.serve_forever, daemon=True)]
    for t in threads:
        t.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        family.shutdown()
        parents.shutdown()


if __name__ == "__main__":
    main()
