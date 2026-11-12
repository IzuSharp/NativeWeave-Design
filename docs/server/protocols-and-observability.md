# D19 — gRPC、MCP、TLS 与跨语言诊断

| 项目 | 值 |
| --- | --- |
| 契约 | C-PROTOCOL-001，0.1.0 |
| 输入任务 | R28、R30；交叉 R02/R07/R08/R29/R34、D18/D20 |
| 基线 | Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5` |
| 状态 | 设计规范 0.1.0；接受状态由 registry 中相同内容哈希与独立 Review 确定；所有本文件 C# / Rust 片段未编译；产品、AOT 与协议认证未验证 |
| 核验日期 | 2026-11-12 |

## 1. 需求、边界与选择

gRPC、MCP 和 telemetry exporter 都是可独立引用的 managed 包；不使用它们的应用没有这些包引入的程序集或依赖。它们建立在 [D18](hosting-and-streaming.md) Kestrel、预算、deadline、关闭及独立 Engine 边界上，不向 Core 塞入业务协议。独立无数据库的 managed 服务保留通用 .NET diagnostics；使用 Database 的应用仍依赖必需的 Rust DB Engine，不能因为协议包为 managed 就声称整个应用没有 native dependency。Rust Engine 只接收小型、可选的诊断上下文。

本轮已选择版本化协议 profile、静态可达注册与有界流语义；不承诺所有历史版本、所有插件、动态 assembly 扫描、任意 JSON `object` 图或任意浏览器 transport。协议升级修改独立包/profile 与兼容矩阵，不要求修改 Core ABI。

源码证据见 [R28](../research/topics/R28/report.md) / [R30](../research/topics/R30/report.md)。已固定 grpc-dotnet `v2.85.0`（`a7767e28a2c2f4e89a17e9efb95f75e8a82637d0`）、MCP C# SDK `v2.4.0`（`4cbf42ef107763f0bc75c358af8cb2dfe47a769a`）、MCP spec `2026-07-28`（`5f5440bb26a62e2cf3440b92da5a667efa03b267`）、OpenTelemetry .NET `core-1.21.0`（`51c6db11dadde6ed5019af4f42332860f1a5d8da`）及 .NET 11。版本是当前研究与候选依赖基线，不是所有平台已兼容的认证。

## 2. gRPC：生成服务、受限消息、明确终态

采用 grpc-dotnet 与由 `.proto` 编译生成的 service/DTO/marshaller；Google.Protobuf 等传递依赖在 B18/B24 锁文件精确锁定。本轮不手写 HTTP/2 framing 或 protobuf 运行时，也不把任意运行时 service discovery 作为 AOT 路径。生成代码、服务泛型及 DTO 必须有静态调用入口；反射服务（若产品显式需要）是另一个有限 descriptor profile，不能全程序集 root。

```csharp
// 草案：B18 必须在固定 net11.0 与 NuGet lock 上编译并发布 AOT。
builder.Services.AddGrpc(options =>
{
    options.MaxReceiveMessageSize = 1024 * 1024;
    options.MaxSendMessageSize = 1024 * 1024;
});
app.MapGrpcService<WorkItemsGrpcService>();

public override async Task Watch(
    WatchRequest request, IServerStreamWriter<WorkItemEvent> writer,
    ServerCallContext context)
{
    await foreach (var item in events.ReadAsync(request, context.CancellationToken))
        await writer.WriteAsync(item, context.CancellationToken);
}
```

Message cap 是参考 profile 的选择；累积 stream 仍由时间/速率/总量预算约束。`WriteAsync` 返回后才能发下一条；不得以 `Task.WhenAll` 并行写同一 writer。grpc-dotnet 的 `HttpContextStreamWriter.WriteCoreAsync` 在锁内检查 pending write，并在 finally 释放 token registration；对应测试验证 concurrent write 拒绝、默认 flush 和 BufferHint 不立即 flush。应用不能把 BufferHint 当无界批处理许可。

接收限额同时覆盖 wire message length 和解压输出；v2.85.0 `PipeExtensions.TryReadMessage` 把同一限额传入解压 helper，超限产生 ResourceExhausted。B18 仍须用高压缩比输入、分片及超大 declared length 检查真实输出分配峰值，不以 header cap 代替解压 cap。未知压缩方式拒绝；默认 profile 关闭未验收压缩器，避免扩大攻击面。

每个 RPC 具有统一最终状态：正常 OK；业务定义 status；deadline exceeded；取消；协议/连接错误。`ServerCallContext.CancellationToken` 在有 deadline 时来自 deadline manager，否则来自 RequestAborted；不能只监听 `HttpContext.RequestAborted`。已读 `DeadlineExceededAsync` 先设置 grpc status/trailers 并尝试完成 response，然后 reset/abort。NativeWeave 不再写第二份 HTTP JSON 错误；应用响应已经 committed 时通过协议终态结束流。客户端断开与服务端未执行没有等价关系，涉及 DB COMMIT 的 Unknown 由业务 RPC 返回/恢复协议保留。

默认要求经过验收的 HTTP/2 与 ALPN/TLS 配置。HTTP/1 gRPC-Web、HTTP/3、浏览器代理行为为显式独立 profile，不因普通 REST 成功自动放行。

## 3. MCP：协议版本直接决定生命周期

### 3.1 显式 profile

| Profile | 设计支持状态 | 会话/消息语义 | 配置与验收 |
| --- | --- | --- | --- |
| `Mcp2026_07_28` | 默认推荐候选，B19 实施目标 | 每次请求提供版本/能力 metadata；无 initialize 握手、无协议 session；POST JSON 或该请求的 SSE response | SDK `Stateless`，固定版本；GET/DELETE 为405；不生成/回显 session ID；现代 conformance fixture |
| `Mcp2025_11_25` | 应用显式选择的兼容候选，不与新 profile 隐式混合 | initialize、协商、session/旧 transport 规则按旧规范执行 | 独立 endpoint 或明确 hybrid；会话数量/idle timeout/存储有界；单独 AOT/conformance |
| `HybridInitializeClients` | 只有兼容需求与独立验收后启用 | SDK `StatefulForInitializeClients`：旧 initialize client 为 stateful，新 metadata client 为 stateless | 明确允许版本集，逐请求路由，隔离两种状态/取消语义 |
| 未列版本、任意旧 SSE | 不自动支持 | 返回协议定义的 unsupported version 错误/能力信息 | 禁止为“连接成功”静默退回未知版本 |

应用可主动选择旧 profile；默认推荐最新稳定是本项目设计选择，不是迫使所有应用升级，也不承诺无限历史兼容。版本、SDK major、transport、serializer、server capabilities、认证方式都写进发布 manifest。SDK 升级不能静默改变应用 profile；客户端降级须调用者策略明确允许，并记录最终版本。遇现代 unsupported-version 结构化错误不能误当成“旧 server”而盲试 initialize。

### 3.2 已核实的新语义

[官方固定版本 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) 与 SDK `HttpServerSessionMode`、`McpProtocolVersions`、`StreamableHttpHandler` 一致：现代请求使用 per-request metadata，旧的 session ID、GET unsolicited SSE 与 DELETE terminate session 不适用。关闭某次请求的 response stream 会取消该请求；这不同于旧 session/profile 中 SSE 断线/恢复的处理，不可用一个笼统“断流只是重连”规则覆盖两者。

入口检查 HTTP method、Content-Type、Accept、Origin/认证及 header/body 一致性。`MCP-Protocol-Version` 与 body metadata 必须一致；`Mcp-Method` 必须与 JSON-RPC method 一致；需要名称的 method 校验 `Mcp-Name`。header 名大小写不敏感，值按规范解释；不能直接把用户任意 Unicode/控制字符写进 HTTP header。custom metadata 镜像遵守规范编码规则，不自造 JSON/HTTP 双重解释。header 与 body 不一致是错误，不择一静默覆盖。SDK 在 parse 后带请求 id 返回错误，这意味着 NativeWeave 仍要在 parse 前限制 bytes、depth、headers，不能认为后置校验防止解析资源消耗。

现代 profile 不把工具实例/数据库 transaction 保留在隐含 session。每次调用的鉴权、服务 scope、预算和 cancellation 均独立建立；长期工作先转为显式持久 operation，再给授权的 status/query 入口，不能让一次 HTTP SSE 永久持有 DB transaction。协议 tool cancellation 是请求终止意图；外部副作用按 D20 幂等与恢复语义处理。discovery/tool schema 也是有限集合，不能把用户任意输入转成运行时注册工具。

### 3.3 静态注册、序列化与 C# API

```csharp
// 全部 NativeWeave wrapper / generated name 是未编译的候选 API。
builder.Services.AddMcpServer()
    .WithTools(GeneratedWorkItemTools.All)
    .WithHttpTransport(options =>
    {
        options.SessionMode = HttpServerSessionMode.Stateless;
    });
// B19 同时配置 SDK 的固定 ProtocolVersion="2026-07-28"；
// 具体 options binding 由版本锁定后的编译 fixture 核对，不使用隐式 SDK default。
app.MapMcp("/mcp");
```

`GeneratedWorkItemTools.All` 是 B19 生成的 `McpServerTool[]`：明确 tool 名、输入 JSON schema、输出 schema、typed handler 与已知 DTO 的 `JsonTypeInfo`，不扫描 assembly，不从任意 CLR `Type` 建 schema。`McpServerTool.ProtocolTool` 与 `InvokeAsync` 是已读 SDK 扩展口，实例枚举注册 overload 只添加明确实例。生成器使用 SDK 提供的序列化和 protocol types，不再实现另一套 JSON-RPC。

可保留更简洁的 `WithTools<WorkItemTools>(ApiJsonContext.Default.Options)` 有限泛型注册 profile；源码用 `DynamicallyAccessedMembers` 标记并仍通过 `GetMethods`/attribute 发现该固定类型。它是 **受约束的反射路径，不是零反射生成器**。只有该精确泛型/DTO集合的 trim/AOT 测试通过才放行；non-generic `IEnumerable<Type>`、`WithToolsFromAssembly` 的 RUC 路径不进入严格 profile。

DTO 使用源码生成的 `System.Text.Json` metadata；闭合泛型和集合类型必须可达。拒绝无 schema 的任意 `object` 返回、未知派生类型与运行时匿名模型；诊断指出具体 tool/parameter/result/path。输入 schema 验证、业务鉴权和 serializer 都不能互相代替。工具名、路由和 JSON 属性名兼容性由 package profile 管理，重命名需 migration/version 决定。

### 3.4 AOT 证据的真实限制

SDK 自带 AOT TestApp 的 csproj 设置 `net10.0`、`PublishAot=true`，但同时 `TrimmerRootAssembly` 保留多个 SDK assembly；Program 使用 in-memory stream。它说明上游有 AOT 覆盖入口，**不证明** NativeWeave 的 net11 HTTP endpoint、静态注册、精确 DTO、TLS 与 trimming 组合已经工作。本轮只读源码，没有运行该测试。B19 必须使用最小 app、无全程序集 root、明确 profile，运行发布后的 Windows/Linux 二进制，验证 discovery、tool success/failure、取消、畸形 header、超大 JSON、unknown version、GET/DELETE 和 shutdown。

## 4. TLS、身份与错误边界

TLS 只有一个终止 owner，见 D18。MCP Origin 校验和 CORS 不能代替认证；反向代理传播的身份只来自已配置可信边界。每个 tool/RPC 绑定显式权限和资源范围；异常信息、SQL、token、证书私钥、request body 不进入默认 telemetry。MCP tool error、JSON-RPC error、HTTP error、gRPC status 与 Engine error 分层映射，不能把内部统一错误码直接当所有协议的 wire code。

协议 parser fuzz 至少覆盖长度溢出、分片、压缩炸弹、JSON depth、重复/冲突 headers、非法 UTF-8、重复 JSON 属性的确定处理、unknown method/tool、trailer 竞态、客户端取消与业务提交竞争。协议本身的错误/版本规则由固定规范决定；本项目不为方便创建宽松 fallback。

## 5. Diagnostics：C# 默认、跨 FFI 小上下文

默认用 `ActivitySource`、`Meter` 与结构化日志接口；OpenTelemetry exporter 为选装包。dotnet/runtime 11 的 `ActivitySource` 无 listener 时直接不创建 activity，故昂贵 tags、links、formatted strings 应在 enabled/sampling 判断之后创建。`HasListeners` 只是快速判断，不能取代 sampling；无 listener 仍可按配置转发已有 trace context，不需要创建 Activity 对象。

Engine 入口仅传 optional `TraceContextV1`；不把 `Activity`、`ExecutionContext`、Rust span guard 或 GCHandle 当通用诊断数据跨边界。下面是领域扩展 metadata 的候选布局，非 Core 强制字段，D08 的 `ErrorRecord.correlation_id` 仍只是关联编号：

| offset | 字段 | wire 类型/约束 |
| --- | --- | --- |
| 0 | size | u32，v1 为32，按有界 extension 读取 |
| 4 | version | u16，v1 为1 |
| 6 | trace_flags | u8，只保留该 profile 理解的 flags |
| 7 | reserved | u8=0 |
| 8 | trace_id | 16 bytes，W3C 字节次序；全零无效 |
| 24 | parent_span_id | 8 bytes；全零无效 |

布局仅含固定字节，不含平台指针；C# explicit/sequential layout 与 Rust repr(C) 的 size/offset assertions 由 B20 编译验证，当前未运行。Engine 不支持此 capability 时忽略，不影响业务结果。可选 tracestate 通过单独有界 UTF-8 元数据传入并在同步入口复制，默认不转发 baggage；完整格式校验按 [W3C Trace Context 1 推荐规范](https://www.w3.org/TR/2021/REC-trace-context-1-20211123/) §3.2/§3.3，畸形外部上下文开启新 root 并计数，不当作认证/授权依据。该32-byte layout是本项目领域Adapter选择，不是W3C定义的二进制ABI。跨 ABI 的结构越界仍是契约错误，不容忍非法指针。

Rust 内部 tracing span 与 managed Activity 共享 trace/parent 关联，不假设 thread-local 能跨 callback/async 迁移；完成 callback 只带 operation/correlation ID，在 managed continuation 恢复该请求 scope。重试 child span 必须保留 attempt 编号，数据库 Unknown 为独立可观测事件，不写假 Rollback/Succeeded。采样只影响诊断，不影响资源释放或业务计数。

指标 tag 允许 route template、protocol profile、provider、规范化 error category；禁止 request ID、operation ID、SQL 字面值、任意 tool argument 成为无界维度。trace events/attributes 每项长度、每 span 数量、总 exporter queue 与批次大小有界；reference profile 例如每 span 32属性、字符串最大256 UTF-8 bytes、队列2048条，同时限制每条payload。数量界限不是字节/RSS界限。

OpenTelemetry `BatchExportProcessor.TryExport` 在队列满或自旋失败后 drop 并计数，shutdown 给 worker/exporter 传剩余 timeout。NativeWeave 采用相同故障隔离原则：网络 exporter 不在 FFI callback 或业务锁内阻塞；满队列丢诊断并计 drop，不阻止业务完成。必须实测 callback 最坏耗时与 exporter 故障时CPU，不把“有 bounded queue”当零成本保证。关闭先结束业务/资源，再给 telemetry 有限 flush deadline；无法导出的诊断不得造成永不退出。

## 6. 正式验证义务与设计关闭建议

| 既有任务 | 必需验收 |
| --- | --- |
| B18 | generated gRPC 服务/DTO；Windows/Linux net11 AOT HTTP/2 真运行；unary/stream、并发write拒绝、deadline、headers/trailers、截断、压缩前后限额；异常与状态一致 |
| B19 | 精确 MCP profile manifest；静态/泛型两种受控注册分别验收；现代/legacy endpoint 各自 conformance；profile错配不静默降级；无root-all AOT；Origin/authn/authz；SSE关闭取消、资源归还 |
| B20 | trace layout size/offset、跨线程parent传播、禁用诊断分配对照、限额/高基数/secret测试、exporter断网/阻塞/关闭deadline；所有丢失有计数 |
| B22/B24 | 协议/SDK升级差异、TLS证书重载/关闭、跨平台兼容；长跑无session/registration泄漏；所选profile的实际发布二进制回归 |

Q17 的设计问题可关闭为“独立 gRPC/MCP 包、生成/受控泛型注册、显式版本 profile、分层有界流与 diagnostics”；并不声称 B18/B19 的真实 AOT、兼容性或生产验收完成。新的 SDK 或协议变更按该接口局部修订，保留固定旧 profile 或明确迁移，不重新设计 Core。

独立 reviewer 应检查：现代与旧 MCP 取消是否混同；metadata/header校验前是否有资源上限；泛型反射是否被误称零反射；native error/correlation 与trace/身份是否混淆；上游AOT fixture是否被夸大为产品证据。许可证也按固定 release 核对：MCP SDK/spec 的当前 LICENSE 记录 MIT→Apache-2.0 过渡、部分旧贡献仍 MIT、非规范 documentation CC-BY-4.0；不得机械标记整个项目为 MIT。本文是原创建议，不复制上游实现；B24 记录实际分发包的 LICENSE/NOTICE/SBOM。
