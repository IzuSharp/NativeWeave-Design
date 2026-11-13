# Plan 迁移独立审查：已合并 PR #4

**结论：通过当前迁移内容完整性与阶段边界审查，781/781 项独立内容核查通过，6 个隔离验证命令退出码均为 0。** 未发现阻止继续现有 Research/Documentation 工作的当前迁移内容缺陷。此结论针对下面的已合并 commit，不针对本会话随后创建的重复 PR #5。

## 审查身份与并发恢复说明

审查者为本会话子代理 `/root/migration_evidence`，独立于迁移补丁作者，未编写或修改所审查的 Plan、Design、产品源文件，未执行任何远端写操作。验证程序在本报告目录内的隔离 worktree 执行；它们生成的验证 JSON 留在该隔离副本。

本轮最初收到对另一个冻结的 47 文件迁移补丁的审查请求，该补丁后来提交为 `66902cfd9cbbd86223a30cf9002919cc1c261644`。整合者随后发现远端已并发完成 Plan PR #4，并已关闭产品 PR #1。因此停止了重复补丁的后续审查，把审查对象改为实际已合并的 PR #4；原来 47 文件补丁的检查结果没有转用为当前 main 的证据。原 Design 研究资产与 Actions artifact 的独立审计仍适用，因为其精确来源与内容 hash 均相同。

**这是独立于作者的本会话子代理审查，不是另一 GitHub 账号的 approval，不是 GitHub required review 的替代，也不是产品契约接受或产品交付验收。** 本报告只审查内容与本地可复核检查。历史 GitHub 规则执行、实际 PR/Actions 状态和产品关闭结果由整合者另行读取远端确认。

## 精确审查对象

| 项目 | 标识 |
|---|---|
| Plan 基线 | `f6ed91dddba62b9eba246f2af56ca5b93cc2593b` |
| Plan 已合并 PR #4 | `04c2f043c0ec60a2d49dd3ca8ea4ad1c8c888d89` |
| Plan 实际 tree | `85cb3a3b54778ab6f226f57dc0f204f6aff611ae` |
| PR #4 原 head | `00dfb1b5b0e299624d49cebe2d0dc1c92f9592d4` |
| 变更文件数 | 49 |
| 49 文件内容清单 SHA256 | `c1bbbb6a2cd88ac65466eb3a9eeef6be71b45a6e6b86d48e396d616b8629c8ec` |
| 完整二进制 diff SHA256 | `2b88c39f32beec75a4f1083a8e4afe498d5abb4b40e3db497938103a2ec3925d` |
| Design 合并输入 | `c7e123a74405a92dc3de1ef450355b08d1c05ceb` |
| Design PR #7 原 head | `d3db57b900cdfcc62bde85eefbd55bfbed507dd0` |
| Design 实际执行 fixture commit | `67b48674e469c98f2f73f1c9ff0d63b113abc47b` |
| Design 新运行 | `43371161177` |
| 原产品 PR #1 来源 | `267364a440074a61e193cf33315f1b9d0fa8126b` |
| 原产品 main/base | `658ed6a410783de356a7b9b2cd6601336fff5148` |

文件级 hash 清单见 `merged-plan-review-input.json`，完整差异见 `merged-plan-review-final.patch`。内容清单 hash 计算方式为对 `{base, files}` 使用键排序、紧凑分隔符的 UTF-8 JSON 计算 SHA256；files 保留 git diff 文件顺序，并记录 status、字节数、新旧 SHA256。diff hash 为 `git diff --binary BASE HEAD --` 原始输出的 SHA256。后续任何内容变化都需要重新核对，不能沿用本报告接受不同字节。

## 三图、packet 与依赖复核

独立程序直接读取 Git 对象中的基线及合并内容，未把新迁移 verifier 的断言结果当作唯一依据。

| 核查范围 | 结果 |
|---|---|
| 三图 ID、顺序、图级元数据 | 全部保留 |
| Research 34 节点 | 10 个 `partially_evidenced`，24 个 `planned`，与基线完全一致 |
| Documentation 32 节点 | 3 个 `partially_evidenced`，29 个 `draft_ready`，与基线完全一致 |
| Delivery 48 节点 | 全部 `planned_candidate`，授权均为 `not_authorized` |
| 实际修改 packet | 33 个，恰好是 12 个直接迁移节点的实际依赖闭包 |
| 其他 packet | 81 个与基线字节一致 |
| Delivery graph 与 48 个 Delivery packet | 全部与基线字节一致 |
| packet SHA256 与 revision | 114 个 hash 均匹配实际字节；33 个修改 packet 各增加一次 patch revision |
| 依赖 revision | 所有 dependency pins 与相应节点 revision 一致，未改变依赖边 |
| 契约与正式 Delivery 就绪状态 | 0 accepted contracts；ready/continuable Delivery 均为空 |

12 个直接迁移节点为 `D01 D02 D07 R03 R04 R07 R10 R13 R22 R25 R27 R29`。其余 21 个变更仅用于传播真实依赖 revision。逐个 packet 复核确认：除自己的 revision、必要的 dependency pins、12 个节点中明确的证据位置变更和研究阶段说明外，没有改写原研究责任、契约输入、验收内容、输出所有权或其他正文。所有原 Task ID 保留。

本次 `continuation_evidence` 将当前可访问位置指向 Design，同时显式保留 `historical_native_evidence_commit` 与 `historical_design_commit`。原证据状态仍是 `partial_execution_or_authored_draft`，`independent_review` 仍为 false。未把迁移成功冒充任务完成或契约接受。旧 `ledger/checkpoints/native-slices-2026-11-12.json` 字节不变。

## 研究资产与真实执行来源

当前 baseline 的 Design commit、原产品来源 commit、契约 registry hash 与独立资产审计一致。迁移 map 的实际 SHA256 为 `1f306d8f4625421360f4e324f1e83f1382d53155f9b6748a7c11682af7b9c1c8`；新结果清单的实际 SHA256 为 `b3ad8b53f4c5aa80107e4b7b63489bd46a319040d58af3ced6dba8b19863a220`。它们均是从固定 Design 输入实际读取并计算的值。

此前独立资产审计 `INDEPENDENT-MIGRATION-AUDIT.md` / `integrity-audit.json` 已通过 1240/1240 项核查；本轮重新确认精确来源和 map/results 字节不变，故该审计仍适用。该审计包括 139 个来源至目标映射、137 个字节一致文件、仅 2 个路径适配 runner、112 份历史原始证据、90 份 Design 新原始证据、14 个实际下载 artifact ZIP 的摘要与成员、Interop 二进制摘要和真实 source/lock hash。`integrity-audit.json` 本次绑定 SHA256 为 `300dd3f516e36939ec4776f57e6328a74c8efa7f102e950da7c448a4870db7a5`。

历史 112 份证据仍保留原执行来源：8 个平台记录，其中 6 个成功、2 个最初 Database 编译失败。Design 新结果明确属于 `67b48674e469c98f2f73f1c9ff0d63b113abc47b` 和 run `43371161177` 的六个 Windows/Linux 平台任务。历史结果没有被改标为 Design 重跑结果，新的执行也没有被改标为产品交付。本审查没有再次执行 Rust/C# native fixture。

现有的 clean Rust-free host 等未覆盖义务仍未变成通过；历史独立审查报告缺口也没有因为本次归档审查而被补造。

## 当前阶段与 CI 边界

`CURRENT-PHASE.md`、AGENTS、README、research/documentation policy 和 execution policy 均明确限制当前阶段为研究、详细设计与未来实施规划。实验留在 Design；正式 A/B Delivery 和产品源码写入没有授权。产品 PR #1 只能在已验证 Design/Plan 迁移合并后关闭，不得合并或删除历史。旧执行授权段落被明确标为受最新阶段约束。

最终完整性 workflow 从实际 PR head 或 push SHA 检出 Plan，再读取该 snapshot 的 `design_merge_commit`，要求完整 40 位 SHA，并以该 SHA 检出 Design。本次因此固定到 `c7e123...`。workflow 使用 read-only contents 权限，不检出产品仓库，不保留 checkout 凭据；Actions 版本固定为完整 commit。原图门禁脚本和 schema 字节未改变，验证步骤没有 `continue-on-error` 或绕过失败的 shell 分支。

一次性引用迁移 workflow 使用 Plan 写权限，但严格限定为 `IzuSharp/Plan` 的 `research/pr1-asset-migration` 分支，只向该研究分支 push；未检出或写入产品仓库。该实现的目的与当前只读完整性 workflow 不同，报告没有把它误称为 read-only。

本地源码检查不能证明某次历史 GitHub 合并是否满足服务端所有 required checks/review/rules；本报告不对此作替代性声明，也不授权绕过规则。

## 独立执行的检查

在实际 PR #4 隔离 worktree 上依次执行以下命令，六项退出码均为 0；stdout/stderr 与命令记录见 `merged-plan-validations.json` 和 `merged-plan-validation-*.stdout/.stderr`。

1. `python tools/verify_research_assets.py`
2. `python tools/validate_graphs.py`
3. `python tools/mutation_checks.py`
4. `python tools/rust1100_checks.py`
5. 三图使用 `Draft202012Validator` 验证 `schemas/graph-v1.schema.json`
6. `git diff --check f6ed91dddba62b9eba246f2af56ca5b93cc2593b HEAD --`

14 个既有 mutation case 均使错误状态 fail closed，4 个 Rust gate 回归检查均通过。额外独立程序 `review_merged_plan.py` 完成 781 项检查，包括逐节点语义、逐 packet 字节/依赖/证据迁移比对、精确 Git tree 和 diff 绑定、阶段边界、workflow 身份与旧门禁保留；详细结果全部保存在 `PLAN-MIGRATION-REVIEW.json`。

## 后续维护事项与结论范围

`verify_research_assets.py` 当前把“相对 f6ed91 基线恰好 33 个 packet 变化”作为历史迁移断言。它在当前迁移 snapshot 上正确通过，但后续合法研究若修改更多 packet 并更新 source-driven baseline，会可能触发同一个 workflow 后失败。届时应明确限定或重构历史 checkpoint 的检查范围，同时保留本次原始证据；不应为了保留数字 33 而伪造 packet 内容或跳过失败。本项是未来维护约束，不是当前迁移完整性失败。

合并前生成的 checkpoint 保留 `awaiting verified Plan merge` 字样，属于当时观察；它没有声称本报告确认了 PR 关闭。本轮整合者已通知远端 PR #4 合并及产品 PR #1 关闭，本子代理只将其作为并发恢复背景。最终远端状态应以整合者的实时 GitHub 读取记录为准。

**可继续现有 Research/Documentation 的缺失研究与详细设计。不得据此提升任务状态、接受产品契约、执行 A/B Delivery、重复合并迁移补丁或重新操作已完成的产品关闭动作。**
