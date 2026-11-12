# Rust ORM 语义、关系与查询请求规范

- Task：D16；设计规范：**C-QUERY-001@0.1.0**；作者：database_design；2026-11-12。
- 状态：**review-ready**；接受状态以 registry 中相同内容hash及独立Review为准。代码样例仍design-draft、未编译；无Rust ORM/C#/PostgreSQL/Native AOT运行证据。
- 输入packet：revision0.1.1，SHA-256 `e7c09be39a8817ba183ff525c7e526eee2879924b52af251de4f5ee253d2c8b6`；基线Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`、Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- 输入：[R22](../research/topics/R22/report.md)、[R24](../research/topics/R24/report.md)、[R25](../research/topics/R25/report.md)。相邻权威：[D14 Rust Engine](drivers.md)、[D15事务](transactions-and-pooling.md)、[D17 C#捕获/双侧生成](../generators/query-generation.md)。

## 1. 明确选择与权威边界

**QUERY-D004：选定 SeaORM2.0.4 作为 Rust ORM。** 实体、ActiveModel部分更新、关系、查询表达、SQL生成、数据库行映射、工作单元和数据库执行都在Rust。C#只有最上层声明语法、请求编码、自然Task/泛型API和边界DTO解码。C#不会维护SQL方言、关系optimizer、数据库identity map或ORM事务实现。旧QUERY-D001的C# IR/SQL核心、QUERY-D002的自有C# ORM/TrackedUnitOfWork因需求修正而superseded；旧源码证据与有限SQL实验仍保留。

**QUERY-D005：采用生成的schema-specific SeaORM模型与静态dispatcher，不宣称万能无schema引擎。** C# declaration→带类型请求/schema manifest→Rust工具生成SeaORM Entity/Column/ActiveModel/Relation及projection→同一模型native module。静态查询的已登记ID进入生成handler；动态条件只能在该模型已登记实体/字段/关系/投影上变化。新增schema/静态query需要native重编译，可由SDK/CI完成，普通应用不写Rust。

**QUERY-D006：Rust执行受限查询请求的含义校验与规范化，然后构造SeaORM Select/Entity mutation/Relation；SQL方言交SeaORM/SeaQuery，值经SqlxValues绑定。** NativeWeave只补两值C#语义、能力/预算和业务约束所需的小层，不重写整个ORM。ORM与原生driver选择已决定，不要求用户逐项选库；正确性、性能和发布验收仍在B任务。

| 候选 | 已证实的机制 | 本次决定 |
| --- | --- | --- |
| SeaORM2.0.4 | 静态Entity/ActiveModel/Relation + runtime Condition；async PG/SQLite SQLx；可生成模型 | 选择。适合声明捕获后生成模型，并允许受限动态条件 |
| Diesel2.3.14 | 静态类型查询；dynamic-schema和boxed query确实存在，动态schema失去部分schema/type检查；boxed仍有ST/QS/DB/GB边界 | 合理替代，但本次跨语言动态条件/异步组合选择SeaORM；不声称性能较差，不声称没有动态schema或不能异步 |
| SQLx单独 / SeaQuery单独 | 前者驱动与查询，后者SQL构建器 | 不满足本次“Rust提供合适ORM”的选型要求，作为SeaORM下层 |
| EF/Npgsql/DapperAOT | C# provider、ORM或mapper参考机制 | 研究/benchmark，不是产品默认依赖或fallback |

普通ORM能力必须真实参与：例如生成`work_item::Entity::find().filter(condition)`、`.into_model::<WorkProjection>()`、ActiveModel insert、Entity update_many与RelationDef join。只传C# SQL到`query_raw`然后声称“已集成ORM”不满足B11/B14验收。专家SQL可作为显式补充，不替代常规路径。

## 2. 实际源码、测试与限制

SeaORM `db40a19a7bde7be8e1c4b346b1b70d72e87f0245`：`base_entity.rs` 65–135定义静态关联类型；`active_model.rs` 15–53定义Set/Unchanged/NotSet及try_set；225–235/347–402/448–457连接ActiveModel→Entity executor→结果。`executor/update.rs` 1–205显示rows_affected、RecordNotUpdated及RETURNING分支，不能从普通主键更新推导自动乐观并发。`relation.rs` 1–145定义关系key/方向/多对多via，311–317支持ON条件；`query/helper.rs` 625–810包含runtime Condition和排序。`executor/select.rs` 266–324/869–925显示projection/stream的真实FromQueryResult调用。

`tests/transaction_tests.rs` 142–169/206–235/272–300/994–1027包含scope Drop、commit/rollback及SQLite IMMEDIATE；`tests/relational_tests.rs`实际所读区段包含ActiveModel插入与关联操作；`tests/transaction_tests.rs`373–455的after_save失败仍看到事务内row，然后scope回滚，支撑hook失败与写入effect分离。**测试存在和阅读不是运行结果。** R25 evidence记固定blob/行段；Diesel比较由root独立源码handoff引用，不冒称本作者完整读其实现。

EF Core `9e685c7a52d1a344d133a3d370e458db97417b3f` 的SqlNullabilityProcessor 1875–2015和nullable negation测试提供语义反例；它们不提供Rust translator验证。SeaQuery1.0.2 `f2d5e04d30919c342da1f8845ff1fde46e3308fc` prepare.rs/QueryStatementBuilder分离SQL与Values；SQLite SEARCH/CYCLE实现为空的已读反例说明NativeWeave必须先拒绝不支持的capability，不能依赖backend静默降级。

本轮 [R24 SQLite参考实验](../research/topics/R24/sqlite_semantics_probe.py)实际运行Python3.12.14/SQLite3.53.1/Linux x86_64，50checks、0failures，涉及nullable NOT、LEFT JOIN、bound参数、keyset、decimalTEXT和整数溢出。它**不是**SeaORM、SQLx、NativeWeave、C#、PostgreSQL或AOT运行证据。源码、参考模型、实际产品和生产验收分开记录。

## 3. 请求 IR、实体 schema 与 Rust lowering

协议名`orm-request/1`是跨边界声明请求，不是C# ORM runtime。节点有限：Scan、Filter、Project、Join、GroupAggregate、Distinct、Sort、Limit、Offset、UnionAll；标量为Parameter、Constant、Column、RegisteredCall、Case、Compare、Boolean。每节点具opcode、result_type_id、nullability、truth_kind、child索引、entity/column/relationship引用和有界typed payload。没有自由SQL字符串节点；专家SQL是不同capability/载荷。

B09发布schema与Rust validator/语义规范化；B10 C#工具只按准确Roslyn symbol捕获语法、类型与位置并序列化该请求。**最终含义与capability判定由Rust执行**：相同Rust validator用于构建期诊断和运行期动态请求；C#可提前检查类型/预算，但不是第二权威实现。节点顺序为拓扑序，child索引只能指向已存在节点，禁止循环、非法/未知opcode、复用不兼容type/codec、越界entity/column/relationship、超预算和开放投影。

Rust schema包含每实体数据库表、列logical/storage codec、nullability、key/tenant/concurrency token、FK/关系及允许函数。C#声明给逻辑类型和属性；Rust工具决定数据库type/方言约束并生成SeaORM代码，不在C#藏一套SQL type mapper。schema_hash覆盖上述定义；model_build_hash另覆盖query/projection、ORM/driver/codegen版本、Cargo.lock/features与目标，不以字符串表名建立信任。

静态handler通过query ID匹配到闭合Rust Entity/Projection；动态条件按column ID匹配到生成Column enum，组合Condition并调用相同Entity查询；Join只允许已登记关系或已声明静态join shape。任意动态组合不能发明未知Rust泛型类型，动态结果必须选择预生成projection ID。Rust验证原始请求和最终SeaQuery Statement的参数数量/SQLbytes，拒绝或有证明地使用provider bulk参数，绝不靠C#先验计数跳过最终预算检查。

PG/SQLite能力profile声明SQL版本、codec、参数/文本上限、collation和受支持操作。缺capability构建时报具体源码span，动态运行时在发送前失败。固定静态query仍需运行时schema/profilehash核对和输入budget检查；不能因“生成过”接受旧schema的新数据含义。

## 4. NULL 与布尔协议

默认静态 LINQ 使用 C# 谓词，进入 Rust request validator 后先转成完整的 two-valued predicate，再由 Rust SeaORM/SeaQuery lowerer 优化。如下表的 `x` / `y` 可以 nullable；`T/F/U` 为 SQL TRUE/FALSE/UNKNOWN。

| 用户语义 | PostgreSQL 规范形式 | SQLite 规范形式 | null 情况 |
| --- | --- | --- | --- |
| C# `x == y` | `x IS NOT DISTINCT FROM y` | `x IS y` | 两 null 为 true；仅一 null 为 false |
| C# `x != y` | `x IS DISTINCT FROM y` | `x IS NOT y` | 两 null 为 false；仅一 null 为 true |
| C# `x > y`（其余顺序比较同理） | `COALESCE(x > y, FALSE)` | `COALESCE(x > y, 0)` | 任一 null 为 false |
| C# `!(x > y)` | `NOT COALESCE(x > y, FALSE)` | `NOT COALESCE(x > y, 0)` | 任一 null 为 true；不能化简为 `x <= y` |
| 显式 SQL 相等 | `x = y` | `x = y` | 任一 null 为 UNKNOWN |

只有 codec 已声明该 equality 等价时才能用表中的 provider 运算符；例如字符串仍受选定 collation 约束，浮点 NaN、SQLite mixed storage classes 不自动获得 C# `==` 保证。portable numeric 比较的初始域为已验证的同 codec 有限值；NaN/Infinity 比较要显式 provider profile，否则诊断。

SQL 三值逻辑保留 `NOT U=U`、`F AND U=F`、`T AND U=U`、`T OR U=T`、`F OR U=U`；`WHERE` 只保留 T。`Sql.Equal(a,b)` 等显式 SQL 节点返回 `SqlTruth`，进入普通 C# Filter 必须用 `.IsTrue()`，不能隐式转 `bool`。nullable bool 列需 `x.Flag == true` 或明确 `.IsTrue()`，避免把 null/false 混为业务同义。

所有 normalization rule 要附前置条件并由 B09/B11 测试 null 输入、投影、NOT 与 AND/OR 嵌套。禁止以 “WHERE 丢弃 UNKNOWN” 为由使用仅对过滤成立的 rewrite，再在别处当成总是 two-valued 的表达式。

## 5. Contains、范围与数值

C# `values.Contains(column)` 的有限集合语义：空集合为 false；集合中 null 匹配 null；重复值不改变结果。规范 lowering 是平衡树形的 null-safe equality OR，取反对规范化布尔求 NOT。provider 可以选择参数数组/IN 优化，但需证明与此规范等价，不能直接用含 NULL 的 `NOT IN`。集合在命令入口快照；默认上限900元素/总参数900，超限拒绝或进入明确声明的 provider bulk-parameter capability，不临时拼接字面量。

只在 codec 域内做参数类型转换；读取/绑定整数窄化必须 checked。SQLite 超过 int64 的整数算术可转 REAL，本轮反例已执行；因此默认 portable profile 不把不受约束的 `long + long`、decimal 算术或溢出后的结果声明为 C# checked 等价。可接受静态/模型范围证明后的算术，或要求用户选择 `Sql` provider 运算和失败规则。除零、取整、modulo、NaN、舍入必须各自声明，不能把 SQL 名称相同当成语言等价。

PostgreSQL decimal 使用显式 numeric(p,s) 与溢出/舍入策略。SQLite decimal TEXT codec 仅保证规范化精确往返，**拒绝**直接数值排序、范围比较、SUM/AVG；portable money 使用 checked、固定 scale 的 int64，schema 写入也必须保持相同 scale。String 的 culture、case-folding、Unicode normalization 均不自动加入查询。

## 6. 排序、字符串与分页

所有字符串比较/排序在 schema 上选择 provider collation 或受限 portable profile。初始跨库 portable profile 只保证 ASCII 范围的 binary 比较；不能把 UTF-8 binary 排序宣称为任意 .NET UTF-16 ordinal 顺序。完整 Unicode/culture profile 需要 B11 的实际目标引擎结果及版本固定。`Contains` / `StartsWith` / `EndsWith` 需 Rust lowerer 正确参数化并转义 `%` / `_` / escape 字符，且有声明的 collation/case 语义；未配置则编译诊断，不做客户端过滤。

Sort 每键携带方向、NULLS FIRST/LAST 与 collation；不得依赖 provider 默认 NULL 次序。Take/Skip 要求明确顺序，分页必须带唯一、稳定 tie-break key；否则 NWQ0009。默认业务例子使用 `(CreatedAt, Id)` keyset，下一页按相同方向及 null order 构造词典式谓词并绑定上页最后键。cursor 绑定 query ID、schema/profile、排序和值编码；服务层若向客户端公开，必须防篡改并限制租户作用域。cursor 不能用于绕过 tenant predicate。

offset 分页保留但受明确 max offset/limit 限制；keyset 避免大 offset 扫描并不提供并发修改中的快照保证。需要跨页一致结果时使用显式 snapshot/物化 ID 清单或产品定义的 as-of token；不在多次独立 ReadCommitted 请求间承诺不漏/不重。

## 7. Join、分组与集合

INNER JOIN、LEFT JOIN 与投影是初始支持范围。Filter 位置是 IR 语义：LEFT JOIN 右侧条件在 ON 内和在 WHERE 内并不等价，optimizer 不可任意移动。右侧输出 nullable；使用 non-null primary key / 显式 match marker 区分 “没有匹配行” 与 “匹配行的值恰为 NULL”。无可用 marker 的复杂 projection 要生成存在标识列或报诊断。

GroupBy 初始只允许键与 Count/Sum/Min/Max/Average 等声明聚合，不返回可枚举的整组对象。`Count` 规范返回 long；显式 Int32 Count 要 checked。C# Sum 的空集零值与 SQL SUM 的 null 必须使用不同 IR 语义，前者生成相应 COALESCE；Min/Max/Average 的空集行为由可空/非空结果签名决定，非空空集抛 `EmptyAggregateException`。整数累加溢出边界见第5节，不将强制零值误称为完整数值等价。

Distinct 根据整条投影及 codec/collation；不能隐含忽略某列。UnionAll 支持形状兼容的结果；Union、Except、Intersect 需 provider capability + null/duplicate 语义明确后启用，不作为任意 IEnumerable 操作fallback。窗口函数、递归CTE、provider JSON 操作走已登记扩展或专家 SQL，未支持时拒绝，不静默省略。

## 8. Rust ORM 实体、变更、关系与并发

普通查询在Rust由SeaORM把DB row转为生成Model/Projection，再编码有界owned batch；C#只从wire字段构造可访问的record/class。NULL/精度/范围与shape均校验，不使用runtime反射setter。LEFT JOIN missing marker参与Rustprojection，不产生一个所有成员default的伪实体；C# DTO构造失败仍须finally释放batch/关闭cursor。

生成mutation保留三种字段状态：Absent→ActiveValue::NotSet（不写该列）、ExplicitNull→Set(None)、Value→Set(value)。Original/Unchanged用于显式工作单元；不得将null和未提供混同。外来输入先按Rustschema验证并用`try_set`或生成typed field构造；不调用会因type mismatch panic的`set`。v1生成ActiveModelBehavior使用无副作用默认hook，不接收C#回调或任意应用Rust hook；框架受控验证在DB写入之前完成。SeaORM的after_save在写入之后运行，返回Err不证明没有写入；若后续允许受控after-save，必须保留effect并在拥有事务内处理，禁止自动重试。关系多条写入/changeset始终显式事务，单语句autocommit成功后wire/DTO错误仍保留已确认effect；响应丢失可能Unknown。关系Replace/Clear/Delete是明确命令及授权的cascade策略，不能把C#集合缺项或null自动推断成删除旧行。公共方法明确Insert/Update/Delete/Upsert；SeaORM `save`只是按主键NotSet选择insert/update，不能当存在性UPSERT。

以下为**未编译的设计片段**，展示真实SeaORM组合方向；`validate_patch`/`check_count`为待实现NW函数，不声称已有库API：

```rust
// Generated model crate: real SeaORM Entity/ActiveModel, not an opaque SQL string.
#[derive(Clone, Debug, PartialEq, sea_orm::DeriveEntityModel)]
#[sea_orm(table_name = "work_item")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = false)]
    pub id: i64,
    pub tenant_id: i64,
    pub version: i64,
    pub title: String,
}
// Generated Relation enum + Related impls are emitted from schema, as appropriate.
// Handler body uses the public ORM against NW's ConnectionTrait implementation.
let changed = work_item::Entity::update_many()
    .col_expr(work_item::Column::Title, sea_orm::sea_query::Expr::value(new_title))
    .col_expr(work_item::Column::Version, sea_orm::sea_query::Expr::value(next_version))
    .filter(work_item::Column::Id.eq(id))
    .filter(work_item::Column::TenantId.eq(tenant_id))
    .filter(work_item::Column::Version.eq(expected_version))
    .exec(session_executor).await?;
check_count(changed.rows_affected)?;
```

片段省略use imports和生成Relation/ActiveModelBehavior，以免把示意体当可直接编译文件；B11/B14必须提供完整可编译fixture。`next_version`由checked规则生成，必须与预期version同事务原子更新；不能在应用先无保护读再写。0 affected表示预期条件未成功更新（不存在/权限/版本冲突不能单靠0行区分），1成功，>1违反唯一性/契约并使事务失败。trigger/row count差异需实际profile测试，不把SeaORM普通update的RecordNotUpdated当完整CAS实现。

C#使用草案：`await WorkCommands.UpdateTitleAsync(session, new UpdateTitleArgs(id, expectedVersion, title), ct)`，结果为Updated/ConcurrencyConflict；C#只编码请求，不生成UPDATE SQL。Insert返回数据库确认键/生成字段，Delete应用同样tenant/key/token条件。默认禁止implicit lazy loading；读取导航属性不会触发I/O。

关系支持明确HasOne/HasMany/多对多join实体；生成SeaORM Relation/Related，Rust显式join projection或split loader。split loader先读有界父keys，再通过已生成子Entity条件按batch查询；保持row/bytes/query-count预算并在Rust组装。外键顺序、tenant过滤和关联key验证均在Rust。需要一致快照时复用显式事务/isolation；ReadCommitted多语句不承诺同snapshot；对笛卡尔放大和N+1给诊断/指标，不靠Include名称担保性能。

可选`DataChangeSet`是C# native handle/typed mutation façade，真正unit of work在Rust，保留有预算的ActiveModel/原始version/关系依赖。entry为Unchanged/Added/Modified/Deleted/Conflict/Uncertain；只支持显式已声明的无环写入图，用户修改C# DTO不会被隐式跟踪。`SaveChangesAsync`在已有外层Active事务时明确拒绝，避免隐式nested begin或过早acceptchanges；它通过B05自己拥有的单事务按生成依赖顺序执行；只有ConfirmedCommitted才清除dirty/接受生成值，Unknown冻结并禁止再Save，恢复后reload/new change set。无需C# identity map、snapshot反射扫描或全局缓存。ActiveModelEx自动graph-save是可选未来内部优化，不能绕过明确写入顺序与版本gate。

## 9. 运行与成本

每个模型native module静态链接生成Entity/dispatch、common Rust host、SeaORM、SQLx和选中driver；不跨DLL传Rust对象。静态query可在构建时生成固定Rusthandler和request template；运行时绑定typed参数后由SeaORM/SeaQuery生成Statement。可以缓存经profile/schema校验的SQLshape，但只能在Rust统一实现并量化cache成本，不回流到C#方言代码。

动态AST Rust校验/构造约O(nodes+parameters)，cache键包括model/semantic/profile/queryshape/codec，值和租户内容不产生无限shapecache。参数复用、NULL补偿可能增加placeholder数量，因此以**最终生成Statement**的参数总数/bytes再次检查，超限拒绝且发送计数0。SQLx prepared cache与NW shape cache分别有限，不能重复无界缓存。

默认Entity/Projection、owned rowbatch和C# DTO可能产生多次copy与分配；async-trait/stream也非自动零成本。B23记录完整生命周期的CPU、native/managedalloc、RSS、线程数、FFI/复制、tail latency、包体/build时间和开发步骤，对比同SQL/事务/正确性下纯RustSeaORM、完整NativeWeave和managed参考。Rust是产品边界决定，性能结论需证据。

流式消费和transaction/cursor lifetimes按D14/D15/D06；reader结束、Task终态、native retire、连接可返池、远端effect是独立条件。通用查询API不泄露SeaORM/SQLx类型，但保留明确能力和不支持诊断，不能通过隐式客户端求值掩盖差异。

## 10. Codex 实施与验收

| Task | 实际产物 | 可观察接受条件 |
| --- | --- | --- |
| B09 | orm-request/1 Rust validator/语义profile；双侧protocol数据定义 | cycle/非法节点/类型/预算全部发送0；两值/三值/NOT/投影rewrite property与oracle一致 |
| B10 | C# syntax/semantic capture、SDK manifest、薄facade | 不生成SQL/ORM核心；缺Rusthandler/manifest错误使build失败；业务执行不调用声明delegate |
| B11 | Rust模型generator、SeaORM dispatcher/lowerer、PG/SQLite能力 | 真正Entity/ActiveModel/Relation源码并可编译运行；最终参数预算；无全rawSQL伪ORM；SQL golden+实库差分 |
| B12 | RustProjection→wire与C#DTO decoder边界 | shape/null/overflow/constructor异常可查；batch一次take、释放；不把C#decoder当数据库mapper |
| B14 | Rust关系/ActiveModel changeset/CAS | 0行不成功；tenant/version原子条件；Unknown不acceptchanges；无implicitSQL；split预算/事务snapshot正确 |
| B22/B23 | 全链AOT/故障/成本 | win-x64/linux-x64真实native运行并加载同hashEngine；结果/次序/error、资源长期有界，命令及产物hash可追溯 |

属性/fuzz生成nullable、边界整数、重复空集合、Unicode、collation、无匹配join、空组、深树、过量参数、非法schema和projection。预期由独立有限C#语义oracle/数据库事实建立，不用同一Rust lowerer生成期望。C#实验只作oracle，实际接受必须执行RustORM→DB→wire→AOT客户端。数据库version/SQLitecompile options及Rustcrate锁是输入。

未来命令（本轮未执行）：`cargo test --locked -p nw-orm-seaorm`、`cargo test --locked -p nw-orm-relations`及生成fixture的C#/Rust构建、真实PG/SQLite差分和Windows/Linux NativeAOT发布运行。语义、schema、requestIR和modelbuild版本共同协商；改变NULL/collation/overflow含义必须新profile或主版本。Q13/Q14的RustORM职责与安全动态边界是已形成的设计决定，正式接受需独立review；所有编译/运行义务保持pending。
