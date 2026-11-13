# Final independent Interop review — 2026-11-13

Reviewer: `/root/interop_review`. This is a distinct subagent execution, independent of the authors listed in the JSON. It is a technical review, **not another GitHub identity or GitHub approval**. The reviewer changed only these two review records; the integrator authored the corrections.

## Decision

Accept the named **13 Research tasks, 12 Documentation tasks and 9 contract designs** for research/detailed-design purposes at the exact hashes in `interop-review.json`. There is **no remaining blocking finding within this scope**. The named 14 Delivery packets are ready as future implementation instructions. No product implementation, release, long-load run or product authorization is accepted.

## Findings resolved

| Finding | Issue | Verified resolution |
| --- | --- | --- |
| FINAL-INTEROP-01 (low) | D03 UniFFI backend attribution | Integrator clarified that C# binding/backend is third-party, distinct from official language generators. Current complete paragraph re-read. |
| FINAL-INTEROP-02 (medium) | A05 poison policy drift | A05 now poisons the owning Engine after every contained native panic and permits only explicitly trusted cleanup; packet and fragment match. |
| FINAL-INTEROP-03 (low) | A03 finite test scope | A03 now covers named boundary schedules under recorded operation/thread/preemption bounds; packet and fragment match. |

## Task-by-task disposition

| Task | Result and substantive basis | Future obligation remains |
| --- | --- | --- |
| R03 | Accept design: Fixed-width ABI, explicit size/capability evolution and pointer provenance are well-defined. Existing two-OS layout evidence and new BigInteger extent/UCO probes support the scoped decision. | A01/A02/A12 full generated C/Rust/C# public matrix and A22 binary compatibility remain implementation gates. |
| R04 | Accept design: LibraryImport/DllImport alternatives, UCO signature limits, callback roots and structural boundary costs are supported by generated binding and normal/AOT records. | A06/A07/A10-A12 full wrappers; A14/A15 all published shapes; A21/B23 actual workload cost. |
| R05 | Accept design: Seven generator alternatives are distinguished by actually inspected ranges; the csbindgen omitted-export counterexample and primitive normal/AOT comparison justify inventory validation. | A09-A12 implement the production semantic sidecar, emitter, linked export inventory and complete diagnostics. |
| R06 | Accept design: The real nine-check compiler-driver probe and fixed Roslyn/framework source support value-equatable metadata and no same-pass peer-output dependence. | Multi-target IDE/package/generator cancellation and actual public consumer conformance remain Delivery. |
| R07 | Accept design: SafeHandle Closed-vs-Disposed behavior was independently re-read. Logical admission, physical lifetime, parent ownership and transferred result lifetime are separately specified and evidenced. | A03/A04/A20/A23 complete parent-child/finalizer/affine/weak-memory and long-load behavior. |
| R08 | Accept design: Real native-thread UCO, GC roots and cancellation-registration drain support stop/retire and independent managed dispatcher drain. Registration/callback self-wait is explicitly excluded. | A06/A07/A20 full subscription dispatcher, allocation failure, saturation and lifecycle races. |
| R09 | Accept design: Immutable native terminal, take-once output and result independence are evidenced; the 541-state retirement and 17/11-state mailbox results retain exact limits and negative controls. | A07/A08/A19/A20 full setup compensation, latch failures, weak-memory mapping, saturation and poison recovery. |
| R10 | Accept design: Checked extent uses a different BigInteger oracle; result transfer and Bytes owner source establish the chosen borrow/copy/retain boundaries without a zero-copy or hard-RSS claim. | A04/A20/B06/B07/B12/B16/B17 complete codec/ownership/retained-memory product cases. |
| R11 | Accept design: Seven retained panic-process records, ordinary callback containment and two invalid-UCO child failures support D08 containment/fatal distinctions. Nonzero expected cases were not hidden. | A05/A06/A07/A14/A15/A20/B22 full concurrent poison, Windows fatal and long-run quarantine cases. |
| R12 | Accept design: Tokio Runtime/Handle and shutdown semantics were independently re-read; engine-local runtime, actual quiet, managed drain and OS joins stay separate. | A08/B04/B20 full scheduler/runtime close, worker affinity and long-load behavior. |
| R15 | Accept design: Existing abstract retirement model and new mailbox model contain real negative controls, nonvacuity and stated SC bounds. Loom/Miri/Kani are selected by property with no false execution claim. | A19/A20 map actual implementation lock/CAS/memory-ordering and scope instrumented tools. |
| R16 | Accept design: The corpus/replay/oracle/fatal-process strategy follows executed representative properties and preserved failures; no sanitizer/fuzz campaign is fabricated. | A20/B22 production fuzz corpus, supported sanitizers, fault injection and long-load runs. |
| R34 | Accept design: Trust domain, raw slice preconditions, checked arithmetic, capability/owner rules, bounded data and diagnostic privacy are explicit. The Rust slice requirements were independently re-read; protocol claims link scoped server evidence and cardinality correction. | A20/B07/B16/B18/B19/B22/B24 product hostile-data, protocol, dependency and resource testing; no in-process sandbox claim. |
| D02 | Accept design: Complete selected wire representations, bootstrap, capacity semantics, ownership annotations and version rules; D08 is the status authority. | A01/A02/A10-A12/A14/A15/A22 implement and verify complete public ABI inventory. |
| D03 | Accept design: A narrow semantic sidecar supplements authoritative Rust exports; pipeline order, omission checks, deterministic model identity and diagnostic IDs are implementable. Third-party UniFFI wording was corrected and re-read. | A09-A12 full product generator/diagnostics and independent package consumption. |
| D04 | Accept design: Logical gate and SafeHandle lease have a common linearization protocol; parent state, async obligations, module lifetime and nonblocking finalizer rules are distinct. | LT-01 through LT-06 in A03/A06/A07/A14/A15/A18/A20/A21/B22. |
| D05 | Accept design: Create/start failure atomicity, no-future-callback retirement, fixed cookie lifetime, bounded dispatcher, discard-pending/join-active disposal and self-wait rules are complete. | CB-01 through CB-07 in A06/A07/A08/A12/A14/A15/A18/A19/A20/A21/B22. |
| D06 | Accept design: Three setup/result/cleanup dimensions, explicit NoRegistration/StartSkipped/Indeterminate sentinels, once-only terminal/take and preallocated failure latch give implementable cleanup ordering. | AS-01 through AS-08; product coordinator, weak memory and complete fault injection remain pending. |
| D07 | Accept design: Contiguous view, caller provenance, checked extents, creating-module release and explicit async copy/retain policy prevent escaped naked views; byte budgets follow owners. | A04/A20 and domain batch/body/codec/long-memory gates. |
| D08 | Accept design: Unique u32 status authority and full 24-byte ErrorRecord capacity/write algorithm are unambiguous. Ordinary callback failure preserves native effect; every contained native panic poisons the engine and retains honest cleanup limits. | ER-01 through ER-07, including target-specific child failures and quarantine resource costs. |
| D09 | Accept design: Instance profiles/states, coalesced bounded mailbox, permit ownership, internal cleanup capability and ordered close/resource/worker semantics are complete without mandatory Core runtime. | A08/B04/B16/B17/B20 and relevant lifecycle/affinity/long-load gates. |
| D12 | Accept design: Research/design and implementation/release evidence are explicitly separated. Fixed identities, source-only limits, negative controls, platform rows and replay metadata are sufficient for execution planning. | A19/A20/A21/B22/B23 actual product proof, fuzz/fault and benchmark execution. |
| D22 | Accept design: Five existing A01-A05 tasks have consistent interfaces, disjoint file scopes, dependency references and concrete tests. A05 poison and A03 finite-schedule wording corrections were re-read. | No A01-A05 implementation is accepted or authorized by this documentation review. |
| D23 | Accept design: Four existing A09-A12 tasks preserve generator authority, raw/full wrapper distinction, exact upstream omission negatives and separate compiler-host/consumer target constraints. | A10 early fixed fixture is not real A07 closure; A14/A15 must test completed assembled dependencies. |
| D24 | Accept design: Three existing A06-A08 tasks separate terminal/callback/control/root/native retirement, bound queues and waiters, and specify safe close behavior. | No actual Core async/runtime component is implemented or accepted in this stage. |

## Evidence actually checked

All 18 distinct embedded evidence references matched their named bytes. Six original local/CI run manifests supplied **54 source identities and 53 command records / 106 raw stdout/stderr streams**; every checked identity matched. The Windows and Linux CI archives preserve **24 files each**, and all 48 extracted-file hashes matched. This review verifies preserved bytes; it does not claim a new ZIP download or new execution.

The main fixture really records 10,528 normal / 10,529 Native AOT assertions, 32 controlled callback rounds, nine generator checks and four/six normal/AOT restriction checks per OS. The Linux-only comparison has 60 normal and 60 AOT cases. Seven panic child cases and the two invalid-UCO child failures remain visibly nonzero where expected; UCO body-entry markers are absent and InvalidProgramException is present.

The old local Linux Cargo.toml is intentionally different from the later committed input; its original source snapshot and all 13 archived source hashes were checked. Windows CI source differs by recorded CRLF checkout in 13 files. Neither historical record was rewritten or counted as a new run.

The fixture and retained model source were reviewed. Existing model outputs preserve a 541-state retirement candidate plus omitted-guard counterexamples, and a 17-state lost-wake negative versus an 11-state atomic mailbox candidate. Their finite, sequentially consistent scope is explicit. No successful experiment was rerun.

## Source checks and technical conclusions

Seven critical fixed upstream files were independently re-read: .NET SafeHandle and CancellationTokenRegistration, csbindgen parser, Roslyn GeneratorDriver, Tokio Runtime, Bytes::from_owner and Rust raw-slice requirements. Exact commits, returned Git blob IDs and read ranges are in the JSON. These confirm logical admission versus physical lifetime; external cancellation drain and self-wait exceptions; silent omitted-export risk; normal generator ordering; runtime timeout versus actual thread/work retirement; backing-owner lifetime versus visible slice length; and shape checks versus pointer provenance. Other domain/source evidence was reviewed within its retained manifest and prior independent scope, not advertised as a fresh whole-repository audit.

D02–D09 keep physical leases, logical admission, mutation serialization, terminal outcomes, once-only results, native quiet, managed drain and retained buffers as separate obligations. Invalid UCO signatures require signature/AOT diagnostics; a method-body catch cannot repair code that was never entered. D08 full 24-byte ErrorRecord rules preserve the business status even when diagnostic capacity is short, and panic poison leaves only trusted cleanup paths. D03 reuses mature generation and never makes ordinary entity additions compile Rust.

## Planning readiness and limits

A01–A12/A19/A20 packets were compared with their current fragment details, write scopes and graph packet hashes; all matched. The corrected A03 finite schedule boundary and A05 mandatory poison policy propagated correctly. A10 may test its emitter with a labelled conformance fixture while A14/A15 must exercise actual completed A07 closure; that distinction avoids treating a fixture as full product validation. A19 may be implemented independently as an abstract model, with A20 later checking actual code.

This review binds individual outputs and semantic task projections, not the whole mutable registry or task graphs. Final integration must still bind these reports, contract contents, packet versions, evidence wrappers and dependency states and satisfy GitHub checks. Later semantic edits require scoped follow-up review. Complete weak-memory, generated ABI, failure-injection, distribution, no-Rust consumer, long-run and performance gates remain assigned to existing Delivery tasks.
