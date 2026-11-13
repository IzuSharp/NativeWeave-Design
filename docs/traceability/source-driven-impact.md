> Historical checkpoint. Current product constraints and acceptance boundaries are in [ADR-0003](../decisions/ADR-0003-rust-engine-mandate-and-design-acceptance.md). Any optional Rust Server/Kestrel product-host wording below describes the prior snapshot, not current authorization. Original evidence retains its recorded scope.

# Source-driven integration: recovery, impact and independent-review handoff

Status: proposed amendment in existing Design PR #5. No product-source implementation or automatic final acceptance. Exact source pins/ranges, preserved commands/logs and file hashes are in `docs/research/source-driven-evidence/`. The paired Plan PR must pin the resulting Design commit; the two repositories are not an atomic transaction.

## Recovered versus missing

Recovered the complete baseline archives, pinned source snapshots, corrected SQLx/Actix source identities and successful query feasibility artifact. Reused existing commits/PR and the actual Linux x64/SQLite Native AOT experiment; it was not rerun. The earlier failed SQLx API attempt remains in Actions history. Native asset hash equality, second entity and expected type-error fixture were rechecked from recovered records. Raw logs and source are persisted before temporary artifact expiry.

Six separately attributable completed subagent reports were not found in the currently accessible records. There is no callable subagent interface in the recovery session. No independent review is fabricated. PR2–4 historical reviews apply only to their original bytes. New source inspection, integration, finite model and structural tests are author-side evidence.

## Concrete conflicts, corrections and retained obligations

| Finding | Previous conflict / omission | Revision | Existing tasks |
|---|---|---|---|
| SDI-01 | Merged DB required static SeaORM models and per-schema Rust rebuilds | Precompiled dynamic SeaQuery+SQLx ordinary candidate; static SeaORM specialized | R19–R25, D14–D17, B01–B14 |
| SDI-02 | Plan still had managed PostgreSQL and optional native DB | Mandatory Rust providers/host, no managed product fallback; B04 required in composition | D27/D30, B01–B08/B21–B24 |
| SDI-03 | Declaration-only LINQ/IR pipeline and managed SQL semantics exceeded requested experience | Typed native-backed Fluent, SQL semantics, optional static descriptor/DTO generation; no complete C# SQL engine | R06/R23/R24/R25, D16/D17, B09–B14 |
| SDI-04 | Public binding alone understated reusable native structure and maintenance choices | Source-informed public seams, justified extension/fork ladder, small Core and exact upstream maps | R03–R10/R14/R18, D02–D11, A13–A16/A22/A24 |
| SDI-05 | Passing through a mature builder could silently lose semantics | SQLite unsupported clauses explicitly rejected; CTE/value validation and fallible argument encoding | R16/R22/R24, D14/D16, B07/B11/B13 |
| SDI-06 | Generic Server adaptation did not state native Service/Body reuse precisely | ForeignService plus native connection/body ownership, Actix affinity and proxy alternatives; Kestrel baseline retained | R26–R31, D18/D20, B16/B17/B20/B22 |
| SDI-07 | Response-future/protocol credit could be mistaken for lifetime/RSS bounds | Body/callback lease and retained-byte budgets; shutdown timeout never retires native owners | R09/R10/R29, D06/D07/D18, B16/B17/B22 |
| SDI-08 | Maintainer native builds and ordinary entity builds were coupled | NuGet precompiled assets, clean Rust-free/RID-free development tests; native hash remains same for supported model variation | R13/R14, D10/D17, A13–A16/B10/B24 |
| SDI-09 | Upstream/patch updates lacked explicit source seam/behavior compatibility duty | Pins, Cargo closure/features, patch queue, semantic differential/performance gates and fork retirement | R14/R18, D10/D11, A22/A24/B24 |
| SDI-10 | Existing acceptance metadata could outlive changed design bytes | Eight contracts revised as proposed with actual hashes; all114 Plan packet/pin revisions, real independent review still pending | D31/D32 |

Retain ownership, callback quiescence, cancellation versus retirement, Unknown COMMIT, fixed-session admission, rollback confirmation, pool quarantine, SQL null/collation/CAS, atomic idempotency/outbox and bounded telemetry. Historical source findings are not deleted merely because the default integration route changes. No unrelated GPU/mobile implementation or global Core runtime is added.

## Evidence and limits

R25/R27 record selected source call chains and relevant tests. Source tests were read, not executed by this recovery. The original registry-crate Cargo.lock is distinct from inspected Git source pins. The recovered prototype demonstrates real Linux AOT execution and reuse for a second entity, but used explicit RID, handwritten mappings, PATH Rust-denial shims and research-only synchronous JSON/fetch_all/per-call runtime shortcuts. It does not prove clean-machine or RID-free consumer behavior, PostgreSQL execution, Windows, a source generator, production streaming/concurrency, full ORM coverage or performance superiority.

The newly executed two-request admission model finds a response-head-only permit counterexample and no violation in the finite body-and-callback policy model. It is not a Hyper/Tower run, byte/RSS proof, weak-memory model, liveness proof or independent review. Precise counts and command hashes are in the preserved result.

## Design answers versus gates

Q11/Q13's universal per-entity Rust build/full-LINQ assumptions are answered negatively for the dynamic profile, with source and finite execution evidence. Independent architectural acceptance, real implementation and production release gates stay separate. Q14 backend semantics, Q15 Server value and Q16 real resource safety remain scoped obligations. Preserve all applicable Windows/Linux AOT, race/property/fuzz/model, fault/soak, compatibility and workload tests in the existing Delivery tasks.

## Independent-review entry and disjoint continuation

Use the existing `IzuSharp/Plan:prompts/independent-review.md`, current R25/R27 packets and D10/D11/D14–D18 packets; record exact Design and Plan commits and packet hashes before reviewing. One independent reviewer should verify dynamic identifiers/AST/parameters, SeaORM's static boundary, missing ORM policies and no-Cargo consumer claims. A second can inspect ForeignService/body/worker affinity, credit/retirement and shutdown traps. A third can check packaging, source/patch maintenance and all graph/contract/packet pins. These are reusable existing task scopes, not claimed active agents or a new coordination graph.

Review every changed contract at its new content hash, retain finite evidence limits, reject unsafe silent backend behavior and identify avoidable translation/runtime layers. Record finding IDs/severity/evidence/fixes and re-read final bytes. Do not approve merely because structural checks pass, reuse old PR approvals, or merge until the actual independent-review requirement and effective repository checks are satisfied. Product implementation remains unauthorized.
