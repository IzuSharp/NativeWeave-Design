# R20 — Rust SQLite worker、取消与资源

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `8064d704f2e3b2e07e4d1fbf1922a97b01ce2a93ce4f4f4ff4bc151b6d8b853f`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 当前决定：SeaORM + SQLx SQLite

选定Rust SQLite driver，与PG共享SeaORM ORM和版本化请求，不发布Microsoft.Data.Sqlite产品adapter。原managed SQLite方案superseded；先前同步API/Cancel空实现研究保留为对照，不冒充Rust运行证据。普通应用用Task/async，实际SQLite VM仍同步。

## 2. 实际源码链

SeaORM SQLite executor→SQLx SqliteExecutor→ConnectionWorker command→ExecuteIter→sqlite3_step→bounded row channel→QueryResult/SeaORM projection。SeaORM公共SqliteRow/QueryResult转换以及ConnectionTrait让SessionExecutor复用既有机制。默认SeaORMquery_all收集全部rows，因此NW必须实现带总行数/bytes的collect和stream。

SQLx0.9 SQLite证据由真实独立子代理interop_design读取，固定commit/blob/ranges随本报告evidence保存；本作者不冒称已独立复读其所有内容。每连接一个专用OSthread和bounded command channel；row channel也bounded，但item-count上限不是byte/RSS上限。连接池上限约束线程数，参数/row/等待工作另按bytes计费，不能叠加无限worker层。

## 3. 取消及释放陷阱

丢future/receiver令迭代在rowsend失败处停止，不会强制打断已经进入的sqlite3_step。选定执行前通过lock_handle安装native-only progress handler，捕获该operation独立atomic取消flag；request_cancel只store，不在取消路径等待DB锁。handler不分配、不回调managed、不修改connection。结束/清理后移除或安全换代才允许下一操作，registration也要drain，迟到取消不得杀下一语句。

progress机制是协作中断，不保证busy/file I/O/extension所有路径硬时限。ExecuteIter Drop只reset().ok()，不能据此证明清洁。worker start_rollback/shutdown有同步bounded-channel send，会阻塞；禁止进SafeHandle ReleaseHandle、request_stop或try_retire。close_hard/drop/flush也不是worker退出证明。源码Shutdown ack在连接引用drop后、threadclosure返回前，不能把ack冒充OS JoinHandle证据；模块v1常驻，清理需保留状态/预算到NW-local访问义务结束。

## 4. 事务与故障

BEGIN成功但ack丢失会在worker立即rollback，失败可退出worker；COMMIT/ROLLBACK成功但ack丢失有ignore_next_start_rollback防重复Drop补偿。它们不等于C#收到成功，依然需要D15的CommitUnknown与RollbackUnconfirmed分类。SQLite单条statement错误不自动证明整个事务已回滚。

固定WAL/foreign_keys/busy_timeout/synchronous/journal与线程构建选项；Isolaton=null采用profile普通Serializable语义，DEFERRED/IMMEDIATE明确，不模仿PG ReadCommitted。系统或bundledSQLite实际版本/compileoptions需要发布记录，不能从crate版本推导。

## 5. 参考证据和未完成义务

MS.Data.Sqlite ExecuteReaderAsync→同步ExecuteReader、Cancel空实现及同步reader/transaction路径只说明该候选，不套到SQLx。官方sqlite3_interrupt资料说明连接必须存活、近结束可能无效、没有活动statement时无作用，支持代际/ownership要求，不能当已实现interrupt证据。

上游progress handler tests740–809只读未运行。R24 Python/SQLite50checks只验证有限SQL语义，R31另一实验也不证明SeaORM/SQLx。B03必须实跑RustSQLite/C#AOT、handler late cancel/replacement、busy/locked、worker shutdown压力、丢ack、重开连接与文件故障；B04/B05共享预算/cleanup invariants。尚未读SQLite VM、所有statement reset/finalize、全部rowclone/driver tests，研究状态继续partially_evidenced。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R20-C01 | [src/Microsoft.Data.Sqlite.Core/SqliteCommand.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteCommand.cs#L357-L439) | [[357, 439], [458, 543]]; source-observed; reader=database_design |
| R20-C02 | [src/Microsoft.Data.Sqlite.Core/SqliteDataReader.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteDataReader.cs#L118-L144) | [[118, 144], [154, 180], [182, 208], [243, 301]]; source-observed; reader=database_design |
| R20-C03 | [src/Microsoft.Data.Sqlite.Core/SqliteTransaction.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteTransaction.cs#L70-L243) | [[70, 243]]; source-observed; reader=database_design |
| R20-C04 | [test/Microsoft.Data.Sqlite.Tests/SqliteTransactionTest.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/test/Microsoft.Data.Sqlite.Tests/SqliteTransactionTest.cs#L14-L32) | [[14, 32], [310, 328], [359, 377], [379, 397]]; test-source-observed; reader=database_design |
| R20-C05 | [LICENSE.txt](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/LICENSE.txt#L1-L23) | [[1, 23]]; license-text-observed; reader=database_design |
| R20-C06 | https://www.sqlite.org/c3ref/interrupt.html | 定位见evidence; official-documentation-observed; reader=database_design |
| R20-V1 | [refs/tags/v11.0.0](https://api.github.com/repos/dotnet/efcore/git/refs/tags/v11.0.0) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R20-V2 | [refs/tags/v3.0.5](https://api.github.com/repos/ericsink/SQLitePCL.raw/git/refs/tags/v3.0.5) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R20-RU01 | [src/driver/sqlx_sqlite.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_sqlite.rs#L155-L254) | [[155, 254], [311, 337]]; source-observed; reader=/root/database_design |
| R20-SQ09-SQLITE-01 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 25-138;163-212;364-389; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-02 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 213-313;538-574; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-03 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 390-412;490-505;335-344; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-04 | [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs) | 214-287; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-05 | [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs) | 128-137;291-305;386-422;524-527;550-560; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-06 | [sqlx-sqlite/src/connection/execute.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/execute.rs) | 1-133; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-07 | [sqlx-sqlite/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/transaction.rs) | complete; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-08 | [tests/sqlite/sqlite.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/tests/sqlite/sqlite.rs) | 740-809; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-09 | [sqlx-sqlite/src/connection/executor.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/executor.rs) | 1-102; cross-task-source-evidence; reader=/root/interop_design |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
