"""路由层包。"""
from assistant.api.routes import audit, collectors, events, health, stream

__all__ = ["health", "events", "stream", "audit", "collectors"]
