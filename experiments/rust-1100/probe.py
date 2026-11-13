#!/usr/bin/env python3
"""Execute new R01 fixtures. No production, AOT, benchmark or independent-review claim."""
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence';WORK=ROOT/'work'
OUT.mkdir(exist_ok=True);WORK.mkdir(exist_ok=True)
rows=[]
def command(name,args,cwd=WORK,negative=False,contains=None):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=300)
    end=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT/(name+'.stdout')).write_text(p.stdout)
    (OUT/(name+'.stderr')).write_text(p.stderr)
    ok=(p.returncode!=0) if negative else (p.returncode==0)
    if contains:ok=ok and contains in p.stdout+p.stderr
    rows.append({'name':name,'command':args,'cwd':str(cwd),'exit_code':p.returncode,'expected':'failure' if negative else 'success','expected_diagnostic':contains,'passed':ok,'started_at':start,'finished_at':end,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr.encode()).hexdigest()})
    if not ok:raise RuntimeError(name+' failed expectation\n'+p.stdout+'\n'+p.stderr)
    return p
NEGATIVES={
 'arc_custom_allocator':('use std::{sync::Arc,alloc::Global}; fn main(){let _=Arc::new_in(3,Global);}','E0658'),
 'box_try_map':('fn main(){let _=Box::try_map(Box::new(1_u8),|v|Ok::<_,()>(v));}','E0658'),
 'custom_ordinary_body':('pub extern "custom" fn x() {} fn main(){}','custom'),
 'never_overlap':('trait T {} impl T for fn()->! {} impl T for fn()->std::convert::Infallible {} fn main(){}','E0119')}
finished=False
try:
    command('rustc-version',['rustc','+1.100.0','-Vv'])
    command('cargo-version',['cargo','+1.100.0','-Vv'])
    exe=WORK/('tests.exe' if os.name=='nt' else 'tests')
    command('stable-tests-compile',['rustc','+1.100.0','--edition=2024','--test',str(ROOT/'stable_tests.rs'),'-Dwarnings','-o',str(exe)])
    command('stable-tests-run',[str(exe),'--test-threads=1'])
    for name,(src,diagnostic) in NEGATIVES.items():
        p=WORK/(name+'.rs');p.write_text(src)
        command(name,['rustc','+1.100.0','--edition=2024',str(p),'--emit=metadata'],negative=True,contains=diagnostic)
    p=WORK/'custom_naked.rs'
    p.write_text('#![deny(warnings)]\n#[unsafe(naked)] pub unsafe extern "custom" fn x(){core::arch::naked_asm!("ret");}')
    command('custom-naked-compile-only',['rustc','+1.100.0','--edition=2024','--crate-type=lib',str(p),'--emit=metadata'])
    p=WORK/'edition2021.rs';p.write_text('fn main(){let r:Result<u32,!>=Ok(9);let Ok(v)=r;assert_eq!(v,9);}')
    command('never-2021-compile',['rustc','+1.100.0','--edition=2021',str(p),'--emit=metadata'])
    (WORK/'lint/src').mkdir(parents=True,exist_ok=True);(WORK/'dep/src').mkdir(parents=True,exist_ok=True)
    (WORK/'dep/Cargo.toml').write_text('[package]\nname="unused_dep"\nversion="0.0.0"\nedition="2024"\n')
    (WORK/'dep/src/lib.rs').write_text('pub fn value()->u32{1}\n')
    (WORK/'lint/Cargo.toml').write_text('[package]\nname="lint_probe"\nversion="0.0.0"\nedition="2024"\n[dependencies]\nunused_dep={path="../dep"}\n[lints.cargo]\nunused_dependencies="deny"\n')
    (WORK/'lint/src/main.rs').write_text('fn main(){}\n')
    command('cargo-unused-negative',['cargo','+1.100.0','check','--offline','--all-targets'],cwd=WORK/'lint',negative=True,contains='unused dependency')
    (WORK/'lint/src/main.rs').write_text('fn main(){assert_eq!(unused_dep::value(),1);}\n')
    command('cargo-unused-positive',['cargo','+1.100.0','check','--offline','--all-targets'],cwd=WORK/'lint')
    command('cargo-build-dir-json',['cargo','+1.100.0','build','--offline','--message-format=json','--config','build.build-dir="native-build-cache"'],cwd=WORK/'lint')
    artifacts=[json.loads(l) for l in (OUT/'cargo-build-dir-json.stdout').read_text().splitlines() if l.startswith('{')]
    found=[p for m in artifacts if m.get('reason')=='compiler-artifact' for p in m.get('filenames',[]) if Path(p).is_file()]
    assert found,'No supported JSON artifacts found'
    (OUT/'json-artifacts.json').write_text(json.dumps(found,indent=2)+'\n')
    finished=True
finally:
    result={'source_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'os':platform.system(),'arch':platform.machine(),'all_expected_results':finished and all(x['passed'] for x in rows),'commands':rows,'test_source_sha256':hashlib.sha256((ROOT/'stable_tests.rs').read_bytes()).hexdigest(),'scope':'New stable API/compiler fixtures; no AOT/production/independent review/performance claim'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
