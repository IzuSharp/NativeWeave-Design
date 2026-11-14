#!/usr/bin/env python3
"""Author-side declaration and ABI syntax checks only; never executes a database."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

EVIDENCE = Path(__file__).resolve().parent
dotnet = Path(sys.argv[1]).resolve()
results = []


def run(name, args, cwd, expected=0, diagnostic=None):
    log = EVIDENCE / (name + ".log")
    if log.exists():
        raise RuntimeError("Preserve previous logs; create a new evidence attempt.")
    result = subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                                 "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1"})
    log.write_text(result.stdout)
    accepted = result.returncode == expected and (
        diagnostic is None or re.search(r"\b" + re.escape(diagnostic) + r"\b", result.stdout))
    results.append({"name": name, "command": [str(x) for x in args], "cwd": str(cwd),
                    "exit_code": result.returncode, "expected_exit_code": expected,
                    "expected_diagnostic": diagnostic, "passed": bool(accepted),
                    "log": log.name, "sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
    print(name + ": " + ("passed" if accepted else "FAILED"), flush=True)
    if not accepted:
        raise RuntimeError(result.stdout)


with tempfile.TemporaryDirectory(prefix="nativeweave-db-final-fixes-") as scratch:
    workspace = Path(scratch)
    shutil.copytree(EVIDENCE / "inputs", workspace / "inputs")
    for name in ["check.csproj", "NuGet.Offline.Config", "ReferenceLiftConsumer.cs.txt", "database-abi.c"]:
        shutil.copy2(EVIDENCE / name, workspace / name)
    run("sdk", [dotnet, "--version"], workspace)
    run("restore", [dotnet, "restore", "check.csproj", "--configfile", "NuGet.Offline.Config", "--nologo"], workspace)
    run("positive-consumers", [dotnet, "build", "check.csproj", "--no-restore", "--nologo", "-p:UseSharedCompilation=false"], workspace)
    for name, diagnostic in [
        ("DatabaseNullableJoin", "CS0029"),
        ("DatabaseNullableLiftReverse", "CS0029"),
        ("DatabaseNullableLiftRepeat", "CS0453"),
    ]:
        run(name, [dotnet, "build", "check.csproj", "--no-restore", "--nologo",
                   "-p:UseSharedCompilation=false", "-p:NegativeFile=inputs/" + name + ".cs.txt"],
            workspace, expected=1, diagnostic=diagnostic)
    run("c-abi-syntax", ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "database-abi.c"], workspace)
    for name in ["database-coverage.json", "database-symbol-policies.json"]:
        json.loads((workspace / "inputs" / name).read_text())
    results.append({"name": "coverage-and-policies-json", "passed": True})

summary = {
    "schema_version": "1.0.0",
    "author": "/root/recover_database",
    "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Targeted design-signature consumer compilation and normative C declaration syntax only",
    "passed": all(x["passed"] for x in results),
    "cases": results,
    "positive_consumer_coverage": ["Optional long? FK LEFT JOIN with long AsNullable", "Independent post-Build Relation.CreateOptional and LoadRelatedAsync", "Reference AsNullableReference comparison"],
    "claims": {"product_database_executed": False, "native_relation_implementation_tested": False,
               "sql_semantics_executed": False, "aot_published": False,
               "independent_review": False, "old_native_probes_reexecuted": False},
}
(EVIDENCE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print("All targeted author checks passed; independent review and product behavior remain separate.")
