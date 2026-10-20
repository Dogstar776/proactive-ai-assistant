package com.dogstar776.proactive.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LlmConfigTest {

    @Test
    fun `normalizeUrl adds https`() {
        assertEquals("https://api.example.com/v1", LlmConfig.normalizeUrl("api.example.com/v1"))
    }

    @Test
    fun `normalizeUrl keeps https and strips trailing slash`() {
        assertEquals("https://a.b", LlmConfig.normalizeUrl("https://a.b/"))
    }

    @Test
    fun `normalizeUrl keeps http`() {
        assertEquals("http://127.0.0.1:8787", LlmConfig.normalizeUrl("http://127.0.0.1:8787/"))
    }

    @Test
    fun `blank key means incomplete`() {
        assertFalse(LlmConfig(apiKey = "").isComplete)
        assertTrue(LlmConfig(apiKey = "sk-123").isComplete)
    }
}
