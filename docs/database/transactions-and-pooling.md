# 事务、连接池与不确定结果恢复

- Task：D15；契约：C-TX-001@0.3.0；作者：database_design / source-lifecycle continuation；2026-11-12。
- 历史输入packet：revision0.1.1，SHA-256 `cce4d00e3cc7983c2808cf7a5d47e4a08707885973c497ba5a929a78c5bd554c`，曾与当时Plan图匹配；当前修订输入与hash见 [database-completion](../../verification/database-completion/task-status.json)。
- 历史基线：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- 状态：**0.3.0 设计候选；registry记录精确内容独立审查与接受，产品实施/发布验收保留于Delivery**；接受状态以registry中相同内容hash及独立Review为准。契约代码样例仍design-draft、未编译；完整生产adapter与C# AOT验证尚未完成；历史有限Rust/SQLite回收实验见第12节，本次真实PostgreSQL响应丢失、协议恢复与迁移锁实验见第13节。
- 输入：[R19](../research/topics/R19/report.md)、[R20](../research/topics/R20/report.md)、[R21](../research/topics/R21/report.md)；与[驱动规范](drivers.md)共享WeaveDataSource/DataSession命名。

> 旧packet与Review仅为原版本历史溯源，不能接受本次新内容hash。

## 1. 设计决定

TX-D001：Rust事务协调器独占一个native Session及其SQLx物理连接lease；一次只允许一个命令/reader/COPY。事务对象不池化。业务保留的Outcome快照在Dispose后仍可读取，不因内部连接复用发生ABA。

TX-D002：分别维护**事务效果、应用操作结果、协议可复用状态、本地资源生命周期**。任何取消、Task终结、Dispose或native静默都不单独决定数据库是否提交。

TX-D003：`CommitAsync(admissionToken)`仅在提交发送前接受用户取消。进入CommitInFlight后，提交由独立commit期限驱动到确认或Unknown；不主动让请求断开token覆盖已经发生的效果。调用方可以停止等待，但清理责任仍由事务对象/Session持有。

TX-D004：默认不自动重试业务写入或整个事务。可证明未发送、明确已回滚、或有业务级原子幂等保护的操作，才进入显式retry策略。Unknown必须进入恢复分支。

这些决定解决Q12的研究设计问题；网络故障、真实调度、AOT和长期资源验证继续是B05/B22接受条件。

## 2. 源码证据与 Rust 适配边界

普通路径是预编译SeaQuery + SQLx Rust Engine；SQLx研究pin为v0.9.0 `75bc0487eb661da811bb7a3c5d158f1bd463fef4`。SeaORM固定源码保留为专用静态Entity profile证据，其trait/model编译耦合不是普通应用前置。

Rust SessionExecutor持有物理connection lease；B01声明共享driver/session接口，B04组合并持有host，B02/B03执行，B05协调事务/cleanup。SeaQuery构建SQL，fallible binder传播参数编码错误。借用transaction/stream局限在拥有连接的native async任务，不transmute越过生命周期。新增普通C#实体是runtime metadata；不跨动态库传SQLx pool/trait object/allocator owner。当前真实原生编译及有限PG/SQLite故障证据见第12/13节；正式产品跨语言并发门禁仍须执行。

SQLx PoolConnection::close保留池permit到关闭结束；close_on_drop只安排关闭，Drop可能spawn返池；返池执行after_release与ping并在失败时close_hard。PG TransactionManager通过命令与ReadyForQuery推进事务深度；commit调用后错误不证明未提交。SQLite worker将BEGIN成功但失去ack与COMMIT成功但失去ack区别处理；start_rollback/shutdown可同步等待bounded channel，不能进入SafeHandle ReleaseHandle或非阻塞control函数。详细固定文件/行段与真实reader身份在R20/R21 evidence。

Npgsql v10.0.3的受控延迟reset、坏连接剔除、取消请求不等于终态保留为**对照证据**，不是新产品依赖。PostgreSQL18 [协议流](https://www.postgresql.org/docs/18/protocol-flow.html)定义Sync/ReadyForQuery边界。所引用上游测试源码只读未执行；本次独立实验已取得第13节所列有限PG故障证据，不能替代生产adapter及完整AOT验证；PR5有限Linux/SQLite查询原型也不能替代这些验证。

## 3. 四个状态维度

| 维度 | 状态 | 说明 |
| --- | --- | --- |
| TxLifecycle | Active / Failed / CommitInFlight / RollbackInFlight / Closed | 是否允许继续在此事务操作 |
| TransactionOutcome | InProgress / Committed / RolledBack / Unknown | 对持久化效果的知识；只允许有证据的终态 |
| ConnectionDisposition | Usable / ProviderResetPending / Quarantined / Discarded | 下一应用操作是否得到干净协议与session语义 |
| LocalLifetime | Live / Closing / Quiescent / Reclaimed | 还可能访问本地对象、buffer或callback的义务 |

`ProviderResetPending`仅包含provider内部已知、被顺序化且在下一用户命令前处理的maintenance。它不允许未读取的任意用户结果、无法归属的协议字节、未确认错误恢复或未知并发写入。Npgsql允许延迟reset，因此不要求“每次返池时零待发字节”；要求的是provider保证新租借者不会观察前一使用者的事务/session状态。

Unknown是知识状态，不是需保活native内存的理由。资源静默后可释放本地句柄，另留managed/durable恢复标识。协议不可信的连接不能返池，即使native已静默。

## 4. 状态机和线性化点

| 输入/事件 | 前态 | 后态及结果 |
| --- | --- | --- |
| Begin成功 | Session无事务/无active operation | Active、InProgress；取得独占绑定 |
| 普通命令成功 | Active | Active；保留事务 |
| 使事务失效的命令错误 | Active | Failed；只允许Rollback或受支持的RollbackToSavepoint |
| Commit前token已取消 | Active | 保持Active；提交未被发起；抛取消；之后仍需rollback/Dispose |
| Commit入线 | Active | CAS到CommitInFlight；禁止新命令、第二次commit和并发rollback |
| 可信提交确认 | CommitInFlight | Closed、Committed |
| 可信回滚确认 | CommitInFlight或RollbackInFlight | Closed、RolledBack；保留失败原因 |
| 已可能发送后断线/期限到达且无可信终态 | CommitInFlight | Closed、Unknown；连接清理或丢弃；抛Unknown异常 |
| Rollback确认成功且从未commit | RollbackInFlight | Closed、RolledBack；本地仍按独立cleanup/retire屏障释放 |
| Rollback未确认、断线/期限到达，且从未进入CommitInFlight | RollbackInFlight | Closed、InProgress、CommitAttempted=false；Cleanup=RollbackUnconfirmed；禁止继续使用；连接隔离/丢弃 |
| Unknown之后尝试cleanup rollback或得到“无事务” | Closed、Unknown | Unknown保持；该响应不能证明此前COMMIT未发生；仅更新Cleanup/ConnectionDisposition |
| 独立deadline到达但native调用/SQLite worker仍运行 | 任一完成流程 | 应用gate关闭；LocalLifetime=Closing且Cleanup=Pending；保留连接、callback、buffer与预算，不报告安全清理成功 |
| Dispose | 任何Live态 | Closing；关闭准入，join已开始完成流程；不盲目把Unknown改成RolledBack |

`InProgress`表示尚无确认的数据库事务终结知识，并不保证本地仍可执行；必须和TxLifecycle一起读。RollbackUnconfirmed且CommitAttempted=false只说明本框架没有发起COMMIT，不能声称服务器rollback已经完成；非事务外部副作用也不由它保证撤销。以上判断以独占连接且事务内禁止SessionMutating专家SQL为前提。Begin部分成功但未取得确认同样隔离并保留cleanup，不先向应用发布Active。

提交入线是本地“可能已开始发送”的保守边界，不能声称等于服务器持久化点。仅能证明未调用provider commit/未交给native执行器时，才标提交未发送。若公共provider API不能报告精确发送位置，调用其commit方法以后发生的传输/超时错误按Unknown分类。

已知Failed事务不允许Commit：PostgreSQL失败事务的结束不能被误报成成功提交。适配器必须保持statement错误/保存点恢复状态；不能只看一个无异常的Task就忽略先前失败。需要B05用真实失败事务/延迟约束验证分类。

## 5. 公共API和异常路径

以下代码为**design-draft，未编译**。接口的严格语义由本节定义。

```csharp
public enum TransactionOutcome { InProgress, Committed, RolledBack, Unknown }
public sealed record TransactionOptions(
    IsolationLevel? Isolation = null,
    string? RecoveryKey = null);

await using DataSession session = await source.OpenSessionAsync(requestToken);
await using DataTransaction tx = await session.BeginTransactionAsync(
    new TransactionOptions(RecoveryKey: operationId), requestToken);
try
{
    await WorkCommands.UpdateAsync(session, change, requestToken);
    await tx.CommitAsync(requestToken); // token只控制提交入线前的准入。
}
catch (CommitOutcomeUnknownException ex)
{
    await recovery.RecordUncertainAsync(ex.RecoveryKey, ex.CorrelationId);
    // 根据同一幂等键/operation_id查询；不将这次失败当作没有写入。
}
```

`CommitOutcomeUnknownException`包含Outcome=Unknown、可选RecoveryKey、ProviderCode与CorrelationId；不包含连接密码、SQL参数或原始敏感payload。`DataTransaction.Outcome`、`CommitAttempted`和`Cleanup`在Dispose后可读取；成功CommitAsync只代表Committed。明确的事务回滚/失败以相应DataException返回；未知不得降级为普通OperationCanceledException。

Commit、Rollback及cleanup使用可配置但有限的独立期限，不继承已经取消的request token。默认commit期限30秒、cleanup期限5秒，供初始实现/反例使用；这些是操作策略，不构成数据库完成时间保证。具体provider无法中断同步调用时，必须记录deadline exceeded但仍保有worker/资源义务，不能伪造已终止。等待方超时与执行方停止分别观察。

`DisposeAsync`关闭应用准入；若Active则请求rollback，若已有commit则join它。业务失败和cleanup失败分别锁存：显式RollbackAsync失败抛DataCleanupException；自动Dispose不以cleanup异常覆盖已经报告的主错。`tx.Cleanup`是不可变快照，字段为Status（NotStarted/Pending/Succeeded/RollbackUnconfirmed/Failed）、CorrelationId、ProviderCode、LocalResourcesReleased、ConnectionDisposition、DeadlineExceeded；不包含敏感参数。诊断事件与该snapshot相同关联ID。

DisposeAsync的成功返回必须满足LocalResourcesReleased=true；这只表示本地安全，不保证Outcome=RolledBack。若deadline到达仍有native访问者，**DisposeAsync仍join且不提前成功**，Engine保留清理责任、roots及预算。需要有限等待的显式`CloseAsync(deadline)`返回CleanupResult snapshot（Status=Pending、ConnectionDisposition=Quarantined、LocalResourcesReleased=false），调用者据此决定停止等待；该结果不伪装成已Disposed。后续DisposeAsync/join等待同一清理任务，不重新rollback。普通rollback/close错误记Cleanup，不从await using清理路径覆盖已经报告的CommitUnknown/业务错误；显式RollbackAsync仍报告自己的错误。若希望有界关闭，使用CloseAsync的明确控制流，不再用await using期待有限时间保证。

DataSession/DataSource也有同语义CloseAsync(deadline)，由Engine cleanup owner保留session及其父lease并join既有tx/cursor；有限HTTP响应路径不再额外await using强制等待。该API不开始新业务、不提前归还仍在用的准入/连接预算。

同步Dispose只请求关闭并转交已注册cleanup owner，不阻塞finalizer、不承诺已排空；需要确认本地安全时使用DisposeAsync。Closed TxLifecycle可以与LocalLifetime=Closing和Cleanup=Pending同时存在；“应用禁止继续使用”不是“内存已经可释放”。

SQLx/SeaORM对象的析构只在允许阻塞或等待runtime的受控executor路径发生。finalizer和ReleaseHandle仅设置关闭/转移到有预算的retirement队列，不能执行SQLite start_rollback/shutdown同步send。不能在runtime销毁后安排依赖它的cleanup。

## 6. 连接归还、隔离与丢弃

归还必要条件：无活动SeaORM/SQLx stream/COPY/发送Future；无在途访问该连接的取消/handler；事务已结束或SQLx受控rollback维护可在下一命令前完成；session状态恢复；没有未知协议/并发损坏。应用operation terminal、native retire、可返池分别记录。

Rust SessionExecutor保有PoolConnection直到判断明确。正常路径允许SQLx自己的after_release/ping和顺序化rollback；禁止自己复制Npgsql的DISCARD ALL协议或假定两者reset行为完全相同。可选择profile只允许固定会话设置，应用不能任意修改；每次租借验证/重置受支持设置。若不得不清理未知或未支持状态，调用公开`PoolConnection::close()`并join，不返池。

`close_on_drop`是剔除意图，不能单独记LocalResourcesReleased=true；Drop安排的工作仍在Engine cleanup ledger内。禁止用detach提前放开permit同时把仍存活connection/SQLite线程排除预算。返回池后的内部SQLx maintenance由pool拥有，DataSource关闭要join pool关闭和本Engine所有清理；不能先销毁runtime，D02 v1模块不卸载。跨ABI owner是否retire不由SQLx私有字段猜测。

Unknown远端effect本身不强制丢弃已证明协议/事务干净的连接；丢弃依据是协议与session状态。相反，Task成功或本地静默也不能放行脏连接。SQLite statement reset()被忽略的错误不证明复用安全；不能证明transaction/statement结束则close并join worker，期限不能强行free。

## 7. 保存点、隔离与session状态

默认拒绝嵌套BeginTransaction，显式提供Savepoint/Release/RollbackTo。只有选用SeaORM集成profile时，才需处理其TransactionTrait的关联Transaction实现固定点约束；该profile的nested begin在v1返回明确UnsupportedNestedTransaction错误，不能因trait要求存在该方法就隐式启动第二顶层事务。普通SeaQuery+SQLx路径不要求实现SeaORM trait。需要的保存点由NW显式API映射SQLx同连接保存点机制，维护栈及generation，拒绝乱序释放/rollback。保存点名称由框架生成安全标识，不把用户字符串直接拼接；作用域对象绑定当前事务generation。RollbackTo成功后是否回到Active取决于provider的真实语义。Dispose保存点不提交外层事务。

PostgreSQL按请求传递ReadCommitted/RepeatableRead/Serializable能力；serialization failure/deadlock可提示“整事务可重试”，但不自动重放业务委托。SQLite的普通Serializable及BEGIN IMMEDIATE/DEFERRED选项分别表达，不能把SQLite模拟成具有PostgreSQL完整隔离矩阵；ReadUncommitted仅在明确profile中支持且标出共享缓存等前置条件。

`TransactionOptions.Isolation=null`表示使用provider profile中公布的默认值：PostgreSQL为ReadCommitted；SQLite为其普通Serializable语义，BEGIN模式由SQLite profile显式选DEFERRED/IMMEDIATE。显式请求不支持的隔离级别须在开始前拒绝，不能静默降级。这样只传RecoveryKey的跨provider应用不会无意要求SQLite实现PostgreSQL ReadCommitted。

禁止普通生成命令自行执行BEGIN/COMMIT/ROLLBACK或修改事务所有权。专家SQL入口需显式标记SessionMutating；在框架拥有的Active事务内拒绝该类别及未经审查的多语句/事务控制SQL，不提供任意SQL完全静态审计保证。非事务使用会降低可复用保证并默认在归还时丢弃连接。没有能绕过operation lease的公开SQLx connection escape hatch。

## 8. 原子幂等与Unknown恢复

框架提供RecoveryKey传播和Unknown结果，不替业务规定幂等身份。参考应用应采用以下可实现协议：

1. 在同一事务中尝试插入唯一`(scope,key)`记录，包含request_hash、operation_id和状态；scope包含租户/主体/操作种类。
2. 冲突时读取既有记录并比较request_hash。相同key不同请求返回冲突；不能重放旧结果给不同请求。
3. 执行业务写入，并在同一事务记录规范化结果和outbox事件；提交成功后才能对外宣称完成。
4. COMMIT结果Unknown时，通过operation_id或同key恢复查询。一次“未找到”不能证明旧事务永远不会提交，尤其在旧执行尚未结束、读取replica或读快照时。
5. 同key重试通过唯一约束和同事务协议与旧事务序列化；不在事务外做“先查不存在再写”。清理幂等记录的保留期必须覆盖客户端重试窗口，超期键不再承诺同样的防重语义。

外部邮件、对象存储或其他不可同事务副作用使用outbox和独立幂等消费者；不能宣称数据库事务使外部系统exactly-once。恢复读取应使用满足一致性要求的主库/明确确认点。详细HTTP和参考服务接口由D20定义。

PostgreSQL18的具体分支：在ReadCommitted事务执行 `INSERT ... ON CONFLICT(scope,key) DO NOTHING RETURNING operation_id`；返回0行后，执行**下一条独立SELECT语句**读取同scope/key并核对hash。不能把一个CTE中的INSERT DO NOTHING + SELECT组合宣称为必定读到冲突记录：冲突事务的结果可能尚不可见于同statement的snapshot。官方[隔离规则 §13.2.1](https://www.postgresql.org/docs/18/transaction-iso.html)及[INSERT RETURNING](https://www.postgresql.org/docs/18/sql-insert.html)分别说明此可见性和仅返回实际insert/update行。若下一条读取仍无行（清理、过期、超时等），进入有界恢复/重试流程，不推断旧事务rollback；保留期内禁止提前物理删除，使用明确retention/tombstone策略。SQLite同key原子协议需B03/B21在目标journal/locking配置下验证，不从PostgreSQL语法类推其并发行为。

## 9. 安全不变量

- `active_protocol_operations(session) <= 1`；关闭准入后不能取得新操作lease。
- 一个事务最多发布一个已确认终态；Unknown只能被后续有身份绑定的恢复证据细化，不能被本地Dispose覆盖。
- 每个返池连接满足provider定义的隔离复用协议；未知损坏状态不能以“稍后可能reset”放行。
- 取消注册、reader和provider发送任务离开前，连接仍由该操作所有；数据源关闭不转移这些责任给已销毁runtime。
- committed business write与幂等结果/outbox具有相同事务原子性边界；失败分类不把“可重试异常”当作“业务没有执行”。

这些是实施验收义务。状态表与源码分析支撑设计决定，尚不证明真实调度器满足它们。

## 10. 成本与AOT

Rust复用SQLx物理池；增加native Session对象、操作gate/lease、失败上下文和有界cleanup ledger。C#只有native handle包装及Outcome/Cleanup快照，不维护第二份ORM事务模型或物理池。事务对象不池化，避免disposed对象复用及恢复标识ABA。

Engine-local执行器拥有SQLx futures和SQLite线程清理责任；这不强制其他Native Engine共享Tokio。关闭时先停止新准入、停止stream/事务、清理连接、排空callbacks/control，最后关闭pool/runtime实例。D02 v1的native module保持加载至进程退出，不热卸载。计入commit in-flight、quarantined connections、rollback pending和等待者的预算；不能用后台清理无限扩大容量。

C# Outcome/异常及恢复DTO静态定义，serializer使用明确metadata；PG/SQLite provider均在Rust native资产。B23对比同一固定原生候选栈的纯Rust调用与C#→ABI调用：普通候选是SeaQuery+SQLx，SeaORM动态或静态profile另行对照，不强制普通路径经过SeaORM。managed驱动作为独立benchmark对照；不把“Rust必须”作为无证据性能优越声明。

## 11. Verification / Delivery义务

| ID / owner | 场景 | 可观察接受条件 |
| --- | --- | --- |
| TX-V01 / B05 | Commit前取消、提交中request断开、提交应答丢失 | 未发与Unknown区别准确；不自动重试；恢复可识别已提交业务 |
| TX-V02 / B05,B22 | rollback未确认、断连、native清理超时 | 从未commit→Closed/InProgress/CommitAttempted=false/回滚未确认；此前Unknown保持Unknown；连接不可借出；仍在运行则LocalResourcesReleased=false且budget不归零；primary error与Cleanup分别可查 |
| TX-V03 / B05 | failed事务Commit、savepoint恢复、重复终结 | 不误报提交；非法转换稳定拒绝 |
| TX-V04 / B02,B03 | Pool耗尽/取消、reset失败、会话设置残留 | 准入名额恢复；下个租借者状态隔离；包含SQLx受控pending rollback与未知协议损坏的不同路径 |
| TX-V05 / B21,B22 | 并发同key同/异payload、COMMIT返回丢失、过期记录 | 单业务效果或明确冲突；记录/结果/outbox一致；未找到不伪证回滚 |
| TX-V06 / B05,B22 | start/commit/Dispose/Cancel交错模型及真实压力 | 终态唯一、无双重归还/死锁、资源计数恢复 |

实库故障通过可控proxy切断COMMIT响应方向、server终止会话、事务内约束/死锁等方式注入；必须记录故障发生点、服务器观察和客户端分类。分别用win-x64/linux-x64 Native AOT二进制执行；Python或模型结果不能替代。长期资源指标包括未清理Session、等待者、物理连接、worker、buffer和Unknown恢复积压。

## 12. 新增的有限SQLite回收与取消证据

[R20/R21/R25续接研究](sqlx-retirement-study.md)及[真实研究fixture](../../experiments/database-retirement/README.md)使用固定SQLx0.9、SeaQuery1.0.2、Tokio1.54.1与Rust1.100。六项本地Linux测试已执行：事务Drop后同物理连接复用、提前停止stream、取消acquire不丢permit、COMMIT已dispatch但ack未交付时drop Future、progress handler状态隔离，以及Pool关闭等待借出owner。各次成功/失败输入和原始日志独立保存，Windows/CI以其实际运行记录另记。

其中COMMIT测试在SQLite原生commit hook中进行受控暂停，丢弃应用等待Future后再放行，最终观察到已提交行。这个反例支持TX-D002/TX-D003：停止等待不能报告RolledBack；未知提交效果和本地清理继续分别记录。故障注入hook刻意阻塞，仅用于研究，不能复制到生产callback/finalizer。

独立读取的六个SQLx源码文件与实际编译的registry文件逐字一致；包的VCS声明与历史研究Git pin不同，所以不声明整个包等同。SQLx worker Shutdown响应发生在其连接引用释放之后、线程闭包返回之前；该响应和Pool.size归零不等于取得OS JoinHandle。D02初始module常驻约束继续有效。上述有限Rust证据不接受生产adapter、PostgreSQL响应丢失、跨语言retirement或完整AOT契约。

## 13. PostgreSQL response loss, protocol recovery and migration ownership

The database-completion research fixture adds explicit PostgreSQL18.0 probes with a
source/lock/OS/server identity manifest. Its COMMIT-loss proxy forwards the request,
consumes server COMMIT and idle ReadyForQuery, discards those replies to the client,
and checks durable state through another connection. A client error with a committed
row is the concrete oracle for Unknown; it does not implement the future C# exception.
The timeout case observes 57014, then 25P02 before rollback, then same-backend recovery.
The stream case drops consumption and verifies cleanup before the next query.

Migration lifetime is an administrative instance of the same rule. SQLx's PG
Migrator acquires a session advisory lock, checks ledger/checksums and unlocks on its
success path. Some errors return before unlock. A pooled application's connection
must never inherit this state. Use a dedicated migration connection, close it after
error/cancellation and preserve its cleanup owner until closure. A close failure
leaves the admin operation quarantined with resources counted; it is not proof of
remote lock release. The research negative control queries pg_locks after checksum
mismatch and after closing the dedicated connection. SQLite migration lock/unlock
are no-ops; the documented SQLite administrative profile owns write serialization
and rejects unsupported nontransactional migration inside its atomic batch.

SQLite 的原子迁移批次必须经 SQLx 公开 `Connection::begin_with("BEGIN IMMEDIATE")` 创建受跟踪的 `Transaction`，再调用 `Migrator::run(&mut *tx)`。先用 `migrator.iter().any(|m| m.no_tx)` 拒绝不支持的非事务条目，再准入并取得 writer lock。成功后仅 `tx.commit().await` 结束外层批次；迁移错误时显式 `tx.rollback().await`，回滚失败则隔离并关闭专用连接。不能先 `query("BEGIN IMMEDIATE").execute(&mut conn)`：原始 SQL 不更新 SQLx transaction depth，Migrator 内部再次 BEGIN 会失败。

```rust
// Illustrative public SQLx 0.9.0 chain; domain error/cleanup mapping remains B08.
use sqlx::Connection;
if migrator.iter().any(|m| m.no_tx) {
    return Err(UnsupportedNonTransactionalMigration);
}
let mut tx = conn.begin_with("BEGIN IMMEDIATE").await?;
match migrator.run(&mut *tx).await {
    Ok(()) => tx.commit().await?,
    Err(error) => {
        // If rollback fails, retain both errors and retire this dedicated connection.
        let rollback = tx.rollback().await;
        return Err(map_migration_failure(error, rollback));
    }
}
```

独立审查者实际运行了原始 BEGIN 反例、受跟踪外层 rollback/commit，以及第二条迁移失败后整批 rollback 三项 Linux Rust 回归；schema 与迁移 ledger 同时撤销，内层保存点不提交外层事务。见 [independent three-case regression](../../verification/interop-completion/db-review-migration/result.json)。这证明公开调用链和有限原子性，不代替 B08 的跨进程竞争、Windows、崩溃/重启和产品 AOT 验证；示例错误名和 map_migration_failure 仅说明领域映射，不是已发布 API；该映射必须保留原始迁移错误及回滚错误，并要求隔离/关闭尚未安全清理的连接。


These facts refine B05/B08/B22: distinct outcome/cleanup observables, zero advisory
locks after successful retirement, no pool reentry after unknown admin state, and
explicit finite deadlines that never free still-used native owners.

### Published research CI evidence

The [database CI confirmation](../../verification/database-completion/ci-confirmation.json) binds source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` and run `43388468172` to actual Windows/Linux metadata/SQLite results (5/5 on each) and Linux PostgreSQL 18.0 results (6/6). Archived inputs/logs were checked byte-for-byte; Windows CRLF inputs remain separately identified. This confirms the finite native research oracles and leaves the specified C# product, TLS, concurrency, long-load and independent design-review obligations distinct.
