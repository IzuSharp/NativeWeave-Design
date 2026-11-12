# R22 — Rust类型映射、wire与Schema演进

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `4d1a2391ad586e528cc898985824bc3c3f27381685de53ffe3c5a8263b564b9a`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 现在的类型边界

C#只负责CLR值↔db-wire/1以及DTO构造；Rust的schema、SeaORM Model/Projection和SQLxcodec负责数据库类型与rowmapping。原“Npgsql默认静态mapper”决定superseded，但原精度/UUID/资源研究保留为比较。DB-D004与D14固定wire字段，D16控制可用比较语义，不用object/string默认猜类型。

## 2. 新读Rust真实路径

SQLx0.9 PG Uuid encode使用as_bytes，binary decode from_slice、text parse；SQLite Uuid编码BLOB，Hyphenated/Simple是独立TEXT映射。NW声明16字节RFC4122 wire与SQLiteBLOB，不复制CLR Guid内部混合端序，不混用schema。SeaORM公开row→QueryResult转换后，Select into_model/into_partial_model/stream调用FromQueryResult，由Rust生成的闭合Projection完成DB映射。

PG chrono时间codec以相对PG epoch微秒编码、DateTime转换naive_utc。源码没有替NW实现“拒绝sub-microsecond损失”的规则；NW须在schema/codec前检查。binary decode中的时间加法极端值是额外负例，需验证范围/受控错误，不以trait Result推断不会panic。Rust typed codec、wireUTCmicroseconds与CLR值之间的完整支持域必须在B07逐项往返证明。

## 3. 语义与预算

decimalPG numeric(p,s)明确范围/舍入；SQLiteexact TEXT只承诺往返，不能默认数值排序/SUM；跨库money用固定scale checkedInt64。NULL、空值、missing mutation field分开；C# NRT不能替代runtimeNULL检查。JSON按wiretext/bytes与显式静态JsonTypeInfo，不启动managed动态provider；自定义/开放类型未注册即拒绝。

D14定义96byte header、16byte列描述和24byte cell、checkedoffset与owningbuffer。Rust每fetch有row/bytes双上限，C#decode持有batchowner直到完结；异常/早停释放一次，不逐cell过FFI、不将当前行borrow跨MoveNext。超inline batch大BLOB走独立chunkstream，不隐式突破预算。

SeaORM默认all/fetch_all可能一次收集全部，NW SessionExecutor用stream有界collect，RustModel/wire/C#DTO共存成本计费，allocator/providerbuffer/线程栈另测。logicalbudget不冒充RSS硬上限。

## 4. 原对照仍可追溯

Npgsql PgTimestamp ticks/10、DateTime Kind/Infinity、Guid big-endian实现及测试源码均保留；DapperAOT AsyncQueryState数组和reader释放、NpgsqlReader消费/发送协调也保留。它们不证明SQLx所有codec相同，且本轮这些测试未执行。R24实际SQLiteprobe的decimal TEXT/整数溢出是参考语义反例，不是Rustcodec实测。

## 5. schema与迁移

schemahash含逻辑/存储类型、precision/scale、nullability、key/relations/codec；modelbuildhash另含generatedquery与依赖/target。Rust迁移ledger有ID/hash/from/to/provider/transactionmode；并发迁移互斥，DDL与ledger同事务或明确不可事务恢复步骤。SeaORMschema-sync能力不自动授权生产改变liveDB，普通连接打开不得隐式迁移。

B07类型property/differential、恶意长度/UTF8/NULL/日期极值/decimal/Guid；B06stream/COPY/partialbatch/constructor error/consumerbreak；B08hash漂移/半迁移/权限/互斥；B12完整RustProjection→wire→C#AOTDTO。SQLxnumeric/所有datetimefeatures/SQLiteVM/迁移实现仍未全读，研究partial，不伪造全矩阵验证。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R22-C01 | [src/Npgsql/Internal/Converters/Temporal/PgTimestamp.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/Converters/Temporal/PgTimestamp.cs#L1-L44) | [[1, 44]]; source-observed; reader=database_design |
| R22-C02 | [src/Npgsql/Internal/Converters/Temporal/DateTimeConverterResolver.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/Converters/Temporal/DateTimeConverterResolver.cs#L1-L120) | [[1, 120]]; source-observed; reader=database_design |
| R22-C03 | [src/Npgsql/Internal/Converters/Primitive/GuidUuidConverter.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/Converters/Primitive/GuidUuidConverter.cs#L1-L25) | [[1, 25]]; source-observed; reader=database_design |
| R22-C04 | [test/Npgsql.Tests/Types/DateTimeTests.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.Tests/Types/DateTimeTests.cs#L245-L281) | [[245, 281]]; test-source-observed; reader=database_design |
| R22-C05 | [src/Npgsql/NpgsqlDataReader.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataReader.cs#L238-L259) | [[238, 259], [357, 378], [500, 521], [593, 614], [952, 973], [1033, 1054], [1077, 1227]]; source-observed; reader=database_design |
| R22-C06 | [src/Dapper.AOT/Internal/AsyncQueryState.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/Internal/AsyncQueryState.cs#L15-L54) | [[15, 54], [76, 116]]; source-observed; reader=database_design |
| R22-C07 | [src/Npgsql/NpgsqlDataSourceBuilder.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataSourceBuilder.cs#L140-L225) | [[140, 225]]; source-observed; reader=database_design |
| R22-RU01 | [src/executor/select.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/select.rs#L266-L324) | [[266, 324], [869, 925]]; source-observed; reader=/root/database_design |
| R22-RU02 | [src/driver/sqlx_postgres.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_postgres.rs#L180-L275) | [[180, 275], [828, 898], [328, 354]]; source-observed; reader=/root/database_design |
| R22-RU03 | [src/driver/sqlx_sqlite.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_sqlite.rs#L155-L254) | [[155, 254], [311, 337]]; source-observed; reader=/root/database_design |
| R22-RU04 | [sqlx-postgres/src/types/uuid.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/types/uuid.rs#L1-L38) | [[1, 38]]; source-observed; reader=/root/database_design |
| R22-RU05 | [sqlx-sqlite/src/types/uuid.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/types/uuid.rs#L1-L86) | [[1, 86]]; source-observed; reader=/root/database_design |
| R22-RU06 | [sqlx-postgres/src/types/chrono/datetime.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/types/chrono/datetime.rs#L1-L112) | [[1, 112]]; source-observed; reader=/root/database_design |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
