# 首次交付：独立审查、验证结果与边界

日期：2026-11-12。状态：**research-bootstrap / proposed**。本记录由整合者汇总；独立审查意见保留在各审查者自己的文件中。它记录本次启动包可以被审阅和分发的依据，不接受 NativeWeave 产品架构、ABI 或平台能力。

## 1. 本次实际交付

Design 包含需求章程、28条需求映射、源码目录、固定版本的初步研究、候选边界、21项 proposed 契约登记、验证义务、模板、有限模型及审查记录。Plan 包含34个Research任务、32个Documentation任务、48个Delivery候选任务，以及三张独立图和114份可独立使用的任务说明。

首次Draft PR发布后，任务说明统一修订至0.1.1，补齐未合并阶段的输入定位。契约版本仍为0.1.0-draft，所有研究/文档/产品状态及路线选择保持不变。

ArcForges Design/Plan仅作为格式和组织参考。本启动包的内容、依赖、研究义务及验收机制来自本次NativeWeave目标；没有将ArcForges技术选择或执行规则作为继承依据。

## 2. 实际独立审查

| 审查记录 | 作者关系与范围 | 当前处置 |
| --- | --- | --- |
| [toolchain-review.md](reviews/toolchain-review.md) | toolchain_verification审查root候选设计、证据政策和模型，并以合成夹具审查parallel_plan的三图/门禁；其自编工具链报告不算独立接受 | RV-TC-001～009已完成所述范围的修复与对应复查 |
| [domain-review.md](reviews/domain-review.md) | domain_research审查root候选领域边界及Plan的局部领域依赖；不将自己的领域报告当作独立接受 | DR-001～005文本歧义及DP-001～004局部计划依赖/启动入口已关闭；具体历史和复查hash保留 |

最终候选边界内容SHA256为`432fa9cb1863485e928b6a5dc5ecf3752afa5465cbf9b4c519b3247216122264`。toolchain审查快照先于最后的DR-003精确定义补充；domain审查已对该增量实际复核。旧审查快照没有被重写成新文件的审查记录。

主要整改包括：

- 区分Task结果、本地内存静默、连接协议可复用与远端事务效果；Unknown结果由独立恢复记录保留，未确认干净的连接丢弃。
- 原子幂等边界、typed查询多维验证，以及逻辑内存预算和RSS实测分别定义。
- managed callback普通异常与非法UCO签名fail-fast分别列出；native静默不代替managed取消注册排空。
- 规范、任务正文、依赖实现commit、证据和独立审查绑定实际内容；输出范围使用单向包含判断。
- 去掉移动/GUI整专题对桌面基础规范的伪依赖，去掉基础DB codec对完整ORM契约及HTTP诊断对可选协议的伪依赖。
- 已选择的native/协议包进入对应集成及发布的条件依赖，未选择的路线不阻塞纯C#路径。

## 3. 本次真实执行的验证

| 检查 | 实际结果 | 证据与限制 |
| --- | --- | --- |
| Plan图与门禁 | 114节点；0结构错误；无已发现依赖环、独占写范围冲突；Research ready 34、Documentation ready 32、Delivery ready 0；accepted contracts 0 | Plan:verification/graph-validation.json；整合者使用最终文件重新运行 |
| 作者错误注入 | 14项均达到预期；错误输入使ready集合为空 | Plan:verification/mutation-checks.json；整合者重新运行 |
| Schema | 两份Schema自检和三图Draft2020-12校验通过 | Plan:verification/schema-validation.json；parallel_plan实际执行记录 |
| 整合文件一致性 | 28条需求覆盖全部114个节点且无未知ID；22份JSON可解析；177个本地Markdown链接目标均存在 | 整合者对两个最终目录实际检查；不包含远端网页可用性或链接锚点验证 |
| 独立门禁反例 | 缺规范、错hash、旧review、自审、空身份、越界输出、任务正文改变及依赖变化等按预期拒绝 | [原始结构检查](reviews/evidence/nativeweave-independent-validator-review.json)、[最终复查](reviews/evidence/nativeweave-validator-final-followup.json) |
| 独立运行证据检查 | 修正日志格式夹具后的13组正负控制均符合预期 | [follow-up原始结果](reviews/evidence/nativeweave-independent-evidence-followup.json)；为合成数据，不是实际AOT运行 |
| 有限异步状态模型 | 负控制找到释放后访问；候选在159个探索状态内无所检查的违反，9个已回收状态 | [模型及作者结果](../../experiments/async-quiescence/README.md)、[独立复跑结果](reviews/evidence/async-quiescence-independent-review.json) |

门禁最初的独立25组夹具有一项正控制因旧日志数组格式被拒绝，原始结果为24/25；随后按当前stdout/stderr schema修正夹具，13组运行证据检查通过。保留原始失败和解释，不把所有历史执行写成全部通过。最终validator SHA256：`d4e393016bd75de523b78f2df9c989eb417dbc7bdd05ca9f23a1fbefb58888c9`。

有限模型的负控制探索226个状态，违反路径在首次违反后剪枝；这个数量不是未剪枝完整状态空间。候选无反例只限于单操作、单callback、顺序一致性及已声明原子性假设。它不证明活性、弱内存、多操作、真实GC/FFI、取消注册回调或产品实现。

## 4. 尚未执行与接受的事项

本环境未提供可调用的dotnet/rustc/cargo/clang，也没有Windows运行环境。本次没有C#/Rust编译、真实Native AOT发布或执行、数据库故障试验、服务器负载、性能比较与产品包发布。源码文件中的测试已读与实际测试已运行分别记录。初步研究不代表34个专题全部完成。

21项技术契约均为proposed。所有产品任务均为planned_candidate。本次审查允许继续研究、草拟文档和提出局部变更；正式接受仍需准确版本的证据和独立实质审查。

图校验器只验证结构、文件哈希和manifest关联。它不能认证作者身份，也不能凭自报manifest证明命令确实执行。正式证据必须结合可信CI、可取得的制品/原始日志或独立重放。

## 5. GitHub交付边界

Design和Plan分别使用`research/bootstrap-2026-11-12`分支及Draft PR承载本批内容。通过Git树以上游main为父提交保留现有LICENSE；仅增加本批文件。产品仓库不在本批写入范围内。主分支、仓库权限及保护规则不在本批修改范围。

后续worker使用自己的task分支和Draft PR；整合者处理共享图、registry及根索引。开始草稿与接受规范分别判断，不设置“所有研究结束”或“阶段A全部完成”这一普遍前置条件。最新远端提交与PR状态以实际GitHub记录为准。

整合者在首次Draft发布后发现：默认main尚未包含启动文件，自包含提示词需要明确输入入口。全部114份任务说明及README、任务索引、独立Review入口现已补充两文档仓库的研究分支和PR位置，要求开始时分别解析、记录完整commit SHA，核对graph revision与packet hash，再从各自快照创建任务分支。分支仅用于导航，不替代不可变证据；两仓库不被假定原子更新。同步更新全部任务revision、依赖版本和packet hash，并重新执行图与Schema检查。该限定补充的独立复查见domain-review中的DP-004，历史审查快照保留。

