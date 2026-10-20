package com.dogstar776.proactive.data

import kotlinx.serialization.json.Json
import java.io.File
import java.time.Instant

/**
 * 对话 / 状态日志：写入本地 JSONL，供 14 天实验结束后导出分析。
 *
 * 每条记录一行 JSON：{ ts, kind, role?, content?, state? }
 * - kind=turn：一轮对话（role=user/assistant）
 * - kind=state：状态机切换（LISTENING/WAITING/THINKING/SPEAKING）
 * - kind=gesture：识别到的「等待/继续」意图
 *
 * 目录由调用方注入（应用传 context.filesDir，测试传临时目录），保证可在 JVM 单测。
 */
class ConversationLog(private val dir: File) {

    private val file = File(dir, "cosmos_log.jsonl")
    private val json = Json { encodeDefaults = true }

    @Serializable
    data class Entry(
        val ts: String,
        val kind: String,
        val role: String? = null,
        val content: String? = null,
        val state: String? = null,
    )

    fun appendTurn(role: String, content: String, state: String? = null) {
        append(Entry(Instant.now().toString(), "turn", role = role, content = content, state = state))
    }

    fun appendState(state: String) {
        append(Entry(Instant.now().toString(), "state", state = state))
    }

    fun appendGesture(gesture: String, text: String) {
        append(Entry(Instant.now().toString(), "gesture", content = "$gesture|$text"))
    }

    @Synchronized
    private fun append(e: Entry) {
        file.appendText(json.encodeToString(Entry.serializer(), e) + "\n")
    }

    fun count(): Int = if (!file.exists()) 0 else file.readLines().count { it.isNotBlank() }

    fun readAll(): String = if (file.exists()) file.readText() else ""

    /** 导出目标文件（由 UI 通过 FileProvider 分享）。 */
    fun exportFile(): File = file
}
