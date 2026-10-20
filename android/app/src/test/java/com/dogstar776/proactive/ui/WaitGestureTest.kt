package com.dogstar776.proactive.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class WaitGestureTest {

    @Test
    fun `wait patterns detected`() {
        listOf("多等我一会", "等我一下", "先等等", "我还没说完", "听我说完", "别急")
            .forEach { assertEquals(WaitGesture.Intent.WAIT, WaitGesture.detect(it)) }
    }

    @Test
    fun `resume patterns detected`() {
        listOf("说完了", "我说完了", "继续", "好了", "可以了", "讲完了")
            .forEach { assertEquals(WaitGesture.Intent.RESUME, WaitGesture.detect(it)) }
    }

    @Test
    fun `none for normal speech`() {
        assertEquals(WaitGesture.Intent.NONE, WaitGesture.detect("今天天气不错"))
        assertEquals(WaitGesture.Intent.NONE, WaitGesture.detect(""))
    }

    @Test
    fun `resume beats wait when both present`() {
        // 含「继续」结尾 → 解除等待优先
        assertEquals(WaitGesture.Intent.RESUME, WaitGesture.detect("我说完了你继续"))
    }
}
