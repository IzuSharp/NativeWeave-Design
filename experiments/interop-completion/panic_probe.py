"""Actual child-process outcomes for Rust panic policy; no expected platform exit code assumed."""
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
E=Path(__file__).resolve().parent;D=E.parents[1];W=E/'.work/panic';W.mkdir(parents=True,exist_ok=True)
OUT=D/'verification/interop-completion/panic-linux';OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def no_core():
    import resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
records=[]
def run(name,args):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r=subprocess.run(list(map(str,args)),cwd=E,capture_output=True,text=True,timeout=30,preexec_fn=no_core if sys.platform!='win32' else None)
    (OUT/(name+'.stdout')).write_text(r.stdout);(OUT/(name+'.stderr')).write_text(r.stderr)
    records.append(dict(name=name,argv=list(map(str,args)),exit_code=r.returncode,started_utc=start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdout_sha256=sha(OUT/(name+'.stdout')),stderr_sha256=sha(OUT/(name+'.stderr'))))
    return r
assert run('version',['rustc','-Vv']).returncode==0
for strategy in ['unwind','abort']:
    exe=W/(strategy+('.exe' if sys.platform=='win32' else ''))
    assert run('compile-'+strategy,['rustc','--edition=2024','-C','panic='+strategy,E/'panic_probe.rs','-o',exe]).returncode==0
    for case in (['catch','payload-drop','payload-forget','hook','cleanup','ffi'] if strategy=='unwind' else ['catch']):
        r=run(strategy+'-'+case,[exe,case])
        success=strategy=='unwind' and case in ['catch','payload-forget']
        assert (r.returncode==0)==success,(strategy,case,r.returncode)
        if case=='catch' and success:assert 'CAUGHT ordinary' in r.stdout
        if case=='payload-forget':assert 'QUARANTINED payload' in r.stdout
        if not success:assert 'panic' in r.stderr.lower(),r.stderr
(OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
(OUT/'result.json').write_text(json.dumps(dict(success=True,platform=platform.platform(),source_commit=None,baseline_commit=subprocess.check_output(['git','-C',str(D),'rev-parse','HEAD'],text=True).strip(),source_files={str((E/p).relative_to(D)):sha(E/p) for p in ['panic_probe.py','panic_probe.rs']},cases=7,independent_review=False,limits=['Linux process outcomes only; not full engine poison or allocator OOM proof','Payload quarantine intentionally retains the caught payload; not leak-free recovery']),indent=2)+'\n')
print('SUCCESS panic-probe cases=7 positive=2 fatal=5')
