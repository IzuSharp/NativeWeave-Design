# R30 — 跨语言诊断、低开销路径与有界 exporter

历史研究始于 2026-11-12，本次补证至 2026-11-13；当前 packet、输入 baseline/hash 见[evidence.json](evidence.json)。本次已补读 tracing 0.1.44 的异步 span/subscriber 边界，并实际运行独立诊断 Native AOT 探针；研究/设计接受仍待独立审查。未读全部 metric/exporter 实现，未执行未来产品性能验收。设计已同步[D19](../../../server/protocols-and-observability.md)。

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

32-byteTraceContextV1字段/offset在D19，内容为size/version/flags/reserved/16-bytetraceid/8-byteparentspanid。C# Native AOT 与 Rust 布局已分别编译执行，size=32、trace_id offset=8、parent_span_id offset=24。非法 size/version/zeroID、unknownflags、tracestate 超长与实际 FFI 跨线程 context 恢复仍由 B20 集成验证；单边布局成功不等于跨语言传输已执行。FFI可选metadata不支持时忽略，不改变业务语义；畸形外部traceparent开启新root，非法ABI内存访问仍是契约错误。

| Task | 可执行验收 |
| --- | --- |
| B20 | layout静态断言/序列化golden；并发callback和parent关联；admission与shutdownrace；exporter满/失败/阻塞/timeout；drop计数与不泄漏secret |
| B22 | telemetry在24h/72h churn/取消/故障负载下无registration/Activity/buffer持续增长；业务资源不能被exporter保留 |
| B23 | diagnostics开关与采样成本分解，native/managed两侧trace一致且性能测试条件对齐 |
| B24 | 独立exporter包、cleanmachineAOT、Windows/Linuxtimer/thread差异、SBOM与升级兼容 |

Q17中的diagnostics边界有可审查设计决定；真正低开销、无泄漏、跨平台AOT属于这些实现义务。独立Review接口：R08检查callback热路径与寿命；R29检查budget不是只看count；R34检查输入trace不能变成身份/secret泄露；R28检查协议error/Unknown与trace映射。


## Current completion and architecture correction (2026-11-12)

The latest user mission requires a Rust Server engine. Kestrel is solely the comparator.
The selected initial design is Tokio + Hyper/hyper-util + Tower, with Axum available
for native routing and composition where needed. Actix remains a worker-affine
alternative and Pingora a proxy-specific engine; neither is copied into C#. Public
Service/Body APIs suffice for the current Adapter; no fork is justified by this study.
Prior passages describing optional Rust or a Kestrel product host are superseded as
architecture decisions, while their scoped source/evidence identities remain historical.

D18 now defines the native Handler/Body bridge and retirement protocol; D19 binds
Tonic/rmcp/rustls to that same host. New actual protocol/network/TLS evidence is in
`verification/server-completion/`, with exact commands/source hashes and retained prior
attempts. Native HTTP1/HTTP2 loopback and bounded TLS tests are real executions, but
not a C# Server product, equivalent-load benchmark or production soak. The existing
Body/Bytes/permit and finite credit models are reused without inflating their coverage.

Research-design closure is proposed for this bounded source/lifecycle study; future
B16/B17/B20/B22/B23 implementation, complete cross-language transport and long-load
acceptance remain explicit obligations. Independent review and graph integration
must bind this exact revised content before acceptance.


## 7. Completed tracing source and actual Native AOT diagnostics probe

New source identity: tracing0.1.44, crate VCS commit
`2d55f6faf9be83e7e4634129fb96813241aac2b8` in `tokio-rs/tracing`.
Read `tracing/src/span.rs:596–641,780–790`, `instrument.rs:176–231,277–324,378–389`
and `subscriber.rs:1–63`; source hashes and crate provenance are in
[source-inspection.json](../../../../verification/server-completion/source-inspection.json).
`Instrumented<Future>::poll` enters/exits the span per poll; `WithDispatch::poll`
sets the captured dispatcher per poll. A Span::enter guard held across await leaves
unrelated work inside the wrong span. A thread-local subscriber is not automatically
propagated to another worker; library code must not seize the process-global subscriber.
The Server adapter uses an explicitly owned dispatcher plus instrumented futures,
with value context carried in operations; callback scheduling restores managed context.

[DiagnosticsProbe](../../../../experiments/server-completion/diagnostics/Program.cs)
was published and executed as Linux x64 .NET11 Native AOT with warnings as errors.
The exact run is `verification/server-completion/diagnostics-local-2/run.json`.
Eleven assertions cover the 32-byte C# layout, disabled listener state, null Activity
creation, no steady-loop current-thread allocation, avoiding tag construction,
explicit remote parent, managed await/Task parent propagation and listener disposal.
The 200000-call observation was 13.589 ns/call and 0 allocated bytes on this run;
this single-process observation is not a transferable throughput claim or native-memory
measurement. It is the required disabled-observer cost witness. The initial failed
compile attempt is retained separately; no failed run is presented as success.

A separate Rust1.100 layout witness also executed successfully in
`verification/server-completion/diagnostics-rust-layout/run.json`. These probes do not
include native callback-to-managed trace propagation, exporter saturation or arbitrary
OS targets. They close the bounded design questions and leave concrete integration/
load obligations with B20/B22/B23, not a blanket requirement to redo the architecture.

## Windows observation failure and corrected measurement boundary

The first Windows diagnostics CI at run43390177287 passed the layout/listener/null
checks but failed its zero-allocation assertion. Its raw stdout/stderr and run manifest
remain under `verification/completion-ci/43390177287/diagnostics-windows-2022/`.
That version included the first clock calls inside the allocation measurement and
printed the numerical observation only after the assertion, so the failed run does
not preserve an allocation count and cannot attribute the extra allocation to
ActivitySource alone. It is not reported as a successful Windows observation.

The corrected source warms clock/counter setup outside the measurement and places
only the `StartActivity` loop inside the allocation counter window; its numerical
observation is printed before either assertion. The Linux NativeAOT rerun at
`verification/server-completion/diagnostics-reviewed-local/run.json` passed all eleven
checks and observed 200000 null returns, zero current-thread allocated bytes and
12.437 ns/call. This is another scoped observation, not a promise of a universal
zero-allocation or timing result. At that checkpoint Windows still required its corrected run; the threshold was not raised to mask its failure. The later retrieved run below closes this finite platform-evidence gap.

## Final corrected Windows/Linux evidence and diagnostic defaults

Existing Actions run43401371233 at source `5bb128424259f3d9cf594b4e50d7688ad5b6541e`
has now been retrieved, not rerun. The exact source/CRLF transformation, archives,
logs and binary hashes are recorded in `verification/server-completion/diagnostics-final-ci.json`.
Both Release Native AOT executions passed all11 assertions and observed200000 null
returns and0 current-thread allocated bytes in the StartActivity-only warm loop.
Windows observed16.634 ns/call; Linux20.468 ns/call. These single-run timings do not
compare operating systems or prove universal zero overhead. Debug, Meter/log sinks,
enabled sampling/export, native callback propagation and native memory were not measured.

D19 now makes configuration explicit: Release and Debug install no listener/provider,
process-global Rust subscriber or exporter by default. The optional convenience log preset
uses Warning/Error through application-configured sinks, with IsEnabled before formatting;
Debug does not automatically switch on high-volume tracing. Resource safety and retirement
checks stay active independently. B20/B23 implement and measure the explicit disabled,
Debug-local, sampled/full and exporter-fault modes; these product rows are not claimed here.
