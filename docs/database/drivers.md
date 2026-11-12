# Rust Database Engine、驱动与数据边界

- Task：D14；契约：**C-DB-001@0.1.0**；作者：database_design；2026-11-12。
- 状态：**review-ready**；正式接受以 contract registry 为准。本文是设计决定，产品实现、C#/Rust 编译、Native AOT 和生产验收均未完成。
- 输入 packet：revision0.1.1，SHA-256 `4e88a711f4ebac25ffd83b41f7a9f283b515ef4d047bc28a432ca3ae0377e84c`；基线 Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`、Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。后续 packet 导航修订不伪造本次输入。
- 输入：[R19](../research/topics/R19/report.md)、[R20](../research/topics/R20/report.md)、[R21](../research/topics/R21/report.md)、[R22](../research/topics/R22/report.md)、[R25](../research/topics/R25/report.md)。事务见 [D15](transactions-and-pooling.md)，Rust ORM 语义见 [D16](query-semantics.md)，C# / Rust 构建生成见 [D17](../generators/query-generation.md)。

## 1. 已决定的架构与需求修正

**DB-D004：Database 是必须使用 Rust 的独立 Native Engine；选定 SeaORM 2.0.4 为 ORM，SQLx 0.9 为 PostgreSQL / SQLite 驱动、池与底层事务机制，SeaQuery 1.0 系列为 SeaORM 内部查询构建器。** C# 是最上层：自然查询声明、泛型 API、参数快照、ABI 调用和边界 DTO。实体/关系模型、查询含义校验、SQL 方言、事务协调、池、数据库行映射与执行归 Rust。SQLx 和 SeaQuery 各自不是本规范选定的 ORM。

**DB-D005：使用 schema 专属、自动生成的 Rust 模型包和静态 dispatcher。** C# 声明经 SDK 工具导出逻辑 schema 与查询请求；Rust 构建工具生成 SeaORM `Entity/Model/ActiveModel/Column/Relation`、闭合 projection 和已登记 query handler，再编译应用所需数据库引擎。普通开发者不写 Rust。新增实体、关系或未登记静态查询需要重新生成并编译 native 制品；CI 可预先构建按 schema/query hash 标识的包。不承诺一个预编译二进制能接受任意未来 schema 而仍获得 SeaORM 静态实体能力。

**DB-D006：Rust 适配层实现 SeaORM 公开的 `ConnectionTrait` / `StreamTrait` 及所需 `TransactionTrait`，并拥有 SQLx 物理连接 lease。** 它保留 NativeWeave 的会话独占、故障连接丢弃、预算和可观察 cleanup；不自行重写 PostgreSQL 协议、SQLite VM、物理池或整个 ORM。驱动的实际 transaction manager 仍来自 SQLx；SeaORM 的实体查询、ActiveModel 更新和 RelationDef 真实参与执行。

历史决定 DB-D001 的 Npgsql / Microsoft.Data.Sqlite 默认产品依赖，以及 DB-D003 的 C# SQL/ORM 核心，因用户明确要求 Rust 数据库和 Rust ORM 而 **superseded**。既有源码比较和 SQLite 参考实验保留，不能解释为新路线已运行。Npgsql、EF Core、Microsoft.Data.Sqlite、DapperAOT只进入研究和基准工具；不进入默认发布依赖。

Core 仍无数据库或全局 Tokio 依赖。不使用 Database 的应用不加载本 Engine；使用 Database 必须携带相应 Rust native 制品。PG / SQLite 以 feature 与独立包选择，不要求未来 GPU、音视频等 Engine 依赖本 ORM。ArcForges 不参与产品依赖或内容继承。

## 2. 真实源码与选型依据

| 机制 | 固定源码与实际已读范围 | 决定及限制 |
| --- | --- | --- |
| SeaORM 静态实体与 ActiveModel | `SeaQL/sea-orm` 2.0.4，`db40a19a7bde7be8e1c4b346b1b70d72e87f0245`；`base_entity.rs` 65–135、`active_model.rs` 1–100/225–235/347–402 | 支持真实 ORM 实体与部分更新；`save` 按主键是否 NotSet 选 insert/update，不是数据库 exists-upsert |
| Rust 关系与动态条件 | 同 commit `relation.rs` 1–145/311–317，`query/helper.rs` 625–810 | 构建时关系类型与运行时受限 Condition 可以共存；不能把未知 C# 实体自动变成 Rust 泛型 |
| 正式生成入口 | `sea-orm-codegen/.../writer/compact.rs` 全文、生成 fixture `tests/compact/fruit.rs` 全文 | Entity/Relation 生成可参考；NativeWeave 导入自身 schema，不要求生产构建联网探测数据库 |
| 连接与流扩展 | `database/connection.rs` 1–88/167–251；PG/SQLite driver acquire、row/result From 与 SqlxValues 路径 | 自有 SessionExecutor 可通过公开 traits 使用 SeaORM；不能直接把按查询 acquire 的 DatabaseConnection 当成固定物理连接 |
| 事务与 Drop | SeaORM `database/transaction.rs` 238–405；SQLx0.9 `transaction.rs` 与 PG transaction manager | commit consumes self；SeaORM Drop 的 rollback/try_lock/expect 不等于跨 ABI 静默。NW 显式协调并保留故障 lease |
| SQLx 清理 | `transact-rs/sqlx` v0.9.0，`75bc0487eb661da811bb7a3c5d158f1bd463fef4`；pool/connection、SQLite worker/handle | Drop 会异步返池；SQLite 有专用线程和有界队列，但 channel 数量不等于字节预算 |
| Diesel 对照 | 2.3.14，`4007d771b1e808839f771a693f6bae9f821f0e64`；root 实读 dynamic-schema 与 boxed select | 动态 schema 确实存在，不能误称不支持；本方案仍选择 SeaORM 的 async Entity/ActiveModel + runtime Condition 组合。未做性能胜负声明 |

SeaORM Cargo.toml 1–195 声明 Rust edition2024、MSRV1.94、SeaQuery `~1.0.0`、SQLx0.9、sea-query-sqlx0.9；开启必要宏、stream、PG/SQLite与所需 codec，关闭无关可选功能。`entity-registry` 的 inventory 并非必需；NativeWeave 使用生成的显式匹配表。ActiveModelEx 源码明确 minor 版本可能变形，因此 v1核心依赖普通 ActiveModel/Relation，不以 evolving graph-save API 作为公共 ABI。

本次研究 pin 不替代实际 `Cargo.lock`。SQLx0.9发布说明指出 crate 来自合并前分支；源码 tag 与 crate checksum、Cargo.lock、features、SQLite linkmode/版本/compile options、TLS 后端都必须由 B02/B03/B04/A13 记录和验证。SeaORM MIT 文本已读，Cargo 声明 MIT OR Apache-2.0；发布收集实际依赖 notices/SBOM，不把已读一个 license 当成完整依赖审计。

## 3. 模块、运行与公共 API

| Task / 产品范围 | 职责与权威 | 编译边界 |
| --- | --- | --- |
| B01 `Data.Abstractions` / DB wire schema | C# DataSource/Session/Transaction 外观、能力、限制、失败类型；共享请求/结果描述 | 可用 fake transport 单独编译；最终 Database 运行依赖 Rust |
| B04 `native/database/host` | opaque handles、准入、SessionExecutor、Engine-local runtime、driver traits、关闭协调 | 依赖已接受 ABI/lifetime/async/buffer/error；不等全部阶段 A |
| B02 `native/database/postgres` | Rust SQLx PG driver、SeaORM public-trait adapter、TLS/profile | 不发布 managed provider |
| B03 `native/database/sqlite` | Rust SQLx SQLite adapter、worker/锁/取消/native SQLite 资产 | 同一 ORM，异步包装下 VM 仍同步 |
| B05/B06/B07 | Rust 事务/恢复协调、batch/stream、双侧 wire codec | 分工独占文件；B04 定义可注入 trait，不循环引用实现 crate |
| B08 | Rust 迁移执行与 ledger、C# 管理命令外观 | 显式部署操作；不用每次连库自动改 schema |
| B09–B14 | Rust ORM 请求/语义/生成/实体/关系；C# syntax/DTO | D16/D17 定义，C# 无 SQL 方言或 ORM identity map |

以下是 **design-draft、未编译** 的公共形状；`DataSources.Postgres` 加载应用生成的 SeaORM Engine 包，不创建 Npgsql 连接：

```csharp
await using WeaveDataSource source = DataSources.Postgres(options);
await using DataSession session = await source.OpenSessionAsync(ct);
IReadOnlyList<WorkItemRow> rows = await WorkQueries.FindOpenAsync(
    session, new FindOpenArgs(tenantId, minimumPriority, 100), ct);
await foreach (WorkItemRow row in WorkQueries.StreamOpen(session, args, ct))
{
    Consume(row); // C# DTO 自身拥有所需值。
    if (Enough()) break; // generated finally 关闭 native cursor 并排空。
}
```

`OpenSessionAsync` 返回 `Task<DataSession>`；Session 实现 `IAsyncDisposable`，拥有一个 native session handle 及父 DataSource lease。DataSource native owner 持有 Engine/runtime/pool；Session 持有一个 SQLx connection lease；transaction/cursor/operation 又持有 Session 的独立 native lease。关闭外层 managed wrapper 不使子对象悬空，也不允许新 child 准入。DataSession及WeaveDataSource同时提供显式CloseAsync(deadline)：关闭新业务准入并加入已有子项终结/cleanup，到期限仍未静默返回CleanupResult(Status=Pending,LocalResourcesReleased=false,ConnectionDisposition=Quarantined)。Engine保留必要parent leases/roots/预算，后台只完成已入线工作与清理，不重新开始业务。DisposeAsync仍join到本地安全；有界HTTP路径选择CloseAsync而不再无条件await using等待。关闭DataSource runtime实例必须等待全部子项retire。

一个 Session 同时最多一个用户 command/reader/COPY。误用立即拒绝，不暗中排队改变事务顺序。Rust 控制/cleanup 路径使用独立内部准入，不能被已关闭的公共 gate 阻挡。SessionExecutor的query_all实现必须stream推进并在每行/bytes预算后有界收集，不能照抄SeaORM默认driver的fetch_all无界收集。每个数据库流由 native operation task 持有完整 stream 和 connection 借用，其生命周期局限在该 async body；公开 cursor 仅持有控制状态/有界通道，不通过 transmute 把借用 stream 塞入自引用跨 FFI 对象。

## 4. ABI 与请求生命周期

复用 [ABI](../contracts/abi-v0.1.md)、[生命周期](../contracts/lifetime-v0.1.md)、[异步](../contracts/async-v0.1.md)、[buffer](../contracts/buffer-v0.1.md)、[错误](../contracts/error-v0.1.md)。不把 Rust enum、Vec、trait object、SeaORM Model 或 CLR object 布局导出。

数据库操作集为 datasource-open / session-open / execute-registered-query / execute-mutation / cursor-open / cursor-fetch / tx-begin / tx-commit / tx-rollback / close-drain；全部异步入口使用两阶段 create→start、一次 terminal notice、一次 typed take_result 和独立 retire。`request_cancel` 只设置 operation 取消意图，不能同步等待 SQLx/SQLite 锁或队列。SafeHandle ReleaseHandle 不执行网络 I/O、阻塞 channel send 或 join。所有生成model native module按D02 v1常驻至进程退出；关闭DataSource实例不卸载模块。

静态查询请求携带 engine/schema/query/projection/semantic-profile IDs 与 typed 参数；动态请求携带同一 schema 下的受限 request IR。**不由 C# 生成 SQL 再让 Rust 当 raw SQL wrapper。** 用户明确的专家 SQL 是独立 capability，仍受参数/预算/静态结果/事务限制，不作为普通查询 fallback。

C# 在第一个 await 前快照参数并构造 wire buffer。成功 start 接管的规则按 D06：create 阶段复制请求到 native-owned arena，失败直接释放；成功 start 后由 operation owner 保有，直到 native retire，不能借用 C# 临时 Span/stackalloc。typed take_result 成功一次移交 owned row-batch/cursor handle；失败保持 native 所有，out 为空。结果 Task 完成不代表 operation 已 retire，更不代表连接已可返池或事务已提交。

### 4.1 db-wire/1 数据格式

以下为字段序列化格式，**不是 C struct 内存布局**；整数 little-endian，无隐式 padding。B01 生成双侧 codec，D07 负责拥有外层 bytes。固定 header 96 bytes：magic `NWDB`(4)、version u16、payload_kind u16、header_bytes u32、flags u32、total_bytes u64、schema_hash[32]、record_count u32、descriptor_count u32、entity_id u32、query_id u32、projection_id u32、semantic_profile_id u32、descriptor_offset u64、payload_offset u64。所有 reserved flags 为0，未知必需版本拒绝。descriptor_offset必须为96（8-byte对齐）；descriptor表紧接header。

普通参数/row-batch payload 使用按行排列的 cell 表。`cell_table_offset = descriptor_offset + 16*descriptor_count`，`cell_count = record_count*descriptor_count`，cell表连续占`24*cell_count` bytes；`payload_offset = cell_table_offset + 24*cell_count`，这些值均checked且8-byte对齐。header、descriptor、cell表分别连续不重叠，payload起点以上才可存cell data；total_bytes不得小于payload_offset。column descriptor 为16bytes：column_or_parameter_id u32、logical_tag u16、flags u16、codec_id u32、reserved u32。每个 cell 为24bytes：logical_tag u16、flags u16、codec_id u32、absolute_data_offset u64、byte_length u64；NULL flag 时 offset/length 必须0。fixed-width 值长度必须与 codec 精确匹配；UTF-8严格校验；variable payload 禁止指向 header/descriptor/cell 表。cell_count=`record_count*descriptor_count`、表长度、offset+length、对齐全部 checked，每个非空cell data范围互不重叠，不接受指向header/descriptor/cell表或其他非空cell的别名；payload可紧密排列，不要求每值天然对齐，codec按bytes读取而不做未对齐typed pointer解引用。row-batch column IDs/shape必须与生成 projection 一致。静态参数 record_count=1；没有参数则 descriptor_count=0。

动态 request IR 使用另一个 payload_kind，节点 opcode/child indices/typed operand字段由 B09 schema 定义；禁止任意 SQL-string 节点，深度/节点/字段/类型重复在 Rust 校验。C# 校验是提前诊断，Rust 是执行权威。header total_bytes 与 owned buffer length 必须相等，schema_hash/semantic profile 必须与 Engine compiled manifest匹配，不以短整数 ID 单独建立跨版本信任。

## 5. 类型语义与 Rust 数据库 codec

C# 侧 codec 仅在 CLR 值与 db-wire 值之间转换；数据库 SQL 类型、参数类型、row→SeaORM Model/Projection 的解释由 Rust schema/driver 决定。对应不匹配在发送前或首个结果 shape 验证失败；没有 `object[]`、反射 setter 或自动字符串化兜底。

| 逻辑值 | PostgreSQL | SQLite 及 portable 限制 |
| --- | --- | --- |
| signed integers | int2/int4/int8，窄化 checked | INTEGER，拒绝溢出后的 REAL 冒充整数 |
| bool | boolean | INTEGER0/1 + schema CHECK，其他值拒绝 |
| string | text/varchar；UTF-8参数 | TEXT；collation显式，不冒充所有.NET字符串语义 |
| Guid | UUID，wire16字节RFC4122顺序 | 同顺序16字节BLOB；禁止历史混合端序 |
| DateOnly | date | 固定ISO日期TEXT，明示范围/日历 |
| UTC instant | timestamptz | Unix microseconds INTEGER；默认拒绝sub-microsecond精度丢失 |
| decimal | 明确numeric(p,s)、范围/舍入策略 | exact TEXT仅往返；可比较money使用固定scale checked Int64 |
| bytes | bytea | BLOB，普通DTO拥有副本 |
| JSON | Rust schema映射JSON列；wire UTF-8文本 | SQLite JSON能力profile；C# typed DTO需显式静态JsonTypeInfo |
| enum/custom | 生成Rust显式类型/转换与数据库声明 | 明确整数/文本映射；未知类型拒绝 |

Npgsql日期/UUID源码只是对照，不能直接证明 SQLx/SeaORM等价；R22保留原证据，B07必须逐类型实测 Rust 路径。nullable 是 SQL NULL；空字符串/default(T)/空array不是替代。NaN/Infinity、时区无限值、大范围numeric、数组和复合类型分别列 provider-specific capability；不自动进入跨provider等价域。

## 6. 有界资源、流与成本

初始保护值：每 DataSource 最多32个外借Session、128等待者、15秒准入超时；buffered结果最多10,000行/16MiB计费数据；每 fetch 最多256行/1MiB；一般字段上限8MiB，但 inline cell 必须同时放入当前 max-batch-bytes，超过者返回 LargeValueRequiresStreaming，不静默突破 batch 上限。大BLOB使用专门有界chunk流。所有上限有限、可配置、checked；参数总bytes/集合元素分别受D16/D17限制。

Rust cursor 一次最多一个 fetch，最多一个未 take 的 owned batch；每个 batch 的 byte permit 随实际owner转移，C#映射完成后归还。预取关闭为默认；启用须明确总页数和字节预算。背压停止 producer推进；取消/消费者break/decoder抛错时停止准入、请求停止、join stream、执行协议清理，再依D06 retire。不能因用户不 await Task 而泄露结果owner。

SQLx rows、SeaORM Model/Projection、wire buffer和C#DTO可能同时存在；预算要覆盖各层在用逻辑bytes，且记录复制次数/FFI次数。SQLx内部buffer、allocator、线程栈和GC开销另测，逻辑budget不是RSS严格上界。ORM模型映射和async-trait boxed future有成本；不能无证据承诺零分配。初版优先可证明正确；B23测吞吐、P95/P99、CPU、native/managed alloc/RSS、build时间、codegen大小和开发代码量。

## 7. SQLite 执行与取消

选定 SeaORM SQLx SQLite 路线，不再发布 Microsoft.Data.Sqlite adapter。SQLx0.9每连接已有专用OS线程、bounded command channel和row channel；不要外面再无条件套 Task.Run 或无限线程池。连接上限同时约束线程数，有限条数队列另加bytes budget。WAL、foreign_keys、busy_timeout、synchronous、journal模式和线程构建选项进入profile。

取消：入线前可拒绝；开始运行后安装在执行前的 native-only progress handler 读取独立 operation atomic flag。request_cancel只store，不获取SQLite handle锁；handler不回调托管、不分配、不panic。结束/清理确认后移除handler或安全更换代际，才能把同一连接给下一操作。SQLx公开lock_handle/progress API需按固定版本验证；不在请求取消时才等待锁去安装handler。

progress interrupt是协作的，不承诺任意sqlite3_step、busy等待、文件系统或扩展代码都有硬时限。丢future/row receiver不是任意step终止证据。SQLx worker的 `start_rollback` / `shutdown` 有同步 bounded-channel send，必须在专用cleanup/coordinator路径，不能进入ReleaseHandle/非阻塞request_stop/try_retire。Drop/reset/close_hard不足以独立证明worker退出；到deadline仍在执行则保留worker、buffer与预算，标 CleanupPending，不伪造安全释放。

SQLx BEGIN成功但ack丢失会回滚；COMMIT/ROLLBACK成功但ack丢失有抑制重复Drop rollback的状态。NativeWeave仍按自己的commit admission和可观察结果分类，不能把这些内部补偿误当业务已收到确认。具体proof与反例见R20/R21；相关上游tests只读未执行。

## 8. PostgreSQL 执行与会话恢复

Rust SQLx PgPool/connection执行参数化SeaORM Statement。生成SQL及sea_query_sqlx::SqlxValues走同一ownership路径；SQLx0.9的AssertSqlSafe只能在已验证Rust lowerer输出或显式审计专家SQL边界使用，不能把它当SQL sanitization。

普通取消是request而不是抢先Task.Canceled；SQLx已读公开路径没有被证明提供等价Npgsql cancel token，因此v1不承诺即时远端CancelRequest。开始前检查标志；执行中以固定会话/事务statement_timeout和受控transport终止策略请求停止，最终状态与cleanup由provider结果决定。若后续加入协议CancelRequest，需单列后端密钥/代际/新连接竞态证明，不能臆造API。本决定不阻止完成设计；B02验证取消、超时、长语句与清理边界。

SessionExecutor保持连接到stream和事务真正结束；可复用需明确无未消费结果/在途取消、事务已终结、session状态恢复。SQLx返池ping可flush待rollback；known deferred cleanup与unknown protocol damage不同。未知损坏用公开PoolConnection::close/close_on_drop剔除，close_on_drop仅安排动作，仍需跟踪cleanup完成。`detach`会放开池permit，不能拿来掩盖仍在清理的连接并突破总预算。完整状态见D15。

## 9. 迁移、包装与版本

应用 Engine manifest包含engine ABI、schema/query/projection hash、Rust工具链/目标、SeaORM/SQLx/SeaQuery及Cargo.lock hash、SQLite实际版本/compile options、codec/语义profile。C#生成facade在加载时校验匹配，缺包/错RID/错误schema禁止连接。Windows win-x64 与Linux linux-x64均用实际native制品和.NET Native AOT二进制执行；其他平台仅候选。

迁移是显式Rust部署命令。不可变migration ID、内容SHA256、provider、from/to schema、最低应用版本及transaction模式写ledger；PostgreSQL事务advisory lock或SQLite明确写事务/部署单owner建立互斥。事务性DDL和ledger同事务提交；非事务DDL分阶段记录、可重入检查/恢复，中断不得补写成功。缺迁移、同ID异hash、schema过旧/过新明确失败，生产不默认destructive down。

SeaORM schema-sync能力不等于生产自动迁移策略。生产构建使用checked-in manifest与migration，不在startup猜测并自动改变live数据库。扩大/收缩兼容窗口显式记录；模型hash变化与SQL数据库schema兼容是两个检查，不能互相替代。

## 10. Codex 可执行验收与剩余义务

| Task | 必须验证的oracle |
| --- | --- |
| B01/B04 | header/offset/length溢出与fuzz拒绝发送；错schema/版本/engine在连库前拒绝；session gate与parent leases安全；无产品Npgsql/MS.Data.Sqlite引用 |
| B02/B03 | Rust真实PG/SQLite→SeaORM Entity/Projection→wire→C#DTO；参数/NULL/错误/stream早停；一Session固定连接；pool耗尽/取消/断线/workercleanup |
| B05/B06 | COMMIT应答丢失Unknown；rollback未确认不谎报RolledBack；返池与retire分离；batch重复take/decoder抛出/消费者break/大值预算 |
| B07/B08 | 每类型往返/负例/范围精度；并发迁移/hash漂移/事务或非事务中断/权限失败；同schema不同旧客户端兼容 |
| B10/B11/B12/B14 | 应用只写C#可生成真正Rust Entity/ActiveModel/relations；schema变化重建并命中hash门禁；关系/并发写入走SeaORM而非全rawSQL |
| B22/B23 | Windows/Linux实际Native AOT、故障与长期负载；对比同语义纯Rust SeaORM与完整C#→FFI→SeaORM；managed参考仅测试依赖 |

未来命令（测试项目由正式任务创建，**本轮未执行**）：`cargo test --locked -p nw-db-postgres`、`cargo test --locked -p nw-db-sqlite`、`dotnet publish <AotSmoke> -c Release -r linux-x64 -p:PublishAot=true` 后运行制品；Windows在对应宿主执行。保留命令/exit/logs/seed、源码/制品hash、实库版本与环境，不用全局抑制IL2026/IL3050制造通过。Q11的RustORM/数据库选型已形成明确设计决定；这些实现义务继续pending。
