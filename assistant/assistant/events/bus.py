"""观测事件总线：进程内发布/订阅（论文 3.1「显著变化事件队列」的工程形态）。

P2 阶段消费者是 SSE 端点；P3 起自省层订阅同一总线。
"""
from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from assistant.logging_setup import get_logger
from assistant.models import ObservedEvent

logger = get_logger("events.bus")

Subscriber = Callable[[ObservedEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: list[Subscriber] = []
        self._queues: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self, fn: Subscriber) -> None:
        with self._lock:
            self._subs.append(fn)

    def subscribe_queue(self) -> queue.Queue:
        """SSE 专用：返回一个可持续消费的队列。"""
        q: queue.Queue = queue.Queue(maxsize=1000)

        def _pump(ev: ObservedEvent) -> None:
            try:
                q.put_nowait(ev)
            except queue.Full:
                logger.warning("sse.queue.full, drop event_id=%s", ev.event_id)

        self.subscribe(_pump)
        with self._lock:
            self._queues.append(q)
        return q

    def unsubscribe_queue(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._queues:
                self._queues.remove(q)

    def publish(self, event: ObservedEvent) -> None:
        with self._lock:
            subs = list(self._subs)
        for fn in subs:
            try:
                fn(event)
            except Exception:  # 单个订阅者异常不得中断总线
                logger.exception("subscriber error for event_id=%s", event.event_id)

    def stats(self) -> dict:
        with self._lock:
            return {"subscribers": len(self._subs), "sse_queues": len(self._queues)}


_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
