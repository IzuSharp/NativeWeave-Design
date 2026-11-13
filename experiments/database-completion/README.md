# Database completion research fixture

This is a finite R19–R25/R31 study in Design, not a NativeWeave product implementation.
It complements the preserved native-slices and database-retirement evidence rather
than rerunning them as new coverage. All dependency identities are in Cargo.lock.

## Commands

With Rust 1.100.0:

```sh
cargo test --locked --test runtime_metadata -- --nocapture
cargo test --locked --test postgres -- --ignored --nocapture --test-threads=1
```

The first command runs on Windows/Linux without an external database. The second
requires `DATABASE_URL` for a disposable PostgreSQL database with create/drop-table
permission and a plain TCP endpoint. It explicitly disables TLS only in this local
fault-injection fixture; production TLS is not tested or disabled by this study.
Do not point it at application/user data. Missing DATABASE_URL is a test failure,
not silently successful skipped coverage. Normal `cargo test` reports the PG cases
as ignored; that does not count as PG execution.

The PostgreSQL proxy discards the COMMIT response after forwarding the request and
observes COMMIT/idle ReadyForQuery on the server side. A separate connection then
checks durable state. This is a real response-loss counterexample, not a simulated
failure after a client-observed success. Tests are bounded by external CI timeout
and the in-test fault deadline. The fixture asserts provider facts; it does not
claim that the future C# wrapper already maps errors correctly to Unknown.

Record toolchain, OS/arch, server version and container digest (when applicable),
source and lock hashes, command/exit status, complete stdout/stderr and review.
No performance, cross-language/AOT, production TLS/auth, long-load or full ORM
claim follows from these narrow cases.
