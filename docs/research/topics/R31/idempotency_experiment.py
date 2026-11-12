"""Research-only SQLite transaction experiment; not NativeWeave product code.

Run: python idempotency_experiment.py
No retained database and no external service. JSON on stdout is the raw result.
The simulated lost response happens AFTER a real SQLite COMMIT. The crash case
uses a real child-process exit before COMMIT; it is not a network fault test.
"""
from __future__ import annotations

import concurrent.futures
from contextlib import closing
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def setup(path: str) -> None:
    with closing(connect(path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
CREATE TABLE operations (
  scope TEXT NOT NULL, request_key TEXT NOT NULL, request_hash TEXT NOT NULL,
  operation_id TEXT NOT NULL UNIQUE, response TEXT NOT NULL,
  PRIMARY KEY(scope, request_key));
CREATE TABLE items (
  operation_id TEXT NOT NULL PRIMARY KEY REFERENCES operations(operation_id),
  title TEXT NOT NULL);
CREATE TABLE outbox (
  event_id TEXT NOT NULL PRIMARY KEY, operation_id TEXT NOT NULL
  REFERENCES operations(operation_id), payload TEXT NOT NULL);
""")


def command(path: str, key: str, title: str, crash: bool = False,
            lose_response: bool = False) -> dict[str, str]:
    request_hash = hashlib.sha256(
        json.dumps({"schema": 1, "title": title}, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()
    db = connect(path)
    try:
        # SQLite provider-specific writer admission, not PostgreSQL's SQL recipe.
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT request_hash, operation_id, response FROM operations "
                              "WHERE scope=? AND request_key=?", ("tenant:user:create-v1", key)).fetchone()
        if previous:
            db.execute("ROLLBACK")
            if previous[0] != request_hash:
                return {"kind": "conflict", "operation_id": previous[1]}
            return {"kind": "replay", "operation_id": previous[1], "response": previous[2]}
        operation_id = str(uuid.uuid4())
        response = json.dumps({"operation_id": operation_id, "title": title}, sort_keys=True)
        db.execute("INSERT INTO operations VALUES (?, ?, ?, ?, ?)",
                   ("tenant:user:create-v1", key, request_hash, operation_id, response))
        db.execute("INSERT INTO items VALUES (?, ?)", (operation_id, title))
        db.execute("INSERT INTO outbox VALUES (?, ?, ?)",
                   (operation_id + ":created", operation_id, response))
        if crash:
            # Abrupt process termination: intentionally skip finally/rollback.
            os._exit(17)
        db.execute("COMMIT")
        if lose_response:
            return {"kind": "simulated_response_lost"}
        return {"kind": "created", "operation_id": operation_id, "response": response}
    finally:
        db.close()


def counts(path: str) -> dict[str, int]:
    with closing(connect(path)) as db:
        return {name: db.execute("SELECT count(*) FROM " + name).fetchone()[0]
                for name in ("operations", "items", "outbox")}


def main() -> None:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="nativeweave-r31-") as temporary:
        path = str(Path(temporary) / "research.sqlite")
        setup(path)
        checks: list[dict] = []
        created = command(path, "first", "alpha")
        replay = command(path, "first", "alpha")
        assert created["operation_id"] == replay["operation_id"]
        assert created["response"] == replay["response"] and replay["kind"] == "replay"
        assert counts(path) == {"operations": 1, "items": 1, "outbox": 1}
        checks.append({"name": "same_key_same_hash_replays_original", "passed": True})
        conflict = command(path, "first", "changed")
        assert conflict["kind"] == "conflict"
        assert counts(path) == {"operations": 1, "items": 1, "outbox": 1}
        checks.append({"name": "same_key_changed_hash_no_new_effect", "passed": True})
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            concurrent_results = list(executor.map(
                lambda _: command(path, "concurrent", "one effect"), range(4)))
        assert sum(result["kind"] == "created" for result in concurrent_results) == 1
        assert len({result["operation_id"] for result in concurrent_results}) == 1
        assert counts(path) == {"operations": 2, "items": 2, "outbox": 2}
        checks.append({"name": "four_connections_same_key_one_transaction_effect", "passed": True})
        lost = command(path, "lost", "durable", lose_response=True)
        assert lost["kind"] == "simulated_response_lost"
        recovered = command(path, "lost", "durable")
        assert recovered["kind"] == "replay"
        assert counts(path) == {"operations": 3, "items": 3, "outbox": 3}
        checks.append({"name": "actual_commit_then_simulated_lost_response_recovery", "passed": True})
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                "--crash-child", path], capture_output=True, text=True)
        assert child.returncode == 17
        assert counts(path) == {"operations": 3, "items": 3, "outbox": 3}
        recovered_crash = command(path, "crash", "uncommitted")
        assert recovered_crash["kind"] == "created"
        assert counts(path) == {"operations": 4, "items": 4, "outbox": 4}
        checks.append({"name": "child_process_exit_before_commit_atomic_rollback_then_retry",
                       "passed": True, "child_exit_code": child.returncode})
        print(json.dumps({
            "experiment": "R31 SQLite idempotency and transaction boundary prototype",
            "status": "passed", "checks": checks,
            "python": sys.version, "sqlite": sqlite3.sqlite_version,
            "os": platform.platform(), "architecture": platform.machine(),
            "journal_mode": "WAL", "synchronous": "FULL",
            "final_counts": counts(path), "duration_seconds": time.monotonic() - started,
            "limitations": ["Not NativeWeave product implementation", "No C# or Rust execution",
                            "No Native AOT proof", "No PostgreSQL concurrency execution",
                            "Response loss simulated after actual COMMIT, not a network proxy fault",
                            "Process exit is not OS power-loss/fsync hardware verification"]
        }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--crash-child":
        command(sys.argv[2], "crash", "uncommitted", crash=True)
        raise AssertionError("crash child unexpectedly returned")
    main()
