# R28 — gRPC、MCP 的固定协议、静态注册与 AOT 边界

日期：2026-11-12；packet0.1.1及hash见[evidence.json](evidence.json)。研究状态：**partially_evidenced**，已读关键生命周期/错误/测试片段，未穷尽全部候选路径；设计选择已写[D19](../../../server/protocols-and-observability.md)，等待独立Review。未编译或运行C#、上游测试及NativeAOT。

## 1. 选择与非目标

gRPC采用独立managed包、固定grpc-dotnet与生成protobuf service/DTO；MCP采用独立managed包、固定协议profile、显式静态工具集或经过验收的受控泛型注册。两者初始宿主为Kestrel，不要求Rust；可选nativeServer不能仅因支持HTTP2就自动声称同样兼容。

不实现第二套JSON-RPC/protobuf/HTTP2协议栈；不支持任意动态assembly发现；不将上游AOT示例等同本项目产品AOT；不把旧MCP session/断线行为套到现代协议。Q17设计问题可按D19决定关闭，真实AOT与互操作性转B18/B19/B24。

## 2. 固定来源

| 来源 | 固定版本和SHA | 新阅读范围 |
| --- | --- | --- |
| grpc/grpc-dotnet | v2.85.0 / `a7767e28a2c2f4e89a17e9efb95f75e8a82637d0` | writer及测试、deadline/cancel、PipeExtensions与解压helper |
| modelcontextprotocol/csharp-sdk | v2.4.0 / `4cbf42ef107763f0bc75c358af8cb2dfe47a769a` | 版本常量、session enum、HTTPhandler、modern/legacy测试、tool注册、AOT项目与Program |
| modelcontextprotocol/modelcontextprotocol | 2026-07-28 / `5f5440bb26a62e2cf3440b92da5a667efa03b267` | 固定StreamableHTTP、cancellation与versioning规范片段 |

每条结论的精确文件、symbol、locator、blob与run状态见[evidence](evidence.json)；[coverage](coverage.json)区分读过源码、读过测试定义和未执行测试。grpc-dotnet固定LICENSE为Apache2；MCP固定LICENSE声明MIT到Apache2过渡、未授权relicense旧贡献仍MIT、非spec文档CC-BY4，不能直接用历史MIT标签描述当前整包。本文原创建议不复制上游产品代码，B24核对分发包NOTICE/SBOM。

## 3. gRPC write生命周期与反例

`HttpContextStreamWriter<T>.WriteAsync`进入`WriteCoreAsync`：校验message；若token可取消则注册CancelRequest；观察完成/request-aborted；在writeLock内拒绝已有未完成write，再保存BodyWriter的`WriteStreamedMessageAsync`任务；await后统计write count；finally释放registration。

关键结论是“一条stream一个pending write”，不是“每次都加lock就允许任意并行write”。测试`WriteAsync_WriteInProgress_Error`用未完成response-start任务卡住首write，再确认第二次write失败；另两测试对比默认flush与BufferHint缓冲。NativeWeave保留自然`await writer.WriteAsync(...)`，而非为效率隐藏无界后台发送队列。

`HttpContextServerCallContext.CancellationTokenCore`优先deadline manager的token；否则RequestAborted。deadline路径设置grpc status/trailers、尝试CompleteAsync，再调用stream reset或HttpContext.Abort。错误映射必须留在gRPC协议，不再写REST JSON错误；DB未知提交依然是业务Unknown，不能被RPC取消吞掉。

## 4. 压缩长度与内存成本

`PipeExtensions.TryReadMessage`先检查declared message length，再切wirebuffer；压缩路径把MaxReceiveMessageSize传给`TryReadCompressedMessage`，超限抛RpcException。helper租8192字节scratch，循环最多读到“剩余额度+1”以发现超限，finally把scratch还ArrayPool；输出以MemoryStream底层buffer形成ReadOnlySequence。

这支持“解压输出长度也必须受限”的设计，不支持“实际RSS最多等于message limit”的结论。MemoryStream capacity增长、scratch pool保留、wire与解压buffer同时存活都计入成本。B18必须测压缩炸弹、任意分片、负/溢出长度、不同compressionprovider及提前结束，不能把HTTPbody cap当解压cap。本轮没运行这些测试。

## 5. MCP2026-07-28：版本即生命周期

官方固定规范与SDK共同证明以下变化（R28-E006至E017）：

| 机制 | 现代profile | legacy2025-11-25及更早 |
| --- | --- | --- |
| 初始化 | 每请求metadata；`server/discover`可查询能力 | initialize握手与协商 |
| 会话 | 无协议session/Mcp-Session-Id | 可有stateful session |
| HTTP通信 | POST获得JSON或本请求SSE | 可有GET独立SSE、DELETE终结session与旧resumption规则 |
| SSE断开 | 当前请求取消信号 | 依旧profile的会话/恢复规则，不可混同 |
| 版本失败 | 结构化unsupported-version与supported列表 | 旧握手协商路径 |

StreamableHTTP source232–297要求header版本与body `_meta`一致，Mcp-Method与method一致，Mcp-Name按tools/call/resources/read/prompts/get来源匹配；source650–689明确现代/旧客户端回退与旧session机制边界。Modern-only面对旧GET/DELETE，规范建议405；NativeWeave选405作为固定profile行为。旧session ID及Last-Event-ID不应复活现代会话或流resumption。

SDK `HttpServerSessionMode`提供Stateless、Stateful、StatefulForInitializeClients；Hybrid不是“所有请求都可以有session”，而是按协议era分开。`StreamableHttpHandler`parse后取得JSON-RPC请求id，再做version/envelope/header/requiredmetadata校验；因此外层body/depth/header budget不能省。读取的modern conformance tests验证缺失/错误Mcp-Method被拒、正确method/name通过；hybrid测试分别验证旧session与新无session请求。

默认推荐2026-07-28是NativeWeave的明确设计选择，应用可固定旧profile或启用经独立验收的hybrid endpoint。所有客户端降级需显式策略；不把现代400错误误判为旧服务器并盲退initialize。兼容性矩阵记录protocol/SDK/transport/serializer/auth profile，SDK升级不隐式改变应用选定协议。

## 6. 工具静态注册与AOT真实证据

SDK `WithTools<TToolType>`以DynamicallyAccessedMembers约束固定类型，但实际仍用GetMethods/attributes。它减少未知类型集合，不代表零反射。非泛型`IEnumerable<Type>`标记RUC；assembly扫描不在严格AOTprofile。明确`IEnumerable<McpServerTool>`overload只注册给定实例，结合抽象`ProtocolTool`、`Metadata`、`InvokeAsync`为生成式descriptor提供实际扩展口。

选择B19生成`McpServerTool[]`、显式输入输出schema、typedhandler与JsonTypeInfo，保留受约束泛型注册作更简洁的可选已测路径。不从任意object图推导schema，不运行时猜闭合泛型，不把未知derivedtype悄悄reflectionserialize。常用API与错误诊断目标见D19，所有样例未编译。

上游AOT TestApp.csproj明确net10.0、PublishAot=true，同时TrimmerRootAssembly保留Core/ModelContextProtocol/AspNetCore等多个SDKassembly，且Program通过in-memory streams。这个fixture不能证明net11、无root-all、真实HTTP/TLS、所选DTO/profile已经AOT通过。本轮只读，没有执行；B19要真正publish并运行独立的最小fixture，把warning、工具注册/调用、取消、错误、现代与legacyprofile分别存证。

## 7. 安全、成本与验收

Origin校验不代替认证；tool/RPC逐请求权限与tenant范围；body/schema/JSONdepth有界；明确信息泄露策略；协议错误不直接暴露内部exception。MCP长操作应转持久业务operation，不把一个SSE stream当无限持有数据库事务的许可。stream关闭只说明取消意图，无法证明外部副作用已撤销。

静态生成减少反射/重复schema构造与错误后移，但增加构建产物及生成器维护；泛型反射受控profile可减少自有代码，应在真实trim/AOT/启动和分配成本比较后选默认实现细节。gRPCmessage与MCPJSON都有serialization成本；不得因有sourcegen就声称零分配。可选协议包避免所有应用为其付依赖/二进制体积成本。

B18：proto/service golden、并发write/flush/deadline/trailers、压缩前后caps、HTTP2/ALPN、Windows/LinuxAOT。B19：静态及泛型注册各自fixture、profile manifest、版本错配/错误header/未知tool/断SSE/Origin/auth、无session泄漏、no-root-alltrim。B22/B24：升级和关闭交错、长跑、证书变化、干净机器发布。新规范profile如需扩大范围，局部新增精确验收，不重新规划Core。

交叉Review：R02检查sourcegen/closedgeneric诊断；R29检查流预算、deadline与取消；R30检查error与trace隐私；R34检查输入验证、认证与包许可。未读全部SDK/HTTP2/protobuf实现，所以R28保持partially_evidenced；D19的设计关闭与正式产品验收分别记录。
