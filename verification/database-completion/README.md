# Database research completion checkpoint

Author: `/root/database_research`, a real delegated agent. This is author research
and self-check evidence. It is **not** independent acceptance or a second GitHub
account approval. Current per-task conclusions and exact review hashes are in
[task-status.json](task-status.json). Input baselines: Design
`ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan
`5b346ebb5acdb387077d0faae16b00bbc77cb299`.

## Actual initial audit

All eight assigned R tasks (R19–R25, R31) already had report/evidence/coverage.
All five D tasks (D14–D17, D20) already had detailed specifications. The graphs
therefore understated authored/evidenced work. This did not mean the existing
material was already consistently acceptable: older primary reports and machine
records still selected static SeaORM and per-entity Cargo while later appendices
recommended precompiled dynamic metadata. R31/D20 still selected Kestrel product
hosting. Those current conclusions were replaced; original source observations,
reader identities, successful experiments and raw historical evidence were kept.

## Findings resolved in the current design

| ID | Finding | Resolution and evidence |
| --- | --- | --- |
| DB-COMP-001 | Static SeaORM selected merely as the required ORM route | Ordinary profile chooses native SeaQuery+SQLx; public SeaORM dynamic projection positively tested; static loader boundaries source-inspected |
| DB-COMP-002 | Ordinary entity/query changes required Rust generation/build | Static managed descriptors/runtime native metadata; existing unchanged-native C# AOT evidence reused and new native dynamic schema experiment added |
| DB-COMP-003 | R31/D20 retained product Kestrel/optional Rust Server | Product composition corrected to mandatory Rust Server and Rust DB; Kestrel only comparison |
| DB-COMP-004 | Dynamic nullable decode assumed to reject missing fields | Real failure and source show ColumnNotFound→None; explicit result-shape/duplicate preflight now normative |
| DB-COMP-005 | SQLx migration lock treated as universally scoped cleanup | PG error can retain session advisory lock; dedicated admin connection closes on failure; SQLite lock no-op requires explicit native write serialization |
| DB-COMP-006 | Bounded batches could be confused with server fetch-size bounds | SQLx PG Execute limit=0 source recorded; exported rows/bytes do not imply provider/server memory bound |
| DB-COMP-007 | TLS connection success could imply peer validation | Remote profile explicitly requires VerifyFull; Prefer downgrade/Require limitations documented |
| DB-COMP-008 | Protocol cleanup or waiting cancellation could settle COMMIT effect | Real PG proxy confirms client failure plus committed row; outcome, protocol and local cleanup remain separate |
| DB-COMP-009 | One-statement conflict CTE assumed to always find prior result | Real lock-synchronized PG race returns no row, then next statement recovers; two-statement protocol retained |

## Source and execution identities

[source-inspection.json](source-inspection.json) records ten inspected source files,
full commits, Git blob hashes, selected read ranges and executed registry identity.
Every listed Git blob hash was independently computed from the registry file and
compared with the fetched GitHub blob identity. This is file-level equality, not
an unsupported whole-crate-to-Git equivalence claim.

The fixture has **11 distinct native research cases**: five metadata/SQLite/SeaORM
and six PostgreSQL cases. Repeats and multiple OS runs are separate executions,
not additional unique coverage. The Rust dependency lock is in
`experiments/database-completion/Cargo.lock`.

| Record | Actual scope |
| --- | --- |
| `linux-attempt-1` | Preserved failing missing-nullable-column hypothesis, three other cases passing; source snapshot and raw streams |
| `linux-attempt-2` | Corrected four common cases passing; four then-existing PG cases compiled but explicitly ignored |
| `linux-metadata-final` | Five common cases passing, after adding native migration case; includes its exact then-current input snapshot |
| `linux-metadata-current` | Same five cases, verification against final frozen package input set; not counted as new coverage |
| `linux-postgres-setup-failure` | Initial server setup failed because the workspace filesystem rejected Unix-domain socket creation; not a test success |
| `linux-postgres-final` | Six PG cases actually executed against locally built official PostgreSQL18.0; exact source tarball SHA256 verified against official checksum, binary hash/version and server log retained |

The successful local PG server used loopback TCP, explicit local trust auth and no
TLS; it was stopped after the test. These tests do not validate production
TLS/authentication, Windows PG, C# AOT, filesystem power-loss durability,
performance or long-load behavior. Prior Windows/Linux native and C# AOT evidence
remains pinned in its original manifests. New CI replication is recorded separately
by the integrator at its real commit/run/artifact identities.

## Handoff

R19–R25/R31 and D14–D17/D20 are ready for independent research/design review.
The author has not promoted registry/graph acceptance. Future implementation
obligations are mapped per ID in task-status.json; they cannot be misrepresented
as executed product work, but they also do not require product implementation
before accepting the detailed design. The NativeWeave product repository was not
modified.

## Published fixture CI confirmation

[ci-confirmation.json](ci-confirmation.json) records the actual archived run `43388468172` at fixture commit `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`. Metadata/SQLite passed five cases on Windows and five on Linux; PostgreSQL 18.0 passed all six on Linux. All archived file, snapshot and raw-stream hashes were checked by the author. Windows new-fixture inputs differ from Linux only by retained CRLF; their original hashes are preserved. The published PostgreSQL container digest is `postgres@sha256:41fc5342eefba6cc2ccda736aaf034bbbb7c3df0fdb81516eba1ba33f360162c`. Eleven unique cases remain eleven, regardless of repeated platform executions. This is additional execution evidence, not independent technical approval.
