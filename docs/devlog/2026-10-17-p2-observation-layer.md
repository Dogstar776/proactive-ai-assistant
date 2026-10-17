# 开发日志 · 2026-10-17 · P2 观测层

## 今日完成（P2：论文 3.1 环境持续观测层的工程实现）

### 交付物（assistant/，约 30 个文件）

```
assistant/
├── assistant/                    # 主包
│   ├── config.py                 # 集中配置（env 校验、快速失败）
│   ├── errors.py                 # 类型化错误体系
│   ├── logging_setup.py          # 结构化 JSON 日志 + request_id
│   ├── db.py                     # SQLite WAL / 迁移 runner / 线程局部连接
│   ├── models.py                 # ObservedEvent（provenance + chain_depth）
│   ├── migrations/001_init.sql   # 事件/记忆/授权/审计四表（可回滚）
│   ├── collectors/               # ics / markdown_notes / rss + runner
│   ├── extraction/               # rules（默认）/ mock_llm（显式可选）
│   ├── memory/                   # repository（幂等 upsert）+ vector（chroma 可选降级）
│   ├── events/bus.py             # 进程内事件总线
│   ├── services/                 # observation_service（编排层）
│   └── api/                      # FastAPI：health/events/stream/audit/collectors
├── fixtures/                     # 种子数据（ics + 2 笔记 + rss）
├── scripts/seed.py               # 种子生成 + 幂等回放
└── tests/                        # 20 个测试
```

### 验证结果（全部实测通过）

| 验证项 | 结果 |
|---|---|
| ruff lint | All checks passed |
| pytest | 20 passed |
| 种子回放幂等 | 第一次 inserted 5+8+3=16；第二次 inserted 全 0，总数不变 |
| `/health` `/ready` | ok / ready（schema_version=1） |
| `POST /api/v1/collectors/run` | 3 个连接器 ok，16 事件入库 |
| SSE 实时推送 | 空库连接 → stats 帧；触发采集 → 16 个 observed 帧实时到达 |
| 事件时间解包 | ICS DTSTART/DUE → ISO8601（修了 vDDDTypes 包装对象的坑） |
| 重要度规则 | 7 天内事件 +0.4；过期事项 +0.3；紧急词命中 +0.25/个 |
| 错误结构 | 404 → `{code, message, request_id}`，无堆栈 |
| 授权硬约束 | revoke 后连接器 skipped_revoked，不再采集 |

### 当日修复的问题

1. fixtures 路径多退一级（测试 6 连挂）；
2. 审计 detail 未解析 JSON；
3. 测试缺授权账目触发外键约束；
4. **SQLite 跨线程崩溃**（FastAPI 线程池 + SSE 事件循环）→ ThreadLocalConnection（ADR-0006）；
5. 直接 uvicorn 启动无连接器 → fixtures 自动挂载（ADR-0006）；
6. `contextlib.suppress` 导入笔误导致停机 NameError。

### 下一步

P3 自省层 + 目标层：周期自省任务（缺口检测/一致性审计）、模板化目标合成（`template-based` 标注）、charter 锚定加载。开工前发设计确认。
