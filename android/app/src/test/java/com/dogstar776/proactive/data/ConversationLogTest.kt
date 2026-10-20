package com.dogstar776.proactive.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class ConversationLogTest {

    private val dir = File.createTempFile("cosmos", "tmp").apply { delete(); mkdirs() }

    @Test
    fun `appends and counts entries`() {
        val log = ConversationLog(dir)
        assertEquals(0, log.count())

        log.appendTurn("user", "你好")
        log.appendTurn("assistant", "你好呀")
        log.appendState("LISTENING")
        log.appendGesture("WAIT", "多等我一会")

        assertEquals(4, log.count())
        val all = log.readAll()
        assertTrue(all.contains("\"kind\":\"turn\""))
        assertTrue(all.contains("\"kind\":\"state\""))
        assertTrue(all.contains("\"kind\":\"gesture\""))
        assertTrue(log.exportFile().exists())
    }
}
