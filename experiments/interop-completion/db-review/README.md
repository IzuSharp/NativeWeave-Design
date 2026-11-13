# Independent SQLx migration admission regression

This three-case Linux Rust fixture was authored and executed by the independent
database design reviewer `/root/interop_research`. It resolves a concrete public
API ambiguity in R20/R22 and D14/D15. It is a research fixture in Design, not a
product database implementation or a replacement for the published eleven-case
database-completion fixture.

With the pinned Rust 1.100.0 toolchain and cached dependencies:

```sh
cargo test --locked --offline --test migration_admission -- --nocapture
```

Run from this directory. Cargo.lock fixes SQLx 0.9.0 and Tokio 1.54.1. The actual
command, toolchain, source hashes, stdout/stderr and result are preserved in
`verification/interop-completion/db-review-migration/` relative to the repository
root. The result records a dirty-worktree execution by exact input hashes; it does
not claim a nonexistent committed source revision.

The negative control begins a transaction through raw SQL. SQLx's tracked depth
remains zero and Migrator's internal BEGIN fails. The positive path uses
`Connection::begin_with("BEGIN IMMEDIATE")`, passes `&mut *tx` to Migrator, and
checks that its nested savepoints preserve the outer transaction. Explicit outer
rollback removes schema and ledger; the successful commit preserves the ledger.
A failing second migration is followed by outer rollback and leaves neither
first nor partial schema nor ledger.

The three cases passed. They do not test concurrent processes, Windows, filesystem
crash recovery, nontransactional migrations, C# or Native AOT. The design rejects
`no_tx` entries before entering this atomic profile. B08 retains those product
and platform obligations, including preservation of both the migration error and
any cleanup error.
