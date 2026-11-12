# R07：拥有权、SafeHandle、GCHandle与父子资源

研究日期：2026-11-12。作者：interop_design。状态：**partially_evidenced；v1 design decision recorded；independent review pending**。本报告给出可审查的实现选择，不代表真实产品、全部来源或生产平台已验证。

## 1. 输入与交付边界

共同基线为Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`、Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。远端固定Plan图的R07 revision为`0.1.1`，本地packet实际SHA256与图一致：`e983236fed611d62a949927a5d1a14a4189e4338ae5da884df984e7a813015f8`。配套D04 packet为`0.1.1`，hash `75c6ccd848ed543a3eae0a2738ca1097a62959621c5b764565d3a5f10fe2ed02`。

本轮只完成资源身份、有效调用、父子拥有与回收设计；Buffer具体布局由D07负责，callback和异步清理分别由D05/D06负责。ArcForges仅为格式参考。没有产品源码实施、上游测试执行或C#/Rust/AOT编译结果。

## 2. 需求、非目标与决定

应用必须获得自然的C#资源对象，Dispose可拒绝新调用，已经合法开始的调用不能因为并发Dispose而访问释放后的native对象。父包装关闭后，已有child所需的parent state必须仍活着；共享所有权与借用不能通过复制指针混为一谈。GCHandle只能用作回调cookie的强根，不能同时充当pin、句柄合法性检测和防ABA方案。

**v1采用private opaque pointer、SafeHandle单一owner、独立managed准入门和显式调用/异步lease。** 普通公开API不暴露`nint`；同步热路径不分配GCHandle，不经过全局句柄表，也不启动统一native runtime。特殊复用/跨进程身份才引入代际token，不能据此省略静默协议。完整规范见[D04](../../../contracts/lifetime-v0.1.md)。

非目标包括隔离恶意native代码、修复任意内存破坏、把本地静默等同数据库远端效果已知，以及以一个实现强制所有Engine拥有相同线程或runtime。

## 3. 固定源码与实际覆盖

详细逐项定位与blob SHA见[evidence.json](evidence.json)，已读/未读清单见[coverage.json](coverage.json)。本轮读取以下固定快照，不使用浮动分支支持技术结论：

| 来源 | 固定commit | 实际追踪 |
| --- | --- | --- |
| dotnet/runtime，v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | SafeHandle状态字、AddRef、InternalRelease和测试 |
| Godot，2026-11-11 master快照 | `069458825a8e4a01938a176372c0709ab6fd9dc3` | GodotObject.Dispose、runtime interop、managed callable、signal awaiter GCHandle |
| YetAnotherHttpHandler | `c386c1cc48d2e56711c15286cf2769353fdccf07` | SafeHandle parent引用、RequestContext根与release、TLS callback复用负例测试源码 |

Godot快照用于调查机制，不是NativeWeave选择依赖Godot，也不是声明该快照为稳定版本。Qt for Python未进入本轮深入阅读；其Python对象所有权和解释器关闭机制仍是候选扩展来源。没有把整个项目列为已读。

## 4. SafeHandle真实链路：逻辑关闭不等于最后释放

[`SafeHandle.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs)的构造器建立初始owner引用；DangerousAddRef通过原子更新增加引用；Dispose进入InternalRelease。引用计数、Closed和Disposed在一个状态字中，最后释放才调用ReleaseHandle。DangerousGetHandle仅取出地址，没有增加引用。

特别影响NativeWeave的事实是：DangerousAddRef拒绝Closed，**没有把Disposed本身作为所有新AddRef的拒绝条件**。若另一个lease尚在，Dispose可以已发生而对象还未Closed。因此SafeHandle是物理存活保护，不足以定义业务API的“Dispose以后禁止新调用”。[R07-S01]

我们据此增加一个短managed准入临界区：在同一锁下检查Open并取得DangerousAddRef；Dispose在同一锁下把状态改为Closing，再到锁外停止业务及释放owner。FFI与用户callback均不在门锁内执行，finally配平DangerousRelease。若将来改为CAS，仍须保持“关门”和“取得租约”的共同线性化点。[R07-D01]

已读的[SafeHandle测试](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Runtime/tests/System.Runtime.Handles.Tests/SafeHandle.cs)覆盖合法/非法handle、重复Dispose、SetHandleAsInvalid，并以AddRef→Dispose→DangerousRelease测试Windows LastError行为。它们没有替NativeWeave执行其并发门、父子协议或真实FFI，不能作为本项目竞态验收。[R07-T01]

## 5. YAHA真实链路：父引用、context强根与释放时点

[`YahaSafeHandles.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/YahaSafeHandles.cs)中context retain runtime，request retain context；释放request先调用对应native destroy再归还parent引用。TLS验证callback的GCHandle由context SafeHandle拥有，在context释放时归还。这是可核查的父子生存链，不是仅靠managed变量指向parent。[R07-S02]

[`RequestContext.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/RequestContext.cs)的构造额外保有request SafeHandle引用；Allocate创建Normal GCHandle，Release归还GCHandle并发出完成信号，native handle则由单独Dispose路径释放。TryAbort在锁下确认context尚活，调用abort期间同时持有context/request AddRef，并用finally配平。该源码明确区分“托管callback context不再需要”和“native handle可以释放”。[R07-S03]

同一文件的finalizer等待native完成，注释将其关联到Unity Domain Reload，并承认锁与调度可能令终结器阻塞。NativeWeave不照搬这个宿主特例：有活动操作时由有界cleanup协调器持有强根；终结器不等待、不能运行用户代码，长期无法静默则隔离并保留资源。[R07-S03、R07-D02]

TLS[生命周期测试](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/test/YetAnotherHttpHandler.Test/CertificateVerificationCallbackLifetimeTest.cs)建立受控握手，在活动请求中Dispose handler，尝试分配replacement callback handle，随后断言未调用替代验证器。测试放在子进程，以免回调异常拖垮测试runner。**本轮读了测试源码，没有运行。** 这给出比“Target非null就安全”更具体的反例与验收形状。[R07-T02]

## 6. Godot真实链路：多种拥有关系不能压成一个bool

[`GodotObject.base.cs`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/GodotObject.base.cs)区分memory owner、native pointer、关联GCHandle以及refcounted/nonrefcounted释放。Dispose释放关联handle前核对当前target仍是this，因为关联可能已被其他线程替换；GetPtr检查disposed与零指针。其反射与完整对象体系不进入NativeWeave Core。[R07-S04]

对应[`runtime_interop.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/runtime_interop.cpp)将不同对象关系交给CSharpInstance或binding helper，refcounted路径在unreference后可能删除对象。我们读到这层适配，但没有继续读完CSharpInstance内部，因此不声称证明Godot所有线程和销毁组合。[R07-S05]

SignalAwaiter构造强GCHandle，native one-shot callable持有该handle并在析构时释放；ManagedCallable也有显式delegatehandle释放路径。这说明回调cookie可以属于native持有的subscription生命周期，而非某一次callback栈帧。[R07-S06] NativeWeave选择显式stop/retire，把“来源不会再调”和“在途调用已经返回”写成契约，避免依赖整个引擎对象模型的隐含保证。

## 7. 候选比较与资源矩阵

| 方案 | 能解决 | 尚须解决 | v1处置 |
| --- | --- | --- | --- |
| opaque pointer + SafeHandle | 单owner、最后释放、managed最终释放后备 | 业务关门、异步留存、callback静默 | 默认基础 |
| 全局generation table | 复用身份的陈旧访问检测 | 表的线程安全、代际溢出、table寿命、仍在访问旧对象 | 仅特殊profile |
| 每调用native retain/release | 独立native共享owner | 两次额外FFI与原子成本 | 跨异步或native共享时按需 |
| managed parent引用 / KeepAlive | 防managed对象过早GC | 不能阻止显式Dispose | 不独立承担native安全 |
| native child持有Arc<ParentState> | 子使用期间parent state存活 | 逻辑关闭、无引用环、析构线程 | 默认父子机制候选，由各Engine落实 |

同步借用只到调用返回；callback payload只到callback返回；异步输入必须复制或持有明确的pin/owned lease；结果owner在typed take成功点才换手。每个资源选择一个明确父lease权威，不能managed与native互相retain形成环。allocator与release来自同一Engine，模块代码必须比最后一个函数指针调用活得久。[R07-D01]

## 8. API、失败补偿与证明义务

公开C#常用方式是`using`管理同步owner、`await using`管理需要完成drain的Engine/operation；不提供普通用户Detach裸指针。D04已有未编译C#准入骨架；D06给出create/start、typed take、stop与retire的精确接口。Rust可以用Box包opaque owner、Arc持有共享state，但`Arc::from_raw`/`into_raw`必须由生成或审查过的拥有权协议配对，不能任意从借用指针制造owner。

create失败out pointer必须为null；SafeHandle包装/GCHandle/取消注册失败必须逐项补偿；parent创建child失败须归还已取得parent lease。Dispose可重复但owner release恰好一次。异步Dispose是请求停止，成功DisposeAsync才表示全部规定的清理完成。

证明义务是`native_access => live && valid_lease`、`free_count <= 1`、Closing后新业务不接受、最后释放时无callback/start/control/cancel注册义务，以及父子释放不调用已卸载代码。R09模型只覆盖其中的抽象退休条件；内存模型与具体实现映射仍待R15/A19/A20。

## 9. 成本、平台与验证

同步基线成本为一个短准入临界区、SafeHandle AddRef/Release和业务FFI；不宣称实际ns值。异步多出context、TCS、GCHandle和cleanup slot，不能把其成本藏进“零拷贝”宣传。父child保有引用降低复制，但会延迟native state回收，必须计量bytes和cleanup age。

初始平台为win-x64/linux-x64。Windows handle LastError、native析构线程与未来Arm64/mobile/GUI亲和性分别验证；不从Linux Python模型推导跨平台安全。C#/Rust骨架均为draft，未编译。交付任务映射为D04 LT-01～06：A03句柄、A06 callback、A07异步、A14/A15真实AOT、A18关闭、A19模型、A20竞态/故障、A21/B22长负载。

正式测试要包含Dispose与准入对撞、parent先Dispose/child后结束、GC压力与重复Dispose、创建中OOM、handle复用负例、线程亲和finalizer负例、模块卸载与最后lease，以及资源计数回到界限。负例中无法保证进程存活的用子进程运行并保存退出码、种子、日志与二进制hash。

## 10. 研究结论、未决与审查接口

Q04生命周期设计已有明确方案，可在D04/D05/D06独立审查后关闭设计问题；Q02私有指针与代际表的选择已提供D02依据。实施验证和生产验收继续pending，不能因此宣称已完成。

R08核对callback内Dispose、cookie最终释放与late-callback反例；R09核对start未返回、取消注册与take_result的lease；R32核对独立Engine parent/module寿命与线程亲和profile。影响文件为D04/D05/D06及对应Plan任务。Qt for Python、Godot完整signal dispatch/CSharpInstance深层实现未读，不妨碍当前建议被审查，但本任务整体保留partially_evidenced，后续可针对真正反例补查，不能标全项目研究完成。

许可证：固定快照的dotnet/runtime、Godot、YAHA许可证均已读，为MIT；证据文件记录其blob。报告为机制转述与新设计，不复制大段上游实现；未来产品复用源码仍须保留适用声明并逐项核查。
