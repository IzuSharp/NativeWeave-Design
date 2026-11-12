# 证据、证明义务与验收政策

状态：proposed；版本 0.1.0；根据 NativeWeave 当前要求独立制定。ArcForges 文档只参考格式。

## 1. 结论分层

| 标签 | 允许说明 | 不允许推导 |
| --- | --- | --- |
| source_confirmed | 固定 SHA 的指定代码执行路径确实如此表达 | 当前机器已运行、全部项目无缺陷 |
| test_confirmed | 指定制品、命令和环境确实观测到结果 | 未测平台/架构也相同 |
| official_doc_confirmed | 官方来源明确陈述功能/限制 | 具体包组合必然正确 |
| inferred | 从已知证据推导，列出假设 | 把推断写成实测 |
| pending | 尚缺源码/运行/审查 | 计入已完成 |
| refuted | 有明确反例 | 以一次反例否定所有相关路线 |

代码示例另有状态：design-draft、static-reviewed、compiled、executed、native-aot-executed、independently-verified。每次升级附证据，不默认线性跃迁。source_confirmed必须记录解析后的完整commit SHA；release tag可并列显示但不能替代SHA。通过模型只增加 model_checked 记录，不升级为 AOT。

## 2. 每项证据最小字段

evidence_id、claim、classification、repository_url、完整commit_sha（tag只作显示定位）、file、symbol、line_range、read_coverage、limitations、collector、collected_at、related_requirements/contracts/tasks。运行证据另需：

- 源码与制品 SHA256、工具链与依赖锁、OS/architecture/CPU/ABI/链接器。
- 完整命令、退出码、stdout/stderr 位置及内容哈希、起止时间。
- 预期与实测、测试数量、失败/跳过/超时、输入和随机种子。
- Native AOT publish 产物被实际启动的证据；不能只保存编译日志。
- 分析器警告及处置；禁止全局抑制未解释警告来伪造通过。

## 3. 正确性验证方法选择

| 机制 | 证明义务 | 首选证据组合 |
| --- | --- | --- |
| Handle / owner | 单次释放、live lease、父子销毁次序、ABA界限 | 状态模型+属性/并发测试+实际调用与故障注入 |
| callback / async | terminal ≤1，注销后无非法访问，关闭可收敛 | 有限模型/TLA+、Loom适配native状态、C#并发调度测试、进程隔离崩溃测试 |
| buffer | 访问区间有效、长度溢出、对齐、allocator配对 | 属性测试、fuzz、Sanitizer；Miri只用于其支持的Rust路径 |
| ABI / generation | size/offset/calling convention、声明与实现一致 | C/Rust/C#三方layout与调用探针，生成快照和负例诊断 |
| SQL query | 参数化、NULL/Join/排序/数值语义 | 数据库差分、属性测试、真实PG/SQLite语料 |
| transaction | 失败不错误提交、未知结果不被当rollback成功 | 真实DB断线/超时/重启，状态日志与幂等恢复 |
| server | 有界内存/并发、慢端背压、graceful shutdown | 负载/故障/长跑、allocation与线程跟踪 |
| release | 来源可追踪，包与RID匹配，旧新兼容 | 干净consumer安装、AOT运行、SBOM/license、升级/降级矩阵 |

TLA+、Loom、Miri、Kani、fuzz 和 Sanitizer 是候选工具，不要求全部必用。每个工具固定版本、适用假设、不能覆盖的FFI/OS/调度行为；不能用部分模型宣称系统绝对安全。

## 4. 平台矩阵

首次必须规划 win-x64 与 linux-x64 原生目标构建运行。Arm64、musl、其他桌面与移动目标先建 capability matrix；真实需求与实验决定何时正式支持。32位研究布局差异，不因写了差异表就宣布支持。

“Windows/Linux通过”必须对应各自真实宿主、目标和制品。容器内Linux证据说明容器/宿主内核条件，不能充当用户专用MCP主机或Windows证据。当前只发现本地Linux执行与GitHub工具，未发现Windows/Linux专用MCP验收工具。

## 5. 性能方法

相同功能语义、数据集、TLS/协议、错误策略、并发、暖机和资源限额下比较 C# AOT、C# AOT+Rust、适当纯Rust。先验证业务结果等价，再讨论速度。

记录 cold start、稳态吞吐、CPU time、P50/P95/P99、错误率、RSS/峰值、托管GC、native allocations、复制字节、FFI次数、线程、包体积、长期泄漏和恢复。开放式负载注意 coordinated omission；保存延迟直方图和负载生成器瓶颈证据。基准机隔离资源竞争，独立重复多次并报告分布/区间。

暂不指定任意提升百分比或延迟目标。完成基线后以实际SLO、测量噪声和维护成本提出局部阈值。微型FFI benchmark只用于解释成本，不能替代端到端结果。

## 6. 审查与状态

四层审查：证据支持性；专题接口与生命周期交叉审查；独立整体对抗性审查；交付准备审查。作者不能独自将其重大设计标accepted。发现记录含ID、severity、位置、反例、影响、处置和验证。

审查范围固定到提交或文件哈希。源码证据、模型和脚本校验只证明各自范围；没有真实Windows/Linux AOT证据就不把相关产品能力标accepted。

研究文件可在proposed状态进入Draft PR供交流，正式实施的ready集合另行计算。未执行项不伪装通过，也不让不相关任务无故等待。
