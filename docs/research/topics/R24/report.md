# R24 — Rust查询语义与参数安全

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `eb8ca392ff71d128ca7a373e4dcdacc261d2cb280389f02450c692cb9d2dede0`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 语义权威迁到Rust，参考事实不变

Q14确定RustORM request validator/lowerer负责C#可空语义、SQLTruth、capability/参数预算，SeaORM/SeaQuery负责实际查询/方言/绑定。C#只捕获typed语法和参数，旧C#关系IR/SQLemitter决定superseded。专家SQL是显式补充，不能普通查询失败后自动转rawSQL。

## 2. NULL与可验证反例

C#nullable > 任一null为false，取反后为true；SQL普通比较为UNKNOWN且NOT UNKNOWN仍UNKNOWN。Rust采用完整two-valued normalization，只有满足上下文前提才优化，不能把WHERE专用rewrite搬入projection/NOT。EFSqlNullabilityProcessor完整补偿/过滤优化源码和negatednullable测试已读；C#与SQLite官方语义页面已读。

Contains空集合false、null匹配null、重复不改变结果；不能把含NULL的NOT IN当C#取反。最终RustStatement重新计参数数量，默认总900；只检查输入900个元素不够，补偿/重复表达可能展开。变量必须参数化，table/column/operator来自schemaID；SqlSafeStr/AssertSqlSafe只保证调用者断言，非sanitizer。

## 3. 已读Rust ORM链

SeaORM2.0.4 QueryFilter.filter本体调用SeaQuerycond_where，runtimeCondition可与静态Entity共存；显式order nulls示例。RelationDef包含关系方向/key/via/ONcondition，supporttypedjoin。Selectprojection由RustFromQueryResult处理，不依C#数据库mapper。SeaQuery1.0.2 build生成SQL+Values而to_string inline，SQLiteSEARCH/CYCLE空实现反例要求capability先拒绝。

## 4. 关系、数值、排序

LEFTJOIN ON vs WHERE改变行集；missing row用nonnullkey/matchmarker，不能把nullablecell当存在性。GroupBy仅明确aggregate，C#emptySUMzero与SQLSUMnull不同；Min/Max/Average签名明确empty/error。SQLiteint64overflow会转REAL，portableprofile拒绝未证明范围的checked等价；decimalTEXT不允许数值sort/SUM。字符串collation/Unicode不可从相同方法名推导跨库一致，初始portablebinary只覆盖受限ASCII。

分页显式排序/唯一tie-breaker，keysetcursor绑query/schema/profile与租户授权。ReadCommitted多请求不保证snapshot一致；需要显式snapshot/物化IDs策略。未支持operator/functions/collation/动态projection拒绝，不能客户端求值。

## 5. 本轮唯一实际实验及边界

`sqlite_semantics_probe.py`：Python3.12.14、SQLite3.53.1、Linuxx86_64，实际50checks0failures，原始stdout/stderr/result及hash均保留。9组nullablepairs×eq/ne/gt/notnormalized、empty/nullContains、负对照NOT、LEFTJOIN、COUNT/SUM、参数注入样值、keyset、decimalTEXTsort和整数overflow。未修改该实验，也未将它标为Rust/SeaORM/NativeWeave验证。

B09Rust语义property；B11PG+SQLite真实差分；B13AST/value/identifier/nodecycle与最终参数预算fuzz；B22完整C#AOT经nativeORM执行。预期来自独立有限oracle和实库，不能用待测emitter自己生成期望。没读完数据库optimizer/全部collation/functionmatrix，保持partially_evidenced；设计支持/拒绝边界已经给出而非笼统open。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R24-C01 | [src/EFCore.Relational/Query/SqlNullabilityProcessor.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore.Relational/Query/SqlNullabilityProcessor.cs#L38-L79) | [[38, 79], [728, 751], [856, 879], [1118, 1141], [1398, 1421], [1875, 2015]]; source-observed; reader=database_design |
| R24-C02 | [test/EFCore.Relational.Specification.Tests/Query/NullSemanticsQueryTestBase.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/test/EFCore.Relational.Specification.Tests/Query/NullSemanticsQueryTestBase.cs#L1628-L1656) | [[1628, 1656], [2081, 2113]]; test-source-observed; reader=database_design |
| R24-C03 | [src/prepare.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/prepare.rs#L1-L196) | [[1, 196]]; source-observed; reader=database_design |
| R24-C04 | [src/query/traits.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/query/traits.rs#L1-L131) | [[1, 131]]; source-observed; reader=database_design |
| R24-C05 | [src/backend/query_builder.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/backend/query_builder.rs#L678-L701) | [[678, 701], [715, 738], [825, 848], [1070, 1101], [1108, 1131], [1909, 1932]]; source-observed; reader=database_design |
| R24-C06 | [src/backend/sqlite/query.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/backend/sqlite/query.rs#L21-L47) | [[21, 47], [65, 86]]; source-observed; reader=database_design |
| R24-C07 | [tests/postgres/query.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/tests/postgres/query.rs#L5-L48) | [[5, 48], [166, 184]]; test-source-observed; reader=database_design |
| R24-C08 | [LICENSE-MIT](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/LICENSE-MIT#L1-L25) | [[1, 25]]; license-text-observed; reader=database_design |
| R24-C09 | https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-value-types | 定位见evidence; official-documentation-observed; reader=database_design |
| R24-C10 | https://www.sqlite.org/lang_expr.html | 定位见evidence; official-documentation-observed; reader=database_design |
| R24-C11 | [sqlite_semantics_probe.py](sqlite_semantics_probe.py) | actual script SHA-256 `f78a340af85a34b16464531b0ad6c3249f33aeda1d8d11e9dff4e8e51570b455`; result/logs in [evidence.json](evidence.json); executed-reference-experiment; reader=database_design |
| R24-V1 | [refs/tags/1.0.2](https://api.github.com/repos/SeaQL/sea-query/git/refs/tags/1.0.2) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R24-RU01 | [src/query/helper.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/query/helper.rs#L625-L810) | [[625, 810], [811, 838]]; source-observed; reader=/root/database_design |
| R24-RU02 | [src/entity/relation.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/relation.rs#L1-L145) | [[1, 145], [301, 326]]; source-observed; reader=/root/database_design |
| R24-RU03 | [src/executor/select.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/select.rs#L266-L324) | [[266, 324], [869, 925]]; source-observed; reader=/root/database_design |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
