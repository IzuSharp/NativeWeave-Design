# R30 — 跨语言诊断、低开销路径与有界 exporter

日期：2026-11-12；packet0.1.1、输入baseline/hash见[evidence.json](evidence.json)。状态partially_evidenced：已读.NET与OpenTelemetry关键生命周期及测试；未读全部Rusttracing/metric/exporter实现，也未运行产品性能/AOT。设计已同步[D19](../../../server/protocols-and-observability.md)。

## 1. 已选择的边界

C#应用默认使用ActivitySource、Meter、结构化日志；exporter是独立可选包。没有listener时应避免Activity与高成本tag构造；跨FFI只传小型可选tracecontext与operationcorrelation，不能把Activity对象、ExecutionContext或Rustspanguard当跨语言公共handle。采样、丢日志或exporter断网不能改变业务终态/资源回收。

非目标：默认开启全量payload/SQL日志、任意高基数metrics、统一替换每个Engine的diagnostics库、把correlationID当安全身份、声称telemetry零成本。

## 2. 固定来源与阅读

| 来源 | 固定commit | 路径/范围 |
| --- | --- | --- |
| dotnet/runtime v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | ActivitySource.cs121–141、234–256 |
| opentelemetry-dotnet core-1.21.0 | `51c6db11dadde6ed5019af4f42332860f1a5d8da` | BatchExportProcessor.cs99–203；BatchExportActivityProcessorTests.cs28–53、117–260、300–322 |
| W3C TraceContext1 | 2021-11-23 Recommendation固定URL | §3.2.2字段、§3.2.4版本规则 |

精确URL/blob在evidence；[coverage](coverage.json)不把测试源码当执行结果。runtime固定许可MIT，OpenTelemetry固定许可Apache2。W3C规范支持trace字段语义；D19的32-byte二进制adapterlayout是NativeWeave自己选择，不是W3C规定的ABI。

## 3. Activity从公共入口到分配路径

已读`HasListeners`检查listener集合非空且未disposed；内部创建路径无listener直接返回null。调用者若先构造大tag字典/字符串，库不创建Activity也无法抵消这些成本。因此热路径先检查是否需要诊断，再按实际sampling创建tags；轻量operation计数和失败终态仍可靠维护。

`HasListeners`不是sample决策，也不等同“没有listener就不可转发入站tracecontext”。传入的有效context可按配置传给下游，不必创建Activity对象。跨语言入口捕获的是值，callback任意线程回来后由完成协调器恢复managedscope，不依赖同一个threadlocal。Rustspan的enter/exit作用域只留在Rust执行路径，不能把guard活过FFI并期待managedawait正确处理。

候选C#路径，未编译：

```csharp
using var activity = TraceSource.StartActivity("nativeweave.db.execute");
if (activity?.IsAllDataRequested == true)
    activity.SetTag("db.system.name", providerName);
// correlationId用于事件关联；不记录SQL参数，不放入metric tag。
var result = await operation.ConfigureAwait(false);
return result;
```

失败/Unknown路径记录独立结果分类与有界errorcategory，finally释放scope；不得因没有telemetrylistener跳过cleanup。将Task返回成功与业务durability混为一个spanstatus同样错误。

## 4. Export queue及shutdown调用链

`TryEnterOnEnd`先检查shutdown、登记activeOnEnd，再复查shutdown；竞争失败会撤销登记。这个双检查避免“检查未关闭，尚未登记时shutdown已结束”漏洞。`TryExport`尝试circularbuffer add；只有到batchthreshold的那次enqueue唤醒worker，避免每条都触发kerneltransition。队列满或自旋预算耗尽时drop并计数。

`OnShutdown`以Interlocked进入shutdown，等待已接受的OnEnd使用剩余时间预算，再shutdownworker，最后把remainingtimeout传给exporter。源码支持有界关闭协调，不等于任意第三方exporter能被强制中止；NativeWeave要隔离坏exporter并让业务退出策略明确。

测试定义体现实际反例：queue大小1触发export；已登记但未退出的OnEnd会阻止shutdown完成；有限timeout能结束等待；多线程重复race确保OnEnd要么被拒要么被等待，不留下永远不退出的登记。本轮只阅读测试，没有执行；不能把上游测试名当通过证据。

## 5. NativeWeave采用与不照搬部分

采用可选boundedbatch-export与失败dropcounter；不强制所有Engine依赖OpenTelemetrySDK，不在FFIcallback持锁格式化或同步网络export。D19定义TraceContextV1固定值metadata与可选有界tracestate，CoreErrorRecord.correlation_id保持诊断编号，不代替traceid或authorization。

metriclabels限定routetemplate、protocolprofile、provider、规范化errorcategory；requestID/operationID、SQL、任意用户label不得成为默认无界维度。每span属性数量/单值bytes、event数量、queue条数与每条payload都限制；条数上限不是字节/RSS证明。默认不记录secret、fullbody、rawSQLparameter或私钥；debug采样也需显式有界策略。

诊断本身耗CPU与分配；TryAdd的spinbudget也可能在高竞争下明显耗时。B23应分别测disabled/sampled/fulltrace/exporterfailure，并记录callback耗时、CPU/op、allocations、queue/drop以及业务p99变化，不能只测空listener理想路径。

## 6. API/ABI、平台与验证

32-byteTraceContextV1字段/offset在D19，内容为size/version/flags/reserved/16-bytetraceid/8-byteparentspanid。C#与Rust布局断言、非法size/version/zeroID、unknownflags、tracestate超长与跨线程context恢复必须由B20实际编译/运行；当前布局未编译。FFI可选metadata不支持时忽略，不改变业务语义；畸形外部traceparent开启新root，非法ABI内存访问仍是契约错误。

| Task | 可执行验收 |
| --- | --- |
| B20 | layout静态断言/序列化golden；并发callback和parent关联；admission与shutdownrace；exporter满/失败/阻塞/timeout；drop计数与不泄漏secret |
| B22 | telemetry在24h/72h churn/取消/故障负载下无registration/Activity/buffer持续增长；业务资源不能被exporter保留 |
| B23 | diagnostics开关与采样成本分解，native/managed两侧trace一致且性能测试条件对齐 |
| B24 | 独立exporter包、cleanmachineAOT、Windows/Linuxtimer/thread差异、SBOM与升级兼容 |

Q17中的diagnostics边界有可审查设计决定；真正低开销、无泄漏、跨平台AOT属于这些实现义务。独立Review接口：R08检查callback热路径与寿命；R29检查budget不是只看count；R34检查输入trace不能变成身份/secret泄露；R28检查协议error/Unknown与trace映射。
