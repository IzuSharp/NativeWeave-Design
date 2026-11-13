# SQLx SQLite cancellation and retirement research

This continues R20/R21/R25 after the PR1 assets were migrated into Design. It is
a separate finite experiment, not product implementation or a replacement for
`experiments/native-slices/database`.

## Execute

Install the pinned Rust 1.100.0 minimal toolchain. A local C toolchain is required
for the bundled SQLite build. From the repository root, on Linux or Windows:

```text
python experiments/database-retirement/run.py --out <new-evidence-directory>
```

The runner uses `cargo +1.100.0 test --locked -- --nocapture --test-threads=1`.
It refuses to overwrite an existing result, records the six passed test names,
and preserves commands, versions, dependency tree, stdout/stderr and exact input
files with SHA256. A process-level timeout is a failed execution; it does not
establish native retirement.

No external database service is required. SQLite is in-memory, with one pool
connection, command capacity eight and row capacity one. The TEMP-table marker
checks actual physical connection reuse. Those item capacities do not prove
byte or RSS bounds.

## Tests

1. Dropped transaction rolls back before the same physical connection is reused.
2. Early stream drop unblocks the bounded row path for the tested SELECT.
3. Canceling a pending acquire does not lose the pool's only permit.
4. Dropping a dispatched COMMIT future before acknowledgment can still commit.
5. Removing/replacing a progress handler isolates old cancellation state.
6. Pool close waits for an outstanding owner and rejects new acquisition.

The COMMIT witness deliberately pauses a **test-only native SQLite commit hook**
using a host-controlled channel. Production progress/FFI/finalizer callbacks must
not copy that blocking behavior. On a test error, dropping the release sender
also releases the hook. The test's later query is a direct recovery observation;
dropping the future itself carries no outcome proof.

## Evidence and identity

- [Execution summary](execution-summary.json) selects the final local result and
  lists retained earlier attempts.
- [Source inspection](source-inspection.json) binds six selected upstream files
  to actual registry source bytes and checks five package archives against the lock.
- [Design study](../../docs/database/sqlx-retirement-study.md) explains the
  call chains, contract consequences and remaining gates.

The initial lockfile was copied from `experiments/native-slices/database` and
only its root package name changed; Cargo's locked executions validate this
closure. The final crate's dependencies are test-only. No dependency versions
were upgraded for this experiment.

The first local attempt is retained as a failure of Cargo's
unused-dependencies lint. The correction was to declare test-only dependencies
as dev dependencies; the lint remains enabled. Subsequent raw results are kept
separately. Native success does not imply C# Native AOT success, PostgreSQL
behavior, OS thread join, hard cancellation deadlines, memory bounds,
performance or acceptance of a proposed contract. Hosted Windows/Linux results
must be recorded under their own run/commit identities when actually executed.
