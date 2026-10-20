package com.dogstar776.proactive.ui

/** 对话状态机（用户定义的交互形式）。 */
enum class CosmosState(val label: String) {
    IDLE("待命"),
    LISTENING("我在听"),        // 默认态：一直听着
    WAITING("你说，我等着"),     // 用户说"等我一下"进入：光晕收缩，听完才动
    THINKING("让我想想"),        // 用户说完了，后台思考
    SPEAKING("我说"),           // 它开口
}

/**
 * 从用户话语里识别"等待/继续"意图。
 *
 * 用户原话："我跟它说多等我一会，我自己说完它再回我"——这是本地规则，
 * 不依赖 LLM（等待判断必须即时可靠，不能让网络延迟破坏信任）。
 * LLM 接入后这些规则仍然优先（本地裁决，远程生成）。
 */
object WaitGesture {

    private val WAIT_PATTERNS = listOf(
        "等我一下", "等我一会", "等一下", "先等等", "别急", "先别说",
        "听我说完", "我还没说完", "等我说完", "先听我说", "多等我一会",
        "等会", "暂停", "稍等",
    )

    private val RESUME_PATTERNS = listOf(
        "说完了", "我说完了", "好了", "继续", "可以了", "讲完了",
        "没了", "完事", "结束", "嗯好了", "行",
    )

    enum class Intent { WAIT, RESUME, NONE }

    fun detect(text: String): Intent {
        val t = text.replace("，", "").replace(",", "").replace(" ", "")
        if (t.isEmpty()) return Intent.NONE
        // 指令类优先：先判"继续/说完了"（解除等待），再判"等待"
        if (RESUME_PATTERNS.any { t.endsWith(it) || t == it }) return Intent.RESUME
        if (WAIT_PATTERNS.any { t.contains(it) }) return Intent.WAIT
        return Intent.NONE
    }
}
