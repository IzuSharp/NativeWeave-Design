# 首次 Bootstrap 独立局部审查

审查者：`toolchain_verification`。日期：2026-11-12。审查类型：对其他作者产物的 limited adversarial review。**这不是 NativeWeave 全产品最终验收，也不把本审查者自己编写的工具链报告算作独立验收。**

## 范围与方法

本次先审查 root 编写的候选边界、证据政策、契约登记、需求章程、五个模板及三图 ADR；并检查 AGENTS/README 的相关一致性。方法为逐文件内容检查、与用户当前要求及澄清比较、识别潜在状态晋升漏洞。本文件初次写入时 Plan 图和校验器尚在编制，尚未宣称运行其反例测试。

审查快照使用内容 SHA256，避免后续修改使本次意见看似针对新版本。整改后必须记录复查范围与新快照；不能仅更改发现状态。

| 文件 | 初始被审查 SHA256 |
| --- | --- |
| docs/architecture/candidate-boundaries.md | `6baed2965aac588633dcecd2959fe592d9972ec95ddd9d4d835097a735dd3670` |
| docs/verification/evidence-policy.md | `78c8a47ca86ec918b0c11628443575dbe7bb3f468e20b2c6169da5426a430de1` |
| docs/contracts/registry.json | 初次结构读取与取哈希之间有并行修订；本项以文末最终复查快照为准，不把修订后哈希当成初稿哈希 |
| docs/requirements/charter.md | `ada66993334e1754832c7e8e4be90cc61c91b1ca13568bc4ec26a4c68a7bc5ad` |
| docs/decisions/ADR-0001-three-graphs.md | `2e78346f3a464185c24d39bb33a12e12b8a43f826b719f47371dab93ffb331e7` |
| templates/adr.md | `bfe674b927ec53bdeecb770a70d08d71142ea60ca011bfdd14ebffbbf15278e0` |
| templates/code-validation.json | `e8df6d4472a47731efc03874105774d2ca9d3ee34ab7a9e49998420026770285` |
| templates/research-report.md | `7a591ff5b4d106ad31144b08761f0ee4e65be17cdab60e6fd8695fdc25cb7c6f` |
| templates/task.md | `e722716e7c8eb2eb6b4ef7a9a236e28d34d89992c3a3d5354ae4d097c096e8b2` |
| templates/technical-spec.md | `137f4a4ec42a400a0cef2220223c69da43a188fd9d36fbabb37f82baddcecbeb` |

## 已确认的范围内优点

1. 用户“ArcForges 规范只参考格式”已明确写入需求章程、AGENTS、证据政策和 ADR；本次被审文本没有要求沿用其业务、技术选择或串行规则。
2. 边界文件明确标记 design-draft；契约当前全部 proposed；没有将候选 API、现代语法、源码阅读或文档存在冒充编译运行结果。
3. 异步公开完成状态与 native quiescence 分开建模，明确 `terminal ≤ 1` 只是安全性、不是最终完成保证；记录同步完成、同步 cancellation registration、回调注销与在途回调问题。
4. 数据库提交结果未知、Drop 回滚与确认不同，server 队列条数与字节预算不同，均被明确列为研究义务。
5. 三图 ADR 区分启动依赖、接受依赖和契约输入，允许研究及文档在候选输入下开始，未设置“所有研究完成”的全局前置门。

## 发现

### RV-TC-001 — 契约接受记录尚不足以机器验证内容与独立审查

- 严重性：**P1，阻断将该机制宣称为可安全自动接受契约/启动产品实现**；当前全 proposed 的研究草稿不因此暂停。
- 位置：`docs/contracts/registry.json`，与后续 Plan validator 的连接。
- 证据：初始登记项仅含 ID/version/status/title/evidence/reviewers/specification_status/content_sha256；没有规范文件定位、作者身份、审查记录所绑定的内容版本、依赖契约准确版本。
- 反例：若后续校验器只要求 `accepted`、非空 evidence/reviewers 或非空 hash，填写任意字符串即可表达“已接受”，即使规范不存在、审查针对旧内容或审查者就是作者。
- 已执行程度：结构审查；本项初次记录时尚未取得最终 validator，因此**不声称已经实际绕过校验器**。
- 建议：proposed 允许缺字段；任何 accepted 晋升必须校验规范路径与实存内容哈希、非模板证据记录、独立审查者与作者不同、审查准确绑定该内容及版本、依赖契约的准确版本和状态、未解决阻断发现。
- 验证：使用临时反例副本验证缺规范、错哈希、自审、旧审查、模板证据、错版本依赖均被拒绝；保留真实基线可通过。
- 处置：已发送 root 与 Plan 作者；等待整改后局部复查。

### RV-TC-002 — managed reverse callback 的异常与签名失败需要分别规定

- 严重性：**P2，阻断对应 callback/error 契约接受**；不要求首次报告完成全部实现。
- 位置：`docs/architecture/candidate-boundaries.md` 第 5 节及 callback/error 后续任务。
- 证据：初始文本深入列 Rust panic/unwind/abort，但没有对 C# reverse callback 的普通异常边界与进入方法体前的签名错误分别提出规则。
- 风险：只实现 Rust `catch_unwind` 不会处理 C# 回调体异常；仅在 C# 方法体加 try/catch 也不能修复非法 UCO 签名导致的 fail-fast。
- 新官方事实：.NET 11 在启用 runtime marshalling 时，native 调用带非 blittable 参数/返回值的 `[UnmanagedCallersOnly]` 方法（例如 bool 返回、char 参数）可产生不可恢复的 InvalidProgramException/fail-fast。来源：[Native AOT interop](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop#native-exports)，2026-11-12 实际打开核验；这是官方文档证据，未本地编译复现。
- 建议：普通 managed 异常在回调适配层内捕获并按确定的 status/error 通道记录；out 参数与资源清理具有异常路径约定。非法签名由 generator/analyzer 阻断，并安排独立进程 Native AOT 负例。进程致命故障不能伪装为可恢复 Result。
- 验证：回调体主动 throw、错误映射自身失败、Dispose/取消竞争、非法 bool/char 签名、开关变化和生成绑定一致性。
- 处置：已发送 root；等待候选边界和任务输入补充。

### RV-TC-003 — 固定源码身份要求在模板间不一致

- 严重性：**P2，证据可追溯一致性**。
- 位置：`docs/verification/evidence-policy.md`、`templates/research-report.md` 与 `AGENTS.md`。
- 证据：前两者写 `commit_sha/tag` 或 `完整SHA/tag`；AGENTS 要完整 commit SHA，动态分支仅导航。
- 风险：release tag 名称可以用于人类定位，但只存 tag 无法自动验证研究时的具体对象与后续引用仍一致；不同作者会按不同门槛标 source_confirmed。
- 建议：保留 tag/version 作为显示信息，同时要求 source_confirmed 的代码证据记录 resolved 完整 commit SHA。官方网页事实另走 official_doc_confirmed，不强塞代码 SHA。
- 验证：模板与门禁对 source_confirmed 无 SHA 的输入一致拒绝；官方文档事实允许无源码 SHA，但保留准确 URL、检索日期及范围。
- 处置：已发送 root；等待统一。

### RV-TC-004 — 运行证据模板缺少自身政策要求的部分可复现字段

- 严重性：**P2，证据模板完整性**。
- 位置：`templates/code-validation.json` 对照 evidence-policy 第 2 节。
- 证据：模板尚缺起止时间、依赖锁、CPU/ABI、预期与实际、超时统计、输入/种子及结构化日志内容哈希等政策字段。
- 风险：作者严格照模板填完仍无法满足政策；若 validator 只检查现有模板字段，记录的“成功”可能绑定错制品或无法复现。
- 建议：补全字段，说明不适用字段如何给理由；校验器对 executed/native-aot-executed 的最低必填集合严格验证。模板继续 `is_template=true/status=not_run`，不能作为任意 accepted 证据。
- 验证：失败退出码、tests_failed>0、超时、missing log、错 artifact hash、只有 publish 没有执行的记录不得作为产品能力通过证据；允许明确记录失败实验而不把它当验收通过。
- 处置：已发送 root；等待补充。

### RV-TC-005 — direct P/Invoke 的加载策略应加入构建专题问题

- 严重性：**P3，具体研究补项**。
- 位置：后续 build/packaging/linkage 规范。
- 官方证据：[Native AOT direct P/Invoke](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop#direct-pinvoke-calls) 说明该模式由 OS loader 解析，不遵循 `DefaultDllImportSearchPathsAttribute`；动态依赖缺失可在进程启动时失败。
- 建议：将默认 lazy binding、direct binding、静态链接的加载路径、缺库失败、符号重名和平台 linker flags 分别纳入比较与验收，不把 managed resolver 的保证套用到所有链接模式。
- 处置：已通知 root；作为后续具体研究义务，无现成最终策略承诺。

## 当前结论

当前材料适合以明确 proposed 状态进入研究与文档协作；不支持把 NativeWeave 产品、ABI、AOT 平台或计划自动验收机制标为已完成。上述发现需要按影响范围修订或保留为相应接受门的阻断记录；不能用“首次报告”作为关闭具体问题的理由。

Plan 三图与校验器的后续复查，以及 root 对本发现的具体修复，须另列下面的复查记录；本文件尚未给出全产品 final acceptance。

## Plan 三图与门禁追加发现

### RV-TC-006 — 整个未来专题不应成为基础 Profile 接受前置

初版 D01 必须等待整个移动平台 R33；D11 必须等待 GUI/GPU R32；D13 必须等待完整参考应用 R31。它们可通过基础契约传播，扩大成与当前 Windows/Linux 基础能力不相称的等待。严重性 P2。

Plan 作者将这些连接改为 reference-only，保留 D21 对未来平台的真实研究责任。独立复查图确认：研究与文档没有被人为排列成串行链；扩展问题仍有明确节点。**已按初版图的影响范围修复**，未来新契约仍需按实际 profile 分别审查。

### RV-TC-007 — 选中的可选组件需要进入对应集成与发布验收

初版 B04/B17 有选型状态，但该状态未成为 B21–B24 的条件接受输入；发布范围也没有明确绑定协议包 B18/B19。严重性 P1，影响未来集成/发布接受，不是本轮已经发布了无证据包。

Plan 作者增加 conditional dependencies、selection snapshot、release scope 和组成任务准确版本。独立检查确认选择 B04 会激活 B21 的接受依赖并改变其证据 subject；未选原生路线仍不成为纯 C# 路线的前置。**针对本次发现已修复结构连接**。本轮没有声称任何组件已经实现或通过真实集成。

### RV-TC-008 — 校验器初稿可接受自相矛盾的 AOT 证据及越权输出

初稿 validator SHA256 为 `70dcb13d10050ec708dbdfc03d7c81806e2052200b7376df0f4668b22e280b4a` 时，独立临时夹具重现了以下问题：

- `status=passed/kind=native_aot_run`，但 `aot.executed=false`、失败/超时计数为 1、日志为空，`evidence()` 返回零错误。
- 输出路径 `NativeWeave:src/` 与允许写入路径 `NativeWeave:src/Only/` 被对称 overlap 当作合法归属。
- node fingerprint 只保存 prompt 路径，未绑定正文内容，旧审查可能不随正文变更失效。
- `author=None` / `producer=None` 可在字符串化的身份检查中遗漏。

严重性 P1；这些是**合成测试数据**，没有修改正式契约状态、编译 AOT 二进制或运行产品。

作者补充：方向性的 scope containment、packet SHA256、强类型非空 identity、运行完成/失败/超时字段、AOT 发布与执行字段、运行模式、目标 RID、原始 stdout/stderr 哈希、时间区间和 binary 哈希。修订版 `d3ce977aa46f838a2c3ec47147e3e148f78b30e17bfcf7d46d383a1fbdbfdfc0` 下，独立负例确认它们被拒绝；符合结构的正控制仍可通过。**这一组具体漏洞已修复**；校验器仍不能认证真人身份或证明命令确实执行过，这些继续由独立原始证据审查负责。

### RV-TC-009 — 依赖任务实现改变后，下游证据必须失效

修订中 `node_digest` 排除 `source_commit`，适合避免把“任务定义授权”与每次实现提交混为一事。但 dependency snapshot 初版仅含依赖任务 revision 与任务定义 hash，没有实现 source commit / acceptance evidence hash。依赖实现改动并重新验收后，下游旧集成证据可能仍匹配。严重性 P1，影响未来接受传播。

建议在 dependency snapshot 中同时绑定依赖实现 source commit 和已接受证据的哈希；保持定义授权与实现来源分离。已发送 Plan 作者，最终处置见后续复查表。

## 复查记录

### 文档修订复查

| 发现 | 独立复查结果 | 当前处置 |
| --- | --- | --- |
| RV-TC-001 | registry 已补作者、规范路径、依赖和 reviews；实际正负夹具验证缺规范、错 hash、自审、旧 subject、模板证据及 null 作者被拒绝 | 本轮门禁范围已修复；不等于技术内容通过验收 |
| RV-TC-002 | candidate boundary 已分别规定普通 managed 异常 containment 与 .NET 11 非 blittable UCO 签名 fail-fast | 文档补项已修复；C#/Rust/AOT 负例仍未执行 |
| RV-TC-003 | policy 与研究模板统一要求 source_confirmed 有 resolved 完整 commit SHA | 已修复 |
| RV-TC-004 | code-validation 模板已补起止时间、依赖、CPU/ABI、预期实测、超时及日志格式 | 模板补项已修复；新证据仍需按 Plan 机器格式校验 |
| RV-TC-005 | candidate ABI 部分加入 direct P/Invoke 与 OS loader 的具体义务 | 初始研究问题已补；最终链接策略未决 |
| RV-TC-006 | D01/D11/D13 的未来整专题前置已调整 | 已修复结构连接 |
| RV-TC-007 | 可选组件选择进入条件依赖和 selection snapshot | 已修复本轮结构连接；发布本身尚未授权或执行 |
| RV-TC-008 | 图、契约、运行证据正负控制按预期通过/拒绝 | 已修复复现的具体漏洞 |
| RV-TC-009 | 依赖实现 source_commit 与 acceptance evidence 哈希均已进入 snapshot；分别改变任一项都会使下游 subject 改变 | 已修复并独立复测 |

### 实际执行的独立检查

初次独立结构检查覆盖全部 114 节点：34 Research、32 Documentation、48 Delivery；所有 packet 路径存在，start+acceptance 联合图无环，声明的独占写入路径未发现重叠。

修订门禁的独立正负夹具检查覆盖：未改动基线、prompt 篡改、输出越界、缺依赖、循环、空证据 accepted、完整合成契约正控制、缺规范、错规范 hash、缺 review、null 作者、自审、旧 review subject、阻断发现未关闭、模板证据，以及原生分支选型引起的下游 snapshot 变化。真实基线结果为：34 个研究任务和 32 个文档任务可启动；0 个产品 Delivery 可启动；真实 registry 无 accepted 契约。

运行证据另作 13 组检查：一个结构完整的合成正控制；未运行 AOT、JIT 误标、失败检查、超时、旧 source commit、错 RID、缺 binary、null producer、缺原始日志、日志 hash 错误、逆序时间及缺开始时间。13 组均产生预期结果。

首轮夹具曾以旧的 logs 数组形状提供日志，因作者已增加 stdout/stderr 字典 schema，那个正控制被正确拒绝；修正测试夹具后重新执行上述 13 组。此处没有隐藏测试失败，也没有把旧格式兼容失败当作产品缺陷。

### 有限异步研究模型的独立审查与复跑

独立读取并复跑 root 的 `experiments/async-quiescence/model.py`，输出到临时结果，不覆盖作者结果。修订模型 SHA256：`2e05810a13a46959dc301dab8deef69fad49af8435934c62250900820a4178c7`；独立输出 SHA256：`47706780600c303d36c2c886286ad05b5de3d8f386812973c17b0fff7cae2755`，与作者结果逐字段相同。

- 过早回收负控制在 226 个探索状态内找到 use-after-free 路径：close → publish cancellation → native queue → reclaim → callback dereference。
- 加入 native quiescence 与 call lease 的候选在 159 个探索状态内未发现所检查的反例，存在 9 个已回收状态。
- 违反安全性质的路径在首次违反后剪枝，因此这些计数不是用于比较两设计复杂度的完整状态空间规模。
- 结果 publication 的 compare/exchange 和 admission/lease 原子性是模型假设；`≤1` 检查没有证明某个实际语言原子实现正确。
- 已补 managed CancellationTokenRegistration 的回调 lease、注销等待和 context 访问未建模；native quiescence 不自动证明托管取消注册已经静默。
- 单操作、单回调、有限状态、顺序一致性及非活性证明边界写明。没有将该模型升级为真实 C#/Rust/GC/FFI/Windows/Linux AOT 安全证明。

本次审查支持把上述模型作为**有明确边界的研究证据和反例**继续使用；不授予任何产品契约 final acceptance。

### 最终门禁复查与收敛

最终复查 validator：`d4e393016bd75de523b78f2df9c989eb417dbc7bdd05ca9f23a1fbefb58888c9`。实际执行确认：真实基线仍通过，ready 为 Research 34、Documentation 32、Delivery 0，accepted contracts 为 0；分别改变依赖实现 source_commit、依赖已接受证据哈希及原生分支选型都会改变下游 subject。输出方向约束与 null identity 检查仍拒绝原反例。正式验收需求已包含准确 OS、architecture 与适用时的 target RID，校验逻辑同时比较这些字段。

| 最终复查文件 | SHA256 |
| --- | --- |
| NativeWeave-Design/docs/architecture/candidate-boundaries.md | `7153a79a7284585570f148000e48756a5804035b9bcccaa6e356e3203d272d3f` |
| NativeWeave-Design/docs/verification/evidence-policy.md | `f6c343fa613a282f837218f913fe5a1b850f82ab37ba40f254943b868f50ff4f` |
| NativeWeave-Design/docs/contracts/registry.json | `f5b688a59d879bc59a89810523c4291fca8dbccdc23774d6ea58bdf5a4912868` |
| NativeWeave-Design/templates/code-validation.json | `d73d5f0b6511642e921e7f80f985cfe86f5e09104c25247969ef74912fdb3665` |
| NativeWeave-Design/templates/research-report.md | `14db0c6d8d55f368f46f68ed3d6a8a4a88d896adb4b421ff1dd156ad4dc173f9` |
| Plan/research-graph.json | `6e8ae7aed21b976760609fb2d21fb4b9412f0e264ee2fb8d8ccde90502639f06` |
| Plan/documentation-graph.json | `9488cf8a5075a187ff7eb51d27f706fab4486f81765c2c5092da04b036f1bad4` |
| Plan/delivery-graph.json | `391bc63d9842d7a08e30d2a3c50f7e41d9cd2abe1a18bcedcd5342375d5ea5df` |

**本次 limited review 发现的具体启动包缺陷已完成局部修订与对应复查；可以继续以 proposed/bootstrap 状态分发研究与文档任务。** 这项结论只限本报告所列文件、状态与反例，不是全面源码审计、产品实现授权、平台认证或最终架构接受。所有实际语言/FFI/AOT/Windows 验证与正式领域研究仍按各自任务执行。
