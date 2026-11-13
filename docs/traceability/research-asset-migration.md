# Research asset migration — current authority and provenance

The latest user instruction corrects the project phase: NativeWeave remains in deep source research, detailed design and future Codex planning. Real experiments are encouraged, but all such code belongs in NativeWeave-Design. The product repository is read-only except closing PR1 after the migration and paired Plan changes are merged and verified. Never merge PR1, delete its source branch/commits or execute A/B Delivery. See [CURRENT-PHASE.md](../../CURRENT-PHASE.md).

## Observed baseline and scope

NativeWeave PR1 was observed open/Draft/unmerged at267364a440074a61e193cf33315f1b9d0fa8126b,139 added files against main658ed6a410783de356a7b9b2cd6601336fff5148. Design main4adf7a38c3159c9e12e2f89b85884514a430f0a4 and Plan mainf6ed91dddba62b9eba246f2af56ca5b93cc2593b were the observed latest baselines; no previous migration branch/PR was found. Old Design PR5/6 and Plan PR2/3 are not repeated.

All139 PR-added files are mapped once. Working code moves to `experiments/native-slices/{interop,database,server}`; toolchains remain workspace-local. Original workflows/collector/instructions are archived under `experiments/native-slices/provenance` without activation. Every original evidence file moves byte-exact to `verification/native-slices/original-pr1`; successful and failed attempts are preserved. Only two Python runner root/path expressions change. Root evidence attributes and nested source attributes prevent Windows checkout normalization. A new Design-only workflow replaces old execution destinations without changing historical workflow bytes.

`verification/native-slices/migration-map.json` records source repository/PR/base/head, original and destination Git blob SHA1, SHA256, path, byte identity and adaptation reason. The original112 evidence hashes are checked through that map without rewriting their original manifest. Original Actions run IDs and artifact/binary hashes remain original observations; GitHub history is not migrated or forged. The one-shot migration script fails on inventory drift or preexisting output instead of duplicating a completed migration.

## New execution and archival gates

The Design workflow runs actual Interop, Database and Server fixtures on Ubuntu24.04 x64 and Windows2022 x64. New results must reference the exact relocated Design checkout, not the workflow seed or old NativeWeave commit. It checks all139 mapped files, all112 original raw evidence files, locked dependency closure, ordinary NuGet build/run and actual AOT execution where applicable. Native API/Rust language research outside this migration scope is reused, not restarted.

New command logs, source/lock hashes, artifact ZIP hashes and successful/failed test identities are separate under `verification/native-slices/migrated/<run>/`. `migration-results.json` is authoritative for new execution success; the original mapping's pending status only describes the initial copy checkpoint. The collector verifies package/native/AOT binary hashes before retaining raw text. Failure artifacts must remain available and must be archived if any migration attempt fails.

## Plan and closure order

After Design migration integrity and actual platform runs pass, review and merge the Design PR through normal GitHub gates. Update only affected Plan evidence links, active check scripts/workflows, task packets/hashes and required dependency revisions; keep historical checkpoint records and original source identities. Preserve34/32/48 IDs. Correct earlier ongoing product-implementation authorization to this latest research-only phase. Product output paths in future Delivery instructions remain future paths; do not mechanically replace them with Design paths.

Only after the Plan PR is checked and merged, reread product PR1/head/main, verify no drift and close it WITHOUT merging or deleting history. Record the actual replacement Design/Plan commits in the closure body. This file and the two PR discussions/checkpoints retain the mapping and merge evidence.

## Acceptance boundaries and continuation

Archival/documentation merge is not technical contract acceptance. No independent reviewer or original six subagent reports have been recovered in this session; self-review and CI are labelled accordingly. Existing proposed contracts remain proposed unless their specific evidence/review gate is actually met. Do not block ordinary research because product tests are still future work, and do not promote a finite test into production acceptance.

After migration, continue existing R03/R07/D02/D04 logical-admission research, R08/R09 async retirement, R22/R25 SeaQuery/SQLx semantics and R27/R29 native handler/body ownership. Keep the lightweight Core, mandatory Rust Database and precompiled typed C# Fluent direction. No new planning hierarchy or product branch is needed.
