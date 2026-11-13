# Source-lifecycle research continuation checkpoint

Date: 2026-11-13 UTC / 2026-11-12 America/Los_Angeles.
Phase: research, detailed design, experiments and future Codex planning only.
No formal A/B Delivery or NativeWeave product-source implementation is authorized.

## 1. Recovered state and concurrent work

| Repository / action | Exact observed identity |
| --- | --- |
| Design research-asset migration, PR #7 | merged `c7e123a74405a92dc3de1ef450355b08d1c05ceb` |
| Paired Plan migration, PR #4 | merged `04c2f043c0ec60a2d49dd3ca8ea4ad1c8c888d89` |
| Product PR #1 | closed at `2026-11-13T05:33:17Z`, `merged=false`, `merged_at=null` |
| Product main / retained source branch | `658ed6a410783de356a7b9b2cd6601336fff5148` / `267364a440074a61e193cf33315f1b9d0fa8126b` |
| Concurrent Design R07 continuation, PR #8 | merged `3767f3c932ebf95bd82f6ed1c9bafc9eec1c5b1e` |
| PR #8 primary executed source / run | `28f6cf7e6e4e80b9f32a92ad587a528d82911bd0` / `43373306474` |

The earlier session continued writing during recovery. The coordinator detected
and reused Plan PR #4 and product closure, then detected and incorporated Design
PR #8 before publishing this new research. A duplicate Plan migration branch
had already been saved at `68650b5abe0ddfec8975a4bc0aa4bc4391238243`; its PR #5
was closed without merge when PR #4 was discovered. No history or source branch
was deleted. Do not repeat migration, product closure or already-completed R07 CI.

The six complete attributable historical subagent reports remain unrecovered.
Current independent reviewers are real separate session agents; their scoped
reviews are not historical report recovery, a second GitHub account approval,
accepted product contracts or substitutes for GitHub required checks.

## 2. Migration integrity, reused rather than repeated

The independently downloaded and checked archive set contains all 14 original
and migrated fixture ZIPs. The source PR has 139 mapped paths: 137 byte-exact
copies and two reviewed runner path adaptations. All 112 original raw evidence
files (including two database failures), 90 newly migrated raw evidence files,
and 12 Interop binary hashes across four archives matched. The local independent
audit passed 1240/1240 checks; the already-merged Plan PR #4 review passed
781/781 content checks and six isolated validation commands.

The migrated Windows/Linux execution belongs to Design source
`67b48674e469c98f2f73f1c9ff0d63b113abc47b`, run `43371161177`, not the workflow
seed or merge HEAD. Exact immutable mapping and results remain at
`verification/native-slices/migration-map.json` and `migration-results.json`.
Historical `independent_review: false` records remain unchanged; the later
independent audit is a separately bounded observation.

## 3. New source study and actual local experiments

| Existing tasks | Substantive addition | Actual execution so far |
| --- | --- | --- |
| R20/R21/R25 → D15 | [SQLx cancellation, rollback, COMMIT uncertainty and worker retirement](../database/sqlx-retirement-study.md) | Six new Linux Rust tests; one initial Cargo-lint failure and corrected attempts preserved |
| R27/R29 → D18 | [Body termination, old channel permits and retained allocation credit](../server/body-retirement-protocol.md) | Six new Linux Rust tests, independently rerun by a different agent |
| R07 → D04 | [Parallel independent local replication](../research/topics/R07/logical-admission-probe.md) of the now-merged PR #8 boundary | Linux ordinary no-RID NuGet consumer: 931 assertions; actual Native AOT: 932. Supplemental replication, not new Windows coverage |

New test entry points are `python experiments/database-retirement/run.py --out
FRESH_DIRECTORY` and `python experiments/server-retained-bytes/run.py --out
FRESH_DIRECTORY`. The source-lifecycle workflow runs these two fixtures on
Windows2022 and Ubuntu24.04. At this initial checkpoint those new remote runs
are pending; their exact commits, run IDs, artifacts and failures will be
recorded separately before any successful CI claim. The R07 primary two-platform
run already exists and is not repeated by this workflow.

These fixtures add finite native behavioral evidence. They do not prove C#
Database/Server adapters, PostgreSQL commit-response loss, HTTP/2 wire reset
behavior, TLS, full callback retirement, weak-memory safety, process RSS bounds,
clean Rust-free hosts or performance. Each report lists its fixed upstream
commit/file/range and the relationship to actual Cargo packages; matching
selected files does not imply whole-commit equivalence.

## 4. Design and planning decisions

C-TX-001 and C-SERVER-001 advance to `0.2.1-draft`, remain `proposed`, and bind
their actual document hashes in the registry. C-LIFETIME-001 retains PR #8's
non-normative addendum/hash and proposed status. Old reviews cannot accept new
bytes. New scoped independent reviews are recorded separately from contract
acceptance.

The SQLx study keeps database outcome, operation completion, connection reuse
and resource retirement separate. A COMMIT may succeed after its awaiting
Future disappears. A SQLite shutdown acknowledgment is not an OS thread join;
synchronous worker-queue sends cannot acquire a hard deadline merely by being
wrapped in an async timeout. SeaORM-specific trait constraints apply only to
its chosen profile; ordinary SeaQuery+SQLx remains a valid native path.

The Server design distinguishes Body `EndObserved`, transport cause, queue
closure and final allocation release. Old queue permits survive close, byte
waits require explicit cancellation, and retained non-empty slices keep the
whole allocation charged. Closing/retirement-pending metadata remains bounded.
Kestrel is a required research comparator; neither Kestrel nor Rust is a
preselected product default. Plan must express conditional host dependencies
and require at least one selected host for a composed Server delivery.

The existing graph remains 34 Research / 32 Documentation / 48 candidate
Delivery tasks. No task is marked production-complete and no formal Delivery
is authorized by these experiments. Plan continuation uses the existing IDs
and propagates actual packet/contract input hashes, preserving historical
migration checks as immutable checkpoints.
