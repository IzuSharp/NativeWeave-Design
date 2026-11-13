# Server / Extensions 最终独立技术审查 — 2026-11-13

**结论：建议接受 R26–R33 与 D18–D21、D29–D30 声明范围内的研究和详细设计；没有未解决的本范围阻断性 Finding。** C-SERVER-001、C-PROTOCOL-001、C-REFERENCE-001、C-EXTENSION-001 的当前 0.3.0 规范可进入正式设计接受。B15–B24 的实施计划可供未来阶段执行，当前产品实现、长期负载、发布和移动/GPU 支持均未验收。

## 1. 执行者、独立性和输入身份

独立执行者为 `/root/server_review`。原研究作者包括 `/root/server_extensions`、`/root/database_research`；本次规范修正由 `/root` 完成。本执行者没有撰写所审的规范或任务修正，只提出 Finding、阅读真实源码/实验/输出、复审修正并撰写本审查记录。这是独立技术执行者审查，**不是另一个 GitHub 账号的审批**。历史审查和实验的作者身份保持原样。

恢复入口是 Design `5bb128424259f3d9cf594b4e50d7688ad5b6541e`、Plan `7359060f88f94591b0dc41178e35701eefc8eb6d`。它们是远程恢复基线，不能代替本轮已修文件的身份。本报告在 `2026-11-13T13:00:53.014486+00:00` 固定当前逐文件 SHA-256；完整研究输出、24 份相关任务 packet、fragment 和支持证据列表见同目录 `server-review.json`。共享 graph/registry 尚将由整合者写入正式接受记录，不把它们的整文件临时哈希当作固定审查主体。

| 任务 | 当前规范/细化输出 | SHA-256 |
| --- | --- | --- |
| D18 | `docs/server/hosting-and-streaming.md` | `1b2aee53926004b11535167ef44a1c7ca7bc1a148a8f676b182add5aa2344d1d` |
| D19 | `docs/server/protocols-and-observability.md` | `baf35e49784995322d5c25a65767ee7340678c0411d235c01ea53a84c6aeffeb` |
| D20 | `docs/verification/reference-application.md` | `c6c7cefa5645a17a2d0bd19973969f6f46b4c0e6fb0556a99032e96a93db02be` |
| D21 | `docs/extension/future-platforms.md` | `fa41359b578e998feb9479d7e3ab47a400f69aca141967a75200ed3fa4febd54` |
| D29 | `fragments/server.json` | `9b81edbf25672b020011b808e3b716c752388b210c808e7eb636a4a0f015e5a1` |
| D30 | `fragments/end-to-end.json` | `217c78e4e6d1d7fe380025d8ef32c2406464900c4e2ffd71d17417973fd71160` |

审查读取了两个仓库 AGENTS、R26–R33 的报告/来源/覆盖记录、四份规范、Body 退休补充、相应 R/D packets、B15–B24 packets 与两个 fragments。图引用依赖的 R34、R17/R18/R21、D12/D13 及 Core/Database 全域验收仍由其他明确分工的独立审查覆盖；本报告不冒充其完整审查。

## 2. 逐项实质结论

| 任务 | 结论 | 已审查的实质依据 | 未来产品义务与限度 |
| --- | --- | --- | --- |
| R26 | 接受声明范围内的研究/设计 | 已审真实 Kestrel 研究程序、静态 AOT 路由、流/请求边界断言和 Windows/Linux 原始证据。5 项执行只建立可复用等价比较入口；其网络能力没有被误作 NativeWeave 正式 Host。 | B23 以相同语义/数据/协议/负载比较完整产品；当前未声称 Rust 有实测吞吐或内存优势。 |
| R27 | 接受声明范围内的研究/设计 | Tokio/Hyper/Tower 与选择性 Axum 的复用和 Adapter 边界具体；C# 静态 Handler 注册复用预编译 native。通知只借用票据，Request/owned-header 领取与拒绝释放明确，不另建大型 Core runtime。旧 optional-Rust 文字已修。 | B15/B17 将来执行真实两语言 Handler、panic/异常、拒绝/取消/关闭和普通无 Rust 消费；研究切片不冒充完整 Host。 |
| R28 | 接受声明范围内的研究/设计 | 独立复读 Tonic unary/trailers 源码、作者 19 项与另一执行者 5 项 cardinality 反例/修复；每请求 Decoder 的单消息模式区分零消息/空 payload，并保留流式多消息。rmcp 公共服务接缝、准确 profile、运行时 metadata、认证/Origin、TLS 分层清楚；补齐 JSON 物化前预算。 | B18/B19 证明完整 C# ABI+HTTP2/TLS 互操作、压缩/解码峰值与 MCP preflight 实际公式；原有13项两OS、19项Linux和独立5项Linux范围分别保留。 |
| R29 | 接受声明范围内的研究/设计 | 明确 Tower ResponseFuture permit 与 Body 终结、HTTP2 flow credit 与 backing bytes 存活的差别。双侧独立预算、分配前许可、copy 重叠双记账、last-owner 退休和 active/retiring slots 满足关闭期上界推理。 | B16/B17/B22 用真实慢读、半关闭、retain、取消/EOF/close 竞争检验资源退休与有限 deadline；队列项数不等同 RSS 上界。 |
| R30 | 接受声明范围内的研究/设计 | 源码、布局探针与改正计量窗的两OS Release AOT 原始输出已核。默认 Release/Debug 均不隐式启动 listener/exporter；日志 IsEnabled 与 trace sampling 分离。诊断失败不阻止业务释放，先前 Windows 失败仍保留。 | B20 证明真正跨 FFI parent/golden bytes/非法字段；B23 分测 Debug、disabled/sampled/full、日志、Meter、exporter 故障。零线程分配观察不能外推零开销。 |
| R31 | 接受声明范围内的研究/设计 | 规范给出 operations/items/outbox/attachments、租户/hash/留存、独立事务观察者与外部 oracle。COMMIT Unknown 不被 cleanup 改写，冲突幂等查询使用新 statement snapshot；与数据库独立审查确认的真实 PG 反例一致。 | B21/B22/B23 实现全栈故障、重启、durable blob-before-reference、outbox 至少一次、30分钟/24小时/72小时分层负载与等价统计。当前设计接受不宣称这些已执行。 |
| R32 | 接受声明范围内的研究/设计 | 独立核读固定 Winit/WGPU 源码范围，区分事件循环线程、surface/window 生命周期、映射/提交完成及 callback 退场。当前仅输出 Engine capability 和生命周期约束，未预造全局 GUI/GPU runtime。 | 未来独立领域实施/平台授权后执行实际 device-lost、window-first-destroy、map/poll 与主线程测试；本轮没有 GPU/GUI 运行证据。 |
| R33 | 接受声明范围内的研究/设计 | 固定官方 .NET/Rust 平台资料与 Winit 生命周期源码支持分开描述 iOS/Android、AOT/R2R/实验状态。Android suspend 回调返回前 surface 失效/释放义务明确；桌面 AOT 未被外推真机支持。 | 未来逐目标证明静态链接/裁剪/加载、签名、真机/模拟器、暂停恢复；本轮不声明移动部署或生产支持通过。 |
| D18 | 接受声明范围内的研究/设计 | Rust 主导网络/协议/运行时，C# 主导业务；Buffer/byte owner、request/response、callback 退休和 async result 的分离可实施。流 EOF、响应 future 完成与 SafeHandle/GC 根静默不混同。 | B15–B17/B22 证明动态竞态、实际内存与完整 Host 行为。底层 Core 契约按对应独立审查接受。 |
| D19 | 接受声明范围内的研究/设计 | 准确 Tonic raw Codec 接缝、单消息约束、rmcp Tower 接缝/预解析峰值准入、TLS/认证边界、trace ABI 和 diagnostics 默认/成本模式均已明确。两项最终阻断已修并独立复读。 | B18–B20/B22–B24 的真实实现、协议一致性、MCP 公式证明、FFI trace、负载与发布保留为产品验收。R34 的全域审查由其他执行者负责。 |
| D20 | 接受声明范围内的研究/设计 | 64MiB Gm/Gn 分侧总预算、每请求每侧4MiB、256 active/retiring、128 metadata waiter、32KiB chunk 与 D18 一致；64MiB附件是流总长度。幂等、Unknown、outbox、blob 顺序与 bounded Close/joining Dispose 可执行。 | B21–B24 执行完整系统及长期资源验收；DB专门语义由 /root/database_review 对固定输入独立确认。 |
| D21 | 接受声明范围内的研究/设计 | capability、线程亲和、event loop、native owner 与 mobile target 区分明确；各领域 Engine 独立，普通 Core 不承担全局窗口/GPU/mobile runtime。 | 未来领域/平台工作独立授权；设备执行、签名、分发与平台兼容没有现在 accepted 的声明。 |
| D29 | 接受声明范围内的研究/设计 | B15–B20 精确模块/接口、步骤、失败路径、证据、write scopes 与 worktree 已逐项核。B15 接受依赖 B17，B17 不反向等待 B15；100历史+110最终重叠字段对图一致，未新增规划体系。 | 6项仍为 future planned delivery；实际产品测试与 AOT/NuGet 消费不得复用研究 passed 代替。 |
| D30 | 接受声明范围内的研究/设计 | B21–B24 从精确参考服务到故障、长期负载、性能与发布的输入、局部依赖、文件归属和证据可执行。并行 worktree 与 A13共享manifest整合职责明确；依赖联合图无循环。 | 4项需未来阶段授权和真正完整产品执行；30分钟/24小时/72小时、无Rust独立消费者、不可变包与兼容矩阵不是当前成功项。 |

## 3. 本轮 Finding 与关闭依据

### SR-FINAL-01 — 默认诊断和构建模式，Medium，已关闭

原规范没有完整区分 Release/Debug、日志启用、采样和 exporter。D19 现给出明确模式表：两种构建默认不安装 listener、Meter provider、全局 Rust subscriber 或 exporter；应用显式配置 sink/级别/采样和预算。日志在 `IsEnabled` 后格式化，trace tags 在启用/采样后构造；trace sampling 不得抑制已启用的 Warning/Error 日志。Debug 断言不能定义 Release 正确性，资源准入/释放/退休计数始终有效。B20/B23 同步了真实实现及成本矩阵。本执行者复读后关闭此项。

### SR-FINAL-02 — rmcp JSON 物化前内存准入，Medium，已关闭

独立读取固定上游 `modelcontextprotocol/rust-sdk@53e64a93c8e32d8f7699af587b9e28566929940c` 的 `crates/rmcp/src/transport/common/server_side_http.rs:207–267`。完整 blob 为 `ba248ba82a9ea001cf24eb5e26a438b0011506db`；返回完整文件 13011 bytes 的 SHA-256 为 `1421d3610d487ed51d5c37674e4717b52531cae5330fde2ac286ac2fd1146f09`，计算出的 Git blob 一致。`expect_json` 是 `pub(crate)`；先用 `BytesMut` 收集有 wire 长度上限的请求，再调用 `serde_json::from_slice::<ClientJsonRpcMessage>`。C# DTO 验证或 `get_tool` 都发生得太晚，1MiB wire 上限不能证明 4MiB 的真实树/复制重叠峰值。

D19/B19 修正使用公共 `StreamableHttpService` 外层的 native Tower admission：一个计费的有界 wire buffer、成熟 serde `Deserializer`/`DeserializeSeed`/`Visitor` 结构预扫、深度/节点/成员/字符串/解析工作上界与预留 scratch；不构建临时 `Value` 树、不调用私有 helper、不手写 JSON grammar。按固定 SDK/parser profile 的布局和容量增长计算并预留 wire、SDK 再收集、native tree、UTF-8 桥与 managed DTO 的重叠峰值；两侧预算分开。不具备可证明界限的 profile 不能启用，不合预算的请求在 SDK parse/Handler 前拒绝。

B19 负例明确许多细小元素、深层嵌套、长转义字符串、全局/单请求边界和取消，要求准入失败时 SDK parse/Handler 计数为零、lease 恰好释放一次。以上是可实施且可检验的设计，不声称未来实现或具体数值公式已验证。已独立核对保存的源码摘录哈希及 R28 新来源绑定后关闭。源码记录见 `verification/server-completion/rmcp-json-admission-source.json`。

### SR-FINAL-03 — R27 optional-Rust 旧措辞，Low，已关闭

原 graph 的 verification 仍残留 Rust 可因性能结果而成为可选路径的措辞。当前 R27 packet/graph 明确测量用于选择和优化必需 Rust Host 的引擎组合，Kestrel 只作为比较基线，与用户授权架构一致。

### REC-SERVER-BUDGET-01 — D20 预算说明，Low，已关闭

独立复核恢复/修正后的 D20：native 与 managed 的总预算 Gm/Gn 各 64MiB、每请求每侧 4MiB、256 active/retiring slots、128 metadata-only waiters、32KiB chunks。64MiB attachment 是完整流长度，不是可同时保留的 payload。copy overlap 先计费，永远无法容纳的峰值在等待前拒绝，不以 body EOF 回收仍有 owner 的字节，不声称 RSS 总上界。

### SR-FINAL-04 — 已保存 artifact 文件在恢复副本缺失，Medium，已关闭

旧 artifact manifest 中两份 `KestrelComparator.staticwebassets.endpoints.json` 标为已保存，恢复副本因 publish ignore 缺失。整合者从原工作区恢复 Linux/Windows 原始各 53 bytes；本执行者重算两份均为 `c1686417e8d5c31bba969f12b6f3d2b35e6609adb5ca42f212261a3a02771aac`。这不是重建或伪造原始证据；发布提交需实际带上这些字节。

## 4. Tonic、Body 与关闭的关键正确性复核

本执行者重新读取固定 Tonic `grpc.rs` unary 请求接缝及 `decode.rs` 的 `trailers()`：默认 unary 先取第一条，随后 drain 剩余消息，因此第二条可能被静默丢弃。不能从 API 名称或成功返回推导恰好一条。

作者修复使用每请求新建、带 remaining quota 的 public `Decoder`：unary 与 server-streaming 请求仅允许一条；第二条解码错误在 Handler 之前返回，零消息与合法零长度 payload 区分。client/bidi streaming 保留多消息模式和独立消息/字节额度。当前 `protocol-reviewed-local` 的 19 项实执行结果、`server-review-cardinality` 另一执行者的 5 项独立反例/回归与实际源码吻合。本次没有重新运行实验，也不把旧 13 项跨平台结果改写成新 19 项跨平台结果。

D18/D07 的物理 owner、业务准入、Body 终止和 callback 退休分别建模。Tower response future 结束不能自动终止 Body；HTTP2 flow credit 释放不能自动释放应用保留的 `Bytes`。EOF、取消、channel close 或 C# Task 完成不等同最后 byte owner 消失。复制保留两个 owner 时同时计费，response chunk permit/retiring request slot 直到对应 owner 真正退场；bounded Close 与等待静默的 Dispose 也不混同。这些规则及未来 B16/B17/B22 的负例可以阻止生命周期状态被表面完成信号提前回收。

## 5. 实际证据核验及范围

初次恢复审查重算了历史独立记录中 238 个存在的 `(path, expected SHA)` 输入；全部匹配。它们是**修订前的历史身份检查**，不是现在 R28/R30/D19 仍等于旧哈希的声明。当前 `reviewed_outputs` 明确绑定修订后字节。另核对 11 个本地 research run manifests、60 份 stdout/stderr、18 份可恢复的固定上游源码缓存；成功和失败记录都保留，没有重新标注失败为成功。

最新诊断 run [43401371233](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43401371233) 的两个真实 job（Ubuntu `131804743640`、Windows `131804744074`）由本执行者通过 GitHub 独立查询，均成功。整合者取回原 artifact；本执行者独立重算了提交保留的 20 份文件、12 份命令流与 6 个输入 checkout 转换。Windows 三个源文件是可验证的 LF→CRLF，Linux 字节一致。每平台实际 AOT 运行 11 项断言通过。

200000 次 warm no-listener 调用均返回 null Activity；两 OS 各观察到 current-thread allocation 0 bytes；Windows 16.634ns/call、Linux 20.468ns/call。该单次 Release Native AOT 观察不证明平台性能优劣、Debug 开销、logging/Meter/exporter 成本、原生内存或真实 FFI 传播成本。早期 Windows 失败 run `43390177287` 仍完整保留；它没有到达输出数字，不能推断具体分配量或归因给 ActivitySource。binary/archive 字节重算由整合者完成，本执行者未重新执行/独立重算可执行 ZIP，记录边界不混淆。

另实际查询 run `43401371232` 的全部 11 个研究 job 均成功；这里只作为平台 CI 状态，不用 success 元数据替代未独立下载的最新 protocol stdout。证据主体仍使用各已保存 manifest 明确列出的源码/案例/平台。

对 R31/D20 的数据库接缝，当前独立执行者 `/root/database_review` 实际读 PostgreSQL fixture、原始 stdout 与输入哈希，确认 COMMIT proxy 读到完成/idle 后吞回复、另一连接观察 durable 效果，以及竞争 CTE 由 `pg_locks` 同步后旧 snapshot 查不到、新 statement 查到的反例。其固定 manifest 为 `verification/completion-ci/43388468172/completion-postgres-ubuntu-24.04/postgres/manifest.json`，SHA-256 `2657a79ccf8c11b351fafe23bd3f928c7b597d23cad7d22d89caa4a88cbf239e`。这属于明确归属的交叉审查输入，未伪称本执行者新运行 PG。

## 6. B15–B24 的可执行规划检查

| 任务 | 开始依赖 | 额外接受依赖 | 独立 Worktree/分支 |
| --- | --- | --- | --- |
| B15 | A02, A07, A10 | B17 | `task/B15-implementation` |
| B16 | A07 | 无额外 | `task/B16-implementation` |
| B17 | A07, A10, A11, B16, A02 | 无额外 | `task/B17-implementation` |
| B18 | B15, B17 | 无额外 | `task/B18-implementation` |
| B19 | B15, B17 | 无额外 | `task/B19-implementation` |
| B20 | B17 | 无额外 | `task/B20-implementation` |
| B21 | B04, B08, B13, B14, B15, B17 | B20 | `task/B21-implementation` |
| B22 | B21 | 无额外 | `task/B22-implementation` |
| B23 | B21, A21 | B22 | `task/B23-implementation` |
| B24 | B22, B23 | A16, A22, B18, B19 | `task/B24-implementation` |

已比较两个 fragments 与 delivery graph 的 110 个重叠字段，全部一致；26 个 B15–B24 packet 内规范摘要均与当前字节一致；三图 start+acceptance 联合依赖无循环。文件所有权各归模块，根 solution/Cargo workspace 等小范围共享注册由 A13 整合，不占全局 worker 锁。

B15 只先完成 C# 应用/静态 Handler 层，其接受需要真正 B17；B17 依赖 Body/Core 但不反向依赖 B15，故不制造环。协议 B18/B19 在两层就绪后执行。B21 的集成起点和 B20 的接受前置允许相关工作并行，B22/B23/B24 承担故障/长期资源、实际性能和领域发布，未把它们提前置为实现通过。

**当前没有产品实施授权。** 根整合者应将本审查与其他独立审查绑定到精确规范/证据，完成正式接受及两仓库提交。若 packet 再生成使本文冻结字节发生实质变化，应针对 diff 再确认；仅写共享接受索引也不得伪称新的实质内容已审。
