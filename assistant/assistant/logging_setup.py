"""结构化 JSON 日志：全链路携带 request_id，不记录密钥与隐私内容（专家规范）。"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_REDACT_KEYS = {"api_key", "apikey", "token", "secret", "password", "authorization"}


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "extra_data", None)
        if isinstance(extra, dict):
            for k, v in extra.items():
                if k.lower() in _REDACT_KEYS:
                    v = "***"
                payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **fields) -> None:
    logger.log(level, event, extra={"extra_data": fields})
