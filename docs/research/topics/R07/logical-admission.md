# R07 / D04 — logical admission, physical lifetime and native mutation

Status: **source-inspected; finite two-platform Native AOT experiment executed; design decision reaffirmed; independent review pending**. This continues the existing R07/D04 work, not formal A03 Delivery. The latest phase remains research/design/planning. NativeWeave PR1 was closed without merge after Design PR7 and Plan PR4; its preserved history is not a current code destination.

## 1. Exact evidence and actual result

Executed Design commit **28f6cf7e6e4e80b9f32a92ad587a528d82911bd0**, Actions **43373306474**. Windows2022 x64 and Ubuntu24.04 x64 each passed ordinary .NET and actual Native AOT execution: **653 assertions, three groups and64 controlled gate/Dispose rounds per invocation**. The negative control was observed on both platforms; the candidate rejected post-close calls and retained existing calls. A managed exception after reference acquisition returned its lease in finally. Logs are in `verification/logical-admission/43373306474/`; source/native/AOT hashes and artifact ZIP identities are in `verification/logical-admission/primary-results.json`. This experiment rebuilds the unchanged native fixture for new managed scenarios; it does not rerun the old native test suites or rewrite migrated evidence.

Source reviewed: dotnet/runtime **deae2e32bf0e018e09d64597b7c59b62b73bb3ce**, `src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs`, actual inspected range130–265, blob **2d1f9313b485c57afab1f187e00a180df7fad3ba**. The complete265-line file was preserved and blob-verified. `DangerousAddRef` checks Closed; `InternalRelease` records Disposed separately and closes on final reference release. This proves the scope of SafeHandle's guarantee, not a defect in SafeHandle.

## 2. Counterexample and selected decision

The negative control uses the original static LibraryImport/SafeHandle facade. An earlier native SumHeld call holds a generated reference. Dispose releases the owning reference, but the last reference is not gone. A second Sum still succeeds. The object remains physically valid, so the test does not intentionally dereference stale memory. The stronger NativeWeave rule—no new ordinary business calls after logical close—therefore needs a separate gate.

**LA-01 decision: retain a private SafeHandle plus a short logical admission gate.** The admitted call must check Open and acquire its reference atomically under one synchronization protocol. Then it leaves the gate before FFI. Dispose transitions Open→Closing under that gate and releases its owning reference outside. The admitted operation's finally releases exactly its reference, whether native work succeeds or the managed adapter throws. A non-inheritable public facade must not expose its owning SafeHandle or raw pointer as an ordinary bypass route.

The compiled implementation is `experiments/logical-admission/Program.cs`, class GatedBuffer. Its exact research signatures are `ulong Sum(bool held = false, bool injectAfterLease = false)` and `void Dispose()`. The two Boolean arguments are fixture instrumentation, not proposed public API. The production generator emits the equivalent per-operation admission/reference/finally structure around each exact C ABI signature; it does not ship these test toggles.

| Transition | Linearization point | Required result |
|---|---|---|
| Open call admitted | Open check + successful DangerousAddRef inside same gate | The call may complete after later logical close |
| First Dispose | Closing written inside same gate | New ordinary calls fail; no callback/native wait under gate |
| Repeated Dispose | Closing observed | No second owning release |
| Admitted call fails | finally after successful acquisition | Its reference is returned even before/after FFI failure |
| Last reference ends | SafeHandle final release | Creating module's destructor runs; no alternate allocator |

The positive test performs Dispose on a separate Task while the native call is deliberately held. Dispose must finish before that native hold is released, so holding the admission lock across FFI would fail. A closed-facade Sum and SumHeld both must reject while native live-count is still1. The original call then completes with the expected value and count reaches0. These guided interleavings are not exhaustive scheduling or weak-memory proofs.

## 3. Three distinct protections, not one generic lock

| Protection | Owner | Does not establish |
|---|---|---|
| Business Open/Closing admission | Managed facade or an equivalent validated native admission profile | Exclusive mutation, remote effect, async retirement |
| Physical owner/reference lifetime | SafeHandle/native ownership protocol | That new business calls are still allowed |
| Mutable state exclusivity | Engine-local native guard or owner-worker protocol | Callback/source quiescence or durable database outcome |

A single managed lifetime gate released before FFI cannot protect two concurrent native `&mut` accesses. Conversely, keeping that gate held across native calls or callbacks risks blocking close/reentrancy and does not generalize to async work. These responsibilities stay explicit instead of adding a mandatory global handle table/runtime.

## 4. Database adapter impact — deeper reuse without unsafe aliasing

Re-read SeaQuery **1.0.2 / f2d5e04d30919c342da1f8845ff1fde46e3308fc**:

- `src/query/select.rs`, lines40–64, blob **f5d48689a7b88e3b17f855b67ad3b40af05c2940**: SelectStatement owns dynamic Vec/Condition/With state and derives Clone. It is not a Rust generic business Entity and is not an ABI-stable struct.
- `src/query/traits.rs`, lines5–25 and83–87, blob **7527dab633c156e6918bc4404b7d98b923760452**: native build borrows the statement, delegates to SqlWriterValues/backend rendering, and returns owned SQL plus ordered Values. Rendering does not require exporting or recreating the AST in C#.

**LA-02 proposed adapter refinement:** preserve native state behind an engine-local owner. For a thread-safe mutable query handle, take a shared reference to that live owner, then obtain mutable query access through its native guard. Do not first manufacture `&mut QueryOwner` from an opaque pointer and only then acquire a lock: exclusivity must already hold before creating such a mutable reference. A thread-affine profile may instead route commands to its owning worker. The exact profile is part of the Engine capability, not inferred from SafeHandle or Arc alone.

Suggested operation split (design obligations, not newly executed DB code): validate finite metadata/codec/capability inputs; admit and lease; serialize the native mutation; call SeaQuery's real API; release the mutation guard; return status; finally release the call lease. Rendering obtains a consistent native query view and produces a bounded owned SQL/Values result before leaving the builder ownership domain. The SQLx operation then owns its needed SQL/arguments/session references independently of the caller's builder wrapper. It must not hold a synchronous builder guard across await, I/O or reverse managed callbacks.

Do not clone the entire AST for every Fluent operator merely because Clone is available. In-place exclusive native mutation is the correctness reference; an explicit Clone/Fork operation may duplicate native state when the API really promises independent branches. Allocation/FFI cost requires measurement. Batched operation atomicity must explicitly choose prevalidation, rollback or builder invalidation; a partial mutation must never masquerade as no-op success. Unknown COMMIT and connection reuse remain D15 domain concerns, unaffected by local gate success.

SeaORM's dynamic module remains a real but unstable native alternative; this result neither disproves it nor proves it supplies complete runtime ActiveModel/relations. Preserve the existing R25 three-route comparison and scalar/NULL/projection/type checks. No SeaORM integration executable or PostgreSQL fault test was run in this study.

## 5. Server adapter impact — gate before dispatch, retirement after all owners

Re-read Tower **0.5.3 / 4b0a6b0e688bd177eb2c9c97f5268dd9703c66fc**, `tower/src/limit/concurrency/future.rs` complete ResponseFuture implementation, blob **2d8833692e3434f533900e2ae8cd637995eaf13e**. The permit is a field of ResponseFuture, not of the eventual arbitrary response Body. Its release follows actual future destruction, so merely observing Poll::Ready is not itself a destructor event. The already executed native Body tests demonstrate the relevant ordinary service composition where another request is admitted while the earlier body lives.

**LA-03 proposed ForeignService lifecycle refinement:** close route/request admission under a local gate, reserve the operation's owners before dispatch, and leave that gate before invoking native or managed handler work. A C# handler result can publish response headers while Body, byte leases and reverse-call context remain independently live. Closing the Server facade therefore stops new dispatch; it does not free existing bodies, cookies or pending control-call state. Keep native Service/Body/protocol implementations and send completion through their existing native future/channel seams; no C# HTTP parser or network core is introduced.

Keep three separate resource counters where applicable: admitted requests/live streams, retained payload bytes, and cleanup/retirement obligations. A stream slot is not a byte budget, Task completion is not callback silence, and the synchronous GatedBuffer experiment is not a C# Server Handler bridge. Actix worker-affine state and Tokio runtime shutdown retain their separate rules. No Rust Server default or performance winner is selected here.

## 6. Rust1.100 allocation, poisoning and safety boundary

The stable channel was freshly observed during migration on2026-11-13UTC/2026-11-12Los_Angeles and still identified Rust1.100.0; exact manifest and observed CLI identities are preserved under `verification/native-slices/`. Existing R01's detailed stable/unstable experiments are reused, not rerun. New language/library features do not remove admission, mutation or retirement requirements.

Re-read Rust **0ef1bc386059596dada8fb65b50425aab2ea637a**, `library/std/src/sync/poison/mutex.rs`, lines1–110, blob **42c5fcf3e27c02adf3d2143e30b5c77d2bf05491**. Its documentation explicitly treats poisoning as advisory and warns unsafe code not to depend on it for soundness. NativeWeave's D08 Engine poison state is a semantic fail-closed policy, not a proof that a partially moved raw allocation remains valid. Use memory-safe owned state and guard-based access regardless of whether poison detection fires; never automatically recover an unknown invariant with into_inner merely to keep serving.

DropGuard remains appropriate for local unpublished rollback; it does not enforce logical call admission. A custom Allocator must outlive its allocations, but does not serialize query mutation or bound every upstream allocation. Box/Arc map must not transform already-exported object identity. The additional gate does not justify a framework-wide allocator, scheduler or global runtime.

## 7. Future Codex acceptance, without starting Delivery

A03/A20 should consume the executed negative/positive traces, generate the gate/reference/finally pattern, and add randomized call/Dispose races, GC/finalizer/parent-child and mutable-resource cases. A06/A07 still need actual reverse async callback, start-return, cancellation-registration and control-call drain tests. B11 must add concurrent native mutation/render/clone and partial-batch failure tests under its chosen writer profile. B17 must add actual C# Handler→native Future completion plus body/cookie/retained-byte shutdown races. These are detailed future acceptance inputs, not tasks executed by this session.

The bounded design question LA-01 is resolved by source and finite execution: SafeHandle-only admission is insufficient for this stronger contract, and the explicit gate is the selected local approach. Full C-LIFETIME-001 acceptance still requires its remaining review/evidence; all formal contracts remain proposed. No throughput/RSS claim, exhaustive concurrency proof or product delivery is implied.

## CI trigger correction

A documentation-helper push unintentionally triggered run43374127432 with exactly the same tested inputs. It also passed and its separate32 raw files are preserved. It is not additional research coverage. `primary-results.json` retains the original run43373306474; `results.json` remains the actual latest run, and `ci-trigger-correction.json` records both. Execution triggers were narrowed; final documentation checks do not rerun native/managed scenarios.
