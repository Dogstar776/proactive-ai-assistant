# 路线图 P0–P7

> 执行规则：每阶段开工前与维护者确认方向；每阶段固定收尾 = 验证清单 + 一篇 ADR（如产生新决策）+ devlog 记录。不一步到位，不返工。

## P0 定位冻结 ✅

- 确认技术栈：FastAPI + SQLite/ChromaDB + React/TS + SSE（ADR-0002）
- 确认数据边界：本地三类信息源起步——日程待办、笔记文件夹、信息流（ADR-0004）
- 确认对外表述：诚实定位"受限常驻实例 + 实证仪器"（ADR-0003）
- 确认常驻成本策略：低频深周期 + 高频轻观测 + MockLLM（ADR-0005）
- 产出：`docs/charter.example.yaml`（项目自身宪章，C_human 概念的工程预演）

## P1 工程骨架 + 论文资产化 ✅（2026-10-17 完成）

- 仓库结构、README（含"这是什么/不是什么"诚实边界表）、LICENSE（代码 MIT / 论文 CC BY 4.0）
- 论文资产化：Markdown 权威源 + `md2tex.py` 生成的投稿级 LaTeX
- 文档体系：`docs/ARCHITECTURE.md`（FL-PCL→工程映射）、本路线图、ADR-0001~0005、devlog
- **市面调研**：`docs/RESEARCH-2026-landscape.md`——2026 主动式 AI 助理全景（STEPX Neo、豆包手机、小艺/Bixby/小布Next/Siri AI、ChatGPT Dreaming V3、第三方记忆层），按论文 P1–P5 判据体检，确认生态位与差异化
- 验证清单：tex 环境配对平衡、bibitem 15 条、README 链接可达、目录结构完整

## P2 观测层 ✅（2026-10-17 完成）

- `collectors/`：ICS 日历/待办连接器、Markdown 笔记文件夹连接器、RSS 连接器；统一 Collector 接口 + ConsentSpec 授权声明
- 事件化抽取管道：本地规则模式（默认，不调 LLM）+ MockLLM 模式（显式可选，输出带 mock 标记）
- `memory/`：SQLite 事件库（provenance + chain_depth + 确定性 event_id 幂等）、审计日志表、consent ledger；ChromaDB 可选（缺失自动降级）
- 基础设施：集中配置（env 校验、快速失败）、类型化错误 + 全局中间件、结构化 JSON 日志 + 请求 ID、`/health` `/ready`、优雅停机、CORS 显式来源
- REST + SSE：`/api/v1/events`、`/api/v1/stream`（实时推送）、`/api/v1/audit`、`/api/v1/consents`（可撤回）、`/api/v1/collectors/run`（手动触发轻周期）
- 种子数据 fixtures + 20 个测试 + GitHub Actions CI（ruff + pytest）
- 验证清单（全部实测通过）：ruff 全绿；20/20 测试；种子回放幂等（第二次 inserted 全 0）；SSE 端到端实时推送 16 帧；ICS 时间解包；重要度规则（7 天内 +0.4）；授权撤回后连接器跳过；错误结构规范化
- 详见 `docs/devlog/2026-10-17-p2-observation-layer.md` 与 `docs/adr/0006-p2-observation-decisions.md`

## P3 自省层 + 目标层 ✅（2026-10-17 完成）

- `introspection/`：三个缺口检测器（deadline-prep / theme-cluster / contradiction-scan）+ 一致性审计（OQ4 近似指标：自生内容占比/重复率/过期项/链深）+ 自省报告（`[B-simulated]` 标注）
- `goals/`：三个目标合成模板（全部 R1 只读型，`template-based` 显式标注）+ 目标队列（确定性 ID 幂等 + ON CONFLICT 刷新）+ 启发式 Ĝ 近似排序（0.6·info_gain + 0.4·practical_value，权重显式常量）
- `charter.py`：C_human 工程化（data/charter.yaml → docs/charter.example.yaml 回退），域权重匹配
- `services/deep_cycle.py` + `scripts/run_deep_cycle.py`：深周期编排与 CLI（ADR-0005 低频深周期，P6 起接入定时）
- API：`/api/v1/introspection/run|reports`、`/api/v1/goals`、`/api/v1/goals/{id}/status`
- 验证清单（全部实测通过）：ruff 全绿；30/30 测试；深周期端到端 16 事件→6 缺口→6 目标；第二轮 new_goals=0（幂等）；队列按优先级降序；charter 锚定生效（面试文本匹配 career 域拉高优先级）；suspend 后移出 active；非法 status 400
- 详见 `docs/devlog/2026-10-17-p3-introspection-goals.md` 与 `docs/adr/0007-p3-introspection-goals-decisions.md`

## P4 对齐层 + 提醒引擎 ✅（2026-10-17 完成）

- `gateway/`：R0–R3 风险分级（关键词初筛，[B-simulated]）+ Gateway 四态判决（沉默条件优先：免打扰 → 冷却 → 每日预算 → 风险分级）+ 提醒引擎（目标→干预→触达/沉默/待确认）+ 超时清扫（默认拒绝）+ 批量审计 + 授权疲劳自检
- **可审计的沉默**：每次 silence 判决写入 reminders 台账与审计日志（status=suppressed + reason），人类可区分"系统认为不该说"与"系统没说话"——论文 4.5 监督稀释问题的工程对策
- API：`/api/v1/reminders`（run/list/approve/reject/batch）、`/api/v1/gateway/stats`；CLI `scripts/run_reminder_cycle.py`
- 验证清单（全部实测通过）：ruff 全绿；47/47 测试；三种沉默路径单测；端到端 5 目标 → act 3 / silence 2（daily_budget 3/3 全部留痕）；二轮 5/5 沉默；approve→delivered、reject、超时 expired；疲劳指标输出
- 当日修复：模板免责声明触发高风险词导致只读目标误判 R3（措辞规避 + 回归测试 + 局限记录，见 ADR-0008）
- 详见 `docs/devlog/2026-10-17-p4-alignment-reminders.md` 与 `docs/adr/0008-p4-alignment-decisions.md`

## P5 仪表盘 ✅（2026-10-17 完成）

- `dashboard/`：Vite + React + TS，7 视图（认知环/事件流/自省/目标/提醒门控/Charter/成本），与 API 1:1 不阉割
- Liquid Glass 设计系统：浅色 mesh 背景、层叠半透明白玻璃卡、顶部高光带、同心圆角、悬浮胶囊导航、Space Grotesk 数字、Apple 弹簧动效
- 认知环 SVG：FL-PCL 五层 + 流动光点 + SSE 实时脉冲；**沉默可见**（suppressed 条目与原因同级展示）
- 后端新增：`GET/POST /api/v1/charter`（校验 + 热重载）、`GET /api/v1/system/status`
- 验证清单（全部实测通过）：tsc 零错误；vite 构建 248KB；52/52 测试；ruff 全绿；vite→后端代理全链路；bsk 浏览器四页截图（docs/devlog/screenshots/p5-*.png）
- 当日修复：UTC/本地时区错位（本地中午误判免打扰）；charter 保存相对路径；事件流 content 字段缺失白屏（+ErrorBoundary）
- 详见 `docs/devlog/2026-10-17-p5-dashboard.md` 与 `docs/adr/0009-p5-dashboard-decisions.md`

## P6 实验与度量 ⬜（持续，14 天个人运行）

- **OQ7 模板移除测试**：受控移除目标模板，测量目标队列退化曲线与自省报告质量变化
- **OQ5 周期率剂量—效应**：不同深周期频率下的提醒采纳率/误报率/打扰率
- **目标谱系追踪**：内生目标的目标漂移方向性分析（对应 OQ1 的工程近似）
- **记忆健康指标**：溯源率、自生内容占比、生成链深度分布、检索信噪比（对应 OQ4 的工程近似）
- 产出：实验数据 + 分析报告（论文二《受限常驻系统的实证测量》的素材）

## P7 作品集化 ⬜（按需）

- 实证论文草稿（P6 数据 → OQ5/OQ7 案例研究）
- README 终版、demo GIF/视频、简历表述（克制版："开源项目：理论论文 + 受限实例 + 个人实证数据"）

## 风险登记册

| 风险 | 缓解 |
|---|---|
| LLM API 成本超支 | 高频层本地规则不调 LLM；每日 token 预算硬上限；MockLLM 默认模式 |
| 求职/备考占用时间 | 阶段切碎（3–7 天/阶段），每阶段独立可验证产出；P1 已一次性拿到快赢 |
| "无感收集"伦理争议 | ADR-0004：授权账本 + 审计 + 本地优先；对外统一表述"授权持续感知" |
| 被误读为"AGI 演示" | README 边界表 + 模块分级标记 + 调研文档中的判据体检 |
| 论文与竞品撞车 | 论文判据即护城河：市面无"主动性计量基准"，P6 实验是独占资产 |
