package com.dogstar776.proactive

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.dogstar776.proactive.ui.CosmosApp
import com.dogstar776.proactive.ui.theme.ProactiveTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ProactiveTheme {
                CosmosApp()
            }
        }
    }
}
