package com.dogstar776.proactive.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** 单条对话消息（system / user / assistant）。 */
@Serializable
data class ChatMessage(
    val role: String,
    val content: String,
)

/** 发送给 OpenAI 兼容接口的请求体。 */
@Serializable
data class ChatRequest(
    val model: String,
    val messages: List<ChatMessage>,
    val temperature: Double = 0.7,
    @SerialName("max_tokens") val maxTokens: Int = 1024,
    val stream: Boolean = false,
)

/** OpenAI 兼容响应体（仅取我们需要的字段，其余忽略）。 */
@Serializable
data class ChatResponse(
    val choices: List<Choice> = emptyList(),
    val error: ErrorDetail? = null,
) {
    @Serializable
    data class Choice(
        val index: Int = 0,
        val message: ChatMessage? = null,
        val finish_reason: String? = null,
    )

    @Serializable
    data class ErrorDetail(
        val message: String = "",
        val type: String? = null,
    )

    /** 优先取 choices[0] 的文本；缺失则取 error.message；再缺失给占位文案。 */
    val text: String
        get() = choices.firstOrNull()?.message?.content?.trim()
            ?: error?.message?.takeIf { it.isNotBlank() }
            ?: ""
}
