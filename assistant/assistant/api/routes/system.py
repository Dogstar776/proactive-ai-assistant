"""路由层：charter 读写与系统状态（P5 仪表盘支撑）。"""
from pathlib import Path

import yaml
from fastapi import APIRouter, Body, Depends

from assistant.api.deps import get_deep_cycle_service, get_settings_dep, reload_services
from assistant.config import Settings
from assistant.errors import ValidationIssue
from assistant.services.deep_cycle import DeepCycleService

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/charter")
def get_charter(svc: DeepCycleService = Depends(get_deep_cycle_service)) -> dict:
    """返回解析后的 charter 与原始 YAML 文本（编辑器用）。"""
    charter = svc.goals.charter
    try:
        raw = Path(charter.source_path).read_text(encoding="utf-8")
    except OSError:
        raw = ""
    return {
        "parsed": {
            "version": charter.version,
            "owner": charter.owner,
            "domains": [
                {"name": d.name, "weight": d.weight, "active": d.active, "notes": d.notes}
                for d in charter.domains
            ],
            "quiet_hours": charter.quiet_hours,
            "intervention_budget": charter.intervention_budget,
            "risk_policy": charter.risk_policy,
            "preferences": charter.preferences,
            "source_path": charter.source_path,
        },
        "yaml": raw,
    }


@router.post("/charter")
def save_charter(
    payload: dict = Body(..., description='{"yaml": "..."}'),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    """写入 charter（先校验再落盘），随后热重载服务。"""
    text = str(payload.get("yaml", ""))
    if not text.strip():
        raise ValidationIssue("yaml 不能为空")
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValidationIssue(f"YAML 解析失败: {e}") from e
    if not isinstance(parsed, dict) or not parsed.get("domains"):
        raise ValidationIssue("charter 至少需要一个 domain")

    from assistant.charter import Charter, Domain

    Charter(
        domains=[
            Domain(name=str(d["name"]), weight=float(d.get("weight", 0)))
            for d in parsed["domains"] if isinstance(d, dict) and d.get("name")
        ],
    )  # 仅校验形态

    # 真实偏好写 配置的 data_dir（不是相对路径——曾因相对路径在测试中写错位置，2026-10-17）
    target = Path(settings.data_dir) / "charter.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    reload_services()
    return {"status": "saved", "path": str(target)}


@router.get("/system/status")
def system_status(settings: Settings = Depends(get_settings_dep)) -> dict:
    """运行配置与预算（成本面板数据源）。"""
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "deep_cycles_per_day": settings.deep_cycles_per_day,
        "daily_token_budget": settings.daily_token_budget,
        "light_observe_interval_minutes": settings.light_observe_interval_minutes,
        "data_dir": str(settings.data_dir),
        "db_path": str(settings.db_path),
    }
