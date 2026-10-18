"""API Key 鉴权中间件（安卓 APK 远程接管入口）。

激活条件：settings.api_key 非空。此时：
- `/health` `/ready` 保持开放（供 APK 连通性测试，不泄露数据）；
- 其余路径要求 `X-API-Key` 请求头，常数时间比较防时序攻击；
- 未配置时完全跳过（本地单用户模式不变，ADR-0002）。
"""
from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

OPEN_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._key = api_key.encode()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in OPEN_PATHS or not path.startswith("/api"):
            return await call_next(request)
        provided = request.headers.get("X-API-Key", "")
        if not provided or not hmac.compare_digest(provided.encode(), self._key):
            return JSONResponse(
                status_code=401,
                content={
                    "code": "unauthorized",
                    "message": "缺少或非法的 X-API-Key",
                    "request_id": "-",
                },
            )
        return await call_next(request)


def maybe_install(app, api_key: str | None) -> None:
    """配置了 key 才挂载；本地模式零开销。"""
    if api_key:
        app.add_middleware(ApiKeyMiddleware, api_key=api_key)
