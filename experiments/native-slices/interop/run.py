"""Run recovered Interop sources; preserve real outputs and artifact hashes.
No release publishing or task acceptance. Cargo has no third-party dependencies.
The native build and consumer run share a CI host, NOT a pristine Rust-free host.
"""
from pathlib import Path
import datetime, hashlib, json, os, platform, shutil, subprocess, sys, zipfile
ROOT = Path(__file__).resolve().parents[1]
rid = 'win-x64' if sys.platform == 'win32' else 'linux-x64'
WORK = ROOT / '.work' / rid
OUT = ROOT / 'artifacts' / ('interop-' + rid)
WORK.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
records = []
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(name, args, cwd=ROOT, timeout=600):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        proc = subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc, stdout, stderr = 124, str(exc.stdout or ''), str(exc.stderr or '')
    (OUT / (name + '.stdout')).write_text(stdout, encoding='utf-8')
    (OUT / (name + '.stderr')).write_text(stderr, encoding='utf-8')
    records.append({'name':name,'argv':[str(a) for a in args],'cwd':str(cwd),'exit_code':rc,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':sha(OUT/(name+'.stdout')),'stderr_sha256':sha(OUT/(name+'.stderr'))})
    (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print(name, rc, flush=True)
    if rc: raise RuntimeError(f'{name} failed ({rc}):\n{stdout[-4000:]}\n{stderr[-4000:]}')
    return stdout

env=os.environ.copy()
env.update(CARGO_TARGET_DIR=str(WORK/'target'), CARGO_BUILD_BUILD_DIR=str(WORK/'intermediates'), NUGET_PACKAGES=str(WORK/'packages'), DOTNET_CLI_TELEMETRY_OPTOUT='1')
manifest=ROOT/'interop/native/Cargo.toml'
result={'source_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'platform':platform.platform(),'rid':rid,'success':False,'scope':'R03/R04/R07/R10 executable fixture; not production ABI or completed Delivery','clean_rust_free_host':False}
try:
    run('rust-version',['rustc','+1.100.0','-Vv'])
    run('cargo-version',['cargo','+1.100.0','-Vv'])
    run('dotnet-info',['dotnet','--info'])
    run('rust-tests',['cargo','+1.100.0','test','--locked','--offline','--manifest-path',manifest,'--','--test-threads=1'])
    output=run('native-build',['cargo','+1.100.0','build','--locked','--offline','--release','--manifest-path',manifest,'--message-format=json'])
    libraries=[]
    for line in output.splitlines():
        try: item=json.loads(line)
        except json.JSONDecodeError: continue
        if item.get('reason')=='compiler-artifact' and item.get('target',{}).get('name')=='nw_interop_probe':
            libraries += [Path(f) for f in item['filenames'] if f.endswith(('.so','.dll'))]
    assert len(libraries)==1,libraries
    native=libraries[0]; original_hash=sha(native)
    feed=WORK/'feed';feed.mkdir(exist_ok=True)
    run('pack',['dotnet','pack',ROOT/'interop/managed/NativeWeave.Interop.Probe.csproj','-c','Release','-o',feed,f'-p:NativeAsset={native}',f'-p:ProbeRid={rid}'])
    package=feed/'NativeWeave.Interop.Probe.0.0.1.nupkg'
    with zipfile.ZipFile(package) as z:
        asset=f'runtimes/{rid}/native/{native.name}'
        assert hashlib.sha256(z.read(asset)).hexdigest()==original_hash
    # Copy a real consumer out of the source tree. It refers only to the packed NuGet.
    consumer=WORK/'consumer';shutil.copytree(ROOT/'interop/consumer',consumer,dirs_exist_ok=True)
    import xml.sax.saxutils
    (consumer/'NuGet.Config').write_text('<configuration><packageSources><clear/><add key="local" value="'+xml.sax.saxutils.escape(str(feed),{'"':'&quot;'})+'"/><add key="nuget" value="https://api.nuget.org/v3/index.json"/></packageSources></configuration>',encoding='utf-8')
    # Deliberately no RID arguments for normal local .NET development.
    run('consumer-build-no-rid',['dotnet','build','-c','Release'],cwd=consumer)
    normal=run('consumer-run-no-rid',['dotnet','run','-c','Release','--no-build'],cwd=consumer)
    assert 'SUCCESS assertions=' in normal
    publish=WORK/'publish'
    run('aot-publish',['dotnet','publish','-c','Release','-r',rid,'-p:PublishAot=true','-o',publish],cwd=consumer)
    exe=publish/('Consumer.exe' if sys.platform=='win32' else 'Consumer')
    native_copies=list(publish.rglob(native.name))
    assert len(native_copies)==1 and sha(native_copies[0])==original_hash,native_copies
    aot=run('aot-run',[exe,'--expect-aot'],cwd=publish,timeout=90)
    assert 'SUCCESS assertions=' in aot and 'aot=True' in aot
    assert sha(native)==original_hash
    result.update(success=True,native_sha256=original_hash,package_sha256=sha(package),aot_executable_sha256=sha(exe),rust_tests=4,managed_groups_per_execution=6,held_call_dispose_rounds_per_execution=32,rid_free_build_run=True)
    shutil.copy2(package,OUT/package.name)
    shutil.copy2(manifest.with_name('Cargo.lock'),OUT/'Cargo.lock')
    shutil.copytree(publish,OUT/'publish',dirs_exist_ok=True)
finally:
    result['source_files']={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'interop').rglob('*')) if p.is_file() and not any(x in p.parts for x in ('bin','obj','target','__pycache__'))}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
