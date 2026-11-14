# NativeWeave C# Public API Specification

Version: 0.4.0. Scope: design and implementation instructions, not a released SDK. The exact current acceptance record determines review status. No NativeWeave product functionality is implemented by the declaration fixtures in this repository.

## Authoritative layers

| Layer | Authority | Meaning |
| --- | --- | --- |
| Engineering standard | [C# API and documentation standard](../standards/csharp-public-api-and-documentation.md) | Mandatory reusable design, implementation, documentation and review rules |
| Exact public declarations | [Design declaration project](../../experiments/public-api/NativeWeave.Api.Design/) and [generated reference](reference.md) | Namespaces, types, members, constraints, overloads, nullability and defaults |
| Domain semantics | [Database](database.md), [Server](server.md), [Interop](interop.md) | Results, lifecycle, errors, concurrency, capability, costs and exact native operations |
| Developer journey | [NuGet and consumption](nuget-and-consumption.md), [getting started](getting-started.md), [guides](guides.md) | Installation, imports, configuration, normal operations, troubleshooting and AOT |
| Coverage and provenance | `foundation-coverage.json`, `database-coverage.json`, `server-coverage.json`, `interop-coverage.json`, corresponding source manifests | Relevant .NET feature families, actual source inspected, support decisions and owning tasks |
| Documentation maintenance | [Documentation system](documentation-system.md) | XML/API reference, sample states, compatibility and future CI ownership |
| Acceptance | [Contract registry](../contracts/registry.json), [independent reviews](../traceability/reviews/public-api-2026-11-14/), Plan's existing graphs | Exact reviewed inputs; preserved previous accepted versions |

Read declarations and domain semantics together. A property signature does not specify its lifetime, and an upstream feature does not establish NativeWeave support. An explicit unsupported/planned coverage row is not an implementation gap in a different supported row.

## Stable technology baseline

Official release pages observed on 2026-11-14 identify .NET 11.0.0, SDK 11.0.100, C# 15.0 and Rust 1.100.0. Fixed .NET 11 runtime, EF Core, ASP.NET Core and mature library sources are recorded in the source manifests. Existing Rust source pins and finite experiment identities remain authoritative unless a documented delta replaces them. No Preview language feature is required by the declarations.

This extension preserves the existing 21 contracts and 34R/32D/48 Delivery structure. The domain files refine those contracts; they do not introduce another task graph. Ordinary Entity/DTO/Handler additions compile into the C# application and static metadata, with precompiled Rust assets reused. Core owns no SQL or HTTP engine and no default global Tokio runtime.

## Evidence states

The `experiments/public-api` project compiles design declarations, checks consumer syntax and builds a reference inventory. Its native-facing bodies deliberately fail if invoked; they are not a product implementation. Validation manifests state whether compilation, generator checks, package-fixture consumption, or Native AOT fixture execution actually occurred and on which platform. Product database/server execution, pristine no-Rust installation, production load and performance remain acceptance obligations of the existing Delivery tasks.

## Implementation entry

Future Codex work starts from the relevant `Plan:tasks/<ID>.md`, the exact Design commit pinned by Plan, the symbol/reference inventory, domain operation table and the standard. A13 installs shared rules; each module implements and documents its own symbols; A22 checks compatibility; A16/B24 gate package and consumer releases. Read the [adoption checklist](../../templates/public-api/adoption-checklist.md) before creating another repository.
