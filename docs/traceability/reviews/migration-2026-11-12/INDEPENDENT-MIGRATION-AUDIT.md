# Independent audit of the completed PR1 research-asset migration

## Result

**PASS for migration completeness and execution provenance.** The migration was already merged in Design PR #7 before this audit. It must be recovered and reused, not repeated. This review made no remote mutations and did not rerun any Rust/C# experiment.

- Source: `IzuSharp/NativeWeave`, PR #1, HEAD `267364a440074a61e193cf33315f1b9d0fa8126b`; base `658ed6a410783de356a7b9b2cd6601336fff5148`.
- Source PR observed open, Draft, unmerged; 8 commits and 139 added files.
- Reviewed Design HEAD: `c7e123a74405a92dc3de1ef450355b08d1c05ceb`; actual tree `8bcec53e01405167042d3873dc7ebbe1f27631b8`.
- All 139 source paths exactly equal the source PR git-diff inventory; every mapping is unique and all source/destination Git blob SHA1 and SHA256 values verify.
- 137 files are byte exact. The only two adaptations are the Python runner root/relative path expressions, reviewed with actual source/destination diffs. Test semantics are unchanged.
- All 112 original raw evidence files are preserved byte exact. The original README and manifest are separate, hence 114 original evidence-directory entries total.
- All 90 new Design execution files verify independently against their stored SHA256 and the actual downloaded artifact ZIP contents.
- All 14 fixture artifact ZIPs (8 original and 6 migrated) were downloaded anew and SHA256-checked against both GitHub artifact metadata and the persisted manifests. All match; none was expired at audit time.
- Four interop artifacts (old/new x Windows/Linux) also pass independent NuGet package, native library and actual AOT executable SHA256 checks against the bytes inside their ZIPs.
- Existing `python experiments/native-slices/verify_migration.py` executed locally and passed.
- The separate independent script `audit_migration.py` completed **1240/1240 checks**, no errors. See `integrity-audit.json` and `integrity-checks.json`.

## Original execution provenance

| Run | Actual executed source | Observed result |
| --- | --- | --- |
| [43363045559](https://github.com/IzuSharp/NativeWeave/actions/runs/43363045559) | `4a4adc883b80719d2a9b2bfb03be5ec86b543f3c` | Windows/Linux interop success; each platform 4 Rust tests, real NuGet consumer, ordinary RID-free build/run and Native AOT publish/run |
| [43363994414](https://github.com/IzuSharp/NativeWeave/actions/runs/43363994414) | `5dd696725afe75f2b8b03b104c8275db50dcf2c7` | Windows/Linux server success; Windows/Linux first database attempts failed and both failure records remain preserved |
| [43364366610](https://github.com/IzuSharp/NativeWeave/actions/runs/43364366610) | `43e4fbcbe0417165c0f7df03507bfa1da8a53049` | Changed database fixture succeeds on both platforms |
| [43365053808](https://github.com/IzuSharp/NativeWeave/actions/runs/43365053808) | Input `4513fcf60aa7d48e7e821d68125f7144c8acfb0d`; preservation commit `267364a440074a61e193cf33315f1b9d0fa8126b` | Evidence persistence only, not an experiment rerun |

The repository-wide Actions collection contains these four runs; there are no additional cancelled or failed runs omitted from that collection at the observed point. The second run's workflow seed was `d2ba134118ec39a8c2ed579c26dad3924b47cd2b`, while its lock job created the actual tested source `5dd6967...`. Preserve this distinction.

## Migrated execution provenance

[Design run 43371161177](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43371161177) has eight successful jobs: migration, six Windows/Linux fixture jobs, and evidence preservation. Its workflow seed is `0310344e8008b1d5397c5319816fd1a2dc3ca5ad`, while the actual six tested checkouts are `67b48674e469c98f2f73f1c9ff0d63b113abc47b`. Every saved result binds that latter commit. It is incorrect to label the workflow seed, the final merge, or the original product HEAD as the newly tested source.

The six new fixture ZIP digests match the live GitHub metadata and the migration results. The results also bind the exact migration-map SHA256 `1f306d8f4625421360f4e324f1e83f1382d53155f9b6748a7c11682af7b9c1c8`.

The migration map's `new_execution_status: pending separate migration jobs` is an immutable initial-copy checkpoint; `migration-results.json` is the authoritative completed new execution record. Likewise, historical `independent_review: false` is retained; this new independent audit has a narrower explicit scope and does not rewrite historical review claims.

## Closure conditions and limits

The migration completeness and actual migrated execution prerequisites pass this independent audit. Closing product PR #1 still requires the coordinator to verify the paired Plan changes are merged and internally consistent, and to reread product PR head/base/state for drift immediately before closure. Only close; do not merge, delete branches/history, or alter product files.

The six original historical subagent reports remain unrecovered. This audit does not manufacture their results. No product Delivery, accepted ABI, native Server selection, PostgreSQL validation, clean Rust-free consumer host, performance claim, sanitizer/soak acceptance, or Windows/Linux rerun in this new session is inferred from this archival verification.

## Reproduction and saved files

- `audit_migration.py`: independent local read-only auditor.
- `integrity-audit.json`: summary, precise source identities and individual archive/binary conclusions.
- `integrity-checks.json`: all 1240 check results.
- `blob-audit.json`: GitHub source/destination tree mapping cross-check.
- `migration-map.json`, `migration-results.json`, `original-manifest.json`: immutable reviewed source records.
- `runs.json`, per-run `*_jobs.json` and `*_artifacts.json`: original source API snapshots.
- `design_migration_run.json`, `design_migration_jobs.json`, `design_migration_artifacts.json`: migrated execution API snapshots.
- `archives/download-audit.json`: 14 downloads, verified ZIP digests, sizes and member counts; actual ZIPs and content-hash indices remain alongside it.
