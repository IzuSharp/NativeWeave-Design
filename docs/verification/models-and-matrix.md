# D12 — Proof obligations, experiments and implementation acceptance

Contract **C-VERIFY-001@0.3.0**. Complete research/design candidate; the registry records the exact reviewed version/hash and acceptance. Product verification remains in Delivery. Inputs R15/R16/R34 and the actual per-domain evidence. This specification defines how future A19/A20/A21/B22/B23 evidence is produced; it is not a claim that NativeWeave product tests have run.

## 1. Two acceptance scopes

**Research/design acceptance** requires a clear decision, fixed and actually read sources, normal/error/boundary analysis, experiments needed to resolve the question, concrete interfaces/state/ownership rules, independent review of exact content, and explicit future obligations. A design can be accepted before the product implementation exists.

**Implementation/release acceptance** additionally requires the product implementation at its exact commit to satisfy the specified real platform, protocol, package, fault, resource and performance tests. A research fixture does not satisfy this gate by sharing a task ID, function name or architecture.

Do not close a research task solely because files exist, nor keep a fully reviewed design permanently incomplete because its future implementation has not been written. Source-target breadth is judged by the decision: inspect adopted code and plausible alternatives sufficiently to justify the choice; unrelated paths remain recorded as not adopted/not read rather than invented coverage. A genuinely unresolved technical fact stays an explicit research blocker with evidence and next action.

## 2. Evidence kinds and exact identity

| Kind | What it establishes | What it cannot establish |
|---|---|---|
| Source read | Fixed revision's implementation or test intent, within listed ranges | That a test was executed, that all callers are safe |
| Compiled | Compiler accepted the exact source/configuration | Executed behavior, AOT execution, other OS support |
| Executed normal | Concrete command/binary and its checked assertions | Native AOT equivalence or all schedules |
| Native AOT executed | PublishAot produced an executable that actually ran on recorded target | Other RID, production implementation, realistic speed |
| Finite model | Listed invariants under declared state bounds and transition assumptions | Weak memory, arbitrary native code, global liveness |
| Independent review | A different real agent/person checked named immutable inputs and findings | A separate GitHub account approval or executed production acceptance |

Each run record contains source repository/commit or exact uncommitted source hashes with baseline commit, toolchain identity, OS/architecture/RID, command argv/cwd, UTC start/end, exit code, raw stdout/stderr hashes, test seeds/oracles and artifact hashes. A nonzero command or timeout remains visible. If a required AOT publication fails, the runner fails; normal success cannot turn its job green. Current and historical runs keep different records and source identities.

Exact-source review uses a manifest excluding itself, with per-file SHA-256 and an ordered scope list. A reviewer records which files, source ranges and commands they actually inspected/executed. Integration can separately hash that manifest; avoid circular hashes or claiming a working-tree experiment already existed in a prior commit. Later source/spec changes invalidate the relevant prior acceptance subject, not unrelated evidence.

## 3. Required invariants

### Ownership and ABI

For each owned resource: successful create transfers exactly one owner; failures leave out-owner empty; each acquired lease is compensated on exceptions; creator and destructor match; free occurs at most once; all memory access is covered by a live owner/lease. Call-scoped borrowing cannot escape into async/native queues. Length/offset arithmetic is checked before constructing slices or allocating. Null+zero is handled without forming an invalid Rust reference.

### Async/callback

Native terminal commits at most once; cancellation request is not a terminal. Result take is once-only and independent of operation retirement; a transferred owner cannot be reclaimed by duplicate notifications or operation release. Context free requires native producer closure and callback quiet **and** managed setup/start-return, control/callback lease and cancellation-registration drain. Notification mailbox scheduling must not lose a wake during store/drain/unschedule.

### Domain effects

Commit acknowledgment loss can leave transaction effect Unknown; cleanup outcome cannot overwrite it. Returning a connection to a pool requires backend protocol/session cleanliness. HTTP head completion does not prove Body completion; Body EOS does not prove backing allocation release. Flow-control credit is not a memory-owner counter. Native runtime shutdown timeout is not a proof of stopped blocking work or joined threads.

## 4. Tool selection by property

| Mechanism | Selected use | Explicit limit |
|---|---|---|
| Existing Python finite transition models | Explain and replay lifecycle counterexamples; state graph/negative controls | Sequentially consistent atomic abstract steps, small declared operation counts |
| Loom | Explore Rust synchronization algorithms when implementation uses Loom-instrumented primitives | Only declared scheduling/state bounds and instrumented operations; does not execute CLR/FFI |
| Miri | Detect Rust UB in supported pure/native pieces with valid harnesses and varied seeds | No full CLR/network/OS FFI; incomplete weak-memory coverage; passing execution is not soundness proof |
| Kani | Bounded scalar/index/ownership helper obligations with explicit unwind/problem bounds | Insufficient unwind is failure/undetermined; cannot call it an unbounded system proof |
| proptest or equivalent deterministic property driver | Shrinking and replay of scalar/codec/shape domains | Oracle correctness must be independently checked; random success is not exhaustive |
| cargo-fuzz/libFuzzer | Coverage-guided valid-memory parsers/codecs and serialized request boundaries | A time/coverage budget and corpus are required; unsupported sanitizers are not passed tests |
| Real C#/Rust/Native AOT process | Actual imports/UCO/GC/cancel, ABI/layout, platform loading | Finite schedules and fixture scope; not production soak or performance by default |

Pinned Loom builder, Miri limitations, Kani unwinding and proptest persistence sources are recorded in [source-inspection](../../verification/interop-completion/source-inspection.json). Tool names are not evidence of execution. TLA+/Coyote remain available when a concrete algorithm/property benefits; do not add an infrastructure prerequisite merely to list more tools.

## 5. Positive and negative controls

Every model/property fixture must include a non-vacuity check: a legal success path reaches a usable result and a recoverable cleanup state. Where practical remove one guard or perturb one semantic rule to show the oracle detects the named failure. Negative controls must distinguish memory-safety violations from cleanup contract violations; e.g. missing cancellation-registration drain does not automatically prove native use-after-free when other leases still protect native state.

Existing `experiments/async-quiescence` and R09 retirement models preserve their original counterexamples and limitations. The R07 logical-admission experiment has a safe negative control: SafeHandle alone allows a post-Dispose call while an earlier reference remains; it does not intentionally dereference freed memory. New `interop-completion` checks callback blocks retirement, duplicate completion is rejected, result ownership survives operation release, and DTO conversion failure releases that result. Its seeded extent comparison uses **BigInteger** as an independent C# oracle for Rust checked multiplication and isize/budget bounds.

Fatal input tests run in child processes: invalid UCO ABI, abort panic strategy, destructor/hook double panic and deliberately invalid memory must not terminate the ordinary test runner or be executed as safe-pointer fuzz cases. Their expected outcome is explicit nonzero termination/diagnostic, not merely any crash. The main interop fixture catches an ordinary managed callback exception. Separate panic-linux and uco-invalid-linux manifests now record explicitly scoped fatal child cases; they do not cover arbitrary invalid memory, all signatures or Windows fatal behavior.

## 6. Platform and package matrix

| Layer | Required future execution |
|---|---|
| ABI/import/export | C/Rust/C# size/offset/symbol probes; Windows x64 MSVC and Linux x64 GNU actual binaries |
| Application surface | Ordinary `dotnet build` and `dotnet run` without application Cargo; actual Native AOT publish/run per RID |
| Distribution | Independently restored NuGet package in a clean consumer workspace; matching native asset hash and ABI identity |
| Async/ownership | Controlled callback/start/Dispose/cancel barriers, GC/finalizer pressure, result conversion failures, repeated cleanup |
| Database | Actual PostgreSQL and SQLite; protocol cancellation/resync, transactional effect, connection retirement, typed values and schema behavior |
| Server | Real socket HTTP/TLS/protocol workloads; slow body, half-close, reset, retained chunks, drain and handler cancellation |
| Upgrade | Old/new managed/native pairs; missing capability/symbol; provider feature differences and deterministic rejection |

JIT/normal execution, AOT compilation and AOT execution are separate rows. Windows results never stand in for Linux or vice versa. Mobile/Arm64/GPU profiles keep their own support criteria under D21. A test on a host that also has Rust installed is not a clean Rust-free consumer proof even if the consumer command did not invoke Cargo.

## 7. Fuzz, faults and resource accounting

Persist deterministic PRNG seed, generator version, original and minimized failing input, corpus hash, sanitizer flags, environment class and reproduction command. A minimized input alone is insufficient if shrink behavior or schema changed; version the decoder and oracle. Compare query results and effects against the direct Rust/database engine for the same dialect/parameters, not against textual SQL equivalence only.

Inject failure at every ownership acquisition/transfer boundary: native create rejection; allocation/reserve; managed wrapper allocation; registration; start rejected/accepted; callback mapping; result take/DTO conversion; protocol flush; worker stop and cleanup timeout. Record which side owns each resource after injection. Do not retry unknown-effect writes merely to obtain a passing test.

Resource observations include live native objects, managed roots/pins, operation/queue/waiter counts, owned versus retained payload capacity, pool connections, threads, file descriptors/handles, cleanup backlog and process RSS/managed allocation. Counters returning to zero for a fixture do not prove zero process memory retention. Long-load baselines and headroom belong to D13/B22/B23 and must include steady state, overload and recovery windows.

## 8. Required future task outputs

A19 maps each abstract transition to actual lock/CAS/acquire-release code and preserves bounded counterexamples. A20 owns ABI/layout/ownership property/fuzz corpus and valid-memory vs fatal-process separation. A21 owns comparable benchmark tooling. B22 owns real combined-domain fault/long-run evidence; B23 measures product performance/memory with honest confidence and comparators. D32 independently reviews exact scope and decides research/design acceptance separately from these future implementation obligations.

The concrete current evidence is indexed in `verification/interop-completion/`; prior verified artifacts remain at their original paths and hashes. No current graph status should imply that a new product executable, full FFI fuzzer, sanitizer sweep or production load test exists when only a study has run.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
