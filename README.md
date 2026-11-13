> **Current phase:** research and detailed design, not product implementation. All executable research assets belong here. See [CURRENT-PHASE.md](CURRENT-PHASE.md) and [migration provenance](docs/traceability/research-asset-migration.md).

# NativeWeave Design

> 2026-11-13 最终研究、详细设计与独立技术审查。21 项契约的正式状态、固定版本与证据见[契约登记](docs/contracts/registry.json)和[精确接受索引](docs/contracts/acceptance-index.json)；R01–R34 / D01–D32 的任务接受在 Plan 登记。**研究设计接受不授予产品实施或发布授权。**

NativeWeave 的目标是让应用开发者主要使用现代 C#，通过 Native AOT 与独立 Rust Native Engine，获得可测量的性能、内存与开发效率收益。Database 底层必须使用 Rust，普通新增实体复用预编译原生资产；Server 底层同样必须 Rust，Rust 内部组合按源码与实验选型；Kestrel 仅作对照。独立 managed 组件保留纯 C# 路径；互操作基础设施按能力组合，不强制引入统一原生运行时。

## 阅读入口

1. [需求与边界](docs/requirements/charter.md)：用户授权、最新澄清与阶段 A/B 完整范围。
2. [34 项研究目录](docs/research/topics/)：各项 report、evidence、coverage 保留固定源码、真实实验、失败及适用边界；[R01 工具链事实](docs/research/topics/R01/report.md)。
3. [21 项版本化契约](docs/contracts/registry.json)：Core、Rust Database/ORM、Rust Server/协议、平台、验证与扩展；每项规范的标题状态由 registry 中的精确内容接受记录解释。
4. [最终独立审查](docs/traceability/reviews/final-2026-11-13/)：四份领域报告、验收完整性与 D32 续审、各执行者本人写入的精确绑定确认。
5. [设计结论与未来验证](docs/traceability/open-questions.md)、[模型与验收矩阵](docs/verification/models-and-matrix.md)、[ADR-0003](docs/decisions/ADR-0003-rust-engine-mandate-and-design-acceptance.md)。
6. [Plan 最终汇总 D32](https://github.com/IzuSharp/Plan/blob/main/ledger/reviews/D32.md)、[Plan 接受登记](https://github.com/IzuSharp/Plan/blob/main/acceptance-register.md)：34 Research、32 Documentation、114 份说明和 48 项未来 Codex 任务。
7. 历史恢复依据：[接管审计](docs/traceability/takeover-audit-2026-11-12.md)、[本轮实际恢复记录](docs/traceability/final-takeover-2026-11-13.json)、[生命周期检查点](docs/traceability/source-lifecycle-followup.md)。旧快照中的 proposed/partial 和旧 Host 选择按其历史时点解释。

## 正式状态与证据边界

本轮沿用既有 34R / 32D / 48Delivery 体系，保存完整研究与详细规范、真实不同执行者的技术审查以及精确来源绑定。契约接受绑定规范版本、内容 hash、不可变 Commit、依赖和实际审查；Plan 另绑定每项 R/D 的节点、说明、来源、依赖接受证据及独立确认。文件存在或 CI 成功本身不能代替独立技术审查。

已通过的研究实验保留其实际执行版本、平台与原始结果。后续只修正文档和接受记录时复用这些证据，不把它们标成新 Commit 上重新执行的结果。生产负载、完整产品组合、真正干净的无 Rust 消费环境、发布签名和性能收益由现有 A/B 验收任务证明。

48 项 Delivery 均保留 planned_candidate / not_authorized。NativeWeave 产品仓库保持原状；PR1 已关闭且未合并。未来阶段切换和产品实际验收独立于这里的研究设计接受。

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
python3 tools/verify_completion.py --require-complete
```

先按 Plan 的 source-driven-baseline.json 检出其固定 Design Commit；完整阶段校验会要求 34R / 32D / 21 契约均已正式接受。历史检查在原始配对 Commit 上完整执行；当前检查核对当前版本和独立绑定。工具不认证现实身份，也不证明未来产品安全或平台兼容。研究模型与验证记录在各专题中单独标明。


## Source-driven integration continuation

PRs #5–#7 preserve the preceding research, Rust 1.100 work and product-repository research-asset migration. Read [ADR-0002](docs/decisions/ADR-0002-source-driven-native-integration.md), [SeaQuery](docs/research/topics/R25/source-driven-seaquery.md), [Server](docs/research/topics/R27/source-driven-server.md), [Engine integration](docs/extension/engine-integration.md), [precompiled build/maintenance](docs/platforms/build-package-release.md), and [impact/recovery](docs/traceability/source-driven-impact.md). The finite Linux SQLite AOT query probe was recovered, not relabelled as new work or promoted to production. New finite experiments address [logical admission](docs/research/topics/R07/logical-admission-probe.md), [SQLx retirement](docs/database/sqlx-retirement-study.md), and [Body/retained-byte retirement](docs/server/body-retirement-protocol.md). Database is mandatory Rust; supported ordinary entity changes reuse precompiled native assets. Lifecycle, transaction safety and independent review remain mandatory.
