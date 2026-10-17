"""路由层包。"""
from assistant.api.routes import (
    audit,
    collectors,
    events,
    gateway,
    goals,
    health,
    introspection,
    stream,
)

__all__ = [
    "health", "events", "stream", "audit", "collectors", "introspection", "goals", "gateway",
]
