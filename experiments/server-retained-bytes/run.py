"""Execute only the new R27/R29 probes and preserve exact commands and inputs."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = ['Cargo.toml', 'Cargo.lock', 'src/lib.rs', 'run.py', '.gitattributes']
TESTS = {
    'body_end_does_not_retire_an_externally_retained_frame',
    'byte_credit_survives_last_retained_slice',
    'cancelled_byte_wait_restores_message_capacity_before_allocating',
    'oversized_chunk_is_rejected_before_reservations_or_allocation',
    'channel_close_does_not_revoke_an_already_reserved_send',
    'receiver_drop_releases_queued_but_not_external_bytes',
}


def hashes():
    return {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in INPUTS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = hashes()
    for name in INPUTS:
        saved = out / 'inputs' / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / name, saved)
    env = os.environ.copy()
    env['CARGO_TARGET_DIR'] = str(out / 'build')
    manifest = {
        'scope': 'finite Rust research; no FFI, C# handler, transport, RSS or production acceptance',
        'repository': 'IzuSharp/NativeWeave-Design',
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'worktree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        'github_run_id': os.environ.get('GITHUB_RUN_ID'),
        'github_run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'platform': platform.platform(),
        'source_sha256_before': before,
        'commands': [],
        'success': False,
    }
    try:
        commands = [
            ['rustc', '+1.100.0', '--version', '--verbose'],
            ['cargo', '+1.100.0', '--version'],
            ['cargo', '+1.100.0', 'test', '--locked', '--manifest-path', str(HERE / 'Cargo.toml'), '--', '--nocapture'],
        ]
        test_output = ''
        for index, command in enumerate(commands):
            started = datetime.datetime.now(datetime.timezone.utc).isoformat()
            timed_out = False
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
                output, errors, code = result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired as error:
                timed_out = True
                output, errors = error.stdout or b'', error.stderr or b''
                if isinstance(output, bytes):
                    output = output.decode('utf-8', errors='replace')
                if isinstance(errors, bytes):
                    errors = errors.decode('utf-8', errors='replace')
                errors += '\nProcess timeout; no successful retirement or test result is inferred.\n'
                code = 124
            except OSError as error:
                output, errors, code = '', str(error) + '\n', 127
            stdout, stderr = f'{index}.stdout', f'{index}.stderr'
            (out / stdout).write_text(output, encoding='utf-8', newline='\n')
            (out / stderr).write_text(errors, encoding='utf-8', newline='\n')
            manifest['commands'].append({
                'command': command, 'started_utc': started,
                'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'exit_code': code, 'timed_out': timed_out, 'stdout': stdout, 'stderr': stderr,
            })
            if code:
                raise RuntimeError(f'command {index} exited {code}')
            test_output = output
        passed = set(re.findall(r'^test tests::([a-z_]+) \.\.\. ok$', test_output, re.MULTILINE))
        assert passed == TESTS, sorted(passed)
        assert '6 passed; 0 failed' in test_output
        manifest['named_tests_passed'] = sorted(passed)
        manifest['source_sha256_after'] = hashes()
        assert before == manifest['source_sha256_after'], 'input bytes changed during execution'
        manifest['success'] = True
    except Exception as error:
        manifest['error'] = f'{type(error).__name__}: {error}'
    finally:
        manifest['logs_sha256'] = {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(out.iterdir()) if f.is_file()
        }
        (out / 'result.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(manifest, indent=2))
    return 0 if manifest['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
