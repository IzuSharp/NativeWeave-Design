# R27/R29: retained byte credit and channel retirement

Research fixture only. This adds six finite tests over Bytes 1.12.1, Tokio 1.54.1
and Hyper 1.12.0's Body interface. It preserves the earlier four server probes.

The tests distinguish response/body completion, channel reservations and the
last byte owner. In particular, a non-empty retained slice keeps the whole original allocation;
receiver close permits already-reserved sends; and cancelling a byte waiter
must restore its message reservation without allocating payload first.

Run with Rust 1.100.0:

```sh
cargo +1.100.0 test --locked --manifest-path experiments/server-retained-bytes/Cargo.toml
```

The fixture does not implement an FFI bridge or a full budget coordinator. It
does not measure RSS, fairness, socket/TLS buffers, HTTP/2 resets or Native AOT.
An actual native adapter must also bound waiter metadata and request slots,
coordinate per-request/global credits, close logical admission before drain,
and preserve foreign callback/module owners until their separate retirement.
The managed retained owner is simulated by a live Bytes value; no C# callback
execution is claimed by these Rust tests. See the D18 follow-up for the public
protocol obligations and exact inspected upstream source identities.
