"""路由层：自省报告与深周期触发。"""
from fastapi import APIRouter, Depends

from assistant.api.deps import get_deep_cycle_service
from assistant.services.deep_cycle import DeepCycleService

router = APIRouter(prefix="/api/v1", tags=["introspection"])


@router.post("/introspection/run")
def run_deep_cycle(
    trigger: str = "api",
    svc: DeepCycleService = Depends(get_deep_cycle_service),
) -> dict:
    """手动触发一次深周期：自省 → 目标合成（论文 3.2→3.3）。

    对应 ADR-0005 的低频深周期；输出携带 [B-simulated] 语义。
    """
    return svc.run(trigger=trigger)


@router.get("/introspection/reports")
def list_reports(
    limit: int = 20,
    svc: DeepCycleService = Depends(get_deep_cycle_service),
) -> dict:
    return {"items": svc.introspection.list_reports(limit=limit)}
