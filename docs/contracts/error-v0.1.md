# C-ERROR-001：状态、领域错误、managed异常与Rust panic

版本：0.3.0；D08 / R11。作者：interop_design。状态：**研究/设计候选已完成；registry记录精确审查版本、内容hash与接受状态；产品验证保留在Delivery阶段**。本文件是v1状态值和基础ErrorRecord的唯一文档权威；生成代码由D03 ABI描述生成，D02验证布局。本文件示意片段未单独编译；已执行研究原型见末尾精确证据，完整产品实现/平台行为仍需Delivery验证。

## 1. 目标

普通失败可预测、可诊断、无跨语言异常传播；错误报告本身不依赖成功分配大字符串。领域语义与基础互操作故障分开，保留原始provider代码及可追踪ID。进程致命故障如abort、无效内存访问、非法UCO签名不包装成虚假的可恢复Exception。

Rust普通可失败操作使用Result；managed普通失败在自然API中映射为有类型Exception或领域Result。FFI只传固定布局状态与显式owned领域数据。

## 2. 统一wire状态值

`nw_status`固定为`uint32_t`；Rust为u32，C#为uint。不使用C enum大小或Rust/C# bool进行ABI推断。

| 值 | 名称 | 语义与约束 |
| --- | --- | --- |
| 0 | OK | 本次调用成功；普通API唯一成功值 |
| 1 | PENDING | 仅声明为非阻塞try_/poll的API允许；不是失败，不填ErrorRecord |
| 2 | CANCELED | 仅已确认的操作终态；request_cancel成功不返回此值 |
| 3 | INVALID_ARGUMENT | 输入值/形状不符合契约；不说明任意无效指针可安全探测 |
| 4 | INVALID_STATE | 合法句柄处于不允许的状态，如重复take |
| 5 | OUT_OF_MEMORY | 可报告的分配失败；不承诺捕获allocator abort或所有managed OOM |
| 6 | NOT_SUPPORTED | 请求能力未实现；调用方可选择已声明替代路线 |
| 7 | BUFFER_TOO_SMALL | 调用方容量不足，输出按具体API约定保持未转移状态 |
| 8 | CALLBACK_FAILED | managed回调普通失败；按§6区分decision/普通通知/terminal通知，不能重写既有native终态或远端effect |
| 9 | NATIVE_PANIC | 成功捕获的unwinding panic；所属Engine被poison |
| 10 | ENGINE_POISONED | 拒绝新业务；允许专用停止/退休/释放控制路径 |
| 11 | CONTRACT_VIOLATION | 适配器/生成接口违反协议；不是普通用户输入错误 |
| 12 | TIMEOUT | 该领域操作确认的超时；不表示远端效果被撤销 |
| 13 | DOMAIN_ERROR | provider或领域错误，使用对应domain/code与typed payload |

未知非零值按未知native失败处理；不执行隐式重试，不作为成功。未知PENDING出现在非try API也按契约错误处理。新增状态保持旧值语义，不重用编号。status与API特定的结果枚举分开。

## 3. 固定ErrorRecord

```c
typedef struct nw_error_info_v1 {
    uint32_t struct_size;
    uint32_t domain;
    int32_t  code;
    uint32_t flags;
    uint64_t correlation_id;
} nw_error_info_v1;
```

初始win-x64/linux-x64自然布局预期size=24、alignment=8、offsets=0/4/8/12/16；由R03实际布局探针和最终C/Rust/C#三方验证确认，不能向未测目标外推。flags v1为0，保留位不得自行解释。`domain=0`保留给基础互操作；Engine domain ID由其契约注册，provider code保留原义，不能只剩一段人类消息。

`out_error`是可选的诊断输出，不是决定业务status的第二次操作。v1采用完整24-byte记录写入，不采用含糊的逐字段短prefix。ABI主版本选择布局；本记录没有另一个内嵌version字段。D02的`get_abi(out_capacity)`是另一种输出接口，不能把其容量失败状态套到已确定的业务错误上。

caller在**每次调用前**零初始化整个有效buffer，再把起始`struct_size`设为实际可写容量（u32）。非null指针必须自然对齐且至少指向4个已初始化、可读的字节；容量值不能大于caller真实可写范围，且buffer不与输入或其他输出重叠。指针本身的有效性仍是caller前置条件，provider不探测任意坏地址。

| out_error / 原始status / 输入容量 | provider行为 | 返回status |
| --- | --- | --- |
| null / 任意 | 不访问诊断内存 | 原始业务status不变 |
| 非null / OK或PENDING / 任意合法声明 | 完全不写；caller已清零的字段保持原值 | OK或PENDING不变 |
| 非null / 失败 / struct_size为0～23 | 至多读取4-byte容量头；不写任何字节，不返回部分ErrorRecord | 原始失败status不变，不改成BUFFER_TOO_SMALL |
| 非null / 失败 / struct_size至少24 | 在局部构造完整v1 record，再写恰好前24bytes；输出struct_size=24、flags=0；24以后的caller字节保持不变 | 原始失败status不变 |

容量值0～3不撤销至少4-byte可读头的前置条件；它只表达不够容纳v1输出。provider在验证容量以前不得以完整`nw_error_info_v1`引用读取24bytes。大容量buffer不允许写未知尾部；未来追加字段需要以明确ABI能力/版本说明扩展，v1 consumer只读取已经返回的完整已知字段。诊断信息不足时status仍可用；生成wrapper默认栈上准备完整24bytes。该写入无需分配或转移任何owner。

correlation_id用于连接日志/trace，可以为0；不代表身份、权限、不可猜测随机数或持久查询句柄。不能拿它向共享错误表读取过期内存。基础record不含TLS last-error字符串、跨线程借用指针、native异常对象或需要释放的panic payload。

## 4. 丰富领域错误

数据库SQLSTATE、约束名、服务端诊断、HTTP错误详情等通过领域typed error或显式owned payload保留。可变文本采用D07的UTF-8与明确allocator/release协议，设定长度上限、截断标记及隐私规则。它们不能成为返回最基础失败状态的必需分配。

异步terminal callback只传借用的固定ErrorRecord，managed立即复制；丰富结果用D06的一次take_error/typed take_result取得拥有权。诊断payload接管失败仍能返回基础状态并释放未转移资源。API返回成功与err字段不一致属于契约缺陷，不静默选择一方掩盖错误。

## 5. managed映射

生成adapter把INVALID_ARGUMENT/INVALID_STATE映射到适合该API的参数或状态异常；CANCELED仅由操作终态映射到Task取消；TIMEOUT映射TimeoutException；领域错误映射provider/领域异常；PANIC/POISONED/CONTRACT映射保留Engine、operation、status、domain、code和correlation的NativeEngineException。

异常消息不包含裸地址、GCHandle、凭据或整段用户数据。原始Exception只在managed进程内部保留，不尝试跨C ABI序列化System.Exception。C#15 union可用于领域可预期分支，但不是所有异常的强制封装；需要测量默认union值类型装箱与AOT体积。

取消请求、Task状态、native静默、数据库连接可复用及远端effect分别记录。Unknown提交结果要进入领域恢复记录，即使本地资源已可安全回收；不自动重试不幂等操作。

公开失败使用正常C#异常流程，原始状态字段用于诊断，不要求业务代码操作wire指针。下面是未编译API示意，实际字段与构造由生成adapter/领域类型确定：

```csharp
try
{
    using var result = await engine.ExecuteAsync(input, cancellationToken);
    await result.CopyToAsync(output, cancellationToken);
}
catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
{
    // The operation reported cancellation; this is not a transaction rollback proof.
}
catch (NativeEngineException error)
{
    logger.LogError(error, "Engine {Engine}; status {Status}; trace {Correlation}",
        error.EngineId, error.StatusCode, error.CorrelationId);
    throw; // no implicit retry of possibly effectful work
}
```

## 6. managed→native回调边界

UCO入口为静态非泛型函数，只有精确blittable参数与返回值。普通可处理Exception在回调适配器内捕获；日志、错误记录和finally退出路径也必须不让普通异常越ABI。失败处置按回调角色定义：

- 同步decision callback：返回CALLBACK_FAILED或该profile明确的拒绝值，native按fail-closed处置，不接受未经确认的安全/业务决策。
- 普通可失败notification callback：锁存binding fault并请求停止或让尚未终结的领域操作失败；已有独立发生的远端effect不因此被撤销。
- **D06 terminal notification callback：native唯一终态已经存在，不能为响应callback失败再发布第二次Failure、重写Success/Canceled/Failure，或把数据库Unknown/已提交effect改成未发生。** managed用预分配binding-failure latch记录桥接错误，在finally唤醒既有cleanup slot；协调器按D06发布单一managed Faulted结果，同时保留原native状态与领域effect。若managed任务已经完成，只补充桥接/cleanup诊断，不回改其终态。仍须一次take或放弃结果，并完整retire/drain/release；回调返回的CALLBACK_FAILED不隐含结果所有权回退。

terminal通知的void profile没有返回状态时，也执行相同latch/唤醒/清理规则。该规则直接服从[D06终态接收与清理](async-v0.1.md)，不能用“触发领域失败”越过其唯一终态约束。

.NET11官方文档说明：启用runtime marshalling时，无效的non-blittable UCO签名可在native调用时fail-fast；callback方法体的catch不能修复签名。bool/char使用显式wire类型，生成器拒绝非法签名；隔离进程测试才验证致命路径。见[官方AOT interop](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop)。

错误映射自身分配失败时保留固定状态和已有context，不递归格式化/日志；真正无法继续的OOM、StackOverflow、访问违规或运行时致命状态由进程策略处理。本契约不承诺catch恢复这些故障。

## 7. Rust panic策略与候选比较

| 方案 | 适用与缺点 | v1决定 |
| --- | --- | --- |
| 所有失败panic | 错误路径难区分，成本与恢复语义不明确 | 拒绝；常规失败用Result |
| panic=abort | 简洁明确，任何panic终止进程，不能恢复 | 可作为明确声明的fatal profile；不能宣称NATIVE_PANIC可捕获 |
| panic=unwind +边界捕获 | 可将已捕获panic隔离到Engine，但需处理部分变更及payload析构 | 默认研究/发布候选profile，必须满足下面的严格约束 |
| C-unwind跨到C# | 不能让两个语言runtime共同承担任意异常解栈 | 不用于公共ABI |

原始Rust1.99.1研究及本次Rust1.100固定源码均表明catch_unwind只捕获unwinding panic；panic hook先执行，abort不会被它恢复，返回的panic payload在Drop时还可能再次panic。其存在不证明被修改状态仍可继续使用。相关官方run-crash测试源码仅阅读；本次实际运行的是§13列明的独立研究子进程。[R11报告](../research/topics/R11/report.md)

## 8. 捕获、poison与清理

每个导出入口在不会越ABI的guard内执行；异步工作还必须在其真正运行/轮询边界捕获或由supervisor消费panic结果。仅包住spawn/start入口不能捕获稍后worker中的panic。

捕获后：原子poison所属Engine，拒绝新业务；已接受操作由仍可信的supervisor发布一次NATIVE_PANIC或ENGINE_POISONED终态并请求停止。cancel、try_retire和release等专用清理路径仍允许，不能因poison把资源永远关在一个无法调用的API后面。但它们只能报告已真实证明的静默，不得伪造成功。

v1错误返回路径不格式化或Drop未知panic payload。隔离路径可有意保留/forget该payload并记录quarantined-payload计数，避免第二次panic越界；这是一项异常后的资源保留成本。每个Engine首个panic后关闭新准入，但已有多个并发任务仍可能分别panic，隔离对象上限须结合已接受任务数，不能假设只会保留一个payload。unknown payload可达bytes可能无法精确计量，须标记未知/保守估计。宿主限制隔离Engine数量并决定重启；不能把此策略宣传成无限次数panic后无泄漏运行。

清理known-safe字段时仍使用不会unwind的guard；析构中panic、panic hook panic、allocator abort等可能终止进程。若不能证明某资源仍可安全析构，就保留/隔离它，不执行未定义的修复。DisposeAsync只有实际清理成功才报告成功；隔离未完成必须保留诊断及未释放预算。D02 v1将native模块保留至进程退出，不支持热卸载；未来若另立热卸载profile，必须先证明无活动代码/回调及全部owner退出，不能将该未来条件解释为v1已有卸载能力。

```rust
// Design skeleton only; engine state and entry preconditions must be verified.
fn guarded_entry<F>(engine: &EngineState, body: F) -> u32
where F: FnOnce() -> Result<(), EngineError> + std::panic::UnwindSafe
{
    if engine.is_poisoned() { return ENGINE_POISONED; }
    match std::panic::catch_unwind(body) {
        Ok(Ok(())) => OK,
        Ok(Err(error)) => map_regular_error_without_panicking(error),
        Err(payload) => {
            engine.poison_without_panicking();
            std::mem::forget(payload); // recorded quarantine; not normal leak-free recovery
            NATIVE_PANIC
        }
    }
}
```

清理入口需要单独guard，不复用上面拒绝poison后业务的检查。禁止无论内部状态如何都用AssertUnwindSafe包住整个Engine；每处assert必须解释捕获后的状态约束、哪些操作仍合法，以及为什么不会访问被部分修改的不安全表示。

## 9. 失败原子性

create/start提交前失败不交付半拥有对象；out owner保持null，取得的临时资源在本语言内回滚。所有权转移成功后由新owner释放；不能同时返回失败并要求caller猜测是否已经adopt。

完成结果、native退休与远端事务效果各自有记录。普通失败允许Engine继续使用的条件由错误分类定义；PANIC、CONTRACT_VIOLATION默认poison，NOT_SUPPORTED与INVALID_ARGUMENT通常不poison。不能把故障变成Exception就声称状态已经恢复。

## 10. 诊断、性能和兼容

成功热路径不构造错误字符串或Exception；固定record为冷失败路径，out_error可选。记录status分布、callback fault、panic/poison数、quarantine bytes/objects和cleanup age；采样/日志开销单独测量。correlation跨C#/Rust传播，不把完整诊断栈强制成为每个Engine依赖。

旧consumer遇到新状态保持失败；领域payload有自己的版本与能力声明。固定基础record严格遵循第3节完整v1记录的容量与写入算法；未来新增记录字段必须经新的ABI版本或明确协商的能力定义，不能据此写入v1 caller的尾部或恢复逐字段短prefix规则。所有版本组合都要检验错误路径与owned payload释放。

## 11. 验证与Delivery

| ID | 测试 | 必须观察 | Delivery |
| --- | --- | --- | --- |
| ER-01 | 每个status、未知值、ErrorRecord容量0/3/4/23/24/更大与尾部canary、错误domain/payload版本 | 失败原status不变，短record不写、完整仅写24bytes；无越界/误成功，准确映射，release配平 | A05、A12、A20 |
| ER-02 | 普通Rust Result、导出入口panic、异步worker panic | 普通失败可继续；panic poison且终态一次 | A05、A07、A18 |
| ER-03 | panic=abort、panic hook、Drop再panic、跨FFI非法unwind | 独立子进程按预期退出，不杀测试runner | A05、A14、A15 |
| ER-04 | managed callback throw，错误映射/日志失败 | 普通异常不越ABI，fail-closed，清理完整 | A06、A20 |
| ER-05 | 非blittable UCO，错误calling convention | analyzer诊断；隔离AOT负例的真实进程结果 | A12、A14、A15 |
| ER-06 | poison与其他并发操作、cancel/retire/release竞争 | 新业务拒绝，已接受操作有终态/明确隔离，不能伪造静默 | A05、A08、B22 |
| ER-07 | domain error文本截断、未知事务效果、错误payload接管失败 | 语义不丢失，不误重试，内存/隐私界限 | B05、B07、B22 |

上述完整产品测试矩阵尚未实施；§13明确列出本次已执行的研究子集。正式产品验收必须固定panic策略、编译器、OS/架构、AOT二进制、退出码、标准输出/错误和失败注入种子；不得全局关闭警告或修改oracle来得到通过。

## 12. 研究问题处置

Q08已有明确设计决定：常规失败Result/status、fixed error record、managed普通异常入口containment、Rust unwind捕获后poison、fatal profile独立声明。经独立审查后可标design-resolved；ER-01～07仍是实现及生产验收义务。不能以研究问题关闭为由将未运行实验登记为verified。

## 13. 本次完成复核与错误证据（2026-11-13）

[R11 完成报告](../research/topics/R11/report.md) 现已补齐 Rust1.100 的固定源码与 [7 个真实隔离子进程](../../verification/interop-completion/panic-linux/result.json)：捕获普通 unwind 与隔离未知 payload 正常返回；payload Drop、hook、cleanup 双 panic、extern-C 逃逸及 abort profile 分别导致预期非成功终止。原始 stdout/stderr/exit、源 hashes 与编译参数保留；不把这些局部结果外推成完整 Engine poison 恢复证明。

[主探针](../../verification/interop-completion/linux/result.json) 实际验证普通 managed callback 异常在方法内封闭及 result 转换异常的 finally release；[非法 UCO 探针](../../verification/interop-completion/uco-invalid-linux/result.json) 在 normal/AOT native 调用 char/bool callback 时均于方法体进入前因未处理 InvalidProgramException 终止子进程。后者说明方法内 catch 无法纠正签名，不声称已验证每种进程致命机制或外部 catch 语义。

本文件仍是 wire status 唯一权威。实验的私有枚举必须保留为实验数据，不回写成本契约的新编号。错误语义、隔离成本和清理接口已足够指导实现；正式设计接受等待独立审查，完整 ER-01～07 产品验证、Windows 新致命用例与长期隔离预算验证保持在其 Delivery 阶段。


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
