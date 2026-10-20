package com.dogstar776.proactive.data

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class ChatSerializationTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `roundtrip chat request`() {
        val req = ChatRequest(
            model = "gpt-4o-mini",
            messages = listOf(ChatMessage("user", "hi")),
        )
        val s = json.encodeToString(ChatRequest.serializer(), req)
        val back = json.decodeFromString(ChatRequest.serializer(), s)
        assertEquals("gpt-4o-mini", back.model)
        assertEquals("hi", back.messages.first().content)
        assertEquals(false, back.stream)
    }

    @Test
    fun `parse openai response`() {
        val raw = """
        {
          "id":"1","object":"chat.completion","model":"gpt-4o-mini",
          "choices":[{"index":0,"message":{"role":"assistant","content":"你好"},"finish_reason":"stop"}],
          "usage":{"prompt_tokens":1,"completion_tokens":1}
        }
        """.trimIndent()
        val resp = json.decodeFromString(ChatResponse.serializer(), raw)
        assertEquals("你好", resp.text)
    }

    @Test
    fun `parse error response`() {
        val raw = """{"error":{"message":"invalid api key","type":"auth"}}"""
        val resp = json.decodeFromString(ChatResponse.serializer(), raw)
        assertEquals("invalid api key", resp.text)
    }
}
