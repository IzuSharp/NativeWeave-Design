"""One-time, preimage-checked documentation continuation for existing PR #5.
No product source, license, protection or main-branch changes.
"""
from pathlib import Path
import hashlib,json,subprocess
D=Path.cwd()
BASE='baa953772d2a771bb4da3aff0cf4b4be6fc811a1'
PATHS=['AGENTS.md','README.md','docs/database/drivers.md','docs/database/transactions-and-pooling.md','docs/verification/reference-application.md','docs/server/hosting-and-streaming.md','docs/requirements/charter.md','docs/architecture/candidate-boundaries.md','docs/requirements/coverage-matrix.md','docs/research/source-catalog.md','docs/traceability/open-questions.md','docs/contracts/registry.json']
for name in PATHS:
    if (D/name).read_bytes()!=subprocess.check_output(['git','show',BASE+':'+name]):
        raise SystemExit('Preimage drift; reconcile instead of overwriting: '+name)
def put(p,s):
    t=D/p;t.parent.mkdir(parents=True,exist_ok=True);t.write_text(s.strip()+'\n')
def edit(p,fn):put(p,fn((D/p).read_text()))
p='docs/database/drivers.md';old=(D/p).read_text()
wire=old.split('### 4.1 db-wire/1 数据格式\n')[1].split('## 5.')[0].split('动态 request IR 使用另一个 payload_kind')[0]
wire=wire.replace('schema_hash','metadata_hash')
retained=old.split('## 5. 类型语义与 Rust 数据库 codec')[1].split('## 9. 迁移、包装与版本')[0]
for a,b in {
 'row→SeaORM Model/Projection':'row→显式结果projection',
 'Rust schema/driver':'Rust metadata/driver','Rust schema映射JSON列':'Rust metadata映射JSON列',
 '生成Rust显式类型/转换与数据库声明':'预编译能力内的显式整数/文本映射；新增native codec另发Engine版本',
 'SQLx/SeaORM':'SQLx / NativeWeave Rust adapter',
 'SQLx rows、SeaORM Model/Projection、wire buffer和C#DTO':'SQLx rows、wire buffer和C#DTO',
 'ORM模型映射和async-trait boxed future':'结果转换和必要async适配',
 '选定 SeaORM SQLx SQLite 路线':'普通路线使用Rust SQLx SQLite adapter',
 'Rust SQLx PgPool/connection执行参数化SeaORM Statement':'Rust SQLx PgPool/connection执行SeaQuery构建的参数化语句',
 '生成SQL及sea_query_sqlx::SqlxValues走同一ownership路径':'生成SQL及显式fallible参数binder走同一ownership路径；不得丢弃Arguments::add错误或对unsigned窄化unwrap',
 '已验证Rust lowerer输出':'经过能力/类型检查的Rust SeaQuery输出',
 '初始保护值：':'以下数值是可配置设计起点，不是已测得的容量或性能结论：'
}.items():retained=retained.replace(a,b)
put(p,'''# D14 — Rust Database Engine and precompiled application boundary

Contract: **C-DB-001@0.2.0-draft**. Status: proposed; independent review pending. Supersedes DB-D004/DB-D005/DB-D006's ordinary SeaORM model-build assumptions, not the historical source facts. Evidence: [R25](../research/topics/R25/source-driven-seaquery.md), [recovered prototype](../research/source-driven-evidence/README.md), existing R19–R22. Transaction safety remains [D15](transactions-and-pooling.md).

## 1. Architecture and selection

Database lower layers are mandatory Rust. After comparing dynamic SeaQuery and static SeaORM, the default implementation candidate is a maintainer-precompiled **SeaQuery 1.0.2 + SQLx 0.9.0** Engine. SeaQuery owns native query construction and dialects; SQLx owns execution, connections, pools and protocol. NativeWeave's Rust Adapter supplies bounded admission, fallible codecs, capability checks, transaction/cleanup coordination and explicit ORM policies. C# supplies business types, typed Fluent calls, static metadata/DTO code and interop; no C# SQL dialect engine or managed-provider fallback.

Static SeaORM Entity/ActiveModel/Relation integration remains a specialized profile with a separately compiled model package. Its build coupling is not a universal property of Rust database access. Ordinary Student/User entities using supported codecs/operators vary as runtime metadata and C# code, not generated Rust. No Cargo or CI-built application Engine is required on that path. New native codecs/operators/providers can require a new maintainer Engine version.

Core has no SQL AST, pool or mandatory global Tokio runtime. Managed drivers remain external comparisons. Source reuse and consumer experience justify this candidate; no performance superiority or independent acceptance is claimed.

## 2. Modules and implementation boundaries

B01 owns domain interfaces/descriptors/limits/errors and the typed C# facade, never a managed product provider. B02/B03 implement Rust PostgreSQL/SQLite adapters. B04 is the required native host, resource admission and runtime/session/pool ownership. B05/B06/B07 own native transactions, bounded streams and fallible codecs. B08 owns Rust migration execution with a C# administration surface. B09/B10 own thin binding metadata and optional static C# generation. B11/B12/B13/B14 own native query/binding, DTO materialization, runtime Fluent composition and explicit Rust relation/CAS policies.

Use disjoint implementation scopes and versioned driver fixtures. Do not create a host/provider cycle or wait for the entire ORM before implementing independent codecs. B21/B22 verify the actual combined implementation.

## 3. Public API and ownership

Draft application shape, **not compiled product API**:
```csharp
await using WeaveDataSource source = DataSources.Postgres(options);
await using DataSession session = await source.OpenSessionAsync(ct);
using var query = session.From(Students.Table);
query.Select(Students.Row).WhereGe(Students.Age, minAge).Take(100);
IReadOnlyList<Student> rows = await query.ToListAsync(ct);
```
The recovered experiment executed a narrower synchronous static-descriptor API. DataSource owns its Engine-local runtime/pool; Session holds one physical connection lease. Transactions/cursors/operations retain parent owners. A Session admits at most one user command/reader/COPY at a time, rejecting concurrency rather than silently changing transaction order. Cleanup admission is independent of the closed public gate.

SafeHandle lifetime protection is separate from the mutable builder's single-writer gate. Sealing freezes query shape and parameter snapshots. Native streams remain inside native async operations that hold connection ownership; do not transmute lifetimes to manufacture a self-referential FFI cursor. Disposal cannot invalidate in-flight callbacks/results.

CloseAsync(deadline) stops admission and waits for retirement up to the deadline. Pending cleanup retains roots, owners and budgets; DisposeAsync joins actual safety. A bounded HTTP path must not follow Pending close with an unconditional indefinite await-using join. Public task outcome, native retirement, connection reuse and remote transaction effect remain separate.

## 4. ABI and operation lifecycle

Consume existing lifetime/callback/async/error contracts and the eventual accepted ABI/buffer layouts. Do not export Rust Vec/String/Expr/Value/traits or CLR layouts. Native modules remain alive while objects/operations/callbacks/buffers can use them. Instance close is not module unload.

Operations cover datasource/session open, builder create/mutate/seal, execute, cursor fetch, transaction begin/commit/rollback and close/drain. Async operations retain create→start, terminal notification, exactly-once take_result and separate retirement. Cancellation requests cannot block on a SQLite lock, channel send or network action. SafeHandle release is not an I/O join.

Direct native-builder calls are the reference route. Batched native operations are a measured optimization candidate requiring bounded validation and partial-mutation failure semantics, not a predetermined universal IR. Expert raw SQL is a separate parameterized capability; never silently fall back to it.

Metadata hashes identify runtime table/column/projection declarations and cache content, not entities compiled into a schema-specific library. Validate enabled native codecs/operators and actual metadata/database compatibility. New application metadata does not by itself change the native Engine binary.

### 4.1 db-wire/1 result and parameter candidate

'''+wire+'''

This retained header is a candidate value/result transport, not a frozen query-operation protocol. Its metadata_hash meaning supersedes compiled-entity inventory semantics and requires explicit compatibility versioning. Native builders may use direct typed ABI methods instead. Reject unknown required versions/tags, oversized allocation, overlapping payload regions, malformed UTF-8 and profile mismatch before submission. B09 compares representations without reimplementing SQL semantics.

## 5. 类型语义与 Rust 数据库 codec
'''+retained+'''

## 9. Migration, precompiled packages and compatibility

The Engine manifest binds ABI, capability/codec profile, RID, toolchain, locked dependencies and native asset hash. Application metadata, query shape and migration history are separately versioned; see D10. Ordinary entity changes require at most static C# metadata/DTO regeneration, never default Cargo. Registry crates and source commits retain separate provenance until checked.

Migrations are explicit Rust administrative operations, not speculative startup schema-sync. Immutable ID/content hash/provider/from-to version/transaction mode enter the ledger. PostgreSQL advisory locking or SQLite explicit writer/deployment admission serializes migration owners. Transactional DDL and ledger commit together; nontransactional DDL uses staged resumable checks. Same ID/different hash, missing migration, inadequate permission and incompatible schema fail explicitly. Destructive down-migration is not the production default.

## 10. Source-driven failure gates and acceptance

Reject SQLite row-lock/SELECT INTO/SEARCH-CYCLE requests that the pinned renderer silently ignores. Catching panic cannot detect omitted semantics. Check CTE shape and values before native rendering. A fallible argument binder propagates every encoding error and checks narrowing; do not use discarded add errors or unsigned unwrap. Poison unsafe partial builder mutations and retain all live owners.

B01/B04 verify malformed metadata/length/shape fuzzing, ABI/RID/capability rejection and no managed product provider. B02/B03 verify actual Rust PG/SQLite into typed batches/DTOs, schema errors, cancellation, stream early stop and pool/worker cleanup. B05/B06 verify Unknown COMMIT, unconfirmed rollback, reuse versus retirement, decoder exceptions and huge fields. B07/B08 cover every codec negative and migration interruption. B09–B14 cover typed native query parity, metadata/DTO generation and bounded relation/CAS scope. B21–B24 cover Windows/Linux AOT, faults/soak, clean no-Rust and RID-free consumers, unchanged native hash after entity changes, and full-workload costs.

The recovered Linux SQLite AOT experiment is real but finite. Its JSON/fetch_all/per-call-runtime/raw-handle shortcuts are not the production streaming/pool/concurrency design. Windows, PostgreSQL faults, production generator, async lifetime and hard resource bounds remain unverified. Never suppress IL2026/IL3050 indiscriminately to manufacture acceptance.
''')
# Preserve D15 safety dimensions while removing mandatory static SeaORM coupling.
p='docs/database/transactions-and-pooling.md';s=(D/p).read_text().replace('C-TX-001@0.1.0','C-TX-001@0.2.0-draft').replace('**review-ready**','**proposed；本修订待独立Review**')
a=s.index('选定SeaORM2.0.4');b=s.index('SQLx PoolConnection::close',a)
s=s[:a]+'''普通路径是预编译SeaQuery + SQLx Rust Engine；SQLx研究pin为v0.9.0 `75bc0487eb661da811bb7a3c5d158f1bd463fef4`。SeaORM固定源码保留为专用静态Entity profile证据，其trait/model编译耦合不是普通应用前置。

Rust SessionExecutor持有物理connection lease；B04定义可注入driver接口，B02/B03执行，B05协调事务/cleanup。SeaQuery构建SQL，fallible binder传播参数编码错误。借用transaction/stream局限在拥有连接的native async任务，不transmute越过生命周期。新增普通C#实体是runtime metadata；不跨动态库传SQLx pool/trait object/allocator owner。真实编译、PG/SQLite故障与并发门禁仍须执行。

'''+s[b:]
s=s.replace('本轮没有Rust adapter、实库故障或AOT运行证据。','本事务规范未取得生产adapter、PG故障及完整AOT证据；PR5有限Linux/SQLite查询原型不能替代这些验证。')
s=s.replace('## 1. 设计决定','> 旧packet与Review仅为原版本历史溯源，不能接受本次新内容hash。\n\n## 1. 设计决定');put(p,s)
# Reference-service correctness remains, application native build requirement changes.
p='docs/verification/reference-application.md';s=(D/p).read_text().replace('设计规范 0.1.0','设计规范0.2.0-draft；本修订待独立Review').replace('C-REFERENCE-001，0.1.0','C-REFERENCE-001，0.2.0-draft')
s=s.replace('C# Source Generator 捕获受支持语法、给出编译期诊断并编码版本化查询 IR','C#使用普通typed Fluent，SG可选生成static metadata/DTO与诊断')
a=s.index('数据库规范选用 Rust SeaORM 路线');b=s.index('\n',a)
s=s[:a]+'''数据库普通路径使用维护者预编译SeaQuery + SQLx Rust Engine。普通C#实体/投影/查询使用runtime metadata与static DTO，不生成Rust Entity、不需Cargo或CI才能本地运行。专用SeaORM模型包是另行构建的可选profile。应用metadata/schema、Engine ABI/capability、native hash分别验证；B21/B24验证Windows/Linux AOT、无Rust干净环境及无显式RID本地build/run。'''+s[b:]
a=s.index('常用列表要求调用者自然使用');b=s.index('\n',a)
s=s[:a]+'''常用列表使用自然typed C# Fluent；SG可选提供static metadata/DTO，SeaQuery负责native构建/方言，SQLx执行，显式关系/CAS政策留在Rust。动态过滤只能用已登记列/操作，native再次检查capability并参数化。分页`(created_at,id)`含唯一tie-breaker；独立ReadCommitted不承诺跨页snapshot。需要一致导出时使用明确snapshot/transaction profile、最长时限及stream lease，慢客户端不能永久占池。'''+s[b:]
s=s.replace('C# 最上层编码 typed query IR 与参数','C#最上层调用typed native-backed Fluent并绑定参数').replace('ExecuteCreateAsync编码typed IR','ExecuteCreateAsync调用typed native operations').replace('SQL/queryIR','SQL/查询操作描述').replace('最上层 LINQ/泛型/async/AOT','最上层Fluent/泛型/async/AOT');put(p,s)
p='docs/server/hosting-and-streaming.md';s=(D/p).read_text().replace('设计规范 0.1.0','设计规范0.2.0-draft；本修订待独立Review').replace('C-SERVER-001，0.1.0','C-SERVER-001，0.2.0-draft')
s+='''
## Source-driven native Server seam — D18 / B17

Reuse Hyper Service/Body/connection drivers, Tower/Axum routing and Tokio scheduling through one compiled ForeignService. C# handler IDs/routes are runtime registrations, not generated Rust per handler. Do not port the HTTP/TLS core into C# or treat Hyper's unstable client C FFI as a stable server ABI. Actix worker-affine and Pingora proxy-specific routes remain alternatives. Kestrel AOT remains the managed baseline; see [R27](../research/topics/R27/source-driven-server.md).

Tower's response-future permit does not cover response-body lifetime. A body/stream lease remains charged until body and callback retirement. Hyper H2 protocol credit does not reclaim Bytes retained by managed consumers; retained-byte accounting is independent. Tokio shutdown_timeout is not quiescence; Pending close retains roots, owners and budget.

Callbacks enqueue bounded dispatcher work, never block native polling on Task.Result or execute arbitrary application handlers synchronously in reverse callbacks. Complete native Future exactly once; ordinary application HTTP errors should become responses rather than unnecessary Service errors that abort a connection. TLS fatal errors stop reads, with separate handshake/TLS/application queue limits. B16/B17/B20/B22 test slow/aborted bodies, trailers, huge chunks, completion/cancel/close races, callback roots and pool-held database streams. The finite R27 model is not a production Server or performance test.
''';put(p,s)
edit('AGENTS.md',lambda s:s.replace('不新增默认 Rust runtime，不决定所有数据库或服务器必须使用 Rust，不引入 ArcForges 业务模型。','Core不新增默认全局Rust runtime；Database底层必须Rust，Server按证据选型；ArcForges只参考格式。源码驱动深度复用，普通C#实体不默认要求Rust重编译。'))
edit('docs/requirements/charter.md',lambda s:s.replace('版本 0.1.0','版本 0.2.0').replace('只有在生态能力、工程成本、可靠性或实测效率有具体依据时引入 Rust。','Database底层按最新澄清必须Rust；其他Engine按生态能力、成本、可靠性或实测效率选型。').replace('引入 ADR 必须有能力/成本/可靠性或工作负载证据','Database Rust是产品约束；其他Engine引入ADR须有能力/成本/可靠性或负载证据').replace('LINQ 风格静态代码生成','可选static metadata/DTO生成，不要求完整LINQ Provider').replace('无需让纯 C# provider 的独立研究等待无关 Rust 引擎完成','managed provider仅作独立源码/基准对照，不是产品数据库后端')+'''

## Source-Driven Deep Native Integration — clarified requirement

Study and reuse actual native structures, algorithms and lifecycle before designing the C# convenience layer. Prefer public APIs, but evaluate dedicated source-informed adapters, upstream extensions and controlled forks when justified. Never expose private Rust layout as ABI. Ordinary C# database entities/queries using enabled native capabilities consume maintainer-precompiled NuGet assets, without Cargo or a CI dependency for local execution. Typed Fluent is preferred over a full IQueryable/EF translator; no duplicate C# SQL engine. Optional generators supply static metadata/DTOs, not a mandatory runtime query compiler.

Preserve capability/error/ownership correctness, AOT and cross-platform acceptance. Compare native Server with Kestrel AOT, without presuming a winner. Source pins, locked closure, behavior/ABI/performance regression and patch retirement belong to D10/D11 and existing tasks. Research decisions, implementation verification and production acceptance are distinct.
''')
p='docs/architecture/candidate-boundaries.md';s=(D/p).read_text().replace('版本 0.1.0','版本 0.2.0-draft');a=s.index('## 6. Database');b=s.index('## 7.',a)
s=s[:a]+'''## 6. Database / ORM revised candidate boundaries

Database lower layers must be Rust; managed providers are comparisons only. The ordinary candidate uses precompiled dynamic SeaQuery AST/identifiers/values with SQLx execution. C# owns typed Fluent and static metadata/DTOs, not a SQL AST/dialect or full LINQ translator. Static SeaORM Entity remains a specialized profile; its native model-build coupling does not imply all Rust database integrations require per-entity compilation.

See ADR-0002, D14, D16/D17 and R25's source study. Direct native builder is the reference route; batching requires measurements, not a preselected universal IR. Explicit SQL null/collation/join/pagination and codec semantics remain mandatory. Reject SQLite silently omitted clauses and use fallible native binding. Unknown transaction effect, protocol reuse and local retirement remain independent.

'''+s[b:]
s=s.replace('ORM查询IR','native查询绑定').replace('本轮没有 C#/Rust 编译器和 Windows 实验结果。','恢复的Actions已有有限Linux/SQLite C#/Rust Native AOT实验；当前本地无相应编译器且无Windows结果，见source-driven evidence。')
s+='''
## 11. Source-driven Engine maintenance

[D11](../extension/engine-integration.md) defines public/source-informed/extension/fork integration. [D10](../platforms/build-package-release.md) separates maintainer native builds from ordinary C# consumption and specifies source/closure pins and upgrade differential gates. Core owns no domain SQL or Server state. These amended contracts remain proposed; previous reviews do not approve new hashes.
''';put(p,s)
for p in ['docs/requirements/coverage-matrix.md','docs/research/source-catalog.md']:
 edit(p,lambda s:s+'''

## Source-driven amendment / 2026-11-12

Existing IDs remain authoritative. R19–R25/D14–D17/B01–B14 cover native SeaQuery/SQLx, no managed fallback or per-entity Cargo, typed Fluent instead of full LINQ SQL translation. R26–R31/D18–D20/B15–B24 cover native Service/Body reuse and retirement budgets, retaining Kestrel AOT. R13/R14/R18/D10/D11/A13–A16/A22/A24 cover precompiled consumers, upstream mapping and controlled upgrades. See [impact/recovery record](../traceability/source-driven-impact.md). Partial source evidence does not complete all tasks.
''')
p='docs/traceability/open-questions.md';s=(D/p).read_text().replace('状态：open；2026-11-12。','状态：设计回答、实现验证、生产接受分别记录；2026-11-12。')
s=s.replace('| Q11 | Npgsql/SQLx/SQLite支持矩阵与Rust价值 | R19–R22 → D14/D15 | 功能等价AOT/负载/取消/恢复 | provider未最终选型 |','| Q11 | Rust动态数据库与预编译复用 | R19–R25 → D14/D15 | SeaQuery+SQLx候选及有限Linux AOT，无逐实体native构建 | 设计回答形成；独立接受/PG/Windows验证pending |')
s=s.replace('| Q13 | 可自然表达且可证明的LINQ/AOT子集 | R23/R25/R06 → D16/D17 | 支持/拒绝语法、调用接管、静态mapping | 不承诺任意IQueryable |','| Q13 | Typed Fluent及static metadata/DTO | R23/R25/R06 → D16/D17 | 普通native-backed Fluent，不要求完整LINQ Provider | 设计问题已回答；SG/全能力/跨平台验证pending |')
s+='''
## Scope of design answers and remaining verification

The Q11/Q13 questions “must every ordinary C# entity compile Rust?” and “must this be a full LINQ SQL Provider?” are answered **no for the dynamic profile** by R25 and ADR-0002. They no longer remain open language-feasibility questions. SeaORM's static-profile restrictions remain real but do not generalize to all native database access. Contracts still require independent acceptance.

Q01/Q09 have only explicit-RID Linux/SQLite NuGet/AOT and unchanged-native-hash evidence; Windows, clean Rust-free consumers and RID-free commands remain pending. Q14 retains SQL differential, silent-no-op rejection and fallible binder gates. Q15's Server benefit choice is not closed by source feasibility. Q16 has a finite response-body admission counterexample/model, not a verified network/memory/shutdown implementation. Q04/Q12's existing safety distinctions remain; design resolution does not erase implementation tests. Continue through existing R14/R17/R25/R27, D10/D11/D14–D18 and Plan's independent-review prompt, not a new graph.
''';put(p,s)
edit('README.md',lambda s:s+'''

## Source-driven integration continuation

Existing PR #5 continues the interrupted research. Read [ADR-0002](docs/decisions/ADR-0002-source-driven-native-integration.md), [SeaQuery](docs/research/topics/R25/source-driven-seaquery.md), [Server](docs/research/topics/R27/source-driven-server.md), [Engine integration](docs/extension/engine-integration.md), [precompiled build/maintenance](docs/platforms/build-package-release.md), and [impact/recovery](docs/traceability/source-driven-impact.md). The finite Linux SQLite AOT probe was recovered, not rerun or promoted to production. Database is mandatory Rust; supported ordinary entity changes reuse precompiled native assets. Lifecycle, transaction safety and independent review remain mandatory.
''')
# Registry hashes bind actual newly written bytes; none are accepted.
rpath=D/'docs/contracts/registry.json';r=json.loads(rpath.read_text())
updates={'C-BUILD-001':'docs/platforms/build-package-release.md','C-ENGINE-001':'docs/extension/engine-integration.md','C-DB-001':'docs/database/drivers.md','C-TX-001':'docs/database/transactions-and-pooling.md','C-QUERY-001':'docs/database/query-semantics.md','C-QUERYGEN-001':'docs/generators/query-generation.md','C-SERVER-001':'docs/server/hosting-and-streaming.md','C-REFERENCE-001':'docs/verification/reference-application.md'}
for c in r['contracts']:
 if c['id'] in updates:
  p=updates[c['id']];c.update(version='0.2.0-draft',status='proposed',spec_path=p,content_sha256=hashlib.sha256((D/p).read_bytes()).hexdigest(),specification_status='authored_proposed_independent_review_pending',author='recovery_session',reviews=[],reviewers=[])
  c['evidence']=['docs/research/topics/R25/source-driven-seaquery.md','docs/research/topics/R27/source-driven-server.md','docs/research/source-driven-evidence/README.md']
 for dep in c.get('dependencies',[]):
  if isinstance(dep,dict) and dep.get('id') in updates:dep['version']='0.2.0-draft'
r['note']='Existing IDs retained. Source-driven amendments are proposed; old reviews do not accept new bytes. Implementation and production validation remain separate.'
put('docs/contracts/registry.json',json.dumps(r,ensure_ascii=False,indent=2))
print(json.dumps({'changed_existing_documents':len(PATHS),'revised_contracts':list(updates),'independent_review':'pending','product_implementation_authorized':False}))
