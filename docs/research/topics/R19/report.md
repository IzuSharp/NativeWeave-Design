# R19 — PostgreSQL Rust驱动与managed对照

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `ff0d0303b2b0a58d8d9b7e07b89eecc807af79dd62c3c057a2ff50a504f5e019`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 当前决定：Rust PostgreSQL，不再默认 managed provider

DB-D004选择SeaORM2.0.4作为Rust ORM、SQLx0.9作为PG驱动与池，C#只保留公共API/请求/DTO。原Npgsql默认路线因用户明确边界被superseded，Npgsql深读仍有价值但只作对照。这里不是根据未经执行的基准宣称Rust更快；Rust后端/ORM是既定产品方向，性能由B23同负载测量。

## 2. 实际调用链与适配点

SeaORM Entity查询/ActiveModel→SeaQuery Statement→ConnectionTrait→SQLx query_with + SqlxValues→PG connection→QueryResult→Rust Model/Projection。已读SeaORM PG driver默认每条execute/query acquire一个pool connection；因此直接包装DatabaseConnection不能实现DataSession固定lease。公开ConnectionTrait/StreamTrait及PgRow/PgQueryResult的From转换提供可用扩展点。

选择Rust SessionExecutor持有PoolConnection，实现这些公开traits并受单active-operation gate约束。关系/模型/SQL仍归SeaORM；只实现薄执行与所有权适配，不复制数据库协议。TransactionTrait关联类型有固定点要求，v1普通nested begin明确拒绝，显式savepoint独立定义。此组合尚未编译，B04/B05必须以真实Entity查询/事务/stream fixture验证Send/borrow/trait约束。

SQLx PG TransactionManager的begin排命令并等ReadyForQuery、维护depth；commit/rollback调用后失败不能推断旧effect没有发生。池close保留permit；Drop可spawn清理；取消/早停需保持connection到协议安全，不把Task取消当池可重用。

## 3. 与Npgsql比较所得的具体约束

Npgsql PoolingDataSource的容量/等待取消/坏连接与generation剔除是真实实现。Connector受控延迟reset可以将清理排入下一次发送，因此“尚有待发维护消息”不能一概叫协议污染；未知用户结果/未归属字节/并发发送则不同。其取消请求发送成功不是取消完成。DataReader Close消费余结果并等待发送任务，支持不能跳过清理的决定。

Npgsql动态JSON/tuple/unmapped API的裁剪限制和SlimDataSourceBuilder的AOT小例子说明逐特性验证的重要性；不能把一个例子当全库AOT证明。这些文件只读未运行，不进入默认NuGet依赖。

## 4. 取消、错误与资源

本次没有从SQLx已读公开接口证明Npgsql式即时CancelRequest能力，v1只承诺取消请求：入线前可拒绝，运行中用声明的statement_timeout/受控结束策略，最终结果以真实执行为准。任何未来remote cancel实现必须单列后端身份/代际/新操作竞态，不凭空命名API。

SessionExecutor不照抄query_all的fetch_all；用stream逐行计费、有界收集。未知损坏用公开close/close_on_drop剔除，close_on_drop只是意图；D15分别记录effect、connection disposition和local cleanup。COMMIT入线之后无确认返回Unknown，恢复标识不要求保活native pointer。

## 5. 版本、成本及验证

固定SeaORM2.0.4与SQLx0.9研究pin，实际crate checksum/Cargo.lock/features/TLS/RID仍由B02/B04/A13落地。普通应用不写Rust，但schema专属native包需由SDK/CI编译。B02必须测试TLS/认证/参数/NULL/长语句/取消/断线/协议清理；B04固定lease、parent lifetime、stream先drain；B05commit应答丢失；B23同SQL/事务对比纯RustSeaORM与完整FFI，managed对照仅测试依赖。Windows/Linux真实AOT运行仍pending。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R19-C01 | [src/Npgsql/PoolingDataSource.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/PoolingDataSource.cs#L100-L356) | [[100, 356], [445, 455]]; source-observed; reader=database_design |
| R19-C02 | [src/Npgsql/Internal/NpgsqlConnector.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/NpgsqlConnector.cs#L2075-L2258) | [[2075, 2258], [2706, 2810], [2936, 2993]]; source-observed; reader=database_design |
| R19-C03 | [src/Npgsql/NpgsqlDataSourceBuilder.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataSourceBuilder.cs#L140-L225) | [[140, 225]]; source-observed; reader=database_design |
| R19-C04 | [test/Npgsql.NativeAotTests/Program.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.NativeAotTests/Program.cs#L1-L20) | [[1, 20]]; test-source-observed; reader=database_design |
| R19-C05 | [test/Npgsql.Tests/PoolTests.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.Tests/PoolTests.cs#L47-L143) | [[47, 143]]; test-source-observed; reader=database_design |
| R19-C06 | [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/pool/connection.rs#L130-L163) | [[130, 163], [195, 225], [271, 369]]; source-observed; reader=database_design |
| R19-C07 | [LICENSE](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/LICENSE#L1-L18) | [[1, 18]]; license-text-observed; reader=database_design |
| R19-C08 | [LICENSE-MIT](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/LICENSE-MIT) | 定位见evidence; license-text-observed; reader=database_design |
| R19-V1 | [refs/tags/v10.0.3](https://api.github.com/repos/npgsql/npgsql/git/refs/tags/v10.0.3) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R19-RU01 | [Cargo.toml](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/Cargo.toml#L1-L195) | [[1, 195]]; source-observed; reader=/root/database_design |
| R19-RU02 | [src/database/connection.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/connection.rs#L1-L88) | [[1, 88], [167, 251]]; source-observed; reader=/root/database_design |
| R19-RU03 | [src/driver/sqlx_postgres.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_postgres.rs#L180-L275) | [[180, 275], [828, 898], [328, 354]]; source-observed; reader=/root/database_design |
| R19-RU04 | [sqlx-postgres/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/transaction.rs#L1-L102) | [[1, 102]]; source-observed; reader=/root/database_design |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
