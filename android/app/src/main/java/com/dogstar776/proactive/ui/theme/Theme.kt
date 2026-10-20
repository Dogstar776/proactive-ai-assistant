package com.dogstar776.proactive.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/* 星空深色调：与宇宙前台一致（强制深色，不随系统切换）。 */
private val Accent = Color(0xFF0A84FF)
private val AccentDeep = Color(0xFF0A3A6B)
private val Ok = Color(0xFF30D158)
private val Danger = Color(0xFFFF453A)

private val DarkScheme = darkColorScheme(
    primary = Accent,
    onPrimary = Color.White,
    primaryContainer = AccentDeep,
    onPrimaryContainer = Accent,
    secondary = Color(0xFF5E5CE6),
    tertiary = Ok,
    error = Danger,
    background = Color(0xFF020208),
    onBackground = Color.White,
    surface = Color(0xFF0E0E16),
    onSurface = Color.White,
    surfaceVariant = Color(0xFF1A1A24),
    onSurfaceVariant = Color(0xFFB8B8C8),
    outline = Color(0x33FFFFFF),
)

@Composable
fun ProactiveTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkScheme, content = content)
}

object GlassColors {
    val accent = Accent
    val ok = Ok
    val danger = Danger
}
