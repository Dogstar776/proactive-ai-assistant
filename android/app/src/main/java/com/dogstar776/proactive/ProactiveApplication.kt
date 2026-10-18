package com.dogstar776.proactive

import android.app.Application
import com.dogstar776.proactive.data.ApiFactory
import com.dogstar776.proactive.data.ApiService
import com.dogstar776.proactive.data.Repository
import com.dogstar776.proactive.data.SettingsStore
import com.dogstar776.proactive.sync.Notifier
import com.dogstar776.proactive.sync.SyncWorker
import kotlinx.coroutines.runBlocking

class ProactiveApplication : Application() {

    lateinit var settings: SettingsStore
        private set

    @Volatile
    private var cachedApi: ApiService? = null

    /** 当前 API 实例（未配置时回落到本地默认地址，调用方会拿到可读错误）。 */
    val api: ApiService
        get() = cachedApi ?: synchronized(this) {
            cachedApi ?: buildApi().also { cachedApi = it }
        }

    val repository: Repository by lazy {
        Repository(settings = settings, apiProvider = { if (configured()) api() else null })
    }

    override fun onCreate() {
        super.onCreate()
        settings = SettingsStore(this)
        Notifier.ensureChannels(this)
        SyncWorker.ensurePeriodic(this)
    }

    /** 连接配置变化后调用：重置 API 实例 + 立即同步一次。 */
    suspend fun onConfigChanged() {
        synchronized(this) { cachedApi = null }
        SyncWorker.syncNow(this)
    }

    fun configured(): Boolean = runBlocking { settings.current().baseUrl.isNotBlank() }

    private fun buildApi(): ApiService = runBlocking {
        val cfg = settings.current()
        ApiFactory.create(cfg.baseUrl.ifBlank { DEFAULT_BASE_URL }) {
            runBlocking { settings.current().apiKey }
        }
    }

    companion object {
        const val DEFAULT_BASE_URL = "http://127.0.0.1:8787"
    }
}
