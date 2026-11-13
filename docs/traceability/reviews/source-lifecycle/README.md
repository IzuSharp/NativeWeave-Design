# Independent reviews of the new lifecycle research

Review independence is explicit and limited to the listed bytes. A subagent
review is not another GitHub account's approval, and none of these reports
accepts a product contract or enables formal Delivery.

| Work | Author | Separate reviewer | Evidence |
| --- | --- | --- | --- |
| SQLx/SQLite retirement fixture and D15 changes | `design_source_review`; D15 version integration by root | `migration_evidence` | [Report](database/DATABASE-LIFECYCLE-REVIEW.md), 59-file manifest, 37 checks and actual independent six-test Linux run |
| Body/Bytes/permit fixture, protocol, D18 and four-job workflow | root | `design_source_review` | [Report](server/report.md), ten reviewed input files, 43 raw reviewer files, two actual six-test Linux runs and explicitly simulated runner-error recording checks |
| Concurrent local Interop replication C# and runner | `migration_evidence` | root | [Review](interop-replication-review.json), source/oracle/ownership analysis and53 actual input/output/binary hash checks; no additional test execution |
| Four-job CI provenance and actual checkout bytes | root's archive integration | `migration_evidence` | [134-check review](ci/SOURCE-LIFECYCLE-CI-REVIEW.md), fresh provider identities, original ZIPs and all56 unchanged members |
| Evidence verifier, trigger coverage and review-hash binding | root | `design_source_review` | [Integrity addendum](integrity/addendum.md), final verifier execution and exact file hashes; four small original ZIPs preserved in its bundle |
| Already-merged PR #8 primary logical-admission provenance | preceding session | `migration_evidence` | [213-check identity review](pr8/PR8-IDENTITY-REVIEW.md), four actual downloads,64 preserved raw files and eight binary digests; no test rerun |

Server findings addressed artifact selection, timeout evidence, empty-slice
precision, outstanding byte waiters, copied allocations, pending-retirement
metadata and stale source-metadata paths. The approved D18 hash is
`9acf2b3bd464815ac0bb66700ee0c5c8791fa3772f7b0fbe54736e59e2f47358`;
the approved D15 change hash is
`34788328a967205b6d139aa4d613fdb224cde1bf3dca5f4784acc4eb18c09cce`.
Both remain `0.2.1-draft / proposed`.

The `raw` paths in the Server manifest and `database-independent-run` contain
the actual saved reviewer inputs/results. Any absolute or recovery-relative
paths inside original source-retrieval metadata describe the historical local
execution environment; they are not promised live links after relocation.
No raw log or original input hash was changed to hide that distinction.
PR #8's downloaded binary ZIPs remain recovery inputs and GitHub artifacts;
the retained report and provider snapshot identify them precisely, while its
already-versioned64 raw files are reused in `verification/logical-admission/`.
The incidental second run is explicitly not counted as new coverage.

`verification/source-lifecycle/verify.py` checks these reviewed file hashes and
the 56 separately archived CI members, in addition to the historical migration
audit. Later evidence-integrity review addenda are kept separately so the
Server author/reviewer split and Database author/reviewer split remain clear.
