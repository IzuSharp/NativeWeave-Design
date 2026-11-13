# 技术问题的设计结论与未来验证

2026-11-13。既有Q01–Q21保留；技术结论/研究接受与产品验证分开。最终正式接受以精确registry和独立审查记录为准，不能因产品尚未实现把已解决设计永久留为open。

| ID | 问题 | 当前设计/研究回答 | 未来产品义务 |
| --- | --- | --- | --- |
| Q01 | 工具链/平台 | Rust1.100/.NET11/C#15与双OS真实研究；D01选择明确初始profile | A14/A15完整产品与运行机器矩阵 |
| Q02 | ABI/句柄 | 固定C ABI/size-prefix协商；logical admission+physical lease；D02/D04 | A01/A02/A03完整布局/旧新版本/失效路径 |
| Q03 | 绑定唯一来源 | D03最小inventory；实际generator对照与silent omission负例 | A09–A12正式工具/导出漂移验证 |
| Q04 | callback退休 | D04–D06 native quiescence+managed queued/running双屏障 | A06/A07/A20完整竞争/weak-memory相关工具范围 |
| Q05 | async表面 | Task优先；take-once终态，ValueTask池化须成本及寿命证明 | A07/A21正式实现和实际收益 |
| Q06 | 共享runtime | 无需统一runtime；同步miniz与异步Hyper为异质证据 | A08/A17/A18局部能力与线程/RSS |
| Q07 | Buffer | D07 owner/extent/stride/borrow/pin/copy；真实溢出/GC研究 | A04/A20产品fuzz/retained allocation |
| Q08 | 错误fatal | D08精确ErrorRecord；Rust panic及无效UCO子进程事实 | A05 poison/失败注入与可恢复范围 |
| Q09 | 打包来源 | 真实双OS独立NuGet/RID-free/AOT，消费有效环境无Rust工具 | A16真正pristine no-Rust、发布签名和runtime-only机器 |
| Q10 | 两真实Engine | miniz_oxide同步codec与Tokio/Hyper异步network | A17/A18正式Core facade conformance |
| Q11 | 原生DB/ORM | 预编译SeaQuery+SQLx动态metadata；SeaORM有条件复用 | B01–B14完整产品API/闭包与双OS AOT |
| Q12 | 事务Unknown | 实际PG丢COMMIT响应/失败tx/迁移锁；SQLite深度正反例 | B05/B08/B21/B22 durable reconciliation/长负载 |
| Q13 | 自然强类型查询 | Fluent/static metadata/DTO，SG可选，无全LINQ/逐实体Cargo | B09–B14正式完整能力与编译负例 |
| Q14 | SQL语义 | D16 fallible native binder/后端拒绝/SQL3VL/shape严格区分 | B02/B03/B07/B11完整真实backend差分矩阵 |
| Q15 | Rust Server组合 | 必需Rust；Tokio/Hyper/Tower/Axum foreign service；Kestrel仅对照 | B17正式Host，A21/B23公平成本数据 |
| Q16 | Server预算/关闭 | D18 Body/Bytes/许可/两侧预算及退役；真实HTTP2/TLS和owner实验 | B16/B17/B20/B22完整C#桥与soak/RSS |
| Q17 | gRPC/MCP | D19 Rust Tonic/rmcp+静态C#DTO/Handler；明确公开API验证/超时缺口 | B18/B19实际AOT transport/消息/流/取消/协议互通 |
| Q18 | 未来平台 | R32/R33/D21真实源码和可用性，亲和性/device loss/静态链接边界 | A23目标设备/平台专项，不阻塞当前桌面 |
| Q19 | 正式接受 | R34/D31/D32精确来源/内容/依赖及真实独立审查；三图保留 | 未来产品阶段授权与实际产品接受 |
| Q20 | 供应链 | D10/R14准确crate/source/lock/license/provenance差异与更新策略 | A16/A22/B24最终闭包/签名/组织发布政策 |
| Q21 | 最新特性 | 稳定union/closed与preview内存安全区分；实际RuntimeAsync lowering/AOT | A21成本测量、A22后续版本升级 |

研究仍发现的新反例必须修复并重审当前精确输入，不能仅移动到未来义务掩盖设计错误。当前没有因Kestrel/Rust二选一、全LINQ或逐实体Rust编译而继续开放的反向架构问题。GPU/mobile的具体产品目标尚未纳入正式桌面发布，不伪称已运行所有设备。
