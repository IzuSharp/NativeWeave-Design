# R21 — Rust事务、返池与Unknown恢复

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `1f7c1b4bb1baaf188e3da40b1286e20d334fac10d941f04f103f00b80ecf7ab4`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 已收敛的设计问题

Q12以D15明确解决设计层：事务effect、操作结果、可返池状态、本地资源四维分离；CommitAsync token只控制commit admission，之后根据真实终态/Unknown；默认不自动重试写入。未完成实库fault/AOT压力是独立Verification义务，不使该技术决定永远open。

Rust路径选SeaORM+SQLx；原Npgsql默认清理策略superseded，仅保留其受控reset机制作为比较。Rust SessionExecutor持有PoolConnection，事务协调器保存CommitAttempted/Outcome/Cleanup快照，C#只是外观与immutable结果。

## 2. API→实现→错误→释放链

SeaORM公开Connection/Transaction traits允许自有适配器，但默认DatabaseTransaction commit/rollback消费self，仅成功置open=false，Drop会try_lock并expect start_rollback。已有stream持锁时不能无条件Drop；跨FFI清理更不能依靠这个Drop。选自有RustSessionExecutor/B05coordinator，先drain reader再事务终结，SQLxTransactionManager只在实现Connection的driver适配层使用。

SQLx PG manager发送commit/rollback并维护depth；PoolConnection.close保留permit，Drop回收含after_release/ping与失败关闭。SQLite worker有commit/rollback lost-ack特殊状态以及可能阻塞的start_rollback/shutdown。读取这些路径不证明NW已满足quiescence，B04/B05必须真正实现并运行fixture。

## 3. 成功、失败和Unknown

CommitInFlight是本地保守“可能已发送”边界；真实提交确认才Committed，明确回滚才RolledBack，无可信终态且可能发送则Unknown，不能被OperationCanceledException或Dispose覆盖。已知事务Failed时拒绝commit，不把无异常COMMIT返回自动等同成功业务写入。

独立review DB-CR01要求补齐rollback失败oracle，已落D15：从未commit而rollback未确认→TxLifecycle Closed/Outcome InProgress/CommitAttempted=false/Cleanup RollbackUnconfirmed；不再可用，不声称服务器rollback完成。曾可能commit则Unknown保持。local调用仍运行→Closing/Pending，保留roots/budget；安全丢弃连接后可完成local cleanup，但effect不能伪改。

DisposeAsync成功必须local safe，普通cleanup错误锁存Cleanup不覆盖主业务/CommitUnknown异常；deadline未静默时继续join。需有限等待用CloseAsync(deadline)返回Pending/Quarantined快照，不能用成功void Task暗示释放。同步Dispose只移交cleanupowner，runtime关闭必须后于所有待清理工作；native模块按D02常驻。

## 4. 返池与幂等

ProviderResetPending只容纳被provider顺序化、下一用户命令前会执行的maintenance，未知协议损坏必须剔除。SQLxclose_on_drop是意图不是完成；detach会允许池补开连接，不能用它绕过总在用预算。Unknown恢复与本地handle分离，不能永远持有native内存等待业务恢复。

幂等记录(scope,key)+request_hash+operation_id+business writes+result+outbox同事务；PG ReadCommitted的ON CONFLICT DO NOTHING返回0行后必须下一statement SELECT，单CTE可能读不到冲突行。一条“未找到”不证明旧事务不能提交；retention/tombstone窗口、主库一致性和同key重试约束明确，外部副作用经outbox不承诺跨系统exactly-once。官方PG18INSERT/隔离页面已实际读取，详见evidence。

## 5. 对Codex的具体交接

B05实施state/CAS、commit admission、固定lease、savepoint stack/generation、Unknown异常/恢复标识、RollbackUnconfirmed/Cleanup快照；v1nested begin与已有外层transaction的ChangeSet SaveChanges明确拒绝。B02/03真实断连/超时/清理，B22切断COMMIT响应方向并观察服务器/客户端记录；多key/同key并发、失败事务commit、latecancel、streamlock、shutdown依赖。Python模型和上游测试阅读不能替代Windows/Linux实库NativeAOT。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R21-C01 | [src/Npgsql/NpgsqlTransaction.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlTransaction.cs#L120-L230) | [[120, 230], [290, 390]]; source-observed; reader=database_design |
| R21-C02 | [src/Npgsql/Internal/NpgsqlConnector.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/NpgsqlConnector.cs#L2075-L2258) | [[2075, 2258], [2706, 2810], [2936, 2993]]; source-observed; reader=database_design |
| R21-C03 | [src/Npgsql/NpgsqlDataReader.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataReader.cs#L238-L259) | [[238, 259], [357, 378], [500, 521], [593, 614], [952, 973], [1033, 1054], [1077, 1227]]; source-observed; reader=database_design |
| R21-C04 | [src/Npgsql/PoolingDataSource.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/PoolingDataSource.cs#L100-L356) | [[100, 356], [445, 455]]; source-observed; reader=database_design |
| R21-C05 | [src/Npgsql/NpgsqlDataSource.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataSource.cs#L242-L257) | [[242, 257]]; source-observed; reader=database_design |
| R21-C06 | [test/Npgsql.Tests/TransactionTests.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.Tests/TransactionTests.cs#L36-L58) | [[36, 58], [65, 87], [94, 116], [123, 145]]; test-source-observed; reader=database_design |
| R21-C07 | [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/pool/connection.rs#L130-L163) | [[130, 163], [195, 225], [271, 369]]; source-observed; reader=database_design |
| R21-C08 | [sqlx-postgres/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-postgres/src/connection/mod.rs#L81-L108) | [[81, 108], [180, 207], [211, 258]]; source-observed; reader=database_design |
| R21-C09 | https://www.postgresql.org/docs/18/transaction-iso.html | 定位见evidence; official-documentation-observed; reader=database_design |
| R21-C10 | https://www.postgresql.org/docs/18/sql-insert.html | 定位见evidence; official-documentation-observed; reader=database_design |
| R21-C11 | [LICENSE-MIT](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/LICENSE-MIT) | 定位见evidence; license-text-observed; reader=database_design |
| R21-RU01 | [src/database/transaction.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/transaction.rs#L1-L112) | [[1, 112], [238, 410]]; source-observed; reader=/root/database_design |
| R21-RU02 | [src/database/connection.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/connection.rs#L1-L88) | [[1, 88], [167, 251]]; source-observed; reader=/root/database_design |
| R21-RU03 | [sqlx-core/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-core/src/transaction.rs#L1-L150) | [[1, 150], [260, 292]]; source-observed; reader=/root/database_design |
| R21-RU04 | [sqlx-postgres/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/transaction.rs#L1-L102) | [[1, 102]]; source-observed; reader=/root/database_design |
| R21-RU05 | [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-core/src/pool/connection.rs#L50-L125) | [[50, 125], [195, 225], [280, 355]]; source-observed; reader=/root/database_design |
| R21-SQ09-SQLITE-02 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 213-313;538-574; cross-task-source-evidence; reader=/root/interop_design |
| R21-SQ09-SQLITE-03 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 390-412;490-505;335-344; cross-task-source-evidence; reader=/root/interop_design |
| R21-SQ09-SQLITE-04 | [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs) | 214-287; cross-task-source-evidence; reader=/root/interop_design |
| R21-SQ09-SQLITE-07 | [sqlx-sqlite/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/transaction.rs) | complete; cross-task-source-evidence; reader=/root/interop_design |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
