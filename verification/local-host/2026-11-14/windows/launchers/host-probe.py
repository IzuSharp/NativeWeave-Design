from pathlib import Path
import datetime,json,os,platform,shutil,subprocess,sys
commands={}
for name,argv in [('dotnet',['dotnet','--version']),('rustc',['rustc','-Vv']),('cargo',['cargo','-V'])]:
 r=subprocess.run(argv,capture_output=True); commands[name]={'argv':argv,'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}
record={'record_kind':'actual_windows_mcp_preflight','captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'os':platform.platform(),'machine':platform.machine(),'python':sys.version,'tools':{name:{'selected':shutil.which(name),'resolved':str(Path(shutil.which(name)).resolve())} for name in ['dotnet','rustc','cargo','python','cl','link']},'necessary_environment':{name:os.environ.get(name) for name in ['DOTNET_ROOT','Platform','VCToolsVersion','WindowsSDKVersion','VSCMD_ARG_TGT_ARCH']},'versions':commands}
Path('verification/local-host/2026-11-14/windows/host-environment.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'os':record['os'],'python':platform.python_version(),'Platform':record['necessary_environment']['Platform'],'VCToolsVersion':record['necessary_environment']['VCToolsVersion']}))
