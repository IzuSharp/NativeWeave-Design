# 外部源码研究目录与优先级

状态：研究入口目录；2026-11-12；不是依赖清单。**P0/P1/P2是阅读优先级，互不构成人为启动依赖。** 每个专题可主动扩展来源，但要说明新增项目解决的具体问题。

本次真正读取的固定SHA与限定行段，在 [Interop evidence](interop/evidence.json)、[领域 sources](domains/sources.json)、[v11补查](domains/v11-evidence.json) 中。工具链官方事实在 [toolchain](toolchain/evidence.json)。下表其余路径/符号是待定位或待深入入口，不是已经完成覆盖。

## P0：决定基础安全与可行性的来源

| 项目 | 具体研究问题/优先入口 | 本轮覆盖 | 专题 |
| --- | --- | --- | --- |
| [dotnet/runtime](https://github.com/dotnet/runtime) | NativeAOT、SafeHandle、LibraryImport生成、Span/Memory、异步和GC；实现与测试必须成对读 | 官方文档已核验，运行时源码待完整固定阅读 | R01–R04、R07、R09–R13 |
| [dotnet/roslyn](https://github.com/dotnet/roslyn)、[csharplang](https://github.com/dotnet/csharplang) | IncrementalGenerator、语法/语义分析、新union lowering、诊断、生成稳定性 | 特性官方文档已核验，编译器实现待研究 | R01、R05、R06、R23 |
| [rust-lang/rust](https://github.com/rust-lang/rust) | Rust2024、布局、FFI、panic、Pin/Future、安全边界和测试 | 官方发布与reference已核验；编译器源码待研究 | R01、R03、R09、R11 |
| [Cysharp/YetAnotherHttpHandler](https://github.com/Cysharp/YetAnotherHttpHandler) | RequestContext、SafeHandles、native binding/context、完成/取消/背压与相关测试 | 固定SHA部分调用链已读，无运行结果 | R07–R12、R18 |
| [Cysharp/csbindgen](https://github.com/Cysharp/csbindgen) | emitter/type mapping/parser与AOT生成边界 | 固定SHA emitter片段已读，其他仅取得/待研究 | R03–R06 |
| [Npgsql](https://github.com/npgsql/npgsql) | connector/pool/command/reader、类型解析、取消、AOT样例与功能限制 | 固定SHA局部实现及测试/CI定义已读 | R19、R21、R22 |
| [DapperAOT](https://github.com/DapperLib/DapperAOT)、[Dapper](https://github.com/DapperLib/Dapper) | 增量生成、调用覆盖、参数和结果映射、动态fallback | DapperAOT固定生成入口/快照已读；Dapper常规实现待读 | R06、R23、R25 |
| [EF Core](https://github.com/dotnet/efcore) | QueryCompiler、预编译、SQL翻译/nullability、实体/关系、provider测试 | v10/v11入口片段已读；翻译全链待研究 | R20、R23–R25 |
| [SQLx](https://github.com/transact-rs/sqlx) | pool、query/row、transaction/drop、SQLite worker、协议取消/同步 | v0.8.6事务链及测试片段已读 | R19–R22 |
| [ASP.NET Core](https://github.com/dotnet/aspnetcore) | Kestrel、RequestDelegateGenerator、response/request/connection lifecycle | v10/v11 response writer与测试限定范围已读 | R26、R29 |
| [Tokio](https://github.com/tokio-rs/tokio)、[hyper](https://github.com/hyperium/hyper) | executor、bounded channel、HTTP流/关闭、FFI边界 | 固定SHA channel/连接/feature片段已读 | R09、R12、R27、R29 |
| [PostgreSQL](https://github.com/postgres/postgres)、[SQLite](https://www.sqlite.org/src/) | 服务端协议、事务/保存点、SQL真实语义、崩溃恢复 | 官方和驱动研究入口；引擎实现待固定阅读 | R19–R24、R31 |

SQLx旧launchbadge地址本轮解析到transact-rs/sqlx；引用应使用实际返回仓库及固定SHA。不要把旧发布源码观察当作自动覆盖最新版本。

## P1：减少自行开发与揭示反例的来源

| 项目 | 为什么需要 | 待深入入口/注意事项 | 专题 |
| --- | --- | --- | --- |
| [Godot](https://github.com/godotengine/godot) | 原生/托管对象身份、信号与生命周期的复杂现实案例 | modules/mono、GCHandle、销毁、线程、信号、测试；不继承游戏引擎runtime | R07、R08、R12 |
| [Qt for Python](https://github.com/qt/qtforpython) | ownership、parent-child、事件重入与线程关联 | Shiboken binding/object管理、信号与析构测试；不能将Python运行时机制直接套C# | R07、R08、R32 |
| [UniFFI](https://github.com/mozilla/uniffi-rs) | 类型/IDL、ownership、async桥与多语言生成的现成设计 | 仓库已核验；生成器、callback/future scaffolding和tests待读；不预设官方C#后端可直接采用 | R05、R08、R09 |
| [Interoptopus](https://github.com/ralfbiedert/interoptopus) | Rust→C# inventory、patterns和生成边界 | 仓库已核验，需确认当前API、lifetime、async与AOT测试 | R05、R18 |
| [Diplomat](https://github.com/rust-diplomat/diplomat) | 借用/lifetime描述、跨语言API生成 | 仓库已核验；需核实实际支持语言、C#路径与限制 | R05、R07 |
| [cbindgen](https://github.com/mozilla/cbindgen)、[bindgen](https://github.com/rust-lang/rust-bindgen) | Rust→C header、C→Rust工具链的不同方向 | 仓库已核验；布局/类型/条件编译/测试；两者不等价也不自动生成高层C# API | R03、R05、R13 |
| [CsWin32](https://github.com/microsoft/CsWin32)、[ClangSharp](https://github.com/dotnet/ClangSharp) | 成熟C#静态interop和metadata/clang路线比较 | 仓库已核验；生成器、诊断、测试；不能直接假定覆盖Rust高级语义 | R04–R06 |
| [linq2db](https://github.com/linq2db/linq2db) | LINQ翻译和多方言成熟实现 | builder、SQL转换、mapper、AOT限制；不能据单次成功宣称全库支持 | R23–R25 |
| [SeaQuery](https://github.com/SeaQL/sea-query)、[SeaORM](https://github.com/SeaQL/sea-orm) | Rust query AST、类型/事务/关系边界 | 部分目录已定位，代码内容待读；不把Rust宏直接当C#编译期SQL验证 | R22–R25 |
| [SQLitePCL.raw](https://github.com/ericsink/SQLitePCL.raw)、[rusqlite](https://github.com/rusqlite/rusqlite) | SQLite最小C#绑定与同步Rust路线 | statement/connection lifetime、interrupt/WAL/threading、native加载 | R20–R22 |
| [ET](https://github.com/egametang/ET) | Actor/Fiber调度与状态管理参考 | 先核验当前成熟路径与使用条件；不是通用Server默认框架 | R12、R26 |
| [Tower](https://github.com/tower-rs/tower)、[Axum](https://github.com/tokio-rs/axum)、[hyper-util](https://github.com/hyperium/hyper-util) | middleware/backpressure/connection层分工 | service、buffer、load-shed、shutdown tests；额外executor成本 | R27、R29 |
| [grpc-dotnet](https://github.com/grpc/grpc-dotnet)、[MCP C# SDK](https://github.com/modelcontextprotocol/csharp-sdk) | 协议模块的静态注册和序列化路线 | AOT、stream cancellation、transport/version边界 | R28 |
| [OpenTelemetry .NET](https://github.com/open-telemetry/opentelemetry-dotnet)、[tracing](https://github.com/tokio-rs/tracing) | 跨语言诊断关联和成本 | context传播、采样、异步线程跳转；不强制每引擎引入完整栈 | R30 |
| [TLA+](https://github.com/tlaplus/tlaplus)、[Loom](https://github.com/tokio-rs/loom)、[Miri](https://github.com/rust-lang/miri)、[Kani](https://github.com/model-checking/kani) | 竞争、Rust有效性与有界证明的不同能力 | 限定可检查性质与FFI/OS不覆盖范围；不把工具数量当质量 | R15、R16 |
| [Coyote](https://github.com/microsoft/coyote) | managed并发调度测试候选 | 仓库已核验；检查重写/调度与AOT关系，测试工具不必成为产品依赖 | R15、R16 |
| [BenchmarkDotNet](https://github.com/dotnet/BenchmarkDotNet)、[Criterion](https://github.com/bheisler/criterion.rs) | 可重复本地性能实验 | AOT toolchain、冷启动与长跑限制；不能代替端到端负载 | R17 |
| [Testcontainers .NET](https://github.com/testcontainers/testcontainers-dotnet)、[Toxiproxy](https://github.com/Shopify/toxiproxy) | 实库和网络失败重现 | 宿主能力、容器/实机证据边界；只作为验证工具 | R16、R21、R31 |

## P2：检验未来兼容边界，避免提前膨胀Core

| 项目 | 研究目标 | 不在本次产品实现范围 |
| --- | --- | --- |
| [GPUI/Zed](https://github.com/zed-industries/zed)、[gpui-kit](https://github.com/longbridge/gpui-kit)、[nsh](https://github.com/longbridge/nsh) | 主线程、事件循环、窗口/渲染资源、移动shell约束；后两仓库已核验 | 完整GUI产品、既定引擎采用承诺 |
| [wgpu](https://github.com/gfx-rs/wgpu)、[wgpu-native](https://github.com/gfx-rs/wgpu-native) | GPU handle、callback、异步映射、线程与稳定C接口边界 | 自制渲染框架或所有平台支持声明 |
| [Zstd](https://github.com/facebook/zstd)、[zstd-rs](https://github.com/gyscos/zstd-rs) | 同步/流式buffer引擎候选，并与.NET11内置Zstandard比较 | 预设Rust wrapper必然胜过.NET |
| [Apache Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) | 大批数据交换、release callback和列式布局是否值得复用 | 强制所有DB返回值列式化 |
| [.NET平台文档](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/)、[Rust平台支持](https://doc.rust-lang.org/rustc/platform-support.html) | iOS/Android、静态链接、CPU ISA、打包、语言/运行时桥 | 未实际构建运行的平台“正式支持” |

## 源码证据准入

固定完整SHA；记录具体文件、符号和行段；公共API→实现→错误→释放→测试完整覆盖所研究机制。标明仅README/文档、目录定位、取回未读、限定源码阅读、运行证实。当前目录仅将已做的工作标已读。

每个新候选要补许可证、维护状态、目标支持和替代成本；不得因为知名或现代就直接采用。正式复用要审查准确版本LICENSE和来源，不能把GitHub的自动license标签当完整法律结论。
