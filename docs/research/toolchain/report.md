# 工具链与现代语言机制：首次核验

状态：**事实核验报告；不是已经接受的产品工具链 ADR，也不是源码研究或运行验收。**

核验日期：2026-11-12，America/Los_Angeles。证据汇总时钟：2026-11-12 12:23:11 UTC（当地 04:23:11）。研究者：`toolchain_verification`。机器可读记录见 [evidence.json](evidence.json)。

## 1. 当前可证实的稳定基线

| 对象 | 本次核验结果 | 发布时间 / 支持期限 | 证据层级与限制 |
| --- | --- | --- | --- |
| .NET | **11.0.0，GA** | 2026-11-10；STS；当前官方支持表列 2028-11-14 结束支持 | 官方发布公告、下载页、机器可读发布元数据相互印证；尚未在本执行环境安装运行 |
| .NET SDK | **11.0.100** | 2026-11-10 | 官方下载页与 `releases.json` 一致 |
| C# | **15.0** | 随 .NET 11 SDK；`net11.0` 默认语言版本 | canonical C# 15 文档与 SDK 下载页语言表一致；具体新语法未本地编译 |
| Rust | **1.99.1**，本次检索可见的最新 stable | 2026-10-15 | 官方 release index 最新条目与固定发布日期公告一致；stable channel TOML 本次未成功读取，后续执行前必须再核验 |
| Rust edition | **2024 可用于稳定通道研究** | 2024 Edition 的 FFI 规则由官方 Edition Guide 定义 | Edition 与 rustc 版本分别锁定；不得把 edition 当编译器版本 |
| .NET 10 | 保留为兼容性比较候选，不作为本轮默认最新基线 | 当前官方表：LTS，2028-11-14 结束支持 | 是否正式多目标支持需要单独成本和下游需求决策 |

来源：[.NET 11 发布公告](https://devblogs.microsoft.com/dotnet/announcing-dotnet-11/)、[11.0 下载页](https://dotnet.microsoft.com/en-us/download/dotnet/11.0)、[11.0 发布元数据](https://builds.dotnet.microsoft.com/dotnet/release-metadata/11.0/releases.json)、[支持政策](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)、[C# 15](https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/csharp-15)、[Rust 发布索引](https://blog.rust-lang.org/releases/)、[Rust 1.99.1 固定公告](https://blog.rust-lang.org/2026/10/15/Rust-1.99.1/)。

**“最新”是带时间戳的观测，不是永久属性。** Rust 官方说明采用六周发布列车并只维护最新 stable；后续研究、实验、发布任务启动时重新核验，然后锁定准确版本。不能仅按日历推断某版本已经发布。参见 [Rust 发布与维护机制](https://doc.rust-lang.org/book/appendix-07-nightly-rust.html)。

### 1.1 本次处理的证据冲突

搜索结果中 `csharp/whats-new` 的旧缓存仍称 .NET 11 SDK prerelease，另一条 `dotnet/core/whats-new` 摘要仍称 RC2。实际打开版本专属页面、GA 公告、下载页和发布 JSON 后，均显示 .NET 11 已发布。版本结论采用更具体、可交叉核验的发布事实，旧缓存作为冲突记录保留，不能静默丢弃。

Runtime Async 的情况不同：canonical runtime 页面仍直接标注 preview；overview 的“无需 EnablePreviewFeatures”不能替代稳定性声明。因此把 Runtime Async 作为**待澄清的预览研究项**，不因为 SDK GA 就将所有可用开关升级为正式依赖。

## 2. 现代特性对 NativeWeave 的实际影响

以下“建议”均为本轮研究方向，不是已经通过源码、性能与跨平台验收的最终架构。

| 机制 | 本轮状态 | 值得研究的用途 | 必须避免的误判与验证义务 |
| --- | --- | --- | --- |
| C# 15 union types | 稳定文档可证实 | 面向开发者的成功/失败/取消结果、闭合查询节点 | `union` 声明生成的 struct 以 `object?` 存储，值类型 case 会装箱；不能直接承诺零分配，也不能作为 C ABI 联合布局 |
| 自定义 union / non-boxing access pattern | 官方 C# 15 参考描述 | 测量有明确标签和值字段的结果类型与 `TryGetValue` 访问 | 自定义存储必须满足官方行为约束；检查 default/null、分支转换、泛型体积、AOT 代码生成；不能仅凭语法推断性能 |
| Closed hierarchies | 稳定文档可证实 | 领域状态、查询 IR、编译器诊断对象 | direct descendant 在同一程序集内闭合；非 closed 的子类仍可能被外部继承，不能误认为整棵继承树自动封闭 |
| Collection expression arguments、extension indexers 等 | 列入 C# 15 稳定特性 | 降低 API 使用和内部代码重复 | 只在减少复杂度时使用；生成器支持、错误诊断与目标编译器必须有编译用例 |
| Memory safety 新规则 | **preview** | 隔离实验中评估指针与 ref 安全规则 | 不设置生产核心 `LangVersion=preview` 来获得它；当前稳定核心必须有独立实现路线 |
| Span/Memory/ref struct、值类型、静态抽象接口成员 | 已有稳定机制的研究基线 | 同步借用、显式内存所有权、静态分发 | 生命周期不能跨不允许的 await/回调边界；AOT 泛型实例化、装箱和代码体积必须测量 |
| `LibraryImport` 源生成 | 官方稳定机制 | 静态 P/Invoke glue 和可审查 marshalling | 生成成功不代表 ABI/生命周期安全；比较 blittable `DllImport` 和手工声明的实际支持范围，不武断宣称所有 DllImport 都不支持 AOT |
| Native AOT / trimming / 静态元数据 | 正式部署机制 | 正式 C# 应用的发布与验收 | `IsAotCompatible` 是分析声明，不是运行证据；每个目标需要 publish 后执行 |
| Runtime Async V2 | **canonical 文档仍标 preview** | 性能对照、异常栈、ExecutionContext/AsyncLocal 语义 | runtime 文档描述 NativeAOT/R2R 支持，但仍需具体版本实验；不将 JIT 专属优化收益转写为 AOT 实测收益 |
| .NET 11 内置 Zstandard / span 压缩 API | 官方库文档可证实 | 若选压缩为同步引擎验证模块，建立 .NET 自身基线 | 新的 Rust wrapper 必须解释相对内置库的真实价值，不能以缺失的旧版能力作为引入理由 |
| Rust 2024 `unsafe extern`、unsafe attributes | 稳定规则 | FFI 声明、导出符号、链接审计 | 声明进口函数的 extern block 与导出函数是不同语法；`no_mangle`/`export_name` 应记录安全理由 |
| Rust 2024 `unsafe_op_in_unsafe_fn` | 默认 lint 规则 | 将调用方义务与函数体中的不安全操作分离 | 显式 unsafe block 不能替代有效性证明、别名和释放规则 |
| Rust 1.99 原始布局与所有权 API | 稳定发布说明可证实 | `Layout::for_value_raw`、`Box::into_non_null`、`Vec::into_parts` 等降低 glue 重复 | 必须核对每个 API 的安全前置条件；不要使用 `Box::leak` 后再释放的模式代替清楚的 ownership transfer |
| Rust 1.99 C variadic definitions | 已稳定，但不建议作为通用 ABI 默认形状 | 既有 C 库适配的特定需求 | 能使用不等于应引入；typed fixed-arity 接口更易生成、分析和跨平台核验 |
| Rust 1.99.1 FFI bool 修复 | 官方补丁说明可证实 | 将布尔 ABI 回归列入测试 | 语言层类型大小与调用寄存器语义不同；明确 NativeWeave 的布尔 wire 表示并跨编译器验证 |

主要来源：[C# 15 功能表](https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/csharp-15)、[Union reference](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/union)、[P/Invoke 源生成](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/pinvoke-source-generation)、[AOT 部署](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/)、[.NET 11 runtime](https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-11/runtime)、[.NET 11 libraries](https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-11/libraries)、[Rust 1.99.0](https://blog.rust-lang.org/2026/10/01/Rust-1.99.0/)、[unsafe extern](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-extern.html)、[unsafe attributes](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-attributes.html)、[unsafe operation lint](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-op-in-unsafe-fn.html)。

## 3. AOT 与目标平台必须分层核验

不能从“某平台有 .NET SDK 下载”推导“Native AOT、选定 Rust engine、原生依赖和 NuGet 包已经共同支持该平台”。构建宿主、目标 OS/architecture、C runtime、最低 CPU、链接方式、engine 依赖和真实运行证据分别记录。

官方 AOT 文档明确限制动态托管程序集加载和运行时代码生成；表达式树具有解释执行路径，因此“Expression Trees 一概不能在 AOT 使用”是过度概括。ORM 研究应分别审查表达式构造、解释、SQL 翻译、动态编译以及元数据可达性。[AOT 限制](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/#limitations-of-native-aot-deployment)

官方跨编译说明不支持常规跨 OS Native AOT 构建；同 OS 部分架构间可在具备原生工具链时交叉编译。因此 Windows 和 Linux 验收需要对应宿主与实际目标执行，不能把本 Linux 环境的脚本成功当作 Windows 成功。[AOT cross-compilation](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/cross-compile)

.NET 11 runtime 文档改变了部分硬件基线。ABI、发行包和 benchmark 记录必须固定 CPU ISA 条件；它不是“只要 x64 就兼容所有旧机器”的保证。[.NET 11 hardware requirements](https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-11/runtime#updated-minimum-hardware-requirements)

Android 的 Native AOT 平台表仍列实验性并提示没有内置 Java interop。iOS、MacCatalyst、GUI native shell 等需要独立平台专题，不从桌面/server AOT 推演移动 UI 的完整成熟度。[AOT platform restrictions](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/#platformarchitecture-restrictions)

Rust 公告已说明未来 1.100.0 对 i686 Windows host tools 的调整；这是宿主工具变化，不能误写为不再能生成所有 32 位 Windows 目标。需要跟随实际采用版本重查。[i686 host-tool adjustment](https://blog.rust-lang.org/2026/10/02/demoting-i686-windows-targets-to-std-only/)

## 4. 本环境的实际验证范围

已实际运行一次 PATH/版本探针：Linux x86_64，glibc 2.41；Python 3.12.14；Git 2.52.0；`cc` 为 GCC 14.2.0。`dotnet`、`rustc`、`cargo`、`clang` 均未在 PATH 找到。

这只说明当前执行上下文中没有可直接调用的这些命令，不等于对磁盘所有目录做过安装普查。本专题没有安装编译器、编译 C#/Rust、执行 Native AOT、使用 Windows 主机或跑性能基准。所有相关实验目前状态均为 `not_run`。本轮确实完成的是官方资料检索、发布事实交叉核验和本地命令可用性探针。

## 5. 交给后续研究与验证任务的具体问题

| 验证 ID | 输入与方法 | 正常 / 反例覆盖 | 所需输出 |
| --- | --- | --- | --- |
| TC-V01 | 固定 SDK 11.0.100、Roslyn 准确版本，编译 C# 15 union 与 closed 样例 | 值类型 case、null/default、跨程序集派生、未穷尽 switch | 完整命令、编译器输出、生成 IL/原生代码检查、语言诊断 |
| TC-V02 | 原生 union、自定义 non-boxing union、普通 tagged struct 三组比较 | 成功/失败/取消分支、无值、泛型实例化、冷路径异常 | AOT 可执行样例、分配数、包体积和吞吐；不预设优胜者 |
| TC-V03 | 固定 .NET 11 默认 async 与显式 Runtime Async 配置 | 同步完成、真正挂起、throw、CancellationToken、AsyncLocal、线程切换 | GA 状态澄清、编译与运行记录、Windows/Linux AOT 对照；预览项不进入生产必要契约 |
| TC-V04 | `LibraryImport`、blittable `DllImport` 与生成 glue | bool、UTF-8、空 slice、无效 enum、结构体按值/按引用 | 目标 ABI、大小/对齐/offset 和调用返回值实际观测 |
| TC-V05 | Rust 2024 FFI boundary 最小样例 | 导入 block、导出符号、重复符号、panic unwind/abort | rustc/Cargo/链接器版本、成功构建及故障进程退出行为 |
| TC-V06 | Rust 1.99.1 对照前版本的 bool 回归用例 | x86_64 直接调用、函数指针回调、值 0/1 | 回归保护；不以单平台结果证明所有 ABI |
| TC-V07 | .NET 内置压缩与 Rust 候选 engine 的完整工作负载 | 空输入、无效输入、分片流、缓冲不足、大输入、取消 | CPU/RSS/吞吐/P99/复制/线程与开发成本；明确 native dependencies |
| TC-V08 | AOT 平台/RID/ISA/linkage 交叉表 | Windows/Linux、x64/Arm64、glibc/musl、不可用库、旧 CPU | 真实可执行制品及目标运行记录；未测单元不得列正式支持 |
| TC-V09 | 锁定 `dotnet/runtime`、`dotnet/roslyn`、`rust-lang/rust` 发布 commit | API→lowering→runtime/FFI→异常→测试完整路径 | 固定 SHA、文件、符号、覆盖清单；官方文档结论升级为源码证据前必须完成 |
| TC-V10 | 编译期生成器在锁定 Roslyn 下执行 | 增量输入变更、取消、并行编译、重复诊断、生成稳定性 | 可重现输入输出和 generator/analyzer 版本兼容记录 |

## 6. 建议的版本治理方式（待 ADR 审查）

研究快照在 `global.json` 锁定已核验 SDK，Rust 用 `rust-toolchain.toml` 锁定准确 release；工具链升级通过独立 PR，附发布事实、差异、受影响目标和回归记录。依赖锁定、SDK pin、Rust MSRV、edition 与 engine ABI version 是不同概念，分别维护。

不要提交 `latest`、不受控 nightly 或 `LangVersion=preview` 作为生产基线。支持周期不等于固定补丁永不更新；.NET 官方政策要求在支持期内跟随 servicing。是否支持 .NET 10 LTS、Rust 更低 MSRV 或某个旧 RID，交给需求与成本研究决定，不能在首次事实核验中自动扩张产品承诺。

## 7. 完成与未完成

本专题已形成可追溯的版本事实、现代机制风险点、实际环境限制和十项验证任务输入。**未完成**源码级编译器研究、任何运行/性能验证、所有平台支持认证、独立架构验收。本报告可用于并行研究和候选设计；不能作为产品发布验收证据。
