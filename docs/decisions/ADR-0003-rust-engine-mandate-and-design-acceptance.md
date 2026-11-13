# ADR-0003 — Rust engine mandate and scoped design acceptance

Date: 2026-11-12 (America/Los_Angeles). Status: user-required architecture constraints;
implementation selections and individual technical contracts still require their scoped reviews.
Supersedes contrary product-choice assumptions in ADR-0002, the original charter and
the source-lifecycle host-selection follow-up. Original evidence and reviews retain their historical scope.

## Context and decision

NativeWeave lets application developers use mature Rust engines through modern, natural,
strongly typed C# Native AOT. C# First describes the application programming language.
It does not select managed implementations for the native domains that the user explicitly requires.

Database drivers, query AST and SQL dialects, execution, pools, transactions and supported ORM
relations operate in Rust. Server networking, HTTP protocol, connections, scheduler, streaming,
backpressure and native resources operate in Rust. Managed DB providers and Kestrel are
research/benchmark comparators. They are not alternative production backends or fallback Hosts.

Within Rust, choose components from actual source, boundary semantics, experiments and maintenance
cost. SeaORM is neither compulsory because of its name nor categorically rejected because a static
Entity API exists. Reuse useful dynamic projection, relation/loader and transaction mechanisms only
where their real generic/metadata/lifetime constraints fit. Keep query construction in SeaQuery and
driver/protocol work in a mature Rust driver. The current dynamic SeaQuery/SQLx route is investigated
and refined by R19–R25; its supported ORM scope must be explicit.

The Server study compares Tokio/Hyper/Tower/Axum, Actix and Pingora within this Rust mandate.
Kestrel remains necessary comparison evidence for behavior, cost and resource use. A measured
regression must be reported and addressed; it does not silently override the user's product boundary.

Ordinary C# entity, DTO, predicate and Handler changes reuse maintainer-precompiled native modules.
Handwritten static descriptors and optional generators are valid language-interface mechanisms.
No complete managed SQL AST/dialect engine or full EF-compatible LINQ provider is required.

## Minimum shared mechanisms

Use target C ABI, explicit capability/version negotiation, resource ownership, buffers, errors and
operation/callback retirement. Keep SQL, HTTP, GUI and GPU objects in their Engine. A domain's need
for Tokio does not force a global Core runtime or other Engines to use that scheduler. Borrowed calls,
owned asynchronous resources and thread-affine engines have different lifecycle capabilities.
Public APIs are preferred; source-informed adapters, small upstream extensions and controlled forks
need concrete capability/maintenance evidence and a documented retirement strategy.

## Acceptance boundaries

1. Research acceptance: fixed source identity and read scope, answered research questions, relevant
   normal/error/boundary analysis, necessary experiments, explicit limits and independent review.
2. Design acceptance: concrete interfaces and ownership/state/error/close rules, coherent dependencies,
   implementation steps and test oracles, source evidence and independent review of exact content.
3. Product acceptance: implemented code, real Windows/Linux AOT and package consumption, actual DB
   and network behavior, race/fault/upgrade/soak/performance evidence for the declared release profile.

The first two can be accepted without claiming the third. No future product test is fabricated or
removed. A missing experiment that prevents a defensible design remains a research blocker with an
exact action; a release/soak obligation alone does not leave an otherwise reviewed design perpetually planned.

## Existing task identities and consequences

Retain all 34 R, 32 D and 48 A/B IDs. B15 becomes the C# Server application declaration and Handler
surface; B17 becomes the required Rust Host adapter. B15 and B17 are complementary modules, not
competing Hosts. R26 remains Kestrel comparison research. Protocol adapters consume the Rust Host
contract, with no implicit ASP.NET/Kestrel dependency. D22–D31 provide the existing ten task fragments.

Review all current prose, graph fields, packet bodies, examples and validator policies for the same
boundary. Historical immutable evidence may contain superseded assumptions and must be labelled
historical instead of edited into evidence of a different execution. This ADR authorizes no product writes.
