# R22/R25 — actual fallible native binder and SQLite semantics

Status: partially evidenced; author-side implementation/tests, not independent review or production ORM. Uses the original pinned SeaQuery1.0.2/SQLx0.9.0/Tokio1.54.1 routes, no C# SQL implementation. NativeWeave PR1 contains the executable fixture at `experiments/database/`.

## Executed chain and correction

Initial source5dd696725afe75f2b8b03b104c8275db50dcf2c7 (locked closure) in run43363994414 failed to compile on both OS: one `InsertStatement::values` element was Value, but this pinned API requires Expr. Fix **43e4fbcbe0417165c0f7df03507bfa1da8a53049** adds the explicit `.into()` conversion. [Run43364366610](https://github.com/IzuSharp/NativeWeave/actions/runs/43364366610) then passed all **six tests on Windows and Linux**. Failed compiler logs remain preserved, not presented as successful tests. The unchanged Server fixture was not rerun by the Database fix.

The executed chain is runtime table/column metadata → native SeaQuery statement/Expr/Value → backend SQL plus ordered Values → checked Rust argument conversion → SQLx execution → typed SQLx row decode. The fixture uses the real libraries and SQLite, not a Python SQL approximation or C# reimplementation. Registry package checksums and Cargo.lock identify the actual execution closure; previously inspected Git commits are separate evidence identities.

## Actual tests and implications

1. Bound parameter count/payload and unsupported variant checks; u64 overflow is a typed failure, NULL and supported scalars survive. Limits are a finite fixture policy (64 arguments,4096 payload bytes), not tuned production limits.
2. A custom encoder deliberately writes a value and then returns an error. The adapter propagates the error; SQLx removes the partially encoded argument. A previous valid argument remains. This is a real fail-after-partial-write negative, not merely checking a synthetic return code.
3. Native SeaQuery rendering omits FOR UPDATE for SQLite and emits it for PostgreSQL. The fixture's SQLite wrapper rejects requested row-lock semantics at entry. This is a real negative control proving successful rendering alone is insufficient; it is not an all-operator validator.
4. An overflowing value is rejected before the instrumented database-send counter increments; table row count remains0. The test does not send invalid SQL and then claim it was prevalidated.
5. Two runtime tables, including a quoted identifier, use native create/insert/select/update/delete. Hostile-looking text is bound separately, wrong-type `try_get` fails, NULL update/deletion and expected affected-row counts are checked.
6. Actual SQLite transaction rollback leaves row count0, and an absent-column query returns an error.

## Adapter decision and non-goals

Keep upstream native query/dialect/driver code. A small fallible native codec is justified where a convenience binder discards encode errors or unwraps narrowing. Do not propagate this into a full Core type system or C# query engine. `AssertSqlSafe` is a narrowly applied provenance assertion for validated native output, not a sanitizer. Metadata quoting is not tenant authorization.

The preflight function bounds its conversion inputs **after caller-created Value/AST allocations**; it is not a whole-native-memory bound. No C# domain FFI, source generator, PostgreSQL server execution, Unknown COMMIT fault injection, async stream shutdown, native allocator failure, full relation ORM or performance is demonstrated. Those remain in B02/B05/B06/B09–B14/B22/B23. Existing earlier C# SQLite AOT second-entity evidence is complementary, not silently rerun or expanded into this test's scope.

Evidence is persisted in NativeWeave `verification/native-slices/database-*` and the two `database-first-failure-*` directories; use the exact commit in Plan's checkpoint. Rust1.100 compiles this locked feature subset, not every feature of all ecosystem crates. R22/R25 and D14/D16 should retain explicit type/capability/ownership checks and no per-entity Cargo; no production task is marked accepted from six finite tests.
