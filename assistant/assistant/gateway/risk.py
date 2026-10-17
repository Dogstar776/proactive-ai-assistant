"""风险分级：行动的四维分类（可逆性/影响范围/资源代价/伦理敏感性）。

论文 5.1 表 2 判定"内生行为的风险分级"为 B 级——现有分类器可迁移做初筛，
但内生目标缺乏风险先验分布。本模块如实标注：规则分类器 + 显式映射表，
不声称可靠的自动分级（[B-simulated]）。

已知局限（诚实记录）：关键词扫描不理解否定语义——"不对外发送"会命中"发送"。
2026-10-17 冒烟时模板免责声明正是因此被误判 R3。对策是双重的：
① 模板措辞避开高风险词表；② 误判方向是"过度谨慎"（只读目标被升为 R3 挂起），
对一个门控系统而言是安全的失败方向——漏放行好于误放行。
"""
from __future__ import annotations

from dataclasses import dataclass

# 风险等级定义（论文 3.5 四级分类的操作化）
RISK_LEVELS = ("R0", "R1", "R2", "R3")

RISK_DESCRIPTIONS = {
    "R0": "纯内部认知操作（自省/记忆整理/目标排序）：默认放行",
    "R1": "低风险外部行为（只读型信息获取、向用户本人推送只读摘要）：自主执行并留痕",
    "R2": "低风险外部行为（草拟内容、整理建议）：生成后入待确认队列，不主动触达",
    "R3": "高风险外部行为（不可逆修改/对外通信/支付/删除）：挂起请示，超时默认不行动",
}

# 目标/行动特征 → 风险等级的关键词映射（显式、可审查；对应论文 3.5 四级维度）
_HIGH_RISK_KEYWORDS = ("支付", "发送", "删除", "转账", "提交表单", "发布", "退款", "签约")
_MEDIUM_RISK_KEYWORDS = ("草拟", "起草", "撰写", "建议")
_READONLY_KEYWORDS = ("只读", "清单", "罗列", "查看", "浏览", "摘要", "梳理", "列出")


@dataclass
class RiskAssessment:
    level: str
    reasons: list[str]


def assess_risk(*, goal_risk: str | None = None, text: str = "") -> RiskAssessment:
    """综合目标自带风险级与文本特征，给出风险初评。

    规则优先级：显式 R3/R2 声明 > 关键词 > 目标默认级 > R1。
    """
    reasons: list[str] = []
    level = "R1"

    if goal_risk:
        level = goal_risk
        reasons.append(f"目标声明风险级 {goal_risk}")

    for kw in _HIGH_RISK_KEYWORDS:
        if kw in text:
            if goal_risk != "R3":
                level = "R3"
            reasons.append(f"命中高风险词「{kw}」")
            break
    else:
        for kw in _MEDIUM_RISK_KEYWORDS:
            if kw in text and level in ("R1",):
                level = "R2"
                reasons.append(f"命中中风险词「{kw}」")
                break
        else:
            if not any(kw in text for kw in _READONLY_KEYWORDS) and not goal_risk:
                level = "R1"
                reasons.append("无显式风险声明，按只读默认 R1")

    if level not in RISK_LEVELS:
        level = "R1"
    return RiskAssessment(level=level, reasons=reasons or ["默认"])
