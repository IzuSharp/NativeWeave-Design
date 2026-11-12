# Recovered source-driven evidence — 2026-11-12

This directory preserves evidence from the interrupted PR #5 investigation. It is not a new execution or an independent review. `recovery-manifest.json` identifies exact baseline commits, Actions run/artifact IDs, ZIP hashes and recovered text-file hashes. The original artifact expiry must not make the decisive logs inaccessible; selected logs, Cargo.lock and executed prototype inputs are therefore retained here. Binary packages remain in the original artifact and are not represented as a product release.

## What actually executed

Actions run **43245931319**, head **16e673b1077f6784936703f4c4dc38b46b4d058b**, built a Rust native library, packed a local research NuGet, and built, published with Native AOT, and executed a Linux x64 C# application against SQLite. Four Rust tests passed. Adding a `User` C# entity with handwritten static metadata and a DTO constructor did not rebuild or change the packaged native library. Its SHA-256, rechecked from the recovered NuGet, is `e47fee8b949599ed5430af36aa403f7782b33d7402b249709c71e50f74dad52e`. The wrong-entity typed-column negative fixture failed compilation as expected.

Read `commands.json`, the corresponding raw logs, `result.json` and `probe-inputs/` together. The `.csproj` and “Generating native code” publish output plus actual native executable invocation are the AOT evidence, not a successful JIT `dotnet test`. The first probe attempt, run **43245538699**, failed against SQLx 0.9 APIs. The existing workflow explicitly produces and records `probe-resolved.py`; the corrected input uses `AssertSqlSafe` only for SeaQuery-generated parameterized statements and removes the obsolete SQLite argument lifetime parameter. Do not erase this failed attempt or attribute the passing run to the uncorrected input.

## Deliberately narrow interpretation

* Consumer build/run commands used `-r linux-x64`. RID-free ordinary `dotnet build` / `dotnet run`, clean restore and package discovery remain required tests.
* Rust invocation was denied with PATH shims. That tests accidental invocation, not an independently provisioned machine without a Rust installation.
* Metadata and DTO decoding were handwritten static C#. A production source generator was not implemented or tested.
* PostgreSQL SQL text/placeholders were inspected in the probe; no PostgreSQL server execution occurred.
* The prototype creates a Tokio runtime and SQLx pool per execution, uses `fetch_all` and JSON, and has raw exclusive-use pointer handles. These are research shortcuts, **not** the proposed production runtime, streaming, concurrency or hard memory-budget implementation.
* Row limits and a managed result-size check do not bound a huge native field, intermediate allocation, pool waiters, total RSS or concurrent callers. No performance advantage, production completeness or full ORM semantics is established.
* No Windows, ARM, production shutdown/callback race, unknown-commit fault or load/soak result is claimed.

`source-lock.json` records the initial collector. `corrected-pins.json` supersedes its SQLx owner resolution and Actix package-tag mistakes. Downloading a repository is not reading it. New reports identify inspected ranges and distinguish inspected tests from executed tests. Git source snapshots and Cargo registry packages are separate evidence identities; equality between a tag tree and registry crate contents was not independently established.

## Recovery and review

Six individually attributable completed subagent outputs were not recovered from the current accessible conversation, filesystem or GitHub records. Historical PR #2–4 reviews apply to their original hashes, not to this amendment. The recovery session has no callable subagent interface and has performed author-side source inspection, integration and checks only. An independent reviewer must review the final PR #5 and paired Plan commit; see the existing `Plan:prompts/independent-review.md` plus the bounded handoff in `docs/traceability/source-driven-impact.md`.

`recovery-model-run.json` belongs to a **new**, locally executed finite Python model in R27, not to the original Actions run. It checks a small admission abstraction and is not a Rust Server execution.
