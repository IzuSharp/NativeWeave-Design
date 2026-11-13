# PR #8 逻辑准入研究：只读身份与归档核对

**结论：213/213 项通过。PR #8 已合并；主运行与偶发重复运行的身份、64 份原始文本、4 个实际 ZIP 和 8 个真实 native/AOT binary hash 均核对一致。** 本次只读取和下载证据，没有执行或重跑实验。

## 主证据身份

| 项目 | 精确标识 |
|---|---|
| [Design PR #8](https://github.com/IzuSharp/NativeWeave-Design/pull/8) 合并 | `3767f3c932ebf95bd82f6ed1c9bafc9eec1c5b1e` |
| PR head | `523a2f6543d3a8770cb3379f8fd7001abd6d8233`，与 merge 内容相同 |
| 主 run | [43373306474](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43373306474) |
| 主执行 source | `28f6cf7e6e4e80b9f32a92ad587a528d82911bd0` |
| 偶发重复 run | [43374127432](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43374127432) |
| 重复执行 source | `9fed6f510479622229cef6e917645f6510f7e3c0` |
| 保留的 D04 最新正文 SHA256 | `d527369dfd97a2d97ecd0930e25effc523791eb5e22586b1d9e18ac6f4aa31c9` |

重新 GET PR/run/artifact API 确认以上身份及 success。四份 ZIP 重新实际下载，计算摘要并与实时 API digest 和 manifest 三方比对；每份 ZIP 内真实 native 库和 NativeAOT 可执行文件分别重新计算 SHA256，与 result 记录相等。主与重复运行的九个 source input hashes 完全相同，且与各执行 commit 及 PR #8 合并内容相等。

| Run | Artifact ID | 平台 artifact | 实际 ZIP SHA256 |
|---|---|---|---|
| 43373306474 | 14013442125 | `logical-admission-windows-2022` | `d7ad2c8fbf3cab4f20ecbad7b8b83015a5e0cd827472ddd41420be9e7f7912a0` |
| 43373306474 | 14012619322 | `logical-admission-ubuntu-24.04` | `7e9ed1036c9daed3d61c55329b9b4b7a9de619387b86a44a03217dbad13cc3fc` |
| 43374127432 | 14013922287 | `logical-admission-windows-2022` | `5a33787d8bd8f85e69f0767f5e021b7aef71c1fde31e007f42e02314f7aed71e` |
| 43374127432 | 14012954553 | `logical-admission-ubuntu-24.04` | `841342506bf8acd7ec9febcc694e7e9c6cd7c6c9f78d6708b02e629c060c16e8` |

每个 artifact 的 16 份 raw file 均与 repository 归档字节相同，共 64 份。命令全部成功，stdout/stderr SHA256 正确；普通运行与 AOT 日志都包含 653 assertions、64 gate rounds、负控制观察及 exception-compensation 通过标记。保存的 SafeHandle.cs 为 265 行，Git blob `2d1f9313b485c57afab1f187e00a180df7fad3ba` 与 SHA256 `eddb5e1ad53377a5d60b7fdfeecb03a771b45406ec34802e5dbf068b71a117fd` 均实算一致。

`primary-results.json` 指向主运行；`results.json` 保留实际后续 run；`ci-trigger-correction.json` 明确它是文档 helper 意外触发的同输入重跑。该重复没有计作新增研究覆盖，原始记录也没有被覆盖或改名。

## 与本会话补充复现的关系

PR #8 的主 fixture 已在 Windows/Linux 各执行普通与 NativeAOT，覆盖 64 轮候选 gate、关闭后 Sum 和 SumHeld 拒绝，以及 managed exception 在取得 lease 后的 finally 补偿。它把既有 Bridge.cs 作为 linked source 编译，以聚焦新 admission 场景。

本会话在尚未获知并发 PR #8 完成时独立编写的 `interop-admission` 只新增了 Linux 本地复现：每模式 32 轮负控制和 32 轮候选、931/932 条细分断言，并实际使用本地打包的 NuGet PackageReference 消费。它没有 PR #8 的 managed-fault 注入覆盖。不能依据更大的断言数声称更广覆盖；NuGet消费能力此前也已有独立迁移证据，本次消费路线不构成再次跑 Windows 的必要理由。

最小重复归档方式与当前整合相符：继续以 `logical-admission.md` / `primary-results.json` 为 R07/D04 主入口；保留偶发 run 的触发纠正；将本会话源输入、逐条 Linux 日志和制品 hash 留为明确标注的补充独立复现；保留它运行当时的旧 D04 与 runner 身份，不改写原始结果。共享 source-lifecycle CI 只执行 Database/Server，不给这份补充复现再加 Windows job，也不新建 Task ID 或 accepted 契约。

## 范围与文件

审查者为 `/root/migration_evidence`。本报告是只读证据身份核对，未独立接受 PR #8 的完整架构/契约，也没有对本人所写补充源码冒充独立代码审查。C-LIFETIME-001 与其他生产门禁仍按实际 registry、独立审查和未完成证据处理。

逐项检查见 `PR8-IDENTITY-REVIEW.json`；实时 API 快照为 `PR8-LIVE-IDENTITY.json`；四份实际 ZIP 与下载摘要保存在 `pr8-archives/`；可复核脚本为 `review_pr8_identity.py`。这次检查没有新增 native/managed 执行记录。
