# R23 — C#语法捕获与RustORM构建

- 日期：2026-11-12；执行者：database_design（真实协作子代理）。
- 状态：**partially_evidenced**；设计决定已有明确建议，正式接受需独立Review；产品实现与生产验收未完成。
- 输入：Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`；Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`。
- Task packet：revision0.1.1，SHA-256 `fa138a96a5ee3e9cb94071783be1bd5070b0cd1057207af92848ad4082cec221`；不伪造后续packet修订为本次原始输入。
- 当前需求：Rust Database + Rust ORM必须；C#只上层语法/请求/API/DTO。旧managed默认决策明确superseded，已有源码观察和实际实验保留。
- 逐结论：[evidence.json](evidence.json)；实际/未读范围与真实reader：[coverage.json](coverage.json)。完整fetch不等于完整阅读。

## 1. 定案：C#自然语法，Rust ORM权威

原C#生成SQL/自有ORM runtime方案因用户要求superseded。Q13当前决定是C#只捕获语法与类型并编码请求，Rust同一validator解释语义并生成SeaORM模型/handler，C#SG再消费manifest生成薄facade和DTOdecoder。Task/async/generic/LINQ体验保持；普通开发者不写Rust，但schema/query改变需要SDK/CI native编译。

## 2. 真实接管与sourcegenerator约束

QueryDefinition的Where/Select/Join等是C#编译绑定的声明pattern，不是IEnumerable/IQueryableruntime，声明方法不会被业务执行。WeaveQuery把声明绑定public partial执行方法；未支持symbol/闭包/方法/未闭合generic/缺manifest时不生成实现并报error，C#本身也阻止缺partial实现。不能用throw-stub当成功，也不暗中client evaluate。

EFQueryCompiler的dynamiccode/QueryNotPrecompiled分支、DapperAOT拦截器skip分支只证实有限机制，不证明全库不可AOT；它们支持每声明覆盖记录需求。Roslyn additive/unordered/看不到其他SG输出约束由R06/root实际读取，本evidence保留真实reader；不能QuerySG产JsonSerializable或LibraryImport后期待另一SG本轮读到。

## 3. 双侧build为何必要

SeaORM EntityTrait绑定Model/ActiveModel/Column/Relation/PrimaryKey的Rust静态类型；它的codegen compact writer和fixture确实生成DeriveEntityModel、FK/Relation/Related。runtimeCondition并不能运行时发明未知Rust实体。因此采用schema-specificnative module，commonengine和generatedRustmodels静态链接，不跨RustDLL对象。

B10 SDK prebuild在CoreCompile前提取用户已提交C#源和显式manifest→B09/B11RustCLI验证/生成→A13Cargo锁定native产物→C#单一incrementalSG消费已存在manifest生成所有helpers。另一个SG本轮才生成的实体需提供预阶段普通Compile输入，否则明确NWQ0014。用户代码不在build执行，RustCLI可离线用checked-inschema，不生产联网猜库结构。

## 4. 失效、snapshot和diagnostic

原始query/span→requestnode→Rustdiagnostic保持映射。C#symbol identity/nullable/overload/转换/readonlyargs按准确语义捕获，不凭Where方法名猜；时间随机外部闭包先作为args。入口第一个await前snapshot，流方法非iteratorwrapper立即snapshot后首次MoveNext开nativecursor；迟到输入变更不影响请求，latecancel必须按native代际排空。

manifest覆盖schema/query/projection/profile/codec/target/Cargo.lock/nativehash。新增实体/投影/静态query必重建；已登记动态条件无需新Rust类型。缺Rusthandler/错旧artifact应build/load fail，不能仅靠整数ID碰巧一致。C#SG只生成encoder/decoder，SQL与最终参数budget全部Rust。

## 5. 验证义务

B10语法正负fixture/诊断IDspan/SG不可见/跨assembly/闭合generic/删除generator失败；B11真正RustEntity/ActiveModel/Relation编译执行，不仅文本golden；B12wire/DTO异常清理；A13跨机器输入hash/相关失效/产物打包；B22win/Linux真实AOT。所有代码片段design-draft，C#/Rust双阶段还未编译；该剩余义务不要求继续向用户询问常规选型。

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R23-C01 | [src/EFCore/Query/Internal/QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs#L60-L115) | [[60, 115], [134, 156]]; source-observed; reader=database_design |
| R23-C02 | [src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs#L53-L74) | [[53, 74], [207, 236], [515, 543]]; source-observed; reader=database_design |
| R23-C03 | [src/Dapper.AOT/Internal/AsyncQueryState.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/Internal/AsyncQueryState.cs#L15-L54) | [[15, 54], [76, 116]]; source-observed; reader=database_design |
| R23-C04 | [License.txt](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/License.txt#L1-L10) | [[1, 10]]; license-text-observed; reader=database_design |
| R23-C05 | [docs/features/incremental-generators.cookbook.md](https://github.com/dotnet/roslyn/blob/b907b90240f9f22873227aa510794dd280d61f57/docs/features/incremental-generators.cookbook.md) | [[1, 230]]; cross-task-source-evidence; reader=/root; source task=R06 |
| R23-V1 | [refs/tags/1.1.0](https://api.github.com/repos/DapperLib/DapperAOT/git/refs/tags/1.1.0) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R23-RU01 | [src/entity/base_entity.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/base_entity.rs#L65-L135) | [[65, 135]]; source-observed; reader=/root/database_design |
| R23-RU02 | [sea-orm-codegen/src/entity/writer/compact.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/src/entity/writer/compact.rs#L1-L159) | [[1, 159]]; source-observed; reader=/root/database_design |
| R23-RU03 | [sea-orm-codegen/tests/compact/fruit.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/tests/compact/fruit.rs#L1-L39) | [[1, 39]]; test-source-observed; reader=/root/database_design |

所有新C#/Rust接口均design-draft、未编译；source/test-source与跨任务源码证据不是执行结果。此前R24的Python/SQLite实验范围及原始hash不变。精确缺口转入现有B任务，不新增元规划体系。
