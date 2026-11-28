# Validation, observed results and remaining gates

Status: bounded research evidence for `Korda-Orm-01`, observed 2026-11-28.
No Korda.Orm product code was implemented, published or accepted. Research projects,
upstream checkouts, generated files, binaries and logs remain on the execution
machine outside both document repositories. This document retains conditions,
results, limits and reproduction methods rather than raw execution material.

## 1. Evidence levels

| Level | What it establishes | What it does not establish |
| --- | --- | --- |
| Fixed-source review | Behavior visible in the cited file/symbol at the pinned commit | Unread commercial code, a complete upstream audit or tests being run |
| Pure SQL oracle | SQL/binding behavior of the selected jOOQ cases | C# equivalence or correctness on every server |
| Research native consumer | A specified small program compiles and runs with AOT | Product APIs, package compatibility or all feature families |
| Database experiment | Behavior of specified SQL/data/provider/version combinations | All dialects, concurrency, cancellation or performance parity |
| Document checks | Schema, references, dependency DAG and diff routing | Product, database, AOT or benchmark acceptance |
| Future product acceptance | The implemented feature's declared matrix actually passes | Capabilities outside its explicit profile and test scope |

## 2. Environment and source pins

The C# experiments used Debian 13 Linux x64, SDK **11.0.100**, runtime **11.0.0**
and **C# 15**. The SDK archive was downloaded from Microsoft's release metadata
and its published SHA-512 verified before extraction to an isolated local toolchain.
GCC 14 and the installed system linker/zlib development files were sufficient for
the tested Native AOT publishes with `CppCompilerAndLinker=gcc`.

The [official release page](https://dotnet.microsoft.com/en-us/download/dotnet/11.0)
and [release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/11.0/releases.json)
identify the SDK/runtime baseline. The installed SDK reported the same version.
The reviewed upstream repositories/tags/full commits are recorded in
[upstream-policy.md](upstream-policy.md) and [execution-aot.md](execution-aot.md).
No mutable `main` source was silently substituted for those release pins.

Java used OpenJDK **21.0.13.1**, jOOQ **3.21.10**, R2DBC SPI **1.0.0.RELEASE** and
Reactive Streams **1.0.4** from Maven Central. The Java SQL-only probe used no JDBC
driver, connection or server. Python's SQLite module reported **3.53.1**; the
Microsoft.Data.Sqlite native runtime separately reported **3.53.4**. These are
different executions and must not be conflated into one SQLite version.

## 3. Actual research experiments

| ID | Experiment | Observed result | Scope limit |
| --- | --- | --- | --- |
| EXP-JOOQ | Four-dialect SQL-only jOOQ source-file program, optional predicate true and false | 34 assertions per run, 68 across two runs, passed | Selected render/bind cases only; not the unavailable upstream regression suite |
| EXP-JOOQ-SQLITE | Execute actual jOOQ SQLite output against an in-memory SQLite 3.53.1 database | Five semantic assertions passed | SQLite only; Java output, not C# output |
| EXP-CSHARP | Pure C# typed query/renderer prototype, no database or driver references, published Native AOT | Both runtime predicate branches executed; 11 assertions in each run passed; native ELF verified | Small illustrative node set; does not implement the complete proposed contracts |
| EXP-CSHARP-NEGATIVE | Compare `Field<int>` with `Param<string>` in the prototype | Build failed with CS1503, as intended | One type-safety case, not the entire public API overload matrix |
| EXP-CSHARP-SQLITE | Execute the C# native program's two emitted SQL shapes with bound values on SQLite 3.53.1 | Two row-set assertions passed, including quoted identifier and apostrophe-bearing value | Exact small fixture only; not a full jOOQ/C# differential corpus |
| EXP-GENERATOR | Real `IIncrementalGenerator`: offline AdditionalFiles schema to typed columns/record, consumed in Native AOT | Publish exit 0 without warnings; eight runtime assertions passed; dynamic code unsupported | Tiny schema whitelist and one SDK-host configuration |
| EXP-GENERATOR-NEGATIVE | Unsupported schema field type and mismatched generated-column comparison | Expected KO001 and CS0411 compile failures, respectively | Both had secondary cascading diagnostics; no claim that every diagnostic was a Korda diagnostic |
| EXP-DAPPER | Runtime SQL, statically known arguments/DTO, Dapper 2.1.100 + Dapper.AOT 1.1.0 + Microsoft.Data.Sqlite 11.0.0 | Native publish/run succeeded; two dynamic shapes returned 3/2 rows, matched direct driver rows; nullable result and fixed QuerySingle passed | SQLite, known CLR shapes and selected supported overloads only |
| EXP-DAPPER-NEGATIVE | Replace fixed QuerySingle with a CommandDefinition overload; promote DAP057 to error | Publish failed with DAP057 as intended | Detects that unsupported call site; not proof of every possible silent fallback |

### 3.1 Reproduce the jOOQ cases

Use the listed Maven artifacts and Java source-file launch (`java --class-path '*'
OracleProbe.java true`, then `false`) in a temporary directory. Recreate these
maintained semantic cases using the pinned jOOQ APIs:

1. For POSTGRES, SQLITE, MYSQL and MARIADB, select `book.id, book.title` with `id > 10` and an
   optional `title = "needle"`. Assert binding occurrences `[10, "needle"]` or `[10]`.
2. Reuse one parameter value 7 in two predicates and assert `[7,7]`. Separately use
   two parameters with the same logical name but values 7/8 and assert `[7,8]`.
   Named rendering must preserve the requested parameter name.
3. Project `row(NULL::integer, 1).isNull()`, `.isNotNull()` and `.isNull().not()`;
   assert the emitted parameter order, including repeated NULL/1 pairs.
4. Render `SELECT 10 UNION (SELECT 20 EXCEPT SELECT 30)` and verify binding order
   `[10,20,30]` and nested-set behavior. Render explicit NULLS LAST and inspect
   the pinned dialect's native or lowered form.
5. Contrast PostgreSQL/MySQL RETURNING and MATERIALIZED behavior. Verify the
   PostgreSQL QUALIFY commercial-gate exception and an OSS parser binding example.

For SQLite execution, create `book(id INTEGER NOT NULL, title TEXT)` and insert
`(9,"needle"), (11,"needle"), (12,"other"), (13,NULL)`. Execute the actual rendered
SQL with its ordered values. Expect id 11 with the title filter and 11/12/13
without it; mixed-row predicates return `(0,0,1)`; the nested set returns 10/20;
explicit NULLS LAST orders NULL after non-null values.

These are observations of upstream behavior, including behavior Korda deliberately
rejects. A jOOQ clause omission is not a positive Korda acceptance case.

### 3.2 Reproduce the pure C# feasibility slice

Create a disposable `net11.0` console project with `LangVersion=15.0`, nullable
enabled, `PublishAot=true`, `TreatWarningsAsErrors=true`, invariant globalization
and `CppCompilerAndLinker=gcc`. It uses BCL immutable arrays, a string builder and
typed `Field<T>`, `Column<T>`, `Param<T>` nodes, equality/AND/IS NULL/IN nodes and an
immutable SELECT record. There are no database package references.

Render SQLite named placeholders and PostgreSQL numbered placeholders, appending
typed parameter occurrences during the same traversal. A command-line switch
adds an optional string predicate. Check query snapshot isolation, quoting,
parameter-value exclusion from SQL, occurrence order, empty IN, explicit IS NULL,
equality to a NULL parameter, unsupported SQLite FOR UPDATE and 100 concurrent
renders of the same immutable query. The concurrent loop is one aggregate check.

Use the installed SDK in a local directory:

```sh
dotnet publish -c Release -r linux-x64 -o out /p:UseSharedCompilation=false
./out/OrmProbe
./out/OrmProbe --filter
dotnet build -c Release -p:DefineConstants=NEGATIVE /p:UseSharedCompilation=false
```

The last invocation enables `id.Eq(new Param<string>("wrong type"))` and must fail
with CS1503. The successful binary is a native x86-64 ELF; its inspected dynamic
dependencies were the normal C runtime/math/linker, not CoreCLR or database drivers.

For database semantics, use `items(id INTEGER NOT NULL, "na""me" TEXT)` with
`(1,"O'Reilly"), (1,"other"), (2,"O'Reilly")`. Execute the actual native program's
emitted SQL, binding id=1 and, when enabled, the name `O'Reilly`. Expect 2/1 rows.

The prototype embeds values in its small parameter objects to keep the experiment
bounded. It does **not** implement the final value-free `RenderedTemplate`/
per-invocation argument split, the complete SQL type system or every jOOQ lowering.
Those are explicit subsequent product gates rather than claims inferred from AOT.

A brief allocation sanity check warmed up rendering 100 times, then rendered the
same small immutable query 1,000 times using `GC.GetAllocatedBytesForCurrentThread`.
It observed **704 bytes per render** in both runs. This confirms that a simple
implementation is not allocation-free; it is not a performance baseline, an
optimization target, a statistical benchmark or a comparison with jOOQ/Dapper.

### 3.3 Reproduce offline generation

Create an incremental generator that reads this AdditionalFiles input:

```text
entity User
Id:int
Name:string?
Active:bool
```

Validate identifiers and a small type whitelist, then emit typed static column
descriptors and `User(int Id, string? Name, bool Active)`. Reference the generator
as an analyzer with `ReferenceOutputAssembly=false` from a separate native consumer.
Check generated property types/values, nullable value, column name/nullability,
typed comparison and `RuntimeFeature.IsDynamicCodeSupported == false`.

The observed generator targeted `net11.0` and referenced Roslyn assemblies from
the exact SDK; its runtime consumer did not depend on the generator or Roslyn.
This is a local host feasibility shortcut, not the final analyzer package target.
Run a publish with the same AOT properties and execute the binary. Append
`Money:money` to require KO001; separately pass a string to the generated integer
column comparison to require CS0411. Restore the valid fixture between negative
cases. Product work must additionally validate incremental invalidation, names,
schema evolution, deterministic output and actual supported IDE/analyzer hosts.

### 3.4 Reproduce Dapper.AOT execution

The detailed source and recipe are in [execution-aot.md](execution-aot.md).
Use the exact package versions in EXP-DAPPER, enable Dapper.AOT interception and
emit compiler-generated files for inspection. A non-inlined helper builds runtime
SQL with an optional `score > @threshold` clause. Parameters have statically known
`long minId`/`long threshold` members and the result DTO contains `long Id`,
`string Name`, `long? Score`. Execute both shapes in the native binary and compare
every field to a direct SqliteCommand using identical SQL and values.

Inspect emitted interceptors, the dynamic binder's `Include` branch and typed
`GetInt64`/`GetString`/`IsDBNull` reader code. A successful restore or an unchanged
vanilla Dapper call does not establish generation. Promote DAP057 to an error and
replace the fixed QuerySingle call with CommandDefinition for the negative case.

## 4. Required future product validation

The first product baseline must create a maintained operation corpus, not simply
copy these small research programs. For every implemented family, record the
pinned source symbol, intentional difference, typed input, profile, expected SQL
semantics, ordered parameter types/occurrences and result shape.

| Layer | Required coverage and independent execution |
| --- | --- |
| Type/API | Positive and negative compilation; overload/default/nullability cases; generated and manual metadata; API/XML baseline |
| Pure language | Scope/alias/correlation, NULL/3VL, row degree, grouping, windows, CTE/recursive references, DML constraints, snapshot concurrency |
| Pure renderer | Every claimed profile/operation pair, parameter ordering, repeated slot/name, quoting, list arity, unsupported/precondition failures |
| Differential | Equivalent query semantics against pinned jOOQ; normalize only irrelevant formatting/placeholder presentation, never NULL/order/cardinality differences |
| Database | PostgreSQL 18, exact tested SQLite runtime, then independently tested MySQL 8.4/MariaDB 11.8 profiles; real rows/errors/types/transactions |
| Provider/AOT | Supported scalar and advanced type paths; generated binder/projector; streaming early exit; cancellation/timeout; owned/borrowed connections; no reflection fallback |
| Package | Each exact nupkg consumed independently; dependency/native-asset/license closure; no unrelated driver; pure DSL has no database prerequisite |
| Compatibility | Public signatures/XML/examples, semantic lowering behavior, schema/generator format and package updates reviewed together |

Native AOT tests run the compiled executable locally and in selected Linux CI
jobs. A local developer uses the same checks without GitHub. Windows, macOS, other
architectures and clean-image/minimum-CPU testing are not claimed here; add their
authorized matrices before claiming support.

The four database families are not one interchangeable test. Tests for a provider
leaf do not run unrelated database services. A shared type/model change reaches
all actual consumers through the module registry. Each source generator has its
own compiler-host tests plus generated native-consumer tests; generator execution
itself is a build-host activity, not a Native AOT application requirement.

## 5. Performance method and acceptance boundary

Separate the following measured paths: query construction; validation/lowering;
SQL/layout rendering; cached-template value binding; direct-driver execution;
Dapper.AOT with the same driver; Korda execution of an already-rendered template;
and complete dynamic construction-to-materialization. Keep SQL, arguments,
projection, connection ownership, preparation, transaction, row counts and buffering
identical. Compare fixed and dynamic shapes separately.

Record wall-clock distributions, throughput, allocations and GC, CPU, cold startup
and native binary size when relevant. Use repeated independent runs, documented
warmup and an unchanged disposable database fixture. Include empty, single-row,
multi-row, nullable, wide and variable-list cases. Treat blocking SQLite and
networked asynchronous drivers as separate workloads. Do not infer server or
pooling behavior from an in-process microbenchmark.

Java jOOQ rendering is a semantic and engineering reference. JVM versus .NET AOT
timings are cross-runtime observations, not a controlled claim that a language or
engine is faster. No Korda-versus-Dapper performance comparison was executed in
this study. The 704-byte prototype observation establishes no production budget.

`ORM-PERFORMANCE` must establish explicit per-workload overhead/allocation budgets
and reproducible baselines before accepting an optimization or claiming near
Dapper.AOT execution. Freeze the comparison conditions and budgets before tuning;
report misses and rejected ideas. `ORM-ACCEPTANCE` cannot mark performance parity
or zero framework allocation complete from source review or these probes. Long
benchmark/profiling campaigns are explicit work, outside normal document/product CI.

## 6. Remaining limitations and next decisions

The research validates architectural feasibility slices, not their full product
composition. Remaining gates include the final typed command protocol, generated
Korda binders/projectors, complete semantic corpus, PostgreSQL/MySQL/MariaDB live
tests, advanced codecs, nested-result decoding, streaming/cancellation races,
package/analyzer hosting and controlled performance comparisons.

The reviewed jOOQ public tree does not expose the complete upstream integration
test suite. Commercial transformations and some older-version emulations are not
portable source inputs. The plan includes independent corpus construction and
explicit unsupported behavior. Parser/translator is an optional later slice.

These limitations do not require changing the selected pure C# architecture.
They define the implementation gates that must be passed before release claims,
product cutover or deletion of the old C++ implementation.
