# R26 — Kestrel 与纯 C# Native AOT Server 基线

日期：2026-11-12。输入 packet：0.1.1，hash 与两个合并基线见 [evidence.json](evidence.json)。状态：限定源码研究已形成设计选择，待独立审查；没有运行 C#、上游测试或 Native AOT 应用。实现规范已同步写入 [D18](../../../server/hosting-and-streaming.md)，不等待其他研究全部完成。

## 1. 研究结论与边界

选择 .NET11 Kestrel + Minimal API + 静态 route/JSON 为默认服务器。理由是已有成熟HTTP状态机、取消、连接管理、Pipelines和静态生成入口，能保留自然C#应用体验，且managed-only应用不需要NativeWeave native runtime。Rust Server只有独立能力或等价完整负载证据足够时才提升为推荐路径。Q15的默认架构选择可以关闭；“哪些负载更快”仍由B23实测，不因为默认决定形成就虚构性能结论。

非目标：重写HTTP、把Kestrel所有middleware宣布AOT兼容、穷尽全部Kestrel源码、实现本项目产品代码。此前v10/v11初读保留历史身份；本轮在固定v11重新读相关路径并扩展关闭/限额/生成器，不改旧证据版本标签。

## 2. 固定源码与已读范围

ASP.NET Core `v11.0.0` → `1def4cdc07dc10fc267136060e3ef5c1a96d4a99`。

| 文件/符号 | 阅读范围 | 证据 |
| --- | --- | --- |
| `KestrelServerImpl.cs` / StopAsync, Dispose | 240–291 | R26-E001 |
| `Infrastructure/TransportManager.cs` / StopTransportsAsync, UnbindAsync | 119–193 | R26-E002 |
| `KestrelServerLimits.cs` | fields、buffer/body/connection setters | R26-E003 |
| `Http/HttpResponsePipeWriter.cs` | 全文件 | R26-E004 |
| `Core/test/HttpResponsePipeWriterTests.cs` | 全文件 | R26-E005 |
| `Http.Extensions/gen/Microsoft.AspNetCore.Http.RequestDelegateGenerator/RequestDelegateGenerator.cs` | 全文件 | R26-E006 |

不可变URL、blob、精确范围在evidence；[coverage.json](coverage.json)如实列出未读的`HttpProtocol.cs`正文（只检索过symbol）。最初猜测的RDG短路径不存在，已通过固定commit目录定位到上述真实路径。没有把目录枚举算作实现阅读。许可证已查固定`LICENSE.txt`为MIT；未复制上游实现；实际打包及传递依赖NOTICE仍由B24核对。

## 3. 公共入口到内部生成

应用采用`CreateSlimBuilder`、明确`MapGet/MapPost`和source-generated `JsonSerializerContext`。已读RDG `Initialize`建立incremental syntax provider，筛选endpoint invocation，构造endpoint model；对诊断逐条报告，仅将没有diagnostic的endpoint传入interceptor/helper生成。由此可以选择“把NativeWeave预算/契约插件接在现有编译期入口，而不是再发明反射路由器”。

这段读取没有证明每种参数绑定、私有DTO、泛型handler或middleware都支持。B15应将实际生成代码纳入快照/编译证据，并在AOT配置中让不支持的endpoint产生可操作错误；不能悄悄回退到动态绑定，再以普通JIT单元测试成功宣告AOT完成。官方可访问NativeAOT文档view10.0作为功能边界参考，实际v11兼容以固定SDK的应用编译/运行作最终证据。

候选最小API见D18。对单个流式endpoint，可保持框架Pipelines习惯：

```csharp
// 设计草案，未编译；HandleBufferAsync必须在AdvanceTo前完成对buffer的使用。
while (true)
{
    var result = await context.Request.BodyReader.ReadAsync(context.RequestAborted);
    var buffer = result.Buffer;
    try { await HandleBufferAsync(buffer, context.RequestAborted); }
    finally { context.Request.BodyReader.AdvanceTo(buffer.End); }
    if (result.IsCompleted) break;
}
```

真实产品不能从这个片段推导无限重试/重置总deadline；异常、`IsCanceled`、业务只消费部分buffer以及reader owner是否可调用Complete，必须遵循宿主API边界。片段表达borrow在advance前结束，不能保存`ReadOnlySequence`到detached工作。

## 4. 关闭与释放调用链

`KestrelServerImpl.StopAsync`用Interlocked把首次stop与重复调用分开，后者等待同一个stopped TCS。首次stop停止heartbeat、取消内部stop源，再进入bind semaphore后调用TransportManager；异常写入共享TCS，finally释放配置/CTS/semaphore。`Dispose`用已取消token调用此路径，表示强制收尾方向，而不是一个“Dispose自然等于优雅关闭”的保证。

TransportManager先对所有listener `UnbindAsync`，其内部等待accept loop结束；随后并行请求各transport关闭连接。返回未全部优雅关闭时，再调用abort；最后dispose listener并从active集合移除。应用级handler、数据库commit、outbox和diagnostic exporter的生命周期还需要NativeWeave宿主协调；不能把“listener已关”当作全部业务资源可释放。

NativeWeave采用D18 `Accepting -> Draining -> Aborting/Stopped -> Disposed`，且和Core native quiescence区分。若独立nativeengine无法证明callback停止，宿主可以记录关闭失败并退出进程，不能提前free callback cookie或卸载库来伪造准时shutdown。

## 5. Response writer 与失败路径

`HttpResponsePipeWriter`有Closed/Open/Aborted，`StartAcceptingWrites`只从Closed开启；Stop把状态关掉并返回complete task。ValidateState在Open或Aborted中首先观察调用token；Closed才抛ObjectDisposedException。因此abort、请求取消、complete和writer dispose不是同一个状态，外层不能用一个布尔值替代。

测试逐项断言stop后`Advance/GetMemory/GetSpan/Complete/FlushAsync/WriteAsync`拒绝访问。本轮只读测试，没有执行。D18据此要求headers已提交后错误只能终结stream，不能再追加一个错误response；body memory的owner还要等消费者释放。

一个具体待核验细节：该固定版本`CompleteAsync(Exception? exception)`内部调用`Complete()`，没有传入参数。源码足以观察这一点，但没有最小复现来断言用户可见bug或所有宿主路径都受影响。NativeWeave不能依赖未经核验的该参数传播语义；B16加入complete/error/abort行为回归，使用受支持的错误终结路径。它不改变选择Kestrel的总体设计，也不是把上游源码改进纳入本轮产品实现。

## 6. 配额、成本及平台差异

读取v11默认值：连接数null/无限，request buffer1MiB、response buffer64KiB、headers32KiB、body30,000,000bytes。它们控制不同环节；乘以应用并发数也不等于RSS。HTTP2的stream/window、TLS及socket buffer、GC/ArrayPool、线程栈和应用队列都要独立列账。

因此D18显式配置连接、stream、活动request、等待request与应用byte credit。默认C#路径避免FFI/runtime启动/额外body复制；streaming减少整body分配，却增加分块调度和flush次数，应测量而非宣称零分配。32KiB chunk只是参考profile；吞吐、尾延迟和buffer驻留共同决定配置。

Windows/Linux的TLS provider、证书链、socket close/reset、AOT本机工具链与发布依赖需要真实分别运行。HTTP3、WebSocket/CONNECT和musl等特殊profile明确选配。一个host或RID通过不能外推全部平台。

## 7. 可执行验证义务与交叉Review

| 任务 | 需执行/保存的内容 |
| --- | --- |
| B15 | net11 Minimal API生成输出；完整应用trim/AOT warnings；linux-x64/win-x64发布二进制HTTP1/2收发；证明managed-only没有NativeWeave native加载 |
| B16 | 慢上传/慢下载、部分消费body、断流、完整body EOF与transport close区别；writer complete/abort竞争；byte/waiter上限与溢出 |
| B20 | readiness先关闭、listener解绑、业务drain、deadline、callback资源静止；COMMIT Unknown不得被host dispose改写 |
| B22/B23/B24 | 长连接与churn、真实RSS/GC/socket/线程、等价TLS/HTTP性能矩阵及平台发布 |

候选命令与项目入口在D18；本轮执行状态全为not-run。代码片段仅设计草案，不能升级为编译通过。

交叉Review：R02检查RDG/DTO生成策略与稳定工具链；R27检查portable handler不虚构ASP.NET兼容；R29检查Kestrel预算覆盖边界、body EOF/abort、复制时双份credit。影响文件为D18及B15/B16/B20/B23；本作者不自行将C-SERVER-001标为accepted。
