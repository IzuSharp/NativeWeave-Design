"""Execute one independent native domain fixture and preserve real command evidence."""
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
ROOT=Path(__file__).resolve().parent
name=sys.argv[1]
if name not in ('database','server'):raise SystemExit('expected database or server')
crate=ROOT/name
out=ROOT/'artifacts'/f'{name}-{platform.system().lower()}';out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
env=os.environ.copy();env['CARGO_TARGET_DIR']=str(ROOT/'.work'/name);env['CARGO_BUILD_BUILD_DIR']=str(ROOT/'.work'/(name+'-intermediates'))
result={'success':False,'fixture':name,'source_commit':os.environ.get('FIXTURE_COMMIT',os.environ.get('GITHUB_SHA')),'workflow_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'platform':platform.platform(),'scope':'finite native source-informed fixture; no C# domain binding, PostgreSQL, TLS, load or product acceptance'}
try:
 for label,args in [('rust-version',['rustc','+1.100.0','-Vv']),('cargo-version',['cargo','+1.100.0','-Vv']),('tests',['cargo','+1.100.0','test','--locked','--manifest-path',str(crate/'Cargo.toml'),'--','--test-threads=1'])]:
  started=datetime.datetime.now(datetime.timezone.utc).isoformat()
  try:
   p=subprocess.run(args,cwd=ROOT,env=env,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=900);rc,stdout,stderr=p.returncode,p.stdout,p.stderr
  except subprocess.TimeoutExpired as e:rc,stdout,stderr=124,str(e.stdout or ''),str(e.stderr or '')
  (out/(label+'.stdout')).write_text(stdout,encoding='utf-8');(out/(label+'.stderr')).write_text(stderr,encoding='utf-8')
  records.append({'command':args,'exit_code':rc,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':sha(out/(label+'.stdout')),'stderr_sha256':sha(out/(label+'.stderr'))})
  (out/'commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
  print(label,rc,flush=True)
  if rc:raise RuntimeError(stdout[-3000:]+'\n'+stderr[-8000:])
 result['success']=True
finally:
 result['source_files']={str(p.relative_to(ROOT)):sha(p) for p in crate.rglob('*') if p.is_file() and not any(k in p.parts for k in ('target','bin','obj'))}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 import shutil
 for n in ('Cargo.toml','Cargo.lock'):
  if (crate/n).exists():shutil.copy2(crate/n,out/n)
 shutil.copytree(crate/'src',out/'src',dirs_exist_ok=True)
