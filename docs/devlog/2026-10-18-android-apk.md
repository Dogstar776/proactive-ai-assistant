# 开发日志 · 2026-10-18 · 安卓 APK 客户端 + 后端 API Key 鉴权

## 今日完成（用户要求优先：安卓 APK，成熟化，APIKEY 即用）

### 后端：远程接管入口

- `api/auth.py`：API Key 中间件——配置 `API_KEY` 后 `/api/v1/*` 要求 `X-API-Key`
  （常数时间比较）；`/health /ready /docs` 保持开放供连通性测试；未配置时零开销跳过
- config 新增 `api_key`；`.env.example` 补说明；测试 `test_auth.py`（401/放行/错 key/开放模式）

### 安卓：完整 Kotlin + Compose 工程（android/，约 20 个文件）

- **架构**：Jetpack Compose + MVVM（Repository 单一数据源 + AndroidViewModel + UiState 密封类）
- **接入**：Retrofit + kotlinx.serialization（ignoreUnknownKeys，后端加字段不炸旧客户端）
  + AuthInterceptor 注入 X-API-Key + DataStore 持久化连接配置
- **五个界面**：引导页（URL + Key）→ 认知环（统计 + 三周期按钮 + charter 域权重）
  → 提醒（待确认队列批准/拒绝 + 干预台账含沉默原因）→ 目标（优先级条）→ 事件（筛选）
  → 设置（连接配置 + 运行状态 + 清除）
- **主动闭环**：SyncWorker 15 分钟周期同步（网络约束 + 失败退避重试）；
  Notifier 双频道通知；**待确认通知带批准/拒绝动作，ReminderActionReceiver
  直接调后端闭环，无需打开应用**；已通知 ID 去重（DataStore）
- **主题**：Material3 动态取色 + Liquid Glass 同源浅色基调（ADR-0009）
- **测试**：JUnit 单测——URL 规范化、通知挑选逻辑（delivered/approved/去重）、鉴权头注入
- **CI**：`.github/workflows/android.yml`——JDK17 + Gradle + 单测 + assembleDebug
  + APK 产物上传（本机无 Android SDK/JDK17，构建在 CI 完成，用户从 Actions 下载）

### 本机环境事实（记录备查）

- 本机只有 JDK 1.8、无 Android SDK/Gradle/kotlinc → 无法本地构建；
  CI 是唯一构建路径（ubuntu-latest 自带工具链）
- node_modules 用 Junction 链到受管工作区；npm 在
  `C:\Users\admin\.workbuddy\binaries\node\versions\22.22.2-6\npm.cmd`（`node install` 不可用）

### 当日修复

- ProactiveApplication 的 API 懒初始化逻辑重构（原写法有缓存赋值 bug）
- ViewModel 工厂：改 AndroidViewModel + 默认工厂（原写法 factory 传错）
- 通知栏动作的 goAsync 用法改正（PendingResult.finish 生命周期）
- 导航图标从 Spacer 占位改为真实 Outlined 图标

### 已知边界（诚实声明）

- 轮询 15 分钟是系统建议值，Doze 模式下可能更长——移动端"主动"实时性弱于 Web SSE，
  是省电取舍，不是缺陷掩饰；
- APK 未经真机运行验证（本机无模拟器/SDK）——CI 构建通过 + 单测通过是当前验证边界，
  真机验证留待用户；
- 后端需手机可达（同局域网或公网）；未做内网穿透与 TLS 固定。

### 下一步

P6 实验与度量（OQ7 模板移除 / OQ5 剂量效应 / 记忆健康 / 14 天个人运行）——
用户已表示先做 APK，P6 设计待发确认。
