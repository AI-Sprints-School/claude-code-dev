#!/usr/bin/env python3
"""Локальный сервер веб-клиента «Кошелёк».

Делает три вещи, и все три — то же самое, что в проде делает nginx:

  1. отдаёт статику из dist/ (сборка 1.4.0) и dist/next/ (сборка 1.5.0);
  2. для маршрутов без файла отдаёт index.html своей сборки (SPA-фолбэк),
     поэтому /topup и /next/topup открываются и по прямой ссылке, и по F5;
  3. проксирует /api/* в бэкенд — запросы в DevTools остаются
     same-origin и выглядят как /api/wallet/topup, без CORS и preflight.

Пути /docs, /openapi.yaml — поверхности бэкенда, на них выдаётся
редирект.

Переменные окружения:
    WALLET_PORT       порт, по умолчанию 5173
    WALLET_BACKEND    адрес бэкенда, по умолчанию http://127.0.0.1:8000
"""
from __future__ import annotations

import os
import posixpath
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

PORT = int(os.getenv("WALLET_PORT", "5173"))
BACKEND = os.getenv("WALLET_BACKEND", "http://127.0.0.1:8000").rstrip("/")

BACKEND_PREFIXES = ("/api",)
BACKEND_REDIRECTS = ("/docs", "/openapi.yaml")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}

FORWARDED_HEADERS = ("authorization", "content-type", "accept")


def is_backend_path(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in BACKEND_PREFIXES)


def is_redirect_path(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in BACKEND_REDIRECTS)


def resolve(path: str):
    """Возвращает (корень сборки, путь внутри неё)."""
    if path == "/next" or path.startswith("/next/"):
        return DIST / "next", path[len("/next"):] or "/"
    return DIST, path


class Handler(BaseHTTPRequestHandler):
    server_version = "WalletWeb/1.0"

    # --- вспомогательное ---------------------------------------------------

    def send_payload(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None

        request = urllib.request.Request(BACKEND + self.path, data=body, method=self.command)
        for name in FORWARDED_HEADERS:
            value = self.headers.get(name)
            if value:
                request.add_header(name, value)

        try:
            with urllib.request.urlopen(request) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                self.send_payload(response.status, payload, content_type)
        except urllib.error.HTTPError as error:
            payload = error.read()
            content_type = error.headers.get("Content-Type", "application/json")
            self.send_payload(error.code, payload, content_type)
        except urllib.error.URLError as error:
            message = ('{"error": {"code": "BACKEND_UNAVAILABLE", "message": "%s"}}'
                       % str(error.reason).replace('"', "'"))
            self.send_payload(502, message.encode("utf-8"), "application/json; charset=utf-8")

    def serve_static(self) -> None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]

        if is_redirect_path(path):
            self.send_response(302)
            self.send_header("Location", BACKEND + path)
            self.end_headers()
            return

        root, relative = resolve(path)
        clean = posixpath.normpath(relative).lstrip("/")
        candidate = (root / clean).resolve() if clean else None

        if candidate is not None and root.resolve() in candidate.parents and candidate.is_file():
            body = candidate.read_bytes()
            content_type = CONTENT_TYPES.get(candidate.suffix, "application/octet-stream")
            self.send_payload(200, body, content_type)
            return

        # SPA-фолбэк: маршрут без файла отдаётся index.html своей сборки
        index = root / "index.html"
        if not index.is_file():
            self.send_payload(404, "dist/ не собран, запустите build.py".encode("utf-8"), "text/plain; charset=utf-8")
            return
        self.send_payload(200, index.read_bytes(), CONTENT_TYPES[".html"])

    # --- методы ------------------------------------------------------------

    def do_GET(self) -> None:
        if is_backend_path(self.path):
            self.proxy()
        else:
            self.serve_static()

    do_HEAD = do_GET

    def do_POST(self) -> None:
        if is_backend_path(self.path):
            self.proxy()
        else:
            self.send_payload(405, b"", "text/plain; charset=utf-8")

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def log_message(self, fmt, *args) -> None:
        print("%s %s" % (self.address_string(), fmt % args))


def main() -> None:
    if not (DIST / "index.html").is_file():
        raise SystemExit("сначала соберите клиент: python3 build.py")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("веб-клиент 1.4.0: http://localhost:%d/" % PORT)
    print("веб-клиент 1.5.0: http://localhost:%d/next/" % PORT)
    print("API проксируется в %s" % BACKEND)
    server.serve_forever()


if __name__ == "__main__":
    main()
