"""Execute only new source-binding helper; never import full owner or invoke admission."""
from pathlib import Path
import ast, hashlib, json, stat
P=Path(__file__).resolve().parent
R=Path('/home/holden/mckernel')
proposal=json.loads((P/'ROOT-INTEGRATION-PROVENANCE.PREPARATION.json').read_text())
owner=P/'native_running_external_modules_owner.installed-proposal.py'
tree=ast.parse(owner.read_text())
names={'Refusal','need','safe_path','sha','validate_runtime_source_bindings'}
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
sources=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='SOURCES'))
cohort=P/'private-installed-cohort';cohort.mkdir(mode=0o700)
for name in sources:
 dest=cohort/name;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 source=R/name
 if name.endswith('native_running_external_modules_owner.py'):source=owner
 if name.endswith('native_running_external_modules_offline.py'):source=P/'native_running_external_modules_offline.installed-proposal.py'
 dest.write_bytes(source.read_bytes())
installed=cohort/'scripts/native_running_external_modules_owner.py'
ns={'Path':Path,'hashlib':hashlib,'stat':stat,'REPO':cohort,'SOURCES':sources,'__file__':str(installed)}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(installed),'exec'),ns)
expected=proposal['proposed_installed_runtime_source_sha256']
assert ns['validate_runtime_source_bindings'](expected)==expected
checks=['complete private installed-cohort source map accepted']
def reject(pins,message):
 try:ns['validate_runtime_source_bindings'](pins)
 except ns['Refusal'] as exc:
  assert message in str(exc),(message,str(exc))
 else:raise AssertionError('expected refusal: '+message)
partial=dict(expected);partial.pop(sources[-1]);reject(partial,'complete runtime source closure');checks.append('incomplete runtime source map rejected')
ns['__file__']=str(owner);reject(expected,'executing owner differs');ns['__file__']=str(installed);checks.append('private executing owner outside installed cohort rejected')
leaf=cohort/sources[-1];original=leaf.read_bytes();leaf.write_bytes(original+b'\n')
reject(expected,'reviewed source drift');leaf.write_bytes(original);checks.append('runtime leaf byte drift rejected')
assert ns['validate_runtime_source_bindings'](expected)==expected
prep=json.loads((P/'current68-host-control-sdk-preparation-20261022-1.json').read_text())
def literal_assignments(path):
 result={}
 for n in ast.parse(path.read_text()).body:
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name):
   try:result[n.targets[0].id]=ast.literal_eval(n.value)
   except ValueError:pass
 return result
owner_values=literal_assignments(owner);driver_values=literal_assignments(P/'native_running_external_modules_offline.installed-proposal.py')
expected_map={r['path']:[r['sha256'],r['bytes']] for r in prep['closure']}
assert len(expected_map)==68 and sum(v[1] for v in expected_map.values())==1346042
assert owner_values['EXACT_SOURCE_MAP']==driver_values['EXACT_SOURCE_MAP']==expected_map
assert owner_values['EXACT_DEPENDENCIES']==driver_values['EXACT_DEPENDENCIES']==prep['source_dependency_sets']
checks.append('owner driver manifest exact68 map and 13/49/10 dependency closure agree')
prior=Path(proposal['prior_proposal']['path']).parent
assert (P/'native_running_external_modules_offline.installed-proposal.py').read_bytes()==(prior/'native_running_external_modules_offline.installed-proposal.py').read_bytes()
checks.append('driver unique-provider and unresolved-reference checker bytes unchanged')
result={'status':'PASS_NEW_HELPER_BODY_AND_SOURCE_CONSISTENCY_ONLY','checks':checks,'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','cohort':str(cohort),'cohort_is_repository_publication':False,'whole_owner_imported':False,'admission_invoked':False,'main_invoked':False,'exhausted_loader_family_repeated':False,'actual_installed_consumer_acceptance':None,'actual_module_acceptance':None,'helper_code_filename':ns['validate_runtime_source_bindings'].__code__.co_filename,'source_sha256':{str(owner):hashlib.sha256(owner.read_bytes()).hexdigest()},'affinity':sorted(__import__('os').sched_getaffinity(0)),'limits':{'AS':list(__import__('resource').getrlimit(__import__('resource').RLIMIT_AS)),'CPU':list(__import__('resource').getrlimit(__import__('resource').RLIMIT_CPU))}}
(P/'HELPER-CHECK-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
