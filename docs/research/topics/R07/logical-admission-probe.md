# R07: Independently Reproduced Logical Admission Record Developed in Parallel

Status: **normal Linux x64 consumption and NativeAOT actually executed; independent reproduction in parallel, with no additional Windows execution; research prototype, with no formal product implementation or contract acceptance.** The task remains R07, with D04 as its design basis; no new task system is established.

## Concurrent Recovery Note

During local implementation and execution, another session concurrently completed and merged [Design PR #8](https://github.com/IzuSharp/NativeWeave-Design/pull/8), merge commit `3767f3c932ebf95bd82f6ed1c9bafc9eec1c5b1e`. The current authoritative research entry point is the [merged study](logical-admission.md), whose source `28f6cf7e6e4e80b9f32a92ad587a528d82911bd0` / run `43373306474` already provides 653 assertions each for Windows/Linux normal execution and Native AOT, additionally covering lease return after a managed exception.

This record preserves the source files, individual assertions, NuGet PackageReference consumption, and Linux results independently produced before that remote update became known. It is independent reproduction evidence, no longer a claim to be the first to close NS-01, and the difference between 931/932 and 653 assertions does not imply broader coverage. Shared source-lifecycle CI does not rerun this equivalent fixture and runs only the new Database/Server scenarios. The hash of D04's latest evidence appendix is `d527369dfd97a2d97ecd0930e25effc523791eb5e22586b1d9e18ac6f4aa31c9`; c21e... below still correctly describes the historical input at the time of the local attempt, and original execution records must not be rewritten.

## 1. The Specific Gap Addressed

NS-01 in the earlier [R03 native slice results](../R03/native-slice-validation.md) explicitly states that keeping an existing SafeHandle call alive during Dispose does not prove that new business calls are rejected after logical closure. This round examines that boundary separately, without rerunning the old consumer's 185 assertions or the old Rust unit tests.

The results agree with the existing [R07 source analysis](report.md) and [D04 admission protocol](../../../contracts/lifetime-v0.1.md): while a native held call maintains a physical reference, a new Sum can still execute after Dispose on a simple `OwnedBuffer`; the short managed-gate candidate rejects the new Sum, allows the previously admitted call to complete normally, and finally returns the native live counter to 0. Success of the negative control means the limitation was observed, not that SafeHandle itself violated its physical-lifetime contract.

The pinned source basis for the earlier R07-S01 is `src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs` at dotnet/runtime `deae2e32bf0e018e09d64597b7c59b62b73bb3ce`: see the original report and evidence.json for how `DangerousAddRef` and `InternalRelease` handle Closed/Disposed and reference counts. This round does not relabel that source reading as new execution; the actual SDK/runtime identity used for this execution is separately recorded in this round's `dotnet-info.stdout`.

## 2. Pinned Inputs and Reuse Boundaries

The migrated native and managed package source from Design `c7e123a74405a92dc3de1ef450355b08d1c05ceb` is reused. Before copying, the runner checks destination SHA256 values against the original `migration-map.json`; builds occur in a temporary directory without modifying old migrated files, manifests, or hashes. The SHA256 of D04's current reference content is `c21e14010397330ba08f41db91d438c98f190f018130a3429f7f58b07f135bcb`; it remains proposed/reference content and is not automatically accepted by this experiment.

| Unmodified reused file | SHA256 |
|---|---|
| `experiments/native-slices/interop/native/Cargo.toml` | `1ec6048a2c40d4de73d59127db3cd4675bdf3fe43d04a20399dcae0cab51707d` |
| `experiments/native-slices/interop/native/Cargo.lock` | `e3e2ffee883d8ec7e0e3c2ca0c297f6ed6d17733c41c9f6df406491a6fa46f60` |
| `experiments/native-slices/interop/native/src/lib.rs` | `e4e632a1145a2148443fb795785dbc693305ca446a298bd840c2fe380187b5ef` |
| `experiments/native-slices/interop/managed/Bridge.cs` | `366f282bc9864e1bf72b4ef711774fb506a418555abceb73836cd249b28d7eef` |
| `experiments/native-slices/interop/managed/NativeWeave.Interop.Probe.csproj` | `f3568055889622ebff2b6b7369c647aadae96bd7a1d108a6ac0a09bac6fe8530` |

New code is in `experiments/interop-admission/consumer/AdmissionBuffer.cs` and `Program.cs`. The actual `.nupkg` is packed from the original managed project and includes the newly built native asset with the same name. The new consumer has only `PackageReference Include="NativeWeave.Interop.Probe" Version="0.0.1"`, with no ProjectReference. The runner checks that native bytes inside the package and AOT publish output both match the build artifact.

## 3. Controlled Execution Ordering and Oracle

Each execution mode sequentially runs 32 rounds of the simple SafeHandle negative control and 32 rounds of the short-gate candidate. Each round uses an independent owner, with lengths from 257 to 288; the consumer independently calculates the expected sum using the native data rule `i % 251`. Existing native test hooks are process-shared signals, so rounds run serially to avoid mistaking a previous round's signal for the next round's signal.

1. Confirm that the native live counter is 0 and reset the held signal.
2. A worker thread calls the real Rust `nw_buffer_sum_held`. The controller waits for the native entered flag; no step substitutes a fake managed task for native entry.
3. The worker holds a physical lease; the controller calls Dispose twice sequentially on the same thread, then checks that the worker is still in flight, the SafeHandle is not yet Closed, and the native live counter remains 1.
4. Before releasing the held call, the controller attempts a new Sum. The negative control must actually return the correct native sum; the candidate must throw ObjectDisposedException.
5. The controller releases the native held signal and joins the worker; the original call must return the correct value without error. It then checks that the owner is physically Closed and the native live counter is 0, remaining 0 after another Dispose.

The native held wait itself has a 10-second limit; the controller's entered wait and join each have a 5-second limit. A timeout is recorded as failure, not cancellation or success. No sleep is used to guess whether native code has acquired a lease. stdout retains every assertion with case, round, ID, expected, and actual.

## 4. Candidate Implementation and Semantics Supported by This Evidence

`AdmissionBuffer` privately holds the package's `OwnedBuffer`. A call checks `_closing` and acquires `DangerousAddRef` within the same short `lock`, then obtains the raw pointer, calls Sum or SumHeld outside the lock through an exact `LibraryImport` signature, and calls `DangerousRelease` in finally. Dispose sets `_closing` to true under the same gate and disposes the owner outside the lock; repeated Dispose returns inside the gate.

Closed and Closing therefore have clear responsibilities: physical references keep native memory valid for calls admitted earlier; Closing is the rejection point for new business admission. Before the candidate's new call throws, the test has already observed that the owner is not Closed and live=1, so rejection cannot be explained by "the old call has exited and the physical owner has been released." The code does not hold the gate while executing FFI, waiting for native code, calling user code, or executing native release.

This candidate addresses only the synchronous, read-only native summation in this experiment. It does not implement stop capability, callback quiescence, asynchronous retirement, mutable-owner serialization, parent-child ownership, finalizer/unload paths, or cancellation protocols; it cannot replace the remaining D04 clauses or D05/D06.

## 5. Raw Linux Results from This Round

The raw directory is `experiments/interop-admission/evidence/linux-local-attempt-1/`, starting at `2026-11-13T05:49:31.714302+00:00` and ending at `2026-11-13T05:51:36.082463+00:00`. This run used an uncommitted research worktree on the baseline commit, with `local_source_dirty=true`; original execution inputs and per-file hashes are retained, and it cannot be described as execution of a new Git commit. See the directory's toolchain output for SDK 11.0.100, Runtime 11.0.0, Rust/Cargo 1.100.0, and the actual Linux environment.

| Mode | Actual execution result | Negative control | Gate candidate | Resources at completion |
|---|---|---|---|---|
| `dotnet build` / `dotnet run --no-build`, both without RID arguments | 931 assertions passed | 32/32 new Sum calls admitted after Dispose and returned the correct value | 32/32 new Sum calls rejected; old calls returned the correct value | live=0 in every round |
| Execute the published file after `dotnet publish -r linux-x64 -p:PublishAot=true` | 932 assertions passed; additionally checks that dynamic code is unsupported and not compiled | 32/32 as above | 32/32 as above | live=0 in every round |

The total is 64 real held-call/Dispose sequences in each of two execution modes, or 128 rounds; this is not presented as exhaustive coverage of all races or all .NET runtimes.

| Actual artifact | SHA256 |
|---|---|
| native library | `889196ff36ad2e5c287aed56ca5a0ddddd3662051425c9a7b9ca37b1c836110b` |
| Local NuGet `.nupkg` | `8f2f482f5b70c1202f052911e9327eed7f971c9f6a847ecf64edcc75dc3ef079` |
| Linux NativeAOT `AdmissionProbe` | `a63b62d358d8290056643056e17a15c554a5d5dfc2f30f9a0d168e514a0b9ae5` |

Original binaries are stored in the local output directory's `binaries/`, including the extensionless Linux executable; every file's length and SHA256 are in `result.json`. The source repository retains their hashes, original inputs, and logs, but does not commit these local binaries; no remote binary artifact exists for this supplementary reproduction either. A local hash must not be treated as a permanently downloadable CI artifact; PR #8's primary evidence and artifacts have their own separate identities. The original commands.json records every command, exit code, start/end time, and log hash.

The runner executed in the local attempt has SHA256 `4b796d14b107b240f491b24cdf70d90e7f98a4a5d324edf6f7af7df6bcfa3778`. During the attempt, only early saving of failure artifacts and refusal to overwrite an existing attempt were strengthened in a later runner version; the archived runner has SHA256 `b8c62dce7b4ea57b918afacb726857400119781bb46463f55183f9719c77147e`. The three consumer C#/project inputs are byte-for-byte unchanged, and the original runner remains in `inputs/experiments/interop-admission/run.py`, with its execution hash unchanged. The archived runner was not executed again; local results are not presented as evidence for other commits or Windows CI.

## 6. Reproduction and Subsequent Boundaries

Run on a host with Rust 1.100.0, SDK 11.0.100, and the NativeAOT build prerequisites satisfied:

```sh
python experiments/interop-admission/run.py --out artifacts/interop-admission-linux
```

Windows can use the same entry point, with the runner selecting win-x64, but this supplementary fixture has no Windows execution result. `--output` is an alias; use a new output directory every time and retain failed attempts too. Prefer reusing PR #8's existing dual-platform evidence; this supplementary record does not justify rerunning equivalent scenarios.

Rust was installed and used on this machine, so these results are not proof of deployment to a clean Rust-free host. The old Windows 185 assertions cannot replace a new Windows experiment for this candidate before one is run. There is no fault injection, GC/finalizer stress, exhaustive arbitrary scheduling, or product-load data; no claim is made of zero cost, higher speed, complete shutdown guarantees, or product deliverability.

This research adds a real counterexample for NS-01 and controlled validation of a candidate, retaining D04's independent review and formal acceptance gates. R07 status, registry acceptance, and A/B Delivery must not be upgraded automatically as a result.
