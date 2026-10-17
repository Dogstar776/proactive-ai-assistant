"""路由层：目标队列查询与生命周期操作。"""
from fastapi import APIRouter, Depends, Query

from assistant.api.deps import get_deep_cycle_service
from assistant.errors import ValidationIssue
from assistant.goals.repository import VALID_STATUS
from assistant.services.deep_cycle import DeepCycleService

router = APIRouter(prefix="/api/v1", tags=["goals"])


@router.get("/goals")
def list_goals(
    status: str | None = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=200),
    svc: DeepCycleService = Depends(get_deep_cycle_service),
) -> dict:
    return {"items": svc.goals.list_goals(status=status, limit=limit), "stats": svc.goals.stats()}


@router.post("/goals/{goal_id}/status")
def set_goal_status(
    goal_id: str,
    status: str = Query(description="active/suspended/done/revoked"),
    svc: DeepCycleService = Depends(get_deep_cycle_service),
) -> dict:
    if status not in VALID_STATUS:
        raise ValidationIssue(f"status 必须是 {sorted(VALID_STATUS)} 之一")
    svc.goals.set_status(goal_id, status)
    return {"goal_id": goal_id, "status": status}
