# Database、AOT ORM 与 Server：首次源码调查与研究边界

- 记录日期：2026-11-12（用户会话日期）。
- 最新版本补查：已另外读取 EF Core / Kestrel v11 固定源码，见 [v11 源码补充核验](v11-recheck.md)。本报告 v10 观察仍保持历史证据身份。
- 状态：**初步研究证据；未形成已接受的架构决策**。
- 执行者：独立阶段 B 研究子代理。
- 检查范围：7 个外部项目、20 个限定源码文件或片段；另有官方文档与候选目录检查。
- 运行状态：本专题没有编译、执行测试、发布 Native AOT 或进行性能测试。上游测试定义与 CI 文件只证明存在相关验证程序，不是本会话通过记录。
- 版本说明：下列固定版本用于可复现源码阅读，不声称是当前最新版本，也不表示已经选为 NativeWeave 依赖。正式版本须与工具链和供应链专题重新核验。
- 依据：用户 NativeWeave 任务要求与公开一手来源。没有将 ArcForges 的设计内容、流程或验收标准用作本项目依据。

## 1. 当前判断与决策边界

阶段 B 应立即展开三个互相比较的实验分支：

1. 纯 C# Native AOT：数据库驱动、静态映射、服务器和业务代码均在 C#，作为不可缺少的对照。
2. C# Native AOT + 独立 Rust 领域 Engine：只有在完整工作负载证明收益，或 Rust 生态补足必要能力时采用。
3. 对等的纯 Rust 工作负载：用于分离原生引擎自身成本和跨语言适配成本。

现有证据支持把 Npgsql + 生成式映射、Kestrel 的 AOT 能力作为优先研究基线；证据还不足以接受最终技术选型。SQLx、SeaQuery、SeaORM 与 hyper/Tokio 应接受同等严格的语义、资源和性能比较。不能将 Rust 版本的类型安全自动等同于 C# 调用面的类型安全，也不能将一个 .NET 包的 AOT 声明扩大到其全部可选功能。

## 2. 固定版本和实际阅读范围

完整机器记录见 [sources.json](sources.json)。所有 SHA 均由真实 GitHub tag/ref 返回，而非根据版本字符串推测。

| 项目 | 固定参考版本 | Commit SHA | 本轮实际研究机制 |
| --- | --- | --- | --- |
| Npgsql | v9.0.4 | `3b6c74c505c4dbc68a39b05e7440153b3bf511f4` | AOT 功能边界、最小查询程序、Native AOT CI |
| DapperAOT | 1.0.31 | `3bd350451f840b15a0894f4e8f2ed8a7ce95fb36` | 增量生成器筛选、拦截器输出快照、打包 |
| EF Core | v10.0.0 | `12b8d44bf691d2e6933a6d1003647cce4f13c3d3` | 动态查询编译门槛、预编译入口、代码生成入口 |
| SQLx | v0.8.6 | `bab1b022bd56a64f9a08b46b36b97c5cff19d77e` | 事务拥有权、Drop 回滚、PostgreSQL 实现与测试 |
| ASP.NET Core/Kestrel | v10.0.0 | `7387de91234d3ef751fa50b3d1bfede4130213ff` | 响应写入状态机、关闭后访问的测试 |
| Tokio | tokio-1.47.1 | `be8ee45b3fc2d107174e586141b1cb12c93e2ddf` | 有界消息通道容量与 permit |
| hyper | v1.7.0 | `400bdfdace8b40e3bdb93c5c6647b6b98211d432` | HTTP/1 关闭入口、C API 稳定性声明 |

SQLx 的旧地址 `launchbadge/sqlx` 在实际调用时返回重定向；通过仓库 ID 230595891 解析到当前 `transact-rs/sqlx`。证据链接使用解析后的仓库，不因旧地址或组织迁移丢失固定 commit。

## 3. 已得到的源码级观察

### DB-E001：Npgsql 的 AOT 能力必须按功能审查

实际调用链：`NpgsqlDataSourceBuilder.EnableDynamicJson` → 内部 builder；另有 tuple record、unmapped enum/range 的功能开关。已读公开 API 上明确的 `RequiresDynamicCode` 和 `RequiresUnreferencedCode` 标注。最小 Native AOT 程序使用 `NpgsqlSlimDataSourceBuilder`、异步打开连接、执行查询并读取字符串；CI 分别进行全库分析与实际发布后运行。

来源：[固定 builder 源码](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/src/Npgsql/NpgsqlDataSourceBuilder.cs)、[AOT 测试程序](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/test/Npgsql.NativeAotTests/Program.cs)、[CI 定义](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/.github/workflows/native-aot.yml)。

**对 NativeWeave 的含义（推断）**：数据库能力清单必须细到数据类型、映射方式和功能开关；不能只有“PostgreSQL 驱动支持 AOT”一格。预生成 JSON 元数据或先序列化到字节再绑定是需要验证的替代路径，不能未经实验宣称所有 POCO 映射都能零成本解决。

**未覆盖**：连接池、认证插件、故障恢复、取消协议、COPY、复杂类型、Windows AOT 的完整链路。本轮未执行上游 CI，也没有核验其历史运行是否通过。

### ORM-E001：DapperAOT 给出了编译期映射的真实参考，也暴露了静默回落风险

实际链路：`Initialize` 建立 Roslyn 增量语法管线 → `PreFilter` 选取候选调用 → `Parse` 获取语义操作、判断启用与支持标志 → 生成拦截器。读取的快照展示了 `Query`/`QueryAsync` 调用如何转向静态 `CommandFactory` 和 `RowFactory`。同时，`Parse` 对 `NotAotSupported`、`DoNotGenerate` 或未启用情况直接返回空结果。

来源：[生成器](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs)、[输入快照](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/test/Dapper.AOT.Test/Interceptors/Query.input.cs)、[输出快照](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/test/Dapper.AOT.Test/Interceptors/Query.output.cs)。[项目 FAQ](https://aot.dapperlib.dev/faq.html) 也说明支持覆盖和实际 AOT 发布测试的重要性。

**对 NativeWeave 的含义（候选要求）**：正式 AOT API 必须让未支持用法产生可操作的编译诊断或明确替代 API，不能静默保留一条依赖运行时动态生成的路径。采用拦截器是否允许，取决于所选稳定 C# 工具链的真实支持；不能从参考项目采用该功能推导它已经符合 NativeWeave 稳定核心要求。

**未覆盖**：全部 Dapper 重载、私有类型、动态参数、生成器诊断覆盖、流式中途退出的资源释放、所有运行时执行路径。快照只是上游期望输出，未在本会话重新生成。

### ORM-E002：EF Core 的普通查询编译与预编译是不同执行路径

固定版本的 `QueryCompiler.ExecuteCore` 先提取参数，再查找编译查询缓存；需要新编译时检查 `RuntimeFeature.IsDynamicCodeSupported`，否则抛出 `QueryNotPrecompiled`。同一源码中的 `PrecompileQuery` 带实验性标注。设计时生成入口连接了 `QueryLocator`、C# 到表达式树转换和预编译输出。

来源：[QueryCompiler](https://github.com/dotnet/efcore/blob/12b8d44bf691d2e6933a6d1003647cce4f13c3d3/src/EFCore/Query/Internal/QueryCompiler.cs)、[PrecompiledQueryCodeGenerator](https://github.com/dotnet/efcore/blob/12b8d44bf691d2e6933a6d1003647cce4f13c3d3/src/EFCore.Design/Query/Internal/PrecompiledQueryCodeGenerator.cs)、[官方 Native AOT 文档](https://learn.microsoft.com/ef/core/performance/nativeaot-and-precompiled-queries)。

**对 NativeWeave 的含义**：要单独比较直接采用成熟 provider 的稳定子集、生成预定义查询方法、编译期 LINQ 子集和运行时受控查询 IR。不能声称“LINQ 不能 AOT”，也不能声称“加 Source Generator 就能支持任意 IQueryable”。所读 EF 文档仍标记 Native AOT/预编译为实验性；该判断限于已读资料和固定版本，需要最新版本专题再次核验。

**未覆盖**：完整 SQL 翻译器、null 补偿、provider 预编译差异、关系修复、跟踪器、compiled model、EF 测试链路。本轮只确认入口与失败分支。

### DB-E002：SQLx 的 Drop 回滚不等于服务端已确认回滚

实际链路：`Transaction::commit/rollback` 等待数据库事务管理器，成功后才将 `open` 设为 false；`Drop` 在仍打开时调用 `start_rollback`。PostgreSQL 实现的 `start_rollback` 将回滚 SQL 放入连接队列，并调整本地事务深度，并不在 Drop 中等待服务端确认。

相关测试包含显式回滚、提交、嵌套保存点、连续丢弃事务后复用同一连接，以及 statement timeout 后显式回滚恢复。源码中的测试意图不等于当前环境已经运行成功。

来源：[通用事务](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/transaction.rs)、[PostgreSQL 事务](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-postgres/src/transaction.rs)、[相关测试，已读 423–620 行](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/tests/postgres/postgres.rs#L423-L620)。

**对 NativeWeave 的含义（候选契约）**：必须区分“已请求回滚”“连接清理完成”“服务端结果已确认”和“连接已丢弃”。C# 同步 Dispose、异步 DisposeAsync、Engine shutdown 和资源最终回收各自能承诺什么，需要明确。提交请求已经送达而响应丢失时，不能把取消或断线自动解释成“没有提交”，也不能自动重试非幂等业务。

**未覆盖**：pool 归还/清理完整链路、取消期间的协议同步、COMMIT 不确定结果分类、SQLite worker 模型、Rust executor 关闭期间的 drain。本轮没有量化 FFI、转换或池层成本。

### SRV-E001：Kestrel 的响应状态不应被简单的 disposed 布尔值取代

固定源码中的响应 PipeWriter 区分 Open、Closed 和 Aborted。写入/flush 都先检查状态；停止接受写入后，相关 API 拒绝访问，并有逐项测试。Aborted 还具有“只有相应取消令牌要求取消时才在写入时抛出”的分支。

来源：[响应 PipeWriter](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Servers/Kestrel/Core/src/Internal/Http/HttpResponsePipeWriter.cs)、[对应测试](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Servers/Kestrel/Core/test/HttpResponsePipeWriterTests.cs)。

**对 NativeWeave 的含义（推断）**：如果引入 Rust HTTP Engine，适配器必须保留请求完成、连接中断、响应停止写入、异步 flush 和回调停止的不同语义，不能只有 `Handle.Dispose()`。

[ASP.NET Core AOT 官方支持矩阵](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/native-aot?view=aspnetcore-10.0) 与 [gRPC AOT 文档](https://learn.microsoft.com/en-us/aspnet/core/grpc/native-aot?view=aspnetcore-10.0) 是选定基线的输入；不能据此认为每个中间件、MVC 或任意插件都兼容。

**未覆盖**：HTTP/2/3、TLS、连接级 shutdown、请求队列、实际内存上限、同步/异步写入完整互斥关系。一个状态类与单元测试不足以证明整个服务器的并发正确性。

### SRV-E002：hyper 自带 FFI 不能直接升级为 NativeWeave 的稳定契约

固定 `Cargo.toml` 将 C API 功能注明为不稳定且不承诺 semver。HTTP/1 的 `graceful_shutdown` 调用 `disable_keep_alive`，相关说明要求继续轮询连接 Future 直到关闭完成。

来源：[hyper Cargo features](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/Cargo.toml)、[HTTP/1 连接关闭](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/src/server/conn/http1.rs#L120-L155)。

**对 NativeWeave 的含义（推断）**：即使复用 hyper，也需要自有版本化 Adapter 边界或明确跟随不稳定上游的实验身份。停止轮询、释放 C# context 和优雅关闭不是同一事件，不能用一个完成回调模糊处理。

**未覆盖**：hyper FFI 实现全链、h2/HTTP/3、hyper-util、TLS 集成、关闭并发测试和最新版本状态。

### SRV-E003：有界消息通道不自动保证总内存有界

已读 Tokio `mpsc::channel` 以 semaphore 建立消息容量，`send` 等待 permit 后发送。源码支持“队列内消息数受容量约束”这一窄结论。

来源：[Tokio bounded channel](https://github.com/tokio-rs/tokio/blob/be8ee45b3fc2d107174e586141b1cb12c93e2ddf/tokio/src/sync/mpsc/bounded.rs)。

**额外推断**：如果每个生产者在等待 permit 前已分配大消息，或不断新建等待任务，则消息容量无法单独约束总 RSS。NativeWeave 的背压预算应分别覆盖接受的请求数、排队字节数、活动任务数和外部在途资源。尚需读取 semaphore、关闭和取消测试，再建立有明确假设的内存界限。

## 4. 候选方案比较：可以判断什么

| 路线 | 已有证据 | 可能的复用点 | 不能提前作出的承诺 |
| --- | --- | --- | --- |
| Npgsql + C# 静态映射 | 核心 AOT 测试、功能 opt-in 标注 | ADO.NET 连接、参数、结果读取；避免 DB FFI | 全数据类型、插件与任意 JSON POCO 均 AOT 安全 |
| DapperAOT | 增量生成与映射快照 | 命令工厂、映射生成、诊断与 API 覆盖测试方式 | 现有任意 Dapper 代码无需修改即可 AOT |
| EF Core | 查询编译与预编译分流 | SQL 语义、关系/投影、参数提取与测试参考 | 固定版本 Native AOT 已完整生产可用 |
| linq2db | 仅核验仓库/官方讨论，尚未读目标实现 | LINQ 翻译和多 provider 语义参考 | 维护者支持某个用户的 AOT 成功个案等于全库支持 |
| SQLx Engine | 事务及回滚源码 | Rust driver、事务/池/流式能力 | 包装 SQLx 后 C# 查询自动获得 Rust 宏的编译期检查 |
| SeaQuery | 官方生成文档、源码目录已定位 | SQL AST、参数编号、多方言序列化 | Rust 查询构建器直接成为自然 C# API |
| SeaORM | 官方生成文档、数据库目录已定位 | 实体/关系、事务/流式接口 | Rust 宏生成模型可以不经额外契约直接复用为 C# 实体 |
| Kestrel + C# handlers | AOT 官方矩阵和局部响应状态源码 | 主应用网络与托管异步栈 | 任意 ASP.NET 模块均 AOT；所有负载均胜过 Rust |
| hyper/Tokio Engine | 局部关闭、通道与 feature 源码 | Rust HTTP、流控、可选 executor | hyper C API 稳定；引入 Tokio 必然降低 RSS 或延迟 |

### AOT ORM 必须分开的四个问题

- **查询表达**：普通 LINQ to Objects、IQueryable 表达式树、编译期语法分析和受控 Fluent IR 是不同入口。
- **SQL 翻译**：解释一棵有限表达式树本身不等于生成机器码；但可用元数据、泛型实例、动态成员访问与结果 materializer 仍需 AOT 设计。
- **结果映射**：预生成映射器可以减少动态生成；必须覆盖 nullable、转换异常、constructor/setter 可访问性、关系投影和流式提前退出。
- **调用替换**：Source Generator 添加代码不能被直接等同为“随意改写原有方法”。需比较明确生成的 partial 方法/API 与已核实稳定性的拦截机制。

动态筛选可作为有限、强类型、参数化的查询 IR 在运行时组装，要求字段、操作、类型映射和允许的方法均有静态定义。它不是执行任意用户 C#，也不应偷偷退回拼接原始 SQL 或客户端全量筛选。是否暴露 IQueryable，必须经过 API 可用性实验与翻译能力契约审查。

## 5. 必须补完的领域问题与输出接口

这些是独立研究边界，可并行启动；正式 ID 由 Plan 的研究图分配。每项先输出证据及候选契约，再由文档图的对应 owner 编制规范和开发任务。

| 问题键 | 研究问题 | 证据/实验 | 输出到 Design / Plan |
| --- | --- | --- | --- |
| DB-Q01 | Npgsql 与 SQLx 对等功能和跨语言成本 | 固定版本的连接、池、执行、取消、参数、读取、释放调用链 | provider 支持矩阵；Rust 引入判定与待测预算 |
| DB-Q02 | SQLite 各路线的线程和取消语义 | Microsoft.Data.Sqlite、SQLitePCL.raw、rusqlite、SQLx SQLite worker 与 SQLite C API | 线程亲和、忙锁、interrupt、WAL、checkpoint 契约 |
| DB-Q03 | 事务和保存点何时可以归还连接 | commit/rollback/drop/pool/reset/断线完整状态机 | 状态转移、未知提交结果、同步/异步清理任务 |
| DB-Q04 | 批量与流式读取如何避免逐单元 FFI | row/批块/columnar 候选与真实数据分布实验 | buffer/row lifetime、复制计数、批量 ABI；不提前强制 Arrow |
| DB-Q05 | Schema 与迁移怎样独立部署 | 事务性 DDL、迁移锁、校验和、失败恢复与权限 | 版本兼容、可重入迁移、回滚/前滚规则 |
| ORM-Q01 | 自然 C# 查询面与可拒绝的语法集合 | 编译期 LINQ 子集、显式生成方法、Fluent IR 用户样例 | 可支持/拒绝语法表、诊断码、无动态代码备用入口 |
| ORM-Q02 | SQL 语义如何验证 | null/空集合/join/聚合/分页/collation/时间与数值差异 | provider 差异表、SQL golden + 实库 differential tests |
| ORM-Q03 | 元数据/映射及结果生命周期 | nullable、投影、值转换、并发枚举、中途异常 | 静态 descriptor、materializer、释放契约 |
| ORM-Q04 | 缓存与预编译如何版本化 | schema、provider、参数shape、泛型组合与生成体积实验 | cache key、失效、构建增量性和体积上限依据 |
| SRV-Q01 | Kestrel 满足哪些需求、额外 Engine 何时有价值 | 相同 TLS、连接复用、payload、业务和数据库访问的基准 | 服务器能力边界、对等实验与选择 ADR |
| SRV-Q02 | Rust 请求适配与流式背压怎样闭环 | 请求/响应 buffer、header、取消、线程回调、关闭全链 | 请求 token、消费确认、预算、drain 状态机 |
| SRV-Q03 | gRPC/MCP 如何组合而不进入 Core | 官方 SDK、序列化、流式方法、工具注册 AOT 实验 | 独立协议 adapter、版本矩阵和诊断 |
| SRV-Q04 | TLS、认证与可观测性由谁拥有 | Kestrel/.NET 与 Rust 原生 TLS、trace context、日志模型 | ownership、证书更新、敏感参数关闭、采样开销 |
| E2E-Q01 | 数据库与服务器能否保持端到端资源边界 | 无业务依赖的记账/订单式事务参考负载 | 参考应用设计、故障矩阵和三路线 benchmark |

推荐参考应用使用一个小型、可校验的资源预订或库存事务模型：创建记录、幂等键、条件更新、分页/流式查询，覆盖写入冲突和提交不确定性。该模型只服务验证，不将任何下游业务协议引入框架。

## 6. 领域不变量与验证义务

下列是不依赖候选实现的待正式化要求，不表示已完成证明：

1. **连接独占**：一次协议交互使用的连接不得同时被不兼容的事务/reader 所复用；若 provider 支持 multiplexing，必须明确其与 transaction、streaming、session state 的兼容边界。
2. **事务终态**：一次事务至多记录一个已确认的终态。Unknown 不能伪装成 RolledBack；在缺少协议确认时不宣称已提交或未提交。
3. **结果有效期**：任何读取操作要求其 backing buffer 和 parent reader 的 lease 有效。提前退出枚举、异常和取消都最终释放 lease。
4. **SQL 参数隔离**：用户数据只能进入值参数；标识符和语法片段来自已验证的静态或受控集合。参数顺序、类型、null 标记必须一致。
5. **查询等价性**：仅在已声明的语义域内要求 `GeneratedQuery(D, p) = ReferenceSQL(D, p)`；域需说明 collation、timezone、null、溢出、浮点 NaN、排序 tie-break 等假设。
6. **完成唯一性**：每个跨语言请求/查询操作最终完成次数至多一次；取消请求与结果到达竞争不得重复消费结果或释放 context。
7. **资源界限**：若活动请求数、排队字节数、并发 materializer 和原生池大小有界，需给出内存预算的组成与计算；只限制 channel 项数不构成整个系统的证明。
8. **关闭静默性**：宣布 shutdown/drain 完成后，不能再进入引用已释放上下文的回调，也不能留下需要已关闭 executor 才能完成的清理操作。

适合模型检查的部分是提交/取消/清理状态转换和回调停止协议；SQL 语义更适合属性测试、真实 PostgreSQL/SQLite differential tests；原生内存边界适合 fuzz、sanitizer 和对应 Rust 工具。不能用 SQL golden 文本快照代替真实执行语义，也不能用压力测试没有失败代替所有竞态已被证明。

## 7. 最低实验矩阵（提案，尚未执行）

| 场景 | 必须观察的结果 | 对照/故障 |
| --- | --- | --- |
| AOT 连接与映射 | 实际发布二进制成功连接、绑定、读取、关闭 | Windows/Linux 各自运行；不同 RID 独立记录 |
| 不支持的查询表达 | 明确编译错误或显式替代路径 | 私有类型、捕获状态、任意方法调用、动态成员 |
| SQL 语义 | 固定测试数据库中结果一致 | null、空集合、left join、聚合、decimal、时区、collation |
| 连接池耗尽 | 有界等待且取消后容量恢复 | 持有连接不释放、认证失败、网络拒绝 |
| 查询取消竞争 | 恰好一个完成结果，连接可清理或丢弃 | cancel before send / during read / after completion |
| 事务失败 | 不错误提交、不将 Unknown 当回滚 | statement timeout、deadlock、断线、COMMIT 响应丢失 |
| 流式中途退出 | reader、连接、原生 buffer 和 GCHandle 回到基线 | 消费一行后 break、materializer 抛异常、客户端断开 |
| 批量读写 | 吞吐和复制/分配账目可解释 | 小行/大行、二进制大对象、UTF-8、nullable |
| 迁移 | schema 结果与版本账本一致 | 并发启动、执行中断、权限不足、不可事务 DDL |
| HTTP 流控 | 慢客户端不能造成无界内存增长 | 慢读、慢写、过大 header/body、HTTP/2 多流 |
| 服务器关闭 | 停止接收后 drain 终结，资源归零或符合约定 | 活跃事务、延迟回调、pending flush、长连接 |
| 协议 adapter | gRPC/MCP 路径真实 AOT 可运行 | 序列化、stream cancellation、错误映射与版本差异 |
| 端到端负载 | CPU/RSS/分配/吞吐/P95/P99/错误率可重复 | 三条路线相同协议、数据、索引、TLS、功能与机器 |

性能门槛须由基线和应用目标确定。本轮不设置任意“快 30%”“RSS 小于 50 MB”等数字。测试记录还应包括吞吐对应的并发与排队状态、冷启动/热启动、持续时间、重复次数、置信区间方法、负载发生器饱和检查和错误率；否则延迟分位数容易误导。

## 8. 扩展源码清单与优先级

“已读”只针对第 2、3 节和 sources.json 声明的范围。下面未固定版本的候选路径只是研究入口，不是已阅读证据。

| 优先级 | 项目/一手入口 | 要解决的问题 | 下一轮源码入口与状态 |
| --- | --- | --- | --- |
| P0 | [Npgsql](https://github.com/npgsql/npgsql) | PostgreSQL 纯 C# 基线 | `NpgsqlCommand`、`NpgsqlConnector`、`PoolingDataSource`、type resolvers；目录/文件名已定位，主体未读 |
| P0 | [SQLx](https://github.com/transact-rs/sqlx) | Rust driver 可选引擎 | `sqlx-core/src/pool/`、postgres executor/connection、`sqlx-sqlite` worker；事务已部分读 |
| P0 | [DapperAOT](https://github.com/DapperLib/DapperAOT) | 静态参数和映射生成 | 已读生成入口/快照；继续 `CommandT.Query`、`AsyncQueryState` 与负向诊断测试 |
| P0 | [EF Core](https://github.com/dotnet/efcore) | 查询语义与预编译 | 已读入口；继续 relational query translator、SQL nullability、compiled model 与 provider 测试 |
| P0 | [ASP.NET Core](https://github.com/dotnet/aspnetcore) | C# Native AOT server 基线 | Kestrel、RequestDelegateGenerator、Pipelines、连接管理及 stream tests |
| P0 | [Tokio](https://github.com/tokio-rs/tokio)、[hyper](https://github.com/hyperium/hyper)、[hyper-util](https://github.com/hyperium/hyper-util) | Rust server/runtime 成本与关闭 | 部分源码已读；继续 body 流控、连接任务、executor、TLS adapter 与 shutdown tests |
| P1 | [linq2db](https://github.com/linq2db/linq2db) | 多数据库 SQL 翻译与诊断 | 内部 LINQ builder、表达式编译与 mapper；本轮只有仓库/官方讨论检查 |
| P1 | [SeaQuery](https://github.com/SeaQL/sea-query) | 可参数化查询 IR 与方言 | `src/backend`、`src/query`、`src/value` 目录已实际定位，内容未读 |
| P1 | [SeaORM](https://github.com/SeaQL/sea-orm) | Rust ORM 层职责与事务/流式 | `src/database/transaction.rs`、`stream`、`statement.rs` 路径已定位，内容未读 |
| P1 | [Microsoft.Data.Sqlite](https://github.com/dotnet/efcore/tree/main/src/Microsoft.Data.Sqlite.Core)、[SQLitePCL.raw](https://github.com/ericsink/SQLitePCL.raw) | 最小 C# SQLite 原生绑定基线 | connection/command/reader、native library loading，待固定版本与阅读 |
| P1 | [rusqlite](https://github.com/rusqlite/rusqlite)、[SQLite C API](https://www.sqlite.org/c3ref/intro.html) | 同步 SQLite 引擎与 thread/interrupt | connection、statement、transaction、unlock/interrupt；待调查 |
| P1 | [PostgreSQL 官方协议](https://www.postgresql.org/docs/current/protocol.html) | cancellation、Sync、事务状态与错误恢复 | extended query、CancelRequest、ReadyForQuery；待按服务端版本固定 |
| P1 | [grpc-dotnet](https://github.com/grpc/grpc-dotnet)、[MCP C# SDK](https://github.com/modelcontextprotocol/csharp-sdk) | 协议 adapter、AOT 生成注册与序列化 | server binding/streaming/serialization/transport；待固定源码 |
| P1 | [System.Text.Json/runtime](https://github.com/dotnet/runtime)、[OpenTelemetry .NET](https://github.com/open-telemetry/opentelemetry-dotnet) | 静态序列化与可观测性开销 | source generation、diagnostics、metrics/traces AOT；待读 |
| P2 | [Apache Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) | 大批数据交换是否值得标准化 | 评估 lifetime、列式转换与依赖成本；不预设作为数据库 ABI |
| P2 | [Testcontainers .NET](https://github.com/testcontainers/testcontainers-dotnet)、[Toxiproxy](https://github.com/Shopify/toxiproxy) | 可复现数据库/网络故障 | 仅测试工具候选，不进入产品运行时；待适配 Windows/Linux 能力 |

新增项目必须说明替代了哪些自行开发工作、带来哪些依赖/许可证和更新成本。不能因为候选清单变长就增加正式产品模块。

## 9. 许可证与复用记录

- Npgsql：固定 LICENSE 实际阅读；保留其版权及许可文本义务进入供应链专题。
- DapperAOT：固定 `License.txt` 实际阅读；工具声明 Apache 2.0，另有名称/logo 使用限制。GitHub 元数据只返回 NOASSERTION，因此不能只依赖自动分类。
- SQLx：固定 Cargo.toml 声明 MIT OR Apache-2.0；仓库同时存在两份许可证。依赖树仍需独立调查。
- ASP.NET Core、EF Core：已读文件含 MIT 头；未完成所有传递依赖与嵌入第三方代码审计。
- hyper：固定 Cargo.toml 声明 MIT；Tokio 本轮未读取许可证，保留待核验状态。

本交付只保存研究总结与链接，未复制大段外部产品源码，也未决定将哪部分代码带入 NativeWeave。

## 10. 当前证据缺口与交叉审查问题

1. 由最新版本专题确认所选稳定语言特性与框架版本；尤其不要把所读 EF/Dapper 的旧固定实现当作未来版本事实。
2. ABI/ownership 专题应审查 SQLx 延迟回滚、流式 reader 与 parent connection 的释放顺序；若核心不支持所需 lease/drain，就修改限定契约而非加全局 runtime。
3. generator 专题应证明 unsupported query 的诊断闭环、增量构建一致性和公开强类型 API；不存在“引用生成器即已 AOT 安全”的验收捷径。
4. concurrency 专题应检查 callback 完成、取消注册释放、executor shutdown 和 .NET continuation 的交互；不能在持有原生锁时任意执行 C# 用户代码。
5. server 专题需要完整 Kestrel 与 Rust 请求链路，不应把本轮单个 PipeWriter 或 hyper 方法作为完整架构比较结论。
6. performance 专题需给出完整工作负载实验；没有性能数据时，可维护性收益也必须基于实际代码/配置差异进行评估。
7. 发布专题需检查 NuGet/RID/原生依赖、TLS 后端、操作系统 ABI、配置与数据库版本组合，所有正式支持平台均需真实构建运行。
8. 独立 reviewer 应抽查固定 SHA 的证据是否支持每个结论，明确将“已读测试源码”与“已执行通过”分开。

**本轮可交付状态**：研究边界、候选比较和 7 条局部源码证据已建立；阶段 B 的正式公共 API、数据库选择、ORM 查询子集、服务器引擎选型与性能承诺仍未接受。它们是下一轮并行研究和文档编制的明确输入，而非被延期为模糊的未来事项。

