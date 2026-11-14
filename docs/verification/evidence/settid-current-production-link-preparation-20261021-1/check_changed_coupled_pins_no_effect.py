"""Bounded actual-body prefix checks; no materialization/compiler/root/ownership.
Run only once under root's genuine ordinary grant. Reads frozen metadata/four
inputs and genuine old authority; writes only one new private result receipt.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,re,sys
R=Path(__file__).resolve().parent
B=Path('/home/holden/mckernel-work/host-preparation/phase5-opt-in-image-lock-binding-20261020-1/panic-free-full-image-correction-1')
A=B/'source-materialization-1/image-execution-preparation-1'
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def need(v,s):
 if not v:raise RuntimeError(s)
def actual_function(path,name,ns,truncate=None):
 tree=ast.parse(path.read_text());fn=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
 if truncate is not None:fn.body=truncate(fn.body);ast.fix_missing_locations(fn)
 exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
 return ns[name]
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12)
assert Path('/').is_relative_to(Path('/')) and not Path('/outside').is_relative_to(Path('/inside'))
m=load(R/'thin-inputs.json');q=load(R/'image-request-UNMATERIALIZED-PROPOSAL.json');patch=load(R/'EXACT-SOURCE-PATCH-AUTHORITY.json');changed=[]
for item in patch['overlays']:
 p=Path(item['input']['path']);assert p.stat().st_size==item['input']['bytes'] and sha(p)==item['input']['sha256'];changed.append(item['relative'])
assert len(changed)==4 and q['source_identity'] is None and q['disk_identity'] is None
assert q['source_manifest']==str(R/'thin-inputs.json') and q['source_manifest_sha256']==sha(R/'thin-inputs.json')
assert q['provenance_path']==str(R/'native_rust_exact_build_offline.py') and q['provenance_sha256']==sha(R/'native_rust_exact_build_offline.py')
assert q['driver_path']==str(R/'native_rust_exact_mckernel_image_offline.py') and q['driver_sha256']==sha(R/'native_rust_exact_mckernel_image_offline.py')
assert q['gitlink_manifest']==str(R/'gitlink-inputs.json') and q['gitlink_manifest_sha256']==sha(R/'gitlink-inputs.json')
assert q['source_derivative_sha256']==m['source_derivative_sha256'] and q['materialization_sha256']==m['materialization_sha256']
# Execute exact independently reviewable contract bodies, never broad source validation.
ns={'_thin_require':need,'_thin_digest':lambda b:hashlib.sha256(b).hexdigest(),'_thin_canonical':canonical}
for p in [R/'thin_source_contract.py',R/'native_rust_exact_build_offline.py']:
 tree=ast.parse(p.read_text())
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['THIN_SCHEMA','BASE_CANDIDATE','BASE_IHK','EXPECTED_SUCCESSOR_CANONICAL_SHA256'] for t in node.targets):exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns)
 fn=actual_function(p,'validate_thin_document',ns);files,metadata=fn(m,q['candidate_sha'],q['ihk_sha']);assert files==m['materialized_repository_files'] and metadata==m['retained_ihk_git_metadata']
 try:fn(load(B/'thin-inputs.json'),q['candidate_sha'],q['ihk_sha'])
 except RuntimeError as e:assert str(e)=='exact independently reviewed cutover authority required'
 else:raise AssertionError('stale canonical source manifest accepted')
# Execute original actual gitlink validator through its metadata prefix, stopping
# immediately before checkout/Git operations. No invented providers/tree proof.
ns={'_json':lambda p,label:load(p),'_fail':need,'_sha256':sha,'re':re}
def before_root(body):
 i=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='root' for t in n.targets))
 return body[:i]+[ast.Return(value=ast.Constant(value=True))]
fn=actual_function(R/'native_rust_exact_mckernel_image_offline.py','_validate_gitlink_closure',ns,before_root)
assert fn(Path('/UNMATERIALIZED'),R/'gitlink-inputs.json',R/'thin-inputs.json',q['candidate_sha'],q['ihk_sha'],None)
try:fn(Path('/UNMATERIALIZED'),B/'gitlink-inputs.json',R/'thin-inputs.json',q['candidate_sha'],q['ihk_sha'],None)
except RuntimeError as e:assert str(e)=='gitlink base manifest hash differs'
else:raise AssertionError('stale supplemental manifest accepted')
# Actual guard authentication first predicate rejects genuine old authority.
# No synthetic PASS release, new source report, locks/findmnt or owner invocation.
g=R/'image-execution-preparation-1/native_exact_current_optin_image_guard.py';tree=ast.parse(g.read_text());ns={'os':os,'Path':Path,'ROOT':Path('/home/holden/mckernel-work/scratch'),'CANDIDATE':q['candidate_sha'],'UUID':'2a5768c8-718d-4914-bdc0-6b32c5a92a52','bound':lambda p:load(p['path'])}
fn=actual_function(g,'authenticate',ns,lambda body:body[:3]+[ast.Return(value=ast.Constant(value=True))])
oldrelease=load(A/'image-execution-release.json')
try:fn(Path(oldrelease['request']['path']),oldrelease['request']['sha256'],A/'image-execution-release.json',sha(A/'image-execution-release.json'))
except RuntimeError as e:assert str(e)=='fresh exact authority3 image release required'
else:raise AssertionError('successor guard accepted predecessor release')
strings={n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
assert m['source_derivative_sha256'] in strings and m['materialization_sha256'] in strings
# Owner provenance pin and source materializer mapping are exact static joins.
owner=ast.parse((R/'native_rust_exact_mckernel_image_container_owner.py').read_text());pins={n.targets[0].id:ast.literal_eval(n.value) for n in owner.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['EXPECTED_DRIVER_SHA256','EXPECTED_PROVENANCE_SHA256','COMMON_EXCLUSION']}
assert pins['EXPECTED_DRIVER_SHA256']==q['driver_sha256'] and pins['EXPECTED_PROVENANCE_SHA256']==q['provenance_sha256'] and pins['COMMON_EXCLUSION']==q['common_exclusion_path']
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_BOUNDED_CHANGED_COUPLED_PINS_AND_ACTUAL_METADATA_PREFIXES_ONLY','actual_contract_successor_passes':2,'actual_contract_predecessor_refusals':2,'actual_gitlink_prefix_successor_passes':1,'actual_gitlink_stale_base_refusals':1,'actual_guard_genuine_old_release_refusals':1,'four_current_input_pins_verified':changed,'Python_Path_capability':True,'source_materialized':False,'compiler_or_root_or_Docker_or_lease':False,'synthetic_execution_authority':False,'future_actual_source_runtime_auth_acceptance':None}
with (R/'CHANGED-COUPLED-PINS-NO-EFFECT-RESULT.json').open('x') as out:out.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result))
