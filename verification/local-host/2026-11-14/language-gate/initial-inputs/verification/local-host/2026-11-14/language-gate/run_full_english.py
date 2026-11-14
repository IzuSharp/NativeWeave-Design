"""Capture the full candidate English gate with every candidate input indexed."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CHECKOUT = ROOT.parent / 'gate-validation/NativeWeave-Design'
BASE = '9f771b704b120823197884125597bb528a77c4b0'
env = os.environ.copy()
env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
assert not CHECKOUT.exists() and not (OUT / 'full-english.json').exists(), 'Preserve existing attempts; use a fresh isolated layout.'
CHECKOUT.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['git', 'clone', '--shared', '--no-checkout', '-c', 'core.autocrlf=false',
                '-c', 'core.longpaths=true', str(ROOT), str(CHECKOUT)], check=True, env=env, capture_output=True)
subprocess.run(['git', 'checkout', '--detach', BASE], cwd=CHECKOUT, check=True, env=env, capture_output=True)
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=CHECKOUT, env=env).strip()
overlays = ['tools/local_host_raw_evidence.py', 'tools/verify_english_translation.py',
            'verification/local-host/2026-11-14/raw-execution-language-exceptions.json']
overlays += [path.relative_to(ROOT).as_posix() for path in sorted(OUT.glob('*.py'))]
overlays += ['verification/local-host/2026-11-14/language-gate/negative-results.json']
hashes = {}
for relative in overlays:
    target = CHECKOUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / relative, target)
    hashes[relative] = sha(target.read_bytes())
subprocess.run(['git', 'add', '--', *overlays], cwd=CHECKOUT, check=True, env=env, capture_output=True)
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=CHECKOUT, env=env).decode().split('\0')
assert set(overlays) <= set(tracked), 'Candidate files must be indexed for the actual tracked-text check.'
command = [sys.executable, 'tools/verify_english_translation.py']
started = now()
try:
    result = subprocess.run(command, cwd=CHECKOUT, env=env, capture_output=True, timeout=600)
    stdout, stderr, code = result.stdout, result.stderr, result.returncode
except subprocess.TimeoutExpired as error:
    stdout, stderr, code = error.stdout or b'', error.stderr or b'', 124
(OUT / 'full-english.stdout').write_bytes(stdout)
(OUT / 'full-english.stderr').write_bytes(stderr)
report = {'kind': 'actual-full-English-gate-execution', 'baseline_checkout_commit': BASE,
          'candidate_overlay_sha256': hashes, 'all_overlay_files_git_indexed': True,
          'command': command, 'cwd': str(CHECKOUT), 'exit_code': code,
          'started_at_utc': started, 'finished_at_utc': now(),
          'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr),
          'raw_exception_manifest_sha256': hashes[overlays[2]],
          'scope': 'Complete existing English, immutable-source and contract-binding checks plus seven exact raw-stream exceptions. Candidate overlay hashes identify uncommitted validator inputs; not a native rerun or new contract acceptance.'}
(OUT / 'full-english.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(stdout.decode('utf-8', errors='replace'), end='')
print(stderr.decode('utf-8', errors='replace'), end='')
raise SystemExit(code)
