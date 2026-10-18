package com.dogstar776.proactive.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.dogstar776.proactive.ProactiveApplication
import com.dogstar776.proactive.data.BootData
import com.dogstar776.proactive.data.ConnectionConfig
import com.dogstar776.proactive.data.Goal
import com.dogstar776.proactive.data.ObservedEvent
import com.dogstar776.proactive.data.Reminder
import com.dogstar776.proactive.data.SettingsStore
import com.dogstar776.proactive.data.SystemStatus
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Ready<T>(val data: T) : UiState<T>
    data class Failed(val message: String) : UiState<Nothing>
}

data class HomeState(
    val eventCount: Int = 0,
    val bySource: Map<String, Int> = emptyMap(),
    val activeGoals: Int = 0,
    val goals: List<Goal> = emptyList(),
    val reminders: List<Reminder> = emptyList(),
    val fatigueAskTotal: Int = 0,
    val fatigueRate: Double? = null,
    val charterDomains: List<com.dogstar776.proactive.data.CharterDomain> = emptyList(),
)

class AppViewModel(application: Application) : AndroidViewModel(application) {

    private val app: ProactiveApplication
        get() = getApplication<ProactiveApplication>()

    private val settings: SettingsStore
        get() = app.settings

    private val _config = MutableStateFlow(ConnectionConfig())
    val config: StateFlow<ConnectionConfig> = _config.asStateFlow()

    private val _home = MutableStateFlow<UiState<HomeState>>(UiState.Loading)
    val home: StateFlow<UiState<HomeState>> = _home.asStateFlow()

    private val _events = MutableStateFlow<UiState<List<ObservedEvent>>>(UiState.Loading)
    val events: StateFlow<UiState<List<ObservedEvent>>> = _events.asStateFlow()

    private val _system = MutableStateFlow<UiState<SystemStatus>>(UiState.Loading)
    val system: StateFlow<UiState<SystemStatus>> = _system.asStateFlow()

    private val _busy = MutableStateFlow<String?>(null)
    val busy: StateFlow<String?> = _busy.asStateFlow()

    private val _toast = MutableStateFlow<String?>(null)
    val toast: StateFlow<String?> = _toast.asStateFlow()

    init {
        viewModelScope.launch {
            settings.config.collect { _config.value = it }
        }
    }

    fun refreshAll() {
        refreshHome()
        refreshEvents()
        refreshSystem()
    }

    fun refreshHome() = viewModelScope.launch {
        _home.value = UiState.Loading
        _home.value = try {
            val b: BootData = app.repository.bootstrap()
            UiState.Ready(
                HomeState(
                    eventCount = b.eventCount,
                    bySource = b.bySource,
                    activeGoals = b.activeGoals,
                    goals = b.goals,
                    reminders = b.reminders,
                    fatigueAskTotal = b.fatigue.ask_total,
                    fatigueRate = b.fatigue.approval_rate,
                    charterDomains = b.charterDomains,
                )
            )
        } catch (e: Exception) {
            UiState.Failed(e.readable())
        }
    }

    fun refreshEvents(kind: String? = null) = viewModelScope.launch {
        _events.value = try {
            UiState.Ready(app.repository.events(kind))
        } catch (e: Exception) {
            UiState.Failed(e.readable())
        }
    }

    private fun refreshSystem() = viewModelScope.launch {
        _system.value = try {
            UiState.Ready(app.repository.systemStatus())
        } catch (e: Exception) {
            UiState.Failed(e.readable())
        }
    }

    fun saveConfig(rawUrl: String, apiKey: String) = viewModelScope.launch {
        val url = SettingsStore.normalizeUrl(rawUrl)
        if (url == "http://" || url == "https://" || url.isBlank()) {
            _toast.value = "请填写后端地址"
            return@launch
        }
        settings.save(url, apiKey)
        app.onConfigChanged()
        refreshAll()
        _toast.value = "已保存，正在同步"
    }

    fun forgetConfig() = viewModelScope.launch {
        settings.clear()
        app.onConfigChanged()
        _home.value = UiState.Loading
        _events.value = UiState.Loading
        _toast.value = "已清除本地配置"
    }

    fun runCollectors() = viewModelScope.launch {
        _busy.value = "collect"
        try {
            app.repository.runCollectors(); refreshAll()
            _toast.value = "轻观测周期完成"
        } catch (e: Exception) { _toast.value = e.readable() }
        finally { _busy.value = null }
    }

    fun runDeepCycle() = viewModelScope.launch {
        _busy.value = "deep"
        try {
            app.repository.runDeepCycle(); refreshAll()
            _toast.value = "深周期完成（自省→目标）"
        } catch (e: Exception) { _toast.value = e.readable() }
        finally { _busy.value = null }
    }

    fun runReminders() = viewModelScope.launch {
        _busy.value = "remind"
        try {
            val r = app.repository.runReminders()
            refreshAll()
            _toast.value = "门控完成：放行 ${r.act} · 沉默 ${r.silence} · 请示 ${r.ask}"
        } catch (e: Exception) { _toast.value = e.readable() }
        finally { _busy.value = null }
    }

    fun approve(id: String) = viewModelScope.launch {
        try { app.repository.approve(id); refreshHome(); _toast.value = "已批准并触达" }
        catch (e: Exception) { _toast.value = e.readable() }
    }

    fun reject(id: String) = viewModelScope.launch {
        try { app.repository.reject(id); refreshHome(); _toast.value = "已拒绝" }
        catch (e: Exception) { _toast.value = e.readable() }
    }

    fun consumeToast() { _toast.value = null }
}

/** 异常 → 可读文案（专家规范：4xx 不重试，网络错误提示检查连接）。 */
fun Exception.readable(): String = when (this) {
    is java.net.UnknownHostException -> "找不到服务器：请检查后端地址"
    is java.net.ConnectException -> "连不上后端：请确认服务已启动且地址正确"
    is java.net.SocketTimeoutException -> "连接超时：后端响应太慢"
    is retrofit2.HttpException -> when (code()) {
        401 -> "API Key 无效（401）：请检查 X-API-Key"
        404 -> "接口不存在（404）：后端版本可能不匹配"
        else -> "服务端错误（${code()}）"
    }
    else -> message ?: "未知错误"
}
