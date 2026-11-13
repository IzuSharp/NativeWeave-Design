# R09：异步结果、取消、回调与资源退休

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

日期：2026-11-12。作者：interop_design。状态：**partially_evidenced；design decision recorded；finite model executed；independent review pending**。研究输出为[D06](../../../contracts/async-v0.1.md)，同时约束D04/D05。普通Task完成、native静默、实际实现验证与生产验收是不同事实。

## 1. 输入、目标与非目标

固定Design基线`1f7d89aa754647a6a530fa34a49acc4b0f5d9997`、Plan基线`da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。R09 packet revision `0.1.1`，SHA256 `b695871a811c8d556edf74d8f75a2f2997bbb808286ae2abea49bd2db45d6afd`；D06 revision `0.1.1`，hash `0d6f8c06dbccf3fbd2a7a391addc203f797a003ede9bbf4b38edd68483917102`。已核对固定远端图与实际packet字节。

目标是自然的Task/async/await和CancellationToken体验，并明确处理同步完成、取消registration同步执行、重复终态、迟到取消、结果owner转移、Dispose重入和cleanup无进展。普通应用开发者不写Rust。同步Engine不被迫进入通用异步runtime；数据库提交效果不由Task取消状态替代。

本轮不实施整个框架，不依赖preview runtime async，不池化context或IValueTaskSource。真实.NET/Rust并发、弱内存和Native AOT尚未执行。

## 2. v1设计决定

1. create与start分开；context与注册状态先可用，再允许native接管。
2. accepted操作的业务终态由native唯一提交；cancel只记录请求，不能立即把Task改为Canceled。
3. 普通API返回Task<T>，TCS使用RunContinuationsAsynchronously；多await语义自然，分配成本明确记账。
4. terminal callback只复制固定status/error；回调外完成协调器调用一次typed take_result，失败原子性与owner转移明确。
5. native try_retire仅证明native工作与callback不再访问；最终release还要start返回、取消注册已外部排空、managed callback与control调用归零。
6. 每操作配额在native接受前预留，Task不被await仍自动清理operation；结果owner与活跃操作分别计量。[R09-D01]

这些是可直接实现的推荐选择，等待独立审查，不以“所有方案都proposed”代替决策。后续性能证据可触发局部演进，不降低当前安全不变量。

## 3. 固定源码与覆盖

| 来源 | SHA | 已读机制 |
| --- | --- | --- |
| dotnet/runtime v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | CancellationTokenSource.Register、CancellationTokenRegistration、TaskCompletionSource<T>、Task完成与continuation调度、取消测试 |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | managed begin/callback/Dispose、Rust spawn/select/oneshot/complete/abort |
| 本仓库有限模型 | 文件SHA256 `016760cddb78698827bccc472a2d653cba55e20ba15c61c3480a3faea559cd1f` | 新增setup/start/control/registration退休偏序与三个负对照 |

逐条source证据与blob见[evidence.json](evidence.json)；[coverage.json](coverage.json)明确未读Task完整调度器、ManualResetValueTaskSourceCore、Tokio内部waker以及UniFFI async桥。Tokio与UniFFI仍是替代实现比较的后续补证，不把已读YAHA中Tokio调用点说成已经读完Tokio实现。

## 4. .NET取消链路：回调能先于registration赋值

[`CancellationTokenSource.Register`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenSource.cs#L586-L687)先尝试登记callback节点，随后仍须处理与取消状态的竞争；已取消时可同步调用callback后才返回registration。这不是异常路径专属情形，NativeWeave不能把“取得返回的registration”当成callback最早执行点。[R09-S01]

因此context、handle、固定计数与cancel_requested必须在UnsafeRegister前初始化。setup lease保持context；回调可以记取消并通过控制lease调用Created状态允许的request_cancel。Register返回后才发布registration_ready。此后若还没start且已观察取消，可以安全跳过start；否则start提交后由native终态决定结果。

[`CancellationTokenRegistration.DisposeAsync`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenRegistration.cs#L32-L110)在需要时等待正在其他线程执行的callback；Unregister本身只是撤销尝试。已读[测试](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Runtime/tests/System.Threading.Tasks.Tests/CancellationTokenTests.cs#L1560-L1745)用同步屏障证明其设计意图：callback未退出前DisposeAsync结果不完成，并覆盖UnsafeRegister的ExecutionContext行为。测试未执行。[R09-S02、T01]

NativeWeave内部取消handler不需要捕获调用者ExecutionContext，采用static UnsafeRegister；应用continuation的ExecutionContext由正常Task机制维护。若领域callback需要特定context，它必须明确选择，不把内部线程环境偶然传播给用户。

## 5. Task链路：异步continuation并非回收屏障

[`TaskCompletionSource_T.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/Tasks/TaskCompletionSource_T.cs)将creation options交给Task，TrySetResult/TrySetCanceled进入Task状态转换；竞争完成还可能等待另一完成过程结束。它管理应用结果，不知道native句柄、cookie或pin的寿命。[R09-S03]

[`Task.FinishContinuations`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/Tasks/Task.cs#L3570-L3715)交换完成哨兵并根据RunContinuationsAsynchronously等标志选择是否内联。该选项阻止当前完成线程内联应用continuation，但不能阻止另一线程在native回调返回前开始执行。由此不能推导“排到线程池以后释放就一定安全”。[R09-S04、D01]

我们不把Task.TrySetCanceled与Token.IsCancellationRequested绑定成即刻释放：数据库写入可能已被接受、服务器响应可能已发送，取消只是竞争中的请求。Success与取消竞争时可合法返回Success；TIMEOUT也不能被覆盖成Canceled。错误领域必须单独记录Effect=Unknown等知识状态。

## 6. YAHA链路与借用数据的结束点

managed初始化RequestContext、Allocate cookie后调用[`yaha_request_begin`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs#L483-L725)。Rust保有Arc request state并spawn异步工作，select cancellation与请求；body frame先调用managed on_receive，再await oneshot确认。managed[`OnReceive/CompleteTask`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L464-L625)把背压完成/失败回传给native。[R09-S05、S06]

正常on_complete调用之后Rust仍设置completed状态；因此应用收到完成不能推断调用方原生帧已不访问对象。RequestContext另有GCHandle释放、native handle release和finalizer策略；NativeWeave只复用“分离这些义务”的思想，不采用依赖特定宿主终结器阻塞的策略。

本轮没有完整审计YAHA ResponseContext、Tokio内部或所有内存借用，因此不据局部调用点宣布其全部buffer生命周期正确。我们的通用v1进一步收紧：callback内只复制借用，owned result通过单独typed take；Server块流由其credit/ack协议进一步定义。

## 7. 启动、结果与关闭的精确偏序

D06规定先预留配额与owner包装，create成功后初始化context/TCS/GCHandle，再注册取消。start拒绝必须没有work和callback；start一旦接管，无论同步成功或失败，都返回OK并通过唯一terminal通知业务结果。start调用lease在native返回以前持续有效。

terminal记录不执行用户代码。完成协调器预先准备托管结果包装与预算，以内部lifetime capability调用take；OK时native归零对应owner，失败时out为空且native仍owns。第二次take返回INVALID_STATE。未取结果由operation release处理。Owner Closing不能挡住处理已接受操作的内部take/retire；它只关闭普通外部准入，协调器是唯一最终回收者。

清理完成必须同时成立：registration已发布且从外部DisposeAsync结束；start返回；普通控制lease为0；native try_retire OK；managed callback数0；结果已发布或失败处置；所有协调器native调用返回。之后才Free GCHandle、释放输入lease和operation owner。native Retired与result Taken是正交状态，退休后、release前仍可take。

所有终态、Owner关闭和超时等待都合并到已有cleanup slot。丢弃Task不会阻止自动清理operation；但应用持有或忽略已返回OwnedResult仍要遵循其Dispose/最终释放责任，不能声称自动取消用户结果的拥有权。[R09-D01]

独立交叉审查补实两条失败路径。D06逐阶段补偿表明确NoRegistration、StartSkipped/Rejected/AcceptedReturned与Indeterminate：完整context尚未建立时直接回滚，未发起的步骤不等待永远不会发生的事件，不明接管则隔离而非假设安全。terminal callback普通失败使用预分配binding-failure latch，finally仍唤醒既有slot，managed Faulted但保留native状态/effect，不要求native违反唯一终态再发一次Failure。这两项是设计修订；当前模型没有覆盖所有初始化失败或latch故障，AS-02/03与正式故障注入继续pending。

## 8. 本轮实际执行的有限模型

运行命令在Design仓库根为：

```sh
python3 docs/research/topics/R09/retirement_model.py
```

实际环境为Python 3.12.14、Linux x86_64，退出码0。代码[retirement_model.py](retirement_model.py)，原始[stdout](model-stdout.txt)、[stderr](model-stderr.txt)、[结果](retirement-result.json)及带时间、命令、hash的[run记录](model-run.json)均已保存。模型在首个Git提交前运行，run明确`source_commit=null`、基线commit和精确模型SHA256；没有虚构旧commit已经含有新代码，也没有把研究run冒充产品验收manifest。

| 模型 | 可达状态 | 探索转换 | 检查反例 | 无检查违例的Reclaimed状态 |
| --- | ---: | ---: | --- | ---: |
| 全部guard | 541 | 1552 | 无 | 8 |
| 删除start-return guard | 549 | 1560 | access_after_free | 12 |
| 删除control-lease guard | 553 | 1568 | access_after_free | 16 |
| 删除registration-drain guard | 565 | 1576 | cleanup_success_without_managed_registration_drain | 8 |

使用广度优先遍历，分支在首次检查违例处停止。正例检查释放后访问、重复Task发布、重复free和无registration drain却宣告cleanup成功。结果中列出全部最短反例轨迹。[R09-M01]

start负例为：注册完成→进入start→commit→native terminal callback进入/通知/返回→managed发布Task→关门→取消注册排空→native退休→回收→start帧继续访问并返回。control负例为：有效控制调用已取得lease→清理忽略lease提前free→该调用访问operation。二者都说明native静默不足以涵盖managed主动调用的栈帧。

registration负例为：取消callback已进入→未启动取消路径→native可退休→若跳过managed drain却宣告DisposeAsync成功。**这证明清理契约不满足，不能自动称为native UAF**：取消delegate仍持有managed state，且原子准入门可阻止迟到native调用。报告保留这一细分，避免夸大负例。

### 模型的精确假设和限制

仅一个operation、一个native terminal callback、一个取消registration/invocation和一个可选ordinary control call；每一步是原子、顺序一致。模型信任start拒绝无义务、终态提交正确、native retire真的封闭未来callback以及lease准入原子性。它不是这些条件本身的实现证明。

不证明活性、公平性、shutdown死锁、弱内存、真实GCHandle/FFI/AOT、多操作、多callback、pool/ABA、计数溢出、result owner转移、pin、OOM或panic。candidate存在8个成功回收状态只排除“完全不可回收的空洞正例”，不证明所有调度最终回收。单一终态的正确提交被抽象为协议事件，重复恶意通知仍须真实故障注入。

## 9. 候选比较与成本

| 选择 | 正确性与体验 | 成本与决定 |
| --- | --- | --- |
| TaskCompletionSource | 多await自然、终态发布清晰 | 每op分配；v1采用 |
| pooled IValueTaskSource | 可降低部分分配 | token/version、复用、误await与迟到callback复杂；当前无收益证据，不默认 |
| callback push | 直接通知就绪 | 需要cookie静默；本轮采用固定通知加独立retire |
| poll/wake ABI | 可将执行权统一到调用侧 | waker注册、丢wake、公平性和额外轮询仍需协议；作为未来证据驱动profile |
| 一次FFI启动并交付handle | 少一次调用 | 同步callback早于managed handle初始化需更复杂协议；v1两阶段 |

成本账本必须含create/start/take/retire/release FFI、GCHandle、context/TCS、input复制/pin、调度队列、native引用和未退休bytes。不能把统计仅局限业务Task时长。高频短工作先用同步/批量API，池化优化有完整负载收益再引入。

## 10. 验证任务、未决和关闭范围

D06 AS-01～08分别覆盖注册同步取消、start拒绝/同步完成、终态竞争、在途lease、一次take/结果转换失败、协调饱和/无进展、多await/ExecutionContext、Windows/Linux AOT与长负载；映射A04/A07/A08/A14/A15/A18/A19/A20/A21/B22。实现时需将状态机动作与实际CAS/lock/acquire-release语义逐项对应；使用适合目标的调度/属性/模糊工具验证，不能只列Loom/Coyote名称。

Q05已有明确Task与不默认池化选择；Q04已有资源退休偏序与可复现实验，可经独立审查关闭设计研究问题。R12执行器、R10 Buffer和R15弱内存进一步补证保持各自范围；不要求此轮先实现所有平台才能记录设计已解决。Tokio/UniFFI及ValueTaskSource内部未读，因此整体研究任务仍partially_evidenced，不能标全部async生态调查完成。

独立审查特别检查：Owner先关门后terminal/take、Task永不await、registration回调先于赋值、PENDING通知合并丢唤醒、永久不静默时配额和诊断，以及效果未知的数据库取消。dotnet/runtime和YAHA固定许可证均已读，为MIT；本报告不复制大段源码。

## Current completion review — source alternatives, real take-once and notification progress

The existing retirement model and its541-state result remain historical evidence. This increment actually executes synchronous/native-worker terminals, precancel and late cancel, duplicate completion rejection, once-only result take, result survival after operation release and DTO-conversion cleanup. Thirty-two controlled callback/GC rounds plus managed registration barriers execute normally and as Linux Native AOT. It is a bounded research operation, not the full future A07 coordinator. Exact evidence is `verification/interop-completion/linux/result.json`.

Previously unread alternative mechanisms are now inspected. .NET11 ManualResetValueTaskSourceCore has a short version and requires the outer owner to prevent access across Reset; version checks and single-continuation enforcement do not make a native cookie safely reusable. UniFFI's actual WrappedFuture separates poll, complete and free; its scheduler handles wake-before-store and calls callbacks outside the internal mutex. Its Arc-backed RawWaker retains future state. These mechanisms support keeping ordinary Task/TCS as the simple initial C# contract and deferring pooling until workload evidence justifies the additional ABA/reset/await rules.

The new finite mailbox model supplies a concrete lost-notification counterexample: worker reads no dirty work, notification marks dirty while scheduled remains true, worker clears scheduled using the stale read. Atomic dirty recheck/unschedule removes that counterexample in the declared finite SC model; exact negative17/candidate11 states and source hash are preserved. D09 specifies the matching bounded mailbox and pending-retirement retry rule; it does not claim a weak-memory proof.

The old preview-only Runtime Async statement is historical and superseded by R01/D01's current .NET11 check. This bridge uses ordinary Task and does not require a runtime-async-specific ABI. Current source/design questions are resolved with the above evidence. Independent review remains required; full setup-allocation compensation, poisoned-worker recovery, multi-operation saturation, every target and production weak-memory/load behavior remain explicit A07/A08/A19/A20/B22 obligations.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
