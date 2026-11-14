#!/usr/bin/env python3
"""Compile the complete design surface, consumers and negative cases; optionally execute an AOT fixture.

This never executes a Database/Server/Interop product operation. The declaration bodies
are deliberately unimplemented. Packaging/generator/native-codec evidence has its own probe.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', default=shutil.which('dotnet'))
    parser.add_argument('--output', default=str(ROOT/'artifacts/public-api'/platform.system().lower()))
    parser.add_argument('--aot', action='store_true')
    args = parser.parse_args()
    assert args.dotnet, 'Install the stable SDK pinned in global.json.'
    dotnet = str(Path(args.dotnet).resolve())
    runtime_root = Path(dotnet).parent
    out = Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('Use a new evidence directory; earlier attempts must remain available.')
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_CLI_USE_MSBUILD_SERVER='0')
    steps = []
    inputs = []
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name != 'packages.lock.json' and not any(x in {'bin','obj','__pycache__','.work','target'} for x in p.relative_to(HERE).parts):
            inputs.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    for p in sorted((ROOT/'docs/api').glob('*-symbol-policies.json')):
        inputs.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    def run(name, arguments, timeout=600, cwd=HERE):
        command = [str(x) for x in arguments]
        started = time.monotonic()
        proc = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
        log = out/(name+'.log'); log.write_bytes(proc.stdout)
        steps.append({'id':name,'command':command,'cwd':str(cwd),'exit_code':proc.returncode,
                      'duration_seconds':round(time.monotonic()-started,3),
                      'log':log.name,'log_sha256':sha(log)})
        print(name+': exit '+str(proc.returncode), flush=True)
        if proc.returncode: raise RuntimeError(name+' failed; see '+str(log))
        return proc.stdout.decode(errors='replace')
    ok = False
    try:
        version = run('sdk',[dotnet,'--version']).strip()
        assert version == '11.0.100', version
        common = ['--disable-build-servers','-p:UseSharedCompilation=false','--nologo','-v:minimal']
        run('consumer-build',[dotnet,'build','NativeWeave.Api.Consumers/NativeWeave.Api.Consumers.csproj',
                              '--configfile','NuGet.Config',*common])
        run('consumer-execute',[dotnet,HERE/'NativeWeave.Api.Consumers/bin/Debug/net11.0/NativeWeave.Api.Consumers.dll'])
        for project in ['Inventory','Checks']:
            run(project.lower()+'-build',[dotnet,'build',f'NativeWeave.Api.{project}/NativeWeave.Api.{project}.csproj',
                                          '--configfile','NuGet.Offline.Config',*common])
        run('inventory',[dotnet,HERE/'NativeWeave.Api.Inventory/bin/Debug/net11.0/NativeWeave.Api.Inventory.dll',
                         HERE/'NativeWeave.Api.Design',runtime_root,ROOT/'docs/api'])
        run('negative-consumers',[dotnet,HERE/'NativeWeave.Api.Checks/bin/Debug/net11.0/NativeWeave.Api.Checks.dll',
                                  HERE/'NativeWeave.Api.Design',runtime_root,out/'negative-consumers.json'])
        run('exporter-regressions',[sys.executable,HERE/'NativeWeave.Api.Inventory/verify_exporter.py',
                                    '--dotnet',dotnet,'--output',out/'exporter-regressions'])
        if args.aot:
            rid = 'win-x64' if platform.system() == 'Windows' else 'linux-x64'
            assert platform.machine().lower() in {'amd64','x86_64'}, 'This fixture claims only x64 execution.'
            publish = out/'publish'
            run('native-aot-publish',[dotnet,'publish','NativeWeave.Api.Consumers/NativeWeave.Api.Consumers.csproj',
                                      '-c','Release','-r',rid,'-p:PublishAot=true','--configfile','NuGet.Config',
                                      '--output',publish,*common])
            executable = publish/('NativeWeave.Api.Consumers.exe' if rid.startswith('win') else 'NativeWeave.Api.Consumers')
            run('native-aot-execute',[executable])
            (out/'native-executable-sha256.txt').write_text(sha(executable)+'\n')
        ok = True
    finally:
        restored_locks=[]
        for p in sorted(HERE.glob('NativeWeave.Api.*/packages.lock.json')):
            target=out/(p.parent.name+'.packages.lock.json')
            target.write_bytes(p.read_bytes())
            restored_locks.append({'path':target.name,'sha256':sha(target)})
        summary = {'schema_version':'1.0.0','scope':'public API design compilation and static consumer fixture',
                   'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'platform':platform.system(),'architecture':platform.machine(),
                   'sdk':'11.0.100','language':'15.0','passed':ok,
                   'native_aot_executed':ok and args.aot,'product_implemented':False,
                   'product_operations_executed':False,'native_product_modules_loaded':False,
                   'inputs':inputs,'restored_package_locks':restored_locks,'steps':steps,
                   'limits':['No real Database/Server request executed by these declaration stubs.',
                             'AOT execution runs static JSON/evidence code; rooted consumer bodies are compiled.',
                             'The separate packaging probe tests generator/native asset consumption.']}
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0

if __name__ == '__main__':
    sys.exit(main())
