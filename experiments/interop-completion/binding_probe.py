"""Compare pinned csbindgen output with framework LibraryImport for the same export.
Pass the checkout root containing csbindgen/Cargo.toml as the first argument.
Run run.py --aot first to build the research native asset. No upstream source is vendored.
"""
from pathlib import Path
import datetime, hashlib, json, os, platform, subprocess, sys
E=Path(__file__).resolve().parent; D=E.parents[1]; UP=Path(sys.argv[1]).resolve()
W=E/'.work/binding'; W.mkdir(parents=True,exist_ok=True)
OUT=D/'verification/interop-completion/binding-linux';OUT.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',CARGO_TARGET_DIR=str(W/'target'),CARGO_BUILD_BUILD_DIR=str(W/'intermediates'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
records=[]
def run(name,args,cwd=E):
    t=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,capture_output=True,text=True,timeout=600)
    (OUT/(name+'.stdout')).write_text(r.stdout);(OUT/(name+'.stderr')).write_text(r.stderr)
    records.append(dict(name=name,argv=list(map(str,args)),started_utc=t,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=r.returncode,stdout_sha256=sha(OUT/(name+'.stdout')),stderr_sha256=sha(OUT/(name+'.stderr'))))
    (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n'); print(name,r.returncode,flush=True)
    if r.returncode:raise RuntimeError(r.stdout[-3000:]+'\n'+r.stderr[-3000:])
    return r.stdout
source_identity=json.loads((UP/'source-identity.json').read_text())
for item in source_identity['files']:
    data=(UP/item['path']).read_bytes();blob=hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
    assert blob==item['blob_sha'],item['path']
assert source_identity['commit']=='b9eb1e84bb8185b78a4e8364fd948fee300329a7'
(W/'Cargo.toml').write_text('[package]\nname="binding_probe"\nversion="0.0.0"\nedition="2024"\n[dependencies]\ncsbindgen={path='+json.dumps(str(UP/'csbindgen'))+'}\n')
(W/'src').mkdir(exist_ok=True)
(W/'src/main.rs').write_text('fn main(){ let a:Vec<String>=std::env::args().collect(); csbindgen::Builder::default().input_extern_file(&a[1]).csharp_namespace("Generated").csharp_class_name("Native").csharp_dll_name("nw_interop_completion_probe").generate_csharp_file(&a[2]).unwrap(); }\n')
run('lock',['cargo','generate-lockfile','--offline'],W)
generated=W/'Generated.cs'
output=run('generate',['cargo','run','--locked','--offline','--release','--',E/'binding-api.rs',generated],W)
text=generated.read_text();assert 'nw_ic_validate_extent' in text and 'unsupported_tuple' not in text
assert "csbindgen can't handle this parameter type" in output
# A required export omitted by an upstream parser must fail the NativeWeave inventory gate.
inventory_missing=['unsupported_tuple']
print('OBSERVED unsupported export omission; inventory gate rejects it',flush=True)
asset=E/'.work/target/release'/('nw_interop_completion_probe.dll' if sys.platform=='win32' else 'libnw_interop_completion_probe.so')
normal=run('normal',['dotnet','run','--project',E/'BindingConsumer.csproj','-c','Release','-p:NuGetAudit=false',f'-p:GeneratedBindings={generated}',f'-p:NativeAsset={asset}','--disable-build-servers'])
assert 'cases=60 aot=False' in normal
rid='win-x64' if sys.platform=='win32' else 'linux-x64'
run('publish',['dotnet','publish',E/'BindingConsumer.csproj','-c','Release','-r',rid,'-p:PublishAot=true','-p:NuGetAudit=false',f'-p:GeneratedBindings={generated}',f'-p:NativeAsset={asset}','-o',W/'publish','--disable-build-servers'])
exe=W/'publish'/('BindingConsumer.exe' if sys.platform=='win32' else 'BindingConsumer')
aot=run('aot',[exe,'--expect-aot'],exe.parent);assert 'cases=60 aot=True' in aot
(OUT/'generated.cs.txt').write_bytes(generated.read_bytes());(OUT/'Cargo.lock').write_bytes((W/'Cargo.lock').read_bytes())
result=dict(success=True,platform=platform.platform(),source_commit=None,baseline_commit=subprocess.check_output(['git','-C',str(D),'rev-parse','HEAD'],text=True).strip(),upstream=source_identity,generated_sha256=sha(generated),native_sha256=sha(asset),aot_sha256=sha(exe),normal_cases=60,aot_cases=60,unsupported_export_missing=inventory_missing,independent_review=False,
source_files={str((E/p).relative_to(D)):sha(E/p) for p in ['binding_probe.py','binding-api.rs','BindingConsumer.cs','BindingConsumer.csproj','Directory.Build.props','native/src/lib.rs']})
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
