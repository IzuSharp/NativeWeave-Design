"""One-shot migration of the observed NativeWeave PR1 snapshot into Design.
Reads the source repository only. No experiment is executed by this script.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
D=Path.cwd(); S=Path(sys.argv[1]).resolve()
HEAD='267364a440074a61e193cf33315f1b9d0fa8126b'
BASE='658ed6a410783de356a7b9b2cd6601336fff5148'
DESIGN_BASE='4adf7a38c3159c9e12e2f89b85884514a430f0a4'
def git(*args):return subprocess.check_output(['git','-C',str(S),*args])
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert (D/'LICENSE').read_bytes()==git('show',HEAD+':LICENSE'),'license preimage mismatch'
raw=git('diff','--name-status',BASE,HEAD).decode().splitlines()
assert len(raw)==139 and all(x.startswith('A\t') for x in raw),'unexpected PR inventory'
manifest_path=D/'verification/native-slices/migration-map.json'
assert not manifest_path.exists(),'migration already present; verify rather than repeat'
records=[]
for line in raw:
 old=line.split('\t')[1]
 before=git('show',HEAD+':'+old); after=before; reason='byte-exact relocation'
 if old.startswith('verification/native-slices/'):
  new=old.replace('verification/native-slices/','verification/native-slices/original-pr1/',1)
 elif old.startswith('.github/workflows/'):
  new='experiments/native-slices/provenance/workflows/'+Path(old).name
  reason='byte-exact historical workflow; inactive outside .github; new Design workflow replaces execution'
 elif old=='tools/preserve_native_slice_evidence.py':
  new='experiments/native-slices/provenance/preserve_native_slice_evidence.py'
  reason='byte-exact historical artifact collector; not executed as current workflow'
 elif old=='.gitattributes':
  new='experiments/native-slices/provenance/original.gitattributes'
 elif old=='experiments/interop/README.md':
  new='experiments/native-slices/provenance/interop-original-README.md'
 elif old=='experiments/DOMAIN-SLICES.md':
  new='experiments/native-slices/provenance/DOMAIN-SLICES.original.md'
 elif old.startswith('experiments/'):
  new=old.replace('experiments/','experiments/native-slices/',1)
 elif old in ('.gitignore','global.json','rust-toolchain.toml'):
  new='experiments/native-slices/'+old
 else:raise RuntimeError('unmapped source file '+old)
 if old=='experiments/interop/run.py':
  text=before.decode();assert text.count('parents[2]')==1
  text=text.replace('parents[2]','parents[1]').replace('experiments/interop','interop')
  after=text.encode();reason='relocate experiment root and interop paths only; test semantics unchanged'
 if old=='experiments/run_domains.py':
  text=before.decode();assert text.count('parents[1]')==1
  text=text.replace('parents[1]','parent').replace("crate=ROOT/'experiments'/name","crate=ROOT/name")
  after=text.encode();reason='relocate experiment root and domain crate paths only; test semantics unchanged'
 dest=D/new;assert not dest.exists(),new
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(after)
 mode=git('ls-tree',HEAD,'--',old).decode().split()[0]
 assert mode=='100644',('unexpected mode',old,mode)
 records.append({'source_path':old,'source_commit':HEAD,'source_blob_sha1':blob(before),'source_sha256':sha(before),'destination_path':new,'destination_blob_sha1':blob(after),'destination_sha256':sha(after),'byte_exact':before==after,'disposition':reason})
assert len({r['destination_path'] for r in records})==139
mapping={r['source_path']:r for r in records}
original=json.loads((D/mapping['verification/native-slices/manifest.json']['destination_path']).read_text())
verified=0
for rec in original['records']:
 for entry in rec['files']:
  r=mapping[entry['path']]
  assert r['byte_exact'] and sha((D/r['destination_path']).read_bytes())==entry['sha256']
  verified+=1
assert verified==112 and len(original['records'])==8 and sum(r['success'] for r in original['records'])==6
report={'source_repository':'IzuSharp/NativeWeave','source_pr':1,'source_head':HEAD,'source_base':BASE,'design_base':DESIGN_BASE,'migration_script_commit':os.environ.get('GITHUB_SHA'),'migration_run':os.environ.get('GITHUB_RUN_ID'),'mapped_files':len(records),'byte_exact_files':sum(r['byte_exact'] for r in records),'adapted_files':sum(not r['byte_exact'] for r in records),'original_raw_evidence_verified':verified,'original_records':8,'original_success_records':6,'original_failed_attempts':2,'new_execution_status':'pending separate migration jobs','independent_review':False,'product_delivery_executed':False,'records':records}
manifest_path.parent.mkdir(parents=True,exist_ok=True);manifest_path.write_text(json.dumps(report,indent=2)+'\n')
# Ensure Windows checkout never normalizes historical/new raw evidence.
p=D/'.gitattributes';text=p.read_text() if p.exists() else ''
rule='verification/native-slices/** -text'
if rule not in text:p.write_text(text.rstrip()+'\n'+rule+'\n')
phase='''# Current phase: research, detailed design and future Codex planning

The latest user instruction supersedes earlier permission to start product implementation.
Research code, prototypes, Cargo/.NET projects, Actions and raw evidence belong in
NativeWeave-Design. Plan owns the existing R/D/A/B task graphs and future implementation
instructions; it does not duplicate executable research projects. NativeWeave is the
future product repository and is read-only in this phase, except closing PR1 after the
Design and Plan migration PRs have merged and preservation is verified. Never merge PR1,
delete its branch/history, change its main, license or protection, or execute formal A/B
Delivery work. A ready design or successful prototype does not grant product permission.

Continue source-driven deep native integration, mandatory Rust Database lower layers,
natural typed C# Fluent and precompiled ordinary-entity reuse; no complete managed SQL
provider or mandatory per-entity Cargo. Server remains evidence-selected, independent of
Database and without a mandatory global Core runtime. Research experiments may compile
and execute on actual Windows/Linux with Native AOT. Self-review is not independent
review; document integration does not automatically accept proposed technical contracts.

Use the existing34 R /32 D /48 candidate Delivery IDs. Apply precise local changes and
persist evidence, including failures. Existing verified design decisions may be recorded
without pretending future product validation is complete. Future Codex implementation is
separate and awaits the user's later transition plus actual accepted task prerequisites.
'''
(D/'CURRENT-PHASE.md').write_text(phase)
p=D/'AGENTS.md';text=p.read_text();text=text.replace('下一阶段按实际任务/契约门禁实施，不再沿用旧的全面禁止研究会话执行代码。','当前阶段以 CURRENT-PHASE.md 为准：只推进研究、真实实验、详细设计与未来 Codex 规划；不执行正式 Delivery，不写 NativeWeave 产品源码。')
text=text.replace('本仓库保存研究、候选规范和 accepted 规范；实现仓库是 IzuSharp/NativeWeave，任务和执行状态在 IzuSharp/Plan。','本仓库保存研究、候选规范、accepted 规范及全部研究实验和原始证据；未来实现仓库是 IzuSharp/NativeWeave，任务和执行状态在 IzuSharp/Plan。当前阶段边界见 [CURRENT-PHASE.md](CURRENT-PHASE.md)。')
p.write_text(text)
p=D/'README.md';text=p.read_text();p.write_text('> **Current phase:** research and detailed design, not product implementation. All executable research assets belong here. See [CURRENT-PHASE.md](CURRENT-PHASE.md) and [migration provenance](docs/traceability/research-asset-migration.md).\n\n'+text)
notes=['docs/research/topics/R03/native-slice-validation.md','docs/research/topics/R22/native-slice-validation.md','docs/research/topics/R27/native-slice-validation.md','docs/traceability/native-slices-recovery.md']
for rel in notes:
 p=D/rel;old=p.read_text();p.write_text('> **Research asset location correction:** these historical execution identities remain unchanged. Current source is `experiments/native-slices/` and original evidence is `verification/native-slices/original-pr1/` in NativeWeave-Design. See `docs/traceability/research-asset-migration.md` and its per-file mapping. No formal product implementation is authorized in this phase.\n\n'+old)
print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
