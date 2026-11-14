#!/usr/bin/env python3
"""Run bounded research fixtures and retain exact commands, bytes, exits and hashes."""
import argparse, hashlib, json, os, pathlib, platform, shutil, subprocess, time

ap=argparse.ArgumentParser()
ap.add_argument('suite',choices=['protocol','kestrel'])
ap.add_argument('--output',required=True)
ap.add_argument('--rid')
args=ap.parse_args()
root=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',MSBUILDUSESERVER='0')
inputs={}
for p in sorted((root/args.suite).rglob('*')):
    if p.is_file() and not any(x in p.relative_to(root/args.suite).parts for x in ['bin','obj','target']):
        rel=p.relative_to(root);data=p.read_bytes();inputs[str(rel).replace('\\','/')]=hashlib.sha256(data).hexdigest()
        target=out/'inputs'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
inputs['run.py']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
def run(name,cmd,timeout=600):
    started=time.time();rec={'name':name,'command':cmd,'timeout_seconds':timeout}
    with (out/(name+'.stdout.txt')).open('wb') as o,(out/(name+'.stderr.txt')).open('wb') as e:
        try: r=subprocess.run(cmd,cwd=root,env=env,stdout=o,stderr=e,timeout=timeout);rec['exit_code']=r.returncode
        except subprocess.TimeoutExpired:rec.update(exit_code=None,timed_out=True)
        except OSError as ex:rec.update(exit_code=None,launch_error=str(ex))
    rec['elapsed_seconds']=round(time.time()-started,3)
    rec['stdout_sha256']=hashlib.sha256((out/(name+'.stdout.txt')).read_bytes()).hexdigest()
    rec['stderr_sha256']=hashlib.sha256((out/(name+'.stderr.txt')).read_bytes()).hexdigest()
    records.append(rec);save();print(name,rec.get('exit_code'),flush=True)
    return rec.get('exit_code')==0
records=[]
manifest={'suite':args.suite,'os':platform.system(),'arch':platform.machine(),'inputs_sha256':inputs,'commands':records,'kind':'research_only','limitations':['No NativeWeave product implementation.','Protocol Rust tests do not execute a C# FFI Handler.','Kestrel is solely the managed comparator.','Finite tests do not establish long-load performance or platform certification.']}
try:manifest['git_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
except subprocess.CalledProcessError:manifest['git_head']=None
def save():
    (out/'run.json').write_text(json.dumps(manifest,indent=2)+'\n')
save()
if args.suite=='protocol':
    ok=run('rustc-version',['rustc','-Vv'],30) and run('cargo-version',['cargo','-V'],30)
    ok=ok and run('test',['cargo','test','--locked','--manifest-path',str(root/'protocol/Cargo.toml'),'--','--nocapture'])
    if ok:ok=run('dependency-tree',['cargo','tree','--locked','--manifest-path',str(root/'protocol/Cargo.toml')],60)
else:
    rid=args.rid or ('win-x64' if platform.system()=='Windows' else 'linux-x64')
    publish=out/'publish'
    ok=run('dotnet-info',['dotnet','--info'],30)
    ok=ok and run('publish',['dotnet','publish',str(root/'kestrel/KestrelComparator.csproj'),'-c','Release','-r',rid,'-p:PublishAot=true','-o',str(publish)])
    if ok:
        exe=publish/('KestrelComparator.exe' if platform.system()=='Windows' else 'KestrelComparator')
        manifest['binary_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
        ok=run('native-aot-run',[str(exe)],40)
manifest['success']=ok;save()
raise SystemExit(0 if ok else 1)
