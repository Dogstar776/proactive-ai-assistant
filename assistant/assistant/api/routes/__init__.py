"""路由层包。"""
from assistant.api.routes import (
    audit,
    collectors,
    events,
    goals,
    health,
    introspection,
    stream,
)

__all__ = ["health", "events", "stream", "audit", "collectors", "introspection", "goals"]
