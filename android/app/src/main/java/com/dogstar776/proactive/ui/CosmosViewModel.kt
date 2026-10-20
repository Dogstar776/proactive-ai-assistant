package com.dogstar776.proactive.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.dogstar776.proactive.data.ChatMessage
import com.dogstar776.proactive.data.ConversationLog
import com.dogstar776.proactive.data.LlmClient
import com.dogstar776.proactive.data.LlmConfig
import com.dogstar776.proactive.data.SettingsStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 星空调伴的核心状态：连接配置、对话历史、本地实验日志。
 * 语音识别 / TTS / 状态机编排在 CosmosScreen 内完成，VM 只持有数据与纯逻辑。
 */
class CosmosViewModel(application: Application) : AndroidViewModel(application) {

    private val settings = SettingsStore(application)
    private val llm = LlmClient()
    private val log = ConversationLog(application.filesDir)

    private val _config = MutableStateFlow(LlmConfig())
    val config: StateFlow<LlmConfig> = _config.asStateFlow()

    private val _history = MutableStateFlow<List<ChatMessage>>(emptyList())
    val history: StateFlow<List<ChatMessage>> = _history.asStateFlow()

    val isConfigured: Boolean get() = _config.value.apiKey.isNotBlank()

    init {
        viewModelScope.launch { settings.config.collect { _config.value = it } }
    }

    fun saveConfig(url: String, key: String, model: String) = viewModelScope.launch {
        val cfg = LlmConfig(
            baseUrl = LlmConfig.normalizeUrl(url).ifBlank { LlmConfig.DEFAULT_BASE_URL },
            apiKey = key.trim(),
            model = model.trim().ifBlank { LlmConfig.DEFAULT_MODEL },
        )
        settings.save(cfg)
        _config.value = cfg
    }

    fun clearConfig() = viewModelScope.launch {
        settings.clear()
        _config.value = LlmConfig()
    }

    fun appendUser(text: String) {
        _history.value = _history.value + ChatMessage("user", text)
        log.appendTurn("user", text)
    }

    fun appendAssistant(text: String) {
        _history.value = _history.value + ChatMessage("assistant", text)
        log.appendTurn("assistant", text)
    }

    fun logState(state: String) = log.appendState(state)
    fun logGesture(gesture: String, text: String) = log.appendGesture(gesture, text)

    /** 调用大模型（挂起），返回回复文本。 */
    suspend fun reply(): String = llm.chat(_config.value, _history.value)

    fun logCount(): Int = log.count()
    fun exportLog(): String = log.readAll()
    fun exportFile() = log.exportFile()
}
