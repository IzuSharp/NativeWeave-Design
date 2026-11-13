# 未决问题与证据缺口

状态：设计回答、实现验证、生产接受分别记录；2026-11-12。这里记录实际未解决事项；每项只阻断依赖该事实的正式契约，不阻断其他专题开始研究/写草稿。

| ID | 问题 | 负责研究 / 文档 | 关闭依据 | 当前影响 |
| --- | --- | --- | --- | --- |
| Q01 | win/linux实际AOT工具链与目标矩阵 | R01/R02/R13 → D01/D10 | 固定SDK/rustc/链接器、真实publish/运行 | 正式平台支持待证 |
| Q02 | pointer或代际token、长度宽度、ABI协商 | R03/R07 → D02/D04 | 布局/调用/兼容/失效句柄实验与成本 | ABI未接受 |
| Q03 | 唯一ABI描述来源与生成器复用范围 | R05/R06 → D03 | 对比真实输入/输出/诊断、AOT负例 | 不预选csbindgen全栈 |
| Q04 | callback/context回收与managed取消注册静默 | R07–R09/R15 → D04–D06 | 反例、模型、实机并发与shutdown | 生命周期核心待证明 |
| Q05 | Task或ValueTask、池化和迟到通知 | R09/R17 → D06/D13 | 正确性先行，分配与收益实测 | 无默认复用池 |
| Q06 | shared runtime是否必要，线程亲和怎样组合 | R12/R18 → D09/D11 | 两异质引擎、无Rust路径、线程/RSS账目 | 不引入巨型Core |
| Q07 | buffer transfer、Pinning、复制/零拷贝 | R10/R16/R17 → D07 | 所有权/别名/溢出/异常/吞吐实验 | 不承诺零拷贝 |
| Q08 | Rust panic与C#callback异常、fatal边界 | R11/R04 → D08/D03 | subprocess负例；unwind/abort和UCO签名分析 | 无“捕获所有异常”承诺 |
| Q09 | 包/RID/静态链接/加载路径与来源 | R13/R14 → D10 | clean consumer、ABI版本、资产/依赖、SBOM | 未发布包 |
| Q10 | 两个真实Engine的选择 | R17/R18 → D11 | 同步/异步差异与当前C#基线对照 | 不以mock代真引擎验收 |
| Q11 | Rust动态数据库与预编译复用 | R19–R25 → D14/D15 | SeaQuery+SQLx候选及有限Linux查询AOT，无逐实体native构建；有限Rust fixture已有Windows/Linux执行 | 设计回答形成；独立接受/PG/完整C#数据库Windows AOT验证pending |
| Q12 | Unknown事务效果、pool恢复与幂等 | R21/R31 → D15/D20 | COMMIT响应丢失、原子幂等、实库故障 | 不能取消即视为回滚 |
| Q13 | Typed Fluent及static metadata/DTO | R23/R25/R06 → D16/D17 | 普通native-backed Fluent，不要求完整LINQ Provider | 设计问题已回答；SG/全能力/跨平台验证pending |
| Q14 | NULL/Join/分页/collation/类型语义 | R22/R24 → D16 | 真实PG/SQLite差分与属性测试 | SQL正确性未验收 |
| Q15 | Kestrel或Rust server在何种负载有价值 | R26/R27/R17 → D18/D13 | 同协议/功能/硬件端到端对照 | 不预设Rust/Tokio |
| Q16 | server整体预算与graceful shutdown | R29/R12 → D18 | 逻辑预算+RSS实测、慢端/断流/长跑 | channel容量不证明总内存 |
| Q17 | gRPC/MCP、静态JSON注册与版本支持 | R28/R30 → D19 | 准确协议版本、AOT二进制端到端 | 只为选择的协议放行 |
| Q18 | GUI/GPU/mobile扩展边界 | R32/R33 → D21 | 官方约束与必要平台探针 | 不能阻塞无关win/linux基线 |
| Q19 | 正式接受门禁与图语义 | R15/R16/R34 → D31/D32 | 图反例测试、精确hash/版本/证据/独立review | 本轮只完成bootstrap检查 |
| Q20 | 外部库准确版本license与供应链 | R14/R34 → D10 | 固定LICENSE、依赖树、SBOM、来源审查 | 不改变现有仓库许可证 |
| Q21 | 最新工具链预览机制与稳定替代 | R01/R02 → D01 | C# union代码生成、Runtime Async状态和实测 | preview不成为必要依赖 |

## 结果声明的边界

工具链版本事实、源码局部行为和Python模型/图检查可以独立成立；它们不能取代以上产品验收。正式结论以证据和契约版本为单位逐步接受，不把“研究报告已写”计成“完整产品可发布”。

后续任务拆分或否定候选时保留历史ID、理由及replacement关系。新Engine沿同一接入规范加入独立任务，不要求所有已有领域同步重做。

## Scope of design answers and remaining verification

The Q11/Q13 questions “must every ordinary C# entity compile Rust?” and “must this be a full LINQ SQL Provider?” are answered **no for the dynamic profile** by R25 and ADR-0002. They no longer remain open language-feasibility questions. SeaORM's static-profile restrictions remain real but do not generalize to all native database access. Contracts still require independent acceptance.

Q01/Q09 now have the recovered and migrated Windows/Linux Interop NuGet consumer, RID-free ordinary build/run and explicit-RID Native AOT execution, in addition to the earlier Linux/SQLite query AOT and unchanged-native-hash evidence. Clean Rust-free consumer hosts, full product packaging and Database/Server C# AOT closure remain pending; do not replace these narrower gaps with the obsolete claim that there is no Windows or RID-free evidence. Q14 retains SQL differential, silent-no-op rejection and fallible binder gates. Q15's Server benefit choice remains open for both Kestrel and Rust: the managed comparator is mandatory research, not an already-selected product default. Q16 now has finite native Body/Bytes/permit executions as well as its prior model, not a verified full network, RSS or shutdown implementation. Q04/Q12's existing safety distinctions remain; new logical-admission and SQLite lost-COMMIT-ack probes refine them without accepting product contracts. See the [source-lifecycle checkpoint](source-lifecycle-followup.md). Continue through existing R07/R14/R17/R20/R21/R25/R27/R29, D04/D10/D11/D14–D18 and Plan's independent-review prompt, not a new graph.
