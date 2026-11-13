# R18 — Real heterogeneous Engines and a deliberately small common boundary

Author: `/root`. Scope: source-driven integration method and two genuinely different mature native domains; product implementations remain future A17/A18/B04/B17.

## Architecture decision

Core contains independently usable ABI/version, ownership/error/buffer and optional async/callback contracts. It does not contain SQL syntax, a universal operation AST, an HTTP scheduler, a mandatory Tokio singleton or a framework-wide allocator. Engine-specific adapters own domain semantics and selected native libraries. C# exposes static strongly typed metadata, DTOs, Fluent operations and business handlers; ordinary application variation is data plus statically compiled managed methods.

The integration ladder is public API, source-informed adapter, upstream extension and controlled fork with an explicit maintenance/exit plan. Source access alone does not make pub(crate) callable. No private layout transmute or Rust ABI is an accepted shortcut. Generator choices and real C# backends are reviewed in R05; C# support is not assumed absent from Diplomat. NSH/GPU/UI/mobile investigations are R32/R33 and need affinity/platform-specific profiles, not additions to the common runtime.

## Engine one: real synchronous zlib codec

Use miniz_oxide **0.9.1**, crates.io locked checksum and packaged `.cargo_vcs_info.json` commit `4e582392df3a739d2b0dfd2c537dc33e8942be38` (subdirectory miniz_oxide), plus adler2 **2.0.1**, VCS `89a031a0f42eeff31c70dc598b398cbf31f1680f`. The source metadata is a crate identity declaration, not an independent signed release verification.

Read `compress_to_vec_zlib` / its inner compressor loop and bounded `decompress_to_vec_zlib_with_limit`. Compression allocates an output Vec and can grow it; unexpected upstream status can panic. Unbounded decompression explicitly risks memory exhaustion from adversarial data. The adapter therefore caps input and uses the native bounded decompressor, drops partial-output Vec on error, initializes out-owner to null and transfers one native Vec owner only on success. `catch_unwind` contains unwind-mode panics at the C export; allocation abort/process failure is not recoverable through it.

The real research adapter is a small C ABI around the mature algorithm, not a newly written C# codec. C# private SafeHandle leases keep the native output alive during copy and dispose it exactly once through the Rust release function. Synchronous calls borrow input only until return, need no callback registration or executor, and expose no raw pointer to the application. A zero-length input is valid; malformed compressed data and a decompression-bomb limit are negative tests. After native success, a guarded managed wrapper construction releases the transferred raw owner if wrapper construction throws. This was a real independent-review correction; final product fault injection must exercise that construction failure. This simple fixture copies to managed arrays deliberately; it does not claim zero-copy or a hard whole-RSS bound.

Three native tests and independent ordinary/AOT NuGet consumers execute cross-implementation round trips with .NET ZLibStream for zero/small/large payloads. This makes a real native algorithm and compatible managed oracle concrete without inventing another product domain roadmap. No benchmark superiority is claimed.

## Engine two: real asynchronous network service

R27/R29 inspect Tokio/Hyper/Tower/Bytes source, and the native-slices/source-lifecycle plus new server protocol experiments execute actual HTTP, body/permit lifetime, HTTP2 and TLS paths. This is heterogeneous relative to the codec: asynchronous state, connection/task shutdown, streaming flow control, callback roots and retained native buffers. It is not another synchronous byte-sum mock.

Native Hyper owns protocol/connection drivers, Tokio owns runtime scheduling, Tower/Axum provide measured public service/routing seams. A single compiled foreign-service type maps runtime route IDs to C# business dispatch. Adding a managed Handler must not synthesize a Rust trait type or rebuild the server binary. The final C# service bridge's production implementation and complete AOT/soak integration are B15–B20; the research does not mislabel native protocol tests as that completed product.

Body lifetime outlives response-future completion. Admission, stream slots and byte credits attach to the actual owners, including Bytes clones that outlive a Body. Native quiescence and managed queued deliveries jointly retire callback roots. Future cancellation requests do not free buffers or prove connection/worker shutdown. D05/D18 provide the exact state machines.

## Incremental cost and optional capabilities

| Addition | Codec | HTTP Engine | Common code change |
|---|---|---|---|
| Native dependency and adapter | miniz_oxide with two exports (run/release) and owned-result transfer | Hyper/Tokio service/body plus engine-specific host/stream operations | None to SQL/HTTP-independent ABI records |
| Runtime/executor | None | Engine-owned runtime configured/shut down by host | Optional async protocol only; no global runtime required |
| Application variability | Input bytes/options | Route metadata, compiled managed dispatch and payloads | No new Rust type per C# model/Handler |
| Buffer policy | Synchronous borrow plus owned result | Retained chunk owners with backpressure/byte credits | Shared owner contract, distinct domain budgets |
| Error policy | Invalid data, size limit, contained panic | Protocol/transport/timeout/handler/cancel/shutdown | Shared status envelope, engine-specific code/category |
| New GPU/UI module | Separate domain adapter and device/fence/affinity rules | No coupling to HTTP host | Add a negotiated optional capability only when actually shared |

A17 uses this synchronous codec category; A18 uses a real asynchronous HTTP fixture. A24 produces a small manifest/scaffold using the proven pattern. No mandatory Zstandard library is added merely because an old planning example named it; if later selected it must compare .NET11 Zstandard under R17 rules.

## Completion and limits

The two-domain walk-through now has exact native source, adapter behavior, executed normal/error/boundary experiments and a concrete incremental-cost table. D11/D10 define conformance and maintenance. Platform-specific linking, GPU/device loss, mobile lifecycle, final asynchronous C# Handler implementation and production long-load tests stay with their existing Delivery/future-platform owners. They do not invalidate the researched small-Core design or require another plan graph.
