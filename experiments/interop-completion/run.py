"""New scoped research probes; no original experiments or product code are changed."""
from pathlib import Path
import datetime, hashlib, json, os, platform, subprocess, sys

E = Path(__file__).resolve().parent
D = E.parents[1]
OUT = D / 'verification/interop-completion' / ('windows' if sys.platform == 'win32' else 'linux')
OUT.mkdir(parents=True, exist_ok=True)
WORK = E / '.work'
WORK.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(CARGO_TARGET_DIR=str(WORK/'target'), CARGO_BUILD_BUILD_DIR=str(WORK/'intermediates'), DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1')
records=[]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(name, argv, cwd=E, timeout=600, required=True):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        r=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
        rc,stdout,stderr=r.returncode,r.stdout,r.stderr
    except subprocess.TimeoutExpired as ex:
        rc,stdout,stderr=124,str(ex.stdout or ''),str(ex.stderr or '')
    (OUT/(name+'.stdout')).write_text(stdout)
    (OUT/(name+'.stderr')).write_text(stderr)
    record=dict(name=name,argv=list(map(str,argv)),exit_code=rc,started_utc=start,
        ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        stdout_sha256=sha(OUT/(name+'.stdout')),stderr_sha256=sha(OUT/(name+'.stderr')))
    records.append(record)
    (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
    print(name,rc,flush=True)
    if required and rc: raise RuntimeError(stdout[-4000:]+'\n'+stderr[-4000:])
    return rc,stdout

result=dict(scope='R02/R04/R07/R08/R09/R10/R11: bounded research fixture, not product or performance acceptance',
    platform=platform.platform(),independent_review=False,success=False,source_commit=None,
    baseline_commit=subprocess.check_output(['git','-C',str(D),'rev-parse','HEAD'],text=True).strip(),
    github_run_id=os.environ.get('GITHUB_RUN_ID'),aot_requested='--aot' in sys.argv)
try:
    run('rust-version',['rustc','-Vv']); run('dotnet-info',['dotnet','--info'])
    run('native-test',['cargo','test','--manifest-path',E/'native/Cargo.toml','--locked','--offline'])
    _,text=run('native-build',['cargo','build','--manifest-path',E/'native/Cargo.toml','--locked','--offline','--release','--message-format=json'])
    assets=[]
    for line in text.splitlines():
        try: item=json.loads(line)
        except ValueError: continue
        if item.get('reason')=='compiler-artifact' and item.get('target',{}).get('name')=='nw_interop_completion_probe':
            assets += [Path(x) for x in item['filenames'] if x.endswith(('.so','.dll'))]
    assert len(assets)==1
    asset=assets[0]
    _,normal=run('normal-run',['dotnet','run','--project',E/'Completion.csproj','-c','Release',f'-p:NativeAsset={asset}','-p:NuGetAudit=false'])
    assert 'SUCCESS interop-completion' in normal and 'aot=False callback_rounds=32' in normal
    result.update(normal_executed=True,native_sha256=sha(asset),aot_executed=False)
    _,generator=run('generator-run',['dotnet','run','--project',E/'GeneratorProbe.csproj','-c','Release','-p:NuGetAudit=false','--disable-build-servers'])
    assert 'SUCCESS generator-probe assertions=9' in generator
    _,restrictions=run('restrictions-normal',['dotnet','run','--project',E/'AotRestrictions.csproj','-c','Release','-p:NuGetAudit=false','--disable-build-servers'])
    assert 'SUCCESS aot-restrictions assertions=4 aot=False' in restrictions
    if result['aot_requested']:
        rid='win-x64' if sys.platform=='win32' else 'linux-x64'
        rc,_=run('aot-publish',['dotnet','publish',E/'Completion.csproj','-c','Release','-r',rid,'-p:PublishAot=true','-p:NuGetAudit=false',f'-p:NativeAsset={asset}','-o',WORK/'publish'],required=False)
        result['aot_publish_exit_code']=rc
        if rc==0:
            exe=WORK/'publish'/('Completion.exe' if sys.platform=='win32' else 'Completion')
            _,aot=run('aot-run',[exe,'--expect-aot'],cwd=exe.parent)
            assert 'SUCCESS interop-completion' in aot and 'aot=True callback_rounds=32' in aot
            result.update(aot_executed=True,aot_executable_sha256=sha(exe))
        else:
            result['aot_blocker']='See exact aot-publish stdout/stderr; no AOT execution claimed.'
            raise RuntimeError('Required AOT publish failed; normal mode is not sufficient')
        run('restrictions-aot-publish',['dotnet','publish',E/'AotRestrictions.csproj','-c','Release','-r',rid,'-p:PublishAot=true','-p:NuGetAudit=false','-o',WORK/'restrictions-aot','--disable-build-servers'])
        rex=WORK/'restrictions-aot'/('AotRestrictions.exe' if sys.platform=='win32' else 'AotRestrictions')
        _,rout=run('restrictions-aot-run',[rex,'--expect-aot'],cwd=rex.parent)
        assert 'SUCCESS aot-restrictions assertions=6 aot=True' in rout
        result['restrictions_aot_sha256']=sha(rex)
    result['success']=True
finally:
    paths=['native/Cargo.toml','native/Cargo.lock','native/src/lib.rs','Completion.csproj','Program.cs','global.json','rust-toolchain.toml','run.py','GeneratorProbe.csproj','GeneratorProbe.cs','AotRestrictions.csproj','AotRestrictions.cs','Directory.Build.props']
    result['source_files']={str((E/p).relative_to(D)):sha(E/p) for p in paths if (E/p).exists()}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
