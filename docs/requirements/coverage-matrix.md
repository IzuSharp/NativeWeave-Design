# Scope coverage and omission checks

Status: planning coverage; this does not mean research/implementation is complete. See [requirements-map.json](../traceability/requirements-map.json) for the full machine-readable mapping. All IDs come from the current three graphs and have actually been checked for existence.

| Requirement | Scope | Research | Documentation | Delivery candidates | Evidence method |
| --- | --- | --- | --- | --- | --- |
| NW-A01 | ABI, type layout, versions, and target differences | R03, R04 | D02, D03 | A01, A02, A10, A11, A22 | Source+three-way layout/call checks+old/new version combinations |
| NW-A02 | Bindings, strongly typed Adapters, Generators, and Analyzers | R04, R05, R06 | D03, D23 | A09, A10, A11, A12 | Generated snapshots+incremental/negative diagnostics+actual AOT |
| NW-A03 | Ownership, Lifetime, GC, and parent-child resources | R07, R10, R15 | D04, D22 | A03, A04, A19, A20 | Lease models+release races+actual FFI |
| NW-A04 | Callbacks, unregistration, reentrancy, and release races | R08, R11, R12 | D05, D08, D24 | A06, A07, A19, A20 | Unregistration quiescence+process-isolated callback negative cases |
| NW-A05 | Async, Cancellation, and exactly-once completion | R09, R12, R15 | D06, D24 | A07, A08, A18, A19 | Terminal-state/quiescence separation+models+actual AOT async |
| NW-A06 | Memory, Buffer, Pinning, transfer, and batching | R10, R16, R17 | D07, D13 | A04, A17, A18, A20, A21 | Allocator/alias/overflow+fuzz+copy ledger |
| NW-A07 | Error, panic, and ABI exception boundaries | R11, R04 | D08, D03 | A05, A12, A20 | Unwind/abort/UCO signatures+subprocess |
| NW-A08 | Concurrency, threads, Runtime, and backpressure | R12, R09, R29 | D09, D24 | A08, A18, A19, A23 | Bounded resources+shutdown+thread affinity |
| NW-A09 | Build, AOT, NuGet/Cargo, and release compatibility | R01, R02, R13, R14 | D01, D10, D25 | A13, A14, A15, A16, A22 | Actual Windows/Linux targets+clean consumer+SBOM |
| NW-A10 | Standard Engine integration and at least two heterogeneous real modules | R18, R17, R12 | D11, D26 | A17, A18, A23, A24 | Real synchronous and asynchronous engines+application costs without Rust |
| NW-B01 | Database, connection pools, transactions, migrations, and recovery | R19, R20, R21, R22 | D14, D15, D27 | B01, B02, B03, B04, B05, B06, B07, B08 | Real PG/SQLite databases+AOT+disconnection/unknown commit outcomes |
| NW-B02 | ORM, LINQ, code generation, and SQL semantics | R23, R24, R25, R06 | D16, D17, D28 | B09, B10, B11, B12, B13, B14 | Supported/rejected syntax+SQL differential testing+static mapping |
| NW-B03 | Server, HTTP/TLS, gRPC/MCP, streaming, and diagnostics | R26, R27, R28, R29, R30 | D18, D19, D29 | B15, B16, B17, B18, B19, B20 | Kestrel comparison+backpressure+protocol AOT+drain |
| NW-B04 | DB/Server reference application, sustained fault workloads, and release | R31, R17, R16 | D20, D30 | B21, B22, B23, B24 | Three routes with identical semantics+independent actual acceptance |
| NW-X01 | GUI/GPU/NSH/thread-affinity extensions | R32, R18 | D21, D11 | A23, A24 | Integration constraints and probes; no complete GUI promised |
| NW-X02 | iOS/Android/static linking and lifecycle | R33, R02 | D21, D01 | A23, A24 | Verification by target profile; does not gate unrelated desktop work |
| NW-P01 | C# First | R17, R19, R26 | D11, D13, D14, D18 | A21, B02, B15, B23 | Pure C# native-compilation baseline and dependency graph |
| NW-P02 | Native AOT Required | R02, R13 | D01, D10 | A14, A15, B24 | Record publish and actual execution separately |
| NW-P03 | Rust When Justified | R17, R18, R19, R27 | D11, D13, D14, D18 | A17, A18, B04, B17, B23 | Adoption ADR based on capabilities/cost/reliability or measurements |
| NW-P04 | Framework simplicity, elegance, and efficiency | R06, R12, R17, R25 | D03, D09, D13, D16 | A21, B23 | Abstraction/runtime/dependency/developer-experience cost ledger |
| NW-P05 | Independent Engines | R14, R18 | D10, D11, D31 | A16, A24, B24 | Independent package/contract/release profiles |
| NW-P06 | Standard Native-ready integration | R18, R13, R14 | D10, D11, D31 | A24, A16 | End-to-end conformance and a new-engine task template |
| NW-P07 | Performance by Evidence | R17 | D13 | A21, B23 | Comparable workloads, memory/threads/copies/distributions |
| NW-P08 | Parallel Research/Documentation/Delivery work | R15, R16 | D31, D32 | Governance checks | Three-graph structure, local-dependency, and file-ownership checks |
| NW-P09 | Plan both phases in depth concurrently | R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31 | D14, D15, D16, D17, D18, D19, D20, D27, D28, D29, D30 | B01, B02, B03, B04, B05, B06, B07, B08, B09, B10, B11, B12, B13, B14, B15, B16, B17, B18, B19, B20, B21, B22, B23, B24 | Concrete task/specification coverage for phase B |
| NW-P10 | Independent NativeWeave content; Arc is a formatting reference only | Requirements constraints | D31, D32 | Governance checks | Requirements charter, documentation, and dependency review |
| NW-P11 | Latest stable technology with preview features isolated | R01, R02 | D01, D03 | A12, A13 | Dated official facts+feature status+compiled examples |
| NW-P12 | Honest evidence and independent Review | R15, R16, R34 | D12, D32 | A19, A20, B22 | Status/hash/provenance+review by a different author |

## Items requiring particular attention to avoid omissions

- Explain task-completion notification, native resource quiescence, and draining managed cancellation registrations separately.
- Validate NULL, collation, sorting tie-breaks, numbers/time zones, and unknown transaction outcomes separately.
- Migrations, schema, pool reuse, and early exit from streaming are not empty subsidiary items of ORM mapping.
- Package provenance, licenses, platform ISA, loading paths, old/new ABI combinations, and independent Engine releases all have owners.
- Measure P99 under high throughput, failure rates, RSS/GC/native memory/threads, sustained workloads, and recovery separately.
- GUI/mobile are boundary research; the desktop baseline does not wait for all future platforms to be complete.
- Domain drafts may begin immediately; formal contract/product acceptance depends on specific evidence and independent review.

## Complete index of the three graphs

### Research

| ID | Task |
| --- | --- |
| R01 | Stable Toolchains and Modern Language Mechanisms |
| R02 | Native AOT, Trimming, and Platform Support |
| R03 | C ABI, Layout, and Version Negotiation |
| R04 | P/Invoke, Callback Entry Points, and FFI Call Cost |
| R05 | Binding Generators and Contract Description Sources |
| R06 | Roslyn Incremental Generation and Analyzers |
| R07 | Handles, Ownership, GC, and Parent-Child Resources |
| R08 | Callback Unregistration, Reentrancy, and Release Races |
| R09 | Async, Cancellation, and Completion State Machines |
| R10 | Buffers, Pinning, Batching, and Data Transfer |
| R11 | Errors, Panics, Exceptions, and Fault Isolation |
| R12 | Concurrency, Executors, Thread Affinity, and Shutdown |
| R13 | MSBuild/Cargo, Linking, and Target Platforms |
| R14 | Packaging, Compatibility, Independent Releases, and Provenance |
| R15 | Formal Methods and Concurrency Proof Obligations |
| R16 | Differential, Property, Fuzz, and Fault Testing |
| R17 | End-to-End Performance, Memory, and Development Cost |
| R18 | Capability-Based Engine Integration and Generality |
| R19 | PostgreSQL Drivers and Pure C# Baselines |
| R20 | SQLite Adaptation, Concurrency, and Threading Restrictions |
| R21 | Connection Pools, Transactions, Cancellation, and Recovery |
| R22 | Type Mapping, Batched Streams, and Schema Evolution |
| R23 | LINQ, Expression, and Compile-Time Query Capture |
| R24 | SQL Semantics, Relational Algebra, and Parameter Safety |
| R25 | ORM Features, Tracking, and Comparison of Existing Solutions |
| R26 | Kestrel and Pure C# AOT Server Baselines |
| R27 | Rust Networking Engines and C# Handler Boundaries |
| R28 | gRPC, MCP, TLS, and Protocol Adaptation |
| R29 | Request Streams, Backpressure, Timeouts, and Graceful Shutdown |
| R30 | Observability, Diagnostic Correlation, and Cost |
| R31 | Database + Server Reference Application and Fault Recovery |
| R32 | Desktop GUI/GPU and Thread-Affinity Extensions |
| R33 | iOS/Android, Static Linking, and Platform Lifecycles |
| R34 | Boundary Security, Input Validation, and Resource Abuse |

### Documentation

| ID | Task |
| --- | --- |
| D01 | Toolchain, AOT, and Platform Specification |
| D02 | ABI and Type Layout Contract |
| D03 | Binding IR, Generator, and Analyzer Specification |
| D04 | Ownership and Resource Lifetime Contract |
| D05 | Callback Registration, Revocation, and Quiescence Contract |
| D06 | Async Completion and Cancellation Contract |
| D07 | Buffer, Transfer, and Memory Contract |
| D08 | Error, Panic, and Exception Boundary Contract |
| D09 | Concurrency, Runtime, and Shutdown Specification |
| D10 | Build, Packaging, Versioning, and Provenance Specification |
| D11 | Engine Integration Specification and Two-Module Verification |
| D12 | Proof Obligations and Actual Verification Specification |
| D13 | Performance, Memory, and Developer Experience Methodology |
| D14 | Database Driver Capabilities and Adaptation Specification |
| D15 | Connection Pool, Transaction, and Recovery Contract |
| D16 | Query IR, SQL Semantics, and ORM Scope |
| D17 | AOT Query Capture, Generation, and Safe Dynamic APIs |
| D18 | Server Lifecycle and Adaptation Specification |
| D19 | Protocol, Observability, and Security Specification |
| D20 | Production-Grade Reference Application and Acceptance Design |
| D21 | Extension Boundaries for Future Engines and Mobile Platforms |
| D22 | Preparation of ABI, Memory, and Resource Development Tasks |
| D23 | Preparation of Generator and Analyzer Development Tasks |
| D24 | Preparation of Callback, Async, and Runtime Tasks |
| D25 | Preparation of Build, Packaging, and Independent Release Tasks |
| D26 | Preparation of Engine, Proof, Testing, and Benchmark Tasks |
| D27 | Preparation of Complete Database Implementation Tasks |
| D28 | Preparing ORM and LINQ AOT Implementation Tasks |
| D29 | Preparation of Server and Protocol Implementation Tasks |
| D30 | Preparation of End-to-End, Long-Running-Load, and Domain Release Tasks |
| D31 | Global Traceability, Version Compatibility, and Future Engine Task Specification |
| D32 | Independent Cross-Review and Delivery Readiness Review |

### Delivery A

| ID | Task |
| --- | --- |
| A01 | ABI Descriptions, Layout Probes, and Version Reads |
| A02 | Status, Capability, and Compatibility Negotiation Entry Points |
| A03 | Synchronous Handles and Resource Leases |
| A04 | Owned Buffers and Async Leases |
| A05 | Controlled Error and Panic Conversion Boundaries |
| A06 | Callback Registration, Revocation, and Draining |
| A07 | Task Async Bridge and Cancellation State Machine |
| A08 | Optional Executors, Capacity, and Shutdown |
| A09 | Binding Contract IR and Input Validation |
| A10 | C# LibraryImport Binding Emission |
| A11 | Rust Exports and ABI Consistency Checks |
| A12 | ABI, Lifetime, and AOT Analyzers |
| A13 | MSBuild and Cargo Reproducible Build Graph |
| A14 | Linux Native Artifacts and AOT Package Verification |
| A15 | Windows Native Artifacts and AOT Package Verification |
| A16 | Independent NuGet/Crate Releases and Provenance Records |
| A17 | Actual Synchronous Engine Integration Verification |
| A18 | Actual Async Engine Integration Verification |
| A19 | Executable Lifetime and Async Models |
| A20 | Cross-Language ABI and Resource Property and Fuzz Testing |
| A21 | Three-Path Benchmark and Resource Observation Tools |
| A22 | ABI/API Upgrades and Compatibility Testing |
| A23 | Thread-Affinity and Special-Platform Integration Probes |
| A24 | Engine Integration Scaffolding and Conformance Entry Points |

### Delivery B

| ID | Task |
| --- | --- |
| B01 | DataSource and Database Capability Foundations |
| B02 | PostgreSQL Pure C# Adaptation and Baseline |
| B03 | SQLite Adaptation and Thread/Lock Semantics |
| B04 | Optional Rust PostgreSQL Engine and Adapter |
| B05 | Transaction State, Pool Leases, and Recovery Policies |
| B06 | Batching, COPY, and Streaming Reads |
| B07 | Statically Typed Codecs and Value Semantics |
| B08 | Migrations, Schema Checks, and Upgrade Coordination |
| B09 | Restricted Query-Semantics IR |
| B10 | Incremental Generation for LINQ/Fluent Syntax Capture |
| B11 | PostgreSQL/SQLite SQL Dialect Generation |
| B12 | Static Mappers, Entity Metadata, and AOT |
| B13 | Safe Runtime Dynamic-Query API |
| B14 | Relationships, Units of Work, and Concurrent Updates |
| B15 | Kestrel Native AOT Host and Handler |
| B16 | HTTP Streams, Request Budgets, and Backpressure |
| B17 | Optional Rust Server Engine Adaptation |
| B18 | Strongly Typed gRPC and AOT Protocol Packages |
| B19 | MCP Protocol Packages and Static JSON Metadata |
| B20 | Diagnostic Correlation, Timeouts, and Shutdown Coordination |
| B21 | General-Purpose Idempotent Task Reference Service |
| B22 | End-to-End Fault, Crash, and Long-Term Resource Verification |
| B23 | Domain Full-Workload Performance and Memory Report |
| B24 | Domain Compatibility Matrix, Independent Packages, and Release Acceptance |



## Source-driven amendment / 2026-11-12

Existing IDs remain authoritative. R19–R25/D14–D17/B01–B14 cover native SeaQuery/SQLx, no managed fallback or per-entity Cargo, typed Fluent instead of full LINQ SQL translation. R26–R31/D18–D20/B15–B24 cover native Service/Body reuse and retirement budgets, retaining Kestrel AOT. R13/R14/R18/D10/D11/A13–A16/A22/A24 cover precompiled consumers, upstream mapping and controlled upgrades. See [impact/recovery record](../traceability/source-driven-impact.md). Partial source evidence does not complete all tasks.
