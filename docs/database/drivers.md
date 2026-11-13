# D14 — Rust Database Engine and precompiled application boundary

Contract: **C-DB-001@0.2.0-draft**. Status: proposed; independent review pending. Supersedes DB-D004/DB-D005/DB-D006's ordinary SeaORM model-build assumptions, not the historical source facts. Evidence: [R25](../research/topics/R25/source-driven-seaquery.md), [recovered prototype](../research/source-driven-evidence/README.md), existing R19–R22. Transaction safety remains [D15](transactions-and-pooling.md).

## 1. Architecture and selection

Database lower layers are mandatory Rust. After comparing dynamic SeaQuery and static SeaORM, the default implementation candidate is a maintainer-precompiled **SeaQuery 1.0.2 + SQLx 0.9.0** Engine. SeaQuery owns native query construction and dialects; SQLx owns execution, connections, pools and protocol. NativeWeave's Rust Adapter supplies bounded admission, fallible codecs, capability checks, transaction/cleanup coordination and explicit ORM policies. C# supplies business types, typed Fluent calls, static metadata/DTO code and interop; no C# SQL dialect engine or managed-provider fallback.

Static SeaORM Entity/ActiveModel/Relation integration remains a specialized profile with a separately compiled model package. Its build coupling is not a universal property of Rust database access. Ordinary Student/User entities using supported codecs/operators vary as runtime metadata and C# code, not generated Rust. No Cargo or CI-built application Engine is required on that path. New native codecs/operators/providers can require a new maintainer Engine version.

Core has no SQL AST, pool or mandatory global Tokio runtime. Managed drivers remain external comparisons. Source reuse and consumer experience justify this candidate; no performance superiority or independent acceptance is claimed.

## 2. Modules and implementation boundaries

B01 owns domain interfaces/descriptors/limits/errors and the typed C# facade, never a managed product provider. B02/B03 implement Rust PostgreSQL/SQLite adapters. B04 is the required native host, resource admission and runtime/session/pool ownership. B05/B06/B07 own native transactions, bounded streams and fallible codecs. B08 owns Rust migration execution with a C# administration surface. B09/B10 own thin binding metadata and optional static C# generation. B11/B12/B13/B14 own native query/binding, DTO materialization, runtime Fluent composition and explicit Rust relation/CAS policies.

Use disjoint implementation scopes and versioned driver fixtures. Do not create a host/provider cycle or wait for the entire ORM before implementing independent codecs. B21/B22 verify the actual combined implementation.

## 3. Public API and ownership

Draft application shape, **not compiled product API**:
```csharp
await using WeaveDataSource source = DataSources.Postgres(options);
await using DataSession session = await source.OpenSessionAsync(ct);
using var query = session.From(Students.Table);
query.Select(Students.Row).WhereGe(Students.Age, minAge).Take(100);
IReadOnlyList<Student> rows = await query.ToListAsync(ct);
```
The recovered experiment executed a narrower synchronous static-descriptor API. DataSource owns its Engine-local runtime/pool; Session holds one physical connection lease. Transactions/cursors/operations retain parent owners. A Session admits at most one user command/reader/COPY at a time, rejecting concurrency rather than silently changing transaction order. Cleanup admission is independent of the closed public gate.

SafeHandle lifetime protection is separate from the mutable builder's single-writer gate. Sealing freezes query shape and parameter snapshots. Native streams remain inside native async operations that hold connection ownership; do not transmute lifetimes to manufacture a self-referential FFI cursor. Disposal cannot invalidate in-flight callbacks/results.

CloseAsync(deadline) stops admission and waits for retirement up to the deadline. Pending cleanup retains roots, owners and budgets; DisposeAsync joins actual safety. A bounded HTTP path must not follow Pending close with an unconditional indefinite await-using join. Public task outcome, native retirement, connection reuse and remote transaction effect remain separate.

## 4. ABI and operation lifecycle

Consume existing lifetime/callback/async/error contracts and the eventual accepted ABI/buffer layouts. Do not export Rust Vec/String/Expr/Value/traits or CLR layouts. Native modules remain alive while objects/operations/callbacks/buffers can use them. Instance close is not module unload.

Operations cover datasource/session open, builder create/mutate/seal, execute, cursor fetch, transaction begin/commit/rollback and close/drain. Async operations retain create→start, terminal notification, exactly-once take_result and separate retirement. Cancellation requests cannot block on a SQLite lock, channel send or network action. SafeHandle release is not an I/O join.

Direct native-builder calls are the reference route. Batched native operations are a measured optimization candidate requiring bounded validation and partial-mutation failure semantics, not a predetermined universal IR. Expert raw SQL is a separate parameterized capability; never silently fall back to it.

Metadata hashes identify runtime table/column/projection declarations and cache content, not entities compiled into a schema-specific library. Validate enabled native codecs/operators and actual metadata/database compatibility. New application metadata does not by itself change the native Engine binary.

### 4.1 db-wire/1 result and parameter candidate


以下为字段序列化格式，**不是 C struct 内存布局**；整数 little-endian，无隐式 padding。B01 生成双侧 codec，D07 负责拥有外层 bytes。固定 header 96 bytes：magic `NWDB`(4)、version u16、payload_kind u16、header_bytes u32、flags u32、total_bytes u64、metadata_hash[32]、record_count u32、descriptor_count u32、entity_id u32、query_id u32、projection_id u32、semantic_profile_id u32、descriptor_offset u64、payload_offset u64。所有 reserved flags 为0，未知必需版本拒绝。descriptor_offset必须为96（8-byte对齐）；descriptor表紧接header。

普通参数/row-batch payload 使用按行排列的 cell 表。`cell_table_offset = descriptor_offset + 16*descriptor_count`，`cell_count = record_count*descriptor_count`，cell表连续占`24*cell_count` bytes；`payload_offset = cell_table_offset + 24*cell_count`，这些值均checked且8-byte对齐。header、descriptor、cell表分别连续不重叠，payload起点以上才可存cell data；total_bytes不得小于payload_offset。column descriptor 为16bytes：column_or_parameter_id u32、logical_tag u16、flags u16、codec_id u32、reserved u32。每个 cell 为24bytes：logical_tag u16、flags u16、codec_id u32、absolute_data_offset u64、byte_length u64；NULL flag 时 offset/length 必须0。fixed-width 值长度必须与 codec 精确匹配；UTF-8严格校验；variable payload 禁止指向 header/descriptor/cell 表。cell_count=`record_count*descriptor_count`、表长度、offset+length、对齐全部 checked，每个非空cell data范围互不重叠，不接受指向header/descriptor/cell表或其他非空cell的别名；payload可紧密排列，不要求每值天然对齐，codec按bytes读取而不做未对齐typed pointer解引用。row-batch column IDs/shape必须与生成 projection 一致。静态参数 record_count=1；没有参数则 descriptor_count=0。



This retained header is a candidate value/result transport, not a frozen query-operation protocol. Its metadata_hash meaning supersedes compiled-entity inventory semantics and requires explicit compatibility versioning. Native builders may use direct typed ABI methods instead. Reject unknown required versions/tags, oversized allocation, overlapping payload regions, malformed UTF-8 and profile mismatch before submission. B09 compares representations without reimplementing SQL semantics.

## 5. 类型语义与 Rust 数据库 codec


C# 侧 codec 仅在 CLR 值与 db-wire 值之间转换；数据库 SQL 类型、参数类型、row→显式结果projection 的解释由 Rust metadata/driver 决定。对应不匹配在发送前或首个结果 shape 验证失败；没有 `object[]`、反射 setter 或自动字符串化兜底。

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
| JSON | Rust metadata映射JSON列；wire UTF-8文本 | SQLite JSON能力profile；C# typed DTO需显式静态JsonTypeInfo |
| enum/custom | 预编译能力内的显式整数/文本映射；新增native codec另发Engine版本 | 明确整数/文本映射；未知类型拒绝 |

Npgsql日期/UUID源码只是对照，不能直接证明 SQLx / NativeWeave Rust adapter等价；R22保留原证据，B07必须逐类型实测 Rust 路径。nullable 是 SQL NULL；空字符串/default(T)/空array不是替代。NaN/Infinity、时区无限值、大范围numeric、数组和复合类型分别列 provider-specific capability；不自动进入跨provider等价域。

## 6. 有界资源、流与成本

以下数值是可配置设计起点，不是已测得的容量或性能结论：每 DataSource 最多32个外借Session、128等待者、15秒准入超时；buffered结果最多10,000行/16MiB计费数据；每 fetch 最多256行/1MiB；一般字段上限8MiB，但 inline cell 必须同时放入当前 max-batch-bytes，超过者返回 LargeValueRequiresStreaming，不静默突破 batch 上限。大BLOB使用专门有界chunk流。所有上限有限、可配置、checked；参数总bytes/集合元素分别受D16/D17限制。

Rust cursor 一次最多一个 fetch，最多一个未 take 的 owned batch；每个 batch 的 byte permit 随实际owner转移，C#映射完成后归还。预取关闭为默认；启用须明确总页数和字节预算。背压停止 producer推进；取消/消费者break/decoder抛错时停止准入、请求停止、join stream、执行协议清理，再依D06 retire。不能因用户不 await Task 而泄露结果owner。

SQLx rows、wire buffer和C#DTO可能同时存在；预算要覆盖各层在用逻辑bytes，且记录复制次数/FFI次数。SQLx内部buffer、allocator、线程栈和GC开销另测，逻辑budget不是RSS严格上界。结果转换和必要async适配有成本；不能无证据承诺零分配。初版优先可证明正确；B23测吞吐、P95/P99、CPU、native/managed alloc/RSS、build时间、codegen大小和开发代码量。

## 7. SQLite 执行与取消

普通路线使用Rust SQLx SQLite adapter，不再发布 Microsoft.Data.Sqlite adapter。SQLx0.9每连接已有专用OS线程、bounded command channel和row channel；不要外面再无条件套 Task.Run 或无限线程池。连接上限同时约束线程数，有限条数队列另加bytes budget。WAL、foreign_keys、busy_timeout、synchronous、journal模式和线程构建选项进入profile。

取消：入线前可拒绝；开始运行后安装在执行前的 native-only progress handler 读取独立 operation atomic flag。request_cancel只store，不获取SQLite handle锁；handler不回调托管、不分配、不panic。结束/清理确认后移除handler或安全更换代际，才能把同一连接给下一操作。SQLx公开lock_handle/progress API需按固定版本验证；不在请求取消时才等待锁去安装handler。

progress interrupt是协作的，不承诺任意sqlite3_step、busy等待、文件系统或扩展代码都有硬时限。丢future/row receiver不是任意step终止证据。SQLx worker的 `start_rollback` / `shutdown` 有同步 bounded-channel send，必须在专用cleanup/coordinator路径，不能进入ReleaseHandle/非阻塞request_stop/try_retire。Drop/reset/close_hard不足以独立证明worker退出；到deadline仍在执行则保留worker、buffer与预算，标 CleanupPending，不伪造安全释放。

SQLx BEGIN成功但ack丢失会回滚；COMMIT/ROLLBACK成功但ack丢失有抑制重复Drop rollback的状态。NativeWeave仍按自己的commit admission和可观察结果分类，不能把这些内部补偿误当业务已收到确认。具体proof与反例见R20/R21；相关上游tests只读未执行。

## 8. PostgreSQL 执行与会话恢复

Rust SQLx PgPool/connection执行SeaQuery构建的参数化语句。生成SQL及显式fallible参数binder走同一ownership路径；不得丢弃Arguments::add错误或对unsigned窄化unwrap；SQLx0.9的AssertSqlSafe只能在经过能力/类型检查的Rust SeaQuery输出或显式审计专家SQL边界使用，不能把它当SQL sanitization。

普通取消是request而不是抢先Task.Canceled；SQLx已读公开路径没有被证明提供等价Npgsql cancel token，因此v1不承诺即时远端CancelRequest。开始前检查标志；执行中以固定会话/事务statement_timeout和受控transport终止策略请求停止，最终状态与cleanup由provider结果决定。若后续加入协议CancelRequest，需单列后端密钥/代际/新连接竞态证明，不能臆造API。本决定不阻止完成设计；B02验证取消、超时、长语句与清理边界。

SessionExecutor保持连接到stream和事务真正结束；可复用需明确无未消费结果/在途取消、事务已终结、session状态恢复。SQLx返池ping可flush待rollback；known deferred cleanup与unknown protocol damage不同。未知损坏用公开PoolConnection::close/close_on_drop剔除，close_on_drop仅安排动作，仍需跟踪cleanup完成。`detach`会放开池permit，不能拿来掩盖仍在清理的连接并突破总预算。完整状态见D15。



## 9. Migration, precompiled packages and compatibility

The Engine manifest binds ABI, capability/codec profile, RID, toolchain, locked dependencies and native asset hash. Application metadata, query shape and migration history are separately versioned; see D10. Ordinary entity changes require at most static C# metadata/DTO regeneration, never default Cargo. Registry crates and source commits retain separate provenance until checked.

Migrations are explicit Rust administrative operations, not speculative startup schema-sync. Immutable ID/content hash/provider/from-to version/transaction mode enter the ledger. PostgreSQL advisory locking or SQLite explicit writer/deployment admission serializes migration owners. Transactional DDL and ledger commit together; nontransactional DDL uses staged resumable checks. Same ID/different hash, missing migration, inadequate permission and incompatible schema fail explicitly. Destructive down-migration is not the production default.

## 10. Source-driven failure gates and acceptance

Reject SQLite row-lock/SELECT INTO/SEARCH-CYCLE requests that the pinned renderer silently ignores. Catching panic cannot detect omitted semantics. Check CTE shape and values before native rendering. A fallible argument binder propagates every encoding error and checks narrowing; do not use discarded add errors or unsigned unwrap. Poison unsafe partial builder mutations and retain all live owners.

B01/B04 verify malformed metadata/length/shape fuzzing, ABI/RID/capability rejection and no managed product provider. B02/B03 verify actual Rust PG/SQLite into typed batches/DTOs, schema errors, cancellation, stream early stop and pool/worker cleanup. B05/B06 verify Unknown COMMIT, unconfirmed rollback, reuse versus retirement, decoder exceptions and huge fields. B07/B08 cover every codec negative and migration interruption. B09–B14 cover typed native query parity, metadata/DTO generation and bounded relation/CAS scope. B21–B24 cover Windows/Linux AOT, faults/soak, clean no-Rust and RID-free consumers, unchanged native hash after entity changes, and full-workload costs.

The recovered Linux SQLite AOT experiment is real but finite. Its JSON/fetch_all/per-call-runtime/raw-handle shortcuts are not the production streaming/pool/concurrency design. Windows, PostgreSQL faults, production generator, async lifetime and hard resource bounds remain unverified. Never suppress IL2026/IL3050 indiscriminately to manufacture acceptance.
