package com.dogstar776.proactive.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.dogstar776.proactive.ProactiveApplication
import com.dogstar776.proactive.data.SyncLogic
import java.util.concurrent.TimeUnit

/**
 * 后台同步 Worker：每 15 分钟拉取一次后端状态，
 * 把门控放行（delivered/approved）的提醒转成本地通知，pending 的带批准/拒绝动作。
 *
 * 设计说明：移动端不用 SSE 长连（省电与保活权衡），用轮询——
 * 这正是论文 1.2.5 指出的"主动服务需要可校准干预"的工程折中，
 * 频率与免打扰由后端 charter 的 intervention_budget 控制，双端共治。
 */
class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? ProactiveApplication ?: return Result.success()
        return try {
            val reminders = app.api().reminders(limit = 100).items
            val already = app.settings.notifiedIds()
            val toNotify = SyncLogic.pickToNotify(reminders, already)
            val pending = SyncLogic.pickPending(reminders)

            Notifier.ensureChannels(applicationContext)
            toNotify.forEach { r ->
                Notifier.notifyDelivered(applicationContext, r.reminder_id, r.title, r.body)
            }
            pending.forEach { r ->
                Notifier.notifyPending(applicationContext, r.reminder_id, r.title, r.body)
            }
            if (toNotify.isNotEmpty()) {
                app.settings.markNotified(already + toNotify.map { it.reminder_id }.toSet())
            }
            app.settings.setLastSync(SyncLogic.nowIso())
            Result.success()
        } catch (_: Exception) {
            Result.retry()  // 网络失败：WorkManager 自动退避重试
        }
    }

    companion object {
        private const val PERIODIC_NAME = "proactive-periodic-sync"
        private const val ONESHOT_NAME = "proactive-oneshot-sync"

        fun ensurePeriodic(context: Context) {
            val req = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(
                    androidx.work.Constraints.Builder()
                        .setRequiredNetworkType(androidx.work.NetworkType.CONNECTED)
                        .build()
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC_NAME, ExistingPeriodicWorkPolicy.KEEP, req,
            )
        }

        fun syncNow(context: Context) {
            val req = OneTimeWorkRequestBuilder<SyncWorker>().build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                ONESHOT_NAME, ExistingWorkPolicy.REPLACE, req,
            )
        }
    }
}
