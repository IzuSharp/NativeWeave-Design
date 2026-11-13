# Independent final Database / ORM review

Reviewer: `/root/database_review`, an actual delegated executor distinct from the research and correction authors. Date: 2026-11-13. This is technical review, not a second GitHub account approval. I changed only this review record and its JSON companion; no specification, task graph, product source or historical evidence was altered.

## Decision

**Recommend research and detailed-design acceptance for R19–R25, D14–D17 and D27–D28 at the exact bytes in `database-review.json`. No unresolved blocking finding remains in this scope.** The four relevant contracts are C-DB-001, C-TX-001, C-QUERY-001 and C-QUERYGEN-001, all version 0.3.0. Formal registry/graph transition and remote source binding remain the integrator's responsibility. This decision does not accept product implementation or release.

The reviewed working bytes recover Design `5bb128424259f3d9cf594b4e50d7688ad5b6541e` and Plan `7359060f88f94591b0dc41178e35701eefc8eb6d` plus the preserved uncommitted corrections. Every scoped research output, specification, task packet and fragment has a SHA256 in the companion record. Subsequent normative changes require a delta review; changing acceptance metadata alone must preserve those inputs.

## Per-task disposition

| Task | Reviewed basis | Disposition |
| --- | --- | --- |
| R19 | Fixed SQLx PG execution/ReadyForQuery/TLS source plus real timeout, same-backend stream drain and response-loss durable-effect cases. Npgsql remains comparative. | Recommend research/design acceptance |
| R20 | SQLx worker/progress/retirement limits retained; SQLite FK/savepoint/checksum cases and independent tracked begin_with migration regressions resolve the native administrative path. | Recommend research/design acceptance |
| R21 | Four independent transaction dimensions; COMMIT dispatch versus known outcome, cleanup and pool reuse remain separate. Actual PG COMMIT-response-loss and lock-synchronized old-snapshot counterexamples support the decision. | Recommend research/design acceptance |
| R22 | Missing nullable column is not SQL NULL; shape preflight precedes Option decode. Explicit finite codecs, precision policy, native migrations and separate batch/RSS accounting are source/evidence supported. | Recommend research/design acceptance |
| R23 | Ordinary C# typed Fluent/static descriptors use the same precompiled native asset. Prior Linux AOT new-entity run and wrong-entity compile-negative preserved; generator implementation is separately planned. | Recommend research/design acceptance |
| R24 | Native SeaQuery owns SQL3VL, parameters, dialect and relation semantics. SQLite truth tables, native join/aggregate and tenant-CAS fixtures provide finite independent oracles without claiming complete SQL equivalence. | Recommend research/design acceptance |
| R25 | SeaQuery+SQLx chosen for ordinary native ORM operations. SeaORM public dynamic projections are real; LoaderTrait static bounds/all() do not promise a dynamic bounded loader. No ordinary per-entity Cargo requirement. | Recommend research/design acceptance |
| D14 | Concrete native/C# ownership, db-wire bounds, finite codecs, Rust provider behavior, real TLS policy, dedicated migration lifetime and precompiled entity boundary are implementable. | Recommend research/design acceptance |
| D15 | Canonical four-dimensional state table, commit admission and Unknown, rollback-unconfirmed, safe reuse versus cleanup, explicit savepoints and CloseAsync/DisposeAsync distinction are consistent with the actual counterexamples. | Recommend research/design acceptance |
| D16 | Native semantic authority, mutable/sealed/poisoned owner rules, SQL3VL, capability rejection, explicit joins/changesets/CAS and parameter/budget rules form a concrete ordinary profile. | Recommend research/design acceptance |
| D17 | Static descriptor/DTO-only generation, handwritten parity, seven diagnostics, result shape preflight, no hidden LINQ engine and unchanged native ordinary entity flow are specific. | Recommend research/design acceptance |
| D27 | Eight B01–B08 task details agree with graph and packets. B01 canonical seams and B07 sole codecs remove duplication; component fixtures and downstream B04 composition avoid an acceptance cycle. | Recommend research/design acceptance |
| D28 | Six B09–B14 task details agree with graph and packets. B09 imports B01, B11 uses B07, B10 is optional with NWQ0101–0107, and B12/B13/B14 retain native ownership and exact result semantics. | Recommend research/design acceptance |

## Substantive conclusions

Rust SeaQuery owns query construction and dialect semantics; SQLx owns execution, protocol and pools. The adapter supplies bounded admission, fallible scalar binding, metadata validation and ownership policy. C# provides typed Fluent declarations, static metadata, DTO materialization and business logic. Ordinary new entities using supported capabilities reuse the same precompiled native asset. SeaORM's public runtime projection is a concrete reusable capability, while its static LoaderTrait/EntityTrait bounds and `all()` collection are retained as explicit limits. The ordinary design does not require a full managed SQL engine, a hidden LINQ provider or per-entity Cargo.

D15 and B05 agree on TxLifecycle, TransactionOutcome, ConnectionDisposition and LocalLifetime. An application result, a local close, provider cleanup and remote durable effect are independent. Commit admission cancellation ends at the conservative dispatch boundary; missing trustworthy confirmation after dispatch is Unknown. A later cleanup rollback cannot overwrite Unknown. Unconfirmed rollback with no COMMIT attempt stays Closed/InProgress with CommitAttempted=false and a separate cleanup observation. CloseAsync may return Pending while resources remain counted; DisposeAsync joins actual local safety. The revised B05 wording is independently reviewed here, including the earlier DB-PLAN-01 correction.

PG response loss is not a synthetic exception after a successful client reply: the fixture forwards COMMIT, consumes the server COMMIT plus idle ReadyForQuery, discards those responses, and then observes durable state over another connection. The conflict-snapshot test synchronizes using a real `pg_locks` wait; the same-statement CTE sees no row while a later statement sees the committed operation. Those finite oracles support D15 and the server reference application's recovery rules without proving production behavior.

SQLite migration locking differs from PostgreSQL. SQLx SQLite migration lock/unlock are no-ops, and raw BEGIN does not update SQLx transaction depth. D14/D15/B08 now require `Connection::begin_with("BEGIN IMMEDIATE")`, a tracked outer Transaction, `Migrator::run(&mut *tx)`, pre-rejection of no_tx and explicit outer commit/rollback. The independent three-case migration regression is retained with matching source hashes and raw logs. PostgreSQL session advisory locks may survive an early Migrator error; a dedicated administrative connection and explicit close/quarantine are correctly required.

Nullable result-shape preflight is concrete: SeaORM `Option<T>` can turn ColumnNotFound into None, so missing columns cannot be treated as SQL NULL. D14/D17 and B06/B12 require count/order/alias/type checks before nullable decode. Public `QueryResult::try_as_pg_row` and `try_as_sqlite_row` supply the provider-row seam; I rechecked that exact upstream source. Remote PostgreSQL VerifyFull policy matches the fixed TLS implementation; Prefer/Require are not treated as equivalent certificate-and-hostname validation.

## Evidence verification

I inspected the actual test source and raw success/failure streams and independently rehashed three CI archives from run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: **33 archived files and 21 executed input snapshots match**. Metadata/SQLite has five passing cases on Linux and five on Windows; PostgreSQL has six passing cases on Linux. That is eleven unique cases and sixteen executions. Five Windows input files differ only by preserved CRLF; their raw hashes were not rewritten. The PG CI manifest SHA256 is `2657a79ccf8c11b351fafe23bd3f928c7b597d23cad7d22d89caa4a88cbf239e`.

The local final metadata/PG snapshots and stream hashes match the current experiment sources. The failed missing-nullable-field hypothesis remains a real retained failure. The three independent migration tests retain their source identities. All 31 recovered original AOT/prototype files match the preservation manifest, including the second-entity unchanged-native run and the wrong-entity CS1503 compile negative. I did not rerun successful experiments or reclassify native-only cases as C# AOT.

Selected fixed source ranges were reread for PG Execute/ReadyForQuery, migration lock cleanup, SeaORM runtime projection and static loader boundaries. Four fresh GitHub reads checked PG TLS, SeaORM QueryResult, PG migration and SQLite migration at exact commits. The old textual scratch source cache adds exactly one terminal LF; removing that cache-only LF reproduces both canonical SHA256 and Git blob SHA. No canonical evidence byte was normalized or edited.

The previous independent Database review remains preserved: **40 of its 41 input hashes and all 14 supporting-evidence hashes still match**. The single changed input is D20's budget paragraph, independently assigned to the current Server reviewer. I did not rewrite the historical review to conceal that delta.

## Plan readiness and remaining stage boundaries

All 27 scoped R/D/Delivery packet hashes match their graph records. Both D27/D28 fragments match every corresponding Delivery graph field. The complete 114-node start-plus-acceptance dependency graph is acyclic, and the 130 inspected product write scopes have no overlap. B01 owns canonical metadata/interfaces, B07 owns fallible codecs, B09 owns thin operation descriptors, B11 reuses native query construction, B12 owns static DTO construction, B13 owns typed Fluent and B14 owns explicit native relations/CAS. The provider/component fixtures and downstream B04 composition avoid cyclic accepted-status prerequisites. B10 includes all seven NWQ0101–NWQ0107 diagnostics and remains optional for handwritten descriptors.

B01–B14 are ready as future implementation instructions and remain `planned_candidate` / `not_authorized`. Product Windows/Linux AOT, TLS/auth, real provider wrappers, malformed-input/race/fault coverage, independent NuGet/no-Rust consumption, long load, memory and performance must be executed in Delivery against actual product commits. This is the correct remaining work, not a reason to leave a sufficiently researched design permanently proposed.

No product repository was modified and no new GitHub approval identity is claimed.
