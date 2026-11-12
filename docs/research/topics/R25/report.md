# R25 — SeaORM选型、实体与关系

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `22a35bfe736e0f07bfb21bc10115a6ea7dd20233489b07d9a7926f1c0436524f`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 自主选定SeaORM，不再用SQLx代称ORM

用户明确Rust提供合适ORM、C#仅最上层。比较后选SeaORM2.0.4+SQLx0.9/SeaQuery1.0系列；SQLx是驱动/查询执行，SeaQuery是SQLbuilder，不能单独满足ORM选型。旧自有C#IR/mapper/TrackedUnitOfWork默认方案superseded，EF/Npgsql/DapperAOT只研究和benchmark。

SeaORM采用真实Entity/Model/ActiveModel/Column/Relation/Related、typedProjection和runtimeCondition。Diesel2.3.14的dynamic-schema与boxedquery由root实际读取：dynamic schema真实存在但失去部分schema/type编译保障，boxed仍有ST/QS/DB/GB泛型与boxfragments；不是“Diesel不能动态/异步”。本场景选择SeaORM的async模型与动态条件组合，未测性能优劣。完整root路径/blob/ranges以cross-task证据保存。

## 2. 公共API到ORM内部与测试

EntityTrait静态关联类型→Entityfind/filter/join→SeaQueryStatement→ConnectionTrait→SQLxdriver→QueryResult→FromQueryResult→Model/Projection。ActiveModel定义Set/Unchanged/NotSet，insert/update先before_save再Entityexecutor后after_save；save只按PKNotSet决定insert/update，不能当真正upsert。try_set返回Result，set不匹配可panic；外部typedrequest先校验，用typed构造/try_set。

RelationTrait/Related提供key/direction/via及RelationDef，真实join/related查询可由生成的Entity复用；codegen compact writer发射DeriveEntityModel/Relation/Related，fixture显示FK和has_many。tests/relational_tests读取了插入join实体、find_also_related/into_model/missingNone/find_related；只读未运行。

Update executor判断rows_affected/RETURNING，普通单行RecordNotUpdated不是自动versionCAS；NW显式key+tenant+expectedversion谓词、原子nextversion，0冲突、1成功、>1违约。transaction_tests显示after_save报错时事务内行已经存在，scope rollback后才清零；failure与effect必须分开。v1使用无副作用默认hooks，关系写操作明确transaction，不接C#回调hook。

## 3. 生成模型而非伪万能引擎

C#schema/query→SDKprebuild逻辑manifest→RustCLI验证/生成静态Entity/ActiveModel/Relation/Projection/dispatcher→与commonRustDBcrate静态链接到一个model native module。C#SG只消费已存在manifest生成薄API/encoder/DTOdecoder。新增实体/关系/projection/staticquery需重编译native，普通开发者不写Rust，可CI预构建；不声称运行时从任意schema生造Rust泛型。

统一requestIR由Rust解释，C#仅提前syntax/type/budget检查；dynamicCondition限于编译实体/列/关系/投影。SeaORMActiveModelEx源码注明minor可能变化，v1核心依赖普通ActiveModel/Relation，显式boundedchangeset，不把evolvinggraph API当public ABI。

## 4. Session/事务适配与Rust工作单元

默认SeaORMDatabaseConnection每queryacquire；DatabaseTransaction私有conn、consumecommit、Droptry_lock/expect不能直接满足NW固定Session及quiescence。RustSessionExecutor实现公开Connection/Stream/Transactiontraits，持有SQLxPoolConnection并控制budget/close，真正ORM链仍工作。公开row/resultFrom和SqlxValues提供依据；Send/borrow/trait组合未编译，由B04/B05fixture验证，不能自称已集成成功。

默认结果无隐式tracking/lazyload；C#DTO修改不自动送库。可选DataChangeSet只是nativehandle façade，Rust保存有界ActiveModel/原始version/关系依赖，SaveChanges拥有明确事务；已有外层Active事务拒绝，避免earlyaccept。ConfirmedCommitted才acceptchanges，Unknown冻结，恢复后reload。关系Replace/Clear/Delete必须显式，不能从C#集合缺项猜删除；显式joins/splitload支持HasOne/HasMany/多对多。

## 5. 候选成本与实测义务

EFStateManager/ChangeDetector真实identitymap/snapshot/scan及成功AcceptAllChanges路径保留作对照，不是NW复制目标。RustModel/Projection+wire+C#DTO有copy和alloc，SeaORMasync-trait/stream也有box成本，schema-specific编译有build时间/包体成本；这些必须量化，不能因Rust/静态类型名称断言胜出。

B11模型生成+实际ORMquery/CRUD，B14FK顺序/relations/CAS/changeset/Unknown/after-saveeffect，B12wire/DTOerrorcleanup；B22真实PG/SQLite和Windows/LinuxAOT；B23与同功能纯RustSeaORM及managed参考对照CPU/alloc/RSS/P99/build/code量。没有执行Rust/C#代码或上游测试。完整SeaORM所有loader/继承/schema-sync、Dieselasync实现、全部drivercodec未读；status保持partial，但适合本项目的ORM选择与边界已有明确设计决定。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R25-C01 | [src/EFCore/ChangeTracking/Internal/StateManager.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/ChangeTracking/Internal/StateManager.cs#L324-L365) | [[324, 365], [1423, 1490]]; source-observed; reader=database_design |
| R25-C02 | [src/EFCore/ChangeTracking/Internal/ChangeDetector.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/ChangeTracking/Internal/ChangeDetector.cs#L130-L179) | [[130, 179], [242, 317]]; source-observed; reader=database_design |
| R25-C03 | [src/EFCore.Relational/Update/AffectedCountModificationCommandBatch.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore.Relational/Update/AffectedCountModificationCommandBatch.cs#L410-L437) | [[410, 437], [526, 590]]; source-observed; reader=database_design |
| R25-C04 | [test/EFCore.Specification.Tests/OptimisticConcurrencyTestBase.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/test/EFCore.Specification.Tests/OptimisticConcurrencyTestBase.cs#L28-L63) | [[28, 63], [351, 407]]; test-source-observed; reader=database_design |
| R25-C05 | [src/EFCore/Query/Internal/QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs#L60-L115) | [[60, 115], [134, 156]]; source-observed; reader=database_design |
| R25-C06 | [src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs#L53-L74) | [[53, 74], [207, 236], [515, 543]]; source-observed; reader=database_design |
| R25-C07 | [src/Dapper.AOT/Internal/AsyncQueryState.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/Internal/AsyncQueryState.cs#L15-L54) | [[15, 54], [76, 116]]; source-observed; reader=database_design |
| R25-RU01 | [Cargo.toml](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/Cargo.toml#L1-L195) | [[1, 195]]; source-observed; reader=/root/database_design |
| R25-RU02 | [src/entity/base_entity.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/base_entity.rs#L65-L135) | [[65, 135]]; source-observed; reader=/root/database_design |
| R25-RU03 | [src/entity/active_model.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/active_model.rs#L1-L100) | [[1, 100], [215, 240], [340, 405], [440, 465]]; source-observed; reader=/root/database_design |
| R25-RU04 | [src/entity/relation.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/relation.rs#L1-L145) | [[1, 145], [301, 326]]; source-observed; reader=/root/database_design |
| R25-RU05 | [src/executor/update.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/update.rs#L1-L220) | [[1, 220]]; source-observed; reader=/root/database_design |
| R25-RU06 | [src/executor/select.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/select.rs#L266-L324) | [[266, 324], [869, 925]]; source-observed; reader=/root/database_design |
| R25-RU07 | [tests/relational_tests.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/tests/relational_tests.rs#L619-L710) | [[619, 710], [711, 784]]; test-source-observed; reader=/root/database_design |
| R25-RU08 | [tests/transaction_tests.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/tests/transaction_tests.rs#L142-L169) | [[142, 169], [206, 235], [272, 300], [994, 1027], [373, 455]]; test-source-observed; reader=/root/database_design |
| R25-RU09 | [sea-orm-codegen/src/entity/writer/compact.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/src/entity/writer/compact.rs#L1-L159) | [[1, 159]]; source-observed; reader=/root/database_design |
| R25-RU10 | [sea-orm-codegen/tests/compact/fruit.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/tests/compact/fruit.rs#L1-L39) | [[1, 39]]; test-source-observed; reader=/root/database_design |
| R25-RU11 | [LICENSE-MIT](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/LICENSE-MIT#L1-L25) | [[1, 25]]; source-observed; reader=/root/database_design |
| R25-ROOT04 | [diesel_dynamic_schema/src/lib.rs](https://github.com/diesel-rs/diesel/blob/4007d771b1e808839f771a693f6bae9f821f0e64/diesel_dynamic_schema/src/lib.rs) | whole_file; cross-task-source-evidence; reader=/root |
| R25-ROOT05 | [diesel/src/query_builder/select_statement/boxed.rs](https://github.com/diesel-rs/diesel/blob/4007d771b1e808839f771a693f6bae9f821f0e64/diesel/src/query_builder/select_statement/boxed.rs) | [[1, 190]]; cross-task-source-evidence; reader=/root |
| R25-ROOT06 | [diesel_dynamic_schema/tests/dynamic_values.rs](https://github.com/diesel-rs/diesel/blob/4007d771b1e808839f771a693f6bae9f821f0e64/diesel_dynamic_schema/tests/dynamic_values.rs) | [[1, 140]]; cross-task-source-evidence; reader=/root |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
