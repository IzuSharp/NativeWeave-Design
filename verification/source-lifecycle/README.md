# New Database and Server lifecycle execution evidence

Run [43375871731](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43375871731)
executed exact source `de43481581df9876cb2d0aed5de2db796d048c9d` on Ubuntu24.04
and Windows2022. All four jobs passed: six Database and six Server tests on
each platform, 12 distinct tests and 24 platform test executions.

`results.json` binds every source input, all 56 raw artifact members, the four
ZIP/API digests and the tested workflow bytes. Actual artifact ZIPs were
downloaded and SHA256-checked before extracting these unchanged text files.
The later evidence commit and eventual merge commit are not the tested source.
No second execution is inferred from preserving results.

## Exact checkout identities

Fifteen of the twenty per-job source inputs match their tested Git blobs byte
for byte. The five Database Windows inputs are exactly Git checkout's LF to
CRLF conversion. The manifest records **both** Git-blob and actual-checkout
SHA256, and verifies that sole transformation for each file. The Windows
input snapshots retain their real bytes. The first strict byte-identity audit
failed on this difference; `artifact-verification-attempt-1.json` preserves
that finding. It is not a failed Rust test and is not hidden by rewriting hashes.

The Server fixture explicitly requests LF through `.gitattributes`; its hidden
input file is included in both artifacts. Raw Windows result/log CRLF bytes
are preserved independently of source conversion. No build cache is archived.

Use `python verification/source-lifecycle/verify.py` from the repository root
with full Git history. It verifies this evidence, canonical committed fixture
inputs, all registered specification hashes, the research phase and archived
independent-review copies. It does not run Rust/C# tests or promote a contract.

These are finite Rust experiments. They do not prove PostgreSQL, C# Database
or Server Native AOT, HTTP/TLS wire behavior, OS thread join, arbitrary callback
retirement, weak-memory safety, process RSS or product acceptance. The already
completed PR #8 Interop run and this session's concurrent Linux replication
retain their separate identities and are not added to this run's coverage.
