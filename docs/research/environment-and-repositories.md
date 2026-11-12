# 仓库与执行环境核验

日期：2026-11-12；时区 America/Los_Angeles。结构化原始观测摘要：[repository-snapshot.json](repository-snapshot.json)。此报告只陈述实际检查范围。

## 1. 三个正式仓库

| 仓库 | 核验时main提交 | 初始根目录 | 权限/本轮操作 |
| --- | --- | --- | --- |
| [IzuSharp/NativeWeave](https://github.com/IzuSharp/NativeWeave) | `658ed6a410783de356a7b9b2cd6601336fff5148` | 只有LICENSE | pull/push为true；未修改 |
| [IzuSharp/NativeWeave-Design](https://github.com/IzuSharp/NativeWeave-Design) | `7034fb54490bb397379787c9b2da3609b393185f` | 只有LICENSE | pull/push为true；研究分支创建成功 |
| [IzuSharp/Plan](https://github.com/IzuSharp/Plan) | `ed6e8e8e1203bbe3149cfb49c418da81a9d9749d` | 只有LICENSE | pull/push为true；研究分支创建成功 |

两份文档仓库已有main和初始commit，因此无需在默认分支做空仓库初始化。研究分支统一为 `research/bootstrap-2026-11-12`，从各自观察到的准确main提交创建。保留原LICENSE；未更改权限和保护规则。

权限元数据不等于每个写动作已经成功。分支创建已实际成功；提交、Draft PR等结果以本轮最终交付记录与GitHub返回为准。本文件的初始快照有意保留动作发生时的状态。

## 2. 参考材料的用途

已定位并检查 ArcForges Design/Plan 的入口、目录、引用和表格组织；检查了固定快照的README、追溯JSON片段与任务图片段。**仅用于理解文档格式和组织方式。**

用户后续明确“参考规范是看格式，不是内容”。NativeWeave 不继承其技术架构、执行规则、验收政策和业务边界，也不把它们作本项目的决策依据。DesktopPlatform 的代码阅读不构成引入该项目为依赖，当前候选设计的技术证据优先来自独立上游官方源码。

此前对话中仓库权限与状态只作为检索线索，本次已重新调用仓库API核验。未取得完整旧背景原文，当前上传材料与用户本轮澄清为需求权威；不根据旧摘要添加新约束。

## 3. 真实可用能力

- GitHub：仓库元数据、contents、固定ref文件、tree和branch读取；创建研究分支已成功；创建tree/commit、更新ref和Draft PR工具存在。
- 本地：Linux x86_64 shell、Python、Git、GCC可调用。工具链专题实际探针见其证据JSON。
- 未发现专用Windows或用户Linux MCP验收工具。当前Linux容器不是Windows运行证据。
- `dotnet`、`rustc`、`cargo`、`clang` 未在PATH找到；不据此声称全磁盘没有安装，但本轮没有C#/Rust/AOT编译运行结果。
- 可真实委派三个子代理，本轮确实分别承担工具链、领域源码、三图编制；随后交叉审查root候选文档。

## 4. 本次能够真实验证的范围

可以核验官方资料、固定源码、JSON/图结构、Python研究模型、文档引用与GitHub操作。不能将这些成功换算为Native AOT支持、数据库事务可靠性、Windows通过或性能达标。阶段A/B真实运行验证作为具体任务保留，不以stub或JIT代替。
