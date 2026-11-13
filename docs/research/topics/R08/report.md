# R08：Callback注册、重入、停止与静默

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

日期：2026-11-12。作者：interop_design。状态：**partially_evidenced；design decision recorded；independent review pending**。本轮在既有任务中深化真实源码并形成[D05 callback契约](../../../contracts/callback-v0.1.md)，不是新的协调规划，也不是产品实现验证。

## 1. 固定输入与问题

Design基线`1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan基线`da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。R08 revision `0.1.1`，packet SHA256 `690b702013f788e3c99144467a6c8157f313b1f5a5bdd398b87fad44c927d36a`；D05 revision `0.1.1`，hash `e493b0ba781d216860587eb6f8e46bc809bba78549733b92e9439c79d349cdbb`。均与固定远端图及实际packet字节相符。

需要同时保证：外来native线程可通知managed；注册后立刻同步callback也安全；Dispose可以在callback内调用；停止不丢已在途回调；cookie不会被迟到回调解释为另一对象；所有普通异常停在语言边界内。非目标是用managed校验恢复任意伪造指针，或强迫GUI、TLS决策和普通通知具有相同线程模型。

**v1选择create/start分离、非阻塞request_stop、独立try_retire、显式调用lease和callback外清理。** 停止请求不承诺已静默。普通通知先复制借用数据/记录固定终态，再交有界managed协调器；同步决策callback仅用于明确需要即时返回的profile，并禁止同步等待自己的关闭。见D05具体接口与[D06](../../../contracts/async-v0.1.md)结果协议。

## 2. 源码覆盖与分类

| 来源 | SHA | 此轮直接阅读 |
| --- | --- | --- |
| Godot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | SignalAwaiter、signal_awaiter_utils、ManagedCallable、GCHandleBridge |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | C# callbacks、RequestContext、SafeHandle、Rust begin/body/complete/abort、TLS lifetime测试 |
| .NET runtime v11 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | CancellationTokenRegistration的unregister/drain与其测试 |

路径、符号、已读行范围与blob SHA在[evidence.json](evidence.json)，没有阅读的Godot信号分发内部和Qt for Python列在[coverage.json](coverage.json)。新增.NET来源用于核实managed取消callback静默，理由与本题直接相关。上游测试均只读未运行。

## 3. Godot调用链：强根、one-shot与返回前复制

[`SignalAwaiter.cs`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/SignalAwaiter.cs)的构造创建强GCHandle并传给native connect。UCO SignalCallback从handle取回awaiter，把借用Variant参数复制到managed数组，设置完成并调用continuation，普通异常由本地catch/log处理。[R08-S01]

[`signal_awaiter_utils.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/signal_awaiter_utils.cpp)把handle放入SignalAwaiterCallable，连接ONE_SHOT信号；call到managed SignalCallback；callable析构释放awaiter handle。[`managed_callable.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/managed_callable.cpp)也有显式delegatehandle检查与析构释放，经[GCHandleBridge](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/Bridge/GCHandleBridge.cs)回到managed free。[R08-S02、S03]

可复用的是“注册对象拥有强根”和“借用参数在callback内转为自己的数据”。不照搬的是inline continuation：NativeWeave普通异步通知不能在任意native线程同步运行用户await后代码。ONE_SHOT只描述逻辑订阅次数，不能单靠名称证明销毁并发、最后call返回或managed取消callback已排空；本轮没有读完Godot Object signal dispatcher，不声称其全局静默已经证明。

## 4. YAHA调用链：完成通知后native栈仍可能访问状态

[`NativeHttpHandlerCore.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs)初始化RequestContext并Allocate cookie，调用native begin。OnReceive接收借用body数据，WriteAsync背压未完成时注册continuation，完成后通过CompleteTask归还一个native任务通知。OnComplete读取响应/错误信息，完成managed响应；finally释放RequestContext cookie，再把Dispose排到managed线程池，注释明确不能直接在native线程释放这些handle。[R08-S04]

对应[`binding.rs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs)在body frame处建立oneshot，调用managed on_receive后await确认；失败转为on_complete Error。正常末尾调用on_complete之后，仍会锁request并设置`completed=true`。这是“逻辑终态通知不是native调用栈已退出”的具体源码实例。[R08-S05]

此观察**不等于判定YAHA当前实现有UAF**：其引用、调度和其他上下文必须整体考虑。它意味着NativeWeave不能把“队列到了managed线程池”或“Task完成”当作普遍静默证明。线程池工作可能比native回调返回更早执行；本项目选择显式try_retire和start/control lease屏障，减少隐含调度假设。[R08-D01]

TLS verification是另一profile：返回bool需要同步作决定，普通handler异常转为false。其生命周期测试用延迟握手、Dispose与GCHandle替代分配暴露错误目标调用的风险；本轮只读测试，未执行。NativeWeave据此规定decision callback异常fail-closed，并把所有可能抛出的转换/日志/退出动作也放在边界策略内，不能只包住用户delegate。[R08-T01]

## 5. managed取消注册也有自己的静默条件

[`CancellationTokenRegistration.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenRegistration.cs)的Unregister只是尝试移除注册；Dispose/DisposeAsync在需要时等待已经执行的callback，且存在当前callback自身的特殊处理。已读测试用屏障阻塞callback并验证DisposeAsync在callback被放行之前不完成。[R08-S06、T02]

因此native try_retire成功仍不能替代managed取消registration drain。cleanup必须从native与取消callback之外进行，在注册句柄已发布后DisposeAsync，再等待native/control条件。若回调内DisposeAsync等待同一callback退出，形成自等待；同步Dispose只标记Closing/请求停止，返回。若API暴露必须等待的DisposeAsync，同一同步callback scope内应给明确InvalidOperationException或领域规定的禁止用法，不能悄悄报告已排空。[R08-D02]

## 6. 必须可检验的反例与线性化点

迟到cookie反例：T1注册handle H；T2请求停止并立即Free(H)；T3分配新context复用H；native已排队的旧callback到达，`GCHandle.FromIntPtr(H).Target`得到新对象。检查非零或非null不能分辨身份，甚至可能调用另一证书验证器。修复不是在解引用后比较对象，而是保证任何callback可能到达时H始终属于原context，并在永久禁止新callback且所有在途退出后释放。[R08-D01]

第二个反例来自[R09真实执行模型](../R09/retirement-result.json)：同步terminal已返回、native try_retire成功，但start入口尚未返回。若略过start-return lease，managed释放operation后native start仍访问它，模型产生access_after_free。第三个反例略过普通control lease，也产生释放后访问。模型没有模拟恶意native、不正确retire、真实GC或内存屏障。[R08-M01]

| 动作 | 线性化点与保证 |
| --- | --- |
| start提交 | callback table与cookie已复制/绑定；之后终态/事件义务由native接管 |
| start拒绝 | 仍Created；没有work/callback留存；caller可补偿 |
| stop请求 | 原子标记不再接受新增业务/事件来源，允许在途退出 |
| callback admission | 与关闭来源同一同步协议下增加in-flight义务；不能先检查再无保护递增 |
| native try_retire OK | work与callback义务为0，未来不能再进入callback；尚未必可释放外部调用帧 |
| managed Reclaimed | start已返回、取消注册已外部排空、调用/回调数0、结果处理结束，一次性归还owner |

## 7. 候选与实现边界

同步drain简单但在reentrant Dispose、线程亲和和执行器shutdown里容易自等待，不能是通用Dispose语义。generation token只能检测部分复用错误，不能证明旧callback不再执行或借用数据仍活着。事件队列可以隔离用户代码，但增加复制/调度，并需要预留容量；它单独不能证明native静默。v1采用异步quiescence与显式lease，普通通知经有界协调器，decision profile保留极短同步返回。[R08-D01]

D05给出的wire为`uintptr_t cookie`、静态Cdecl函数指针、u32状态、call范围借用payload；结构大小按D02目标ABI计算。通用notification不从callback隐式移交owned对象，异步result通过D06 typed take完成。Rust内部必须让每个排队/活动任务持有state引用；callback之外的cleanup在释放cookie前核对实际静默。没有把GCHandle cookie解释为Rust指针。

## 8. 验证、成本与AOT

正式任务A06/A07/A18/A19/A20覆盖D05 CB-01～07：注册同步触发、回调内Dispose、外来线程异常、双通知、停止与准入竞争、最后callback暂停、GCHandle复用负例、控制调用与start尚未返回、取消registration未排空、模块卸载。对需要即时决策的profile验证fail-closed、无同步等待和明确线程亲和。

独立交叉审查指出native静默不覆盖已经排到managed dispatcher的handler。本轮据此把D05细化为独立DispatchClosing：显式Dispose丢弃pending并归还其拥有数据、禁止新handler开始、等待active异步handler实际结束；成功DisposeAsync保证本订阅handler也已排空。该补充为设计推断与审查修订，R09有限模型没有模拟dispatcher，真实用例保留CB-03/A06/A18。

每个accepted异步操作预留完成/cleanup slot，通知合并且callback不等待入队；不能使用bounded queue外加无界持payload等待者。测量callback延迟、复制字节、排队长度、跨FFI次数、cleanup P99、最大retained bytes和静默长期停滞。普通同步API不必启用该协调器。

AOT要求静态、非泛型、精确blittable UCO签名；C#/Rust bool不直接进入wire。Windows/Linux Native AOT、真实竞态、GC压力和fatal subprocess均尚未运行。Python模型只验证抽象偏序，不能写成UCO或ABI已通过。未来GUI/移动端线程亲和是单独profile，无需重写通用stop/retire语义。

## 9. 结论与独立审查

Q04的callback回收策略已可做design-resolved审查；生产验证保留。R07审查cookie/parent/module寿命，R09审查同步start和托管取消注册屏障，R12审查协调器进展、线程亲和和shutdown，R15审查原子准入与真实内存模型映射。需要独立审查者特别尝试：Owner先Closing随后terminal需要take的顺序、callback内Dispose、无await的Task以及poison后排空。

Qt for Python和Godot dispatcher深层未读，故报告整体保留partially_evidenced。MIT来源许可证已在固定SHA读取；无上游测试运行，无源码大段复制。后续补查应针对这些具体证据缺口，不能因一个来源未读而停止其他独立设计。

## Current completion review — real reverse callback and managed registration drain

The original callback/source report and finite model are preserved. The new interop-completion fixture now actually invokes static managed UCO from a Rust-created native thread, holds a controlled callback barrier, requests retirement/cancellation concurrently and forces GC. Retirement stays pending while the callback is active; after permanent native completion and all test calls return, the cookie is freed. An ordinary callback mapping exception is caught and recorded before returning across FFI. Thirty-two rounds execute in normal and actual Linux Native AOT modes; raw evidence and precise source/binary hashes are in `verification/interop-completion/linux`.

The same fixture observes an already-cancelled token's UnsafeRegister callback before registration publication and verifies DisposeAsync remains incomplete while another callback runs, then completes after that callback exits. This closes the previously source-only registration-order experiment. It does not claim arbitrary invalid-cookie probing is safe or that a test barrier is appropriate production callback behavior; production callbacks remain short/nonblocking.

New UniFFI scheduler source at `482095c1ba1b76a1393b582e0589e2fdc9c64b14` invokes foreign continuations outside its mutex and stores wake/cancel state when no continuation is installed. Its callback/free semantics are deliberately not substituted for NativeWeave's no-future-callback retirement requirement. The alternative is now source-inspected rather than falsely listed as universally unexamined; exact read limits remain recorded.

D05/D06/D09 provide stable cookie, source closure, native quiet, managed start/control/callback/registration drain and bounded dispatcher rules. Existing Godot/YAHA evidence already suffices to compare ownership hazards; Qt is not an adopted runtime dependency and its broader source audit is outside this selected C# ABI design. Product notification subscriptions, many concurrent operations, allocator failure and two-OS long-load tests remain A06/A07/A20/B17 implementation obligations. Research/design acceptance awaits independent review of this new scope, not completion of the product.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
