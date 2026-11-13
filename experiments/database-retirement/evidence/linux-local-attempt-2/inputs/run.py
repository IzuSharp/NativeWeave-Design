#!/usr/bin/env python3
"""Run the finite research crate and retain successful and failed command evidence."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="new evidence directory; existing results are not overwritten")
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument("--rustc", default="rustc")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "result.json").exists():
        raise SystemExit("choose a new --out directory to preserve previous attempts")
    commands = []

    def run(name, argv, timeout=900):
        started = time.time()
        try:
            process = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=timeout)
            stdout, stderr, code = process.stdout, process.stderr, process.returncode
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or b""
            stderr = error.stderr or b""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            stderr += "\nProcess-level timeout; this is a failed execution, not a retirement proof.\n"
            code = 124
        (out / (name + ".stdout")).write_text(stdout, encoding="utf-8")
        (out / (name + ".stderr")).write_text(stderr, encoding="utf-8")
        commands.append({"name": name, "argv": argv, "exit_code": code,
                         "elapsed_seconds": round(time.time() - started, 3)})
        return code

    source_names = ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "src/lib.rs", "run.py"]
    inputs = {name: {"sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                     "bytes": (root / name).stat().st_size} for name in source_names}
    for name in source_names:
        saved = out / "inputs" / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes((root / name).read_bytes())
    (out / "source-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n", encoding="utf-8")
    versions_ok = run("cargo-version", [args.cargo, "+1.100.0", "-Vv"], 120) == 0
    versions_ok = run("rustc-version", [args.rustc, "+1.100.0", "-Vv"], 120) == 0 and versions_ok
    tree_ok = run("dependency-tree", [args.cargo, "+1.100.0", "tree", "--locked"], 300) == 0
    code = run("tests", [args.cargo, "+1.100.0", "test", "--locked", "--", "--nocapture", "--test-threads=1"])
    unchanged = all(hashlib.sha256((root / name).read_bytes()).hexdigest() == inputs[name]["sha256"]
                    for name in source_names)
    result = {"schema_version": 1, "scope": "finite-native-sqlite-retirement-research",
              "platform": platform.platform(), "machine": platform.machine(),
              "ci": os.environ.get("GITHUB_ACTIONS") == "true",
              "github_run_id": os.environ.get("GITHUB_RUN_ID"),
              "github_head_sha": os.environ.get("GITHUB_SHA"),
              "expected_tests": 6, "tests_exit_code": code,
              "input_bytes_unchanged": unchanged,
              "passed": versions_ok and tree_ok and code == 0 and unchanged,
              "not_proven": ["PostgreSQL", "C# Native AOT", "hard cancellation deadline",
                             "OS worker JoinHandle", "weak-memory correctness", "production acceptance"]}
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
