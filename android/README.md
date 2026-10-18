# 安卓 APK · 主动式 AI 助理客户端

手机端的"主动式"闭环：后台每 15 分钟同步一次后端，把门控放行的提醒转成本地通知，
待确认事项从通知栏直接批准/拒绝——**无需打开应用**。

## 架构

```
┌────────────────────────────┐         ┌──────────────────────────────┐
│  安卓 APK（本目录）          │  HTTPS  │  后端（assistant/，你的电脑）  │
│  Jetpack Compose + MVVM    │ ──────► │  FastAPI :8787               │
│  · 连接配置（URL + API Key）│ X-API-Key│  · API Key 鉴权（可选开启）   │
│  · 认知环 / 提醒 / 目标 / 事件│ ◄────── │  · 四态门控 / 提醒引擎        │
│  · WorkManager 15min 轮询   │  JSON   │  · SSE（Web 仪表盘专用）      │
│  · 通知 + 批准/拒绝动作      │         └──────────────────────────────┘
└────────────────────────────┘
```

移动端用轮询而非 SSE：省电与保活的权衡，频率由后端 charter 的
`intervention_budget` 与免打扰共同控制（双端共治，论文 3.5）。

## 加入 APIKEY 即可使用

两步：

**1. 电脑端跑后端**（`assistant/` 目录）：

```bash
# .env 里设置（.env.example 有模板）
API_KEY=你的密钥
# 监听所有网卡，手机才能通过局域网访问
uvicorn assistant.api.app:create_app --factory --host 0.0.0.0 --port 8787
```

> 不设 `API_KEY` 时后端不鉴权（本地单用户模式）；设了之后 `/api/v1/*` 要求
> `X-API-Key` 头，本 APK 会自动带上。

**2. 手机端装 APK**：

- CI 构建：GitHub Actions 每次推送自动构建，从仓库 Actions → "android" workflow
  → Artifacts 下载 `proactive-assistant-debug.apk`（见 `.github/workflows/android.yml`）
- 本地构建：`gradle assembleDebug`（需要 JDK 17 + Android SDK）
- 安装后首次启动填两个值：**后端地址**（如 `http://192.168.1.5:8787`，手机与电脑
  同一 Wi-Fi 填电脑局域网 IP，`ipconfig` 可查）+ **API Key**（后端没设就留空）

## 功能（与 Web 仪表盘 1:1，不阉割）

| 界面 | 内容 |
|---|---|
| 认知环 | 观测事件/活跃目标/7 日请示统计 + 三个周期按钮（轻观测/深周期/门控） |
| 提醒 | 待确认队列（批准/拒绝）+ 干预台账（含被沉默的及原因） |
| 目标 | 优先级队列 + template-based 徽章 + 成功判据 |
| 事件 | 事件流 + 类型筛选 + provenance/depth |
| 设置 | 后端地址/API Key + 运行状态（Provider/预算）+ 清除配置 |

## 工程细节

- **minSdk 26 / targetSdk 35**；Kotlin 2.0 + Compose BOM + Material3（动态取色）
- **MVVM**：`Repository` 单一数据源，`AppViewModel` 管理 `UiState`（Loading/Ready/Failed）
- **配置持久化**：DataStore Preferences（baseUrl / apiKey / 已通知 ID 去重）
- **鉴权**：`AuthInterceptor` 注入 `X-API-Key`；401 → "API Key 无效"可读文案
- **后台同步**：`SyncWorker` 周期 15 分钟（NetworkType.CONNECTED 约束），
  失败自动退避重试；通知去重靠 DataStore 记录已通知 ID
- **通知**：两个频道（主动提醒 DEFAULT / 待确认 HIGH），待确认带批准/拒绝动作，
  `ReminderActionReceiver` 直接调后端闭环
- **错误处理**：异常映射可读文案（UnknownHost/Connect/Timeout/401/404 各有文案）
- **测试**：JUnit 单测覆盖 URL 规范化、通知挑选逻辑、鉴权头注入
  （`gradle testDebugUnitTest`）

## 已知边界（诚实声明）

- 轮询间隔 15 分钟是系统建议值，Doze 模式下可能更长——"主动"的实时性弱于 Web 端 SSE，
  这是移动端省电约束的自觉取舍，不是缺陷掩饰；
- 通知依赖系统权限，用户拒绝时静默降级；
- 后端需手机可达（同一局域网或公网部署）；暂未做内网穿透与 TLS 固定。
