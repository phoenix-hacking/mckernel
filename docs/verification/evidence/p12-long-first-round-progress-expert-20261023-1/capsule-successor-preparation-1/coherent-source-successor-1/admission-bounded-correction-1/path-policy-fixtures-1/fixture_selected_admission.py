"""Functional OS exact selected admission predicate regressions only; no security testing.
Authentic query observations copied, controlled path collisions, no new admission/PROC/Docker work.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent;SELECTED=D.parent;COHORT=SELECTED.parent
source=SELECTED/'read_only_LONG_HOST_admission.py';raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='dc3362762416263908ff070545146bd5488919414e3be33fba4a05069fcefe1a'
spec=importlib.util.spec_from_file_location('actual_selected_dc336_query',source);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
c=q.inputs();physicalraw=Path(c['physical']['path']).read_bytes();assert hashlib.sha256(physicalraw).hexdigest()==c['physical']['sha256']=='591cdb070b8f6cfe18a9903a69e3603a5590f737c12e478fc01833d9a5cef01f'
query=SELECTED/'authenticated-admission-readback-1/stdout';queryraw=query.read_bytes();assert hashlib.sha256(queryraw).hexdigest()=='98d98a9dc10a74a58ec9bb78018d1261123b1c2b17205f14ffbe7036aca7cb2a';actual=json.loads(queryraw);assert actual['status']=='PASS_FRESH_READ_ONLY_P12_LONG_ADMISSION'
f=copy.deepcopy(actual['observations']);assert c['retained_previous_owner_evidence_paths'] and all(os.path.lexists(p) for p in c['retained_previous_owner_evidence_paths'])
assert not set(c['retained_previous_owner_evidence_paths']).intersection(f['output_paths_exist'])
fn=next(x for x in ast.parse(raw).body if isinstance(x,ast.FunctionDef) and x.name=='validate');predicate=next(x for x in fn.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and any(isinstance(n,ast.Constant) and n.value=='fresh LONG capture owner attempt and unpublished release/request paths absent' for n in ast.walk(x)))
code=compile(ast.Module(body=[predicate],type_ignores=[]),str(source),'exec')
def check(facts):exec(code,{'f':facts,'need':q.need})
check(f);rows=[{'case':'actual98d98_fresh_paths_clear_while_prior_owner_evidence_retained','result':'PASS_PREDICATE_ONLY'}]
for path in f['output_paths_exist']:
 mutant=copy.deepcopy(f);mutant['output_paths_exist'][path]=True
 try:check(mutant)
 except RuntimeError:rows.append({'case':'collision:'+path,'result':'REJECTED'})
 else:raise AssertionError('freshcollisionaccepted')
# Exact source inputs() SHA protects retained historical path/authority policy.
original_D=q.D
for label,mutate in [('removed_historical_paths',lambda v:v.update(retained_previous_owner_evidence_paths=[])),('changed_retirement_pin',lambda v:v['retained_previous_owner_retirement_authority'].update(sha256='0'*64))]:
 v=copy.deepcopy(c);mutate(v);folder=D/label;folder.mkdir();(folder/'QUERY-INPUTS.json').write_text(json.dumps(v));q.D=folder
 try:q.inputs()
 except RuntimeError:rows.append({'case':label,'result':'REJECTED_EXACT_INPUT_POLICY_HASH'})
 else:raise AssertionError('changedhistoricalpolicyaccepted')
 finally:q.D=original_D
spec=importlib.util.spec_from_file_location('actual_selected_long_transport',COHORT/'source/long_transport.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
proto=json.loads((COHORT/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());proto['profile']=g.TRANSPORT;proto['storage_admission']=f['admission'];assert proto['profile']['host_output']==g.HOST_OUTPUT
assert proto['profile']['host_output']['parent']=='/home/holden/mckernel-work/native-runs/l12b1/p'
assert proto['status'] is None and proto['boot_id'] is None and proto['expires_unix'] is None and proto['independent_review'] is None
with (COHORT/'LONG-RELEASE.ACTUAL-ADMISSION-BOUND.PENDING.json').open('x') as out:json.dump(proto,out,indent=2,sort_keys=True);out.write('\n')
result={'scope':__doc__,'status':'PASS_ACTUAL_SELECTED_DC336_QUERY_PATH_PREDICATE_AND_INPUT_POLICY_REGRESSIONS','checks':rows,'retained_previous_owner_paths':c['retained_previous_owner_evidence_paths'],'actual_retained_paths_present':True,'actual_query_sha256':hashlib.sha256(queryraw).hexdigest(),'selected_query_sha256':hashlib.sha256(raw).hexdigest(),'physical_sha256':c['physical']['sha256'],'query_full_validate_rerun':False,'source_predicate_only':True,'root':0,'PROC':0,'Docker':0,'owner_or_lease_mutations':0,'fresh_admission':False,'release_profile_from_selected_TRANSPORT':True,'expiry_minted':False,'approval_authored':False}
with (D/'ACTUAL-SELECTED-QUERY-PREDICATE-RESULT.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(result))
