# R16 — Differential, property, fuzz and fault evidence

Research decision ready for independent review. The task lacked canonical files despite existing native-slice, lifecycle and negative model evidence. The chosen verification design makes the oracle and valid-memory boundary explicit and adds actual native/managed differential and fault experiments.

## Executed normal, error, race and compatibility slices

The new completion fixture compares Rust checked count×width arithmetic with C# BigInteger for10,000 deterministic cases plus explicit empty/overflow/isize/zero-width boundaries. It exercises32 controlled native-callback/retirement/GC rounds, late cancellation preserving Success, duplicate terminal rejection, once-only take, result survival after operation release, managed callback exception containment and result release after DTO conversion failure. Actual normal/AOT Linux runs have10,528/10,529 assertions, with tool/source/binary identities and raw output.

The same scalar native export is called through pinned csbindgen DllImport and framework LibraryImport for60 normal and60 actual Linux AOT boundary combinations. A parser-only unsupported tuple export is omitted despite generator success; the comparison observes the missing function, and D03 requires the future export inventory gate to reject it. AotRestrictions separately exercises static JSON/closed generics and actual rejection of dynamic-code/reflection fallback paths.

Seven Rust1.100 child-process panic cases cover ordinary caught unwind, intentionally quarantined payload, payload Drop panic, hook panic, cleanup double panic, panic through nonunwind C ABI, and panic=abort defeating catch. Exact exit codes and stderr are retained without assuming identical OS text/status values. This is not arbitrary heap corruption or full engine poison recovery testing.

Existing native-slice Windows/Linux AOT, logical admission negative controls, SQLx retirement and retained Body/Bytes experiments retain their original source/run identities. New Linux evidence is not mislabeled as new Windows or product evidence.

## Oracle selection

| Mechanism | Oracle |
|---|---|
| ABI/layout | C/Rust/C# independent size/alignment/offset probes, exact symbol inventory |
| Arithmetic/codec | BigInteger or authoritative bounded scalar model; verify null/overflow/domain cases |
| Query/relations | Same dialect/parameters against direct Rust engine and actual PostgreSQL/SQLite results/effects |
| Ownership | Per-resource owner/lease/transfer counters with injected failure at each boundary |
| Protocol | Actual peer/server wire behavior plus source-defined state invariants |
| Concurrency | Controlled barriers and model negative controls; supported instrumented scheduling where needed |
| Compatibility | Old/new managed/native combinations; unsupported features fail before transfer |

Comparing generated SQL strings alone is not a semantic oracle. Comparing two wrappers that share the same buggy conversion is not independent evidence. Test source may express expected behavior but is not an executed result.

## Fuzzing scope and replay

Proptest's actual FailurePersistence interface stores seeds associated with source identity and shrunken examples; cargo-fuzz's Run command accepts corpus/artifact inputs and forwards libFuzzer parameters. Use those established mechanisms where they fit. Persist generator/schema/oracle version, initial seed, original/minimized failing bytes, corpus hash, toolchain and exact command. A seed without the generator version is not reliably replayable.

Fuzz only allocated, valid-memory buffers with malformed lengths/contents inside declared safe bounds. Arbitrary stale pointers, invalid UCO ABI and deliberate fatal branches run in isolated processes. ASan/TSan/Miri support must be confirmed for the exact target; unavailable instrumentation is blocked/not-executed, not successful. Do not claim this finite deterministic property experiment was a coverage-guided fuzz campaign or sanitizer run.

## Fault and cleanup cases

Inject before/after native ownership acceptance: create reserve; managed wrapper/context allocation; registration; start rejection or synchronous terminal; callback conversion; take/result wrapping; decoder exception; transaction/protocol flush; runtime shutdown. For every injection state who still owns the input, output, connection, callback root and cleanup slot. A cancelled waiter or expired deadline does not free in-use native memory. Unknown transaction effects require reconciliation, not automatic replay for a green test.

Core ordinary failures and poison/fatal behavior follow D08. Real per-engine resource budgets include queued/waiting/retiring owners and allocation capacity, not only visible payload length. Counters, descriptors/handles, threads, managed allocation and RSS are observed separately over normal/overload/recovery windows in future B22/B23.

## Closure and future implementation

D12 defines evidence discipline and a concrete matrix; A20 owns production corpus/fault/property infrastructure, A19 model mapping, B22 real combined-domain faults and long runs. The current research settles test architecture and exercises representative normal/error/race/compatibility paths. Full product fuzzer targets, supported sanitizers and long-load acceptance remain future tasks with exact test oracles rather than generic 'research later'.


## Supplemental invalid-UCO execution (2026-11-13)

The [isolated manifest](../../../../verification/interop-completion/uco-invalid-linux/result.json) records actual .NET11 normal and Native AOT publication followed by native invocation of an intentionally invalid char/bool `UnmanagedCallersOnly` callback with runtime marshalling enabled. Both child processes exited -6 with unhandled `InvalidProgramException`; `INVALID_CALLBACK_BODY_ENTERED` never appeared. This demonstrates that callback-body catch cannot repair an invalid signature. It does not establish all fail-fast variants or behavior of an outer managed catch. The normal blittable callback succeeds in the main fixture. Invalid-pointer fuzzing was not performed.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
