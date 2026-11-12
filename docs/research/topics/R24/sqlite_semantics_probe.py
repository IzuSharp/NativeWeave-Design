#!/usr/bin/env python3
"""Reference SQL experiment only; not NativeWeave, C#, PostgreSQL or AOT validation."""
import datetime as dt
import hashlib
import itertools
import json
import pathlib
import platform
import sqlite3
import sys

started = dt.datetime.now(dt.timezone.utc).isoformat()
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE vals(id INTEGER PRIMARY KEY, x INTEGER, y INTEGER)")
pairs = list(itertools.product([None, 0, 1], repeat=2))
db.executemany("INSERT INTO vals VALUES(?,?,?)", [(i, x, y) for i, (x, y) in enumerate(pairs)])
checks = []

def check(name, observed, expected):
    checks.append({"name": name, "expected": expected, "observed": observed, "passed": observed == expected})

for i, eq, ne, gt, not_gt in db.execute(
    "SELECT id, x IS y, x IS NOT y, COALESCE(x>y,0), NOT COALESCE(x>y,0) FROM vals ORDER BY id"
):
    x, y = pairs[i]
    lifted_gt = x is not None and y is not None and x > y
    check(f"null_safe_equal_{i}", bool(eq), x == y)
    check(f"null_safe_not_equal_{i}", bool(ne), x != y)
    check(f"nullable_greater_{i}", bool(gt), lifted_gt)
    check(f"negated_nullable_greater_{i}", bool(not_gt), not lifted_gt)

ids = lambda sql, params=(): [r[0] for r in db.execute(sql, params)]
check("equality_where", ids("SELECT id FROM vals WHERE x IS y ORDER BY id"), [i for i,p in enumerate(pairs) if p[0] == p[1]])
check("contains_empty", ids("SELECT id FROM vals WHERE 0"), [])
check("contains_null_and_one", ids("SELECT id FROM vals WHERE x IS ? OR x IS ? ORDER BY id", (None,1)), [i for i,p in enumerate(pairs) if p[0] in [None,1]])
check("not_contains_null_and_one", ids("SELECT id FROM vals WHERE NOT(x IS ? OR x IS ?) ORDER BY id", (None,1)), [i for i,p in enumerate(pairs) if p[0] not in [None,1]])
raw_not = ids("SELECT id FROM vals WHERE NOT(x>y) ORDER BY id")
normalized_not = ids("SELECT id FROM vals WHERE NOT COALESCE(x>y,0) ORDER BY id")
check("negative_control_raw_not_differs", raw_not != normalized_not, True)

db.executescript("CREATE TABLE l(id INTEGER); CREATE TABLE r(lid INTEGER,active INTEGER); INSERT INTO l VALUES(1),(2); INSERT INTO r VALUES(1,0);")
check("outer_join_on_retains_rows", len(list(db.execute("SELECT l.id FROM l LEFT JOIN r ON r.lid=l.id AND r.active=1"))), 2)
check("outer_join_where_changes_rows", len(list(db.execute("SELECT l.id FROM l LEFT JOIN r ON r.lid=l.id WHERE r.active=1"))), 0)
check("empty_aggregate", list(db.execute("SELECT COUNT(*),SUM(x),COALESCE(SUM(x),0) FROM vals WHERE 0"))[0], (0,None,0))

db.execute("CREATE TABLE texts(value TEXT)")
payload = "x'); DROP TABLE vals; --"
db.execute("INSERT INTO texts VALUES(?)", (payload,))
check("bound_value_roundtrip", db.execute("SELECT value FROM texts").fetchone()[0], payload)
check("bound_value_does_not_drop_table", db.execute("SELECT COUNT(*) FROM vals").fetchone()[0], 9)

db.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, created INTEGER NOT NULL)")
db.executemany("INSERT INTO pages VALUES(?,?)", [(1,10),(2,10),(3,10),(4,11),(5,11)])
first = list(db.execute("SELECT id,created FROM pages ORDER BY created DESC,id DESC LIMIT 2"))
last_id,last_created = first[-1]
second = list(db.execute("SELECT id,created FROM pages WHERE created<? OR(created=? AND id<?) ORDER BY created DESC,id DESC LIMIT 3", (last_created,last_created,last_id)))
check("keyset_no_duplicates_or_omissions", [r[0] for r in first+second], [5,4,3,2,1])
check("decimal_text_order_counterexample", db.execute("SELECT '10.00'<'2.00'").fetchone()[0], 1)
check("scaled_integer_order", db.execute("SELECT 1000<200").fetchone()[0], 0)
check("sqlite_integer_overflow_changes_storage_class", db.execute("SELECT typeof(9223372036854775807+1)").fetchone()[0], "real")

db.close()
result = {
    "experiment_id": "R24-SQLITE-SEMANTICS-001",
    "kind": "sqlite_reference_execution",
    "started_at": started,
    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "script_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "os": platform.system(), "arch": platform.machine()},
    "cases": checks,
    "checks_total": len(checks),
    "checks_failed": sum(not x["passed"] for x in checks),
    "negative_control": {"raw_not_ids": raw_not, "normalized_not_ids": normalized_not},
    "limitations": ["Python sqlite3 invokes the local SQLite library; no NativeWeave implementation exists here.", "No C# or Rust compilation; no PostgreSQL server; no Windows or Native AOT execution.", "Finite integer/null dataset; no proof for all data types, collations, optimizer rewrites or concurrent workloads."],
}
destination = pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).with_name("sqlite-semantics-result.json")
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"checks":result["checks_total"],"failed":result["checks_failed"],"sqlite":sqlite3.sqlite_version,"output":str(destination)}))
raise SystemExit(1 if result["checks_failed"] else 0)
