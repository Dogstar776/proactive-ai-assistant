"""FastAPI 应用工厂：中间件顺序、CORS 显式来源、全局错误处理、健康检查。

中间件顺序（专家规范）：request_id → 访问日志(JSON) → 错误处理。
单用户本地部署，绑定 127.0.0.1，v0 无鉴权（ADR-0002）。
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from assistant.api.routes import audit, collectors, events, health, stream
from assistant.config import Settings, get_settings
from assistant.errors import AppError
from assistant.logging_setup import (
    get_logger,
    log_event,
    new_request_id,
    request_id_var,
    setup_logging,
)

logger = get_logger("api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动：集中校验（快速失败）+ 迁移
        settings.validate_for_startup()
        from assistant.db import migrate

        applied = migrate(settings.db_path)
        log_event(logger, 20, "app.start", db=str(settings.db_path),
                  provider=settings.llm_provider, migrations=applied)
        yield
        # 停机：优雅关闭（SSE 队列由端点自行清理）
        from assistant.api.deps import shutdown_services

        shutdown_services()
        log_event(logger, 20, "app.stop")

    app = FastAPI(title="proactive-ai-assistant", version="0.2.0", lifespan=lifespan)

    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # 显式来源，禁通配符
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = new_request_id()
        token = request_id_var.set(rid)
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            log_event(logger, 40, "http.unhandled", path=request.url.path,
                      method=request.method, exc_info=True)
            raise
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-Id"] = rid
        log_event(logger, 20, "http.access", path=request.url.path, method=request.method,
                  status=response.status_code, request_id=rid,
                  duration_ms=int((time.monotonic() - started) * 1000))
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        log_event(logger, 30, "app.error", code=exc.code, detail=exc.detail)
        return JSONResponse(
            status_code=exc.http_status,
            content={**exc.to_dict(), "request_id": request_id_var.get()},
        )

    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(stream.router)
    app.include_router(audit.router)
    app.include_router(collectors.router)
    return app
