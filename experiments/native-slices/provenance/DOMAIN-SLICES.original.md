# Existing R22/R25 and R27/R29 — executable domain continuation

These are small independent Rust fixtures, not a new ORM/Server or accepted Delivery implementation. They add missing actual library execution to the previous source analysis, while the recovered Interop slice separately exercises C# Native AOT. No new C# domain binding, PostgreSQL, TLS, load, async callback retirement or full memory bound is claimed here.

## Database

Pinned SeaQuery1.0.2 + SQLx0.9.0 + Tokio1.54.1. Reuse the native SQL builder and execution implementation. A small scalar-subset binder preflights parameter count/payload/narrowing, propagates SQLx `Arguments::add` failures, and rejects unsupported variants rather than hiding errors. The deliberate failed encoder writes one value then errors, exercising SQLx's rollback of partially encoded arguments. Native Value/String allocation before this function is explicitly outside its local conversion budget.

Actual SQLite tests cover overflow before any database-send counter increment, zero rows after rejection, runtime table identifiers (including a quote), bound hostile-looking values, native CRUD, wrong-type `try_get`, explicit rollback and missing-column errors. A negative control demonstrates SeaQuery's SQLite FOR UPDATE omission; the finite wrapper rejects that capability at entry. This is not an all-operator/backend validator or complete ORM, and it does not silently replace mature Rust internals with a C# SQL AST.

## Server

Pinned Hyper1.12.0 / hyper-util0.1.21 / Tower0.5.3 / Tokio1.54.1. Actual Tower ConcurrencyLimit demonstrates a second response can be admitted while the first Body is still alive. A separate stream-slot owner shared by Body and a simulated foreign callback retains its permit until both retire. A capacity-one body channel is tested for backpressure and EOF/drop. The Hyper HTTP1 client/server test uses a real in-process duplex transport, a pending Service future and streamed frames; this is not an external socket/TLS or a C# handler test.

The permit is a **stream-slot** limit, not a retained-Bytes/RSS proof. A channel count cannot bound arbitrary chunk size. Callback retirement here is represented by explicit ownership; no GCHandle/native-to-managed asynchronous protocol is certified. Both engines remain independent packages without a shared Core runtime.

## Locking and provenance

The workflow only creates missing lockfiles for these NEW research packages, commits them to this existing feature branch, and then runs `cargo test --locked` against that exact resulting commit on both OS. Existing locks are not refreshed. Direct package versions are exact; the full resolved closure is recorded, not automatically declared security-approved or identical to inspected Git snapshots. This initialization is an explicit research dependency resolution, not a production upgrade or use of cooldown as a vulnerability scanner. No source workflow changes main, protection or LICENSE.

Test stdout/stderr, commands, exact source/lock hashes and CI run identities are retained as artifacts and must be persisted into the existing Design evidence paths before relying on expiring artifacts. Passing finite fixtures does not mark B04/B11/B17 or any production task accepted. R25/R27 are continuable even while production contracts are proposed.
