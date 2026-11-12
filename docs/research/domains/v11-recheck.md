# EF Core / Kestrel v11 源码补充核验

日期：2026-11-12。状态：源码复核，未编译或运行。

本文件补充 [初步研究](initial-findings.md) 中明确固定在 v10 的历史观察。v10 记录保留原版本和证据强度，不通过修改版本标签伪装成 v11 研究。当前工具链发布核验由独立 [toolchain 专题](../toolchain/report.md) 负责；本文件只核验对应 v11 tag 下的限定源码。

## 1. EF Core v11.0.0

真实 tag/ref 返回 commit：`9e685c7a52d1a344d133a3d370e458db97417b3f`。

实际完整阅读：[QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs)，blob SHA `7d59e4786702c632ff72f781ae88104c271265f2`。

关注机制与 v10 的对照：

| 机制 | v11 实际观察 | 可作出的结论 |
| --- | --- | --- |
| 新查询编译 | `ExecuteCore` 仍检查 `RuntimeFeature.IsDynamicCodeSupported`；不可动态生成时抛 `QueryNotPrecompiled` | 普通查询编译路径仍不能被当作无需条件的 AOT 执行保证 |
| 预编译入口 | `PrecompileQuery` 仍有 `Experimental(EFDiagnostics.PrecompiledQueryExperimental)` | 在这个具体入口，实验性标注并未因 v11 tag 存在而消失 |
| 参数提取签名 | 相较所读 v10，`ExtractParameters` 不再暴露可选 `generateContextAccessors` 参数 | 内部 API 存在演进；不应让 NativeWeave 公共契约绑定其内部方法签名 |

结论只覆盖当前文件中的路径和标注。没有完整调查 v11 的 provider 支持、设计时代码生成、compiled model、SQL 翻译和全部 AOT 测试。因此可以说“v11 这个预编译入口仍标注实验性”，不应扩大为“已经证明 EF v11 所有 AOT 方案都不可用”，也不能直接宣布生产可用。

## 2. ASP.NET Core / Kestrel v11.0.0

真实 tag/ref 返回 commit：`1def4cdc07dc10fc267136060e3ef5c1a96d4a99`。

实际完整阅读：

- [HttpResponsePipeWriter.cs](https://github.com/dotnet/aspnetcore/blob/1def4cdc07dc10fc267136060e3ef5c1a96d4a99/src/Servers/Kestrel/Core/src/Internal/Http/HttpResponsePipeWriter.cs)：blob `5e5078e05cc54865f02abfbed7a6396894f12e9d`。
- [HttpResponsePipeWriterTests.cs](https://github.com/dotnet/aspnetcore/blob/1def4cdc07dc10fc267136060e3ef5c1a96d4a99/src/Servers/Kestrel/Core/test/HttpResponsePipeWriterTests.cs)：blob `8fb8cb261d0ae8eefeecc5471d9e79ab537fc2e3`。

这两个 blob SHA 与之前实际读取的 v10 文件相同。对这两个限定文件，可确认实现和测试内容没有变化：Open/Closed/Aborted 状态、停止写入后的访问拒绝与对应测试仍存在。

这个结果不能被扩展为 Kestrel v10/v11 整体相同，更不证明完整 HTTP、TLS、AOT、中间件和并发行为均已核验。

## 3. 证据与未完成工作

机器记录见 [v11-evidence.json](v11-evidence.json)。本次新增两个固定版本、三个限定文件读取；历史研究仍为原来的 7 个项目/20 个文件或片段，合并统计应区分“不同路径数”和“按版本的读取次数”。

下一步应在已核验的 .NET 11 工具链上进行 provider/ORM/服务器最小 Native AOT 发布与真实 Windows/Linux 运行。源码中的防护与实验性标注只能帮助确定风险，不能代替这些运行证据。

