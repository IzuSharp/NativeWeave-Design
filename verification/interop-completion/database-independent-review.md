# Independent database research and design review

Reviewer: `/root/interop_research`. Author of the reviewed domain:
`/root/database_research`. Date: 2026-11-13 UTC.

**Decision: accept the reviewed research/design scope. No unresolved blocking
finding remains.** This is an independent technical review by a separate delegated
agent. It is not a second GitHub account approval, a required-check bypass, or a
claim that future product implementation and release tests have passed. The root
integrator records formal task/contract acceptance against the exact hashes below.

## Frozen inputs and scope

The reviewed tasks are R19, R20, R21, R22, R23, R24, R25, R31 and D14, D15, D16,
D17, D20. The contract revision is 0.3.0. The final author manifest is
[`task-status.json`](../database-completion/task-status.json), SHA256
`3081f663362d51b3f836f57b4aa6052b2e8b1dbbd2fd061602addb52bd5e222a`.
All **41 input hashes** matched the actual files at final review. Their exact
map, this review's conclusions and supporting record hashes are in
[`database-independent-review.json`](database-independent-review.json).

The reviewer read all eight current research reports, all sixteen current
evidence/coverage records, both R25 architecture appendices, all five normative
specifications, the fixture source and runner, both fixture/evidence READMEs and
the source/CI manifests. Cargo.lock was parsed for pinned dependency identity;
this is not a claim of a line-by-line semantic review of a generated lock file.
Preserved historical evidence remains attributed to its original authors. This
review independently inspected the thirteen selected SQLx/SeaORM source files
listed in [`db-independent-source-review.json`](db-independent-source-review.json),
with exact commits, Git blob hashes, SHA256, actual line ranges and limits. It did
not reread every historical upstream source citation or execute upstream suites.

## Findings and resolution

| Finding | Severity | Original risk | Resolution verified |
| --- | --- | --- | --- |
| DB-IR-01 | Medium | An outer SQLite BEGIN IMMEDIATE around Migrator was underspecified. A literal raw SQL BEGIN bypasses SQLx transaction depth and makes Migrator issue an invalid nested BEGIN. | D14/D15/R20/R22 now name `Connection::begin_with("BEGIN IMMEDIATE")` then `Migrator::run(&mut *tx)`. They reject `no_tx` entries before admission, explicitly commit/rollback, preserve primary and cleanup errors and isolate cleanup failures. The reviewer executed three positive/negative regressions. |
| DB-IR-02 | Medium | R31 still allowed a NativeWeave Server example without the native Server asset, contradicting the user mission and current D20. | R31 now requires Rust Server for every NativeWeave Server product example; managed Kestrel/database paths are external comparisons only. |
| DB-IR-03 | Low | R31 and top-level evidence fields retained obsolete partial/unexecuted PostgreSQL conclusions despite current real SQLx/PG evidence. | The old snapshot moved to explicit historical fields; current scope is research complete pending independent review. Product implementation remains separate. |
| DB-IR-04 | Low | Two claimed source read ranges ended beyond actual EOF. | PG TLS now ends at line100 and PG migration at374; the reviewer checked every selected range against actual file length and identity. |
| DB-IR-05 | Improvement | Required SeaORM shape validation had no named public provider-row inspection seam. | D14/D17 now identify public `try_as_pg_row` / `try_as_sqlite_row` and SQLx columns/type_info, with row-owner lifetime and SQLite dynamic-type limitations. The reviewer read those public methods. |

All findings above are resolved in the frozen inputs. No fixture that already
passed CI was rewritten to hide a failure or claim new coverage. The newly added
independent regression is a separate fixture with its own input hashes and logs.

## Substantive architectural conclusions

The ordinary route is a maintainer-precompiled SeaQuery 1.0.2 + SQLx 0.9.0 Rust
Engine. C# owns strongly typed declarations, Fluent calls, static DTO construction
and the interop facade. Native SeaQuery owns its query structures/dialect renderers;
SQLx owns actual driver/protocol/pool execution. Normal entity changes using
supported codecs are runtime metadata and managed code, not application-specific
Rust Entity compilation. Neither a managed SQL compiler nor a mandatory global
Core runtime is introduced.

The SeaORM comparison is substantive. Its public dynamic ModelType/FieldType
projection can consume runtime schemas. Its static loader still requires
ModelTrait/EntityTrait and collects/group-maps native rows; those valuable native
algorithms are not falsely claimed to be inherited by a raw SQL call. The default
does not force SeaORM merely because it is named ORM. Static entities or a future
controlled dynamic extraction are explicit specialized capabilities. C# is not
assigned a new full ORM implementation.

The nullable projection defect is real: SeaORM's Option mapping treats
ColumnNotFound as None. The design therefore validates actual result names,
ordinals, duplicates and compatible type shape before nullable decoding. Public
provider-row access makes that preflight implementable without private fields or
a fork. Missing, SQL NULL, an unsupported type and an empty value remain distinct.

Transaction effect is separate from local task outcome, protocol cleanliness and
resource retirement. After COMMIT response loss, cleanup cannot turn Unknown into
Rollback. A closed admission gate does not prevent required cleanup. SafeHandle
retention does not grant mutable Rust aliasing; the connection/session gate and
parent owners remain mandatory. Stream early stop must drain or isolate before
reuse. The specs preserve cleanup errors while retaining the primary error.

The migration design reuses native checksum and apply/ledger behavior. The
reviewed SQLx Migrator can return early after obtaining the PostgreSQL session
advisory lock; a dedicated administrative connection is closed on error. SQLite
lock/unlock are no-ops, so the corrected tracked outer write transaction is
necessary. The tested public API chain preserves outer atomicity; it does not
replace cross-process/crash tests.

SQLx PostgreSQL's reviewed Execute limit is zero, so NativeWeave export batch
limits cannot be advertised as server cursor fetch limits or whole-process RSS
bounds. Logical permits count retained native and managed data separately from
uncontrolled upstream capacity and allocator/runtime overhead. The design is
honest about this limitation. Remote TLS requires VerifyFull; Prefer downgrade
and Require's certificate limitations are not presented as secure identity checks.

The reference application makes idempotency scope/key/hash and the business
effect/result/outbox atomic in one database transaction. Its PG conflict recovery
uses a subsequent statement snapshot; an empty same-statement CTE result cannot
prove no prior write. Unknown HTTP outcomes retain a recovery identity, and
outbox delivery remains at least once. Product examples use the required Rust
Server and Rust Database engines.

## Execution and evidence independently checked

The reviewer read the native metadata and PostgreSQL fixture implementations,
including the framed COMMIT-response fault proxy and the lock-synchronized
conflict race. The proxy checks server COMMIT/idle ReadyForQuery before dropping
the acknowledgement and a separate connection observes the durable row. The
race waits for the actual PG lock, not an arbitrary sleep. PostgreSQL cases are
explicitly ignored by default and run with `--ignored`; an ignored compile is not
counted as execution.

[`db-independent-ci-review.json`](db-independent-ci-review.json) independently
reconciles GitHub run43388468172 at committed fixture
`7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`. All 33 archived files and 21 input
snapshots matched their recorded raw hashes. Linux inputs match that Git commit;
Windows new-fixture files retain CRLF and match only after the explicitly recorded
line-ending normalization. Raw evidence was not normalized or overwritten.

The actual suite logs show five metadata/SQLite cases passing on Windows and five
on Linux, plus six PostgreSQL cases on Linux PostgreSQL18.0. These are eleven
unique original cases with sixteen CI executions. The PostgreSQL image digest,
version text, commands and zero exit statuses were also checked. The reviewer did
not rerun this already successful CI workload.

The reviewer separately authored and **executed** the three migration admission
tests in [`db-review-migration/result.json`](db-review-migration/result.json): raw
BEGIN fails the nested Migrator path; tracked begin preserves outer rollback and
commit; a failing second migration permits whole-batch rollback. All three passed
under Rust1.100.0 on Linux. The result records exact source/lock hashes, command and
raw streams. These are not Windows, C#/AOT, concurrent-process or crash tests.

## Acceptance boundary and remaining implementation obligations

The selected integration, interfaces, ownership, transaction state, error/cancel
rules, native reuse and explicit capability restrictions are sufficiently concrete
to guide implementation. Acceptance here does not depend on the future product
already existing. The following remain enforceable Delivery obligations:

- B01–B14: actual C# ABI wrappers and native domain implementations; supported
  operator/codec/backend matrix, malformed input and ownership error paths,
  static typed compile negatives and no per-entity native rebuild.
- B02/B03/B05/B06/B08: production TLS/auth, provider cancellations, protocol and
  worker cleanup, transaction/recovery faults, migration process competition,
  journal/crash recovery and both-platform Native AOT conformance.
- B21/B22: combined Rust Server/Rust DB reference service, real cross-language
  fault/tenant/outbox/blob tests, cancellation/shutdown and resource retirement.
- B23/B24: matched workload performance and memory evidence, soak, independent
  NuGet consumption and clean no-Rust/RID-free application build/run. No speed,
  memory or long-run superiority is accepted from the finite native research cases.

The author manifest retains these per-task obligations. The product repository
was not changed by this review, and this acceptance does not authorize claiming
those implementation obligations complete.
