package com.dogstar776.proactive.ui.cosmos

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.dogstar776.proactive.ui.CosmosState
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * 星空 + 中央光晕（APK 的门面）。
 *
 * 设计（用户原话落地）：
 * - 黑色宇宙、星星点点闪烁、缓慢漂移；
 * - 中央一团变化的光晕，颜色随对话状态流转；
 * - 状态：聆听（冰蓝脉冲）/ 等待用户说完（暗紫收缩，几乎静止）/ 思考（极光流转）/ 说话（暖金呼吸）。
 */
@Composable
fun CosmosStage(
    state: CosmosState,
    transcript: String,
    modifier: Modifier = Modifier,
) {
    val infinite = rememberInfiniteTransition(label = "cosmos")

    // 全局时间（驱动星的闪烁与漂移）
    val time by infinite.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(200_000, easing = LinearEasing),
        ),
        label = "time",
    )

    // 光晕呼吸
    val breath by infinite.animateFloat(
        initialValue = 0.85f,
        targetValue = 1.15f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = breathMillis(state), easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "breath",
    )

    val stars = remember { List(180) { Star() } }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFF020208), Color(0xFF0A0812)))),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            val cx = w / 2f
            val cy = h / 2f

            // ── 星海 ──
            stars.forEach { star ->
                val px = (star.x * w + time * star.driftX) % w
                val py = (star.y * h + time * star.driftY) % h
                val twinkle = 0.45f + 0.55f * sin(time * star.twinkleSpeed + star.phase)
                val alpha = (star.baseAlpha * twinkle).coerceIn(0.05f, 1f)
                drawCircle(
                    color = star.color.copy(alpha = alpha),
                    radius = star.radius,
                    center = Offset(px, py),
                )
                // 亮星加十字光芒
                if (star.radius > 1.6f) {
                    val flare = 6f * star.radius * twinkle
                    drawLine(
                        color = star.color.copy(alpha = alpha * 0.35f),
                        start = Offset(px - flare, py),
                        end = Offset(px + flare, py),
                        strokeWidth = 0.8f,
                    )
                    drawLine(
                        color = star.color.copy(alpha = alpha * 0.35f),
                        start = Offset(px, py - flare),
                        end = Offset(px, py + flare),
                        strokeWidth = 0.8f,
                    )
                }
            }

            // ── 中央光晕 ──
            val halo = haloColors(state)
            val baseR = size.minDimension * 0.19f * breath
            drawHalo(cx, cy, baseR, halo, time, state)
        }

        // 中央文字层（状态 + 实时转写）
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(horizontal = 40.dp),
        ) {
            Text(
                text = stateLabel(state),
                color = Color.White.copy(alpha = 0.92f),
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium,
                fontFamily = FontFamily.SansSerif,
                letterSpacing = 2.sp,
            )
            if (transcript.isNotBlank()) {
                Spacer(Modifier.height(14.dp))
                Text(
                    text = transcript,
                    color = Color.White.copy(alpha = 0.72f),
                    fontSize = 17.sp,
                    textAlign = TextAlign.Center,
                    lineHeight = 26.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

private fun breathMillis(state: CosmosState): Int = when (state) {
    CosmosState.LISTENING -> 2600
    CosmosState.WAITING -> 5200      // 等待模式：极慢，像屏住呼吸
    CosmosState.THINKING -> 900      // 思考：快速流转
    CosmosState.SPEAKING -> 1700
    CosmosState.IDLE -> 4000
}

private fun stateLabel(state: CosmosState): String = when (state) {
    CosmosState.IDLE -> "待命"
    CosmosState.LISTENING -> "我在听"
    CosmosState.WAITING -> "你说，我等着"
    CosmosState.THINKING -> "让我想想"
    CosmosState.SPEAKING -> "我说"
}

private fun haloColors(state: CosmosState): List<Color> = when (state) {
    CosmosState.LISTENING -> listOf(Color(0xFF7FD4FF), Color(0xFF2E7FD9), Color(0x003E7FD9))
    CosmosState.WAITING -> listOf(Color(0xFF9B8FD4), Color(0xFF4A3D7A), Color(0x001F1A3D))
    CosmosState.THINKING -> listOf(Color(0xFF8FF7D2), Color(0xFF7A5CE0), Color(0x00B44CE0))
    CosmosState.SPEAKING -> listOf(Color(0xFFFFD9A0), Color(0xFFE08A3C), Color(0x00E08A3C))
    CosmosState.IDLE -> listOf(Color(0xFFB8C6E0), Color(0xFF3A4560), Color(0x00162033))
}

/** 光晕：三层径向渐变 + 旋转的极光带（思考态）。 */
private fun DrawScope.drawHalo(
    cx: Float,
    cy: Float,
    baseR: Float,
    colors: List<Color>,
    time: Float,
    state: CosmosState,
) {
    // 外层柔光
    drawCircle(
        brush = Brush.radialGradient(
            colors = colors,
            center = Offset(cx, cy),
            radius = baseR * 2.6f,
        ),
        radius = baseR * 2.6f,
        center = Offset(cx, cy),
    )
    // 内核
    drawCircle(
        brush = Brush.radialGradient(
            colors = listOf(
                Color.White.copy(alpha = 0.85f),
                colors.first().copy(alpha = 0.55f),
                Color.Transparent,
            ),
            center = Offset(cx, cy),
            radius = baseR,
        ),
        radius = baseR,
        center = Offset(cx, cy),
    )
    // 思考态：旋转极光带
    if (state == CosmosState.THINKING) {
        val ringR = baseR * 1.5f
        repeat(3) { i ->
            val a = time * 0.9f + i * (2.1f)
            drawArc(
                color = colors[i % colors.size].copy(alpha = 0.30f),
                startAngle = Math.toDegrees(a.toDouble()).toFloat(),
                sweepAngle = 130f,
                useCenter = false,
                topLeft = Offset(cx - ringR, cy - ringR),
                size = Size(ringR * 2, ringR * 2),
                style = Stroke(width = 2.2f),
            )
        }
    }
    // 聆听态：声波圆环
    if (state == CosmosState.LISTENING) {
        repeat(2) { i ->
            val phase = (time * 0.6f + i * 0.5f) % 1f
            drawCircle(
                color = colors.first().copy(alpha = 0.35f * (1f - phase)),
                radius = baseR * (1.3f + phase * 1.4f),
                center = Offset(cx, cy),
                style = Stroke(width = 1.4f),
            )
        }
    }
}

private class Star {
    val x: Float = Random.nextFloat()
    val y: Float = Random.nextFloat()
    val radius: Float = 0.5f + Random.nextFloat() * 1.8f
    val baseAlpha: Float = 0.35f + Random.nextFloat() * 0.65f
    val twinkleSpeed: Float = 0.4f + Random.nextFloat() * 1.6f
    val phase: Float = Random.nextFloat() * 6.28f
    val driftX: Float = (Random.nextFloat() - 0.5f) * 6f   // px/s 级
    val driftY: Float = (Random.nextFloat() - 0.5f) * 2.5f
    val color: Color = when (Random.nextInt(5)) {
        0 -> Color(0xFFBFD8FF)
        1 -> Color(0xFFFFF3D6)
        2 -> Color(0xFFD6C8FF)
        3 -> Color(0xFFC8FFF0)
        else -> Color.White
    }
}
