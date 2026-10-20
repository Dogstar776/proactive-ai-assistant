package com.dogstar776.proactive.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

/** 本地持久化：大模型连接配置（DataStore，进程内单例）。 */
class SettingsStore(private val context: Context) {

    private val keyBaseUrl = stringPreferencesKey("llm_base_url")
    private val keyApiKey = stringPreferencesKey("llm_api_key")
    private val keyModel = stringPreferencesKey("llm_model")
    private val keySystem = stringPreferencesKey("llm_system_prompt")

    val config: Flow<LlmConfig> = context.dataStore.data.map { p ->
        LlmConfig(
            baseUrl = p[keyBaseUrl] ?: LlmConfig.DEFAULT_BASE_URL,
            apiKey = p[keyApiKey] ?: "",
            model = p[keyModel] ?: LlmConfig.DEFAULT_MODEL,
            systemPrompt = p[keySystem] ?: LlmConfig.DEFAULT_SYSTEM_PROMPT,
        )
    }

    suspend fun current(): LlmConfig = config.first()

    suspend fun save(config: LlmConfig) {
        context.dataStore.edit { p ->
            p[keyBaseUrl] = config.baseUrl.trim().trimEnd('/')
            p[keyApiKey] = config.apiKey.trim()
            p[keyModel] = config.model.trim()
            p[keySystem] = config.systemPrompt
        }
    }

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }
}

private val Context.dataStore by preferencesDataStore(name = "cosmos_settings")
