"""Read-only independent audit of the already merged PR1 research migration."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[1]
DESIGN = WORK / 'NativeWeave-Design'
SOURCE = WORK / 'NativeWeave'
SOURCE_HEAD = '267364a440074a61e193cf33315f1b9d0fa8126b'
DESIGN_HEAD = 'c7e123a74405a92dc3de1ef450355b08d1c05ceb'


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


mapping = read_json(DESIGN / 'verification/native-slices/migration-map.json')
old = read_json(DESIGN / 'verification/native-slices/original-pr1/manifest.json')
new = read_json(DESIGN / 'verification/native-slices/migration-results.json')
errors = []
checks = []
adaptations = []


def check(condition, message):
    checks.append({'check': message, 'passed': bool(condition)})
    if not condition:
        errors.append(message)


check(git(SOURCE, 'rev-parse', 'HEAD').decode().strip() == SOURCE_HEAD, 'source checkout exact HEAD')
check(git(DESIGN, 'rev-parse', 'HEAD').decode().strip() == DESIGN_HEAD, 'design checkout exact HEAD')
expected = set(git(SOURCE, 'diff', '--name-only', mapping['source_base'], SOURCE_HEAD).decode().splitlines())
check(len(expected) == 139, 'PR source git diff contains 139 files')
check({r['source_path'] for r in mapping['records']} == expected, 'complete source path inventory matches migration map')
check(len(mapping['records']) == len({r['source_path'] for r in mapping['records']}) == len({r['destination_path'] for r in mapping['records']}) == 139, '139 unique source and destination mappings')

destinations = {}
for row in mapping['records']:
    src = git(SOURCE, 'show', SOURCE_HEAD + ':' + row['source_path'])
    dst = (DESIGN / row['destination_path']).read_bytes()
    pinned = git(DESIGN, 'show', DESIGN_HEAD + ':' + row['destination_path'])
    check(dst == pinned, 'destination equals pinned Design blob: ' + row['destination_path'])
    check(sha256(src) == row['source_sha256'] and blob(src) == row['source_blob_sha1'], 'source hashes: ' + row['source_path'])
    check(sha256(dst) == row['destination_sha256'] and blob(dst) == row['destination_blob_sha1'], 'destination hashes: ' + row['destination_path'])
    check((src == dst) == row['byte_exact'], 'byte identity declaration: ' + row['source_path'])
    destinations[row['source_path']] = row['destination_path']
    if not row['byte_exact']:
        adaptations.append({'source': row['source_path'], 'destination': row['destination_path'], 'diff': ''.join(difflib.unified_diff(src.decode().splitlines(True), dst.decode().splitlines(True), fromfile=row['source_path'], tofile=row['destination_path']))})

original_files = 0
new_files = 0
artifact_details = []
for label, records in [('original', old['records']), ('migrated', new['records'])]:
    for record in records:
        aid = record['artifact_id']
        archive_path = ROOT / 'archives' / (str(aid) + '.zip')
        archive_bytes = archive_path.read_bytes()
        expected_zip_hash = record.get('zip_sha256', record.get('artifact_zip_sha256'))
        check(sha256(archive_bytes) == expected_zip_hash, f'{label} archive SHA256: {aid}')
        archive = zipfile.ZipFile(archive_path)
        names = [i.filename for i in archive.infolist() if not i.is_dir()]
        for file in record['files']:
            destination = destinations[file['path']] if label == 'original' else file['path']
            raw = (DESIGN / destination).read_bytes()
            check(sha256(raw) == file['sha256'], 'preserved evidence SHA256: ' + destination)
            if label == 'original':
                relative = file['path'].split('/' + record['label'] + '/', 1)[1]
            else:
                relative = file['path'].split('/' + record['artifact'] + '/', 1)[1].split('/', 1)[1]
            matches = [name for name in names if name == relative or name.endswith('/' + relative)]
            check(len(matches) == 1, 'one artifact member for: ' + destination)
            if len(matches) == 1:
                check(archive.read(matches[0]) == raw, 'artifact bytes equal preserved file: ' + destination)
            if label == 'original':
                original_files += 1
            else:
                new_files += 1
        result_names = [name for name in names if name.endswith('/result.json')]
        check(len(result_names) == 1, f'one result in artifact: {aid}')
        result = json.loads(archive.read(result_names[0]))
        expected_source = record.get('source_commit', record.get('tested_design_commit'))
        check(result['source_commit'] == expected_source, f'executed source identity: {aid}')
        check(result['success'] == record['success'], f'actual success/failure identity: {aid}')
        binary_checks = {}
        for field, predicate in [
            ('package_sha256', lambda n: n.endswith('.nupkg')),
            ('native_sha256', lambda n: n.endswith('/publish/libnw_interop_probe.so') or n.endswith('/publish/nw_interop_probe.dll')),
            ('aot_executable_sha256', lambda n: n.endswith('/publish/Consumer') or n.endswith('/publish/Consumer.exe')),
        ]:
            if field in result:
                candidates = [name for name in names if predicate(name)]
                ok = len(candidates) == 1 and sha256(archive.read(candidates[0])) == result[field]
                check(ok, f'{field} independently verified: {aid}')
                binary_checks[field] = ok
        artifact_details.append({'origin': label, 'artifact_id': aid, 'sha256': sha256(archive_bytes), 'source_commit': result['source_commit'], 'run_id': result['run_id'], 'success': result['success'], 'text_files_checked': len(record['files']), 'binary_hash_checks': binary_checks})

check(original_files == 112, '112 original raw evidence files')
check(new_files == 90, '90 distinct migrated execution files')
check(sum(not r['success'] for r in old['records']) == 2, 'both historical database failure records retained')
check(new['tested_design_commit'] == '67b48674e469c98f2f73f1c9ff0d63b113abc47b', 'new execution is identified by actual relocated checkout')
check(new['migration_map_sha256'] == sha256((DESIGN / 'verification/native-slices/migration-map.json').read_bytes()), 'new results bind exact migration map hash')
summary = {
    'audited_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'audit_scope': 'Independent read-only review by migration_evidence subagent; no experiment rerun or product mutation',
    'source_head': SOURCE_HEAD, 'design_head': DESIGN_HEAD,
    'mapped_files': len(mapping['records']), 'byte_exact_files': sum(r['byte_exact'] for r in mapping['records']),
    'adapted_files': adaptations, 'original_evidence_files': original_files, 'migrated_evidence_files': new_files,
    'artifact_archives_downloaded_and_hashed': len(artifact_details), 'artifacts': artifact_details,
    'passed_checks': sum(c['passed'] for c in checks), 'total_checks': len(checks), 'errors': errors,
    'conclusion': 'pass' if not errors else 'fail',
    'closure_scope': 'Migration asset completeness and execution provenance only; paired Plan merge and product PR/head state must be checked separately before closure.',
}
(ROOT / 'integrity-audit.json').write_text(json.dumps(summary, indent=2) + '\n')
(ROOT / 'integrity-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k not in ('artifacts', 'adapted_files')}, indent=2))
print('\n'.join(a['diff'] for a in adaptations))
raise SystemExit(1 if errors else 0)
