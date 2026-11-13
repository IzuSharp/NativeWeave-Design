"""New R07/D04 experiment, not a repeat of the migrated fixture suite or a product build."""
from pathlib import Path
import datetime,hashlib,json,os,platform,re,shutil,subprocess,sys
E=Path(__file__).resolve().parent;D=E.parents[1];W=E/'.work';OUT=E/'artifacts'/('admission-'+('win-x64' if sys.platform=='win32' else 'linux-x64'))
OUT.mkdir(parents=True,exist_ok=True);W.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
env=os.environ.copy();env.update(CARGO_TARGET_DIR=str(W/'target'),CARGO_BUILD_BUILD_DIR=str(W/'intermediates'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
records=[]
source=subprocess.check_output(['git','-C',str(D),'rev-parse','HEAD'],text=True).strip()
result={'success':False,'design_commit':source,'run_id':os.environ.get('GITHUB_RUN_ID'),'platform':platform.platform(),'scope':'R07/D04 synchronous admission research; not product Delivery or full lifecycle acceptance','independent_review':False}
def run(name,args,cwd=D/'experiments/native-slices',timeout=600):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  p=subprocess.run([str(a) for a in args],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout);rc,stdout,stderr=p.returncode,p.stdout,p.stderr
 except subprocess.TimeoutExpired as exc:rc,stdout,stderr=124,str(exc.stdout or ''),str(exc.stderr or '')
 (OUT/(name+'.stdout')).write_text(stdout,encoding='utf-8');(OUT/(name+'.stderr')).write_text(stderr,encoding='utf-8')
 records.append({'name':name,'argv':[str(a) for a in args],'cwd':str(cwd),'exit_code':rc,'started_utc':start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':sha(OUT/(name+'.stdout')),'stderr_sha256':sha(OUT/(name+'.stderr'))})
 (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8');print(name,rc,flush=True)
 if rc:raise RuntimeError(stdout[-3000:]+'\n'+stderr[-5000:])
 return stdout
try:
 run('rust-version',['rustc','+1.100.0','-Vv']);run('cargo-version',['cargo','+1.100.0','-Vv']);run('dotnet-info',['dotnet','--info'])
 # Native source is unchanged. Build it for new managed scenarios; do not rerun old tests.
 output=run('native-build',['cargo','+1.100.0','build','--locked','--offline','--release','--manifest-path',D/'experiments/native-slices/interop/native/Cargo.toml','--message-format=json'])
 assets=[]
 for line in output.splitlines():
  try:item=json.loads(line)
  except json.JSONDecodeError:continue
  if item.get('reason')=='compiler-artifact' and item.get('target',{}).get('name')=='nw_interop_probe':assets += [Path(x) for x in item['filenames'] if x.endswith(('.so','.dll'))]
 assert len(assets)==1;native=assets[0];native_hash=sha(native)
 project=E/'Admission.csproj'
 normal=run('normal-run',['dotnet','run','--project',project,'-c','Release',f'-p:NativeAsset={native}'],timeout=180)
 assert 'OBSERVED negative-control post-Dispose call admitted' in normal
 assert 'SUCCESS logical-admission assertions=653 aot=False gate_rounds=64' in normal
 rid='win-x64' if sys.platform=='win32' else 'linux-x64';publish=W/'publish'
 run('aot-publish',['dotnet','publish',project,'-c','Release','-r',rid,'-p:PublishAot=true',f'-p:NativeAsset={native}','-o',publish])
 exe=publish/('Admission.exe' if sys.platform=='win32' else 'Admission')
 aot=run('aot-run',[exe,'--expect-aot'],cwd=publish,timeout=180)
 assert 'OBSERVED negative-control post-Dispose call admitted' in aot
 assert 'SUCCESS logical-admission assertions=653 aot=True gate_rounds=64' in aot
 assert sha(publish/native.name)==native_hash
 result.update(success=True,native_sha256=native_hash,aot_executable_sha256=sha(exe),managed_assertions_per_execution=653,positive_gate_rounds_per_execution=64,groups_per_execution=3,negative_control_observed=True,logical_post_close_rejection=True)
 shutil.copytree(publish,OUT/'publish',dirs_exist_ok=True)
finally:
 paths=['experiments/logical-admission/Program.cs','experiments/logical-admission/Admission.csproj','experiments/logical-admission/run.py','experiments/native-slices/interop/managed/Bridge.cs','experiments/native-slices/interop/native/src/lib.rs','experiments/native-slices/interop/native/Cargo.toml','experiments/native-slices/interop/native/Cargo.lock','experiments/native-slices/global.json','experiments/native-slices/rust-toolchain.toml']
 result['source_files']={p:sha(D/p) for p in paths}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
