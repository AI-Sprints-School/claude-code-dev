#!/usr/bin/env python3
"""Сборка веб-клиента «Кошелёк».

Никакой сборочной магии: копирование файлов и подстановка четырёх плейсхолдеров.
Открыв DevTools, студент видит ровно те же файлы, что лежат в src/.

Собираются две сборки:

    dist/          основная,        1.4.0 (140), маршруты /login, /topup, …
    dist/next/     регрессионная,   1.5.0 (150), маршруты /next/login, …

Отличие ровно одно: файл js/amount.js берётся из src/variants/. Обе сборки
ходят в один бэкенд.

Переменные окружения:
    WALLET_API_BASE   базовый адрес API, по умолчанию /api
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

TEXT_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".txt"}

BUILDS = [
    {"version": "1.4.0", "build": "140", "route_base": "", "out": DIST},
    {"version": "1.5.0", "build": "150", "route_base": "/next", "out": DIST / "next"},
]


def api_base() -> str:
    return os.getenv("WALLET_API_BASE", "/api")


def substitute(text: str, spec: dict) -> str:
    return (
        text.replace("{{ROUTE_BASE}}", spec["route_base"])
        .replace("{{APP_VERSION}}", spec["version"])
        .replace("{{APP_BUILD}}", spec["build"])
        .replace("{{API_BASE}}", api_base())
    )


def copy_tree(spec: dict) -> int:
    out = spec["out"]
    copied = 0
    for source in sorted(SRC.rglob("*")):
        if source.is_dir():
            continue
        relative = source.relative_to(SRC)
        # variants/ в сборку не попадает: нужный вариант кладётся как js/amount.js
        if relative.parts[0] == "variants":
            continue
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix in TEXT_SUFFIXES:
            content = substitute(source.read_text(encoding="utf-8"), spec)
            target.write_text(content, encoding="utf-8")
        else:
            shutil.copy2(source, target)
        copied += 1
    return copied


def copy_variant(spec: dict) -> None:
    variant = SRC / "variants" / ("amount-%s.js" % spec["version"])
    if not variant.exists():
        raise SystemExit("нет варианта валидации: %s" % variant)
    target = spec["out"] / "js" / "amount.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    content = substitute(variant.read_text(encoding="utf-8"), spec)
    target.write_text(content, encoding="utf-8")


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    for spec in BUILDS:
        count = copy_tree(spec)
        copy_variant(spec)
        print(
            "собрано %s (сборка %s): %s файлов -> %s"
            % (spec["version"], spec["build"], count + 1, spec["out"].relative_to(ROOT))
        )
    print("API: %s" % api_base())


if __name__ == "__main__":
    main()
