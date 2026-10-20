package com.dogstar776.proactive.ui

import android.content.Context
import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.dogstar776.proactive.data.LlmConfig
import java.io.File

@Composable
fun SettingsScreen(vm: CosmosViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    val config by vm.config.collectAsState()
    var url by remember(config.baseUrl) { mutableStateOf(config.baseUrl) }
    var key by remember(config.apiKey) { mutableStateOf(config.apiKey) }
    var model by remember(config.model) { mutableStateOf(config.model) }

    Column(
        Modifier.fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFF020208), Color(0xFF0A0812))))
            .padding(20.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Filled.ArrowBack, contentDescription = "返回", tint = Color.White)
            }
            Text("设置", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color.White)
        }
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(url, { url = it }, label = { Text("API 地址") },
            modifier = Modifier.fillMaxWidth(), singleLine = true,
            textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White))
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(key, { key = it }, label = { Text("API Key") },
            modifier = Modifier.fillMaxWidth(), singleLine = true,
            textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White))
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(model, { model = it }, label = { Text("模型") },
            modifier = Modifier.fillMaxWidth(), singleLine = true,
            textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White))
        Spacer(Modifier.height(16.dp))
        Button(onClick = { vm.saveConfig(url, key, model); onBack() },
            Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(14.dp)) { Text("保存") }

        Spacer(Modifier.height(18.dp))
        Text("实验日志（14 天收集）", fontSize = 14.sp, color = Color.White, fontWeight = FontWeight.Bold)
        Text("已记录 ${vm.logCount()} 条交互", fontSize = 12.sp, color = Color.White.copy(alpha = 0.6f))
        Spacer(Modifier.height(8.dp))
        Button(onClick = { exportLog(context, vm.exportLog()) },
            Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(14.dp)) { Text("导出日志并分享") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = { vm.clearConfig(); onBack() },
            Modifier.fillMaxWidth().padding(vertical = 4.dp),
            shape = RoundedCornerShape(14.dp)) { Text("清除配置（回到演示模式）") }
    }
}

/** 通过 FileProvider 把日志以文本附件分享出去（微信/邮件/保存均可）。 */
private fun exportLog(context: Context, content: String) {
    val file = File(context.cacheDir, "cosmos_log_${System.currentTimeMillis()}.jsonl")
    file.writeText(content)
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, "导出 14 天实验日志"))
}
