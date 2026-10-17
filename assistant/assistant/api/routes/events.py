"""路由层：观测事件查询。"""
from fastapi import APIRouter, Depends, Query

from assistant.api.deps import get_observation_service
from assistant.services.observation_service import ObservationService

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.get("/events")
def list_events(
    source: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO8601，只返回该时间之后的事件"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    svc: ObservationService = Depends(get_observation_service),
) -> dict:
    return {
        "items": svc.list_events(source=source, kind=kind, since=since, limit=limit, offset=offset),
        "stats": svc.event_stats(),
    }


@router.get("/events/stats")
def event_stats(svc: ObservationService = Depends(get_observation_service)) -> dict:
    return svc.event_stats()
