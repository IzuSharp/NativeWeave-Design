# ADR-0004: Complete C# public API and continuous documentation

Status: design decision; exact accepted version is recorded in the contract registry and public API review. Date: 2026-11-14.

## Context

The accepted Rust/C# lifecycle architecture and finite research experiments are substantially more precise than several existing public API examples. Future implementers should not invent incompatible C# signatures, require repeated entity/handler glue, or complete code without user-facing documentation. An upstream Engine's feature list is not a C# feature inventory.

## Decision

Adopt the versioned [C# Public API Design and Documentation Standard](../standards/csharp-public-api-and-documentation.md). Define exact compileable public declarations, per-domain semantics and complete public-to-native mappings. Compare relevant stable .NET 11/C# 15 public feature families and record explicit support/exclusion/cost/AOT/task mappings. Preserve mandatory Rust Database/ORM/Server foundations and independent Engine composition.

Use familiar C# factories/builders, Task-based operations, async enumeration, normal disposal, static mapping/JSON and Extensions integration where it actually improves application code. Keep raw ABI and native handles internal. Domain-specific outcome/cleanup results remain explicit when an ordinary exception cannot express the accepted contract.

Create isolated Design-only signature, consumer, generator and AOT compilation experiments; label their evidence narrowly. Future product packages remain unimplemented and all 48 Delivery tasks remain not_authorized. The actual product assembly plus XML will become the release API Reference source. Every implementing task owns its documentation and consumer tests.

Amend existing Design contracts and Plan packets rather than create a fourth graph. Preserve historical accepted inputs and issue new exact independent acceptance for materially changed designs. Add root AGENTS/README entry points and an explicit new-repository adoption template. GitHub rules and product authorization are unchanged.

## Consequences

The public contract becomes concrete enough to implement and review, while supported capability does not imply release availability. A typed façade can differ from EF Core or ASP.NET internals and still feel natural. Ordinary entity/DTO/handler additions stay in C#; native source upgrades remain maintainer work. Explicit cost and scope decisions prevent convenience from hiding a second runtime, unbounded buffers or duplicate engines.

Maintainers now own API compatibility, XML/reference generation and example CI as part of each change. API amendments require real re-review and hashes; a global status or a previous translation approval cannot accept new content. Future projects must actually adopt the standard; they do not inherit this repository's AGENTS.md automatically.
