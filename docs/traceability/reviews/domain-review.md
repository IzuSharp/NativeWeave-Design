# 独立领域交叉审查：Database / ORM / Server 候选边界

- Review ID：REV-DOMAIN-20261112-01。
- 审查者：`/root/domain_research`，未编写被审查的 root 候选架构文档。
- 作者：`/root`。
- 审查对象：`docs/architecture/candidate-boundaries.md` v0.1.0，重点第 6–8 节，并检查其与第 3–4 节生命周期不变量的交互。
- 被审查快照 SHA-256：`6baed2965aac588633dcecd2959fe592d9972ec95ddd9d4d835097a735dd3670`。
- 日期：2026-11-12。
- 审查方式：文档独立对抗性检查 + 限定外部源码核对。没有运行模型、编译、测试或负载。
- 独立性边界：本审查不对本代理自己的领域报告作“独立验收”；它是 root 候选文档的局部交叉审查，不是整个 NativeWeave 的最终独立架构审查。
- 处置状态：以下发现已提交作者修订；尚未由本审查者复核修订版。

## 总体评价

草案正确保留了 C# First、可选 Rust、功能级 AOT 验证、静态查询与受控动态 IR 的区别，以及公共结果完成和原生资源静默之间的分离。没有发现必须推翻候选分层的证据。它适合作为并行研究输入。

正式契约接受之前，仍应落实下面五个范围有限的澄清。前三项会直接影响事务恢复和释放协议，不能仅以“实现时小心”关闭；其余两项影响验证的可解释性。发现均针对当前文字的潜在实现歧义，不声称已发现实际产品 bug。

## DR-001：事务结果未知需要独立、可恢复的表示

- 严重度：Medium。
- 位置：第 4 节公共结果状态；第 6 节“提交时断线可能意味着提交结果未知”。
- 已有优点：文档已经拒绝“取消意味着没有提交”的错误推论。
- 缺口：公共任务仍只有 Succeeded/Failed/Canceled 示例，领域约束没有要求把数据库效果的知识状态传递给调用者。实现者可能只抛普通取消/网络异常，然后丢失“COMMIT 可能已成功”的信息。
- 反例：服务端已提交，响应丢失；CancellationToken 恰好触发。C# Task 结束为取消，但持久化效果仍可能是已提交，不能由 Task 状态恢复出正确事实。
- 建议修订：明确“调用完成状态”和“数据库提交效果的已知状态”是独立维度。领域错误/结果必须携带或可检索 `ConfirmedCommitted / ConfirmedRolledBack / Unknown` 等效果分类及恢复标识；最终枚举名称待正式 API 决策。并非要求修改所有通用异步任务的终态。
- 验证要求：对 COMMIT 发送前、发送后确认前、服务端已提交但响应丢失注入故障；检查调用者能识别 Unknown，且不会因为 cancellation 误报 rollback。
- 外部事实依据：SQLx 明确区分等待 commit/rollback 成功与仅启动回滚，见 [固定通用事务](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/transaction.rs)。数据库提交不确定性完整协议证明仍需对应 PostgreSQL/SQLite 专题。
- 处置建议：补入候选约束，并绑定事务契约、错误映射与故障注入任务；完成文本修订后再复核。

## DR-002：幂等键不能单独成为自动重试的充分条件

- 严重度：Medium。
- 位置：第 6 节“重试需幂等键或上层恢复策略”；第 8 节原子修改及 outbox 参考应用。
- 缺口：这句话表达了必要方向，但没有说明幂等键只有在正确持久化和重放协议下才有效。
- 反例：业务写入已提交，幂等记录单独写入前进程崩溃；重试查询不到键，再执行一次业务。另一个反例是幂等记录先存在但业务未提交，重试错误地认为已完成。
- 建议修订：若框架或参考应用自动重试有副作用操作，去重记录、业务变更和可重放结果必须有明确原子边界；需说明键作用域、请求内容一致性、并发相同键、保留期和冲突行为。外部副作用通过单独协调/outbox 协议处理，不承诺网络级或跨系统 exactly-once。
- 验证要求：在业务/幂等记录提交边界、确认丢失、并发相同键、相同键不同参数、清理过期记录处测试。重试后的持久化效果和可返回结果必须符合声明。
- 依据类型：由草案现有 Unknown commit 约束和原子修改/outbox 场景推导的工程证明义务；本条不是来自某库营销声明。
- 处置建议：加入 DB 恢复契约及参考应用验收条件；不要求现在选定唯一去重存储实现。

## DR-003：资源静默、连接可复用与数据库确认是三个不同承诺

- 严重度：Medium。
- 位置：第 3 节 `native_obligations=0` 与 free；第 4 节 Quiescent/Reclaimed；第 6 节 SQLx Drop/Dispose。
- 缺口：`native_obligations` 未定义。若把未确认数据库效果也放入这个计数，Unknown 状态可能导致永久无法释放；若仅把句柄引用归零当作可归还连接，又可能把仍有 rollback/协议响应的连接交给其他查询。
- 反例：掉线后数据库提交效果暂时无法确定，但本地连接/context 已可安全丢弃；相反，资源没有外部 callback 并不表示活连接协议已恢复到可复用状态。
- 建议修订：
  - Quiescent 证明之后不再访问该内存/context，是内存生命周期承诺。
  - Reusable connection 需要该 provider 的协议状态已排空、清理已确认；否则丢弃连接。
  - Unknown durable outcome 可以在本地资源释放后保留为独立恢复记录，不强迫保留原生句柄等待无限期确认。
  - 同步 Dispose、DisposeAsync、pool return 和 shutdown 分别列出其承诺，避免共享一个“释放成功”状态。
- 验证要求：排队 rollback 后立刻归还连接、executor 已停止时清理、断线 Unknown、回调迟到、关闭时 drain；确认不会泄漏上下文，也不会把脏连接重新出租。
- 外部源码依据：[SQLx PostgreSQL `start_rollback`](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-postgres/src/transaction.rs) 只排队；[hyper 关闭入口](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/src/server/conn/http1.rs#L120-L155) 仍需持续 poll 才完成。
- 处置建议：第 3/4/6 节各补一句限定定义，正式分项测试归到 ownership、database 和 shutdown 契约。

## DR-004：逻辑资源预算不能未经额外假设解释为 RSS 上界

- 严重度：Medium。
- 位置：第 7 节 `resident_work_bytes` 候选不等式。
- 已有优点：文档已经同时限制活动连接、请求、排队数和 buffer 字节，且指出条数上限不足。
- 缺口：resident 命名与“固定运行成本”容易使候选逻辑预算被误读为整个进程 RSS 的数学上界。GC segment、native allocator arena、TLS/codec、驱动池、任务等待状态和操作系统缓冲不一定由这个表达式覆盖。
- 建议修订：将此式明确命名为“框架拥有的在途工作字节预算”，列出排除项；所有大 buffer 和等待任务必须先取得 admission/byte budget，再分配或登记。进程 RSS、native reserved/committed、GC committed 与线程栈需另测，除非能证明每项均纳入界限。
- 验证要求：大量生产者先分配后等待、超大请求、慢客户端、HTTP/2 多 stream、取消后 allocator 保留内存的长时负载；分别记录 logical owned bytes 和实际 RSS。
- 外部源码依据：[Tokio bounded channel](https://github.com/tokio-rs/tokio/blob/be8ee45b3fc2d107174e586141b1cb12c93e2ddf/tokio/src/sync/mpsc/bounded.rs) 的容量控制是消息 permit；无法仅凭该点证明队列外内存有界。
- 处置建议：局部收紧表达式说明；无需引入新的公共调度/runtime 层。

## DR-005：typed query 契约应分开“类型正确”“SQL 语义正确”和“允许能力”

- 严重度：Low。
- 位置：第 6 节受限 typed AST、identifier allowlist 与语义上限。
- 已有优点：文档已区分 Expression Tree 和动态编译，明确 SQL 三值逻辑及禁止静默客户端求值。
- 缺口：强类型 AST 和 identifier allowlist 仍不直接证明 provider SQL 正确，也不自动证明生成器覆盖完整。
- 建议修订：为 typed AST 指定静态字段/操作/类型目录和 provider capability 检查；标识符还需正确方言引用。支持语法、可执行模型、生成映射和 unsupported diagnostics 应分别追踪。动态 IR 的结构规模、参数数量和展开列表也要有声明的边界，而不仅是功能列表。
- 验证要求：正负编译样例、生成器未接管调用检测、不同 provider 的 null/collation/decimal 实库差分、超出支持能力时拒绝而不是悄悄改变语义。
- 外部源码依据：[DapperAOT 筛选与不生成分支](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs)；[EF Core v11 QueryCompiler 动态编译守卫](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs)。
- 处置建议：在查询 IR、生成器和 SQL 语义文档中分别展开，不要求现在公开完整 IQueryable 接口。

## 当前版本来源复核

本次额外读取了 EF Core v11.0.0 的 QueryCompiler，以及 Kestrel v11.0.0 的 HttpResponsePipeWriter 和对应测试。详见 [v11 源码复核](../../research/domains/v11-recheck.md)。

- EF Core v11 当前限定入口仍有动态代码守卫及实验性预编译标注；不能把 .NET 11 已 GA 推导为每个 ORM AOT 功能都已接受。
- Kestrel 两个限定文件的 blob 与先前 v10 一致；本复核没有扩大为整个 Kestrel/ASP.NET 的版本对比。
- 当前候选文档没有把这两种错误推断作为已接受事实，因而该项是证据更新，不是另一个缺陷。

## 关闭发现的条件

作者应对每个 ID 记录 accepted / rejected-with-reason / superseded，并提供对应修订位置。修订后由本审查者或另一个未主导该修改的人核对具体影响范围。只有文字修订完成而实验未执行时，关闭的是“草案含糊”发现，不是宣称事务、AOT、内存或关闭协议已经通过验证。

## 首次修订复核与局部 Plan 依赖检查

复核日期：2026-11-12。复核者：`/root/domain_research`。

已实际重新读取候选文档，当前复核快照 SHA-256 为 `7153a79a7284585570f148000e48756a5804035b9bcccaa6e356e3203d272d3f`。以下 disposition 只处理 bootstrap 草案中的表达和任务分工歧义，不接受任何产品技术契约，也不代表相关运行验证已通过。

| 发现 | 复核状态 | 实际修订与剩余义务 |
| --- | --- | --- |
| DR-001 | closed_bootstrap_text | 第 4 节新增独立 effect 状态，并明确 Task 取消/失败不能抹掉 Unknown。公开错误/恢复载荷与故障实验仍待正式契约及实现。 |
| DR-002 | closed_bootstrap_text | 第 6 节明确幂等检查、业务写入和结果记录原子性，补充唯一约束、重放、过期、外部副作用；单个 key 不是保证。 |
| DR-003 | partially_resolved | 第 4 节已拆分 native 静默、连接协议可复用与远端效果确认，但 `native_obligations` 仍未限定是否包含 Unknown；建议再明确 Unknown 可作为恢复记录独立于本地句柄存在，协议不干净连接丢弃。 |
| DR-004 | closed_bootstrap_text | 第 7 节改为 `accounted_work_bytes`，限定为预算假设下逻辑在用内存，明确不是 RSS，并列出额外内存项。预算执行机制和真实 RSS 测量仍待验证。 |
| DR-005 | closed_bootstrap_text | 第 6 节分别要求类型、provider 能力、SQL 语义、生成器接管和不支持诊断验收。具体 IR 大小、参数上限与方言规则仍属于正式专题输出。 |

### Plan 中发现并已复核修正的三个局部依赖

本审查只读取候选图与 task packet，不代写 Plan。作者 `/root/parallel_plan` 已落实修改，且本审查者实际读取了修改后图、B04/B07/B20 packet，并计算其哈希与图中 `packet_sha256` 一致。

复核的 `Plan/delivery-graph.json` SHA-256：`391bc63d9842d7a08e30d2a3c50f7e41d9cd2abe1a18bcedcd5342375d5ea5df`。

| ID | 原歧义/门槛 | 实际修订 | disposition |
| --- | --- | --- | --- |
| DP-001 | B07 数据库静态 codec 等待整个 C-QUERY-001，连带使 B02/B03 基础 driver 等待 ORM 查询 IR | B07 只要求 C-DB-001；物理值与 NULL/precision 归数据库契约，查询层消费其规则 | closed_bootstrap_plan |
| DP-002 | B20 普通 HTTP 诊断/关闭等待 C-PROTOCOL-001，即可选 gRPC/MCP 设计 | B20 只要求 C-SERVER-001；无强迫协议依赖 | closed_bootstrap_plan |
| DP-003 | B04 Rust SQLx Engine 未显式输入 runtime 所有权、容量、停止语义 | 增加 C-CONCURRENCY-001；未无条件增加 A08 实现依赖，因此仍可使用引擎自身 runtime | closed_bootstrap_plan |

除此之外，B01、B09、B15 没有“整个阶段 A 完成”的开工依赖；B04/B17 只列相关机制的局部代码依赖。B21–B24 的 optional native 分支采用选择条件门槛，B24 另有发布 scope；这些方向符合当前并行目标。此观察不替代 graph validator，也不证明未来具体实现中不存在新的共享文件或运行资源冲突。

## DR-003 最终局部文字复核

- 日期：2026-11-12。
- 复核者：`/root/domain_research`。
- 当前候选文档 SHA-256：`432fa9cb1863485e928b6a5dc5ecf3752afa5465cbf9b4c519b3247216122264`。
- 范围：只重新读取第 4 节新增的 `native_obligations` 定义与三种确认段落；没有扩展审查。

实际修订明确了三点：

1. `native_obligations` 只计仍会访问本地资源内存或必须在其上完成的清理义务，不包含远端提交结果尚未知这一知识状态。
2. Unknown 的数据库效果可在本地资源安全回收后保留为独立恢复记录。
3. 未确认协议状态干净的连接应关闭并丢弃，不能仅因 native 已静默而归还连接池。

因此 **DR-003 disposition 更新为 `closed_bootstrap_text`**。此记录取代上一轮该项 `partially_resolved` 的当前状态，原始发现与历史复核保留。

至此 DR-001 至 DR-005 的 bootstrap 文本歧义均已关闭。关闭仅说明候选文档准确划清义务；事务恢复、连接回收、异步静默与 AOT 产品技术契约仍未被接受，具体实现和真实验证仍需按照对应研究/文档/交付任务完成。



