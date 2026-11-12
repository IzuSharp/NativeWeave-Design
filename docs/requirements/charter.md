# 需求章程与交付边界

状态：需求整理；版本 0.2.0；日期 2026-11-12。依据：用户上传 NativeWeave 主任务及本轮澄清。此章程是研究输入，不是最终架构 ADR。

## 1. 目标

NativeWeave 是独立通用框架。应用入口、业务、状态管理、普通网络、系统调用、异步和高性能 C# 算法默认仍由现代 C# 表达。通过 Native AOT 发布；Database底层按最新澄清必须Rust；其他Engine按生态能力、成本、可靠性或实测效率选型。应用开发者原则上不必学习 Rust、手写 FFI 或重复处理跨语言生命周期。

“任何应用”表达可扩展方向，不表示所有工作负载已被支持，也不承诺 C# + Rust 在任何指标上同时胜过纯 C# 和纯 Rust。正式能力按平台、版本、功能与证据组合声明。

## 2. 不可妥协约束

| ID | 约束 | 验证方式 |
| --- | --- | --- |
| NW-P01 | C# First，C# 是完整应用开发语言 | 每个领域比较纯 C# AOT 基线；纯 C# consumer 无框架附加原生 runtime |
| NW-P02 | Native AOT Required | 每个正式目标真实 publish、运行和行为测试；警告审查 |
| NW-P03 | Rust When Justified | Database Rust是产品约束；其他Engine引入ADR须有能力/成本/可靠性或负载证据 |
| NW-P04 | 内外都简洁、优雅、高效 | 每个抽象有必要性、依赖和成本账本；删除不产生价值的层 |
| NW-P05 | Independent Engines | 单引擎可独立构建、测试、版本和发布；无隐式领域状态共享 |
| NW-P06 | Native-ready 接入流程 | 接入规范覆盖 ABI→glue→Adapter→AOT→包→兼容→发布 |
| NW-P07 | Performance by Evidence | C# AOT / C# AOT+Rust / Rust 可比工作负载，报告不确定性 |
| NW-P08 | 三种并行独立建模 | Research / Documentation / Delivery 各有图、文件所有权和状态 |
| NW-P09 | 两大阶段同步深入规划 | 数据库、ORM、Server 有具体研究、规范任务与候选实现任务 |
| NW-P10 | 内容独立 | ArcForges 是未来下游；Design/Plan 仅参考格式，不继承内容 |
| NW-P11 | 现代稳定机制 | 实验/preview/nightly 与正式必要能力分离，版本按日期核验 |
| NW-P12 | 证据诚实 | 不伪造源码覆盖、编译、运行、GitHub、review 或性能结果 |

## 3. 阶段 A：本轮必须完整研究和设计

ABI 类型与版本、自动绑定、强类型 C# Adapter、Ownership/Lifetime、SafeHandle/GCHandle、回调注销和重入、异步完成/取消/关闭状态机、缓冲区/Pinning/数据传输、错误/Panic、线程/背压、跨平台构建/AOT/NuGet/Cargo、可组合 Engine 接入。

至少用两种交互显著不同的真实候选模块验证设计：一个同步数据变换模块，一个有状态异步流式模块。候选优先可选择压缩/编解码与 HTTP 流或数据库流，但必须比较当前 .NET 原生能力，并独立决定选型。研究性模块用于暴露基础缺陷，不能据此绕过阶段 A 的生产验收。

## 4. 阶段 B：本轮同等深度规划

- Database：PostgreSQL 与 SQLite 候选矩阵；连接池、类型映射、参数、事务/保存点、查询流、批量、取消/超时、断线、重试幂等、迁移与恢复。
- ORM：实体/关系/投影/Join/聚合/分页、SQL NULL/排序/collation、参数化、强类型 Fluent Query、可选static metadata/DTO生成，不要求完整LINQ Provider、可控动态查询、AOT 元数据与诊断。
- Server：Kestrel/.NET 网络基线、可选 Rust 网络引擎、HTTP/TLS、gRPC/MCP 适配、请求响应流、背压、资源回收、shutdown、Metrics/Tracing。
- 组合验证：独立于 ArcForges 的参考应用；真实数据库、事务、迁移、请求取消、失败注入、长时间负载及恢复。

研究与文档立即并行。正式产品集成只能消费已接受且经过所需验证的局部基础契约。managed provider仅作独立源码/基准对照，不是产品数据库后端；不得把实际集成验收拆成无人负责的空壳。

## 5. 未来边界

GPU/GPUI/NSH、iOS/Android、线程亲和 UI、SIMD、编解码、其他协议只研究接入边界与平台约束，不在本次启动批次全面实现。移动平台是否成熟、静态链接/签名/Java 或平台互操作限制，必须单独核验。

## 6. 本轮授权与状态

已授权：读取指定仓库与公开来源；研究、文档、图、最小证明程序；安全创建研究分支和 Draft PR；准备未来 Codex 任务。

本轮不交付 NativeWeave 完整产品实现，不重构 ArcForges Go Center，不发布正式 NuGet/Cargo 包，不合并未经审查的重要架构决定。需要实测而环境不可用的项目保留明确未执行状态。

## 7. 最新澄清

用户明确：**“ArcForges 的参考规范 是让你看格式的 不是内容。”**

因此只观察文档目录、入口、链接、表格和记录格式。NativeWeave 的技术选择、执行政策和验收门槛均由当前目标和本项目证据独立建立。已读到的参考规范内容不作为本项目依据，不进行规则迁移。


## Source-Driven Deep Native Integration — clarified requirement

Study and reuse actual native structures, algorithms and lifecycle before designing the C# convenience layer. Prefer public APIs, but evaluate dedicated source-informed adapters, upstream extensions and controlled forks when justified. Never expose private Rust layout as ABI. Ordinary C# database entities/queries using enabled native capabilities consume maintainer-precompiled NuGet assets, without Cargo or a CI dependency for local execution. Typed Fluent is preferred over a full IQueryable/EF translator; no duplicate C# SQL engine. Optional generators supply static metadata/DTOs, not a mandatory runtime query compiler.

Preserve capability/error/ownership correctness, AOT and cross-platform acceptance. Compare native Server with Kestrel AOT, without presuming a winner. Source pins, locked closure, behavior/ABI/performance regression and patch retirement belong to D10/D11 and existing tasks. Research decisions, implementation verification and production acceptance are distinct.
