package com.dogstar776.proactive.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.outlined.Flag
import androidx.compose.material.icons.outlined.List
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.dogstar776.proactive.ProactiveApplication
import com.dogstar776.proactive.data.CharterDomain
import com.dogstar776.proactive.data.Goal
import com.dogstar776.proactive.data.ObservedEvent
import com.dogstar776.proactive.data.Reminder
import com.dogstar776.proactive.data.SystemStatus

private data class Tab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val TABS = listOf(
    Tab("home", "认知环", Icons.Outlined.Refresh),
    Tab("reminders", "提醒", Icons.Outlined.Notifications),
    Tab("goals", "目标", Icons.Outlined.Flag),
    Tab("events", "事件", Icons.Outlined.List),
    Tab("settings", "设置", Icons.Outlined.Settings),
)

@Composable
fun ProactiveApp() {
    val app = androidx.compose.ui.platform.LocalContext.current.applicationContext as ProactiveApplication
    val vm: AppViewModel = viewModel()
    val nav = rememberNavController()
    val snackbar = remember { SnackbarHostState() }
    val toast by vm.toast.collectAsState()
    val config by vm.config.collectAsState()

    LaunchedEffect(toast) {
        toast?.let { snackbar.showSnackbar(it); vm.consumeToast() }
    }

    if (config.baseUrl.isBlank()) {
        OnboardingScreen(onSave = vm::saveConfig)
        return
    }

    val backStack by nav.currentBackStackEntryAsState()
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("主动式 AI 助理", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = vm::refreshAll) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新")
                    }
                })
        },
        bottomBar = {
            NavigationBar {
                val current = backStack?.destination
                TABS.forEach { tab ->
                    NavigationBarItem(
                        selected = current?.hierarchy?.any { it.route == tab.route } == true,
                        onClick = {
                            nav.navigate(tab.route) {
                                popUpTo("home"); launchSingleTop = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { pad ->
        NavHost(nav, startDestination = "home", modifier = Modifier.padding(pad)) {
            composable("home") { HomeScreen(vm) }
            composable("reminders") { RemindersScreen(vm) }
            composable("goals") { GoalsScreen(vm) }
            composable("events") { EventsScreen(vm) }
            composable("settings") { SettingsScreen(vm, config.baseUrl, config.apiKey) }
        }
    }
}

/* ── 认知环（首页） ── */

@Composable
private fun HomeScreen(vm: AppViewModel) {
    val state by vm.home.collectAsState()
    val busy by vm.busy.collectAsState()
    LaunchedEffect(Unit) { vm.refreshHome() }
    when (val s = state) {
        is UiState.Loading -> CenterBox { CircularProgressIndicator() }
        is UiState.Failed -> CenterBox { ErrorText(s.message) }
        is UiState.Ready -> LazyColumn(
            Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    StatCard("观测事件", s.data.eventCount.toString(), Modifier.weight(1f))
                    StatCard("活跃目标", s.data.activeGoals.toString(), Modifier.weight(1f))
                    StatCard("7日请示", s.data.fatigueAskTotal.toString(), Modifier.weight(1f))
                }
            }
            item {
                Text("认知周期", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    CycleButton("① 轻观测", busy == "collect", vm::runCollectors, Modifier.weight(1f))
                    CycleButton("② 深周期", busy == "deep", vm::runDeepCycle, Modifier.weight(1f))
                    CycleButton("③ 门控", busy == "remind", vm::runReminders, Modifier.weight(1f))
                }
            }
            item { Text("FL-PCL · 受限常驻实例 [B-simulated]", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
            if (s.data.charterDomains.isNotEmpty()) {
                item { Text("Charter 域权重", fontWeight = FontWeight.Bold) }
                items(s.data.charterDomains) { d -> DomainRow(d) }
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier, shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp)) {
            Text(label, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, fontSize = 28.sp, fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Default)
        }
    }
}

@Composable
private fun CycleButton(text: String, loading: Boolean, onClick: () -> Unit, modifier: Modifier) {
    OutlinedButton(onClick = onClick, enabled = !loading, modifier = modifier,
        shape = RoundedCornerShape(14.dp)) {
        if (loading) CircularProgressIndicator(Modifier.size(14.dp), strokeWidth = 2.dp)
        else Text(text, fontSize = 12.sp)
    }
}

@Composable
private fun DomainRow(d: CharterDomain) {
    Column(Modifier.padding(vertical = 4.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(d.name, fontSize = 13.sp)
            Text(d.weight.toInt().toString(), fontSize = 13.sp, fontFamily = FontFamily.Monospace)
        }
        LinearProgressIndicator(
            progress = { (d.weight / 10.0).toFloat().coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth().height(4.dp).padding(top = 2.dp),
        )
    }
}

/* ── 提醒 ── */

@Composable
private fun RemindersScreen(vm: AppViewModel) {
    val state by vm.home.collectAsState()
    val busy by vm.busy.collectAsState()
    LaunchedEffect(Unit) { vm.refreshHome() }
    when (val s = state) {
        is UiState.Loading -> CenterBox { CircularProgressIndicator() }
        is UiState.Failed -> CenterBox { ErrorText(s.message) }
        is UiState.Ready -> {
            val pending = s.data.reminders.filter { it.status == "pending" }
            val others = s.data.reminders.filter { it.status != "pending" }
            LazyColumn(Modifier.fillMaxSize().padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    Button(onClick = vm::runReminders, enabled = busy == null,
                        modifier = Modifier.fillMaxWidth()) { Text("跑一次门控周期") }
                }
                item { Text("待确认（${pending.size}）", fontWeight = FontWeight.Bold) }
                if (pending.isEmpty()) item { EmptyHint("该沉默时沉默，也是一种输出") }
                items(pending, key = { it.reminder_id }) { r ->
                    ReminderCard(r, onApprove = { vm.approve(r.reminder_id) },
                        onReject = { vm.reject(r.reminder_id) })
                }
                item { Spacer(Modifier.height(8.dp)); Text("干预台账（含沉默）", fontWeight = FontWeight.Bold) }
                items(others, key = { it.reminder_id }) { r -> LedgerRow(r) }
            }
        }
    }
}

@Composable
private fun ReminderCard(r: Reminder, onApprove: () -> Unit, onReject: () -> Unit) {
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(16.dp)) {
            Text(r.title, fontWeight = FontWeight.SemiBold)
            if (r.body.isNotBlank()) {
                Text(r.body.take(140), fontSize = 12.sp, maxLines = 3, overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(Modifier.height(4.dp))
            Text("${r.risk_level} · ${r.state} · ${r.decision_reason.take(48)}", fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onApprove, shape = RoundedCornerShape(12.dp)) {
                    Icon(Icons.Default.Check, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text("批准")
                }
                OutlinedButton(onClick = onReject, shape = RoundedCornerShape(12.dp)) {
                    Icon(Icons.Default.Close, null, Modifier.size(16.dp)); Spacer(Modifier.width(4.dp)); Text("拒绝")
                }
            }
        }
    }
}

@Composable
private fun LedgerRow(r: Reminder) {
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(r.title, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(if (r.status == "suppressed") "沉默原因：${r.decision_reason}" else r.decision_reason,
                    fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Text(r.status, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
        }
    }
}

/* ── 目标 ── */

@Composable
private fun GoalsScreen(vm: AppViewModel) {
    val state by vm.home.collectAsState()
    LaunchedEffect(Unit) { vm.refreshHome() }
    when (val s = state) {
        is UiState.Loading -> CenterBox { CircularProgressIndicator() }
        is UiState.Failed -> CenterBox { ErrorText(s.message) }
        is UiState.Ready -> LazyColumn(Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (s.data.goals.isEmpty()) item { EmptyHint("队列为空——先跑深周期") }
            items(s.data.goals, key = { it.goal_id }) { g ->
                Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(g.title, fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.weight(1f), maxLines = 2,
                                overflow = TextOverflow.Ellipsis)
                            Text("%.2f".format(g.priority), fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.height(4.dp))
                        LinearProgressIndicator(progress = { g.priority.toFloat().coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth().height(4.dp))
                        Spacer(Modifier.height(6.dp))
                        Text("${g.template_id} · ${g.risk_level} · ${g.status}",
                            fontSize = 11.sp, fontFamily = FontFamily.Monospace,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        if (g.success_criteria.isNotBlank()) {
                            Text("成功判据：${g.success_criteria}", fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 2, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
            }
        }
    }
}

/* ── 事件流 ── */

@Composable
private fun EventsScreen(vm: AppViewModel) {
    val state by vm.events.collectAsState()
    var kind by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(kind) { vm.refreshEvents(kind) }
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(null to "全部", "calendar_event" to "日程", "todo" to "待办",
                "note" to "笔记", "feed_item" to "信息流").forEach { (k, label) ->
                FilterChip(selected = kind == k, onClick = { kind = k }, label = { Text(label) })
            }
        }
        Spacer(Modifier.height(8.dp))
        when (val s = state) {
            is UiState.Loading -> CenterBox { CircularProgressIndicator() }
            is UiState.Failed -> CenterBox { ErrorText(s.message) }
            is UiState.Ready -> LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (s.data.isEmpty()) item { EmptyHint("暂无事件") }
                items(s.data, key = { it.event_id }) { e ->
                    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)) {
                        Column(Modifier.padding(12.dp)) {
                            Text(e.title, fontWeight = FontWeight.Medium, maxLines = 2,
                                overflow = TextOverflow.Ellipsis)
                            Text("${e.source} · depth ${e.chain_depth} · ${e.observed_at.take(16)}",
                                fontSize = 11.sp, fontFamily = FontFamily.Monospace,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

/* ── 设置 ── */

@Composable
private fun SettingsScreen(vm: AppViewModel, baseUrl: String, apiKey: String) {
    val system by vm.system.collectAsState()
    var url by remember(baseUrl) { mutableStateOf(baseUrl) }
    var key by remember(apiKey) { mutableStateOf(apiKey) }
    LaunchedEffect(Unit) { vm.refreshSystem() }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            OutlinedTextField(url, { url = it }, label = { Text("后端地址") },
                placeholder = { Text("http://192.168.1.5:8787") },
                modifier = Modifier.fillMaxWidth(), singleLine = true)
        }
        item {
            OutlinedTextField(key, { key = it }, label = { Text("API Key（后端配置了才需要）") },
                modifier = Modifier.fillMaxWidth(), singleLine = true)
        }
        item {
            Button(onClick = { vm.saveConfig(url, key) }, modifier = Modifier.fillMaxWidth()) {
                Text("保存并测试连接")
            }
        }
        item {
            OutlinedButton(onClick = vm::forgetConfig, modifier = Modifier.fillMaxWidth()) {
                Text("清除本地配置")
            }
        }
        item { Text("运行状态", fontWeight = FontWeight.Bold) }
        when (val s = system) {
            is UiState.Ready -> item {
                Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        SystemLine("Provider", s.data.provider)
                        SystemLine("模型", s.data.model)
                        SystemLine("深周期/日", s.data.deep_cycles_per_day.toString())
                        SystemLine("日 Token 预算", s.data.daily_token_budget.toString())
                    }
                }
            }
            is UiState.Failed -> item { ErrorText(s.message) }
            UiState.Loading -> item { CircularProgressIndicator() }
        }
        item {
            Text("后台每 15 分钟同步一次；通知动作直接闭环，无需打开应用。",
                fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun SystemLine(k: String, v: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(k, fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(v, fontSize = 13.sp, fontFamily = FontFamily.Monospace)
    }
}

/* ── 通用 ── */

@Composable
private fun CenterBox(content: @Composable () -> Unit) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
}

@Composable
private fun ErrorText(msg: String) {
    Text(msg, color = MaterialTheme.colorScheme.error, fontSize = 14.sp,
        modifier = Modifier.padding(32.dp))
}

@Composable
private fun EmptyHint(text: String) {
    Text(text, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 13.sp,
        modifier = Modifier.padding(vertical = 24.dp))
}
