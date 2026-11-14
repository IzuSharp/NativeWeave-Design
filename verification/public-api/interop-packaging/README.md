# Interop and package-flow resumption evidence

**Accepted observation scope:** design declaration feasibility and a Linux x64 research package-flow slice. These records do not accept a NativeWeave product release. The [experiment source](../../../experiments/public-api/packaging-probe/README.md) and [NuGet specification](../../../docs/api/nuget-and-consumption.md) describe the distinction.

## Final successful run

[Attempt 4 summary](attempt-4/summary.json) records every command/exit/log/input hash. [Artifact readback](attempt-4/artifact-readback.json) binds the completed run's summary digest, restored AOT compiler/linker package identities and output hashes. The retained research native asset has SHA-256 `981efa587ec0ec9f19d8bece547dcfe3a36439faf2efcae3d2371c87154695ee` before and after the model edits, ordinary publication and AOT publication.

| Check | Observed result | Evidence |
| --- | --- | --- |
| Exact Interop API + consumer compilation | C#15/net11 compile passed, XML produced, warnings treated as errors | [Compiler log](attempt-4/interop-declarations.log) |
| Escaping a span through generic result | Rejected with CS9244 | [Negative compile](attempt-4/interop-negative-borrow.log) |
| Shared C ABI layout | All 5 record-size/offset assertions passed on Linux x64 | [Execution](attempt-4/c-layout-execute.log) |
| Only facade directly installed | Exactly facade, build-assets and native-leaf research packages restored; one generated source output | [Summary](attempt-4/summary.json), [build](attempt-4/consumer-build.log) |
| Initial Entity/DTO/Handler metadata + inherited codec | 3 source shapes, native codec roundtrip passed | [Run](attempt-4/consumer-run.log) |
| Ordinary Entity and nullable DTO edit | 4 source shapes, changed metadata fingerprint, unchanged native bytes | [Changed run](attempt-4/changed-model-run.log) |
| Unsupported model | Build failed with NWPKGPROBE001 | [Negative](attempt-4/unsupported-model-negative.log) |
| Ordinary publish + execution | Framework-dependent output executed successfully | [Publish](attempt-4/consumer-publish.log), [run](attempt-4/published-consumer-run.log) |
| Native AOT publish + execution | Real native executable, `aot=True`, 4 generated shapes, native codec roundtrip passed | [Publish](attempt-4/consumer-aot-publish.log), [run](attempt-4/consumer-aot-run.log) |

SDK11.0.100 and runtime11.0.0 were executed. The direct generator compile retained the expected CS1701 System.Runtime10-to11 metadata-unification warning from SDK11's Roslyn assemblies; it was then loaded and executed by the actual SDK11 compiler. No such warning exception was used for the Interop declaration compile or consumer/AOT builds. No AOT/trimming warning was suppressed. Compiler-host/IDE combinations beyond this CLI remain future package acceptance rows.

## Preserved preliminary attempts

| Attempt | Actual outcome and correction |
| --- | --- |
| [1](attempt-1/summary.json) | Interop declarations compiled; the inferred-lambda negative produced CS0201 rather than the harness's expected CS9244. The explicit ref-like generic call was substituted to test the intended borrowing restriction unambiguously. No unsupported code compiled. |
| [2](attempt-2/summary.json) | Interop negative and C layout passed. Direct generator compilation stopped because SDK Roslyn references Runtime10 while the available reference pack is Runtime11; CS1701 was initially promoted to an error. The experiment retained that specific warning and verified the compiler host by actual loading/execution. No broad warning/AOT suppression was introduced. |
| [3](attempt-3/summary.json) | Generator compilation passed; a Python tuple/list concatenation error stopped the harness before facade packaging. The argument-list construction was corrected. |
| [4](attempt-4/summary.json) | All stated design checks passed, including real Native AOT execution. |

These are failed harness attempts, not product regressions or additional accepted features. Logs remain unmodified. Work paths in logs are normalized; no credentials, private environment or unrelated file contents are stored. The probe's current source matches attempt4's executable-input hashes; documentation added after the run is not relabeled as an executed input.

The experiment reuses a previously verified research codec's compiled native bytes. It newly validates the specified split-package/transitive-generator consumption path. It does not rerun the upstream Rust suite, implement a product ORM/server, certify Windows from Linux, test production signing or prove a pristine host image never contained Rust. A14–A16/B24 retain their actual per-platform and full-package obligations.
