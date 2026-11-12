# R11：错误、Rust panic与managed callback异常边界

日期：2026-11-12。作者：interop_design。状态：**partially_evidenced；design decision recorded；independent review pending**。交付为[D08 Error契约](../../../contracts/error-v0.1.md)，其中状态编号与基础ErrorRecord是唯一文档权威。代码示例未编译，fatal行为与真实AOT尚未运行。

## 1. 输入、需求与非目标

Design基线`1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan基线`da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。R11 revision `0.1.1`、packet hash `4450ce8ebaea49e3040dcfec110453d2deca4958c633ef16269259d019e1fdd5`；D08 revision `0.1.1`、hash `64665225e71ff86c0dfa9eb006049333de7dc48bbf8c73624218e07ab68320c9`，与固定远端图及本地字节匹配。

普通失败不能越过语言边界unwind，错误报告不能依赖再次成功分配字符串，异步错误不能读到下一调用覆盖的TLS消息，provider领域信息不能被压成无类型文本。必须区分常规错误、契约缺陷、成功捕获的panic和进程致命故障。

非目标是恢复访问违规、abort、任意堆破坏、双panic或所有OOM；也不承诺将任意Rust/C++异常跨C#运行时安全解栈。普通Rust逻辑用Result，普通C# API使用有类型Exception或领域Result。应用不需要知道native allocator或panic payload布局。

## 2. 源码、官方说明和真实覆盖

| 来源 | 固定身份 | 已读范围 |
| --- | --- | --- |
| rust-lang/rust 1.99.1 | `58cf8f9c35b355199727627d07ae34a4e2846d67` | std::panic::catch_unwind说明、panicking实现、panic安全trait测试与3个run-crash测试 |
| .NET Native AOT官方文档 | 2026-11-12观察，页面更新2026-11-04 | .NET11非法UCO签名与fail-fast限制 |
| Godot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | SignalAwaiter/GCHandleBridge的UCO内普通异常处理 |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | TLS验证fail-closed、异步失败传播、native错误字符串与状态 |

源码行段、blob与限制见[evidence.json](evidence.json)。[coverage.json](coverage.json)保留UniFFI错误桥、运行时UCO入口内部和allocator OOM实现未读；没有据官方页面伪造源码commit。上游panic测试源码已读但全未运行。

## 3. Rust普通失败与catch_unwind的真实边界

固定[`std/src/panic.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/src/panic.rs#L290-L360)和[stable catch_unwind文档](https://doc.rust-lang.org/stable/std/panic/fn.catch_unwind.html)说明：catch_unwind只捕获unwinding panic；普通可失败操作应该使用Result；abort不会被恢复；panic hook在捕获前运行；catch foreign exception的结果没有通用可依赖保证；返回的panic payload在销毁时还可能再次panic。[R11-S01、O01]

[`panicking.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/src/panicking.rs#L495-L600)在catch边界用运行时intrinsic与ManuallyDrop状态转交闭包结果/异常payload。这些内部细节说明错误payload也是具有析构责任的owner；不能把返回Err等同于已安全处置所有异常资源。[R11-S02]

NativeWeave选择默认可恢复候选profile为panic=unwind、入口与异步工作边界捕获、捕获后poison所属Engine；常规失败仍走Result。panic=abort只作为显式声明的fatal profile，不能宣称返回NATIVE_PANIC。C-unwind不进入公共C ABI。AssertUnwindSafe不是任意破坏状态的修复许可证，必须逐处说明失败后哪些表示仍成立、哪些cleanup可安全执行。[R11-D01]

## 4. 已读测试给出的反例

[`panic-in-ffi.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-ffi.rs)为run-crash测试：非unwind FFI内panic不能被想象成普通返回值。它包含析构观察对象并声明预期进程失败。[R11-T01]

[`panic-in-cleanup.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-cleanup.rs)制造unwind途中析构再次panic；该测试对MSVC有特殊忽略说明，因此不能把一条Unix错误输出字符串直接当作Windows验收标准。[R11-T02]

[`panic-in-hook.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-hook.rs)在panic hook中再次panic，给出另一个catch body不能保证恢复的致命路径。[`library/std/tests/panic.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/tests/panic.rs)检查安全trait的静态关系，它不是全部FFI containment的执行证明。[R11-T03、T04]

本轮没有Rust编译器或运行这些测试；“read test source”与“test passed”严格区分。正式验证需在子进程分别覆盖unwind、abort、payload Drop、hook、cleanup double panic，并记录目标工具链、退出码和可移植的行为分类，而非强制跨平台同一错误文本。

## 5. managed callback异常与UCO签名

Godot[`SignalAwaiter`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/SignalAwaiter.cs)和[GCHandleBridge](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/Bridge/GCHandleBridge.cs)在UCO方法内处理普通Exception；YAHA的TLS验证callback在普通异常时返回false。它们提供边界containment和fail-closed的实际形状，不代表任何catch都能兜住整个runtime。[R11-S03、S04]

[Native AOT interop官方文档](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop)明确描述.NET11：启用runtime marshalling时，native调用含non-blittable参数的非法UCO签名可能触发InvalidProgramException并fail-fast，方法体的catch不能修复签名。[R11-O02] NativeWeave因此采用生成的静态非泛型精确blittable签名，bool/char映射为显式wire类型，错误必须在生成/编译诊断及子进程负例发现。

边界catch还要考虑解码、日志和finally动作自身可能失败。callback异常记录走已存在context和固定status；错误路径不递归创建大量字符串、Exception或队列Task。StackOverflow、runtime fatal、访问违规与不能继续的OOM保留宿主进程策略，不伪装为普通可恢复失败。

## 6. 基础status与错误布局的选择

| 候选 | 问题 | 选择 |
| --- | --- | --- |
| TLS last-error字符串指针 | 多线程/异步错线程、下一调用覆盖、谁释放不清 | 不用于Core公共错误契约 |
| 每错误都分配owned文本 | 信息丰富但OOM时可能无法报告原错误 | 仅可选领域详情 |
| 固定status +固定record | 无需字符串分配即可报告基本失败，易布局验证 | v1基础 |
| 任意Exception/panic对象跨ABI | 布局/析构/runtime语义不可统一 | 拒绝 |

D08采用u32 status；0为OK，1=PENDING仅用于声明的try/poll，2=CANCELED仅为已确认终态；其余3～13分别是参数/状态/OOM/能力/容量/callback/panic/poison/契约/超时/领域错误。完整编号只以D08为权威，避免多份表漂移。未知非零失败，不隐式retry。

基础ErrorRecord为`u32 struct_size, u32 domain, i32 code, u32 flags, u64 correlation_id`，x64预期24字节。record没有跨线程借用字符串、TLS error指针或panic对象；callback收到后即时复制。correlation仅用于诊断，不能作为权限或持久内存查询key。C布局探针由R03负责，最终Rust/C#/C三方与AOT仍须实际验证。[R11-D02]

provider详细错误采用typed owned result/UTF-8 payload，遵循D07释放与D06一次take协议。接管失败仍可报告基础status且native保留owner。成功热路径不构造错误字符串；基础错误不因丰富诊断分配失败而丢失。

## 7. poison后的既有操作和资源

只在spawn/start外包catch_unwind不足以捕获随后worker的panic。每个异步任务的真实执行/轮询边界必须捕获，或由仍可信的supervisor消费任务失败。首次panic原子poison Engine、拒绝新业务；既有操作各自一次发布NATIVE_PANIC/ENGINE_POISONED并请求停止。已完成或effect已知的结果不能被盲目改写；领域保留实际效果知识。

stop/cancel/try_retire/release必须仍可进入专用cleanup路径，不走“poison即拒绝一切”的业务门。但不能因为已经向managed发布失败就捏造静默；剩余worker、callback、外部控制调用仍必须排空。若supervisor不再可信或资源表示已破坏，隔离并保留owner/预算，不能强行free来让DisposeAsync假成功。[R11-D01]

panic payload的Drop可能再次panic。v1错误返回路径不格式化/不析构未知payload，可在poison路径有意forget并记录quarantine计数；这不是普通无泄漏恢复。Engine关闭新准入，宿主限制隔离Engine数量并决定重启；已有多个并发任务仍可能各自panic，隔离预算需按已接受任务上限计算，不能谎称仅保留一个payload。unknown payload的可达bytes可能不受精确统计，记录对象数与保守未知bytes状态。

known-safe字段的cleanup也需要不会unwind的边界策略；析构double panic、hook panic、allocator abort仍可能终止进程。未来若改为隔离子进程Engine，可加强故障域，但这不是本轮强制新增runtime或产品范围。

## 8. 失败原子性与场景

create失败保持out owner为空并回滚临时资源；start拒绝不留callback义务；已提交start后的业务错误走terminal。callback本身普通失败返回CALLBACK_FAILED并要求确定停止/失败。结果take成功即转移且native归零；take失败输出为空而native保留owner。错误字符串不是判断是否转移的依据。

正常示例是C# await返回owned结果、using释放；取消示例是调用者token请求停止而native最终成功/取消仍由终态决定；异常示例是NativeEngineException保留Engine/status/domain/code/correlation，再由应用决定是否重试。D08骨架只展示guard形状，未编译，不能复制其中省略的状态与清理逻辑声称产品实现完成。

## 9. 验证任务与性能账本

D08 ER-01～07映射A02/A04/A06/A07/A14/A15/A18/A20/A21/B22：成功路径无错误分配，所有错误值/未知值映射，error struct容量与版本，OOM与详情接管失败，managed callback普通异常，非法UCO与Rust fatal subprocess，poison后的既有操作一次终态与真实排空，长负载quarantine及资源预算。

分别记录status计数、错误详情分配、panic/poison数、已接受任务数、未退休bytes、quarantine对象/未知bytes、cleanup age和fatal子进程退出行为。不能拿“catch到了panic”的微基准证明完整Engine恢复，也不能把错误日志开销隐藏在成功路径吞吐统计之外。

Windows/Linux unwind工具链、panic strategy、C调用约定与AOT二进制hash进入正式manifest。R11未执行这些验证；R03的C布局结果也不能代替Rust/C#/AOT的跨语言一致性。

## 10. 设计关闭与后续审查

Q08已有可审查的明确决定：固定错误基础、typed owned详情、普通managed异常containment、unwind捕获后poison、fatal profile显式声明，以及真实cleanup与错误结果分离。独立审查通过后可关闭设计研究问题，同时把ER系列实施和生产验证保持pending。

R03审查ErrorRecord prefix与状态演进；R08审查callback内失败、退出与不重复拥有；R34审查错误隐私、预算和不可信参数；R12审查worker supervisor与poison排空。UniFFI及runtime内部UCO入口未读，任务整体保留partially_evidenced；不把这些缺口隐去或把所有决定留给用户。

许可证：Rust固定LICENSE-MIT与LICENSE-APACHE全文已读取；其核心标准库双许可，具体将来复用文件仍遵循各自声明。Godot、YAHA的MIT许可证已读取。报告为机制转述和新的NativeWeave设计，不复制大段源码。
