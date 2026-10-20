package com.dogstar776.proactive.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.dogstar776.proactive.data.LlmConfig

/** 首次启动：填入大模型 API Key 即可开始（或先体验演示模式）。 */
@Composable
fun OnboardingScreen(onSave: (String, String, String) -> Unit) {
    var url by remember { mutableStateOf(LlmConfig.DEFAULT_BASE_URL) }
    var key by remember { mutableStateOf("") }
    var model by remember { mutableStateOf(LlmConfig.DEFAULT_MODEL) }

    Box(
        Modifier.fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFF020208), Color(0xFF0A0812)))),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(28.dp),
        ) {
            Text("主动式 AI 伙伴", fontSize = 26.sp, fontWeight = FontWeight.Bold, color = Color.White)
            Spacer(Modifier.height(6.dp))
            Text("星空下，它一直听着你", fontSize = 13.sp, color = Color.White.copy(alpha = 0.6f))
            Spacer(Modifier.height(28.dp))
            Card(
                Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.06f)),
            ) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(url, { url = it }, label = { Text("API 地址") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                        textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White))
                    OutlinedTextField(key, { key = it }, label = { Text("API Key") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                        textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White))
                    OutlinedTextField(model, { model = it }, label = { Text("模型") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                        textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White))
                    Button(onClick = { onSave(url, key, model) },
                        Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)) {
                        Text("保存并开始对话")
                    }
                    TextButton(onClick = { onSave(url, "", model) }, Modifier.fillMaxWidth()) {
                        Text("先体验演示模式（无需 Key）", color = Color.White.copy(alpha = 0.6f))
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            Text(
                "兼容 OpenAI 的任意接口；填入 Key 后即可真实对话。配置仅存于本机。",
                fontSize = 12.sp, color = Color.White.copy(alpha = 0.4f),
            )
        }
    }
}
