# Independent review: finite Server lifecycle research

**Decision: approve research integration of the exact ten files in `manifest.json`. No Server-scoped finding remains open.** This review does not accept C-SERVER-001 as a product contract or authorize formal Delivery.

Reviewer: `/root/design_source_review`. The reviewer did not author the Server experiment, Server design documents or workflow. The reviewer authored the separate Database experiment; this report is not independent approval of that work.

The reviewed files were clean at capture against repository HEAD `b6c3a7c9161edc4949b2d05c3c2443f074f3f0e5`. The CI source under discussion is `de43481581df9876cb2d0aed5de2db796d048c9d`, run `43375871731`. The final workflow has exactly four jobs: Database and Server on Ubuntu 24.04 and Windows 2022. A separate integrity-review addendum covers the newly archived CI evidence and its verifier.

## Evidence and actual coverage

The reviewer executed the six Server tests twice on Linux x86_64 with Rust 1.100.0. `raw/independent-1` retains the first runner result; `raw/independent-2` retains the corrected runner's commands, stdout/stderr, result and all five exact input snapshots. Both runs passed six named tests, and the recorded input hashes were unchanged during each execution. No additional Server test rerun was performed after the author reported the four CI jobs successful.

The tests use actual Bytes ownership, Tokio channel/semaphore permits and Hyper's Body interface. They establish the following finite observations:

| Case | Observation supported by the executed test |
| --- | --- |
| Last retained nonempty slice | One owner allocation remains charged after original/clone drop; its credit returns after the final retaining slice drops. |
| Receiver destruction | Queued owners release credit, but an externally retained frame remains charged. |
| Cancellation during byte wait | The producer has reserved a message slot but has not allocated its payload; dropping its Future returns that slot while the unrelated retained allocation remains charged. |
| Close after reservation | An existing OwnedPermit can send after receiver close. Close is not revocation. |
| Invalid payload length | Zero and oversized payloads are rejected before reservations or allocation in the exercised helper. |
| Body EOF | Polling EOF and dropping the Body do not release a frame already retained elsewhere. |

Four upstream files were independently inspected at their full commit pins, compared byte-for-byte with the actual Cargo registry source, and independently re-fetched through GitHub. Git blob SHA1 recomputation confirmed the fresh upstream identity; the three relevant downloaded crate checksums match Cargo.lock. The exact ranges and source identities are in `source-identity.json` and `independent-fetch-metadata.json`.

Hyper Incoming's HTTP/2 NO_ERROR handling remains **source-inspected only**. This fixture disables transport features and uses a custom ChannelBody; it does not execute HTTP/2, sockets, TLS, a managed handler or Native AOT.

## Findings and final disposition

| ID | Finding | Final disposition |
| --- | --- | --- |
| SRV-REV-001 | Original artifact globs omitted extensionless Linux AOT executables and raw input files while selecting build output recursively. The first repair also omitted the hidden input `.gitattributes`. | Closed. Final workflow selects root evidence logs/manifests, `inputs/**` and `binaries/**`, with `include-hidden-files: true`. This excludes Server build caches. Interop has been removed from this workflow because existing evidence was recovered; the generic binary directory selection still includes extensionless files. Actual GitHub archive verification is handled separately. |
| SRV-REV-002 | Original runner did not save a timed-out command or its partial stdout/stderr. | Closed. The corrected runner records command, failed exit code, timeout status and available output. The reviewer injected Python TimeoutExpired and FileNotFoundError exceptions and verified failure records, partial logs and `success=false`. These are explicitly simulated runner-error checks, **not actual Cargo timeout or missing-tool runs**. |
| SRV-REV-003 | README generalized retaining behavior to every slice, although the fixed Bytes implementation gives empty slices no clone of the original owner. | Closed. README, protocol and D18 now qualify nonempty/shared-owner slices and account separately for empty slices and copied buffers. |
| SRV-REV-004 | A byte waiter can hold an OwnedPermit after channel close, and unrelated buffer copies do not inherit the original owner's charge. | Closed. Protocol/D18 require explicit cancellation/completion of byte waiters and separate accounting for copied, decoded and transport buffers. The six tests are not presented as a complete close or global-budget coordinator. |
| SRV-REV-005 | The `(A + Q)` metadata bound was ambiguous if terminal requests retained cleanup state after returning active-request credit. | Closed. D18 explicitly keeps Closing/retirement-pending holders in A; a separate retirement queue requires its own finite budget and revised bound. |
| SRV-REV-006 | Published source-inspection metadata inherited review-relative execution paths that would not resolve in the repository. | Closed. The final source-inspection file removes those transient execution fields. This review bundle has its own explicit raw-evidence manifest. |

## Design assessment

D18 and the body-retirement note now distinguish logical admission, result publication, Body termination, queue reservations, retained allocation ownership and callback retirement. They do not report peer consumption or precise transport success merely from EOF, nor do they free roots or module owners at a public timeout. The proposed operations reuse the existing Core create/start/take/release protocol rather than introducing a competing wire layout.

The Server choice remains open. Kestrel Native AOT is a required research comparator and a candidate product profile; Rust is another candidate. The revision does not select a universal default, hide an unconditional Kestrel dependency in future delivery prerequisites, or require a default upstream fork from the finite seam result.

## Frozen contract and limits

C-SERVER-001 remains **0.2.1-draft / proposed**, with document SHA256:

`9acf2b3bd464815ac0bb66700ee0c5c8791fa3772f7b0fbe54736e59e2f47358`

The exact fixture, documents, source record and four-job workflow hashes are in `manifest.json`. Approval is scoped to those content hashes. The manifest also hashes all 43 retained raw reviewer files; build caches were intentionally excluded.

Remaining product gates include a real C# handler/FFI adapter, managed cancellation-registration retirement, HTTP/TLS/reset/trailers tests, a complete global/per-request budget coordinator, fairness, exhaustive races, memory/RSS accounting, real Server Native AOT execution and equivalent host comparisons. A successful finite experiment does not close those gates, accept the formal contract or enable product implementation.
