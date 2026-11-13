# C-LIFETIME-001：所有权、资源租约与回收协议

版本：0.3.0。任务：D04；研究：R07–R12、R15/R16的完成证据。作者：interop_design。状态：**研究/设计候选已完成；registry记录精确审查版本、内容hash与接受状态；产品验证保留在Delivery阶段**。本文件选择v1协议；研究切片已有明确真实并发与Windows/Linux Native AOT证据，完整产品实施/平台/生产验收仍单独记录。只由整合者在独立审查后更新registry，不由作者自行接受。

## 1. 目标与非目标

应用层获得自然的C#资源对象、确定性Dispose/DisposeAsync和取消行为；内部按每个Engine的真实需要管理native所有权。Database / ORM / Server核心底层必须Rust；不需要异步调度的Engine不启动native runtime。资源管理不能依靠调用者记住裸指针有效期，也不能让一个同步压缩函数承担异步服务器的全套调度成本。

本契约定义身份、拥有/借用、调用准入、父子引用、跨异步租约、回收条件和关闭责任。它不定义数据库事务已经提交/回滚，也不将native内存静默等同于连接可返池。进程内native代码是同一信任域；本协议不承诺隔离恶意native代码或修复任意内存破坏。

## 2. 设计决定与候选比较

**v1选择：private opaque pointer + 每种资源的SafeHandle + 明确调用准入 + 按需异步租约。** 普通业务API不暴露`nint`、GCHandle或native allocator。所有权信息进入唯一ABI描述，生成器发射匹配释放路径。

| 候选 | 收益 | 成本/缺陷 | 决定 |
| --- | --- | --- | --- |
| 每个操作都使用全局代际句柄表 | 可拒绝部分陈旧身份；适合显式复用/不可信整数句柄边界 | 查表、同步、额外间接访问、generation溢出与table生命周期 | 不作为通用v1默认；对池化或跨进程身份另立profile |
| opaque pointer + SafeHandle | .NET已有拥有/最终释放机制；native布局完全私有 | SafeHandle不解决逻辑关闭、native异步留存和callback静默 | 采用，并补充本契约的独立职责 |
| 仅托管对象引用或GC.KeepAlive | 低表面复杂度 | 显式Dispose仍可与使用竞争，不能自动保护native异步任务 | 不能作为单独安全机制 |
| 每次API调用native retain/release | 可支持多个native owner | FFI和原子操作增加；本就同步借用的调用付出额外成本 | 仅共享/跨异步所有权需要时使用 |

先采用可审阅的managed短临界区保护准入；以后若真实性能证据需要，可在保持同一线性化语义下替换为计数+关闭位的CAS协议。禁止只为了无锁而引入更复杂的回收机制。

## 3. 实际源码依据

[R07报告](../research/topics/R07/report.md)记录固定SHA与行段。.NET11 `SafeHandle`把引用计数、Closed、Disposed放在同一状态字中。`DangerousAddRef`检查Closed，但未以Disposed位禁止所有新引用，因此当其他lease仍存在时，应用逻辑关闭需要自己的准入门。`DangerousGetHandle`只读取地址；单独调用它不会取得使用期引用。

Godot的托管对象、refcounted对象、signal awaiter和managed callable分别维护拥有、关联GCHandle、对象身份与释放；这些现实机制说明不同资源关系必须显式表达。其完整引擎对象模型、反射和热重载不作为NativeWeave公共运行时。YAHA的父引用、活动请求和TLS回调生命周期测试提供真实反例场景；其Unity终结器等待不作为本项目默认策略。

## 4. 三种身份与所有权

| 对象 | 表达 | 权威与有效期 |
| --- | --- | --- |
| native拥有资源 | 私有`nw_<engine>_<kind>*` | 由创建该资源的Engine释放；SafeHandle拥有一个release权 |
| managed callback context | `uintptr_t cookie` | 由managed创建的强GCHandle标识；native只原样保存/回传，绝不解引用其位值 |
| borrowed data | D07的pointer+length或领域typed view | 仅在声明的调用/回调范围内；异步留存需另有owner lease |

每次create成功只交付一个拥有权；失败时out pointer为null。共享所有权使用明确的clone/retain操作或native内部`Arc<State>`，不能以复制指针伪造第二owner。v1不提供公共Detach裸句柄；若特殊互操作profile需要，必须单独定义原子转移与接收者责任。

所有权保持创建器与释放器配对：不能用C# FreeHGlobal释放Rust Box/Vec，也不能用另一个Engine的release函数释放当前Engine资源。模块加载引用必须至少活到最后一个函数指针调用、callback和资源释放完成。

## 5. 准入门、调用租约与线性化点

资源至少具有`Open / Closing / Released`逻辑状态。Open→Closing是新的业务调用停止被接受的线性化点。每次调用在同一同步协议下完成“检查Open并取得SafeHandle引用”；随后在锁外执行FFI，finally释放引用。Dispose在同一门下置Closing，再在锁外释放owner引用。

下面是**未编译的实现骨架**；生成器应生成等价的try/finally，不把可复制的value-type lease暴露给应用：

```csharp
internal unsafe int InvokeGenerated(int argument)
{
    bool lease = false;
    try
    {
        nint pointer;
        lock (_admission)
        {
            ObjectDisposedException.ThrowIf(_closing, this);
            _handle.DangerousAddRef(ref lease);
            pointer = _handle.DangerousGetHandle();
        }
        return _api.Invoke(pointer, argument); // generated exact C ABI
    }
    finally
    {
        if (lease) _handle.DangerousRelease();
    }
}

public void Dispose()
{
    lock (_admission)
    {
        if (_closing) return;
        _closing = true;
    }
    try { RequestStopIfApplicable(); } // no wait or user callback under gate
    finally { _handle.Dispose(); }     // active leases delay physical release
}
```

骨架中的`RequestStopIfApplicable`不能取得已被关闭的普通业务准入；必须使用预先持有的内部关闭能力/owner引用，且异常路径仍执行拥有权释放。正式实现要把该方法和错误路径展开验证，不直接复制这个省略实现的示例。关闭标志判断与DangerousAddRef不能拆成两个无同步步骤。

## 6. 父子资源与独立Engine

默认：一个成功创建的owned child持有其需要的native parent state引用。父包装对象Dispose拒绝新的父业务调用和新child创建，但已有child的合法访问由自己的owner/lease保持。若某领域定义级联取消，应在其API明确标为cascade，并提供异步drain；不能仅靠managed parent变量仍可达保证安全。

Rust实现可把对外opaque owner放在独立Box中，child持有内部`Arc<ParentState>`；每个Engine可以使用自己的等价引用机制。C#的一个parent SafeHandle长期DangerousAddRef也可实现同样关系，但所有失败/释放分支必须配平。v1每种child只选一个权威父lease机制，避免managed与native两边互相持有造成不可回收环。

父state的内存存活不表示父对新业务仍Open。线程亲和资源的最后释放必须交给所属线程/执行器；SafeHandle终结器线程不能直接调用任意GUI/GPU析构。

## 7. 异步资源及GCHandle

异步操作持有自己需要的owner lease、输入内存lease、callback context强引用以及模块函数表引用。它们直到D06的退休条件成立才释放。托管Task成功/失败/取消是应用可见结果，资源退休是另一状态。

GCHandle采用Normal强引用；它固定目标的可达性，不固定对象地址。native只持有cookie，不能把cookie当作managed对象指针。需要稳定native data地址时用D07明确的pin/owned copy，不从GCHandle的存在推导已经pin。

GCHandle可复用，因此“句柄值非零”或`Target != null`不能辨别迟到callback是否指向新的对象。v1通过禁止退休后的callback、确保全部在途回调退出、避免操作context池化来消除正常路径上的复用窗口。代际token只是额外检测，不能替代静默协议。

## 8. 回收不变量

对每个资源r与操作o：

- `free_count(r) <= 1`。
- `native_access(r) => live(r) && valid_owner_or_lease(r)`。
- `Closing(r)`后新的普通业务准入失败；先取得的租约仍可完成。
- context回收需要：native已永久关闭callback来源并确认静默；所有managed callback退出；setup明确完成（start返回或从未调用的哨兵）；取消注册已外部排空或明确NoRegistration；在途control-call lease为0。notification订阅另排空/丢弃managed pending队列并等待active user handler结束。
- 所有借用输入、result和callback参数的释放遵从其自己的ownership终点，不能因Task发布而提前归还ArrayPool或解除pin。

这里`native_obligations`只描述仍会访问当前资源内存或必须在该资源上执行的本地工作。数据库远端提交效果Unknown可以在独立恢复记录中继续存在；它不自动阻止本地安全回收。连接是否可返池由数据库协议另行确认。

## 9. Dispose、DisposeAsync与终结器

同步资源的Dispose可直接完成非阻塞release。异步资源/订阅的Dispose关闭准入并请求停止，返回时允许原生清理仍在进行；公开文档必须说清。**成功完成的DisposeAsync保证本对象规定的callback、取消注册、控制调用和native资源清理均已完成。**

`CloseAsync(CancellationToken)`若提供可取消等待，取消只停止调用者等待；后台清理继续持有全部必要资源，不能强行free。没有进展时应暴露cleanup age、outstanding leases/bytes、pending retire和最后阶段，限制新准入，必要时poison Engine。不能让超时成为内存不安全的释放许可。

终结器不等待native工作，不运行用户代码，不阻塞执行器关闭。异步context由正在进行的操作/cleanup协调器强引用；终结器只可请求非阻塞停止并把已有拥有权交给预先存在的清理路径。若执行环境已经无法推进，保守保留/隔离资源并记录诊断；不能声称仍保证活性。依D02，v1 native模块保持加载至进程退出，实例关闭不卸载库；未来若提供热卸载，需单独证明无活动资源、函数指针、线程与回调。

## 10. 成本、现代C#与平台

同步热路径成本为一个准入临界区、SafeHandle AddRef/Release、一个FFI调用；无每次GCHandle、全局表或必需native scheduler。异步操作使用一个稳定context及一次GCHandle，实际分配与TCS数量由D06记账。Span/ReadOnlySpan可表达同步借用，不能越过异步留存边界。

初始真实验收目标为win-x64、linux-x64；指针宽度和自然对齐按D02目标矩阵验证。future Arm64/mobile/线程亲和profile不能套用桌面finalizer假设。函数表静态签名与生成元数据支持AOT；本文件没有实际C#/Rust编译结果。

## 11. 实施与验收映射

| 验证ID | 场景与判定 | Delivery |
| --- | --- | --- |
| LT-01 | 调用取得lease与Dispose并发：旧调用完成，新调用拒绝，free恰好一次 | A03、A20 |
| LT-02 | 父关闭时child仍活动；创建失败、双Dispose、最后child释放 | A03、A17、A18 |
| LT-03 | GC压力、终结器、模块卸载；不得调用已卸载函数表或阻塞终结器 | A14、A15、A18 |
| LT-04 | Task已完成但callback/控制调用/start尚未退出；buffer/context不得先释放 | A07、A19、A20 |
| LT-05 | 迟到callback、GCHandle复用、错误release函数，隔离进程负例 | A06、A20 |
| LT-06 | 长期取消/失败/关闭循环，稳定基准后资源计数回到预期界限 | A21、B22 |

测试需要真实Windows/Linux AOT消费端、固定源码与二进制hash、原始日志、竞争种子和超时。R09有限模型仅支撑抽象协议；真实SafeHandle、内存模型、FFI与线程亲和仍由这些任务证明。

## 12. 决定状态

Q04的资源安全设计部分可以在独立审查本文件、D05与D06后记录为design-resolved；本地内存静默与远端效果区分已明确。对应实施和生产验证保持pending。Q02中私有指针与代际表的v1选择已有明确建议，其完整ABI接受由D02及独立审查负责。


## Supplemental execution evidence — logical admission only

This non-normative update does not change the v0.1.0 admission protocol or accept the contract. The earlier uncompiled skeleton is now complemented by an equivalent synchronous research facade in `experiments/logical-admission/Program.cs`, tested at Design28f6cf7e6e4e80b9f32a92ad587a528d82911bd0/run43373306474. Both Windows/Linux passed normal and actual AOT runs with653 assertions and64 controlled gate/Dispose rounds each. The original SafeHandle-only facade admitted a new call while an old lease remained; the explicit Open/Closing gate rejected it while allowing the old call to complete. An injected managed failure returned its acquired reference.

See [R07 detailed study](../research/topics/R07/logical-admission.md) for exact source, traces, operation ordering, mutation-lock separation and future Codex test cases. The compiled fixture has no RequestStopIfApplicable, async callback, parent/child, finalizer or module-unload implementation, so those parts of this contract remain unverified by it. Keep native query mutation guards separate, avoid callbacks/await under them, and do not rely on Mutex poisoning for unsafe memory soundness. Research experiment success is not formal A03/A07/B11/B17 implementation or independent acceptance.

## 15. 本次完成复核与实现义务分层（2026-11-13）

保留既有 [logical-admission 证据](../../verification/logical-admission/primary-results.json)：它真实覆盖 Windows/Linux 普通与 Native AOT 的同步准入反例。新增 [interop-completion](../../verification/interop-completion/linux/result.json) 在 Linux 普通与 Native AOT 下控制 native worker 回调持续在途，验证 GCHandle 强根、native quiet 前不回收、一次 take、operation release 后独立 result owner 仍可读，以及 managed 转换抛出时 result release。研究 fixture 的私有状态码与部分手写协调代码不能充当产品 D08 ABI 或完整生成 wrapper。

物理 lease、逻辑准入、可变对象单 writer、结果 ownership、Engine/module ownership 仍分别成立。不能用延迟 free 的 SafeHandle 代替 Open→Closing 准入锁，也不能仅凭 Arc 引用计数声称 worker OS thread 已 join。常规模块进程期常驻；特殊 thread-affine owner 采用 [D09](concurrency-v0.1.md) 专用释放调度，finalizer 不同步等待。

R07 已给出完整研究决策和 scope；非选中 Qt/Python 所有权机制不构成当前 C#/Rust 设计的无期限前置。经独立审查可接受本设计；A03/A04/A20/B01 的完整 parent-child、失配 owner、长期竞争、弱内存、资源归零与产品 package 测试仍是独立义务。


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
