"""Execute focused negatives against the actual supplemental raw-language gate."""
from copy import deepcopy
from pathlib import Path
import datetime
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from local_host_raw_evidence import MANIFEST, check_tracked_language, verified_raw_exceptions

sha = lambda raw: hashlib.sha256(raw).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
original = json.loads((ROOT / MANIFEST).read_bytes())
records = []
started = now()


def write_manifest(root, data):
    (root / MANIFEST).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def change_run(root, data, mutate):
    row = data['entries'][0]
    path = root / row['run']['path']
    run = json.loads(path.read_bytes())
    mutate(run, row)
    path.write_text(json.dumps(run, indent=2) + '\n', encoding='utf-8')
    row['run']['sha256'] = sha(path.read_bytes())


def historical_backfill(root, data):
    # This later existing commit contains the raw file. Keep every other
    # source/host/command/hash condition valid to exercise membership itself.
    source = '9f771b704b120823197884125597bb528a77c4b0'
    data['source_commit'] = source
    data['entries'] = data['entries'][:1]
    change_run(root, data, lambda run, row: run.update(source_commit=source))


def case(name, mutate=None, language_file=None, reject=True):
    with tempfile.TemporaryDirectory(prefix='nw-raw-language-') as temporary:
        root = Path(temporary) / 'NativeWeave-Design'
        clone = subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(ROOT), str(root)], capture_output=True)
        assert clone.returncode == 0, clone.stderr.decode(errors='replace')
        data = deepcopy(original)
        paths = {str(MANIFEST)}
        for row in data['entries']:
            paths.update([row['path'], row['run']['path']])
        for relative in paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        allowed = verified_raw_exceptions(root)
        assert len(allowed) == 7
        check_tracked_language(root, sorted(allowed), allowed)
        if mutate:
            mutate(root, data)
        write_manifest(root, data)
        caught = None
        try:
            allowed = verified_raw_exceptions(root)
            if language_file:
                relative, text = language_file
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
                # This is the same final classifier called by the full English gate.
                check_tracked_language(root, [relative], allowed)
            else:
                check_tracked_language(root, sorted(allowed), allowed)
        except (AssertionError, subprocess.CalledProcessError) as error:
            caught = {'type': type(error).__name__, 'reason': str(error)}
        passed = (caught is not None) == reject
        records.append({'case': name, 'passed': passed, 'expected_rejection': reject,
                        'valid_seven_entry_baseline_checked': True, 'rejection': caught})
        assert passed, (name, caught)


case('seven_exact_registered_streams_pass', reject=False)
case('unregistered_english_prose_passes', language_file=('docs/new-note.md', 'New English evidence note.\n'), reject=False)
case('raw_byte_tamper_rejected', lambda root, data: (root / data['entries'][0]['path']).write_bytes(b'tampered'))
case('raw_length_drift_rejected', lambda root, data: data['entries'][0].update(bytes=1))
case('raw_digest_drift_rejected', lambda root, data: data['entries'][0].update(sha256='0' * 64))
case('runner_byte_tamper_rejected', lambda root, data: (root / data['entries'][0]['run']['path']).write_bytes(b'{}'))
case('runner_source_mismatch_rejected', lambda root, data: change_run(root, data, lambda run, row: run.update(source_commit='f' * 40)))
case('runner_host_mismatch_rejected', lambda root, data: change_run(root, data, lambda run, row: run.update(platform='Linux')))
case('unbound_command_stream_rejected', lambda root, data: change_run(root, data,
     lambda run, row: next(command for command in run['commands'] if command['name'] == row['run']['command_name']).update(stdout_sha256='0' * 64)))
case('duplicate_runner_command_rejected', lambda root, data: change_run(root, data,
     lambda run, row: run['commands'].append(deepcopy(next(command for command in run['commands'] if command['name'] == row['run']['command_name'])))))
case('command_filename_mismatch_rejected', lambda root, data: data['entries'][0]['run'].update(command_name='pack'))
case('path_traversal_rejected', lambda root, data: data['entries'][0].update(path='verification/local-host/2026-11-14/windows/../a.stdout'))
case('absolute_path_rejected', lambda root, data: data['entries'][0].update(path='/verification/local-host/2026-11-14/windows/run/a.stdout'))
case('old_historical_path_rejected', lambda root, data: data['entries'][0].update(path='verification/interop-completion/linux/normal-run.stdout'))
case('current_raw_backfill_into_source_tree_rejected', historical_backfill)
assert records[-1]['rejection']['reason'] == 'historical or duplicate raw exception'
case('markdown_exception_rejected', lambda root, data: data['entries'][0].update(path='verification/local-host/2026-11-14/windows/engine-attempt-1/note.md'))
case('source_exception_rejected', lambda root, data: data['entries'][0].update(path='verification/local-host/2026-11-14/windows/engine-attempt-1/Program.cs'))
case('duplicate_exception_rejected', lambda root, data: data['entries'].append(deepcopy(data['entries'][0])))
case('unknown_commit_rejected', lambda root, data: data.update(source_commit='f' * 40))
case('short_commit_rejected', lambda root, data: data.update(source_commit='4c5c385'))
case('non_raw_authority_rejected', lambda root, data: data.update(scope='authoritative_prose'))
case('unregistered_cjk_prose_rejected', language_file=('docs/unregistered.md', '\u4e2d\u6587\n'))
case('unregistered_cjk_raw_rejected', language_file=('verification/local-host/2026-11-14/windows/engine-attempt-1/unlisted.stdout', '\u4e2d\u6587\n'))

report = {
    'kind': 'actual-raw-language-gate-regression-execution',
    'scope': 'Synthetic mutations of isolated copies; not native execution or product acceptance.',
    'command': [sys.executable, str(Path(__file__).resolve())],
    'started_at_utc': started, 'finished_at_utc': now(),
    'platform': platform.system(), 'python': platform.python_version(),
    'research_source_commit': original['source_commit'],
    'checker_baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'checker_source_commit': None,
    'checker_identity': 'Exact uncommitted validator bytes are identified by source_sha256, not by the research source commit.',
    'source_sha256': {path: sha((ROOT / path).read_bytes()) for path in [
        'tools/local_host_raw_evidence.py', 'tools/verify_english_translation.py',
        MANIFEST.as_posix(), Path(__file__).resolve().relative_to(ROOT).as_posix()]},
    'case_count': len(records), 'all_passed': all(row['passed'] for row in records),
    'records': records,
}
(Path(__file__).resolve().parent / 'negative-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'case_count': len(records), 'all_passed': report['all_passed']}))
