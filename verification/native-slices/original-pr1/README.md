# Native slice execution evidence

Exact already-executed run artifacts, not reruns. `manifest.json` binds ZIP IDs/digests, tested commits, raw text bytes and source checkout identities. Git LF and Windows CRLF bytes are distinguished; raw evidence is not normalized. Executables/packages remain in the original artifacts, with hashes verified from their bytes; no binaries are published as product releases.

Interop: source4a4adc8, run43363045559, Linux+Windows; four native tests and185 managed assertions in each ordinary and actual AOT execution,32 controlled Dispose/call races, six groups. NuGet PackageReference consumers use no RID for local build/run. These are physical SafeHandle-lifetime tests, not logical post-close admission or async retirement. No pristine Rust-free host is claimed.

Server: source5dd6967, run43363994414, four native tests on each OS: actual Tower response-Future negative control, body/callback shared slot, bounded queue/EOF, actual Hyper HTTP1 Service/Body over Tokio duplex. Not C# handlers, external sockets/TLS, load or a retained-byte/RSS proof.

Database: first attempt5dd6967/run43363994414 failed E0271 at Value→Expr conversion. Corrected43e4fbc/run43364366610 passed six tests per OS using locked SeaQuery1.0.2/SQLx0.9/Tokio1.54.1: bound-count/bytes/u64 checks, injected partial encoder failure, native silent-row-lock negative/rejection, no database send after overflow, runtime-table native CRUD/parameterization/type errors and explicit rollback/schema error. No PostgreSQL/C# database binding or full ORM/streaming guarantee.

This evidence supports existing R03/R04/R07/R10/R22/R25/R27/R29. Formal A/B tasks and contracts are not automatically accepted. Independent D32 review, full async, multi-Engine production integration, fault/soak/performance and clean deployment remain separate obligations.
