"""Index three newly authored existing D tasks; no acceptance or status inflation."""
from pathlib import Path
import hashlib,json,re,subprocess,os
root=Path.cwd();p=root/'docs/contracts/registry.json';data=json.loads(p.read_text())
scopes={'C-PLATFORM-001':'docs/platforms/support-and-aot.md','C-ABI-001':'docs/contracts/abi-v0.1.md','C-BUFFER-001':'docs/contracts/buffer-v0.1.md'}
for contract in data['contracts']:
 if contract['id'] not in scopes:continue
 assert contract['status']=='proposed' and contract['version']=='0.1.0-draft'
 assert contract['spec_path'] in (None,scopes[contract['id']])
 path=scopes[contract['id']]
 contract.update(spec_path=path,content_sha256=hashlib.sha256((root/path).read_bytes()).hexdigest(),author='recovery_native_slices_author',specification_status='authored_proposed_partial_execution',evidence=['docs/research/topics/R03/native-slice-validation.md','docs/traceability/native-slices-recovery.md'],reviews=[],reviewers=[])
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
# Every declared contract hash, not just the three additions, must still match.
checked=[]
for c in data['contracts']:
 if c.get('spec_path') and c.get('content_sha256'):
  assert hashlib.sha256((root/c['spec_path']).read_bytes()).hexdigest()==c['content_sha256'],c['id']
  checked.append(c['id'])
files=list(scopes.values())+['docs/research/topics/R03/native-slice-validation.md','docs/research/topics/R22/native-slice-validation.md','docs/research/topics/R27/native-slice-validation.md','docs/traceability/native-slices-recovery.md']
for rel in files:
 for target in re.findall(r'\]\(([^)]+)\)',(root/rel).read_text()):
  if '://' in target or target.startswith('#'):continue
  assert ((root/rel).parent/target.split('#')[0]).exists(),(rel,target)
report={'input_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'newly_authored_contracts':list(scopes),'checked_contract_hashes':checked,'contract_status':'all remain proposed','independent_review':False,'relative_links_ok':True,'formal_delivery_acceptance':False}
(root/'docs/traceability/native-slices-doc-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
