# R03 — Stable C representation and explicit ABI evolution

Research decision ready for independent review. The existing [native-slice-validation](native-slice-validation.md) already contained genuine two-OS native/managed/AOT layout and ownership execution, while the required report/evidence/coverage triplet was missing. This report restores the canonical task record without re-running or inflating that evidence.

## Chosen boundary

Use an engine-specific C ABI with fixed-width scalar statuses/tags, repr(C) wire records, explicit byte lengths and private opaque owner pointers. Rust SeaQuery AST, SQLx connection/transaction types, Hyper Body, Tokio Future, Vec/String/Arc and trait objects remain private. C# generics/Fluent/Task are application APIs, not exported layouts. The initial x64 Windows MSVC and Linux GNU layouts are in D02/D08; additional targets require their own probes.

Size-prefixed ABI information makes version negotiation explicit. Null or insufficient output capacity writes nothing; compatible larger caller capacity does not license writing beyond provider-known fields. Major semantic/layout incompatibility rejects before ownership transfer. Minor additions append only compatible fields/capabilities. Required capability absence fails clearly rather than silently changing backend or SQL semantics. Private probe status values do not become the D08 status enum.

## Evidence and normal paths

The prior native-slice study at original source `4a4adc883b80719d2a9b2bfb03be5ec86b543f3c`, run 43363045559, tested repr(C) and C# size/offset, static imports, ordinary application consumption, owned buffers and synchronous reverse callbacks on both OS, including actual AOT. Its current Design source/evidence relocation is fixed by the migration manifest; historical identities remain unchanged.

The new Rust1.100/.NET11 completion experiment adds a cross-language extent predicate. Rust checked u64 multiplication and isize/budget bounds are compared with C# BigInteger for 10,000 seeded cases plus four explicit boundary cases. This is arithmetic validation on integers, not a claim that arbitrary pointers can be validated. The same scalar export also executes through pinned csbindgen DllImport and framework LibraryImport with identical results in normal and AOT modes.

## Abnormal and compatibility boundaries

Validate shape, finite size, multiplication/addition, alignment and declared nullability before constructing a Rust slice. Empty null+zero becomes an empty slice without constructing a null reference. A nonnull pointer with plausible length may still be inaccessible: valid-address provenance is an ABI caller precondition, not a promise made by a length checker.

Boolean wire values are explicit bytes 0/1; enums are fixed-width tags with unknown-value rejection. No C long/wchar_t, implicit platform string encoding or Pack=1 workaround. Padding is not semantic data and is never hashed/transmitted as though initialized. Owned outputs start null and publish once after complete initialization; caller/callee destructor ownership cannot be ambiguous on errors.

Callbacks use the exact unmanaged convention and static blittable UCO signatures. Returning C# bool or passing char without the precise allowed raw representation is not repaired by a try/catch in the callback body. AOT invalid-signature fatal/compiler negatives remain separately isolated from ordinary valid-memory fuzzing.

## Alternatives and implications

Opaque pointers avoid the allocation, lookup and synchronization of a universal global handle table. D04's generated logical gate and physical SafeHandle lease are still mandatory; unsafe raw callers remain within the same process trust domain. Generational tables can be a separate justified profile for untrusted integer identities or pooling, not compulsory Core machinery.

Direct per-operation exports are the simple initial interface; a versioned function table is useful for module selection without exposing private Rust layout. Both obey identical owner/capability rules. A serialized generic domain message protocol would add needless parsing/translation for ordinary calls and is not introduced as universal Core ABI.

## Design closure and implementation obligations

D02 specifies fixed representations, bootstrap signature, size-prefix behavior and per-export annotations; D08 solely owns status/error values. A01/A02/A09–A12 will generate and test the complete product layout/export inventory, including a C compiler probe, sentinel no-write cases and old/new binary combinations. A20 handles valid-memory property/fuzz tests; A22 handles upgrades. These are concrete implementation work, not a requirement to leave the chosen ABI permanently undecided. The present studies establish only their named records/functions and targets, not all future layouts.


## Supplemental invalid-UCO execution (2026-11-13)

The [isolated manifest](../../../../verification/interop-completion/uco-invalid-linux/result.json) records actual .NET11 normal and Native AOT publication followed by native invocation of an intentionally invalid char/bool `UnmanagedCallersOnly` callback with runtime marshalling enabled. Both child processes exited -6 with unhandled `InvalidProgramException`; `INVALID_CALLBACK_BODY_ENTERED` never appeared. This demonstrates that callback-body catch cannot repair an invalid signature. It does not establish all fail-fast variants or behavior of an outer managed catch. The normal blittable callback succeeds in the main fixture. Invalid-pointer fuzzing was not performed.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
