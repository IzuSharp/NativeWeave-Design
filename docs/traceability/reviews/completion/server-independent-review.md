# Independent Server and extension completion review

Reviewer: `/root/database_research`; author: `/root/server_extensions`. This is an independent technical review, not a distinct GitHub approval identity.

## Decision

Accept R26–R30, R32–R34 and D18/D19/D21 for research/design closure at revision0.3.0. The exact29 output hashes and160 supporting frozen-file hashes are recorded in the JSON. No remaining blocking finding. Final author assessment: `8e5f34d7ec37f297cb47dcdd09d5f03e3eced98a9ba6d9373dd4a5128ffd5c8f`.

Read all8 research reports, their current evidence/coverage, all3 normative designs, R27's detailed source-driven/native-slice reports, full experiment/runner sources and historical Body/credit models. Independently read35 concrete upstream source files/ranges, including Tonic/rmcp, winit/wgpu, Native AOT/Rust targets, tracing, Kestrel/OTel, Tower/Hyper and Actix/Pingora. Source identity checks are not whole-repository audits or upstream-suite executions.

## Findings resolved

| Finding | Problem and verified correction |
| --- | --- |
| DB-SERVER-01, medium/blocking | Tonic unary silently drains additional messages. A fresh per-request mode-aware Decoder now rejects a second message before the Handler while preserving empty messages and multi-message streaming. Five separate reviewer-written Linux tests passed; the author's corrected suite passed19. |
| DB-SERVER-02, low | R27 now assigns route declarations to C# and route matching/dispatch to Rust; only an application without Server can omit the native Server package. |
| DB-SERVER-03, medium/blocking | Dispatch callback only borrows fixed notification fields/ticket; typed take outside callback atomically transfers named request/header owners once, preserving pending leases/budgets and one cleanup path. |
| DB-SERVER-04, low | Exact mobile/Android source EOF ranges corrected without changing upstream identity. |
| ROOT-CI-DIAGNOSTIC-01, externally reported | Original Windows measurement failure is retained. Clock warmup is outside allocation measurement; actual observation prints before assertion. Corrected Linux11 assertions pass; this review does not infer a corrected Windows result. |

## Evidence verified

All160 frozen files,29 task outputs and117 embedded evidence hashes match. Four CI ZIPs from run43388468172 contain48 verified archive files; four built binary/debug outputs were verified directly from ZIP rather than written into the source repository. All28 command streams and14 immutable-commit source identities match, with exact CRLF conversion for7 Windows inputs. Protocol13/13 and Kestrel5/5 actually passed on both Windows and Linux. No successful research probe was rerun just to increase counts.

The corrected author suite's19 Linux cases and the independent reviewer's5 Linux cardinality regressions are real. Six previously published retained-Bytes/Body/Tokio cases passed both platforms; their24 preserved files and10 exact source inputs were checked. The282-state/895-transition logical-credit model and45-state negative/24-state candidate Body admission model were read with their explicit fairness/weak-memory/RSS limits. Scoped diagnostics/layout observations and original failed attempts remain distinguished.

## Architectural conclusion and limits

The required host is the mature Rust Tokio/Hyper/Tower composition, with selective native Axum routing; C# owns application declaration, typed DTO mapping and business Handlers. Native Tonic/rmcp/rustls preserve protocol and transport ownership. Runtime method/tool metadata avoids per-entity/per-Handler Rust compilation. A narrow adapter enforces missing public-seam policies such as cardinality and total request deadlines without implementing a second managed protocol engine.

Body completion does not retire externally held Bytes, and cancellation does not manufacture rollback or quiescence. Dispatch, typed result transfer, callback roots and cleanup follow the accepted Core lifecycle. Future GUI/GPU/mobile designs retain domain-local affinity/progress and honest toolchain/device limits; no giant Core or current mobile support claim is introduced.

Full generated C# callback bridges, integrated TLS/network/gRPC/MCP conformance, production fuzz/sanitizer/load, independent NuGet consumption and physical-device verification remain explicit future Delivery obligations. Research design acceptance does not require those future products to exist first.
