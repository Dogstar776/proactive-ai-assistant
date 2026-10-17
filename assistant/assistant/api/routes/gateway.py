"""路由层：提醒队列与门控（论文 3.5）。"""
from fastapi import APIRouter, Depends, Query

from assistant.api.deps import get_reminder_service
from assistant.gateway.reminder_service import ReminderService
from assistant.gateway.risk import RISK_DESCRIPTIONS, RISK_LEVELS

router = APIRouter(prefix="/api/v1", tags=["gateway"])


@router.post("/reminders/run")
def run_reminder_cycle(
    svc: ReminderService = Depends(get_reminder_service),
) -> dict:
    """跑一次提醒周期：目标 → 四态门控 → 触达/沉默/待确认。"""
    return {"results": svc.run_cycle()}


@router.get("/reminders")
def list_reminders(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    svc: ReminderService = Depends(get_reminder_service),
) -> dict:
    return {"items": [vars(r) for r in svc.repo.list(status=status, limit=limit)]}


@router.post("/reminders/{reminder_id}/approve")
def approve_reminder(
    reminder_id: str,
    svc: ReminderService = Depends(get_reminder_service),
) -> dict:
    r = svc.approve(reminder_id)
    return {"reminder_id": r.reminder_id, "status": r.status}


@router.post("/reminders/{reminder_id}/reject")
def reject_reminder(reminder_id: str, svc: ReminderService = Depends(get_reminder_service)) -> dict:
    r = svc.reject(reminder_id)
    return {"reminder_id": r.reminder_id, "status": r.status}


@router.post("/reminders/batch")
def batch_decide(
    reminder_ids: list[str],
    action: str = Query(description="approve / reject"),
    svc: ReminderService = Depends(get_reminder_service),
) -> dict:
    """批量审计：人类在场时一次审多件（抗授权疲劳）。"""
    return svc.batch_decide(reminder_ids, action)


@router.get("/gateway/stats")
def gateway_stats(svc: ReminderService = Depends(get_reminder_service)) -> dict:
    """决策分布 + 授权疲劳自检（论文 4.5 的工程对策）。"""
    return {
        "fatigue": svc.fatigue_stats(),
        "risk_levels": RISK_LEVELS,
        "risk_descriptions": RISK_DESCRIPTIONS,
    }
