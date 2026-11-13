# Independent Tonic request-cardinality review

This is a finite research regression written by the Database reviewer while
independently reviewing Server D19. It is not a NativeWeave product module.

Run with Rust 1.100.0 and the checked-in lockfile:

```sh
cargo test --locked --manifest-path experiments/database-completion/server-review/Cargo.toml -- --nocapture
```

The minimal adapter uses Tonic 0.14.9 public `Codec`/`Decoder` and `Grpc` APIs.
Its five executed tests preserve a negative control: an unrestricted byte decoder
lets the unary path accept the first message and silently drain the second. A
fresh decoder that admits one message per unary/server-streaming request rejects
the second message with `INVALID_ARGUMENT` before the Handler runs. Binary and
one empty framed message remain valid; zero messages retain Tonic's missing-message
`INTERNAL` error.

Actual Linux commands, source identities, stdout/stderr and exits are retained in
`verification/database-completion/server-review-cardinality/`. This is not a
network, TLS, C# callback, Windows or production conformance test. The Server
author separately added mode-reset and client-streaming controls to the maintained
protocol research fixture after the independent finding.
