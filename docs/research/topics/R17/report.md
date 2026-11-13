# R17 — Honest performance, memory and engineering-cost comparison

Author: `/root`. This task researches and fixes the measurement method. It does not claim product benchmark results before product implementations exist.

## Source findings

BenchmarkDotNet `ecdd5717fc237db869956c4e200883fb58634f7d` NativeAOT builder emits PublishAot and can choose `native` ISA on modern .NET. An otherwise identical benchmark can therefore use a different instruction set from a portable shipped build. Pin D01 ISA explicitly and record the actual generated project/compiler settings. Its inspected integration tests skip some environments and tolerate harness-specific warnings; neither is permission to omit NativeWeave Windows evidence or broadly suppress AOT warnings.

Criterion source `3dbc6c618acb48885066422d81d50729aa17b2b7` estimates iterations from warmup and supports a quick mode with very short sample collection. This is useful microbenchmark machinery, not proof of independent arrivals or tail latency under queueing. This is an inspected historical repository pin; later project relocation must be verified when installing a benchmark dependency.

HdrHistogram `de84b0a7de2378abfc405da503bf4898e84ea98e` expected-interval recording fills omitted samples, and its percentile calculations have quantized bucket semantics. Correction must not be applied twice. A corrected synthetic histogram is not raw observed request arrival latency. The exact inspected ranges and hashes are in coverage.json.

At dotnet/diagnostics `dde6f56c8701d40b93b191e2c840e26f535c09d5`, CounterMonitor configures a refresh interval and EventPipe metrics pipeline, handles EventCounter/Meter duplication on a best-effort basis and defaults to System.Runtime. Such sampling is useful context, not an exact native-allocation tracker or proof that a short peak never occurred. Diagnostics support depends on the actual Native AOT build; unavailable counters are recorded, never filled with zero. Engine owner/byte/permit counters plus OS observations remain necessary.

## Executed counterexample

[omission.py](../../../../experiments/performance-completion/omission.py) is a deterministic finite accounting model: 100 arrivals scheduled one synthetic millisecond apart, first service takes100ms and the remaining99 take1ms each. Service-time p99 is1ms; scheduled-arrival p99 is100ms. An expected-interval fill yields199 observations with p99=99ms. The log explicitly labels these model quantities. This catches a materially wrong latency reporting method without pretending to have implemented the final server/load harness.

The C#15 union experiment separately measures a narrow allocation fact; it is not reused as an end-to-end performance claim. Native Engine functional probes, CI duration and test throughput are not benchmark cells. No fabricated throughput advantage or universal percentage regression threshold is introduced.

## Required design

Compare (1) direct pinned Rust Engine, (2) C# Native AOT plus that same Rust Engine, and (3) equivalent managed AOT comparison application, with matching protocol/durability/serialization/TLS/data/cache/workload semantics. Rust Database/ORM/Server are product requirements regardless of the comparison outcome. Unfavourable costs remain visible.

Primary load generation is external and open-loop: scheduled arrival, dispatch, admission, completion/timeout, status and bytes are separate fields. Report offered/admitted/completed throughput and queue/service/end-to-end latency. Closed-loop is separately labelled. Generator overload invalidates the offered-rate cell. Preserve failed, cancelled, rejected and timed-out requests in the dataset.

Count managed/native allocations and bytes copied separately from live/retained memory. Whole-process RSS/private working set includes mapped code, thread stacks and allocator retention; kernel/TLS/socket buffers may be additional. A queue length bound or custom outer allocator is not a whole-process memory bound. Track resource acquisition/release linearization points, retained Bytes owners and drain-to-quiescence counters under D04/D07/D18.

## Analysis and acceptance

D13 specifies raw histograms, ranges/overflow, independent process repetitions, randomised order, cold/warm separation, predeclared workload cells, uncertainty/effect sizes and a baseline-derived regression policy. Include developer cost: application code for a new model/Handler, generated/native glue, build steps, patches, binary/package size and maintenance burden.

A21 implements the harness; B23 runs actual full applications; B22 supplies correctness/fault/soak oracles; B24 binds release profiles. Those future measurements are intentionally not circular prerequisites for research/design acceptance. The current research resolves how to obtain credible evidence, identifies concrete false-positive methods and provides a reproducible counterexample.
