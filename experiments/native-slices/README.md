# Native slices — Design-owned research workspace

Current phase: research, architecture, detailed specifications and future Codex planning. These are not product packages or completed A/B Delivery tasks. See [CURRENT-PHASE.md](../../CURRENT-PHASE.md).

## Layout and reproduction

- `interop/`: Rust C ABI/owner/buffer tests, static C# imports/SafeHandle, NuGet package and actual Native AOT consumer.
- `database/`: pinned SeaQuery/SQLx SQLite scalar-binding and transaction/capability fixtures.
- `server/`: pinned native Hyper/Tower/Tokio Service/Body/backpressure fixtures.
- `rust-toolchain.toml`, `global.json`: workspace-local exact Rust1.100.0 and .NET SDK11.0.100 pins.
- `provenance/`: original PR1 README/workflow/collector files preserved as historical records, NOT active workflow entry points.
- `../../verification/native-slices/original-pr1/`: original successful and failed execution evidence, byte-exact.
- `../../verification/native-slices/migration-map.json`: every original PR1 path/blob/SHA256 to current path/blob/SHA256, with reasons for the two driver path adaptations.
- `../../verification/native-slices/migrated/<run>/`: newly executed Design migration evidence, separate from original runs.

From the repository root, run `python experiments/native-slices/verify_migration.py` to check the relocated snapshot. Add `interop`, `database` or `server` to execute that fixture. The wrapper sets the actual checked-out Design commit as the evidence source identity and runs inside this directory so the local SDK pin applies. Install the pinned Rust/.NET tools and the platform Native AOT C/C++ linker prerequisites first. Interop needs no third-party Cargo crates; domain tests use their committed locks with `--locked` and never regenerate them automatically.

The active GitHub workflow is `.github/workflows/research-assets-migration.yml`. It reads the original NativeWeave source snapshot, migrates only into this Design feature branch, executes six OS/domain jobs, and commits new text evidence here. It never writes or merges the NativeWeave product repository. The nested historical workflows are deliberately inactive because their original branch/repository/write destinations are historical inputs, not present authorization.

## Original versus migrated execution

Original source repository: IzuSharp/NativeWeave PR1, commit267364a440074a61e193cf33315f1b9d0fa8126b. Original Interop run43363045559, Server/first Database failure run43363994414, corrected Database run43364366610 and preservation run43365053808 remain original history. Their results are not renamed as Design CI. The initial migration mapping verifies139 files including112 raw evidence files. Rust/C#/Cargo source bytes are unchanged; only two Python drivers' root/path expressions are adapted. Fresh Design result status is in `migration-results.json` only after those jobs actually succeed.

Finite limits remain: Interop proves physical call leases, not full logical admission/async retirement; Database covers a scalar subset and real SQLite, not PostgreSQL/full ORM; Server uses actual native HTTP1 over an in-process duplex, not a C# handler/TLS/load/RSS proof. All ordinary consumer and native compilation occur on the same CI host, not a pristine Rust-free host. No performance or production-readiness claim follows from these fixtures. Native libraries/packages/executables are verified in run artifacts; only raw text, source identity and binary hashes are committed. Missing or expired artifacts must be reported, never reconstructed as original outputs.
