# R31 — 参考应用、幂等恢复与等价负载验证

日期：2026-11-12。输入packet0.1.1及baseline/hash见[evidence.json](evidence.json)。研究状态partially_evidenced：完成幂等与Unknown恢复设计及实际SQLite研究原型，未实施C#/Rust产品、PostgreSQL网络故障、真实AOT/跨平台/性能验收。完整应用规范已同步[D20](../../../verification/reference-application.md)。

## 1. 选择的参考场景

通用多租户工作项服务覆盖幂等创建、typedquery分页、附件upload/download、transactionaloutbox与授权status查询。REST为必需最小入口，可选gRPC/MCP复用同一C#应用service。它同时验证阶段Ainterop/生成/包装与阶段Bdatabase/ORM/server，而不是只给阶段B几项抽象“未来任务”。ArcForges只为文档组织参考，不影响业务schema或架构。

产品基线是 Kestrel + C# application/语法/DTO 边界 + 必需 Rust ORM / PostgreSQL/SQLite Database Engine；C# 提供 LINQ/泛型/async/Native AOT 上层体验，应用开发者不写 Rust。C# Source Generator 只捕获语法、诊断并编码版本化 IR，Rust 负责查询语义、SQL 生成、ORM、驱动、池和事务执行；具体 ORM 由数据库 D14/D16 唯一选型，R31 不另行覆盖。依据用户明确约束，旧草稿中的可选 Rust DB / 默认托管 provider 路线已被替代。Npgsql、Microsoft.Data.Sqlite 与 EF Core 仅保留为源码研究和独立等价基准，不进入产品默认数据库执行路径。可选 Rust Server 不改变数据库底层 Rust 要求。

同步数据库当前选择：采用 SeaORM 路线，以 schema-specific model Engine 将生成的 `Entity` / `ActiveModel` / static dispatcher 与 common Rust DB code 静态链接为一个 native module；不跨 DLL 传递 Rust pool/transaction/trait object。新 schema 的构建需要 Rust toolchain（可放 CI），而应用作者无需编写 Rust，运行已发布应用不需 Rust toolchain。此处为对 D14/D16/D10 的设计引用；本 R31 原型没有执行 SeaORM/SQLx/Rust，也不另行宣称其 AOT 验证通过。

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

## 3. PostgreSQL官方语义与具体反例

已读官方v18 [INSERT](https://www.postgresql.org/docs/18/sql-insert.html)与[TransactionIsolation](https://www.postgresql.org/docs/18/transaction-iso.html)§13.2.1。证据是版本化官方文档而非固定serverexecutable；本轮未运行PG。

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

应用普通开发者写 C# typed model / 受支持 LINQ 风格 query / async API，无 Rust/FFI 需求。C# SG 捕获语法/诊断并生成 IR 编码与静态 DTO 元数据，Rust ORM 校验语义并生成参数化 SQL、执行关系/工作单元和数据库操作；C# 静态 DTO 解码不成为第二套 ORM。动态过滤限定列与运算符，Rust 验证 IR 能力和参数边界。业务 operation hash / correlation 不成为无界 metric labels。

## 6. 故障与完整负载证据

B21实现D20完整最小服务、goldenvectors、可选协议facade和参考consumer；B22实现独立oracle与可控faultpoints：BEGIN/写/COMMIT前后/确认丢失、PGrestart、SQLitebusy/diskfull、poolreset、HTTPslow/abort、outboxpublish后crash、blobrename和DBcommit之间crash、drain/retire等。

模型/属性验证至少检查：同scope/key最多一业务效果；item/result/outbox原子一致；终态不可逆；Unknown不因Dispose或空查询变成rollback；每owner最终释放或明确隔离。fuzz针对长度/输入/queryIR/ABI，真实多线程测试控制竞争窗口而不是仅sleep。Windows/Linux真实AOT发布后运行，24h回归与72hrelease soak检查长期资源斜率、steady plateau和故障恢复；不能只报一次峰值RSS。

B23 产品基线比较 Kestrel + C# 语法/DTO 上层 + Rust ORM / PostgreSQL/SQLite Engine，并覆盖已选择的 Rust Server + 同业务 handler + 同一 Rust ORM / DB Engine。纯 C# 的 Kestrel + Npgsql/Microsoft.Data.Sqlite（适用时 EF Core）仅为外部托管基准，纯 Rust 实现仅为生态与跨语言成本对照；不能将它们误列为 NativeWeave 的托管数据库产品 profile。TLS/HTTPprofile、schema/index/isolation/pool、dataset/cache、错误比例、durability、硬件资源、采样都相同。使用固定到达率并记录排队，保留p99/p99.9/rawhistogram、CPU/op、GC/alloc/native/RSS/handles/copies/crossings。不存在/未测组合写not-run，不从微基准推断真实收益；性能门槛基于冻结基线与产品目标，当前不编造百分比。证据用于改进 Rust DB，不能静默取消产品约束；Rust Server 是否推荐仍由端到端收益决定。

B24验收独立包/RID/profile、cleanmachine运行、版本拒绝、upgrade/rollback、SBOM/LICENSE。所有包含数据库的应用都必须验收 Rust DB native library 及相关阶段 A interop/AOT gate；纯 managed 无 native 加载只适用于独立无数据库的 Server 示例。数据库/Server核心必须可单独验收，再组合验证；不为了参考应用强制所有独立任务串行。

## 7. 结题建议与交叉Review

参考应用场景、事务幂等、Unknown恢复及等价性能方法已有明确设计；其实现/生产验证义务全部交B21–B24，不让研究一直等到全产品发布。R31仍partially_evidenced，因为PG真实并发与完整源码/平台候选覆盖未完，不能把作者草案称为accepted。

交叉Review：数据库R21核对Commit状态和PGsnapshot、R20核对SQLite writer语义；R26/R29核对requestabort/stream预算；R28核对gRPC/MCP不同终态；R17检查工作负载等价；R34检查tenant/auth/hash/retention与错误泄露。潜在反例与影响文件均具体落到D20和相关Delivery任务，而非新增元规划层。
