"""Exact language exceptions for this local execution's original raw streams."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess

PREFIX = PurePosixPath('verification/local-host/2026-11-14')
MANIFEST = PREFIX / 'raw-execution-language-exceptions.json'
CJK = re.compile('[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]')


def _path(root, value, raw):
    assert isinstance(value, str) and not any(c in value for c in ('\\', ':', '\0')), 'invalid supplemental path'
    path = PurePosixPath(value)
    assert not path.is_absolute() and path.as_posix() == value, 'noncanonical supplemental path'
    assert len(path.parts) == 6 and not {'.', '..'}.intersection(path.parts), 'invalid supplemental depth'
    assert path.parts[:3] == PREFIX.parts and path.parts[3] in {'windows', 'linux'}, 'outside current host evidence'
    if raw:
        assert path.suffix in {'.stdout', '.stderr'}, 'only raw command streams may be exempt'
    else:
        assert path.name in {'result.json', 'results.json'}, 'not a runner result manifest'
    target = root / value
    assert target.resolve().is_relative_to(root.resolve()) and target.is_file(), 'missing or escaping evidence'
    return path, target


def verified_raw_exceptions(root):
    """Validate every explicit entry before allowing any localized raw bytes."""
    root = Path(root)
    path = root / MANIFEST
    if not path.exists():
        return set()
    manifest = json.loads(path.read_bytes())
    assert set(manifest) == {'schema_version', 'scope', 'source_commit', 'entries'}, 'unexpected exception manifest fields'
    assert manifest['schema_version'] == '1.0.0' and manifest['scope'] == 'raw_execution_only'
    source = manifest['source_commit']
    assert isinstance(source, str) and re.fullmatch('[0-9a-f]{40}', source), 'invalid source commit'
    subprocess.run(['git', 'cat-file', '-e', source + '^{commit}'], cwd=root,
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    baseline = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source], cwd=root).decode().splitlines())
    assert isinstance(manifest['entries'], list) and manifest['entries'], 'empty raw exceptions'
    allowed = set()
    for entry in manifest['entries']:
        assert set(entry) == {'path', 'bytes', 'sha256', 'reason', 'run'}, 'unexpected raw entry fields'
        relative, raw_file = _path(root, entry['path'], raw=True)
        assert entry['path'] not in baseline and entry['path'] not in allowed, 'historical or duplicate raw exception'
        assert isinstance(entry['reason'], str) and entry['reason'].strip(), 'missing raw-evidence reason'
        assert type(entry['bytes']) is int and entry['bytes'] >= 0
        assert isinstance(entry['sha256'], str) and re.fullmatch('[0-9a-f]{64}', entry['sha256'])
        raw = raw_file.read_bytes()
        assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], 'raw bytes changed'
        run = entry['run']
        assert set(run) == {'path', 'sha256', 'command_name', 'stream'}, 'unexpected run binding fields'
        run_relative, run_file = _path(root, run['path'], raw=False)
        assert run_relative.parent == relative.parent, 'raw stream belongs to another run directory'
        assert isinstance(run['sha256'], str) and re.fullmatch('[0-9a-f]{64}', run['sha256'])
        run_raw = run_file.read_bytes()
        assert hashlib.sha256(run_raw).hexdigest() == run['sha256'], 'runner manifest changed'
        result = json.loads(run_raw)
        assert result['source_commit'] == source, 'runner source differs from exception source'
        platform = result['platform']
        actual_os = platform['os'] if isinstance(platform, dict) else platform
        assert actual_os == {'windows': 'Windows', 'linux': 'Linux'}[relative.parts[3]], 'runner host differs'
        assert isinstance(run['command_name'], str) and re.fullmatch('[a-z0-9][a-z0-9-]*', run['command_name'])
        assert run['stream'] in {'stdout', 'stderr'}
        assert relative.name == run['command_name'] + '.' + run['stream'], 'raw filename differs from command stream'
        commands = [row for row in result['commands'] if row['name'] == run['command_name']]
        assert len(commands) == 1 and commands[0][run['stream'] + '_sha256'] == entry['sha256'], 'raw stream not bound by runner'
        allowed.add(entry['path'])
    return allowed


def check_tracked_language(root, paths, allowed):
    """Keep the existing tracked-text check; only verified exact paths are allowed."""
    for path in paths:
        try:
            text = (Path(root) / path).read_text(encoding='utf-8')
        except UnicodeError:
            continue
        if CJK.search(text):
            assert path in allowed, (path, 'unclassified non-English text')
