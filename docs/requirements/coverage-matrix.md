# 范围覆盖与遗漏检查

状态：规划覆盖，不代表研究/实现已完成。完整机器映射见 [requirements-map.json](../traceability/requirements-map.json)。所有ID来自当前三图，已实际校验存在。

| 需求 | 范围 | Research | Documentation | Delivery候选 | 证据方式 |
| --- | --- | --- | --- | --- | --- |
| NW-A01 | ABI、类型布局、版本、目标差异 | R03, R04 | D02, D03 | A01, A02, A10, A11, A22 | 源码+三方layout/调用+旧新版本组合 |
| NW-A02 | 绑定、强类型Adapter、Generator、Analyzer | R04, R05, R06 | D03, D23 | A09, A10, A11, A12 | 生成快照+增量/负例诊断+实际AOT |
| NW-A03 | Ownership、Lifetime、GC、父子资源 | R07, R10, R15 | D04, D22 | A03, A04, A19, A20 | lease模型+释放竞争+真实FFI |
| NW-A04 | Callback、注销、重入、释放竞争 | R08, R11, R12 | D05, D08, D24 | A06, A07, A19, A20 | 注销静默+进程隔离callback负例 |
| NW-A05 | Async、Cancellation、恰好一次完成 | R09, R12, R15 | D06, D24 | A07, A08, A18, A19 | 终态/静默分离+模型+真实AOT异步 |
| NW-A06 | Memory、Buffer、Pinning、传输与批量 | R10, R16, R17 | D07, D13 | A04, A17, A18, A20, A21 | allocator/alias/溢出+fuzz+复制账本 |
| NW-A07 | Error、panic、ABI异常边界 | R11, R04 | D08, D03 | A05, A12, A20 | unwind/abort/UCO签名+subprocess |
| NW-A08 | Concurrency、线程、Runtime、背压 | R12, R09, R29 | D09, D24 | A08, A18, A19, A23 | 有界资源+shutdown+线程亲和 |
| NW-A09 | Build、AOT、NuGet/Cargo、发布兼容 | R01, R02, R13, R14 | D01, D10, D25 | A13, A14, A15, A16, A22 | Windows/Linux真目标+clean consumer+SBOM |
| NW-A10 | 标准Engine接入与至少两异质真实模块 | R18, R17, R12 | D11, D26 | A17, A18, A23, A24 | 同步与异步真实引擎+无Rust应用成本 |
| NW-B01 | Database、连接池、事务、迁移、恢复 | R19, R20, R21, R22 | D14, D15, D27 | B01, B02, B03, B04, B05, B06, B07, B08 | PG/SQLite实库+AOT+断连/未知提交 |
| NW-B02 | ORM、LINQ、代码生成、SQL语义 | R23, R24, R25, R06 | D16, D17, D28 | B09, B10, B11, B12, B13, B14 | 支持/拒绝语法+SQL差分+静态映射 |
| NW-B03 | Server、HTTP/TLS、gRPC/MCP、流与诊断 | R26, R27, R28, R29, R30 | D18, D19, D29 | B15, B16, B17, B18, B19, B20 | Kestrel对照+背压+协议AOT+drain |
| NW-B04 | DB/Server参考应用、故障长跑、发布 | R31, R17, R16 | D20, D30 | B21, B22, B23, B24 | 相同语义三路线+独立真实验收 |
| NW-X01 | GUI/GPU/NSH/线程亲和扩展 | R32, R18 | D21, D11 | A23, A24 | 接入约束与探针，不承诺完整GUI |
| NW-X02 | iOS/Android/静态链接与生命周期 | R33, R02 | D21, D01 | A23, A24 | 按目标profile核验，不gate无关桌面 |
| NW-P01 | C# First | R17, R19, R26 | D11, D13, D14, D18 | A21, B02, B15, B23 | 纯C#原生编译基线与依赖图 |
| NW-P02 | Native AOT Required | R02, R13 | D01, D10 | A14, A15, B24 | publish与真实运行分别记录 |
| NW-P03 | Rust When Justified | R17, R18, R19, R27 | D11, D13, D14, D18 | A17, A18, B04, B17, B23 | 能力/成本/可靠性或实测采用ADR |
| NW-P04 | 框架简洁优雅高效 | R06, R12, R17, R25 | D03, D09, D13, D16 | A21, B23 | 抽象/运行时/依赖/开发体验成本账本 |
| NW-P05 | Independent Engines | R14, R18 | D10, D11, D31 | A16, A24, B24 | 独立包/契约/发布profile |
| NW-P06 | 标准Native-ready接入 | R18, R13, R14 | D10, D11, D31 | A24, A16 | 端到端conformance及新引擎任务模板 |
| NW-P07 | Performance by Evidence | R17 | D13 | A21, B23 | 可比负载、内存/线程/复制/分布 |
| NW-P08 | Research/Documentation/Delivery三种并行 | R15, R16 | D31, D32 | 治理检查 | 三图结构、局部依赖、文件所有权检查 |
| NW-P09 | 两阶段同时深入规划 | R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31 | D14, D15, D16, D17, D18, D19, D20, D27, D28, D29, D30 | B01, B02, B03, B04, B05, B06, B07, B08, B09, B10, B11, B12, B13, B14, B15, B16, B17, B18, B19, B20, B21, B22, B23, B24 | B阶段具体任务/规范覆盖 |
| NW-P10 | NativeWeave内容独立；Arc只参考格式 | 需求约束 | D31, D32 | 治理检查 | 需求章程、文档和依赖审查 |
| NW-P11 | 最新稳定技术与预览隔离 | R01, R02 | D01, D03 | A12, A13 | 日期化官方事实+功能状态+编译例 |
| NW-P12 | 诚实证据与独立Review | R15, R16, R34 | D12, D32 | A19, A20, B22 | 状态/hash/来源+不同作者review |

## 特别防遗漏项

- 任务完成通知与原生资源静默、managed取消注册排空分别说明。
- NULL、collation、排序tie-break、数值/时区、unknown事务结果单独验证。
- 迁移、schema、池复用、流式提前退出都不是ORM映射的附属空项。
- 包来源、许可证、平台ISA、加载路径、旧新ABI组合与Engine独立发布都有owner。
- 高吞吐下P99、失败率、RSS/GC/native内存/线程、长跑和恢复分别测量。
- GUI/mobile作为边界研究；桌面基线不等待所有未来平台完成。
- 各领域草稿可立即开始，正式契约/产品接受依赖具体证据与独立review。

## 三图完整索引

### Research

| ID | 任务 |
| --- | --- |
| R01 | 稳定工具链与现代语言机制 |
| R02 | Native AOT、裁剪与平台支持 |
| R03 | C ABI、布局与版本协商 |
| R04 | P/Invoke、回调入口与FFI调用成本 |
| R05 | 绑定生成器与契约描述来源 |
| R06 | Roslyn增量生成与分析器 |
| R07 | 句柄、所有权、GC与父子资源 |
| R08 | Callback注销、重入与释放竞态 |
| R09 | 异步、取消与完成状态机 |
| R10 | Buffer、Pinning、批处理与数据传输 |
| R11 | Error、panic、异常与故障隔离 |
| R12 | 并发、执行器、线程亲和与关闭 |
| R13 | MSBuild/Cargo、链接与目标平台 |
| R14 | 打包、兼容性、独立发布与来源 |
| R15 | 形式化与并发证明义务 |
| R16 | 差分、属性、模糊与故障测试 |
| R17 | 端到端性能、内存与开发成本 |
| R18 | 按能力组合的Engine接入与通用性 |
| R19 | PostgreSQL驱动与纯C#对照 |
| R20 | SQLite适配、并发与线程限制 |
| R21 | 连接池、事务、取消与恢复 |
| R22 | 类型映射、批量流与Schema演进 |
| R23 | LINQ、Expression与编译期查询捕获 |
| R24 | SQL语义、关系代数与参数安全 |
| R25 | ORM特性、跟踪与现成方案比较 |
| R26 | Kestrel与纯C# AOT服务器基线 |
| R27 | Rust网络引擎与C# Handler边界 |
| R28 | gRPC、MCP、TLS与协议适配 |
| R29 | 请求流、背压、超时与优雅关闭 |
| R30 | 可观测性、诊断关联与成本 |
| R31 | 数据库+服务器参考应用与故障恢复 |
| R32 | 桌面GUI/GPU与线程亲和扩展 |
| R33 | iOS/Android、静态链接与平台生命周期 |
| R34 | 边界安全、输入验证与资源滥用 |

### Documentation

| ID | 任务 |
| --- | --- |
| D01 | 工具链、AOT与平台规范 |
| D02 | ABI及类型布局契约 |
| D03 | 绑定IR、生成器与分析器规范 |
| D04 | 所有权与资源生命周期契约 |
| D05 | Callback注册撤销与静默契约 |
| D06 | 异步完成与取消契约 |
| D07 | Buffer、传输及内存契约 |
| D08 | Error、panic与异常边界契约 |
| D09 | 并发、Runtime与关闭规范 |
| D10 | 构建打包、版本与来源规范 |
| D11 | Engine接入规范与双模块验证 |
| D12 | 证明义务与真实验证规范 |
| D13 | 性能、内存与开发体验方法 |
| D14 | 数据库驱动能力与适配规范 |
| D15 | 连接池、事务与恢复契约 |
| D16 | 查询IR、SQL语义与ORM范围 |
| D17 | AOT查询捕获、生成与安全动态API |
| D18 | Server生命周期与适配规范 |
| D19 | 协议、可观测性与安全规范 |
| D20 | 生产级参考应用与验收设计 |
| D21 | 未来引擎和移动平台扩展边界 |
| D22 | ABI、内存与资源开发任务编制 |
| D23 | 生成器与分析器开发任务编制 |
| D24 | Callback、async与Runtime任务编制 |
| D25 | 构建、打包与独立发布任务编制 |
| D26 | Engine、证明、测试与基准任务编制 |
| D27 | Database完整实现任务编制 |
| D28 | ORM与LINQ AOT实现任务编制 |
| D29 | Server与协议实现任务编制 |
| D30 | 端到端、长期负载与领域发布任务编制 |
| D31 | 全局追溯、版本兼容与后续Engine任务规范 |
| D32 | 独立交叉Review与交付准备审查 |

### Delivery A

| ID | 任务 |
| --- | --- |
| A01 | ABI描述、布局探针和版本读取 |
| A02 | 状态、能力及兼容性协商入口 |
| A03 | 同步句柄与资源lease |
| A04 | 拥有Buffer与异步租约 |
| A05 | 受控错误与panic转换边界 |
| A06 | Callback注册、撤销与排空 |
| A07 | Task异步桥与取消状态机 |
| A08 | 可选执行器、容量与关闭 |
| A09 | 绑定契约IR与输入验证 |
| A10 | C# LibraryImport绑定发射 |
| A11 | Rust导出与ABI一致性检查 |
| A12 | ABI、生命周期与AOT分析器 |
| A13 | MSBuild与Cargo可复现构建图 |
| A14 | Linux原生产物与AOT包验证 |
| A15 | Windows原生产物与AOT包验证 |
| A16 | 独立NuGet/crate发布与来源记录 |
| A17 | 真实同步Engine接入验证 |
| A18 | 真实异步Engine接入验证 |
| A19 | 生命周期与异步可执行模型 |
| A20 | ABI和资源跨语言性质与模糊测试 |
| A21 | 三路线基准与资源观测工具 |
| A22 | ABI/API升级与兼容性测试 |
| A23 | 线程亲和与特殊平台接入探针 |
| A24 | Engine接入脚手架及conformance入口 |

### Delivery B

| ID | 任务 |
| --- | --- |
| B01 | DataSource与数据库能力基础 |
| B02 | PostgreSQL纯C#适配与基线 |
| B03 | SQLite适配与线程/锁语义 |
| B04 | 可选Rust PostgreSQL Engine与Adapter |
| B05 | 事务状态、池租约与恢复策略 |
| B06 | 批量、COPY与流式读取 |
| B07 | 静态类型codec与值语义 |
| B08 | 迁移、Schema检查与升级协调 |
| B09 | 受限查询语义IR |
| B10 | LINQ/Fluent语法捕获增量生成 |
| B11 | PostgreSQL/SQLite SQL方言生成 |
| B12 | 静态Mapper、实体元数据与AOT |
| B13 | 运行时安全动态查询API |
| B14 | 关系、工作单元与并发更新 |
| B15 | Kestrel Native AOT Host与Handler |
| B16 | HTTP流、请求预算与背压 |
| B17 | 可选Rust Server Engine适配 |
| B18 | gRPC强类型与AOT协议包 |
| B19 | MCP协议包与静态JSON元数据 |
| B20 | 诊断关联、超时与关闭协调 |
| B21 | 通用幂等任务参考服务 |
| B22 | 端到端故障、崩溃与长期资源验证 |
| B23 | 领域全负载性能与内存报告 |
| B24 | 领域兼容矩阵、独立包与发布验收 |



## Source-driven amendment / 2026-11-12

Existing IDs remain authoritative. R19–R25/D14–D17/B01–B14 cover native SeaQuery/SQLx, no managed fallback or per-entity Cargo, typed Fluent instead of full LINQ SQL translation. R26–R31/D18–D20/B15–B24 cover native Service/Body reuse and retirement budgets, retaining Kestrel AOT. R13/R14/R18/D10/D11/A13–A16/A22/A24 cover precompiled consumers, upstream mapping and controlled upgrades. See [impact/recovery record](../traceability/source-driven-impact.md). Partial source evidence does not complete all tasks.
