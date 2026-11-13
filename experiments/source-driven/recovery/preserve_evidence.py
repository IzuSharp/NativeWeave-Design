"""Preserve exact existing artifacts; never execute the recovered AOT probe.
Only the NEW finite Python admission model is replayed by this workflow.
"""
from pathlib import Path
import datetime,hashlib,io,json,os,subprocess,sys,urllib.request,urllib.error,zipfile
ROOT=Path.cwd();OUT=ROOT/'docs/research/source-driven-evidence';OUT.mkdir(parents=True,exist_ok=True)
ARTIFACTS=[(43242624552,13954862179,'defda5e08a309dec167ef1c517b3a9d2f1d316215bd8265e3a3fa3c1b5724372'),(43245931319,13956034512,'e0af8616e6ee31fb8fb6dcc5c1cffc6aae9bc4862db1296e110b65aae52e7199'),(43245931319,13957435482,'341d43c19e6c90597f78c584fa63f5ef6ea952a478ad627c2e83cfadffbb5be7')]
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
def download(aid):
 cache=os.environ.get('NW_RECOVERY_ARTIFACT_DIR')
 if cache:return (Path(cache)/f'{aid}.zip').read_bytes()
 url=f'https://api.github.com/repos/IzuSharp/NativeWeave-Design/actions/artifacts/{aid}/zip'
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
 try:
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=120) as response:return response.read()
 except urllib.error.HTTPError as error:
  if error.code not in (301,302,303,307,308):raise
  target=error.headers['Location']
  if not target.startswith('https://'):raise RuntimeError('Unsafe artifact redirect')
  # Do not forward a repository token to the storage redirect host.
  with urllib.request.urlopen(target,timeout=120) as response:return response.read()
archives=[]
for run,aid,expected in ARTIFACTS:
 raw=download(aid)
 if hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('Artifact hash mismatch '+str(aid))
 archives.append(zipfile.ZipFile(io.BytesIO(raw)))
source,corrected,probe=archives
records=[]
def preserve(name,data,origin):
 path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);data.decode('utf-8');path.write_bytes(data)
 records.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'origin':origin})
for name in probe.namelist():
 if name.startswith('evidence/'):
  preserve(name.split('/',1)[1],probe.read(name),'Recovered original artifact 13957435482, not rerun')
 elif name in ['probe.py','probe-resolved.py'] or (name.startswith('work/') and not name.startswith('work/feed/')):
  preserve('probe-inputs/'+name,probe.read(name),'Recovered original prototype input, not production code')
preserve('source-lock.json',source.read('source-lock.json'),'Original source collection artifact 13954862179')
preserve('corrected-pins.json',corrected.read('corrected-pins.json'),'Corrected source identities artifact 13956034512')
package=zipfile.ZipFile(io.BytesIO(probe.read('work/feed/NativeWeave.SourceProbe.0.0.1.nupkg')))
assets=[n for n in package.namelist() if n.startswith('runtimes/linux-x64/native/') and n.endswith('.so')]
assert len(assets)==1,assets
native_hash=hashlib.sha256(package.read(assets[0])).hexdigest()
assert native_hash=='e47fee8b949599ed5430af36aa403f7782b33d7402b249709c71e50f74dad52e'
# Curated source ranges read by the recovery author; downloading is not review.
READS={
'SeaQL/sea-query':{
'src/query/select.rs':[[40,100],[2150,2205],[2500,2570]],'src/query/insert.rs':[[40,80],[220,275],[480,530]],'src/query/update.rs':[[35,75]],'src/query/delete.rs':[[30,74]],'src/query/condition.rs':[[1,95],[120,190]],'src/expr/enum.rs':[[1,56]],'src/types/iden/core.rs':[[1,139]],'src/backend/sqlite/query.rs':[[1,101]],'sea-query-sqlx/src/sqlx.rs':[[1,28]],'sea-query-sqlx/src/sqlx_sqlite.rs':[[1,65],[123,155]],'src/backend/postgres/query.rs':[[1,40],[359,385]],'src/value.rs':[[231,320]],'src/query/traits.rs':[[1,32],[75,92]],'src/backend/query_builder.rs':[[124,233],[886,945],[1639,1728]],'src/query/window.rs':[[65,110]],'src/query/with.rs':[[439,475]],'tests/postgres/query.rs':[[90,166],[921,998],[1052,1115]],'tests/sqlite/query.rs':[[325,350],[1013,1067]],'tests/error.rs':[[1,19]]},
'SeaQL/sea-orm':{'src/entity/base_entity.rs':[[57,140]],'src/entity/active_model.rs':[[210,238],[337,402]],'src/database/connection.rs':[[1,88],[181,216]]},
 'transact-rs/sqlx':{'sqlx-core/src/transaction.rs':[[112,138],[263,284]],'sqlx-core/src/pool/connection.rs':[[76,115],[195,215],[275,330]]},
 'hyperium/hyper':{'src/service/service.rs':[[15,64]],'src/ffi/mod.rs':[[1,99]],'src/server/conn/http1.rs':[[123,145],[392,409],[439,458],[470,523]],'src/body/incoming.rs':[[147,208]]},
 'tower-rs/tower':{'tower/src/limit/concurrency/service.rs':[[58,96]],'tower/src/limit/concurrency/future.rs':[[1,40]],'tower/tests/limit/concurrency.rs':[[152,193]]},
 'tokio-rs/axum':{'axum/src/serve/mod.rs':[[267,305],[353,420]]},
 'tokio-rs/tokio':{'tokio/src/runtime/runtime.rs':[[28,61],[447,475]]},
 'actix/actix-net':{'actix-server/src/worker.rs':[[71,107],[143,180]]},
 'actix/actix-web':{'actix-web/src/server.rs':[[149,229]]},
 'rustls/rustls':{'rustls/src/conn.rs':[[443,458],[510,546]]},
 'cloudflare/pingora':{'pingora-proxy/src/proxy_trait.rs':[[48,118]]}}
lock=json.loads(source.read('source-lock.json'));cor=json.loads(corrected.read('corrected-pins.json'))
pins={p['repository']:p for p in lock['upstreams']};cpins={p['repository']:p for p in cor['sources']};pins.update(cpins)
inspection=[]
for repo,files in READS.items():
 pin=pins[repo];z=corrected if repo in cpins else source
 for name,ranges in files.items():
  key=('' if repo in cpins else 'upstream/')+repo.replace('/','__')+'/'+name;data=z.read(key);lines=data.decode().splitlines()
  assert all(0<a<=b<=len(lines) for a,b in ranges),(key,len(lines),ranges)
  inspection.append({'repository':repo,'tag':pin['tag'],'commit':pin['commit'],'path':name,'line_ranges':ranges,'file_sha256':hashlib.sha256(data).hexdigest(),'url':f"https://github.com/{repo}/blob/{pin['commit']}/{name}",'review':'recovery-author selected source inspection; not independent review','upstream_test_execution':'not executed in recovery'})
def write_json(p,data):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
write_json(OUT/'source-inspection.json',{'scope':'Selected mechanisms used in R25/R27; not full repository audit. Tests read are not tests executed. Git snapshots are not automatically identical to registry crates in Cargo.lock.','records':inspection})
write_json(OUT/'recovery-manifest.json',{'date':'2026-11-12','design_main':'baa953772d2a771bb4da3aff0cf4b4be6fc811a1','plan_main':'da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5','existing_pr':5,'recovered_head':'16e673b1077f6784936703f4c4dc38b46b4d058b','preservation_input_commit':os.environ.get('GITHUB_SHA'),'artifacts':[{'run_id':r,'artifact_id':a,'zip_sha256':h} for r,a,h in ARTIFACTS],'preserved_files':records,'native_asset_sha256':native_hash,'subagent_results':'Six separately attributable completed outputs not recovered in current accessible records','independent_review':'pending; not simulated','original_aot_probe_rerun':False})
# Replay only the NEW finite model, preserving exact source/output and scope.
model=ROOT/'docs/research/topics/R27/body_lease_model.py'
run=subprocess.run([sys.executable,str(model)],capture_output=True,text=True,timeout=30)
if run.returncode:raise RuntimeError(run.stderr)
result=json.loads(run.stdout)
write_json(model.with_name('body-lease-result.json'),result)
write_json(OUT/'recovery-model-run.json',{'command':[sys.executable,str(model.relative_to(ROOT))],'exit_code':run.returncode,'python':sys.version,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'stdout_sha256':hashlib.sha256(run.stdout.encode()).hexdigest(),'stdout':run.stdout,'stderr':run.stderr,'execution':'New finite model replay by recovery CI; not an independent review or replay of original AOT probe','github_run_id':os.environ.get('GITHUB_RUN_ID')})
# Complete baseline inventories classify scope without pretending all historical prose was reread.
inventory=[]
for name in source.namelist():
 if name.startswith('baseline/NativeWeave-Design/'):
  rel=name[len('baseline/NativeWeave-Design/'):];now=ROOT/rel
  inventory.append({'repository':'NativeWeave-Design','path':rel,'baseline_sha256':hashlib.sha256(source.read(name)).hexdigest(),'disposition':'amended' if now.exists() and now.read_bytes()!=source.read(name) else 'preserved_historical_or_unaffected','review_scope':'selected affected requirements/specifications; remaining historical source evidence retained, not a new whole-file audit'})
for kind in ['research','documentation','delivery']:
 graph=json.loads(source.read(f'baseline/Plan/{kind}-graph.json'))
 for n in graph['nodes']:inventory.append({'repository':'Plan','task_id':n['id'],'packet':n['prompt'],'disposition':'existing ID retained; paired source-driven revision required','review_scope':'graph/packet metadata and domain impact, not product completion'})
write_json(ROOT/'docs/traceability/source-driven-inventory.json',{'baseline_design':'baa953772d2a771bb4da3aff0cf4b4be6fc811a1','baseline_plan':'da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5','items':inventory})
impact='''# Source-driven integration: recovery, impact and independent-review handoff

Status: proposed amendment in existing Design PR #5. No product-source implementation or automatic final acceptance. Exact source pins/ranges, preserved commands/logs and file hashes are in `docs/research/source-driven-evidence/`. The paired Plan PR must pin the resulting Design commit; the two repositories are not an atomic transaction.

## Recovered versus missing

Recovered the complete baseline archives, pinned source snapshots, corrected SQLx/Actix source identities and successful query feasibility artifact. Reused existing commits/PR and the actual Linux x64/SQLite Native AOT experiment; it was not rerun. The earlier failed SQLx API attempt remains in Actions history. Native asset hash equality, second entity and expected type-error fixture were rechecked from recovered records. Raw logs and source are persisted before temporary artifact expiry.

Six separately attributable completed subagent reports were not found in the currently accessible records. There is no callable subagent interface in the recovery session. No independent review is fabricated. PR2–4 historical reviews apply only to their original bytes. New source inspection, integration, finite model and structural tests are author-side evidence.

## Concrete conflicts, corrections and retained obligations

| Finding | Previous conflict / omission | Revision | Existing tasks |
|---|---|---|---|
| SDI-01 | Merged DB required static SeaORM models and per-schema Rust rebuilds | Precompiled dynamic SeaQuery+SQLx ordinary candidate; static SeaORM specialized | R19–R25, D14–D17, B01–B14 |
| SDI-02 | Plan still had managed PostgreSQL and optional native DB | Mandatory Rust providers/host, no managed product fallback; B04 required in composition | D27/D30, B01–B08/B21–B24 |
| SDI-03 | Declaration-only LINQ/IR pipeline and managed SQL semantics exceeded requested experience | Typed native-backed Fluent, SQL semantics, optional static descriptor/DTO generation; no complete C# SQL engine | R06/R23/R24/R25, D16/D17, B09–B14 |
| SDI-04 | Public binding alone understated reusable native structure and maintenance choices | Source-informed public seams, justified extension/fork ladder, small Core and exact upstream maps | R03–R10/R14/R18, D02–D11, A13–A16/A22/A24 |
| SDI-05 | Passing through a mature builder could silently lose semantics | SQLite unsupported clauses explicitly rejected; CTE/value validation and fallible argument encoding | R16/R22/R24, D14/D16, B07/B11/B13 |
| SDI-06 | Generic Server adaptation did not state native Service/Body reuse precisely | ForeignService plus native connection/body ownership, Actix affinity and proxy alternatives; Kestrel baseline retained | R26–R31, D18/D20, B16/B17/B20/B22 |
| SDI-07 | Response-future/protocol credit could be mistaken for lifetime/RSS bounds | Body/callback lease and retained-byte budgets; shutdown timeout never retires native owners | R09/R10/R29, D06/D07/D18, B16/B17/B22 |
| SDI-08 | Maintainer native builds and ordinary entity builds were coupled | NuGet precompiled assets, clean Rust-free/RID-free development tests; native hash remains same for supported model variation | R13/R14, D10/D17, A13–A16/B10/B24 |
| SDI-09 | Upstream/patch updates lacked explicit source seam/behavior compatibility duty | Pins, Cargo closure/features, patch queue, semantic differential/performance gates and fork retirement | R14/R18, D10/D11, A22/A24/B24 |
| SDI-10 | Existing acceptance metadata could outlive changed design bytes | Eight contracts revised as proposed with actual hashes; all114 Plan packet/pin revisions, real independent review still pending | D31/D32 |

Retain ownership, callback quiescence, cancellation versus retirement, Unknown COMMIT, fixed-session admission, rollback confirmation, pool quarantine, SQL null/collation/CAS, atomic idempotency/outbox and bounded telemetry. Historical source findings are not deleted merely because the default integration route changes. No unrelated GPU/mobile implementation or global Core runtime is added.

## Evidence and limits

R25/R27 record selected source call chains and relevant tests. Source tests were read, not executed by this recovery. The original registry-crate Cargo.lock is distinct from inspected Git source pins. The recovered prototype demonstrates real Linux AOT execution and reuse for a second entity, but used explicit RID, handwritten mappings, PATH Rust-denial shims and research-only synchronous JSON/fetch_all/per-call runtime shortcuts. It does not prove clean-machine or RID-free consumer behavior, PostgreSQL execution, Windows, a source generator, production streaming/concurrency, full ORM coverage or performance superiority.

The newly executed two-request admission model finds a response-head-only permit counterexample and no violation in the finite body-and-callback policy model. It is not a Hyper/Tower run, byte/RSS proof, weak-memory model, liveness proof or independent review. Precise counts and command hashes are in the preserved result.

## Design answers versus gates

Q11/Q13's universal per-entity Rust build/full-LINQ assumptions are answered negatively for the dynamic profile, with source and finite execution evidence. Independent architectural acceptance, real implementation and production release gates stay separate. Q14 backend semantics, Q15 Server value and Q16 real resource safety remain scoped obligations. Preserve all applicable Windows/Linux AOT, race/property/fuzz/model, fault/soak, compatibility and workload tests in the existing Delivery tasks.

## Independent-review entry and disjoint continuation

Use the existing `IzuSharp/Plan:prompts/independent-review.md`, current R25/R27 packets and D10/D11/D14–D18 packets; record exact Design and Plan commits and packet hashes before reviewing. One independent reviewer should verify dynamic identifiers/AST/parameters, SeaORM's static boundary, missing ORM policies and no-Cargo consumer claims. A second can inspect ForeignService/body/worker affinity, credit/retirement and shutdown traps. A third can check packaging, source/patch maintenance and all graph/contract/packet pins. These are reusable existing task scopes, not claimed active agents or a new coordination graph.

Review every changed contract at its new content hash, retain finite evidence limits, reject unsafe silent backend behavior and identify avoidable translation/runtime layers. Record finding IDs/severity/evidence/fixes and re-read final bytes. Do not approve merely because structural checks pass, reuse old PR approvals, or merge until the actual independent-review requirement and effective repository checks are satisfied. Product implementation remains unauthorized.
'''
(ROOT/'docs/traceability/source-driven-impact.md').write_text(impact)
# Fail on broken relative Markdown file links in amendment documents.
import re
check_paths=['docs/decisions/ADR-0002-source-driven-native-integration.md','docs/extension/engine-integration.md','docs/platforms/build-package-release.md','docs/database/drivers.md','docs/database/query-semantics.md','docs/generators/query-generation.md','docs/research/topics/R25/source-driven-seaquery.md','docs/research/topics/R27/source-driven-server.md']
missing=[]
for rel in check_paths:
 p=ROOT/rel
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  q=(p.parent/target.split('#')[0])
  if not q.exists():missing.append((rel,target))
assert not missing,missing
print(json.dumps({'preserved_files':len(records),'inspected_source_files':len(inspection),'baseline_inventory_items':len(inventory),'native_asset_sha256':native_hash,'model':result,'independent_review':'pending'},ensure_ascii=False))
