"""路由层：连接器管理与手动触发一次轻观测周期。"""
from fastapi import APIRouter, Depends, Query

from assistant.api.deps import get_observation_service
from assistant.errors import NotFoundError
from assistant.services.observation_service import ObservationService

router = APIRouter(prefix="/api/v1", tags=["collectors"])


@router.get("/collectors")
def list_collectors(svc: ObservationService = Depends(get_observation_service)) -> dict:
    return {
        "items": svc.list_collectors(),
        "consents": svc.list_consents(),
        "bus": svc.bus_stats(),
    }


@router.post("/collectors/run")
def run_cycle(
    collector_id: str | None = Query(default=None, description="只跑指定连接器"),
    svc: ObservationService = Depends(get_observation_service),
) -> dict:
    """手动触发一次轻观测周期（高频层，本地规则，不调 LLM）。"""
    known = {c["collector_id"] for c in svc.list_collectors()}
    if collector_id and collector_id not in known:
        raise NotFoundError(f"连接器不存在: {collector_id}")
    return {"results": svc.run_cycle(collector_id)}
