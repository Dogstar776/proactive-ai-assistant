# 开发日志 · 2026-10-17 · P5 仪表盘

## 今日完成（P5：iOS 26 Liquid Glass 仪表盘）

### 交付物

- `dashboard/`：Vite + React + TS 单页应用，7 个视图（认知环/事件流/自省/目标/提醒门控/Charter/成本）
- Liquid Glass 设计系统（theme.css）：浅色 mesh 背景、层叠半透明玻璃卡、顶部高光带、
  同心圆角、悬浮胶囊导航、Space Grotesk 数字字体、Apple 弹簧曲线动效
- 认知环 SVG：FL-PCL 五层节点 + 流动光点 + 实时事件脉冲（SSE 事件点亮对应层）
- 后端新增：`GET/POST /api/v1/charter`（校验+热重载）、`GET /api/v1/system/status`
- 截图证据：`docs/devlog/screenshots/p5-*.png`（浏览器实测四联）

### 验证结果（全部实测通过）

| 验证项 | 结果 |
|---|---|
| tsc 类型检查 | 零错误 |
| vite 生产构建 | 248KB JS / 8.9KB CSS，built in ~1s |
| pytest / ruff | 52 passed / All checks passed |
| vite→后端代理 | /health、/api/v1/* 全链路 200 |
| 浏览器实测（bsk） | 认知环/提醒门控/Charter/事件流四页截图验证 |
| SSE 实时流 | 事件流视图与总线联通 |

### 当日修复（三个真 bug，全部有事故记录）

1. **时区错位**：门控用 UTC 时间比 charter 的本地时间字面量 → 本地中午被判免打扰。
   修复：`_in_quiet_hours` 转本地时区；回归测试 `test_gate_not_quiet_at_local_noon`。
2. **charter 保存走相对路径**：`Path("data/charter.yaml")` 无视配置的 data_dir，
   测试中写进真实目录污染后续运行。修复：走 `settings.data_dir`。
3. **事件流白屏**：后端序列化漏 `content` 字段 → 前端 `.slice()` TypeError → 整应用白屏。
   修复：后端补字段 + 前端空值防御 + ErrorBoundary。教训记入 ADR-0009：单测全绿 ≠ 页面不崩。

### 设计亮点

**沉默可见**：提醒台账里 suppressed 条目与 delivered 同级展示，带原因
（quiet_hours/cooldown/daily_budget）——ADR-0008 的"可审计的沉默"在 UI 侧落实，
用户能亲眼看到"系统今天为我沉默了 5 次，分别是为什么"。

### 运行方式

```bash
# 终端 1：后端
cd assistant && uvicorn assistant.api.app:create_app --factory --port 8787
# 终端 2：前端
cd dashboard && npm install && npm run dev    # http://localhost:5173
```

### 下一步

P6 实验与度量：OQ7 模板移除测试、OQ5 周期率剂量效应、记忆健康指标、14 天个人运行。
