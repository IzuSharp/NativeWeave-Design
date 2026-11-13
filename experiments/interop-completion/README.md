# Interop completion research fixtures

These are isolated research programs for R02–R12/R15/R16. They are not NativeWeave product implementations, public ABI exports or performance claims. The canonical contract status remains in `docs/contracts/registry.json`. Existing successful `native-slices`, `logical-admission` and `source-lifecycle` evidence is reused without rerunning it to manufacture additional results.

## Reproduction

Use the pinned `global.json` (.NET SDK 11.0.100) and `rust-toolchain.toml` (Rust 1.100.0), a working native AOT linker and the corresponding target SDK/toolchain. Disable .NET telemetry explicitly:

```sh
DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 python experiments/interop-completion/run.py --aot
```

Run from the Design repository root. The runner chooses `verification/interop-completion/linux` or `windows` and records the platform, exact arguments, command exits, stdout/stderr hashes, source input hashes and output binary hashes. A required AOT publish or execution failure returns nonzero; normal execution alone cannot satisfy `--aot`. It does not accept an output directory positional argument. Temporary build products stay under `.work`.

`source_commit: null` in local result manifests is intentional: those exact uncommitted source inputs were identified by file hashes at execution time. `baseline_commit` is the checkout base, not a false assertion that the base contains the changes. The later integrating commit and CI run can identify committed reproduction separately.

## Observed main results

The current Linux execution is [recorded here](../../verification/interop-completion/linux/result.json): normal 10,528 assertions, actual Native AOT 10,529, 32 controlled native-thread callback rounds in each, one Rust unit test, nine incremental Roslyn driver checks, and static metadata/AOT restriction checks (four normal, six AOT). The [initial smaller run](../../verification/interop-completion/linux-initial/result.json) and its exact input snapshot are preserved as earlier evidence, not overwritten or counted as extra coverage.

The main fixture observes native callback in-flight retirement, managed cancellation registration drain, pre-cancel, late cancel after success, duplicate terminal and take rejection, one independent result owner, exception-safe result release, and checked u64 extent against an independent `BigInteger` oracle with a fixed seed. A deliberate callback hold is a test barrier; production callbacks must never copy that blocking behavior. The native fixture assumes valid pointers and external call leases; it is not an arbitrary-pointer validator or a complete Engine coordinator. Its private status values differ from D08 and must not become public ABI constants.

`GeneratorProbe` uses the SDK's actual Roslyn assemblies: it compiles generated source, checks unchanged-model caching, one-entity changes, an unsupported delegate diagnostic and ordinary peer-generator output invisibility in the same pass. It is not the production generator. `AotRestrictions` demonstrates static JSON metadata, closed generic instances, disabled reflection serialization fallback and Native AOT rejection of dynamic IL; the dynamic-code warning suppression applies only to the intentional negative test.

## Supplemental programs

| Program | Actual output | Scope |
|---|---|---|
| `binding_probe.py <csbindgen-checkout-root>` | [binding-linux](../../verification/interop-completion/binding-linux/result.json) | Exact csbindgen commit `b9eb1e84bb8185b78a4e8364fd948fee300329a7`, all ten crate files blob-verified, offline generated binding; DllImport vs LibraryImport 60 normal and 60 AOT calls. Unsupported tuple silently omitted despite success; an inventory gate must reject this. |
| `panic_probe.py` | [panic-linux](../../verification/interop-completion/panic-linux/result.json) | Seven Rust child processes: two survive, five terminate as expected. Panic unwind/abort strategy, payload Drop, hook, double panic, non-unwind FFI boundary. |
| `mailbox_model.py` | [mailbox model](../../verification/interop-completion/mailbox-model.json) and [run](../../verification/interop-completion/mailbox-run.json) | Stale-check negative: 17 states/17 transitions and a lost-wake counterexample. Atomic candidate: 11 states/11 transitions, no counterexample within one-worker/one-extra-wake SC model. |
| `uco_invalid_probe.py` | [uco-invalid-linux](../../verification/interop-completion/uco-invalid-linux/result.json) | Deliberately invalid char/bool UCO with runtime marshalling enabled: normal and AOT both publish then terminate isolated child with unhandled InvalidProgramException before callback body. |

Run supplemental scripts from this directory, with the same pinned tools and telemetry opt-out. Panic/UCO runners currently target Linux and disable core dumps for the intentionally terminating children; they do not claim Windows execution. The csbindgen checkout must include the separately recorded `source-identity.json` and exact original crate files; upstream source is not vendored into this repository. Its generated source and lockfile are preserved with the result. The first UCO launch used a narrowed PATH without a `python` alias and failed before any compilation; rerunning with the available `python3` executed the recorded cases. This launcher correction is not an upstream compiler failure.

The UCO experiment records an unhandled exception and process termination in this harness. It does not claim that every non-blittable signature has identical behavior or that an outer managed catch was tested. In particular, it does prove that a catch inside a callback body cannot protect a body that never starts.

## Evidence and limits

[source-inspection.json](../../verification/interop-completion/source-inspection.json) records precise upstream commits, blobs, read scopes and source/test/document distinctions. Native-thread callbacks and actual AOT execution are stronger evidence than compilation alone, but they do not prove the full product protocol, weak-memory soundness, arbitrary scheduler fairness, whole-process RSS bounds, NuGet deployment without Rust, or production load endurance. Full generated layout matrices, product failure injection, ownership accounting and target-specific verification remain assigned in D12 and the existing Delivery graph. No Loom, Kani, Miri, coverage-guided fuzz or sanitizer run is claimed by these experiments.

Independent review must reference the exact input hashes; the author does not mark its own results independently verified. Passing these fixtures is research evidence, not automatic contract or product acceptance.

## Committed CI replication

[CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies actual run `43388468172` at commit `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, on Windows and Linux. Every main fixture command succeeded with the same assertion counts. All 13 inputs match the committed bytes (Linux) or their checkout CRLF representation (Windows). The original local Linux run used an extra final blank line in Cargo.toml; [its exact source snapshot](../../verification/interop-completion/linux/source-snapshot.json) preserves all executed local bytes. Raw results are unchanged. Intentional reflection-fallback negative tests emit IL2026/IL3050; they are documented negative evidence, not an assertion of a warning-free product.
