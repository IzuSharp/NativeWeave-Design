# R07: Independent logical-admission reproduction produced in parallel

Status: **Linux x64 normal consumption and NativeAOT actually executed; independent parallel reproduction, with no new Windows execution; research prototype, without formal product implementation or contract acceptance.** The task remains R07 and the design basis D04; no new task system is created.

## Concurrent recovery note

During local implementation and execution, another session concurrently completed and merged [Design PR #8](https://github.com/IzuSharp/NativeWeave-Design/pull/8), merge commit `3767f3c932ebf95bd82f6ed1c9bafc9eec1c5b1e`. The current authoritative research entry is the [merged study](logical-admission.md), whose source `28f6cf7e6e4e80b9f32a92ad587a528d82911bd0` / run `43373306474` already provides 653 assertions each for Windows/Linux normal execution and Native AOT, additionally covering lease return after a managed exception.

This record preserves independently written source files, individual assertions, NuGet PackageReference consumption and Linux results produced before that remote update became known. It is independent reproduction evidence, no longer a claim to be the first to fill NS-01; neither does the 931/932 versus 653 assertion-count difference imply wider coverage. Shared source-lifecycle CI does not rerun this equivalent fixture and runs only added Database/Server scenarios. The latest D04 evidence appendix has hash `d527369dfd97a2d97ecd0930e25effc523791eb5e22586b1d9e18ac6f4aa31c9`; c21e... below still correctly describes the historical input at the time of the local attempt, and original execution records must not be rewritten.

## 1. Specific gap addressed

NS-01 in the earlier [R03 native-slice results](../R03/native-slice-validation.md) explicitly states that an existing SafeHandle call staying alive during Dispose does not prove rejection of new business calls after logical closure. This experiment tests that boundary separately without rerunning the old consumer's 185 assertions or old Rust unit tests.

The result matches existing [R07 source analysis](report.md) and the [D04 admission protocol](../../../contracts/lifetime-v0.1.md): while a native held call retains a physical reference, a new Sum can still execute after Dispose of a simple `OwnedBuffer`; the short managed-gate candidate rejects the new Sum, permits the earlier call to complete normally, and ultimately returns the native live counter to 0. A successful negative control means the limitation was observed, not that SafeHandle itself violates its physical-lifetime contract.

The earlier R07-S01 pinned-source basis is dotnet/runtime `deae2e32bf0e018e09d64597b7c59b62b73bb3ce`, `src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs`: see the original report and evidence.json for `DangerousAddRef` and `InternalRelease` handling of Closed/Disposed and reference counts. That source reading is not relabeled as new execution; this run's `dotnet-info.stdout` separately records the SDK/runtime identity actually executed.

## 2. Pinned inputs and reuse boundaries

Reuse the native and managed package source already migrated at Design `c7e123a74405a92dc3de1ef450355b08d1c05ceb`. Before copying, the runner checks destination SHA256 values from the original `migration-map.json`; builds occur in a temporary directory without modifying old migrated files, manifests or hashes. The D04 reference content SHA256 is `c21e14010397330ba08f41db91d438c98f190f018130a3429f7f58b07f135bcb`; it remains proposed/reference content and is not automatically accepted by this experiment.

| Unmodified reused file | SHA256 |
|---|---|
| `experiments/native-slices/interop/native/Cargo.toml` | `1ec6048a2c40d4de73d59127db3cd4675bdf3fe43d04a20399dcae0cab51707d` |
| `experiments/native-slices/interop/native/Cargo.lock` | `e3e2ffee883d8ec7e0e3c2ca0c297f6ed6d17733c41c9f6df406491a6fa46f60` |
| `experiments/native-slices/interop/native/src/lib.rs` | `e4e632a1145a2148443fb795785dbc693305ca446a298bd840c2fe380187b5ef` |
| `experiments/native-slices/interop/managed/Bridge.cs` | `366f282bc9864e1bf72b4ef711774fb506a418555abceb73836cd249b28d7eef` |
| `experiments/native-slices/interop/managed/NativeWeave.Interop.Probe.csproj` | `f3568055889622ebff2b6b7369c647aadae96bd7a1d108a6ac0a09bac6fe8530` |

New code is in `experiments/interop-admission/consumer/AdmissionBuffer.cs` and `Program.cs`. The actual `.nupkg` is packed from the original managed project and includes the newly built native asset of the same name. The new consumer has only `PackageReference Include="NativeWeave.Interop.Probe" Version="0.0.1"`, without ProjectReference. The runner checks that native bytes in both the package and AOT publish output match the build artifact.

## 3. Controlled execution order and oracle

Each execution mode sequentially runs 32 rounds of the simple SafeHandle negative control and 32 rounds of the short-gate candidate. Every round uses an independent owner, with lengths from 257 to 288; the consumer independently computes the expected sum according to the native `i % 251` data rule. Existing native test hooks use process-shared signals, so rounds run serially to avoid mistaking a previous round's signal for the next.

1. Confirm the native live counter is 0 and reset the held signal.
2. A worker thread calls actual Rust `nw_buffer_sum_held`. The controller waits for the native entered flag; no step substitutes a fake managed task for native entry.
3. While the worker retains the physical lease, the controller sequentially calls Dispose twice on the same thread, then checks that the worker remains in flight, SafeHandle is not yet Closed and the native live counter remains 1.
4. Before releasing the held call, the controller attempts a new Sum. The negative control must actually return the correct native sum; the candidate must throw ObjectDisposedException.
5. The controller releases the native held signal and joins the worker; the original call must return the correct value without error. Then verify that the owner is physically Closed, the native live counter is 0 and another Dispose leaves it at 0.

The native held wait itself has a 10-second limit; the controller's entered wait and join each have a 5-second limit. Timeout counts as failure rather than cancellation or success. No sleep guesses whether native code has acquired the lease. stdout preserves every assertion with case, round, ID, expected and actual.

## 4. Candidate implementation and semantics supported by this evidence

`AdmissionBuffer` privately holds the package's `OwnedBuffer`. A call checks `_closing` and acquires `DangerousAddRef` inside the same short `lock`, then obtains the raw pointer, invokes Sum or SumHeld outside the lock through the exact `LibraryImport` signature, and executes `DangerousRelease` in finally. Dispose sets `_closing` to true under the same gate and disposes the owner outside the lock; repeated Dispose returns inside the gate.

Closed and Closing therefore have distinct responsibilities: physical references keep native memory valid for calls that entered earlier; Closing rejects new business admission. Before the candidate's new call throws, the test has already observed the owner not Closed and live=1, so rejection cannot be explained as “the old call exited and the physical owner was released.” The code holds no gate while executing FFI, waiting for native code, invoking user code or executing native release.

This candidate covers only this synchronous, read-only native sum. It implements no stop capability, callback quiescence, asynchronous retirement, mutable-owner serialization, parent-child ownership, finalizer/unload path or cancellation protocol; it does not replace the rest of D04 or D05/D06.

## 5. Raw Linux results from this run

The raw directory is `experiments/interop-admission/evidence/linux-local-attempt-1/`, starting at `2026-11-13T05:49:31.714302+00:00` and ending at `2026-11-13T05:51:36.082463+00:00`. This run used an uncommitted research workspace on the baseline commit, with `local_source_dirty=true`; original execution inputs and per-file hashes are retained, so it must not be described as execution from a particular new Git commit. SDK 11.0.100, Runtime 11.0.0, Rust/Cargo 1.100.0 and actual Linux details appear in that directory's toolchain output.

| Mode | Actual execution result | Negative control | Gate candidate | Final resources |
|---|---|---|---|---|
| `dotnet build` / `dotnet run --no-build`, neither with an RID argument | 931 assertions passed | 32/32 new Sum calls still admitted after Dispose and returned the correct value | 32/32 new Sum calls rejected; old calls returned the correct value | live=0 every round |
| Execute the published file after `dotnet publish -r linux-x64 -p:PublishAot=true` | 932 assertions passed; additionally checked that dynamic code is unsupported and uncompiled | 32/32 as above | 32/32 as above | live=0 every round |

The total is 64 actual held-call/Dispose sequences in each of two execution modes, 128 rounds overall; this is not advertised as exhausting all races or all .NET runtimes.

| Actual artifact | SHA256 |
|---|---|
| native library | `889196ff36ad2e5c287aed56ca5a0ddddd3662051425c9a7b9ca37b1c836110b` |
| Local NuGet `.nupkg` | `8f2f482f5b70c1202f052911e9327eed7f971c9f6a847ecf64edcc75dc3ef079` |
| Linux NativeAOT `AdmissionProbe` | `a63b62d358d8290056643056e17a15c554a5d5dfc2f30f9a0d168e514a0b9ae5` |

Original binaries are stored in `binaries/` under the local output directory, including extensionless Linux executables; `result.json` records each file's length and SHA256. The source repository retains their hashes, original inputs and logs rather than commit these local binaries; no remote binary artifact exists for this supplemental reproduction. A local hash must not be treated as a permanently downloadable CI artifact; PR #8 primary evidence and artifacts have their own separate identities. Original commands.json records every command, exit code, start/end time and log hash.

The runner executed in the local attempt has SHA256 `4b796d14b107b240f491b24cdf70d90e7f98a4a5d324edf6f7af7df6bcfa3778`. During the attempt, only the later runner version was enhanced to save failure artifacts earlier and “reject overwriting an existing attempt”; the archived runner SHA256 is `b8c62dce7b4ea57b918afacb726857400119781bb46463f55183f9719c77147e`. The three consumer C#/project input files remained byte-identical, and the old runner text remains in `inputs/experiments/interop-admission/run.py` without rewriting its execution hash. The archived runner was not executed again; local results do not masquerade as evidence from another commit or Windows CI.

## 6. Reproduction and subsequent boundaries

Run on a host with Rust 1.100.0, SDK 11.0.100 and NativeAOT build prerequisites satisfied:

```sh
python experiments/interop-admission/run.py --out artifacts/interop-admission-linux
```

Windows can use the same entry point, with the runner selecting win-x64, but this supplemental fixture has no Windows execution result. `--output` is an alias; use a new output directory each time and retain failure records too. Prefer reusing PR #8's existing two-platform evidence rather than rerun equivalent scenarios because of this supplemental record.

Rust was installed and used on this machine, so the result is not proof of deployment to a clean Rust-free host. Until a new Windows experiment for this candidate has run, the old Windows 185 assertions cannot substitute. There is no fault injection, GC/finalizer stress, exhaustive arbitrary scheduling or product-load data; no claim is made of zero cost, higher speed, complete shutdown guarantees or product readiness.

This study adds an actual NS-01 counterexample and a controlled candidate validation while retaining D04 independent review and formal acceptance gates. R07 status, registry acceptance and A/B Delivery must not be automatically upgraded on this basis.
