# C-CALLBACK-001：注册、回调准入、撤销与静默

版本：0.3.0；D05 / R08、R07、R09。作者：interop_design。状态：**研究/设计候选已完成；registry记录精确审查版本、内容hash与接受状态；产品验证保留在Delivery阶段**。本协议定义v1推荐设计，代码样例为未编译设计骨架。实现、AOT和跨平台证据另行验收。

## 1. 需要解决的问题

callback可能来自外部线程、发生在注册/启动返回前、与取消和Dispose竞争，也可能触发托管异常。注销成功、没有新业务事件、native不再访问cookie、已经进入的回调退出，是不同承诺。

v1将**请求停止**和**成功退休**分开：请求停止非阻塞、可重入；退休只有在所有相关访问来源永久停止后成功。不会通过在callback线程中同步等待自己退出来实现注销。

## 2. 来源及适用范围

[R08报告](../research/topics/R08/report.md)提供完整来源。Godot的SignalAwaiter创建强GCHandle，native one-shot callable持有并在析构时释放；managed signal callback复制借用参数、处理普通异常并可能内联执行continuation。YAHA的TLS生命周期测试专门制造Dispose后GCHandle复用场景。这些实现为ownership和重入提供具体参考，但其线程和引擎假设不直接成为本协议。

.NET11 CancellationTokenRegistration的Dispose/DisposeAsync在自身回调上下文中有避免自等待的例外，因此不能在其内部调用DisposeAsync后就宣布该callback已经退出。[D06](async-v0.1.md)要求清理由独立managed协调路径完成。

## 3. ABI与cookie

wire类型、状态值和ErrorRecord分别以D02与[D08](error-v0.1.md)为权威。此处名称由生成器加Engine前缀；D02的直接版本化导出为默认入口。仅选择可选函数表profile的Engine通过其`get_api`协商函数表；下面的callback table是start输入记录，不强制Engine导出函数表。

```c
typedef struct nw_subscription nw_subscription;
typedef uint32_t (NW_CDECL *nw_on_event_fn)(
    uintptr_t cookie, uint32_t event_kind,
    const void *payload, uint64_t payload_bytes);

typedef struct nw_callbacks_v1 {
    uint32_t struct_size;
    uint32_t flags;                 /* v1 reserved: 0 */
    uintptr_t cookie;               /* opaque managed token */
    nw_on_event_fn on_event;
} nw_callbacks_v1;

uint32_t NW_CDECL nw_subscription_create(
    nw_engine *, nw_subscription **out_subscription, nw_error_info_v1 *);
uint32_t NW_CDECL nw_subscription_start(
    nw_subscription *, const nw_callbacks_v1 *, nw_error_info_v1 *);
uint32_t NW_CDECL nw_subscription_request_stop(nw_subscription *);
uint32_t NW_CDECL nw_subscription_try_retire(nw_subscription *);
void NW_CDECL nw_subscription_release(nw_subscription *);
```

`NW_CDECL`为目标C调用约定宏。指针与表大小按目标ABI计算，不把这张表硬编码成跨32/64位相同尺寸。callback table由native在start提交前复制；不得留存managed栈上table地址。payload是当前回调范围内的借用，长度为D02固定u64字节数，转换为目标地址范围须checked；类型及序列化模式由event_kind对应领域契约定义。异步消费者必须在返回前复制；如领域需要owned结果，callback只记录通知，稍后通过D06的一次typed take接管，不能保留借用指针。

cookie来自一个Normal强GCHandle。native只原样回传；不解引用、不做整数递增、不当安全身份或日志里的私人对象信息。非零cookie不构成有效性验证；正常协议保证它在全部可能回调期间有效。v1通用notification payload只借用；需要拥有结果的异步操作采用D06的显式take_result，不在callback成功/失败返回中隐式转交所有权。

## 4. 创建、启动与失败原子性

create成功返回一个拥有句柄，但不允许回调。managed随后初始化context、计数器、托管委托/静态函数指针及需要的取消注册，再调用start。start在所有可失败准备完成后执行一次提交：

- 提交前失败：没有任何callback已经发生、排队或留存；返回失败，managed可按未启动资源路径释放。
- 提交后：返回OK，即使业务立即失败；失败由正常事件/终态通道表达。可以在start返回前同步回调。
- 不允许出现“已回调后start又返回失败且让managed按未接管路径free”的双重责任。

v1不支持更换活动订阅的cookie或函数表。重新注册创建新的subscription/context，旧对象按自己的退休协议结束；避免热替换与ABA成为基础协议负担。

## 5. native回调准入与停止

native具有`Created / Active / StopRequested / Retired`状态及work/callback义务计数。每次准备回调时，必须在native同步协议下确认允许此类回调并计入callback lease；离开临界区再调用managed。回调返回后释放lease。request_stop原子关闭新的普通事件生产，取消/停止在途来源；它不意味着已有callback已返回。

`try_retire`只返回OK或PENDING，除了无效调用等契约错误。OK的线性化点必须同时做到：关闭全部未来callback来源、确认在途callback为0、确认会访问cookie/payload的native work为0，并将Retired永久锁定。它不在锁内调用managed，不等待外部线程，也不触发回调。PENDING不写ErrorRecord。重复try_retire返回OK；Retired之后request_stop为幂等OK。

release只在Created且从未start，或Retired且没有control call lease时合法。它是非阻塞、不会回调的拥有权释放。违反前置条件是适配器缺陷；不能靠强制free掩盖它。

## 6. managed回调入口与普通用户代码

默认notification profile的native入口只做有界校验、必要复制或take通知登记、状态更新与有界排队。公共Task使用异步continuation；公共事件/流由managed dispatcher/IAsyncEnumerable提供，不在外来线程上运行任意业务continuation。队列必须同时限制项数及字节，溢出策略明确为背压、拒绝或领域允许的丢弃，不能静默无限累积。

TLS验证等必须同步返回决策的profile允许显式登记的同步managed handler。该profile要求快速返回、不得await/阻塞等待同一Engine关闭；异常按fail-closed决策返回。它不能自动继承普通通知的线程或吞吐保证。

领域公开API可返回实现IDisposable/IAsyncDisposable的NativeSubscription，或把它封装在IAsyncEnumerable的enumerator中。示意调用如下；类型及handler为未编译领域占位，不是已经发布的产品API：

```csharp
await using var subscription = engine.Subscribe(HandleEvent, cancellationToken);
try
{
    await RunApplicationWorkAsync(cancellationToken);
}
finally
{
    subscription.Dispose(); // close admission and request stop; does not wait
    await subscription.DisposeAsync(); // outside the handler; wait for cleanup
}
```

重复Dispose/DisposeAsync返回同一清理结果，不能二次free。同步Subscribe参数错误可同步抛出，native启动失败由对应NativeEngineException表达；成功开始之后的handler失败经领域subscription completion/error通道可观察，不能只写日志后静默丢失。

UCO入口使用静态、非泛型、精确blittable签名；bool/char不进入wire。普通异常在入口内处理，转换D08状态并记录managed失败；非法签名、内存破坏等致命错误不被宣传为可恢复。生成器必须验证整个函数签名，而非只在方法体加catch。

```csharp
[UnmanagedCallersOnly(CallConvs = [typeof(CallConvCdecl)])]
private static unsafe uint OnEvent(
    nuint cookie, uint kind, void* payload, ulong bytes)
{
    // Design skeleton: all helpers must have tested non-throwing exit paths.
    CallbackState? state = null;
    bool entered = false;
    try
    {
        state = (CallbackState?)GCHandle.FromIntPtr((nint)cookie).Target;
        if (state is null) return NativeStatus.ContractViolation;
        state.EnterNativeCallback();
        entered = true;
        return state.CopyOrRecordAndEnqueue(kind, payload, bytes);
    }
    catch (Exception error)
    {
        return state is null
            ? NativeStatus.ContractViolation
            : state.RecordCallbackFailureWithoutThrowing(error);
    }
    finally
    {
        if (entered) state!.ExitNativeCallbackWithoutThrowing();
    }
}
```

此骨架不证明helper永不抛出；正式实现须检查包含finally、日志、OOM和队列调度失败的路径。失效GCHandle可能指向其他对象甚至产生致命故障，不能把以上catch当作迟到callback的安全方案。

## 7. 重入、关闭与清理调度

在callback内调用Dispose/RequestStop允许：只关闭准入、设置stop请求并安排清理，不等待任何callback。native函数不能持有callback返回所需锁再调用managed；managed准入锁也不跨FFI持有。

同一订阅callback作用域内调用会等待自身退出的DisposeAsync是使用错误。同步callback profile用生成的线程内CallbackScope检测并拒绝该调用；notification dispatcher对自己的in-flight handler也要检测。若领域支持异步handler，其marker随该handler的异步执行上下文传播，例如专用AsyncLocal scope，不能只用ThreadStatic猜测跨await的身份；纯同步decision profile不收取此额外成本。检测不承诺发现用户主动SuppressFlow、跨线程构造的任意循环等待；文档和失败测试仍禁止callback中同步等待同一资源的drain。

cleanup在callback外执行：送出所需stop并关闭普通managed控制调用准入，保留协调器独占的lifetime capability；等setup明确Settled及注册结果发布；Registered分支调用CancellationTokenRegistration.DisposeAsync并等待它从外部真正结束，NoRegistration分支无需等待未创建的registration；等已取得的control-call lease归零；完成必要的typed结果接管；accepted分支调用native try_retire，Created未启动分支使用无callback义务释放规则；等managed callback计数与下述dispatcher义务归零；释放cookie/借用资源/句柄。Owner关闭不取消协调器处理既有操作的能力，最终release前其native调用也必须全部返回。所有阶段均不持有业务锁跨await。

### 7.1 托管dispatcher是独立的排空维度

native callback结束不表示已经复制并排队的用户handler已经结束。notification subscription另有`DispatchOpen / DispatchClosing / DispatchDrained`、pending条目/bytes与active-handler计数。dispatcher开始执行handler时，必须在与关闭相同的原子门下检查DispatchOpen并增加active-handler；关门后不得启动新的本订阅handler。

v1显式Dispose采用**discard-pending、join-active**：关门时取走所有尚未执行的普通事件条目，归还其已拥有copy/lease与预算；正在执行的handler允许退出，异步handler的计数直到其ValueTask实际完成才归还。已经关门后到达的native通知只完成所需copy/ack或丢弃协议，不调用应用；不能遗失必须交给内部协调器的terminal/error/credit清理消息。若领域要求正常stream EOF前drain所有事件，它可以另外定义drain模式，但不能暗中改变显式Dispose的v1语义。

成功DisposeAsync同时保证native来源静默、managed取消/control/start清理完成、pending=0且active-handler=0，之后不再开始或继续执行本订阅的任何用户handler。等待active-handler在它自己的调用scope之外完成；检测自等待的规则不变。handler永久挂起时，关闭也不能假成功，须保留context/预算并暴露handler阶段与age；取消等待方不强制销毁仍在用的payload。

原生decision profile没有独立排队handler，其user调用由native callback计数涵盖。普通Task的terminal通知不运行用户handler，使用D06预分配terminal latch；不能把订阅dispatcher与Task continuation混成同一个计数。用户自己启动并脱离handler的后台工作不属于框架能join的handler范围，其不得保留已结束借用。

每个使用异步callback的Engine需要一个有界清理协调队列；同步Engine不需要。每个context最多有一个排队清理项，退避重试合并到Engine的一个计时源；不能每次PENDING创建一个无限制Task。调用完成路径和start返回路径都可通知协调器，但通知不是静默证据，最终仍查询try_retire。没有进展时保留拥有权、占用原有预算、暴露阶段与age，停止该Engine新准入；超时不能触发unsafe free。

## 8. 安全性质与活性假设

必要性质：`Retired => future_native_callbacks=0`；`callback_access(cookie) => cookie_live`；`free(cookie) => setup_settled && managed_cancel_drained && control_leases=0 && managed_callbacks=0 && native_retired`；每个cookie最多释放一次。notification订阅还要求`DisposeAsyncSuccess => DispatchDrained && pending=0 && active_handlers=0`；具体NoRegistration/StartSkipped初始化哨兵遵从D06，不等待没有发起的步骤。

活性另外依赖native执行器继续推进、停止请求实际被处理、清理协调器可运行和通知/重试没有永久丢失。仅证明计数为0的安全条件不证明它们最终会达到0。恶意迟到callback不属于可恢复使用错误；生产适配器必须由实测证明不会产生它。

## 9. 正常、失败与版本兼容

正常：create→初始化→start→事件→request_stop→最后callback返回→try_retire OK→managed排空→release。start失败走未接管清理；handler异常映射失败且stop；Engine poison停止新事件但允许终态/清理通道按D08完成。

callback table只允许追加字段与capability协商；新callback类型不能在旧调用方未声明支持时调用。v1 flags为0，非零保留位拒绝；不读取超出struct_size的字段。不以改变cookie含义或旧event payload布局进行兼容升级。

## 10. 验证矩阵与Plan输入

| ID | 必须制造的交错/故障 | 通过条件 | Delivery |
| --- | --- | --- | --- |
| CB-01 | start内同步回调；回调先完成而start尚未返回 | context保持有效，start返回前不释放句柄 | A06、A07、A20 |
| CB-02 | stop与callback准入竞争；多线程并发callback | 线性化点明确，全部in-flight计数配平，退役后无callback | A06、A19、A20 |
| CB-03 | callback内部Dispose、嵌套callback、禁止的自等待、managed队列已有事件/异步handler仍在途 | 非阻塞停止；拒绝自等待；关门后不再启动handler；pending释放且active归零后才关闭成功 | A06、A18 |
| CB-04 | 取消注册同步调用/回调内自DisposeAsync例外 | 从外部排空后再报告关闭完成 | A07、A19 |
| CB-05 | GCHandle复用压力、迟到通知和重复终态 | 正常协议无错误目标调用；违规负例在隔离进程可诊断 | A20 |
| CB-06 | 非blittable UCO、callback抛异常、诊断自身失败 | analyzer拒绝非法签名；普通异常不越ABI；致命负例按预期退出 | A12、A14、A15 |
| CB-07 | PENDING长期不结束、队列满、执行器停止 | 不UAF、不无限排队，预算与pending年龄可观测 | A08、A21、B22 |

Windows/Linux真实AOT、CPU架构、compiler/ABI、原始日志和制品hash分别验收。已有Python模型和上游测试源码都不能替代这些记录。

## 11. 设计研究问题处置

Q04可在独立审查后关闭“采用什么callback回收协议”的设计问题：v1采用独立stop/retire、显式lease、外部managed取消排空和非阻塞清理。验证义务CB-01～07和LT/AS系列继续在A06/A07/A19/A20等任务保持pending。未来引擎只需实现对应能力profile；无需把全部Engine放入同一全局runtime。

## 14. 本次完成复核与调度边界（2026-11-13）

[R08 完成报告](../research/topics/R08/report.md) 保留已有 YAHA/Godot/.NET 源码链，并补入 UniFFI scheduler/future 的精确源码：其外部 continuation 在 mutex 外调用，free/cancel 也可能触发已保存通知，因此不能把某个框架的 free 直接套作 NativeWeave quiet 保证。

[本次真实探针](../../verification/interop-completion/linux/result.json) 在 Linux 普通与 AOT 中各执行 32 次受控 native-thread callback/GC/退休交错；callback 在途时 retire 保持 pending，已返回且 managed 注册排空后才允许回收。探针为制造竞争临时阻塞 callback；生产 callback 必须维持本契约的非阻塞通知行为，不复制该测试屏障。取消 token 已取消时 Register 内同步回调，以及 DisposeAsync 等待在途取消回调也实际执行。

通知 mailbox 的 dirty 与 scheduled 状态须在同一原子状态或同一短锁下修改。worker 清除 scheduled 前必须原子复查 dirty；旧快照不能覆盖新通知。[负例模型](../../verification/interop-completion/mailbox-model.json) 找到 stale-check 丢唤醒；候选仅在其有限顺序一致范围内无反例。完整容量、重试、关闭规则由 [D09](concurrency-v0.1.md) 唯一统筹。独立审查接受研究设计不要求 A06/A20/B14 已完成产品 dispatcher 和长时间压力测试。


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
