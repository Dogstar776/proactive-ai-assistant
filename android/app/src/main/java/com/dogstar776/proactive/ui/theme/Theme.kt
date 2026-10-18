package com.dogstar776.proactive.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

/* Liquid Glass 浅色基调：与 Web 仪表盘同一套色（ADR-0009） */
private val Accent = Color(0xFF0A84FF)
private val AccentDeep = Color(0xFF0066CC)
private val Ok = Color(0xFF30D158)
private val Warn = Color(0xFFFF9F0A)
private val Danger = Color(0xFFFF453A)
private val Neutral = Color(0xFF8E8E93)

private val LightScheme = lightColorScheme(
    primary = Accent,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD6E9FF),
    onPrimaryContainer = AccentDeep,
    secondary = Color(0xFF5E5CE6),
    tertiary = Ok,
    error = Danger,
    background = Color(0xFFF5F6FA),
    onBackground = Color(0xFF1D1D1F),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF1D1D1F),
    surfaceVariant = Color(0xFFEFEFF4),
    onSurfaceVariant = Color(0xFF6E6E73),
    outline = Color(0x3391919A),
)

@Composable
fun ProactiveTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamic: Boolean = true,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val scheme = when {
        dynamic && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ->
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        else -> LightScheme
    }
    MaterialTheme(colorScheme = scheme, content = content)
}

object GlassColors {
    val accent = Accent
    val ok = Ok
    val warn = Warn
    val danger = Danger
    val neutral = Neutral
}
