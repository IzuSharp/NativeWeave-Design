"""Capture one real research run without logging connection credentials."""
import argparse
import datetime
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--suite", choices=["metadata", "postgres"], required=True)
parser.add_argument("--out", type=pathlib.Path, required=True)
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parent
repo = root.parents[1]
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
if (out / "manifest.json").exists():
    raise SystemExit("Refusing to overwrite an existing run manifest")
command = ["cargo", "test", "--locked", "--test",
           "runtime_metadata" if args.suite == "metadata" else "postgres", "--"]
if args.suite == "postgres":
    command += ["--ignored", "--nocapture", "--test-threads=1"]
else:
    command += ["--nocapture"]

def capture(cmd):
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)

inputs = [root / "Cargo.toml", root / "Cargo.lock", root / "run.py",
          *sorted((root / "tests").glob("*.rs")),
          root.parent / "native-slices/database/Cargo.toml",
          root.parent / "native-slices/database/src/lib.rs"]
identities = {}
for path in inputs:
    relative = path.relative_to(repo)
    identities[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    target = out / "inputs" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
    result = subprocess.run(command, cwd=root, capture_output=True, timeout=420)
    stdout, stderr, code = result.stdout, result.stderr, result.returncode
except subprocess.TimeoutExpired as error:
    stdout, stderr, code = error.stdout or b"", error.stderr or b"", 124
(out / "stdout.log").write_bytes(stdout)
(out / "stderr.log").write_bytes(stderr)
manifest = {
    "kind": "actual-research-execution", "suite": args.suite,
    "command": command, "cwd": "experiments/database-completion",
    "exit_code": code, "started_at_utc": start,
    "finished_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "environment": {"os": platform.system(), "arch": platform.machine(),
                    "kernel": platform.release(), "python": platform.python_version(),
                    "rustc": capture(["rustc", "-vV"]).stdout,
                    "cargo": capture(["cargo", "--version"]).stdout},
    "repository_head": capture(["git", "rev-parse", "HEAD"]).stdout.strip(),
    "source_sha256": identities,
    "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
    "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
    "limits": ["finite research fixture, not product implementation",
               "no C# or Native AOT execution in this fixture",
               "PostgreSQL TLS disabled only for explicit local fault-proxy testing",
               "source hashes identify actual inputs even if repository worktree is dirty"],
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(stdout.decode(errors="replace"), end="")
print(stderr.decode(errors="replace"), end="", file=sys.stderr)
raise SystemExit(code)
