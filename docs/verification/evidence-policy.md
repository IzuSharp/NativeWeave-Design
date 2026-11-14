# Evidence, proof obligations and acceptance policy

Status: proposed; version 0.1.0; independently defined according to NativeWeave's current requirements. ArcForges documents serve only as a formatting reference.

## 1. Classification of conclusions

| Label | Permitted claim | Prohibited inference |
| --- | --- | --- |
| source_confirmed | The specified code execution path at a pinned SHA expresses this behavior | It has run on the current machine, or the entire project is defect-free |
| test_confirmed | The result was actually observed for the specified artifact, command and environment | Untested platforms/architectures behave identically |
| official_doc_confirmed | An official source explicitly states a feature/limitation | A particular package combination is necessarily correct |
| inferred | Derived from known evidence, with assumptions listed | Presenting an inference as a measurement |
| pending | Source inspection/execution/review is still missing | Counting it as complete |
| refuted | A concrete counterexample exists | Using one counterexample to reject all related approaches |

Code examples have separate states: design-draft, static-reviewed, compiled, executed, native-aot-executed, independently-verified. Each promotion includes evidence; automatic linear progression is not assumed. source_confirmed must record the resolved full commit SHA; a release tag may be displayed alongside it but cannot replace the SHA. Passing a model check only adds a model_checked record and does not promote the example to AOT.

## 2. Minimum fields for each item of evidence

evidence_id, claim, classification, repository_url, full commit_sha (a tag is only a display locator), file, symbol, line_range, read_coverage, limitations, collector, collected_at, related_requirements/contracts/tasks. Execution evidence additionally requires:

- Source and artifact SHA256, toolchain and dependency locks, OS/architecture/CPU/ABI/linker.
- Complete commands, exit codes, stdout/stderr locations and content hashes, and start/end times.
- Expected and observed results, test counts, failures/skips/timeouts, inputs and random seeds.
- Evidence that the Native AOT publish artifact was actually launched; compiler logs alone are insufficient.
- Analyzer warnings and their disposition; globally suppressing unexplained warnings to fabricate a pass is prohibited.

## 3. Selecting correctness-verification methods

| Mechanism | Proof obligations | Preferred evidence combination |
| --- | --- | --- |
| Handle / owner | Single release, live lease, parent/child destruction order, ABA boundaries | State model + property/concurrency tests + actual calls and fault injection |
| callback / async | terminal ≤1, no invalid access after unregistration, shutdown can converge | Finite models/TLA+, Loom adapted to native state, C# concurrency-scheduling tests, process-isolated crash tests |
| buffer | Valid access range, length overflow, alignment, allocator pairing | Property tests, fuzzing, Sanitizer; Miri only for Rust paths it supports |
| ABI / generation | size/offset/calling convention, declaration/implementation consistency | C/Rust/C# layout and call probes, generated snapshots and negative-case diagnostics |
| SQL query | Parameterization, NULL/Join/ordering/numeric semantics | Database differential tests, property tests, real PG/SQLite corpora |
| transaction | Failures do not incorrectly commit; unknown outcomes are not treated as successful rollback | Real DB disconnects/timeouts/restarts, state logs and idempotent recovery |
| server | Bounded memory/concurrency, backpressure for slow peers, graceful shutdown | Load/fault/long-duration tests, allocation and thread tracking |
| release | Traceable provenance, package/RID matching, old/new compatibility | Clean consumer installation, AOT execution, SBOM/license, upgrade/downgrade matrix |

TLA+, Loom, Miri, Kani, fuzzing and Sanitizer are candidate tools; using all of them is not mandatory. Pin each tool's version, applicable assumptions and FFI/OS/scheduling behavior it cannot cover; a partial model must not be used to claim absolute system safety.

## 4. Platform matrix

The initial plan must include native-target builds and execution for win-x64 and linux-x64. First establish a capability matrix for Arm64, musl, other desktop targets and mobile targets; actual requirements and experiments determine when they become formally supported. Study layout differences on 32-bit targets without declaring support merely because a differences table exists.

“Windows/Linux passed” must correspond to the actual host, target and artifact for each platform. Linux evidence from a container must state the container/host-kernel conditions and cannot substitute for evidence from the user's dedicated MCP host or Windows. At present, only local Linux execution and GitHub tools have been discovered; no dedicated Windows/Linux MCP acceptance tools have been discovered.

## 5. Performance methodology

Compare C# AOT, C# AOT+Rust and appropriate pure Rust implementations under the same functional semantics, dataset, TLS/protocol, error policy, concurrency, warmup and resource limits. Verify equivalent business results before discussing speed.

Record cold start, steady-state throughput, CPU time, P50/P95/P99, error rate, RSS/peak usage, managed GC, native allocations, bytes copied, FFI call counts, threads, package size, long-term leaks and recovery. Account for coordinated omission in open-loop load tests; retain latency histograms and evidence of load-generator bottlenecks. Isolate resource contention on benchmark hosts, repeat runs independently multiple times and report distributions/intervals.

Do not specify arbitrary improvement percentages or latency targets yet. After completing the baseline, propose local thresholds based on actual SLOs, measurement noise and maintenance cost. FFI microbenchmarks explain costs and cannot replace end-to-end results.

## 6. Review and state

Four review layers: evidential support; cross-review of topic interfaces and lifetimes; independent overall adversarial review; delivery-readiness review. An author cannot mark their own major design accepted alone. Finding records contain ID, severity, location, counterexample, impact, disposition and verification.

Pin the review scope to a commit or file hashes. Source evidence, models and script checks prove only their respective scopes; without actual Windows/Linux AOT evidence, the corresponding product capabilities must not be marked accepted.

Research files may enter a Draft PR for discussion while proposed; the ready set for formal implementation is calculated separately. Unexecuted items must not be presented as passing, and unrelated tasks must not be made to wait without a reason.
