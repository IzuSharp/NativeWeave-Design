#!/usr/bin/env python3
"""Publish and execute the scoped diagnostics probe; never enables an exporter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--rid', default='win-x64' if os.name == 'nt' else 'linux-x64')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    inputs = output / 'inputs'
    inputs.mkdir(exist_ok=True)
    source = [base / 'diagnostics/DiagnosticsProbe.csproj', base / 'diagnostics/Program.cs', Path(__file__).resolve()]
    hashes = {}
    for path in source:
        name = path.relative_to(base).as_posix()
        target = inputs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        hashes[name] = digest(path)
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_GENERATE_ASPNET_CERTIFICATE='false',
               DOTNET_CLI_USE_MSBUILD_SERVER='0')
    record = {'kind': 'research_only', 'os': platform.system(), 'arch': platform.machine(),
              'inputs_sha256': hashes, 'commands': [], 'success': False,
              'limitations': ['Not a cross-language propagation test.', 'Single-process no-observer timing is not a production benchmark.', 'Current-thread allocation counter excludes native memory.']}
    executable = output / 'publish' / ('DiagnosticsProbe.exe' if os.name == 'nt' else 'DiagnosticsProbe')
    commands = [('dotnet-info', ['dotnet', '--info'], 30),
                ('publish', ['dotnet', 'publish', str(base / 'diagnostics/DiagnosticsProbe.csproj'), '-c', 'Release', '-r', args.rid, '-p:PublishAot=true', '-o', str(output / 'publish')], 600),
                ('native-aot-run', [str(executable)], 30)]
    for name, cmd, timeout in commands:
        started = time.monotonic()
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout)
        stdout, stderr = output / f'{name}.stdout.txt', output / f'{name}.stderr.txt'
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        record['commands'].append({'name': name, 'command': cmd, 'timeout_seconds': timeout, 'exit_code': result.returncode,
                                   'elapsed_seconds': round(time.monotonic()-started, 3),
                                   'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr)})
        if name == 'native-aot-run':
            record['binary_sha256'] = digest(executable)
        if result.returncode:
            break
    record['success'] = len(record['commands']) == 3 and all(row['exit_code'] == 0 for row in record['commands'])
    (output / 'run.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'success': record['success']}))
    return 0 if record['success'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
