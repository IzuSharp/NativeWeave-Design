# Server, protocol, diagnostics and extension research completion

This directory preserves real scoped research evidence for R26–R30/R32/R33/R34 and
D18/D19/D21. It does not implement NativeWeave product tasks or grant contract acceptance.
`completion-assessment.json` is a per-task evidence audit for the existing graphs,
not a fourth plan. Independent review and root graph/registry integration are separate.

## Current actual execution

| Run | Execution and result | Material scope |
|---|---|---|
| `protocol-local-4` | Rust1.100 pinned Cargo.lock, 13 tests passed | Tonic byte codec/frames/negatives/server streaming; rmcp runtime tool names, metadata/Host/Origin/body limits; real TCP Hyper HTTP1/HTTP2; rustls ALPN/close/trust/name checks |
| `kestrel-local-2` | .NET11 Linux x64 publish Native AOT and actual binary run, five comparator cases passed | health, binary echo, over-limit body, streaming disconnect cancellation, bounded shutdown |
| `diagnostics-local-2` | .NET11 Linux x64 Native AOT, eleven assertions passed | C# trace layout, no-listener null/zero-thread-allocation loop, avoiding tag formatting, explicit/managed async parent, listener disposal |
| `diagnostics-rust-layout` | Rust1.100 executable passed | independent repr(C) size32 and offsets8/24 witness |

The protocol fixture does not invoke a C# FFI Handler and does not combine every
protocol/TLS/network layer in one end-to-end test. The diagnostics fixture does not
execute native callback trace propagation or an exporter. Zero current-thread managed
allocation in its warm loop says nothing about native memory or production overhead.
No long-load, fuzz-completeness, GPU/mobile execution or production certification is
inferred. Existing retained Bytes/Body/Tokio permit Windows/Linux evidence at
`verification/source-lifecycle/results.json` is reused as prior work, not counted again.

Local `git_head` fields identify the checkout base. Source snapshots and SHA256 hashes
identify the actual locally executed uncommitted variants; the record does not assert
that HEAD alone contains the executed source. Remote CI results must identify their
own clean source commit and artifacts.

## Verified cross-platform CI

Run43388468172 tested source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`.
Protocol13/13 and Kestrel AOT5/5 passed on both Windows2022 and Ubuntu24.04.
The four original manifests/logs/inputs are under `verification/completion-ci/43388468172/`.
`ci-verification.json` records author checks of all input/log hashes, including exact
Windows LF-to-CRLF checkout conversion. These are four platform runs of the same
18 distinct cases, not 36 distinct tests and not independent architecture review.

## Reproduce current source

```sh
python experiments/server-completion/run.py protocol --output verification/server-completion/protocol-new
python experiments/server-completion/run.py kestrel --output verification/server-completion/kestrel-new --rid linux-x64
python experiments/server-completion/run_diagnostics.py --output verification/server-completion/diagnostics-new --rid linux-x64
rustc --edition 2024 experiments/server-completion/diagnostics/layout.rs -o /tmp/nativeweave-trace-layout
/tmp/nativeweave-trace-layout
```

Use `win-x64` for Windows .NET runs and an appropriate executable path for the Rust
layout witness. The runners explicitly disable .NET CLI telemetry and first-run
certificate generation. They record command exits, stdout/stderr, toolchain/platform,
source hashes and actual executable hashes. Native build prerequisites still apply.
Executable publish outputs are not committed; source, raw logs and binary hashes are.

## Preserve attempts and credential hygiene

`kestrel-local-1` is a failed compile, not a pass. Its ambiguity diagnostic and exact
source remain. `diagnostics-local-1` likewise preserves an overload compile error;
the successful corrected source is separately snapshotted. Protocol runs1–3 represent
earlier fixture coverage and are not added to the current distinct test count.

Protocol runs2–3 used a stored test-only identity. Their `.der` input bytes are
intentionally omitted from published snapshots, with original SHA256 and precise
omission reasons in `historical-input-omissions.json`; original run manifests/logs
are not rewritten. Those historical input snapshots are explicitly incomplete.
Current run4 generates an ephemeral localhost identity with rcgen0.14.10 entirely in
memory. Current source/lockfile reproduction needs no stored key/certificate, and no
private key is emitted to raw logs or manifests.

## Source and dependency identities

`source-inspection.json` records actual selected reads, commits and full-file digests;
full-file hashing does not imply full-file reading. Eighteen directly retrieved source
files are byte-exact to GitHub blob identities. Additional rmcp/tracing files come
from the Cargo sources actually compiled, with `.cargo_vcs_info.json` provenance.
`package-identities.json` compares the relevant Tonic/rmcp crate source bytes with the
retrieved upstream source and confirms a single resolved Tokio/Hyper/http/Bytes family.

`dependency-inventory.json` lists 157 locked registry packages. License metadata/file
hashes are inventoried where the package is locally present; non-Linux target packages
not downloaded are marked identity-only. This is not a product SBOM, license approval
or advisory scan. B24 retains exact distribution/license/NOTICE/current-advisory work.
