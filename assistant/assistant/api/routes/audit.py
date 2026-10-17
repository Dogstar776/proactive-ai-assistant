"""路由层：审计日志与授权账本（论文 3.5：全量决策日志支持事后审计）。"""
from fastapi import APIRouter, Depends, Query

from assistant.api.deps import get_observation_service
from assistant.errors import NotFoundError
from assistant.services.observation_service import ObservationService

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit")
def list_audit(
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    svc: ObservationService = Depends(get_observation_service),
) -> dict:
    return {"items": svc.list_audit(action=action, limit=limit)}


@router.get("/consents")
def list_consents(svc: ObservationService = Depends(get_observation_service)) -> dict:
    return {"items": svc.list_consents()}


@router.post("/consents/{consent_id}/revoke")
def revoke_consent(
    consent_id: str,
    svc: ObservationService = Depends(get_observation_service),
) -> dict:
    """撤回授权：对应连接器下一轮起跳过（论文 P5 硬约束）。"""
    try:
        svc.revoke_consent(consent_id)
    except NotFoundError:
        raise
    return {"status": "revoked", "consent_id": consent_id}
