"""类型化错误体系 + 全局错误处理约定。

客户端只看到规范化的错误结构 {code, message, request_id}；
绝不返回堆栈或内部细节（专家规范）。
"""
from __future__ import annotations


class AppError(Exception):
    """所有可预期错误的基类。"""

    code: str = "internal_error"
    http_status: int = 500
    message: str = "服务内部错误"

    def __init__(self, message: str | None = None, *, detail: str | None = None):
        self.message = message or self.message
        # detail 仅供服务端日志，绝不透出客户端
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class ValidationIssue(AppError):
    code = "validation_error"
    http_status = 400
    message = "请求参数不合法"


class NotFoundError(AppError):
    code = "not_found"
    http_status = 404
    message = "资源不存在"


class ConflictError(AppError):
    code = "conflict"
    http_status = 409
    message = "资源冲突"


class ExternalServiceError(AppError):
    code = "external_service_error"
    http_status = 502
    message = "外部服务不可用"


class CollectorError(AppError):
    code = "collector_error"
    http_status = 500
    message = "采集器执行失败"


class ConfigurationError(AppError):
    code = "configuration_error"
    http_status = 500
    message = "服务配置错误"
