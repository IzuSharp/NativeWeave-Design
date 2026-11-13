# Source lifecycle 四平台 job 归档独立审查

**结论：134/134 项核查通过。四个 ZIP 的实际 SHA256 与实时 GitHub API digest 一致，56 份归档 raw file 与 ZIP 成员逐字相同。20 份 source inputs 中，15 份与 Git blob 字节一致，Database Windows 的 5 份恰好是 LF → CRLF checkout 转换。** 未改写、归一化或覆盖原始执行输入，也未为这次归档审查重跑 fixture。

## 审查身份与对象

审查者为本会话子代理 `/root/migration_evidence`，独立于 Database 作者和归档整合者；本报告只审查来源、输入与归档关系。Database/D15 代码与独立本地执行见 `DATABASE-LIFECYCLE-REVIEW.md`；Server 代码/协议由另一个指定子代理独审。审查者自己编写的 Interop 补充复现没有在本报告中被包装为其独立代码审查。

| 对象 | 精确身份 |
|---|---|
| GitHub run | [43375871731](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43375871731) |
| 真实执行 source commit | `de43481581df9876cb2d0aed5de2db796d048c9d` |
| 已执行 workflow SHA256 | `81177ac3cce246b402db7275076f26be86c1ac4aa7d47ca8f7c44836c0e40965` |
| `verification/source-lifecycle/results.json` SHA256 | `a08300281336fca4a6ca89d067b4dac49f767ffa34c738288c50998d74365d0f` |
| 本审查实时 API 原始响应 SHA256 | `d43e391fca0662ab2139c05e0227e5a403d023b68b20c1194ad72ada44a1af5d` |

实时 GET 重新确认 run 为 completed/success、HEAD 为上述 commit，jobs 总数为 4 且均 success；artifact 总数为 4、各自 workflow_run/source commit 正确且本次核查时未过期。完整响应保存在 `source-lifecycle-live-api.json`。

执行矩阵为 Database / Server × Ubuntu 24.04 / Windows 2022，合计 12 个不同测试、24 次平台测试执行。此 run 没有 Interop 新 job，也没有把另一个已完成 PR #8 的 Interop 重跑混入本次新增覆盖。

## ZIP 与 raw file

| Artifact ID | 名称 | 实际 raw 成员数 | 实际 ZIP SHA256 = API digest |
|---|---|---:|---|
| 14014900927 | `lifecycle-server-retained-bytes-windows-2022` | 12 | `351f189006efd997bb43d5c5e925d49a00d45de9a5f4d0045478be73b37d6e41` |
| 14014880511 | `lifecycle-database-retirement-windows-2022` | 16 | `0c64ef55a8b742ea16561eedcabf3dd5ec07d72d285e2f15c123c8af2dff70ce` |
| 14014666488 | `lifecycle-database-retirement-ubuntu-24.04` | 16 | `ed99a8da14382f1e5eadc4ed47a0c940d169bde1352e1643be0eb3f2e0c09859` |
| 14014566727 | `lifecycle-server-retained-bytes-ubuntu-24.04` | 12 | `eec344cca170fa07b74bcf3ccb0650964f31e490fef09b90d31dfd3bacf766c0` |

对每个 ZIP 重新读取实际字节并计算 SHA256、核对字节数和 API digest，检查成员没有重复或路径跳转。每个 ZIP 的成员集合与该 artifact 的归档记录精确相等，逐项核对归档文件字节、长度和 SHA256；16 + 16 + 12 + 12 共 56 份，没有用解码重写后的文本替代原始成员。

## Windows 输入与 Git 内容的真实关系

Database Windows 的五个输入如下；其他 Database Linux 和 Server 双平台输入共 15 份均 byte-exact。

| 输入 | Git blob SHA256 | 实际 Windows checkout SHA256 | 字节数变化 |
|---|---|---|---:|
| `Cargo.toml` | `46eca720b4007926525bdad88eaa9e97fdb644a7e37aa6f646564c04388ddfb4` | `ff159de62d2fede24ed10c3f02de3fa748345b43efeca4af09bb5c5fe4b5c13a` | 531 → 547 |
| `Cargo.lock` | `0c309744a8ba9da809c8c7569a3bbef648b43b308df472197aa43b85f996a32c` | `5e3dfdb6b278f1b35b0055c34109f3ff2a4dd572531e3322cd86b252a7c815a2` | 28053 → 29160 |
| `rust-toolchain.toml` | `928f2ced7ea12731b9a5551f06f6088f9994577f32322b008a37007be103082e` | `0ce99f0775a7799b6b4244c677eccd97c4aa98b74b3b803fbfd1b5fc2f3f95be` | 52 → 55 |
| `src/lib.rs` | `39ce2db182ec02c6d4e2fb256ad9ae0141ab4d7c8806f732701308a8fd485c46` | `04f47138fff59d893be6383c7516cf21309249f1258620eb6aa2ed14dae1d5fd` | 10022 → 10236 |
| `run.py` | `bbd297f1d63c431475ce4e4be24beeddbbdf9b5a110cef9b373d1af5234cf366` | `a7d20e739d5b2bd0e5250a58acd63c39a75214daba97066f03f6db8a217eacc5` | 4237 → 4317 |

每一项转换都独立验证以下全部条件：Git 输入不含 CR；ZIP 输入恰好等于 `git_bytes.replace(b'\n', b'\r\n')`；反向替换后与 Git 字节完全一致；增加的字节数等于 Git 文件的 LF 数。没有接受其他空白、编码、源码或内容修改。清单中的 `git_blob_sha256`、`checkout_sha256` 和 `exact_LF_to_CRLF_checkout_conversion` 关系与这次实算一致。

Windows 原始 stdout 同样保持原字节，具名测试解析允许其行尾 CRLF。检查结果没有将 20 个输入全部标成 byte-exact。最初 strict 字节比较失败仍在 `artifact-verification-attempt-1.json` 中保留，并明确解释后续成功核查使用的精确关系；这没有改变实验结果或伪造重新执行。

## 结果与 workflow 对应

每个 artifact 的 result、具名测试 stdout 和命令退出码一致，六个测试名逐项匹配 source commit 中对应 Rust 源码；Database 的输入前后不变标记和 Server 的 source before/after hash 均复核通过。Server 记录的各日志 SHA256 也从 ZIP 实算核对。

已执行 workflow 固定实际 `github.sha` checkout，Actions 引用为完整 commit，contents 权限只读且不保留 checkout 凭据。上传在 `always()` 执行，覆盖根层 JSON/stdout/stderr/log/txt、inputs/**、binaries/**，并设置 `include-hidden-files: true`，因此 Server 的真实 `inputs/.gitattributes` 也在两份 ZIP 中。Linux 无扩展名二进制若位于 binaries/** 也不会因扩展名过滤而被漏掉；本次四 job 是纯 Rust有限研究，并未将不存在的 C# AOT产物列为通过。

本次归档审查支持精确研究来源与实际平台执行的真实性；不证明生产 adapter、PostgreSQL 故障、完整网络传输、RSS界限或正式契约接受，也不构成另一 GitHub 账号 approval 或跳过服务端规则的许可。逐项核查与所有输入双身份详见 `SOURCE-LIFECYCLE-CI-REVIEW.json`。
