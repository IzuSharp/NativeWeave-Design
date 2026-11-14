# Design conclusions and future verification for technical questions

2026-11-13. Existing Q01–Q21 are retained; technical conclusions/research acceptance are separate from product verification. Exact registry and independent review records govern final formal acceptance; resolved designs must not remain open permanently just because the product has not yet been implemented.

| ID | Question | Current design/research answer | Future product obligation |
| --- | --- | --- | --- |
| Q01 | Toolchains/platforms | Rust1.100/.NET11/C#15 and actual research on both OSes; D01 selects explicit initial profiles | A14/A15 complete product and execution-machine matrix |
| Q02 | ABI/handles | Fixed C ABI/size-prefix negotiation; logical admission+physical lease; D02/D04 | A01/A02/A03 complete layout/old-new version/failure paths |
| Q03 | Single binding source | D03 minimal inventory; actual generator comparison and silent-omission negative cases | A09–A12 production tools/export-drift validation |
| Q04 | Callback retirement | D04–D06 native quiescence+managed queued/running dual barriers | A06/A07/A20 complete race/weak-memory-related tool scope |
| Q05 | Async surface | Prefer Task; take-once terminal state; ValueTask pooling requires cost and lifetime proof | A07/A21 production implementation and actual benefits |
| Q06 | Shared runtime | No unified runtime required; synchronous miniz and asynchronous Hyper provide heterogeneous evidence | A08/A17/A18 local capabilities and threads/RSS |
| Q07 | Buffer | D07 owner/extent/stride/borrow/pin/copy; actual overflow/GC research | A04/A20 product fuzz/retained allocation |
| Q08 | Fatal errors | D08 exact ErrorRecord; subprocess facts for Rust panic and invalid UCO | A05 poison/fault injection and recoverable scope |
| Q09 | Packaging provenance | Actual independent NuGet/RID-free/AOT on both OSes; no Rust tools in the effective consumption environment | A16 genuinely pristine no-Rust, release signing, and runtime-only machines |
| Q10 | Two real Engines | miniz_oxide synchronous codec and Tokio/Hyper asynchronous network | A17/A18 production Core facade conformance |
| Q11 | Native DB/ORM | Precompiled SeaQuery+SQLx with dynamic metadata; conditional SeaORM reuse | B01–B14 complete product API/closure and AOT on both OSes |
| Q12 | Unknown transaction outcome | Actual PG lost COMMIT response/failed tx/migration lock; in-depth SQLite positive/negative cases | B05/B08/B21/B22 durable reconciliation/sustained workload |
| Q13 | Natural strongly typed queries | Fluent/static metadata/DTO, optional SG, no complete LINQ/per-entity Cargo | B09–B14 complete production capabilities and negative compilation cases |
| Q14 | SQL semantics | D16 strictly distinguishes fallible native binder/backend rejection/SQL3VL/shape | B02/B03/B07/B11 complete differential matrix with real backends |
| Q15 | Rust Server composition | Mandatory Rust; Tokio/Hyper/Tower/Axum foreign service; Kestrel only for comparison | B17 production Host, A21/B23 fair cost data |
| Q16 | Server budgets/shutdown | D18 Body/Bytes/permits/budgets on both sides and retirement; actual HTTP2/TLS and owner experiments | B16/B17/B20/B22 complete C# bridge and soak/RSS |
| Q17 | gRPC/MCP | D19 Rust Tonic/rmcp+static C# DTOs/Handlers; explicit public-API validation/timeout gaps | B18/B19 actual AOT transport/messages/streams/cancellation/protocol interoperability |
| Q18 | Future platforms | R32/R33/D21 actual source and availability, affinity/device loss/static-linking boundaries | A23 target-device/platform-specific work; does not block current desktop work |
| Q19 | Formal acceptance | R34/D31/D32 exact source/content/dependencies and actual independent review; three graphs retained | Future product-phase authorization and actual product acceptance |
| Q20 | Supply chain | D10/R14 exact crate/source/lock/license/provenance distinctions and update strategy | A16/A22/B24 final closure/signing/organizational release policy |
| Q21 | Latest features | Distinguish stable union/closed from preview memory safety; actual RuntimeAsync lowering/AOT | A21 cost measurement, A22 subsequent version upgrades |

New counterexamples discovered during research must still be fixed, with the exact current inputs reviewed again; merely moving them to future obligations cannot conceal design errors. No questions that reverse the intended architecture remain open on choosing between Kestrel/Rust, complete LINQ, or per-entity Rust compilation. Specific GPU/mobile product targets are not yet included in formal desktop releases; execution on every device is not claimed.
