package com.dogstar776.proactive.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.dogstar776.proactive.ui.cosmos.CosmosStage
import kotlinx.coroutines.launch
import java.util.Locale

/**
 * 星空对话主屏（用户定义的交互形式）：
 * 打开即进入聆听，星海与中央光晕随状态流转；
 * 说「多等我一会」→ 光晕收缩，安静等待；说「说完了 / 继续」→ 后台思考 → 开口回应。
 */
@Composable
fun CosmosScreen(vm: CosmosViewModel) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var state by remember { mutableStateOf(CosmosState.IDLE) }
    var transcript by remember { mutableStateOf("") }
    var reply by remember { mutableStateOf("") }
    var pendingText by remember { mutableStateOf("") }
    var waitingMode by remember { mutableStateOf(false) }
    var errorCount by remember { mutableStateOf(0) }
    var showFallback by remember { mutableStateOf(false) }

    val tts = remember { mutableStateOf<TextToSpeech?>(null) }
    val ttsReady = remember { mutableStateOf(false) }
    val recognizer = remember { mutableStateOf<SpeechRecognizer?>(null) }
    val recognizerReady = remember { mutableStateOf(false) }

    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED,
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> hasPermission = granted }

    fun buildIntent() = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        putExtra(RecognizerIntent.EXTRA_LANGUAGE, "zh-CN")
    }

    fun beginSession() {
        if (!hasPermission || !recognizerReady.value) return
        errorCount = 0
        transcript = ""
        pendingText = ""
        waitingMode = false
        state = CosmosState.LISTENING
        vm.logState("LISTENING")
        recognizer.value?.startListening(buildIntent())
    }

    fun continueWaiting() {
        if (!hasPermission || !recognizerReady.value) return
        state = CosmosState.WAITING
        recognizer.value?.startListening(buildIntent())
    }

    fun afterSpeech() {
        beginSession()
    }

    fun triggerRespond(text: String) {
        val userText = text.trim()
        if (userText.isBlank()) { beginSession(); return }
        val isFallback = showFallback
        waitingMode = false
        reply = ""
        state = CosmosState.THINKING
        vm.logState("THINKING")
        vm.appendUser(userText)
        transcript = ""
        scope.launch {
            try {
                val ans = vm.reply()
                vm.appendAssistant(ans)
                reply = ans
                state = CosmosState.SPEAKING
                vm.logState("SPEAKING")
                val t = tts.value
                if (ttsReady.value && t != null) {
                    t.speak(ans, TextToSpeech.QUEUE_FLUSH, null, "cosmos-utter")
                } else {
                    afterSpeech() // TTS 未就绪则直接回到聆听
                }
            } catch (e: Exception) {
                reply = "（出错了：${e.message ?: e.javaClass.simpleName}）"
                state = CosmosState.SPEAKING
                vm.logState("SPEAKING")
                afterSpeech()
            } finally {
                // 文本兜底模式没有语音识别，回合结束后回到待命等待下一次输入
                if (isFallback) state = CosmosState.IDLE
            }
        }
    }

    fun handlePartial(text: String) {
        val g = WaitGesture.detect(text)
        if (!waitingMode) {
            if (g == WaitGesture.Intent.WAIT) {
                waitingMode = true
                state = CosmosState.WAITING
                vm.logState("WAITING")
                vm.logGesture("WAIT", text)
            }
        } else {
            if (g == WaitGesture.Intent.RESUME) {
                triggerRespond(pendingText + text)
            }
        }
    }

    fun handleFinal(text: String) {
        if (text.isNotBlank()) {
            pendingText = (pendingText + " " + text).trim()
            transcript = pendingText
        }
        if (!waitingMode) {
            triggerRespond(pendingText)
        } else {
            continueWaiting() // 继续听，等待「说完了」
        }
    }

    // TTS 初始化
    DisposableEffect(Unit) {
        val t = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                t.language = Locale.SIMPLIFIED_CHINESE
                ttsReady.value = true
                t.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) { scope.launch { afterSpeech() } }
                    override fun onError(utteranceId: String?) { scope.launch { afterSpeech() } }
                })
            }
        }
        tts.value = t
        onDispose { t.stop(); t.shutdown() }
    }

    // 语音识别初始化
    DisposableEffect(Unit) {
        if (SpeechRecognizer.isRecognitionAvailable(context)) {
            val r = SpeechRecognizer.createSpeechRecognizer(context)
            r.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
                override fun onPartialResults(bundle: Bundle?) {
                    val text = bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull().orEmpty()
                    if (text.isNotBlank()) {
                        transcript = text
                        handlePartial(text)
                    }
                }
                override fun onResults(bundle: Bundle?) {
                    val text = bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        ?.firstOrNull().orEmpty()
                    handleFinal(text)
                }
                override fun onError(error: Int) {
                    if (state == CosmosState.SPEAKING) return
                    if (error == SpeechRecognizer.ERROR_CLIENT) return
                    errorCount++
                    if (errorCount < 12) beginSession() // 超时/无匹配等自动续听
                }
            })
            recognizer.value = r
            recognizerReady.value = true
            onDispose { r.destroy() }
        } else {
            showFallback = true
            onDispose {}
        }
    }

    // 权限满足且识别器就绪即进入聆听
    LaunchedEffect(hasPermission, recognizerReady.value) {
        if (hasPermission && recognizerReady.value && state == CosmosState.IDLE) {
            beginSession()
        }
    }

    Box(Modifier.fillMaxSize()) {
        CosmosStage(state, if (state == CosmosState.SPEAKING) reply else transcript)

        Column(
            Modifier.align(Alignment.BottomCenter).padding(bottom = 48.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            when {
                !hasPermission -> Button(
                    onClick = { permissionLauncher.launch(Manifest.permission.RECORD_AUDIO) },
                ) { Text("授予麦克风权限以开始对话") }

                showFallback -> {
                    var txt by remember { mutableStateOf("") }
                    Card(
                        Modifier.fillMaxWidth(0.86f),
                        shape = RoundedCornerShape(18.dp),
                        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.08f)),
                    ) {
                        OutlinedTextField(
                            txt, { txt = it },
                            modifier = Modifier.fillMaxWidth().padding(12.dp),
                            placeholder = { Text("语音不可用，用文字对话", color = Color.White.copy(alpha = 0.5f)) },
                            textStyle = MaterialTheme.typography.bodyLarge.copy(color = Color.White),
                            trailingIcon = {
                                IconButton(onClick = { triggerRespond(txt); txt = "" }) {
                                    Icon(Icons.Filled.Send, null, tint = Color(0xFF7FD4FF))
                                }
                            },
                        )
                    }
                }

                else -> {
                    if (waitingMode || state == CosmosState.LISTENING) {
                        TextButton(onClick = { triggerRespond(pendingText + transcript) }) {
                            Text("我说完了", color = Color.White.copy(alpha = 0.82f))
                        }
                    }
                    IconButton(onClick = { beginSession() }) {
                        Icon(
                            Icons.Filled.Mic,
                            contentDescription = "聆听",
                            tint = if (state == CosmosState.LISTENING) Color(0xFF7FD4FF) else Color.White.copy(alpha = 0.5f),
                            modifier = Modifier.size(38.dp),
                        )
                    }
                }
            }
        }

        if (!hasPermission) {
            Text(
                "需要麦克风权限才能聆听你说话",
                color = Color.White.copy(alpha = 0.45f),
                fontSize = 12.sp,
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp),
            )
        }
    }
}
