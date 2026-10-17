# 开发日志 · 2026-10-17 · P4 对齐层 + 提醒引擎

## 今日完成（P4：论文 3.5 人机可控安全对齐层的工程实现）

### 交付物

- `gateway/risk.py`：四维风险关键词分类器（R0–R3），[B-simulated] 标注 + 已知局限记录
- `gateway/gate.py`：Gateway 四态判决（沉默条件优先：免打扰 → 冷却 → 每日预算 → 风险分级），每次判决写审计日志（含沉默）
- `gateway/reminder_service.py`：提醒引擎（目标 → 干预 → 门控 → 触达/沉默/待确认）+ 超时清扫（timeout_default: deny）+ 批量审计 + 授权疲劳自检
- 迁移 003（reminders 台账）；API：`/api/v1/reminders`（run/list/approve/reject/batch）、`/api/v1/gateway/stats`
- `scripts/run_reminder_cycle.py` CLI；测试扩到 47 个

### 验证结果（全部实测通过）

| 验证项 | 结果 |
|---|---|
| ruff / pytest | 全绿 / 47 passed |
| 四态门控单测 | quiet_hours/cooldown/daily_budget 三种沉默 + R3 ask + R2 assist + R1 act |
| 端到端（真实服务） | 5 目标 → act 3 / silence 2（daily_budget 3/3），判决全部留痕 |
| 二轮周期 | 5/5 沉默（冷却+预算）——系统该闭嘴时闭嘴 |
| 生命周期 | approve → delivered；reject；超时 24h → expired（默认拒绝） |
| 疲劳自检 | ask_total / approval_rate 输出，随周期累积 |

### 当日修复（值得记录的一个真 bug）

**模板免责声明触发自己的高风险词**："不对外**发送**"命中"发送"、"不自动**删除**任何原始记录"命中"删除" → 两个只读目标被误判 R3 挂起请示。修复：① 三个模板措辞避开词表；② 新增回归测试 `test_readonly_template_drafts_stay_r1`；③ risk.py 文档记录该局限与"失败方向安全"的论证（漏放行好于误放行，与论文 5.1 B 级判定一致）。

### 设计亮点（写给未来的自己）

**"可审计的沉默"**：系统选择不打扰时，reminders 表里留下 `status=suppressed + decision_reason=daily_budget(3/3)`——人类因此能区分"系统认为不该说"与"系统没说话"。这是论文 4.5 监督注意力稀释问题的工程对策，也是 P6 授权疲劳实验的核心测量对象。

### 已知局限

- 风险分类是关键词初筛（B 级），不理解否定语义；模板措辞已规避，但用户自建 charter/目标仍可能误触——误判方向安全（过度谨慎）；
- 触达渠道只有 SSE；本地系统通知未做（不谎称）；
- 免打扰判定用 UTC 时间与 charter 的本地时间字面量比较，未做时区转换——charter 由单人本地使用，可接受，P6 若多设备再处理。

### 下一步

P5 仪表盘：认知环可视化、charter 编辑器、提醒队列（含 suppressed 可见）、成本面板。
