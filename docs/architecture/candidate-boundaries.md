# Candidate boundaries, implementation challenges and decision inputs

Status: design-draft; version 0.2.0-draft. The following is a design space to be investigated, not an accepted API/ABI. See [registry.json](../contracts/registry.json) for related contracts.

## 1. Separate minimal mechanisms from domain semantics

Evaluate four independent aspects:

| Aspect | Responsibilities | Must not assume |
| --- | --- | --- |
| Application and domain API | Natural C#, domain errors, cancellation and resource-usage patterns | Exposing raw pointers to ordinary applications |
| Per-engine Adapter | Strongly typed domain mapping, ownership/borrowing rules, capability selection | Forcing arbitrary domains into one “large object model” |
| Compile-time tools and ABI contracts | Type layout, generation, diagnostics, version checks and platform packaging | Adding a native scheduler to applications without Rust |
| Independent Rust Engine | Selected native libraries and internal implementation, the runtime needed by that engine | Depending on other engines' runtime state or downstream business logic |

These aspects do not have to correspond to four layers of runtime objects. Glue that can be eliminated through generated code does not automatically become a public runtime. Decide individually, based on cost, whether a common managed helper, native helper crate, handle table or shared runtime is needed.

## 2. Questions that ABI research must answer

The candidate ABI is the stable C ABI for each target; it is not one universal binary layout across OS/CPU combinations. Specify each struct's size/alignment/offset, the ABI for passing/returning values, valid enum values and pointer width.

Candidate rules: explicitly sized integers; a fixed-width 0/1 representation for bool; pointer+length for UTF-8; opaque handles; explicit out parameters for composite outputs. Further comparisons are needed for size_t/nuint versus u64 lengths, pointers versus generational tokens, return by value versus by address, and dynamic versus static linking. Directly exposing Rust Vec/String/Trait object/Future or C# managed-object layouts is prohibited.

The latest official AOT interop documentation states that, with runtime marshalling enabled in .NET11, a native call to UnmanagedCallersOnly with a non-blittable signature (such as a bool return or char parameter) fails fast; a catch inside the callback body cannot remedy this. The binding analyzer must validate the entire signature, and negative cases must execute under AOT in isolated processes. Direct P/Invoke also does not follow DefaultDllImportSearchPaths; the OS loader and linking policy require separate verification. [Official basis](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop)

C# 15 union and C ABI union are different issues. See the [toolchain report](../research/toolchain/report.md): value-type boxing in the default union, default/null behavior and non-boxing patterns must all be measured; modern syntax must not be treated as evidence of low cost.

ABI versioning must distinguish at least the product package version, engine version, ABI major/minor, capability version, and schema/generator version. Decide whether to negotiate a function table, use symbol versions or keep package components in lockstep through old/new combination loading experiments.

## 3. Ownership and safety invariants

For each resource r, define owner, live, active_leases, callbacks_inflight, native_obligations and closing. Candidate invariants:

- Release count free_count(r) ≤ 1.
- use(r) ⇒ live(r) ∧ valid_lease(r).
- free(r) ⇒ closing(r) ∧ active_leases(r)=0 ∧ callbacks_inflight(r)=0 ∧ native_obligations(r)=0.
- Before releasing a callback context, obtain confirmation that native code will no longer schedule that context and evidence that all callbacks in flight have exited; independently revoke and drain sources such as managed CancellationTokenRegistration that may access the context. Native quiescence does not replace managed cancellation-registration quiescence.
- A parent object must remain alive until the last child's native access ends; GC reachability is not a native lease.

Checking “handle != 0” cannot replace release-race control. SafeHandle's use-period reference and a long-lived native asynchronous reference serve different responsibilities. When explicitly extracting a raw handle, assess whether automatic reference protection still applies. Generational tokens can reduce ABA/stale-handle risk but introduce lookups, synchronization, counter overflow and reuse policies; a safety slogan must not force every synchronous function to use a table.

## 4. Model asynchronous results and resource quiescence separately

Candidate states have two dimensions:

| Dimension | Example states | Required clarification |
| --- | --- | --- |
| Result exposed to the application | Pending / Succeeded / Failed / Canceled | Unique linearization point; whether cancellation is a request or an outcome |
| Native resource usage | Running / StopRequested / Quiescent / Reclaimed | Whether the completion callback still holds context; which tasks stop confirmation covers |

For every operation o, terminal_publications(o) ≤ 1. This safety property does not prove that the operation eventually completes. Eventual reclamation also requires liveness assumptions such as executor progress, notification delivery, the shutdown protocol and fairness.

Database operations additionally require a separate effect state, such as NotSent, ConfirmedCommitted, ConfirmedRolledBack or Unknown. A Task becoming Canceled or Faulted cannot erase an Unknown durable effect; native resource quiescence, connection protocol recovery sufficient for reuse, and confirmation of the remote transaction effect are three separate promises and cannot substitute for one another.

Here, native_obligations counts only local cleanup obligations that still access the current resource's memory or must complete on that resource; it does not include the knowledge state “the remote commit outcome is still unknown.” An Unknown remote effect may be retained in an independent recovery record after local resources are safely reclaimed. If a connection's protocol state has not been confirmed clean, close and discard it; native quiescence alone does not permit returning it to the pool.

Completion may precede the return from start, and CancellationToken registration may invoke a callback synchronously; both must be tested. Synchronously waiting for native shutdown while holding a lock needed by the callback is prohibited. Clearly identify the execution threads for user continuations and FFI callbacks to avoid hidden synchronous reentrancy.

Compare the Task, ValueTask and IValueTaskSource candidates: the latter two are not unconditionally better, and reuse requires generation/tokens, a single-consumer constraint and protection against late notifications. Establish an understandable, correct state machine in the baseline before deciding whether pooling is worthwhile.

## 5. Data transfer and errors

Specify each buffer's allocator, deallocator, validity period, mutability, aliasing, alignment, and length/capacity units. Synchronous borrowing and asynchronous retention are different capabilities; retaining a pointer across await requires an explicit stable address and release point.

The default cost ledger records FFI calls, per-byte copying, allocations, GCHandle, native handles, threads and runtimes. Zero-copy is only a candidate optimization; explicit copying is permitted when proving source-memory safety is more complex and the benefit is insufficient.

Ordinary failures return Result/status. Panic containment must distinguish unwind from abort: catch_unwind cannot recover from abort, OOM abort or arbitrary foreign exceptions; panic hooks and payload destruction also require study. A C# reverse callback must catch handleable exceptions at the managed entry point and translate them into the contract's error/completion signal; managed exceptions must not cross the FFI boundary, nor may catch be claimed to recover from process-fatal faults. State explicitly whether damaged state remains usable; merely converting an error to an Exception does not establish engine recovery.

## 6. Database / ORM revised candidate boundaries

Database lower layers must be Rust; managed providers are comparisons only. The ordinary candidate uses precompiled dynamic SeaQuery AST/identifiers/values with SQLx execution. C# owns typed Fluent and static metadata/DTOs, not a SQL AST/dialect or full LINQ translator. Static SeaORM Entity remains a specialized profile; its native model-build coupling does not imply all Rust database integrations require per-entity compilation.

See ADR-0002, D14, D16/D17 and R25's source study. Direct native builder is the reference route; batching requires measurements, not a preselected universal IR. Explicit SQL null/collation/join/pagination and codec semantics remain mandatory. Reject SQLite silently omitted clauses and use fallible native binding. Unknown transaction effect, protocol reuse and local retirement remain independent.

## 7. Server candidate boundaries

Pure C# AOT + Kestrel is a mature baseline that must be compared; a Rust engine is the required lower layer for the formal Server, and the specific Rust combination is determined by source evidence, correctness and maintenance cost. Comparison results must not be concealed. The programming experience of ordinary C# handlers, request contexts, cancellation and stream lifetimes should be independent of the engine.

Draw clear HTTP/TLS ownership boundaries so that two implementations do not handle the same layer of protocol state simultaneously. gRPC/MCP may serve as higher-level protocol adapters without becoming mandatory dependencies of every engine. The instability of Hyper's C API does not diminish the research value of its Rust library; if selected, NativeWeave explicitly defines and verifies the stable external contract.

Traffic budgets include at least active_connections, active_requests, queued_requests and buffered_bytes. Candidate boundedness property:
accounted_work_bytes ≤ Σ(connection_budget) + active_requests×request_budget + bounded_queue_budget.
This is only a logical bound on memory in use under the assumption that all corresponding objects are budgeted; it cannot be treated directly as an RSS upper bound. Actual RSS also includes allocator retention, fragmentation, the GC heap, thread stacks, code and runtimes; kernel socket/TLS buffers also need separate accounting. Limiting queue item counts without limiting request-body size cannot prove bounded memory. Test HTTP/2 multiplexing, slow readers, half-close, client abort, TLS handshakes and graceful shutdown separately.

## 8. Reference application and proof using two real Engines

The candidate reference application is a “work-item and attachment service,” with no ArcForges business dependency. Features: create work items, search by criteria, atomic modification with outbox records, paginated/streaming reads, and attachment compression/download. Include a PostgreSQL route; run SQLite only in scenarios where it actually applies, without erasing differences in concurrency or SQL semantics.

Stress and failure scenarios: pool exhaustion, slow clients, DB disconnects, unknown commit outcomes, cancellation/response races, service restarts, migration conflicts, duplicate requests and backpressure. Keep the dataset, protocol, TLS, payload, request distribution, error semantics and hardware comparable across stacks.

The formal choice of the two Engines has not yet been accepted. Synchronous and asynchronous streaming modules verify different capabilities; a research prototype of any module must not be represented as a complete production implementation.

## 9. Work that can be written in parallel now and work that must wait

May proceed in parallel: candidate ABI layouts, state machines, generator design, database semantics, native query bindings, server boundaries, packaging matrix, performance methodology and domain task fragments.

Genuine prerequisites: acceptance of the exact contract version on which a task's formal implementation depends, availability of evidence for that route, and local review of shared changes. “All research complete” is not a universal prerequisite, and there is no shortcut around contract acceptance.

## 10. What remains unproven

The invariants above are proof obligations, and candidate interfaces are not compilation results. The recovered and migrated Actions already include actual NuGet packaging, ordinary consumption without an RID, and Native AOT execution for Windows/Linux Interop; finite Rust Database/Server fixtures on both platforms; and earlier finite Linux/SQLite C#/Rust query AOT execution. See the [migration record](../traceability/research-asset-migration.md) for source, actual execution commits and artifact identities. These records do not establish clean Rust-free consumer hosts, PostgreSQL, complete C# Database/Server AOT, performance or production memory bounds; the earlier recovery observation that “no compiler is available locally and no Windows results exist” is outdated. See the [continuation checkpoint](../traceability/source-lifecycle-followup.md) for the added lifecycle research. A common runtime need not be built in advance to prove “simplicity”; narrow the candidates progressively using source research, models, minimal prototypes, actual AOT and workload evidence.

## 11. Source-driven Engine maintenance

[D11](../extension/engine-integration.md) defines public/source-informed/extension/fork integration. [D10](../platforms/build-package-release.md) separates maintainer native builds from ordinary C# consumption and specifies source/closure pins and upgrade differential gates. Core owns no domain SQL or Server state. These amended contracts remain proposed; previous reviews do not approve new hashes.
