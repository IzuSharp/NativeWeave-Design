# C# 顶层查询语法、Rust ORM 生成与 Native AOT

- Task：D17；设计规范：**C-QUERYGEN-001@0.1.0**；作者：database_design；2026-11-12。
- 状态：**review-ready**；接受状态以registry中的相同内容hash及独立Review为准。C#/Rust样例均design-draft、未编译；没有generator/ORM/Native AOT运行证据。
- 输入packet：revision0.1.1，SHA-256 `ae92f367f9f3d6d61004d903da62225179e38df270ce15801a334d617194ff3d`；基线Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`、Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- 输入：[R23](../research/topics/R23/report.md)、[R24](../research/topics/R24/report.md)、[R25](../research/topics/R25/report.md)。Rust ORM权威：[D16](../database/query-semantics.md)；Database/wire：[D14](../database/drivers.md)；通用生成/build：[D03](binding-pipeline.md)、[D10](../platforms/build-package-release.md)。

## 1. 确定职责与修订

**QGEN-D004：C#仅是上层语法与AOT边界。** 保留显式命名LINQ/Fluent声明和必须生成实现的public partial执行方法；C#工具用Roslyn捕获准确symbol、逻辑类型、参数来源和源码span，输出`orm-request/1`与schema声明。SQL语义规范化、关系、SQL方言、查询执行、DB row→Model/Projection由Rust SeaORM Engine负责。C#只生成请求encoder、对native runtime的薄调用和wire→DTO decoder。

**QGEN-D005：双语言生成采用显式构建阶段，不依赖Source Generator排序。** SDK prebuild提取C#声明→Rust ORM CLI验证并生成Entity/ActiveModel/Relation/Projection与static dispatcher→Cargo生成schema-specific Engine→C#单一增量SG消费已存在的manifest并生成普通C#。普通应用开发者不用手写Rust；新增模型/查询需要Rust编译，可由本机受控工具链或CI按hash预构建包完成。不能承诺任意schema不用native重编译。

**QGEN-D006：缺生成或不支持即构建失败；不存在任意IQueryable运行时fallback。** 动态查询仅构造受限typed request AST，Rust再次验证已登记schema/projection/capability后执行。C#不调用Expression.Compile、Reflection.Emit或MakeGenericType，不重建ORM核心。

旧QGEN-D001直接生成C# SQL/binder、旧“默认Data/Query不需要Rust”、旧“无需跨工具build路线”均superseded。partial入口/源码捕获及SG加法约束仍有效；C#数据库provider只用于参考比较。

## 2. 证据及设计选择

SeaORM2.0.4 `db40a19a7bde7be8e1c4b346b1b70d72e87f0245` 的EntityTrait要求静态Model/ActiveModel/Column/Relation；`sea-orm-codegen/src/entity/writer/compact.rs`全文真实生成DeriveEntityModel、DeriveRelation与Related；fixture `tests/compact/fruit.rs`含实际FK/has_many声明。runtime Condition可构造，但不把未知外部schema自动变成新的Rust泛型。因此选择模型专属生成与编译，而不是把typed ORM包装成万能无模型引擎。详细blob/ranges见R25。

EF Core11 QueryCompiler固定源码的dynamic-code/预编译分支、DapperAOT1.1.0增量入口的skip路径支持“每声明必须有覆盖记录”的要求，不证明这些库全面不兼容AOT。它们是对照，不是产品runtime依赖。

Roslyn cookbook `b907b90240f9f22873227aa510794dd280d61f57` 的generator只能添加源、无执行顺序、看不到其他SG产物，由R06/root实际读取传入。**不能 Query SG生成LibraryImport/JsonSerializable注解后再假设其他SG本轮接管。** 固定数据库ABI绑定沿用D03/A10/A13选定的blittable DllImport bootstrap与typed function table，在普通Compile输入或已编译支持库中提供；Query SG只调用该公开runtime接口。LibraryImport普通Compile输入是可测试备选，不是本数据库管线强制路线；不产生需要第二生成器发现的标记链。

## 3. 用户入口与生成接管点

以下是完整形状示例，**design-draft、未编译、无运行保证**；`QuerySchema.Table<T>`、`QueryDefinition<T>` 和 LINQ pattern 方法是NativeWeave自己的声明API，不实现IEnumerable/IQueryable。

```csharp
public readonly record struct FindOpenArgs(Guid TenantId, int MinPriority, int Limit);
public sealed record WorkItemRow(Guid Id, string Title);

public static partial class WorkQueries
{
    [WeaveQuery(nameof(DescribeOpen))]
    public static partial Task<IReadOnlyList<WorkItemRow>> FindOpenAsync(
        DataSession session, FindOpenArgs args, CancellationToken ct = default);

    private static QueryDefinition<WorkItemRow> DescribeOpen(
        QuerySchema db, FindOpenArgs p)
        => (from w in db.Table<WorkItem>()
            where w.TenantId == p.TenantId && w.Priority >= p.MinPriority
            orderby w.CreatedAt descending, w.Id descending
            select new WorkItemRow(w.Id, w.Title)).Take(p.Limit);
}

await using var session = await source.OpenSessionAsync(ct);
IReadOnlyList<WorkItemRow> rows = await WorkQueries.FindOpenAsync(
    session, new(tenantId, 2, 100), ct);
```

`WeaveQueryAttribute` 绑定同一partial类中的唯一private static声明方法；schema metadata来自用户写入源代码的entity/column属性及引用库的显式已注册manifest。声明方法由普通C#编译器绑定和类型检查，但业务执行不调用它。声明API的 `Where(Func<T,bool>)`、`Select(Func<T,TResult>)`、Join及ordering模式只用于类型检查，运行调用立即抛 `QueryDefinitionExecutionException`，分析器对静态可见调用报错。这里使用delegate签名而非构造Expression Tree；generator从源码取得语义，运行时不创建闭包/树。

带accessibility及非void返回值的partial方法必须有实现。generator缺失、语法不支持或配置缺失时，不生成该实现并报告error；正常C#编译同时阻止缺实现的程序产生。**不得生成throw-only实现后声称覆盖成功**。在生成源码内可直接调用同一次generator产生的private binder/mapper，但不得等待另一个generator再补元数据。

为免有查询定义但没人执行而仍漏诊，发现阶段枚举全部WeaveQuery方法，不依赖调用点是否存在。运行入口只依赖生成实现，不通过反射扫描attribute选路。

## 4. 支持与拒绝矩阵

| 语法/场景 | v1处理 |
| --- | --- |
| 映射表的Where、Select、OrderBy/ThenBy、Take/Skip | 支持C-QUERY-001的谓词/投影及稳定排序；limits参数必须非负有界 |
| INNER/LEFT JOIN、显式aggregate GroupBy | 支持RustORM已登记的关系与projection形状；LEFT JOIN完整nullable/match-marker规则 |
| 参数DTO成员、编译期常量、已登记纯函数 | 支持；参数入口一次快照，常量按类型参数化策略 |
| 有限Contains集合、可空比较、条件表达式 | 支持明确语义及预算；不支持任意对象comparer |
| 外部可变闭包、静态时间/随机/环境读取、属性副作用 | 拒绝；调用者先算好并显式传args |
| 任意本地函数/业务函数/Expression.Invoke/Compile | 拒绝；需要显式Sql函数映射及纯度/方言metadata |
| 返回未约束IQueryable供运行时拼接 | 拒绝；转受限动态AST |
| 跨assembly只有方法body而没有query manifest | 拒绝；构建工具不反编译依赖DLL猜语义 |
| 任意开放泛型结果、运行时MakeGenericType | 拒绝；使用显式闭合泛型注册或非泛型DTO |
| 循环、异常处理、I/O、yield在声明body内 | 拒绝；声明是单一表达式/规范IR组合，不执行用户代码求值 |
| 动态SQL标识符字符串、未登记方言函数 | 拒绝；专家SQL是显式其他入口，不作为自动fallback |

实现应对Roslyn绑定的**精确symbol identity**进行白名单匹配，不凭方法名叫Where/Contains判定。重载、extension method、隐式转换、user-defined operator、nullable及NRT差异要纳入diagnostics测试。查询声明中的 `DateTime.UtcNow` 不能被generator在build时求一次后固化成常量。

## 5. 参数、请求与流的快照

生成入口在第一个await前按稳定顺序快照标量/只读record成员；集合按有限元素数/bytes复制。拒绝任意副作用getter、并发变更的复杂对象、开放类型；调用者把时间/随机等先算好作为args。C#wire codec只转换CLR→logical值；Rust负责logical→SeaORM/SQLx值，NULL及codec必须明确，不能以object推断掩盖类型。

静态请求发送query ID、model/schema/semantic hash、参数cells；不携带由C#生成的SQL。Rust执行generated handler的已验证request template，在最终SeaQuery Statement生成后重新核对placeholder数量/SQLbytes。C#集合900元素限制不等于最终参数900，null补偿/投影重用等可能扩展；超限在Rust命令发送前报错，不能偷偷字面量插值。

流公开方法是非iterator包装器：调用时立即快照args，然后返回捕获immutable request的内部async iterator。第一次MoveNextAsync才开启native cursor；每次枚举新operation，同Session并发仍拒绝。`WithCancellation`与调用token只发取消请求，native最终结果决定结束。提前break、decoder抛错、枚举器DisposeAsync均走batch释放/cursor stop+drain，不仅丢掉托管Task。流的请求/结果owner按D14/D06，不把stack Span借给异步Rust。

## 6. 可实现的构建管线与版本图

1. **C#提取（B10）**：SDK工具在CoreCompile之前，使用相同parse/compilation options分析用户提交的实体/查询源与引用manifest，按准确symbol提取`schema-declarations/1`和`orm-request/1`，保留源码span→node映射。读取方法body但绝不执行用户delegate、属性或构建SQL。预提取只要求用户提交的query/schema声明及其传递依赖符号绑定有效；声明内缺实体、未知operator或类型错误仍失败。无关业务执行调用点对本SG稍后产生的WorkItemSchema/partial实现等引用，此阶段不充当全项目编译门禁，不全局忽略CS0103或其他错误。只对已发现声明分析精确symbol/语义；CoreCompile最终对全Compilation严格检查所有错误（包括生成缺失），不能用预分析白名单吞掉真实错字。
2. **Rust检查与生成（B09/B11）**：锁定版本的`nw-orm-codegen` CLI验证类型、NULL/TruthKind、关系/投影、profile和预算，用同一Rust语义实现生成SeaORM实体、Column/Relation映射、ActiveModel mutation与闭合projection、static query dispatcher。外部标识符只从schema受控映射，生成源码必须正确转义并处理Rust关键字/冲突；拒绝未知类型而不自动转String。
3. **Native构建（B11/A13）**：generated crate与commonRust host/driver/transaction/ORM crates静态链接到一个model native module；`cargo --locked`构建所选RID。不会从C#运行时动态编译Rust或装入任意schema插件，也不在独立DLL之间传Rust Model/Arc/trait object。开发工具链和CI预构建是两种部署方式，不是两套ORM。
4. **产物manifest**：Rust工具输出schema/query/projection IDs、wire与semantic版本、modelbuildhash、实际ORM/driver/features/Cargo.lock、结果shape、capabilities、诊断与native artifact hashes。C# SG的AdditionalFiles来自这个已经存在的build产物；build graph显式记录其输入hash，缺文件/过期hash失败。
5. **C#生成（B10/B12）**：一个incremental pipeline消费声明与manifest，生成所有partial façade、请求encoder、闭合DTO decoder和静态注册；不生成SQL、关系optimizer、DB row mapper或另一个SG所需attribute链。所有公共执行方法必须具有对应Rustquery/projectionmanifest条目；不能生成throw-only stub当成功。
6. **最终校验**：常规C#编译/Native AOT publish绑定正确native包；加载时再校验engine ABI、schema/query/semantic/modelhash和RID。native只有旧query而C#调用新ID必须拒绝，不能依ordinal碰巧兼容。真正AOT进程执行集成fixture，不止比较生成文本。

B10单独可用固定manifest fixture进行语法/增量/diagnostic测试；B11单独可用checked-in逻辑schema fixture编译SeaORM模型，两任务不因对方未完成而停止写作/单元验证。共同集成需要B04/B07/B11/B12/A13的已接受契约和实际编译产物；实际任务依赖由D27/D28 fragment精确表达。

支持用户提交C#源/显式已发布schema manifest。另一个Source Generator本轮才生成的实体/声明不在本次提取器可见输入中，必须由它的SDK预阶段产成普通Compile文件或报NWQ0014；不假装依赖SG顺序。跨assembly只接收版本化manifest，不反编译IL或执行代码发现模型。

增量输入包含全部源/编译选项/AdditionalFiles、schema/query/profile、Rustgenerator版本/锁与target。使用稳定ID和内容hash，不用绝对路径、随机数或timestamp决定代码。无关文件编辑不重建模型；相关实体/投影变化必须invalidate Rustartifact与C#decoder。相同输入不同机器应得到可解释的同内容生成源码；二进制可复现约束按A13，不把机器相关调试路径忽略为已证实reproducible。

### 6.1 模型与查询 hash 的变化义务

| 修改 | 必须重建/校验 |
| --- | --- |
| 只改变运行参数值 | 不重编译；双侧input budget与Rust类型校验 |
| 在已登记column/projection上的动态条件组合 | 不新增Rust类型；Rustvalidate/cache预算；query语义profile固定 |
| 新列/实体/FK/codec/静态query/projection | 重生成Rust模型/dispatcher与C#manifest，重建model native module |
| SeaORM/SQLx/SeaQuery/SQLite/nativefeature升级 | 新modelbuildhash/Cargo.lock/制品hash及实际平台回归；不是只改包版本 |
| 数据库live schema迁移 | B08 ledger与应用兼容窗口；匹配manifest不证明实际数据库已迁移 |

## 7. Rust ORM mapping 与 C# DTO decoder

Rust生成的SeaORM Model/Projection用已确定列/alias和typed codec从DB row读取；随后写db-wire/1 batch。C#decoder只校验batch/schema/projection/cell标签、NULL/长度/范围并构造可访问DTO，不解释DB-specificrow或生成SQL。字段默认值不掩盖SQLNULL；取不到合法projection必须错误，不能按object字典再反射构造未知CLR类型。

C# DTO构造函数可能抛异常；generated finally必须释放已take的ownedbatch，关闭/排空cursor，保留原错误和cleanup关联。native的query/commit effect已发生时，decoder或after-save bridge错误不能把effect清零，也不能自动重试；D15决定Unknown/confirmed结果的传播。样例代码、Rust trait/lifetime实现和实际generator都尚未编译。

JSON可以wire文本/bytes传递，应用要求typedJSON DTO时显式提供已声明`JsonTypeInfo<T>`入口或同一管线确实实现的静态codec；不自动启用动态JSON provider。Query SG不发JsonSerializable后期待System.Text.Json SG二次发现。generic外观允许用户自然调用，但所有实体/DTO/codec/handler都须构建期闭合注册；开放MakeGenericType在AOT进程中拒绝。

## 8. 安全动态请求与专家 SQL

动态 API 的C#工作只是组合受限request，示例仍是design-draft：

```csharp
QueryFilter filter = WorkItemSchema.Priority.GreaterThan(minPriority)
    .And(WorkItemSchema.TenantId.Equal(tenantId));
IReadOnlyList<WorkItemRow> rows = await DynamicQueries.WorkItemRowsAsync(
    session, filter, WorkItemSchema.OrderByCreatedThenId, limit: 100, ct);
```

WorkItemSchema来自同一C#生成输出；普通最终Compilation可绑定它，捕获器无需在同一轮再读取其生成代码。用户字符串字段先由应用映射到预登记descriptor，不接受任意SQLidentifier。Rust验证column/tenant/operation/projection IDs、类型、depth、nodes和最终Statement，映射到真正SeaORM Column/Condition/Entity。C#有typedColumn包装不等于跳过Rust验证。

初始预算：depth64、nodes4096、集合元素900、最终总参数900、最终SQL UTF-8≤512KiB、请求bytes≤4MiB；profile还需满足实际provider上限。运行输入不改变schema/projection，cache条数/bytes有限；无法按模板执行的复杂查询在构建或发送前明确拒绝。不会运行Expression树或C#delegate来完成查询。

专家SqlTemplate属于单独声明入口，常量模板/显式typed参数/静态projection，运行路径仍在Rust、资源/事务/预算相同。动态字符串不自动获得“已参数化”身份；identifier孔只接受trusted descriptor。SQLx AssertSqlSafe是Rust开发者断言，不是转义器。普通ORM不支持的功能不会偷偷转换为expertSQL；事务内SessionMutating专家SQL按D15拒绝。

## 9. 诊断契约

| ID（error） | 触发 | 修复方向 |
| --- | --- | --- |
| NWQ0001 | 声明方法不存在/不唯一、执行签名不匹配 | 使用同类唯一声明、已支持signature |
| NWQ0002 | 未支持语法、方法、operator或调用图 | 改为白名单操作/显式SQL |
| NWQ0003 | 捕获外部状态、副作用getter、不可快照参数 | 显式不可变args |
| NWQ0004 | null、overflow、collation或truth语义不明确 | 选择声明profile/显式转换 |
| NWQ0005 | provider/version缺少feature | 更改query或明确provider扩展 |
| NWQ0006 | 结果无法静态映射、nullability/codec不兼容 | 可访问DTO构造/明确codec |
| NWQ0007 | 未闭合泛型、缺失跨assemblymanifest | 注册闭合类型/发布manifest |
| NWQ0008 | schema/参数/投影shape不一致 | 更新schema与声明，禁止猜测 |
| NWQ0009 | Take/Skip/分页缺少稳定唯一排序 | 加明确order与tie-breaker |
| NWQ0010 | 不安全identifier/SQL片段来源 | 使用descriptor或审计专家SQL |
| NWQ0011 | 静态复杂度/参数预算超限 | 有界batch或简化query |
| NWQ0012 | 业务代码直接调用query声明方法 | 调用生成执行入口 |
| NWQ0013 | JSON/自定义codec无静态metadata | 显式提供typed metadata |

运行时输入budget/shape失败对应有结构化query ID及错误类别的异常，日志不含连接秘密或完整敏感参数。warning级别建议不能替代上述error；禁用分析器也不能使未生成的partial方法静默获得runtimefallback。

## 10. 具体诊断、构建和验收义务

新增error：NWQ0014表示输入依赖另一个SG本轮输出而没有普通Compile源/显式manifest；NWQ0015表示Rust模型/handler/projection缺失或hash不匹配；NWQ0016表示RustORM构建/最低工具链/锁版本不兼容。Rustvalidator诊断携带node ID，由build tool映射回C#span，缺源码span也保留稳定query/node定位。禁用analysis warning不允许绕过缺partial实现/缺manifest错误。

| Task | 必须真实完成的验证 |
| --- | --- |
| B10 | C#正常/拒绝语法fixture，精确symbol/重载/operator/closure/泛型/跨assembly/SG不可见；缺生成即build失败；无SQLemitter/运行时Expressionfallback |
| B11 | 输入schema→完整RustEntity/ActiveModel/Relation/Projection→可编译handler；PG/SQLite真正ORM CRUD/join/动态Condition；schema hash错拒绝 |
| B12 | wire shape/NULL/overflow/constructor异常；owned batch一次take+finally；不借用native row到下一MoveNext；闭合genericAOT |
| B13 | C#/Rust协议mutation与fuzz、非法identifier/opcode/cycle/预算、所有拒绝请求DB发送计数0；最终参数扩张计数准确 |
| B10/B11/A13 | 两阶段build增量/相关失效/无关文件不重建；CLI/IDE差异明确；生成确定性；错RID/锁/模型包不可偷用旧产物 |
| B14/B22 | Rust关系/ActiveModel hook效果/CAS/事务Unknown；完整C# AOT→ABI→SeaORM→PG/SQLite；真实取消/stream/Dispose/故障与长期资源 |
| B23 | 相同语义负载比较纯RustSeaORM与NW端到端、managed参考；build时间/codegen体积/内存/CPU/尾延迟/应用代码量 |

未来执行入口（本轮未运行）：`dotnet test tests/Query.Generator`、`cargo test --locked -p nw-orm-codegen`、`cargo test --locked -p nw-orm-seaorm`，然后按D10/平台规范在Windows/Linux实际publish并执行NativeAOT制品。必须执行生成代码，不能仅assert生成文本或只跑JITtesthost。

C#现代语言特性用于简洁DTO、闭合generic、编译诊断和安全owned边界；Rustedition2024/SeaORM静态types用于实体/关系与资源生命周期，不为展示语法扩大API。公共Task用于自然组合；内部ValueTask仅在有实际收益且单次消费约束明确时使用。性能、内存和开发效率同时计量，Rust方向本身不替代性能证据。

Q13的捕获/构建接管点和Q14的安全动态边界已形成技术决定，正式接受需独立review。Rusttrait最小实现、C#示例编译、模型生成、双平台AOT、真实数据库与压力/fuzz仍是独立pending义务，不以设计决定假称已验证实现。
