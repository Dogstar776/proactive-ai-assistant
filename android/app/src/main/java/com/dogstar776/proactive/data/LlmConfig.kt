package com.dogstar776.proactive.data

/** 大模型连接配置（OpenAI 兼容 /chat/completions 接口）。加入 API Key 即可用。 */
data class LlmConfig(
    val baseUrl: String = DEFAULT_BASE_URL,
    val apiKey: String = "",
    val model: String = DEFAULT_MODEL,
    val systemPrompt: String = DEFAULT_SYSTEM_PROMPT,
) {
    /** 是否已完成配置（有 Key 才走真实大模型；否则回落演示模式）。 */
    val isComplete: Boolean get() = apiKey.isNotBlank()

    companion object {
        const val DEFAULT_BASE_URL = "https://api.openai.com/v1"
        const val DEFAULT_MODEL = "gpt-4o-mini"
        const val DEFAULT_SYSTEM_PROMPT =
            "你是一个安静、克制、主动式的人工智能伙伴。你不会打断对方，会认真听完，" +
            "在对方示意「说完了」之后才回应。你的语气平和、简洁、有温度，重视对方的表达，" +
            "不急于给建议，也不抢话。你偶尔会像一位耐心的朋友那样，把对方没说出口的需求接住。"

        /** 规范化用户输入：补 https 前缀、去尾斜杠。 */
        fun normalizeUrl(raw: String): String {
            var s = raw.trim()
            if (s.isNotEmpty() && !s.startsWith("http://") && !s.startsWith("https://")) {
                s = "https://$s"
            }
            return s.trimEnd('/')
        }
    }
}
