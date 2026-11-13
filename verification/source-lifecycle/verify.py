#!/usr/bin/env python3
"""Read-only verification of exact finite lifecycle evidence; not a test rerun."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def git_bytes(ref, path):
    return subprocess.check_output(['git', 'show', ref + ':' + path], cwd=ROOT)


def main():
    manifest = read_json(HERE / 'results.json')
    commit = manifest['tested_source_commit']
    assert len(commit) == 40 and all(c in '0123456789abcdef' for c in commit)
    run_id = str(manifest['run_id'])
    run_dir = HERE / run_id
    run = read_json(run_dir / 'run.json')
    jobs = read_json(run_dir / 'jobs.json')['jobs']
    artifacts = {a['id']: a for a in read_json(run_dir / 'artifacts.json')['artifacts']}
    assert run['head_sha'] == commit and run['conclusion'] == 'success'
    expected_jobs = {
        f'lifecycle ({os_name}, {fixture})'
        for os_name in ['ubuntu-24.04', 'windows-2022']
        for fixture in ['database-retirement', 'server-retained-bytes']
    }
    assert len(jobs) == 4 and {j['name'] for j in jobs} == expected_jobs
    assert all(j['conclusion'] == 'success' for j in jobs)
    assert digest(git_bytes(commit, manifest['workflow_path'])) == manifest['workflow_sha256']
    assert len(manifest['records']) == 4 and len(artifacts) == 4
    all_files = set()
    exact = converted = executed = 0
    for record in manifest['records']:
        artifact = artifacts[record['artifact_id']]
        assert artifact['name'] == record['artifact_name']
        assert artifact['digest'] == 'sha256:' + record['artifact_zip_sha256']
        assert artifact['size_in_bytes'] == record['artifact_bytes']
        assert record['tested_source'] == commit
        directory = run_dir / record['artifact_name']
        listed = set()
        for entry in record['files']:
            path = ROOT / entry['path']
            assert path.is_relative_to(directory)
            assert entry['path'] not in all_files
            all_files.add(entry['path'])
            listed.add(path.relative_to(directory).as_posix())
            raw = path.read_bytes()
            assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], entry['path']
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
        assert actual == listed, record['artifact_name']
        result = read_json(directory / 'result.json')
        assert result.get('git_head', result.get('github_head_sha')) == commit
        assert result['github_run_id'] == run_id
        assert result.get('success', result.get('passed')) is True
        tests = result.get('named_tests_passed', result.get('passed_test_names'))
        assert tests == record['tests_passed'] and len(set(tests)) == 6
        if record['fixture'] == 'server-retained-bytes':
            assert result['worktree_dirty'] is False
            assert result['source_sha256_before'] == result['source_sha256_after'] == record['source_inputs']
            for name, expected in result['logs_sha256'].items():
                assert digest((directory / name).read_bytes()) == expected
            commands = result['commands']
            output = (directory / '2.stdout').read_text(encoding='utf-8')
        else:
            assert result['input_bytes_unchanged'] is True
            inputs = read_json(directory / 'source-inputs.json')
            assert {name: item['sha256'] for name, item in inputs.items()} == record['source_inputs']
            commands = read_json(directory / 'commands.json')
            output = (directory / 'tests.stdout').read_text(encoding='utf-8')
        assert all(command['exit_code'] == 0 for command in commands)
        assert '6 passed; 0 failed' in output
        assert all('test tests::' + test + ' ... ok' in output for test in tests)
        executed += len(tests)
        assert record['source_inputs'].keys() == record['source_input_identities'].keys()
        for name, identity in record['source_input_identities'].items():
            path = 'experiments/' + record['fixture'] + '/' + name
            canonical = git_bytes(commit, path)
            checkout = (directory / 'inputs' / name).read_bytes()
            assert digest(canonical) == identity['git_blob_sha256']
            assert digest(checkout) == identity['checkout_sha256'] == record['source_inputs'][name]
            # A future fixture change needs new evidence, not an old green run.
            assert git_bytes('HEAD', path) == canonical, 'current committed fixture drift: ' + path
            if identity['relationship'] == 'byte_exact':
                assert canonical == checkout
                exact += 1
            else:
                assert identity['relationship'] == 'exact_LF_to_CRLF_checkout_conversion'
                assert record['fixture'] == 'database-retirement'
                assert record['artifact_name'].endswith('-windows-2022')
                assert b'\r\n' not in canonical and canonical.replace(b'\n', b'\r\n') == checkout
                converted += 1
    assert (len(all_files), exact, converted, executed) == (56, 15, 5, 24)
    assert manifest['preserved_raw_files'] == len(all_files)
    assert manifest['platform_test_executions'] == executed
    assert not manifest['formal_contract_accepted'] and not manifest['product_delivery_executed']

    registry = read_json(ROOT / 'docs/contracts/registry.json')['contracts']
    checked_specs = 0
    for contract in registry:
        assert contract['status'] == 'proposed', 'this research checkpoint does not accept contracts'
        if contract.get('spec_path'):
            assert digest((ROOT / contract['spec_path']).read_bytes()) == contract['content_sha256'], contract['id']
            checked_specs += 1
    assert checked_specs == 15
    phase = (ROOT / 'CURRENT-PHASE.md').read_text(encoding='utf-8')
    assert 'not grant product permission' in phase and 'Never merge PR1' in phase
    assert 'Server remains evidence-selected' in phase

    review_dir = ROOT / 'docs/traceability/reviews/migration-2026-11-12'
    reviews = read_json(review_dir / 'archived-files.json')['files']
    for entry in reviews:
        raw = (review_dir / entry['path']).read_bytes()
        assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], entry['path']
    current_review_dir = ROOT / 'docs/traceability/reviews/source-lifecycle'
    server_directory = current_review_dir / 'server'
    server_review = read_json(server_directory / 'manifest.json')
    assert server_review['author_of_reviewed_server_files'] is False
    assert server_review['unresolved_server_scoped_findings'] == []
    assert server_review['contract']['accepted_by_this_review'] is False
    for entry in server_review['reviewed_files']:
        raw = (ROOT / entry['path']).read_bytes()
        assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], entry['path']
    for entry in server_review['raw_evidence'] + server_review['supporting_review_files']:
        raw = (server_directory / entry['path']).read_bytes()
        assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], entry['path']
    database_review = read_json(current_review_dir / 'database/DATABASE-LIFECYCLE-REVIEW.json')
    assert database_review['errors'] == [] and database_review['blocking_findings'] == []
    assert all(check['passed'] for check in database_review['checks'])
    for entry in database_review['files']:
        raw = (ROOT / entry['path']).read_bytes()
        assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], entry['path']
    array_bytes = json.dumps(database_review['files'], sort_keys=True, separators=(',', ':')).encode()
    assert digest(array_bytes) == database_review['files_content_sha256']
    replication_review = read_json(current_review_dir / 'interop-replication-review.json')
    assert replication_review['author_of_reviewed_csharp_and_runner'] is False
    assert replication_review['passed'] and all(check['passed'] for check in replication_review['checks'])
    for entry in replication_review['files']:
        assert digest((ROOT / entry['path']).read_bytes()) == entry['sha256'], entry['path']
    print(json.dumps({'passed': True, 'tested_source_commit': commit,
                      'raw_files': len(all_files), 'byte_exact_inputs': exact,
                      'explicit_lf_to_crlf_inputs': converted, 'platform_test_executions': executed,
                      'specification_hashes': checked_specs, 'archived_review_files': len(reviews),
                      'server_reviewed_files': len(server_review['reviewed_files']),
                      'database_reviewed_files': len(database_review['files']),
                      'replication_reviewed_files': len(replication_review['files']),
                      'accepted_contracts': 0, 'product_delivery_executed': False}, indent=2))


if __name__ == '__main__':
    main()
