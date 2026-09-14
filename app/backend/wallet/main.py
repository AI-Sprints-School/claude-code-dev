"""Точка входа бэкенда «Кошелька».

Автогенерация OpenAPI выключена на уровне фреймворка — это процессное
решение, а не стилистика: ``openapi_url=None`` и ``docs_url=None`` делают
технически невозможным получить документацию из кода. Публикуется
рукописный ``spec/openapi.yaml``, который писался до первой строки
обработчика и служит приёмочным контрактом сборки.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from wallet import APP_BUILD, APP_VERSION
from wallet.config import settings
from wallet.errors import ApiError, error_response
from wallet.json_response import JsonResponse
from wallet.projection import OperationViewStore
from wallet.routers import assistant, auth, sql_console, wallet as wallet_router, wallets

BASE_DIR = Path(__file__).resolve().parent.parent
SPEC_FILE = BASE_DIR / "spec" / "openapi.yaml"
STATIC_DIR = BASE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Кошелёк API",
        version=APP_VERSION,
        openapi_url=None,   # схема из кода не генерируется (3.1)
        docs_url=None,      # /docs отдаёт статичный Swagger UI, см. ниже
        redoc_url=None,
    )

    app.state.operation_view = OperationViewStore(settings.operation_view_path)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    app.include_router(auth.router)
    app.include_router(wallet_router.router)
    app.include_router(wallets.router)
    app.include_router(sql_console.router)
    app.include_router(assistant.router)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JsonResponse:
        return error.to_response()

    @app.exception_handler(404)
    async def handle_not_found(request: Request, exc) -> JsonResponse:
        return error_response(404, "NOT_FOUND", "Ресурс не найден")

    @app.get("/openapi.yaml", include_in_schema=False)
    def openapi_yaml() -> FileResponse:
        """Рукописная спецификация. Единственный источник задуманного поведения."""
        return FileResponse(SPEC_FILE, media_type="application/yaml")

    @app.get("/docs", include_in_schema=False)
    def docs() -> FileResponse:
        return FileResponse(STATIC_DIR / "docs" / "index.html")

    @app.get("/api/docs", include_in_schema=False)
    def api_docs() -> RedirectResponse:
        return RedirectResponse("/docs")

    @app.get("/api/health", include_in_schema=False)
    def health() -> JsonResponse:
        return JsonResponse(
            {"status": "ok", "version": APP_VERSION, "build": APP_BUILD}
        )

    return app


app = create_app()
