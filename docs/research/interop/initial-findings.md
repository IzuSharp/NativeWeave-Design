# Interop 初步源码发现与待证明边界

状态：limited-source-research；日期2026-11-12。作者root。不是对任何候选库的完整安全审计，也不是正式NativeWeave选型。

固定源码证据：[evidence.json](evidence.json)。实际已读行段和未覆盖路径分别记录。

## 1. YetAnotherHttpHandler：生命周期是协议，不止包装一个SafeHandle

固定提交：`c386c1cc48d2e56711c15286cf2769353fdccf07`。

已读调用链片段：NativeHttpHandlerCore准备RequestContext/GCHandle → yaha_request_begin → Tokio spawn与取消select → 状态/数据/完成callback → RequestContext.Release → 线程池Dispose → request/context/runtime SafeHandle释放。

### INT-E001：父子native生命周期需要显式维持

YahaContextSafeHandle持有runtime引用，YahaRequestContextSafeHandle持有context引用；SetParent执行DangerousAddRef，释放时调用native销毁后DangerousRelease。certificate callback的GCHandle由context持有到ReleaseHandle。

这是该固定实现的源码观察，说明托管对象引用和原生使用期不是同一问题。它不证明所有使用点均有正确配对，也不意味着NativeWeave必须照搬同一SafeHandle层级。

[实际源码](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/YahaSafeHandles.cs)

### INT-E002：业务完成、GCHandle释放与native销毁有不同时间点

RequestContext.Allocate/Release处理managed GCHandle；完成入口finally中Release之后把Dispose放到managed线程池。代码明确保留native完成与native线程返回之间的释放次序。RequestContext的finalizer路径还等待完成事件，这与Unity domain reload背景有关；不应因上游存在该模式就把阻塞finalizer作为通用默认。

候选设计必须额外回答：回调尚未退出时谁持有上下文；Dispose从callback中调用会否等待自己；正常完成、失败、取消、shutdown各自如何推进静默。

[RequestContext](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/RequestContext.cs)；[完成入口](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L526-L625)

### INT-E003：背压跨FFI需要消费确认与数据有效期

Rust响应循环将body frame交给on_receive，并等待oneshot确认；C# OnReceive在flush异步完成后调用CompleteTask，失败则传回错误。这让消费确认成为数据继续推进的条件。上传路径另有ArrayPool租借和CopyTo，不可用“Rust跨语言”概括成全链零拷贝。

尚需完整追踪ResponseContext的实际复制策略、oneshot回收、取消发生在rx.await时的活性、consumer永不确认和runtime关闭。当前证据只证明存在该确认结构，未证明每种故障下最终回收。

[原生循环](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs#L483-L719)；[managed接收](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L466-L523)

### INT-E004：已有测试提供可复用的故障设计思路

CertificateVerificationCallbackLifetimeTest在TLS握手期间Dispose handler，尝试分配替代GCHandle，检查原callback仍保留且不会意外调用替代验证器。测试放入子进程，避免callback异常终止整个测试runner。

这证明测试源码覆盖了一个具体生命周期情景，**不证明本次运行通过**；测试使用反射和dotnet test，并不是NativeWeave AOT验收。后续需为AOT制品设计可观测、进程隔离的对应fixture。

[已读测试前170行](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/test/YetAnotherHttpHandler.Test/CertificateVerificationCallbackLifetimeTest.cs#L1-L170)

## 2. csbindgen：语法绑定生成与安全契约生成不同

固定提交：`b9eb1e84bb8185b78a4e8364fd948fee300329a7`。

INT-E005：所读emitter生成DllImport、指定calling convention/EntryPoint，并为bool加入U1 marshalling。枚举repr处理存在明确映射分支。**它不是已验证的NativeWeave LibraryImport/ownership/async生成流水线。**

DllImport不是天然不兼容AOT。需要比较blittable DllImport、LibraryImport与手工薄层，结合目标版本和marshaller行为。NativeWeave还需决定ABI描述的唯一来源、允许类型、诊断、按平台layout测试和生命周期注解；不能认为一个生成器自动解决所有安全问题。

[已读emitter行段](https://github.com/Cysharp/csbindgen/blob/b9eb1e84bb8185b78a4e8364fd948fee300329a7/csbindgen/src/emitter.rs#L145-L195)

parser、type_meta、负例测试、生成结果的AOT运行尚未深入完成。本次取回type_meta文件但未据此作语义结论；避免把“下载”计为“研究覆盖”。

## 3. 官方FFI边界约束

.NET官方建议优先评估LibraryImport、函数指针/UnmanagedCallersOnly、SafeHandle；具体匹配和生命周期仍由绑定负责。[互操作最佳实践](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/best-practices)

最新AOT文档明确UCO方法不执行marshalling。.NET11在启用runtime marshalling的情况下，native调用非blittable签名可能在进入callback体前fail-fast；正常异常catch不能修复错误签名。Direct P/Invoke的动态加载由OS控制，不使用DefaultDllImportSearchPaths。[AOT互操作](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop)

Rust官方将ABI和unwinding分开描述：panic=abort不受catch_unwind保护，外部异常不能随意穿越非unwind ABI。正常可恢复失败使用Result/status。[Rustonomicon](https://doc.rust-lang.org/nomicon/ffi.html)、[catch_unwind](https://doc.rust-lang.org/stable/std/panic/fn.catch_unwind.html)

## 4. 已真实执行的有限模型

[实验说明](../../../experiments/async-quiescence/README.md)与[结果](../../../experiments/async-quiescence/result.json)记录一个有限状态模型：把“已发布取消结果”误当“可回收native context”会得到具体UAF轨迹；候选barrier在模型范围内消除了该反例。

模型不包含真实GCHandle、FFI、弱内存、线程调度或Windows/Linux AOT；它不使C-ASYNC/C-LIFETIME变成accepted。作用是为R08/R09/R15提供可质疑的起点。

## 5. 接下来的完整路径与比较

- R03/R04：C/Rust/C#布局与调用探针；bool/enum/union、空buffer、32/64bit、回调calling convention。
- R05/R06：csbindgen、Interoptopus、UniFFI、Diplomat、cbindgen、bindgen、CsWin32/ClangSharp，按实际能力与生成边界比较，不全引入。
- R07/R08：Godot modules/mono和Qt for Python的对象身份、所有权与signal生命周期；仅种子，当前未作源码结论。
- R09/R12：完整取消、同步完成、注册同步回调、关闭、执行器停止与回收链。
- R10/R16：长度/容量单位、UTF8、零长度指针有效性、溢出、alias和allocator配对；fuzz和真正跨语言实验。
- R11：panic/unwind/abort、managed callback异常、损坏状态后禁止继续使用；进程隔离负例。
- R17/R18：不同引擎的端到端成本与接入通用性；不根据FFI微基准预选Rust。

## 6. 当前限制与复用政策

本轮未运行这些上游测试、未编译C#/Rust、未认证AOT。上游实现中的Unity适配、默认runtime、限长i32 buffer等都是研究对象，不自动成为NativeWeave约束。需要复制代码或引入依赖前，必须重新读取固定版本LICENSE并记录复用方式；本批只保存自己撰写的分析与永久链接。
