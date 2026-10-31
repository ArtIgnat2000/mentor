"""Серверная аутентификация родительского контура.

Пароли хранятся только как PBKDF2-хеши. Сессии подписываются HMAC.
Никаких паролей и токенов в репозитории: состояние лежит в instance/.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path

ITERATIONS = 600_000
SESSION_TTL = 8 * 60 * 60
PASSWORD_MIN = 12


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def hash_password(password: str) -> dict:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return {"salt": _b64e(salt), "hash": _b64e(dk), "iterations": ITERATIONS}


def verify_password(password: str, record: dict) -> bool:
    try:
        salt = _b64d(record["salt"])
        expected = _b64d(record["hash"])
        iterations = int(record.get("iterations", ITERATIONS))
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


class ParentStore:
    def __init__(self, instance_dir: Path):
        self.dir = Path(instance_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "parents.json"
        self.token_path = self.dir / "bootstrap_token"
        self.lock = threading.Lock()

    def users(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8")).get("users", [])
        except Exception:
            return []

    def has_users(self) -> bool:
        return bool(self.users())

    def find(self, username: str) -> dict | None:
        username = username.strip().lower()
        for user in self.users():
            if user.get("username", "").lower() == username:
                return user
        return None

    def bootstrap_token(self, create: bool = False) -> str | None:
        if self.has_users():
            if self.token_path.exists():
                self.token_path.unlink(missing_ok=True)
            return None
        if self.token_path.exists():
            return self.token_path.read_text(encoding="utf-8").strip()
        if create:
            token = secrets.token_urlsafe(32)
            self.token_path.write_text(token, encoding="utf-8")
            try:
                self.token_path.chmod(0o600)
            except OSError:
                pass
            return token
        return None

    def create_user(self, username: str, name: str, password: str) -> dict:
        username = username.strip().lower()
        if not username or not password:
            raise ValueError("Пустое имя или пароль")
        if len(password) < PASSWORD_MIN:
            raise ValueError(f"Пароль должен быть не короче {PASSWORD_MIN} символов")
        with self.lock:
            users = self.users()
            if any(u.get("username", "").lower() == username for u in users):
                raise ValueError("Такой родитель уже есть")
            user = {
                "id": secrets.token_hex(8),
                "username": username,
                "name": name.strip() or username,
                "password": hash_password(password),
                "created": int(time.time()),
            }
            users.append(user)
            self._save(users)
            if self.token_path.exists():
                self.token_path.unlink(missing_ok=True)
            return user

    def _save(self, users: list[dict]):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"users": users}, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
        tmp.replace(self.path)


def session_secret(instance_dir: Path, production: bool = False) -> str:
    env = __import__("os").environ.get("FAMILY_SESSION_SECRET")
    if env:
        if len(env) < 32:
            raise SystemExit("FAMILY_SESSION_SECRET должен быть не короче 32 символов")
        return env
    if production:
        raise SystemExit("В production задайте FAMILY_SESSION_SECRET")
    path = Path(instance_dir) / "session_secret"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    path.write_text(secret, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return secret


def make_session(secret: str, user: dict, ttl: int = SESSION_TTL) -> tuple[str, str]:
    payload = {
        "sub": user["id"],
        "name": user.get("name", user["username"]),
        "exp": int(time.time()) + ttl,
        "csrf": secrets.token_urlsafe(24),
    }
    body = _b64e(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    sig = _b64e(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}", payload["csrf"]


def read_session(secret: str, cookie: str | None) -> dict | None:
    if not cookie or "." not in cookie:
        return None
    body, sig = cookie.rsplit(".", 1)
    expected = _b64e(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64d(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
