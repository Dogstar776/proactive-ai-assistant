# ADR-0006：P2 观测层的四项工程决策

- 状态：已接受（2026-10-17，P2 实施）
- 背景：P2 要把论文 3.1 观测层落成可运行代码，期间出现四个需要记录的决策点。

## 决策一：event_id 用确定性 uuid5（source|ref|内容哈希）

**理由**：重复采集必须幂等——种子数据可反复回放、连接器重跑不产生重复事件、SSE 重连不重放历史。确定性 ID + `INSERT OR IGNORE` 免费获得幂等性，无需额外的去重层。
**后果**：事件内容相同则 ID 相同；若用户编辑了笔记标题，视为新事件（旧条目仍在库中，由 P3 一致性审计处理）。

## 决策二：ThreadLocalConnection 线程局部连接

**理由**：FastAPI 同步端点在 anyio 线程池执行、SSE 生成器在事件循环线程执行，单一共享 SQLite 连接触发 "objects created in a thread can only be used in that same thread"。每个工作线程一个连接，WAL 模式下读写不互阻；停机时 close_all。
**被否决**：`check_same_thread=False` 单连接共享——多线程并发写同一连接会交错事务，本地单人场景可忍但属于把问题藏起来。

## 决策三：未配置采集源时自动挂载 fixtures 演示连接器

**理由**：开源项目"clone → 启动 → 可见数据"的复现承诺；演示连接器 collector_id 带 `fixture:` 前缀，与用户真实数据在 API 与仪表盘均可区分，日志有明确告警。
**后果**：任何人零配置可跑通全链路；配置 `COLLECTOR_*` 后即切回真实数据。

## 决策四：抽取器默认 rules，mock_llm 显式可选

**理由**：延续 ADR-0005 的成本结构——高频轻观测不调 LLM；MockLlmExtractor 输出带 `[MOCK-xxx]` 前缀与 `mock:true` 元数据，绝不伪装真实推理（与 ADR-0003 诚实定位一致）。
**后果**：规则的重要度启发式是显式可审查的；OQ7 模板移除测试有了明确的测量对象。

## 实施中记录的一个坑

icalendar 的 `DTSTART/DUE` 返回 `vDDDTypes` 包装对象而非原生 datetime，直接 isinstance 判断会静默得到 None——解包 `getattr(value, "dt", value)` 后解决，并有测试断言 `event_time` 非空防回归。
