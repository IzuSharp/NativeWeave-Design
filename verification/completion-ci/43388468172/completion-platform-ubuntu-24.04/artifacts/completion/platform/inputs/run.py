#!/usr/bin/env python3
"""Bounded R01 language/AOT research. Logs all commands, including expected negatives."""
import argparse, datetime, hashlib, json, os, pathlib, platform, shutil, subprocess

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--dotnet', default='dotnet')
ap.add_argument('--aot', action='store_true')
args = ap.parse_args()
root = pathlib.Path(__file__).resolve().parents[2]
fixture = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', MSBUILDDISABLENODEREUSE='1')
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
result = {'scope': 'R01 modern C# finite research; no product or benchmark acceptance', 'platform': {'os': platform.system(), 'arch': platform.machine()}, 'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(), 'source_snapshot': [], 'commands': [], 'started_at': now(), 'passed': False}
for name in ['run.py','modern/Modern.csproj','modern/Program.cs','modern/Negative.cs.txt']:
    p = fixture/name; dest = out/'inputs'/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p,dest)
    result['source_snapshot'].append({'path':str(p.relative_to(root)), 'sha256':sha(p)})

def run(label, argv, expected=0):
    started=now()
    try:
        r=subprocess.run([str(x) for x in argv],cwd=fixture,env=env,capture_output=True,timeout=600)
        stdout,stderr,code=r.stdout,r.stderr,r.returncode
    except subprocess.TimeoutExpired as e:
        stdout,stderr,code=e.stdout or b'',e.stderr or b'',124
    (out/(label+'.stdout')).write_bytes(stdout); (out/(label+'.stderr')).write_bytes(stderr)
    record={'name':label,'command':[str(x) for x in argv],'exit_code':code,'started_at':started,'finished_at':now(),'stdout_sha256':sha(out/(label+'.stdout')),'stderr_sha256':sha(out/(label+'.stderr'))}
    result['commands'].append(record)
    if (expected==0 and code!=0) or (expected!=0 and code==0):
        raise RuntimeError(f'{label} unexpected exit {code}: '+stdout[-3000:].decode(errors='replace')+stderr[-1000:].decode(errors='replace'))
    return stdout.decode(errors='replace')+stderr.decode(errors='replace')

try:
    run('sdk-info',[args.dotnet,'--info'])
    project=fixture/'modern/Modern.csproj'
    ordinary=run('ordinary',[args.dotnet,'run','--project',project,'-c','Release','--disable-build-servers'])
    assert 'checks=9 ' in ordinary and 'aot=False' in ordinary
    negative=out/'negative';negative.mkdir(exist_ok=True)
    (negative/'External.cs').write_bytes((fixture/'modern/Negative.cs.txt').read_bytes())
    (negative/'External.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><LangVersion>15.0</LangVersion></PropertyGroup><ItemGroup><ProjectReference Include="'+str(project)+'" /></ItemGroup></Project>')
    errors=run('external-closed-negative',[args.dotnet,'build',negative/'External.csproj','--disable-build-servers'],expected=1)
    assert 'closed' in errors.lower() and 'error CS' in errors
    result['closed_external_negative']=True
    rid='win-x64' if platform.system()=='Windows' else 'linux-x64'
    result['aot_executions']=[]
    if args.aot:
        for label,properties in [('default',[]),('runtime-async',['-p:Features=runtime-async=on'])]:
            published=out/('publish-'+label)
            run('publish-'+label,[args.dotnet,'publish',project,'-c','Release','-r',rid,'-p:PublishAot=true','--disable-build-servers','-o',published,*properties])
            executable=published/('Modern.exe' if platform.system()=='Windows' else 'Modern')
            output=run('aot-'+label,[executable,'--aot'])
            assert 'checks=10 ' in output and 'aot=True' in output
            result['aot_executions'].append({'configuration':label,'rid':rid,'binary_sha256':sha(executable),'published':True,'executed':True})
    result['passed']=True
finally:
    result['finished_at']=now()
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'aot_executions':len(result['aot_executions']),'closed_negative':result['closed_external_negative']}))
