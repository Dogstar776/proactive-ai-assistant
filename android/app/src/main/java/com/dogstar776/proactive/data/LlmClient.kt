package com.dogstar776.proactive.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

/** 直连大模型（OpenAI 兼容 /chat/completions）。无后端依赖，加入 Key 即可用。 */
class LlmClient(private val debug: Boolean = false) {

    private val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        isLenient = true
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .apply {
            if (debug) addInterceptor(
                HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC },
            )
        }
        .build()

    /** 构造发送给模型的消息列表（注入 system 设定 + 裁剪历史）。 */
    fun buildMessages(config: LlmConfig, history: List<ChatMessage>): List<ChatMessage> {
        val sys = ChatMessage("system", config.systemPrompt)
        // 保留最近 20 轮，避免超出上下文窗口
        val trimmed = if (history.size > 40) history.takeLast(40) else history
        return listOf(sys) + trimmed
    }

    /** 同步风格挂起函数：调用大模型并返回回复文本。 */
    suspend fun chat(config: LlmConfig, history: List<ChatMessage>): String =
        withContext(Dispatchers.IO) {
            if (config.apiKey.isBlank()) return@withContext demoReply(history)

            val url = "${LlmConfig.normalizeUrl(config.baseUrl)}/chat/completions"
            val body = json.encodeToString(
                ChatRequest.serializer(),
                ChatRequest(model = config.model, messages = buildMessages(config, history)),
            )
            val req = okhttp3.Request.Builder()
                .url(url)
                .addHeader("Authorization", "Bearer ${config.apiKey}")
                .addHeader("Content-Type", "application/json")
                .post(body.toRequestBody("application/json".toMediaType()))
                .build()

            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    val detail = resp.body?.string()?.take(300) ?: resp.message
                    throw LlmException("HTTP ${resp.code}: $detail")
                }
                val parsed = json.decodeFromString(
                    ChatResponse.serializer(),
                    resp.body?.string().orEmpty(),
                )
                parsed.text.ifBlank { "（模型未返回内容）" }
            }
        }

    /** 无 Key 时的本地兜底回复，让应用在没有配置时也「能说话」，便于体验与自测。 */
    private fun demoReply(history: List<ChatMessage>): String {
        val last = history.lastOrNull { it.role == "user" }?.content ?: "你好"
        return "（演示模式 · 未配置 API Key）我听到了：「$last」。配置 Key 后我会用真实大模型回应你。"
    }
}

class LlmException(message: String) : Exception(message)
