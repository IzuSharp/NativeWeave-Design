#!/usr/bin/env python3
"""Real miniz_oxide C ABI, NuGet-only consumer, no Rust tool discovery, actual AOT."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, platform, shutil, subprocess, zipfile
from xml.sax.saxutils import escape

parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--aot',action='store_true');a=parser.parse_args()
root=Path(__file__).resolve().parent;repo=root.parents[1];out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
work=root/'.work';work.mkdir(exist_ok=True)
env=os.environ.copy();env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',CARGO_TARGET_DIR=str(work/'target'),CARGO_BUILD_BUILD_DIR=str(work/'intermediates'),NUGET_PACKAGES=str(work/'packages'))
dotnet=shutil.which('dotnet');assert dotnet
rid='win-x64' if platform.system()=='Windows' else 'linux-x64'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
result={'scope':'R13/R14/R18 finite integration research, not production support or performance acceptance','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'platform':platform.system(),'rid':rid,'commands':[],'source_files':{},'passed':False,'clean_operating_system':False,'consumer_rust_toolchain_discoverable':None}
for folder in ['native','managed','consumer']:
    for p in (root/folder).rglob('*'):
        if p.is_file() and not set(p.relative_to(root).parts)&{'bin','obj','target','.work'}:
            rel=str(p.relative_to(root)).replace('\\','/');result['source_files'][rel]=sha(p)
            dest=out/'inputs'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
result['source_files']['run.py']=sha(__file__)

def run(name,cmd,cwd=root,runenv=env):
    start=now()
    try:r=subprocess.run([str(x) for x in cmd],cwd=cwd,env=runenv,capture_output=True,timeout=600);stdout,stderr,rc=r.stdout,r.stderr,r.returncode
    except subprocess.TimeoutExpired as e:stdout,stderr,rc=e.stdout or b'',e.stderr or b'',124
    (out/(name+'.stdout')).write_bytes(stdout);(out/(name+'.stderr')).write_bytes(stderr)
    result['commands'].append({'name':name,'command':[str(x) for x in cmd],'exit_code':rc,'started_at':start,'finished_at':now(),'stdout_sha256':sha(out/(name+'.stdout')),'stderr_sha256':sha(out/(name+'.stderr'))})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(name,rc,flush=True)
    if rc:raise RuntimeError(stdout[-2500:].decode(errors='replace')+stderr[-2000:].decode(errors='replace'))
    return stdout.decode(errors='replace')

try:
    run('rustc',['rustc','-Vv']);run('sdk',[dotnet,'--info'])
    manifest=root/'native/Cargo.toml'
    run('native-test',['cargo','test','--locked','--manifest-path',manifest])
    metadata=json.loads(run('cargo-metadata',['cargo','metadata','--locked','--format-version','1','--manifest-path',manifest]))
    inventory=[]
    for package in metadata['packages']:
        path=Path(package['manifest_path']);vcs=path.parent/'.cargo_vcs_info.json'
        inventory.append({k:package.get(k) for k in ['name','version','license','repository','source','rust_version']}|{'vcs':json.loads(vcs.read_text()) if vcs.exists() else None})
    (out/'dependency-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    log=run('native-build',['cargo','build','--release','--locked','--manifest-path',manifest,'--message-format=json'])
    libs=[]
    for line in log.splitlines():
        try:item=json.loads(line)
        except ValueError:continue
        if item.get('reason')=='compiler-artifact' and item.get('target',{}).get('name')=='nw_codec_research':libs.extend(Path(f) for f in item['filenames'] if f.endswith(('.so','.dll')))
    assert len(libs)==1;native=libs[0];native_sha=sha(native)
    feed=work/'feed';feed.mkdir(exist_ok=True)
    run('pack',[dotnet,'pack',root/'managed/Codec.csproj','-c','Release','-o',feed,f'-p:NativeAsset={native}',f'-p:NativeRid={rid}','--disable-build-servers'])
    package=feed/'NativeWeave.Research.Codec.0.0.1.nupkg'
    with zipfile.ZipFile(package) as archive:
        assert hashlib.sha256(archive.read(f'runtimes/{rid}/native/{native.name}')).hexdigest()==native_sha
        assert not any(name.endswith(('.targets','.props','.rs')) for name in archive.namelist())
        result['package_entries']=archive.namelist()
    consumer=work/'independent-consumer';shutil.copytree(root/'consumer',consumer,dirs_exist_ok=True,ignore=shutil.ignore_patterns('bin','obj'))
    (consumer/'NuGet.Config').write_text('<configuration><packageSources><clear/><add key="local" value="'+escape(str(feed),{'"':'&quot;'})+'"/><add key="nuget" value="https://api.nuget.org/v3/index.json"/></packageSources></configuration>')
    no_rust=env.copy()
    for key in ['CARGO_HOME','RUSTUP_HOME','RUSTUP_TOOLCHAIN','RUSTC','CARGO']:no_rust.pop(key,None)
    paths=no_rust.get('PATH','').split(os.pathsep)
    for tool in ['cargo','rustc','rustup']:
        while found:=shutil.which(tool,path=os.pathsep.join(paths)):
            parent=str(Path(found).parent).lower();new=[p for p in paths if str(Path(p)).lower()!=parent]
            assert len(new)<len(paths);paths=new
    no_rust['PATH']=os.pathsep.join(paths)
    assert not any(shutil.which(t,path=no_rust['PATH']) for t in ['cargo','rustc','rustup'])
    result['consumer_rust_toolchain_discoverable']=False
    run('consumer-build-no-rid-no-rust',[dotnet,'build','-c','Release','--disable-build-servers'],consumer,no_rust)
    ordinary=run('consumer-run-no-rid-no-rust',[dotnet,'run','-c','Release','--no-build'],consumer,no_rust)
    assert 'codec checks=16 aot=False' in ordinary
    # New application code, same nupkg and native asset, offline after restore.
    (consumer/'AdditionalApplicationType.cs').write_text('public sealed record OrdinaryApplicationEntity(int Id, string Name);\n')
    run('consumer-change-offline',[dotnet,'build','-c','Release','--no-restore','--disable-build-servers'],consumer,no_rust)
    assert sha(native)==native_sha
    result.update(native_sha256=native_sha,package_sha256=sha(package),rid_free_consumer=True,application_change_reuses_native=True)
    if a.aot:
        publish=out/'publish'
        run('aot-publish-no-rust',[dotnet,'publish','-c','Release','-r',rid,'-p:PublishAot=true','-o',publish,'--disable-build-servers'],consumer,no_rust)
        exe=publish/('Consumer.exe' if platform.system()=='Windows' else 'Consumer')
        deployed_native=list(publish.rglob(native.name));assert len(deployed_native)==1 and sha(deployed_native[0])==native_sha
        execute_env=no_rust.copy()
        for key in list(execute_env):
            if key.startswith('DOTNET_ROOT'):execute_env.pop(key)
        output=run('actual-aot',[exe,'--aot'],publish,execute_env)
        assert 'codec checks=17 aot=True' in output
        result.update(aot_executed=True,aot_binary_sha256=sha(exe))
    shutil.copyfile(package,out/package.name)
    result['passed']=True
finally:
    result['finished_at']=now();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
