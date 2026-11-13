# 候选边界、实现难题与决策输入

状态：design-draft；版本 0.2.0-draft。以下是待研究的设计空间，不是 accepted API/ABI。关联契约见 [registry.json](../contracts/registry.json)。

## 1. 最小机制与领域语义分离

建议评估四个独立层面：

| 层面 | 职责 | 不应承担 |
| --- | --- | --- |
| 应用与领域 API | 自然 C#、领域错误、取消和资源使用方式 | 暴露原始裸指针给普通应用 |
| 每引擎 Adapter | 领域强类型映射、拥有/借用规则、能力选择 | 将任意领域都塞入同一“大对象模型” |
| 编译期工具与 ABI 契约 | 类型布局、生成、诊断、版本检查和平台打包 | 为无 Rust 应用增加原生调度器 |
| 独立 Rust Engine | 所选原生库与内部实现、该引擎需要的 runtime | 依赖其他引擎的运行状态或下游业务 |

这些层面不必对应四层运行时对象。能以生成代码消除的胶水不自动成为一个公共运行时。是否需要公共 managed helper、native helper crate、handle table 或 shared runtime，逐一作成本决策。

## 2. ABI 研究必须回答的问题

候选 ABI 为各目标的稳定 C ABI；它不等于一个跨 OS/CPU 通用二进制布局。需明确每个 struct 的 size/alignment/offset、按值传参/返回 ABI、枚举合法数值和 pointer width。

候选规则：显式宽度整数；bool 选择 0/1 的固定宽度表示；UTF-8 使用指针+长度；不透明句柄；复合输出通过明确 out 参数。尚需比较 size_t/nuint 与 u64 长度、pointer/代际token、按值/按址返回、动态/静态链接。禁止直接暴露 Rust Vec/String/Trait object/Future 或 C# 托管对象布局。

最新官方AOT互操作说明指出：.NET11启用runtime marshalling时，native调用含非blittable签名的UnmanagedCallersOnly（例如bool返回或char参数）会fail-fast，不能依靠callback体内catch补救。绑定分析器必须验证整个签名，负例在隔离进程AOT执行。Direct P/Invoke也不遵循DefaultDllImportSearchPaths，需要单独验证OS loader和链接策略。[官方依据](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop)

C# 15 union 与 C ABI union 是不同问题。见 [工具链报告](../research/toolchain/report.md)：默认 union 的值类型装箱、default/null 与非装箱 pattern 都应实测，不能把现代语法当作低开销证据。

ABI 版本至少区分：产品包版本、引擎版本、ABI major/minor、capability version、schema/生成器版本。是否协商 function table、按 symbol version 或包内锁步，需通过旧新组合加载实验决策。

## 3. 所有权与安全不变量

为每个 resource r 定义 owner、live、active_leases、callbacks_inflight、native_obligations、closing。候选不变量：

- 释放计数 free_count(r) ≤ 1。
- use(r) ⇒ live(r) ∧ valid_lease(r)。
- free(r) ⇒ closing(r) ∧ active_leases(r)=0 ∧ callbacks_inflight(r)=0 ∧ native_obligations(r)=0。
- 释放 callback context 前，应有 native 不再调度该 context 的确认及所有在途 callback 退出证据；还要独立撤销并排空managed CancellationTokenRegistration等可能访问context的来源。native quiescence不替代managed取消注册静默。
- 父对象必须活到最后一个子对象的 native 访问结束；GC 可达不等于 native lease。

不能用“检查 handle != 0”代替释放竞争控制。SafeHandle 的使用期引用与长生命周期 native 异步引用是不同职责。若显式提取 raw handle，必须评估自动引用保护是否仍然存在。代际 token 可以降低 ABA/陈旧句柄风险，但引入查表、同步、计数溢出和复用策略；不能因安全口号强制所有同步函数使用表。

## 4. 异步结果与资源静默分别建模

候选状态有两个维度：

| 维度 | 状态例子 | 必须澄清 |
| --- | --- | --- |
| 对应用的结果 | Pending / Succeeded / Failed / Canceled | 唯一线性化点；取消是请求还是结果 |
| 原生资源使用 | Running / StopRequested / Quiescent / Reclaimed | 完成回调是否仍持有上下文；停止确认含哪些任务 |

对每个操作 o，terminal_publications(o) ≤ 1。这个安全性质并不证明操作最终完成。最终回收还需要 executor 推进、通知到达、shutdown 协议和公平性等活性假设。

数据库操作还需要独立的effect状态，例如NotSent、ConfirmedCommitted、ConfirmedRolledBack、Unknown。Task变成Canceled或Faulted不能抹去持久化效果Unknown；native资源静默、连接协议恢复可复用、远端事务效果确认也是三个独立承诺，不能相互代替。

这里的native_obligations只计仍会访问当前资源内存、或必须在该资源上完成的本地清理义务；它不包含“尚不知道远端提交结果”这一知识状态。远端效果Unknown可在本地资源安全回收后由独立恢复记录保留。连接若未确认协议状态干净，应关闭并丢弃，不能因native已静默而返回连接池。

完成可以早于 start 返回，CancellationToken 注册可以同步执行回调；两者必须进入测试。禁止在持有回调所需锁时同步等待 native 关闭。用户 continuation 的执行线程与 FFI callback 线程应清楚，避免隐藏同步重入。

Task、ValueTask、IValueTaskSource 的候选需要比较：后两者不是无条件更优，复用需要 generation/token、单消费者约束和迟到通知防护。基础方案应先有可理解且正确的状态机，再决定是否值得池化。

## 5. 数据传输与错误

每个 buffer 明确 allocator、deallocator、有效期、可变性、alias、alignment、length/capacity 单位。同步借用和异步保留是不同能力；跨 await 保留指针须明确稳定地址与释放时机。

默认成本账本记录 FFI 次数、每字节复制、分配、GCHandle、native handle、线程与 runtime。零拷贝只是候选优化；若源内存的安全证明更复杂而收益不足，允许明确复制。

普通失败返回 Result/status。panic containment 要区分 unwind 与 abort，catch_unwind 不能恢复 abort、OOM abort 或任意外部异常；panic hook、payload析构也需研究。C# reverse callback 必须在托管入口捕获可处理异常，转换成契约规定的错误/完成信号；不允许托管异常越过 FFI 边界，也不能宣称 catch 能恢复进程致命故障。损坏状态是否允许继续使用必须明示，不能只把错误转 Exception 就宣布引擎恢复。

## 6. Database / ORM revised candidate boundaries

Database lower layers must be Rust; managed providers are comparisons only. The ordinary candidate uses precompiled dynamic SeaQuery AST/identifiers/values with SQLx execution. C# owns typed Fluent and static metadata/DTOs, not a SQL AST/dialect or full LINQ translator. Static SeaORM Entity remains a specialized profile; its native model-build coupling does not imply all Rust database integrations require per-entity compilation.

See ADR-0002, D14, D16/D17 and R25's source study. Direct native builder is the reference route; batching requires measurements, not a preselected universal IR. Explicit SQL null/collation/join/pagination and codec semantics remain mandatory. Reject SQLite silently omitted clauses and use fallible native binding. Unknown transaction effect, protocol reuse and local retirement remain independent.

## 7. Server 候选边界

纯 C# AOT + Kestrel 是必须比较的成熟基线；Rust engine 只有在具体场景收益支持时引入。普通 C# handler 的编程体验、请求上下文、取消与流生命周期应独立于 engine。

HTTP/TLS 的所有权划清，不让两个实现同时处理同一层协议状态。gRPC/MCP 可作为上层协议适配，不成为所有引擎的必要依赖。Hyper C API 自身不稳定不影响其 Rust库研究价值；如果选用，稳定对外契约由 NativeWeave 明确定义和验证。

流量预算至少包含 active_connections、active_requests、queued_requests、buffered_bytes。候选有界性质：
accounted_work_bytes ≤ Σ(connection_budget) + active_requests×request_budget + bounded_queue_budget。
这只是假设所有相应对象受预算约束时的逻辑在用内存界限，不能直接当作RSS上界。实际RSS还包括allocator保留、碎片、GC堆、线程栈、代码与运行时；内核socket/TLS缓冲也需单列。只限制队列条数而不限制请求体大小不能证明有界内存。HTTP/2 multiplex、slow reader、半关闭、client abort、TLS握手和graceful shutdown分别测试。

## 8. 参考应用与两个真实 Engine 证明

参考应用候选为“工作项与附件服务”，无 ArcForges 业务依赖。功能：创建工作项、按条件检索、原子修改及outbox记录、分页/流式读取、附件压缩/下载。包含 PostgreSQL 路线，SQLite只运行确实适用的场景；不能抹平两者并发或SQL语义差异。

压力与失败场景：连接池耗尽、慢客户端、DB断连、提交结果未知、取消和响应竞争、服务重启、迁移冲突、重复请求和背压。对每个栈保持数据集、协议、TLS、payload、请求分布、错误语义和硬件可比。

两个 Engine 的正式选择尚未接受。同步模块和异步流式模块分别验证不同能力；任何模块的研究原型都不能伪称完整生产实现。

## 9. 现在可并行编写与必须等待的部分

可并行：ABI布局候选、状态机、生成器设计、database语义、native查询绑定、server边界、打包矩阵、性能方法、各领域任务片段。

真正要等待：某任务正式实现依赖的精确契约版本被接受、针对该路径的证据具备、公共变更经局部审查。不存在“全体研究完成”这一普遍前置条件，也不存在跳过契约验收的捷径。

## 10. 尚未证明

上述不变量是证明义务，候选接口不是编译结果。恢复并迁移的 Actions 已有 Windows/Linux Interop 的真实 NuGet、无 RID 普通消费及 Native AOT 执行，两个平台的有限 Rust Database/Server fixture，以及此前有限 Linux/SQLite C#/Rust 查询 AOT。源码、实际执行 commit 与制品身份见[迁移记录](../traceability/research-asset-migration.md)。这些记录不等同于 clean Rust-free 消费主机、PostgreSQL、完整 C# Database/Server AOT、性能或生产内存界证明；旧“本地没有编译器、没有 Windows 结果”的恢复观察已过期。新增生命周期研究见[续接检查点](../traceability/source-lifecycle-followup.md)。无需为证明“简洁”预先造公共 runtime；根据源码研究、模型、最小原型、真实 AOT 和工作负载证据逐步缩小候选。

## 11. Source-driven Engine maintenance

[D11](../extension/engine-integration.md) defines public/source-informed/extension/fork integration. [D10](../platforms/build-package-release.md) separates maintainer native builds from ordinary C# consumption and specifies source/closure pins and upgrade differential gates. Core owns no domain SQL or Server state. These amended contracts remain proposed; previous reviews do not approve new hashes.
