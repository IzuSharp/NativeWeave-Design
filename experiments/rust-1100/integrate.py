#!/usr/bin/env python3
"""One-time preimage-checked Design integration. Only documentation is committed.
Preserve existing successful runs; do not rerun the old query/AOT prototype.
"""
from pathlib import Path
import datetime,hashlib,io,json,os,re,sqlite3,urllib.request,urllib.error,zipfile
ROOT=Path.cwd();OUT=ROOT/'docs/research/topics/R01/rust-1100-evidence';OUT.mkdir(parents=True,exist_ok=True)
PRE={
'AGENTS.md':'8b7c78ea470cc72e6502d578f89823bd2eb9682a15672dd42432719ea5d22a0b',
'docs/research/toolchain/report.md':'1b4d04ef96aacdd30fbfac0a605263b210ebcfecb92fefb12670b1f14e4d3bed',
'docs/platforms/build-package-release.md':'50d442c9bf6b2c29f7a010985e6a83e0e8f09f10749d3b8660f22158e3aa19a3',
'docs/extension/engine-integration.md':'e7e7796662c652e8dde40269f9bcf1143fd28fbdb8d8ef65783f094f822b618c',
'docs/database/query-semantics.md':'ada72b4c580135171a590f27ee54ca53450ef8e6dfd0a3a103a8426b021b0bc1',
'docs/research/topics/R25/source-driven-seaquery.md':'9ffb6e9b05c23fd612dc79d06ad186b709945c7f4bd992c61fad65c7ef08d9ba',
'docs/contracts/registry.json':'04c93d515cd4dc5ebaf3fc49544aacf59c7744c80ddcd1569a06a0c239cac873'}
for p,h in PRE.items():
    if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Preimage changed; reconcile '+p)
def put(p,s):
    p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.rstrip()+'\n',encoding='utf-8')
def data(p,obj):put(p,json.dumps(obj,ensure_ascii=False,indent=2))
def edit(p,fn):put(p,fn((ROOT/p).read_text()))
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**k):return None
def artifact(aid):
    req=urllib.request.Request(f'https://api.github.com/repos/IzuSharp/NativeWeave-Design/actions/artifacts/{aid}/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=120) as r:return r.read()
    except urllib.error.HTTPError as e:
        if e.code not in (301,302,303,307,308):raise
        url=e.headers['Location'];assert url.startswith('https://')
        # Storage redirect must not receive the repository token.
        with urllib.request.urlopen(url,timeout=120) as r:return r.read()
ARS=[('primary',43352016583,14004167752,'92c64c3435cde548e0ce8eeadce7631ab58f12676c35c804034a3153142759b4'),('linux',43352716861,14004931075,'93bbd472740cd99f68f6c7dc942629e403bd1452c74f397ec24e28a7e1b87ef3'),('windows',43352716861,14004626653,'1f8bad1d39f3c5d53348d75d49be7774213ebc0f8f6651b151444ead0c8ceb71'),('followup',43352716861,14004596768,'f803f823ad3a09ce6a33f4318925de95a47010c2e0f983471289998daecf6bd3')]
zips={};saved=[]
for name,run,aid,h in ARS:
    raw=artifact(aid);assert hashlib.sha256(raw).hexdigest()==h,(name,'hash');zips[name]=zipfile.ZipFile(io.BytesIO(raw))
    z=zips[name]
    for key in z.namelist():
        keep=(name in ('linux','windows') and (key.startswith('evidence/') or key.endswith('.rs'))) or (name=='primary' and (key.startswith('environment/') and not key.endswith('.html')))
        if not keep:continue
        b=z.read(key);b.decode('utf-8');p=OUT/name/key;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        saved.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest()})
for osname in ['linux','windows']:
    result=json.loads(zips[osname].read('evidence/result.json'))
    assert result['all_expected_results'] and len(result['commands'])==13
    assert '13 passed; 0 failed' in zips[osname].read('evidence/stable-tests-run.stdout').decode()
    assert result['test_source_sha256']==hashlib.sha256((ROOT/'experiments/rust-1100/stable_tests.rs').read_bytes()).hexdigest()
manifest=json.loads(zips['primary'].read('manifest.json'))
data(OUT.relative_to(ROOT)/'preservation.json',{'input_commit':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],'artifacts':[{'name':n,'run_id':r,'artifact_id':a,'zip_sha256':h} for n,r,a,h in ARS],'preserved_files':saved,'original_query_probe_rerun':False,'independent_review':False})
# Source mechanisms actually inspected by the author; tests read != tests run.
reads={'library/core/src/mem/drop_guard.rs':[[1,170]],'library/core/src/alloc/mod.rs':[[105,202],[276,335]],'library/alloc/src/boxed.rs':[[680,752]],'library/alloc/src/sync.rs':[[1200,1285],[2929,2950]],'library/alloc/src/vec/mod.rs':[[710,775]],'library/core/src/convert/mod.rs':[[890,920]],'compiler/rustc_abi/src/extern_abi.rs':[[60,64]],'RELEASES.md':[[1,165]]}
source_records=[]
rust='0ef1bc386059596dada8fb65b50425aab2ea637a';cargo='3acc79c0c841844675bc53a605922dbfc441e750'
for p,ranges in reads.items():
    b=zips['primary'].read('upstream/rust/'+p)
    source_records.append({'repo':'rust-lang/rust','commit':rust,'path':p,'ranges':ranges,'file_sha256':hashlib.sha256(b).hexdigest(),'coverage':'selected source ranges inspected'})
for p,ranges in {'src/diagnostics/rules/unused_dependencies.rs':[[1,440]],'src/resolver/version_prefs.rs':[[1,320]]}.items():
    url=f'https://raw.githubusercontent.com/rust-lang/cargo/{cargo}/{p}'
    b=urllib.request.urlopen(url,timeout=120).read()
    source_records.append({'repo':'rust-lang/cargo','commit':cargo,'path':p,'ranges':ranges,'file_sha256':hashlib.sha256(b).hexdigest(),'coverage':'connector source reading, not upstream suite execution'})
for key,repo,commit,ranges in [('rust/library/coretests/tests/mem.rs','rust-lang/rust',rust,[[777,822]]),('cargo/doc/book/src/reference/build-cache.md','rust-lang/cargo',cargo,[[1,140]]),('cargo/doc/book/src/reference/config.md','rust-lang/cargo',cargo,[[566,584]]),('cargo/doc/book/src/reference/resolver.md','rust-lang/cargo',cargo,[[313,325]])]:
    b=zips['followup'].read(key);source_records.append({'repo':repo,'commit':commit,'path':key.split('/',1)[1],'ranges':ranges,'file_sha256':hashlib.sha256(b).hexdigest(),'coverage':'read; upstream tests not executed'})
data(OUT.relative_to(ROOT)/'source-inspection.json',{'records':source_records,'limits':'Selected mechanisms only; release-list items not listed as source-inspected are release-note evidence. Registry packages are distinct identities.'})
packages=[]
for key in zips['primary'].namelist():
    if not key.startswith('registry/') or not key.endswith('.json'):continue
    obj=json.loads(zips['primary'].read(key));vs=[v for v in obj['versions'] if not v.get('yanked') and '-' not in v['num']]
    v=vs[0];packages.append({'crate':obj['crate']['name'],'version':v['num'],'rust_version':v.get('rust_version'),'checksum':v.get('checksum'),'published_at':v.get('created_at'),'evidence':'official crates.io metadata; full closure compilation not implied'})
data(OUT.relative_to(ROOT)/'dependency-observations.json',{'observed_at':manifest['created_at'],'packages':packages})
# Correct an actual semantic overstatement with a new, narrowly scoped SQL probe.
con=sqlite3.connect(':memory:');cases=[]
for x in [None,-1,1]:
    for y in [None,-1,1]:
        a,b,c=con.execute('SELECT NOT (? > ?), ? <= ?, NOT COALESCE(? > ?,0)',(x,y,x,y,x,y)).fetchone()
        assert a==b;cases.append({'x':x,'y':y,'sql_not_gt':a,'sql_le':b,'two_valued_compensation':c})
con.close();assert any(r['sql_not_gt']!=r['two_valued_compensation'] for r in cases)
data('docs/research/topics/R24/sql-null-negation-1100.json',{'scope':'Nine nullable-integer SQLite cases only, not all DB types or C# execution','sqlite_version':sqlite3.sqlite_version,'cases':cases,'all_sql_equivalences_passed':True,'compensation_counterexample_found':True,'run_id':os.environ['GITHUB_RUN_ID']})
edit('docs/database/query-semantics.md',lambda s:s.replace('0.2.0-draft','0.2.1-draft').replace('Do not rewrite `NOT(x > y)` into `x <= y` under nullable data or silently wrap every predicate into C# two-valued semantics.','For compatible totally ordered operands, SQL `NOT(x > y)` and `x <= y` both yield UNKNOWN on NULL; nullable data alone does not invalidate that equivalence. Do not silently replace these with C# two-valued null compensation, or generalize the equivalence to NaN/custom partial-order operators. The focused R24 SQLite integer truth-table fixture records this correction.'))
edit('docs/platforms/build-package-release.md',lambda s:s.replace('0.2.0-draft','0.2.1-draft')+'''

## Rust 1.100 maintainer baseline and Cargo changes

Use exact stable Rust/Cargo1.100.0 and edition2024 for new maintainer builds; record `rustc -Vv`, Cargo identity, target and locked dependency closure. Existing historical evidence retains its original compiler. Crates that use the new standard-library APIs declare rust-version1.100; an upstream's lower MSRV is not a claim that the complete NativeWeave feature matrix compiled. See [R01](../research/topics/R01/rust-1.100.md).

Resolve native output via Cargo `--message-format=json` compiler-artifact records; intermediate build-dir layout changed and is not an interface. Separate per-worktree intermediates from final target assets; key reusable caches by toolchain/host/target/profile/features/lockfile. Workspace-path-hash isolation is not a cache hit or concurrency guarantee. Do not run Cargo in C# generators or normal consumers.

Use Cargo's stable unused_dependencies lint for owned crates and deliberate target/feature coverage; dev-dependencies and feature-only dependencies need separate review. Maintainer dependency-update default cooldown is7days (policy choice, not a security guarantee); keep `cargo build/test --locked`. Locked versions and missing publish timestamps are not protected by that age filter. Explicit emergency/security overrides require reviewed provenance, lockfile diff and regression evidence. No automatic production upgrade or blanket nightly feature gate.
''')
edit('docs/extension/engine-integration.md',lambda s:s.replace('0.2.0-draft','0.2.1-draft').replace('actual field layouts come from accepted C-ABI-001','actual field layouts require a future accepted C-ABI-001')+'''

## Rust 1.100 simplification boundaries

Use std::mem::DropGuard instead of duplicate local synchronous rollback guard types when equivalent, with non-panicking/non-blocking actions. It does not retire callbacks or await I/O. Allocator/Vec/Box APIs can retain a per-resource owner; all allocator operations and allocator Drop must not unwind. Preserve the original allocator and layout through raw transfers and native destruction. Outer custom Vec allocation does not account for nested upstream allocations or whole RSS.

Box::map/Arc::map may reduce private conversion glue, but allocation reuse is conditional and cannot preserve a published opaque handle identity or update all shared holders. Vec::from_fn simplifies trusted-size initialization; untrusted sizes still use checked/fallible allocation. `!` is internal only; `extern "custom"` is not the C ABI. Arc::new_in and try_map extensions remain outside the stable core. These rules preserve, rather than replace, D04–D08 ownership and retirement. [R01 source and two-OS probes](../research/topics/R01/rust-1.100.md).
''')
edit('docs/research/toolchain/report.md',lambda s:s.replace('## 1. 当前可证实的稳定基线','> Historical observation below was made before Rust1.100 released. Current Rust source/real-toolchain update: [R01 Rust1.100](../topics/R01/rust-1.100.md). Do not reinterpret old not_run results as new executions.\n\n## 1. 当时可证实的稳定基线'))
edit('docs/research/topics/R25/source-driven-seaquery.md',lambda s:s.replace('## 4. SeaORM versus SQLx, not a predetermined slogan','## 4. SeaORM versus SQLx, not a predetermined slogan\n\nRead the [dynamic-module correction](seaorm-dynamic-boundary.md) with this section: SeaORM is not categorically static-only. Public dynamic projections/connections and a narrow metadata-constructor extension remain real alternatives. Static EntityTrait alone does not disprove a no-Cargo dynamic route.'))
edit('AGENTS.md',lambda s:s.replace('分支与 Draft PR 可在已获授权范围内创建；重大技术决策保持 proposed 直到独立审查。','分支与PR按已有授权推进。2026-11-12用户允许Design PR5/Plan PR2在无可用独立Reviewer时经严格自审和真实检查合并，必须记录未独立审查并保留复审；此例外不改变GitHub强制规则或自动接受proposed产品契约。下一阶段按实际任务/契约门禁实施，不再沿用旧的全面禁止研究会话执行代码。'))
reg=json.loads((ROOT/'docs/contracts/registry.json').read_text())
revised={'C-BUILD-001','C-ENGINE-001','C-QUERY-001'}
linked={'C-LIFETIME-001':'docs/contracts/lifetime-v0.1.md','C-CALLBACK-001':'docs/contracts/callback-v0.1.md','C-ASYNC-001':'docs/contracts/async-v0.1.md','C-ERROR-001':'docs/contracts/error-v0.1.md'}
for c in reg['contracts']:
    if c['id'] in revised:
        c['version']='0.2.1-draft';c['author']='rust1100-integration-author';c['content_sha256']=hashlib.sha256((ROOT/c['spec_path']).read_bytes()).hexdigest();c['evidence'].append('docs/research/topics/R01/rust-1.100.md');c['reviews']=[];c['reviewers']=[]
    if c['id'] in linked:
        c.update(spec_path=linked[c['id']],content_sha256=hashlib.sha256((ROOT/linked[c['id']]).read_bytes()).hexdigest(),author='interop_design',specification_status='existing_review_ready_text_registered_as_proposed')
        c['version_note']='Registry draft label retained; document v0.1.0 text is review-ready, not formally accepted. Original independent review applies only to its original bytes.'
data('docs/contracts/registry.json',reg)
put('docs/traceability/rust-1100-self-review.md','''# Rust1.100 integration self-review — Design PR5 / Plan PR2

Author-side technical review, not independent GitHub approval. The user explicitly permits these documentation PRs to merge after self-review/executable checks when no real independent reviewer is available. GitHub protection is never waived. This does not mark incomplete contracts or Delivery tasks accepted, and D32 retains independent cross-review.

## Findings and disposition

| ID | Severity | Evidence / correction |
|---|---|---|
| RV1100-01 | high | Old Plan execution-policy says B04 optional despite mandatory Rust DB graph. Replace contradictory body; retain optional B17/B18/B19 only. |
| RV1100-02 | medium | acceptance-register still calls all packets0.1.1 and every contract0.1.0. Replace stale live claims with graph/registry authority and dated history. |
| RV1100-03 | medium | D16 incorrectly rejects NOT(x>y) ↔ x<=y solely for nullable operands. Correct SQL3VL versus C# compensation distinction and execute9 nullable-integer SQLite cases. No universal NaN/custom-order claim. |
| RV1100-04 | medium | R25 main comparison omits the later SeaORM dynamic module addendum. Link correction in the actual comparison; no static-only inference. |
| RV1100-05 | medium | Four existing lifecycle/error specs are not indexed. Register current bytes as proposed; do not import old reviews as acceptance or fabricate missing ABI/Buffer specs. |
| RV1100-06 | medium | Research partially_evidenced state was excluded from scheduler readiness. Plan adds a separate continuation set without marking any dependency or Delivery accepted. |
| RV1100-07 | high prevention | Allocator stable does not imply every extension stable. Real E0658 tests for Arc::new_in/try_map; native owner/async retirement remain mandatory. |
| RV1100-08 | medium | Cargo intermediate paths and stale1.99 latest assumption. Adopt artifact JSON, exact1.100 pin, scoped dependency lint/cooldown and preserved historical observations. |

## Scope and evidence

Review includes changed architecture/domain policies, current contract bytes, all114 graph/packet metadata and scoped task refinements, workflow permissions/branch boundaries, recovered evidence provenance and new API fixture sources/logs. It is not a line-by-line re-audit of every historical upstream source snapshot. All original research artifacts and valid safety conditions are retained. No duplicate old C# AOT experiment was run.

Rust collection run43352016583 and API run43352716861 succeeded. Each OS passed13 Rust tests and13 command expectations, including expected failures. These are actual Rust compiler/API probes, not new C# AOT/PG/Server/production evidence. Raw logs are preserved under R01. Source model and algorithmic claims keep explicit limits; no performance superiority is asserted.

Final integration must validate exact post-fix registry hashes, three schemas, packets/dependency pins, existing mutation tests and new continuation/hash negatives, then recheck effective GitHub rules/status/HEAD. Merge Design before Plan and repin Plan to the actual Design merge. Independent review remains a later D32 obligation. Complete production A01–B24 remains gated by precise accepted specifications; actual next research/fixture tasks can proceed without waiting for unrelated domains.
''')
# Hash registration must be exact even while proposed.
for c in reg['contracts']:
    if c.get('spec_path'):assert hashlib.sha256((ROOT/c['spec_path']).read_bytes()).hexdigest()==c['content_sha256']
for p in ROOT.glob('docs/**/*.json'):json.loads(p.read_text())
print(json.dumps({'preserved_logs':len(saved),'rust_tests_per_os':13,'command_expectations_per_os':13,'revised_contracts':sorted(revised),'registered_existing_specs':list(linked),'independent_review':False}))
