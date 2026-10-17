"""路由层：SSE 事件流（论文 3.1 显著变化事件队列 → 仪表盘实时推送）。"""
import asyncio
import json
import queue as _queue

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from assistant.api.deps import get_observation_service
from assistant.events.bus import get_bus
from assistant.services.observation_service import ObservationService

router = APIRouter(prefix="/api/v1", tags=["stream"])


@router.get("/stream")
async def stream_events(svc: ObservationService = Depends(get_observation_service)):
    """观测事件 SSE 流。客户端断线由 EventSource 自动重连。"""
    bus = get_bus()
    q = bus.subscribe_queue()

    async def gen():
        try:
            # 首帧：当前统计，供前端立即渲染
            yield f"event: stats\ndata: {json.dumps(svc.event_stats(), ensure_ascii=False)}\n\n"
            while True:
                try:
                    ev = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: q.get(timeout=15.0)
                    )
                except _queue.Empty:
                    yield ": keep-alive\n\n"  # 心跳，防代理断连
                    continue
                payload = ObservationService._serialize(ev)
                yield f"event: observed\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe_queue(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
