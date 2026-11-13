# R31 — 参考应用、幂等恢复与等价负载验证

日期：2026-11-12（America/Los_Angeles）。原始packet/baseline/hash与SQLite执行记录保持可追溯。当前基线Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`、Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`；当前架构与研究补充由`/root/database_research`整合，独立接受审查待记录。实际新增PG响应丢失/并发snapshot探针在[completion fixture](../../../../experiments/database-completion/README.md)，运行状态以[task-status](../../../../verification/database-completion/task-status.json)与原始manifest为准。未实现C#/Rust产品，不把研究执行等同产品AOT/长期负载验收。详细规范见[D20](../../../verification/reference-application.md)。

## 1. 选择的参考场景

通用多租户工作项服务覆盖幂等创建、typedquery分页、附件upload/download、transactionaloutbox与授权status查询。REST为必需最小入口，可选gRPC/MCP复用同一C#应用service。它同时验证阶段Ainterop/生成/包装与阶段Bdatabase/ORM/server，而不是只给阶段B几项抽象“未来任务”。ArcForges只为文档组织参考，不影响业务schema或架构。

产品基线是 **Rust Server + C# application/typed Fluent/DTO + Rust Database/ORM Engine**。Rust Server负责网络I/O、协议、连接、流与背压；C#负责业务Handler。Kestrel只保留独立功能/成本/性能对照。数据库普通路径选择维护者预编译SeaQuery+SQLx，普通C#实体使用runtime metadata和static DTO，不要求生成Rust Entity或重新Cargo编译。SeaORM动态投影是有实际执行证据的可复用能力，静态Entity/ActiveModel是另行维护的专用profile；具体边界服从D14/D16，不在R31重建ORM选型。

C#不重建SQL AST/方言/复杂LINQ Provider，SG可选生成静态元数据而不是每次捕获完整方法体。Npgsql、Microsoft.Data.Sqlite与EF Core仅为独立比较。数据库与服务器Rust底层是确定的项目目标；性能实验优化实现，不把已明确目标重新设为二选一。

非目标：当前完成整个产品；宣称数据库与外部消息/文件系统分布式exactly-once；将数据库要求扩大为所有模块必须 Rust；以单次Python实验证明Rust driver、AOT或生产durability。

## 2. 候选方案与选择

| 候选 | 结论及原因 |
| --- | --- |
| timeout后无条件重试原写 | 拒绝；COMMIT可能已生效，响应不可见不等于未执行 |
| 先提交幂等记录，再做业务写 | 不作为本版原子协议；需另建持久InProgress/租约/恢复状态机，不能假装天然原子 |
| 单事务唯一(scope,key)+requesthash+business+result+outbox | 选择；唯一键线性化同key竞争，确认结果可重放，异payload不能覆盖 |
| 在DB事务里直接发送外部事件 | 拒绝；外部效果不随DBrollback，长期IO还占连接/锁 |
| transactionaloutbox+稳定eventID+消费者去重 | 选择；诚实承认至少一次外部交付 |
| 以一次GET未找到operation证明rollback | 拒绝；原提交可能仍进行或当前读未见结果 |

事务效果状态由数据库D15/`transactions-and-pooling.md`定义，公共名称与数据库作者对齐：WeaveDataSource→DataSession→DataTransaction；CommitAsync的requesttoken只影响发送前admission；入线后独立commitdeadline；Unknown异常保留RecoveryKey/CorrelationId，Dispose不改写Unknown。TransactionOptions.Isolation默认null，采用provider声明默认；PG为ReadCommitted，SQLite普通Serializable语义，BEGIN模式由SQLite profile选择，不能将RecoveryKey-only示例强迫为PG隔离级别。

有界 HTTP 响应使用 D14/D15 的显式 `DataSession.CloseAsync(deadline)`：Session关闭新业务准入并请求/加入已有transaction/cursor清理，Pending/Quarantined时可以停止等待，但Engine保留全部parent lease、roots与预算，不能声明本地已释放或改写Unknown。后台仅既有终结/cleanup，不携带结束的HttpContext/请求DI scope或新增业务。`DisposeAsync`成功必须实际本地安全；native未静默时继续join，因此不能用await using表达有限HTTP等待。此接口细化是设计决定，本轮SQLite原型没有验证该C#/Rust关闭实现。

## 3. PostgreSQL官方语义与具体反例

已读官方v18 [INSERT](https://www.postgresql.org/docs/18/sql-insert.html)与[TransactionIsolation](https://www.postgresql.org/docs/18/transaction-iso.html)§13.2.1。原始证据是版本化官方文档。新增PG18.0研究执行单独固定源码/二进制与运行manifest，不把文档阅读本身当执行。

DO NOTHING发生冲突时可看到当前statement snapshot尚不可见的并发事务；RETURNING只返真正插入/更新的行。因此同statement的CTE INSERT DO NOTHING加SELECT不能被宣布总能拿到原record。

选择READCOMMITTED下第一条INSERT ON CONFLICT(scope,key) DO NOTHING RETURNING operation_id；0行时以**下一条**SELECT取得新snapshot，再比较hash和返回原response。retention窗口内不物理删除record；若仍无行或超时，保持未确认并按唯一键保护进行有界恢复，不以空结果断言rollback。其它隔离级别/清理策略需另验。SQLite路径采用短BEGIN IMMEDIATE下的先查再写，明确writer串行化，不将PG锁语义机械移植。

hash来自通过验证的业务DTO与语义版本，scope来自可信tenant/principal/endpoint；同key不同hash409。request_key和responsebytes有长度界；status查询同样授权。HTTP还能响应时Unknown返回503和稳定operation恢复信息；不伪称Created或已可靠queued的202。客户端即使只保留原key，也可安全重试同key/hash保护流程。

## 4. 实际研究原型与执行记录

[idempotency_experiment.py](idempotency_experiment.py)为本轮原创最小SQLite原型，仅stdlibrary，临时数据库，退出后清理。不是NativeWeave产品API。`connect`开启foreignkeys/synchronousFULL；setup使用WAL；每次command独立connection，BEGINIMMEDIATE；hash比较在写事务内；operations/items/outbox同一COMMIT。

实际执行命令：

```text
python docs/research/topics/R31/idempotency_experiment.py > docs/research/topics/R31/experiment-result.json
```

主进程exit0、stderr为空。环境Python3.12.14、SQLite3.53.1、Linux6.18.57x64/glibc2.41。为完整记录D12要求，最终结果经instrumented wrapper重新执行，实际argv、UTC起止时间和原始流hash在[run-manifest.json](run-manifest.json)，没有补造第一次运行的时间。脚本SHA256与stdoutSHA256、子进程预期exit17、版本/OS/配置在evidence.run_manifest；[原始stdout](experiment-result.json)全部保留。

| 实际断言 | 结果 |
| --- | --- |
| 相同key/hash重放 | 相同operation_id和response，三个表各1行 |
| 同key异hash | conflict，不增加业务或outbox |
| 4个独立连接并发同key | 恰1个created、3个replay；全部相同operation_id |
| 真实COMMIT后模拟丢response | 新连接重放获得原durableresult，无第二业务效果 |
| 子进程COMMIT前`os._exit(17)` | 实际跳过finally/rollback；新连接见三表无新增，随后同key正常创建 |

结束时operations/items/outbox各4行。实验检查原子结果关系，不测吞吐或延迟；elapsed时间不作为性能结论。Response loss是COMMIT后的程序分支模拟，不是网络代理真实断包；进程exit不是OS断电/磁盘控制器fsync验证。SQLitewriter锁使此反例可重现，但它没有证明PG的MVCC并发实现。产品C#/Rust、AOT、跨平台仍全部not-run。

## 5. 应用实现的具体界限

附件先用diskcredit流式写临时文件、hash/长度校验、持久化并rename不可变blob，再短DB事务提交引用/结果/outbox。失败可遗留有界/可GC的orphan，不能提交指向半写文件的DB成功结果。GC必须保护活跃upload与恢复、考虑retention；目录fsync/rename和Windows/Linux差异需要实际故障测试。不将blobhash当跨tenant读取凭证。

Outboxworker有界claimbatch，发布后标记；发布后崩溃会重复，consumeroracle按event_id持久去重。业务事务不等待客户端下载、不调用外部publisher；慢response也不能永久占有DBlease。分页采用稳定keyset(created_at,id)，默认跨页不承诺一致snapshot；一致导出有单独时限/leaseprofile。

应用开发者写普通C# typed model、Fluent query和async API，无Rust/FFI或逐实体Cargo要求。可选C# SG生成static metadata/DTO；普通Fluent调用复用native SeaQuery builder和SQLx执行。动态过滤先解析允许的列/运算符，再由Rust验证能力/参数/租户与资源边界。业务 operation hash / correlation 不成为无界 metric labels。

## 6. 故障与完整负载证据

B21实现D20完整最小服务、goldenvectors、可选协议facade和参考consumer；B22实现独立oracle与可控faultpoints：BEGIN/写/COMMIT前后/确认丢失、PGrestart、SQLitebusy/diskfull、poolreset、HTTPslow/abort、outboxpublish后crash、blobrename和DBcommit之间crash、drain/retire等。

模型/属性验证至少检查：同scope/key最多一业务效果；item/result/outbox原子一致；终态不可逆；Unknown不因Dispose或空查询变成rollback；每owner最终释放或明确隔离。fuzz针对长度/输入/queryIR/ABI，真实多线程测试控制竞争窗口而不是仅sleep。Windows/Linux真实AOT发布后运行，24h回归与72hrelease soak检查长期资源斜率、steady plateau和故障恢复；不能只报一次峰值RSS。

B23产品基线为Rust Server + C#业务Handler/typed Fluent/DTO + Rust ORM / PostgreSQL/SQLite Engine。纯 C# 的 Kestrel + Npgsql/Microsoft.Data.Sqlite（适用时 EF Core）仅为外部托管基准，纯 Rust 实现仅为生态与跨语言成本对照；不能将它们误列为 NativeWeave 的托管数据库产品 profile。TLS/HTTPprofile、schema/index/isolation/pool、dataset/cache、错误比例、durability、硬件资源、采样都相同。使用固定到达率并记录排队，保留p99/p99.9/rawhistogram、CPU/op、GC/alloc/native/RSS/handles/copies/crossings。不存在/未测组合写not-run，不从微基准推断真实收益；性能门槛基于冻结基线与产品目标，当前不编造百分比。证据用于改进 Rust DB，不能静默取消产品约束；Rust Server底层是既定目标；端到端证据用于选择和优化具体Rust组合。

B24验收独立包/RID/profile、cleanmachine运行、版本拒绝、upgrade/rollback、SBOM/LICENSE。所有 NativeWeave Server 示例均必须验收 Rust Server native library；含数据库的应用同时验收 Rust DB native library 及相关阶段 A interop/AOT gate。纯 managed 示例只能是独立外部对照，不能标记为 NativeWeave Server 产品 profile。数据库/Server核心必须可单独验收，再组合验证；不为了参考应用强制所有独立任务串行。

## 7. 结题建议与交叉Review

参考应用场景、事务幂等、Unknown恢复及等价性能方法已有明确设计；其实现/生产验证义务全部交B21–B24，不让研究一直等到全产品发布。R31当前研究/设计成果已齐备并进入独立接受审查：新增 Rust/SQLx PostgreSQL 18.0 实库反例已执行，包含 COMMIT 确认丢失和并发 snapshot。作者不能自行宣称 accepted；全产品、其他候选特性与长期验证仍是明确的 Delivery 义务，不再据此将已完成研究记为 planned/partially_evidenced。

交叉Review：数据库R21核对Commit状态和PGsnapshot、R20核对SQLite writer语义；R26/R29核对requestabort/stream预算；R28核对gRPC/MCP不同终态；R17检查工作负载等价；R34检查tenant/auth/hash/retention与错误泄露。潜在反例与影响文件均具体落到D20和相关Delivery任务，而非新增元规划层。

## 8. 新增的研究闭环与明确后续阶段

`database-completion/tests/postgres.rs`固定两个决定性反例：COMMIT应答在网络代理中丢弃而新连接看到已提交结果；并发唯一键冲突使用真实pg_locks等待同步后，同statement CTE SELECT可返回空，下一statement获得原operation。原R31 SQLite实验的模拟response loss、真实进程退出与四连接竞争原始结果保留，不重复计数。此轮其他PG/SQLite新研究还覆盖协议恢复、类型损失、shape遗漏与迁移锁，全部通过指定manifest追溯实际执行范围。

D20/B21以同一业务操作定义连接两原生Engine，所有权仍按各Engine本地runtime与CoreABI组合，不造全局巨型调度器。B22/B23保留产品故障注入、真实C# AOT、长期负载、性能和磁盘持久性义务；这些义务不阻止研究层接受幂等/outbox/Unknown/接口设计，也不授权当前开始正式产品开发。

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
