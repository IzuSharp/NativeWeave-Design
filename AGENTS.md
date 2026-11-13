# NativeWeave Design 协作约定

本仓库保存研究、候选规范、accepted 规范及全部研究实验和原始证据；未来实现仓库是 IzuSharp/NativeWeave，任务和执行状态在 IzuSharp/Plan。当前阶段边界见 [CURRENT-PHASE.md](CURRENT-PHASE.md)。

1. 优先遵守用户当前需求。ArcForges 规范只作为格式参考，不导入其技术内容或执行规则。
2. 研究、文档编制和未来产品开发是三套图。没有技术依赖或文件冲突的工作可并行；不设置单任务全局锁。
3. 读取当前任务、已固定证据、契约版本和最新分支。只修改任务声明的文件；共享索引由整合任务更新。
4. 引用源码时记录完整 commit SHA、实际文件、符号、行段和已读/未读覆盖。动态分支 URL 只能用于导航。
5. 不把候选源码路径写成已读证据，不把测试源码写成已执行测试，不把 JIT 或分析器成功写成 AOT 目标运行成功。
6. 关键例子区分 draft、static-reviewed、compiled、executed、native-aot-executed、independently-verified。后面的状态需要相应证据，不能凭前一个状态推导。
7. Core不新增默认全局Rust runtime；Database/ORM/Server底层必须Rust；Rust内部组件按证据选型，Kestrel仅作对照；ArcForges只参考格式。源码驱动深度复用，普通C#实体不默认要求Rust重编译。
8. 不修改 LICENSE、仓库权限或保护规则。分支与PR按已有授权推进。2026-11-12用户允许Design PR5/Plan PR2在无可用独立Reviewer时经严格自审和真实检查合并，必须记录未独立审查并保留复审；此例外不改变GitHub强制规则或自动接受proposed产品契约。当前阶段以 CURRENT-PHASE.md 为准：只推进研究、真实实验、详细设计与未来 Codex 规划；不执行正式 Delivery，不写 NativeWeave 产品源码。
9. 发布证据中不记录凭据、用户私人数据或无关环境变量。基准参数和匿名环境描述应足够复现。
10. 发现缺陷以发现 ID、影响、证据和处置记录；“以后再补”不能关闭正式验收阻断项。
