# 安卓 APK · 星空调伴（主动式 AI 伙伴）

手机端的「星空对话伴侣」：打开即是一片缓缓闪烁的宇宙，中央光晕随对话状态流转。
它一直听着你说话；你说「多等我一会」，光晕安静收缩、耐心等待；你说「说完了 / 继续」，
它才在后台思考、开口回应。所有逻辑在本机，加入大模型 API Key 即可真实对话。

## 交互（状态机）

| 状态 | 光晕 | 含义 |
|---|---|---|
| 聆听 LISTENING | 冰蓝脉冲 | 一直听着，实时转写 |
| 等待 WAITING | 暗紫收缩 | 你说「多等我一会」，它屏息等你讲完 |
| 思考 THINKING | 极光流转 | 你说「说完了」，它调用大模型 |
| 说话 SPEAKING | 暖金呼吸 | 它把回答念给你听，念完回到聆听 |

> 「等待 / 继续」意图由本地规则即时判定（`WaitGesture`），不依赖网络，保证信任。

## 加入 APIKEY 即可使用

首次启动填写：**API 地址**（默认 `https://api.openai.com/v1`，兼容任意 OpenAI 接口）、
**API Key**（必填，仅存本机）、**模型**（默认 `gpt-4o-mini`）。
也可先点「演示模式」体验（无 Key 时返回本地兜底回应）。

- **CI 构建**：GitHub Actions 每次推送自动构建。从仓库 → Actions → `android` workflow
  → Artifacts 下载 `proactive-assistant-debug.apk`（见 `.github/workflows/android.yml`）。
- **本地构建**：`gradle assembleDebug`（需 JDK 17 + Android SDK）。
- 需要麦克风权限（用于语音聆听）；若设备无语音识别，自动回落为文字输入框。

## 工程细节

- **minSdk 26 / targetSdk 35**；Kotlin 2.0 + Compose BOM + Material3
- **星空前台**：`ui/cosmos/CosmosStage.kt` 用 Compose Canvas 绘制星海 + 径向渐变光晕 + 极光/声波
- **状态机与语音**：`ui/CosmosScreen.kt` 用 `SpeechRecognizer`（聆听）+ `TextToSpeech`（念出）+
  本地 `WaitGesture` 判定等待/继续，编排 LISTENING→WAITING→THINKING→SPEAKING 闭环
- **大模型直连**：`data/LlmClient.kt` 调 OpenAI 兼容 `/chat/completions`，无后端依赖
- **配置持久化**：DataStore Preferences（baseUrl / apiKey / model）
- **实验日志**：`data/ConversationLog.kt` 把每轮对话、状态切换、等待意图写入本地 JSONL，
  14 天实验结束后在「设置 → 导出日志并分享」通过 FileProvider 分享给研究者分析
- **测试**：JUnit 单测覆盖 `WaitGesture` 意图、URL 规范化、对话序列化、日志写入
  （`gradle testDebugUnitTest`）

## 已知边界（诚实声明）

- 语音识别依赖设备上的识别引擎（多为 Google 服务）；无该引擎时自动回落文字输入
- 语音聆听为连续模式，识别超时/无匹配会自动续听（上限 12 次/轮），避免死循环靠手动麦克风键
- 大模型调用走网络，需本机可访问所填 API 地址；失败会显示错误文案并回到聆听
- 配置与日志仅存本机，不上传任何服务器（演示/自托管均可）
