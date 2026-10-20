package com.dogstar776.proactive.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

/** 应用根：未配置 → 引导；已配置 → 星空对话；设置叠加层。 */
@Composable
fun CosmosApp() {
    val vm: CosmosViewModel = viewModel()
    val config by vm.config.collectAsState()
    var showSettings by remember { mutableStateOf(false) }

    Box(Modifier.fillMaxSize()) {
        when {
            config.apiKey.isBlank() -> OnboardingScreen(
                onSave = { url, key, model -> vm.saveConfig(url, key, model) },
            )
            showSettings -> SettingsScreen(vm, onBack = { showSettings = false })
            else -> {
                CosmosScreen(vm)
                IconButton(
                    onClick = { showSettings = true },
                    modifier = Modifier.align(Alignment.TopEnd).padding(top = 16.dp, end = 16.dp),
                ) {
                    Icon(
                        Icons.Outlined.Settings,
                        contentDescription = "设置",
                        tint = Color.White.copy(alpha = 0.6f),
                        modifier = Modifier.size(26.dp),
                    )
                }
            }
        }
    }
}
