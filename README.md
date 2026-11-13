> **Current phase:** research and detailed design, not product implementation. All executable research assets belong here. See [CURRENT-PHASE.md](CURRENT-PHASE.md) and [migration provenance](docs/traceability/research-asset-migration.md).

# NativeWeave Design

> 2026-11-12 研究与详细设计续接，状态 **research / proposed**。这里保存源码研究、真实实验与证据；候选设计尚未成为 accepted 产品规范。当前进度见[生命周期续接检查点](docs/traceability/source-lifecycle-followup.md)。

NativeWeave 的目标是让应用开发者主要使用现代 C#，通过 Native AOT 与独立 Rust Native Engine，获得可测量的性能、内存与开发效率收益。Database 底层必须使用 Rust，普通新增实体复用预编译原生资产；Server 的 Kestrel/Rust 产品宿主按实际证据选择。独立 managed 组件保留纯 C# 路径；互操作基础设施按能力组合，不强制引入统一原生运行时。

## 阅读入口

1. [需求与边界](docs/requirements/charter.md)：用户授权、最新澄清与阶段 A/B 完整范围。
2. [仓库与环境核验](docs/research/environment-and-repositories.md)、[工具链事实](docs/research/toolchain/report.md)。
3. [源码研究目录](docs/research/source-catalog.md)、[Interop 初步发现](docs/research/interop/initial-findings.md)、[领域初步发现](docs/research/domains/initial-findings.md)。
4. [候选模块边界与关键问题](docs/architecture/candidate-boundaries.md)、[版本化契约登记](docs/contracts/registry.json)。
5. [证据与验证政策](docs/verification/evidence-policy.md)、[范围覆盖](docs/requirements/coverage-matrix.md)、[待解决问题](docs/traceability/open-questions.md)。
6. [首次独立审查](docs/traceability/initial-review.md)。
7. [Plan 仓库](https://github.com/IzuSharp/Plan)：既有34个 Research、32个 Documentation、48个候选 Delivery 任务及完整任务说明；任务数量不代表完成数量。

## 本批实际产出与状态

本批提供研究体系、已有少量固定版本源码证据、候选边界、模板、验证义务和可并行的文档编制输入。它不是“全部研究结束”，也不代表阶段 A 或 B 已验收。每条源码结论必须指明实际已读范围；测试存在、测试执行、AOT 发布和目标平台运行分别记录。

[契约登记](docs/contracts/registry.json)初始全部为 proposed。Research 与 Documentation 可以并行启动；产品开发任务只有满足具体契约、证据、审查和授权条件后才能进入实施。

## 文档约定

- 中文说明，API、符号、路径保持准确英文；每个文档标明状态、版本和负责专题。
- 原始需求是内容权威。**ArcForges Design / Plan 仅参考文档格式和组织方式，技术内容、工作规则、验收政策均不继承。**
- 官方资料、外部源码、实验是证据，不自动成为本项目的架构决策。
- 每个 accepted 决策需固定输入和独立审查；修订通过局部版本升级，不以全局暂停代替协调。
- 原仓库 LICENSE 保持不变；外部源代码未复制进产品，复用前另查对应许可证和来源。

## 检查

在两个仓库作为相邻目录时，从 Plan 运行：

```bash
python3 tools/validate_graphs.py
```

具体参数以 Plan 工具帮助为准。该检查仅验证计划数据与证据门槛，不证明 NativeWeave 实现安全或平台兼容。研究模型与验证记录在各专题中单独标明。


## Source-driven integration continuation

PRs #5–#7 preserve the preceding research, Rust 1.100 work and product-repository research-asset migration. Read [ADR-0002](docs/decisions/ADR-0002-source-driven-native-integration.md), [SeaQuery](docs/research/topics/R25/source-driven-seaquery.md), [Server](docs/research/topics/R27/source-driven-server.md), [Engine integration](docs/extension/engine-integration.md), [precompiled build/maintenance](docs/platforms/build-package-release.md), and [impact/recovery](docs/traceability/source-driven-impact.md). The finite Linux SQLite AOT query probe was recovered, not relabelled as new work or promoted to production. New finite experiments address [logical admission](docs/research/topics/R07/logical-admission-probe.md), [SQLx retirement](docs/database/sqlx-retirement-study.md), and [Body/retained-byte retirement](docs/server/body-retirement-protocol.md). Database is mandatory Rust; supported ordinary entity changes reuse precompiled native assets. Lifecycle, transaction safety and independent review remain mandatory.
