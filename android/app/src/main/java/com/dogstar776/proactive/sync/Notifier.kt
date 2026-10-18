package com.dogstar776.proactive.sync

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.dogstar776.proactive.MainActivity
import com.dogstar776.proactive.ProactiveApplication
import com.dogstar776.proactive.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** 本地通知：主动式助理在手机上的"触达渠道"（论文 3.5 R1 行为：只读摘要 + 留痕）。 */
object Notifier {

    const val CHANNEL_REMINDERS = "proactive_reminders"
    const val CHANNEL_PENDING = "proactive_pending"
    private const val GROUP_KEY = "com.dogstar776.proactive.REMINDERS"

    fun ensureChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val rm = context.getSystemService(NotificationManager::class.java)
            val reminders = NotificationChannel(
                CHANNEL_REMINDERS, "主动提醒", NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = "系统自主放行并触达的只读提醒" }
            val pending = NotificationChannel(
                CHANNEL_PENDING, "待确认事项", NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = "需要你批准或拒绝的事项（超时默认不行动）" }
            rm.createNotificationChannels(listOf(reminders, pending))
        }
    }

    fun notifyDelivered(context: Context, id: String, title: String, body: String) {
        val intent = Intent(context, MainActivity::class.java)
        val contentPi = PendingIntent.getActivity(
            context, id.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val n = NotificationCompat.Builder(context, CHANNEL_REMINDERS)
            .setSmallIcon(R.drawable.ic_stat_proactive)
            .setContentTitle(title)
            .setContentText(body.take(120))
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(contentPi)
            .setAutoCancel(true)
            .setGroup(GROUP_KEY)
            .build()
        notify(context, id.hashCode(), n)
    }

    fun notifyPending(context: Context, id: String, title: String, body: String) {
        val open = Intent(context, MainActivity::class.java)
        val openPi = PendingIntent.getActivity(
            context, id.hashCode(), open,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val approvePi = actionPi(context, id, ReminderActionReceiver.ACTION_APPROVE)
        val rejectPi = actionPi(context, id, ReminderActionReceiver.ACTION_REJECT)
        val n = NotificationCompat.Builder(context, CHANNEL_PENDING)
            .setSmallIcon(R.drawable.ic_stat_proactive)
            .setContentTitle("待确认：$title")
            .setContentText(body.take(120))
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(openPi)
            .addAction(0, "批准", approvePi)
            .addAction(0, "拒绝", rejectPi)
            .setAutoCancel(true)
            .setGroup(GROUP_KEY)
            .build()
        notify(context, id.hashCode() + 1, n)
    }

    private fun actionPi(context: Context, id: String, action: String): PendingIntent =
        PendingIntent.getBroadcast(
            context, (id + action).hashCode(),
            Intent(context, ReminderActionReceiver::class.java)
                .setAction(action)
                .putExtra(ReminderActionReceiver.EXTRA_ID, id),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

    private fun notify(context: Context, notificationId: Int, n: android.app.Notification) {
        try {
            if (NotificationManagerCompat.from(context).areNotificationsEnabled()) {
                NotificationManagerCompat.from(context).notify(notificationId, n)
            }
        } catch (_: SecurityException) {
            // 用户未授予通知权限：静默降级（不崩溃）
        }
    }
}

/** 通知栏动作 → 直接调后端闭环（无需打开应用）。 */
class ReminderActionReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_APPROVE = "com.dogstar776.proactive.APPROVE"
        const val ACTION_REJECT = "com.dogstar776.proactive.REJECT"
        const val EXTRA_ID = "reminder_id"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getStringExtra(EXTRA_ID) ?: return
        val app = context.applicationContext as? ProactiveApplication ?: return
        val approve = intent.action == ACTION_APPROVE
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (approve) app.repository.approve(id) else app.repository.reject(id)
            } catch (_: Exception) {
                // 网络失败：留待下次同步重试（后端状态未变，安全）
            } finally {
                pendingResult.finish()
            }
        }
    }
}
