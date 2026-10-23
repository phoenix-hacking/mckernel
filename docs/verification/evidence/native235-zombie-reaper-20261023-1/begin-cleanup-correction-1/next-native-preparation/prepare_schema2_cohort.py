"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind independently accepted schema2 to finite native cohort/data templates only.
No module snapshot, archive, stage, root or guest execution; module hashes stay NULL.
"""
from pathlib import Path
import ast,copy,hashlib,json
E=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1');F=N/'begin-cleanup-native-successor-2';OLD=N/'native-runtime-ready-1';R=F/'runtime-cleanup-schema2-1'
D=E.parent/'diagnostic-consumer-successor/candidate2';review=D/'INDEPENDENT-SOURCE-REVIEW.json'
NATIVE='b41a93aad19d312a9bf6f62d064a1c9a525613d89f995de235d9803a0da29741'
V3='0b4bec6576b4aa4ae81a982bbd400b6028ce0aea6b0de02f84d46463af6450ea'
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):
 with p.open('x')as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def source(p,s):ast.parse(s);p.write_text(s)
def replace_assignments(s,values):
 lines=s.splitlines(True)
 for node in sorted([n for n in ast.parse(s).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in values for t in n.targets)],key=lambda n:n.lineno,reverse=True):lines[node.lineno-1:node.end_lineno]=[node.targets[0].id+' = '+repr(values[node.targets[0].id])+'\n']
 return ''.join(lines)
assert ref(review)['sha256']=='132aa53cb616965a0d5d755b9ad19a5715d35076d1eeadd033ca676e543269d9';decision=load(review);assert decision['status']=='PASS'and decision['native_source_sha256']==NATIVE and decision['v3_source_sha256']==V3
map=load(D/'SOURCE-MAP.json');native=Path(next(r for r in map['sources']if r['role']=='native')['private_path']);v3=Path(next(r for r in map['sources']if r['role']=='v3')['private_path']);assert ref(native)['sha256']==NATIVE and ref(v3)['sha256']==V3
R.mkdir(mode=0o700,exist_ok=False)
for name in ['native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py']:(R/name).write_bytes((OLD/name).read_bytes())
(R/'native_diagnostic.py').write_bytes(native.read_bytes())
owner=(OLD/'native_diagnostic_container_owner.py').read_text();tree=ast.parse(owner);pins=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='SOURCE_HASHES'for t in n.targets))
for name in ['native_diagnostic.py','native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py']:
 oldpath=str(OLD/name);assert oldpath in pins;pins.pop(oldpath);pins[str(R/name)]=ref(R/name)['sha256']
owner=replace_assignments(owner,dict(RUNNER=str(R/'native_diagnostic_runner.py'),SELF=str(R/'native_diagnostic_container_owner.py'),SOURCE_HASHES=pins))
needle="source = "+repr(str(OLD/'native_diagnostic.py'));assert owner.count(needle)==1;owner=owner.replace(needle,'source = '+repr(str(R/'native_diagnostic.py')));source(R/'native_diagnostic_container_owner.py',owner)
cohort=dict(scope=__doc__.splitlines()[0],status='SOURCE_BOUND_ACCEPTED_SCHEMA2_COHORT_MODULES_STILL_PENDING',schema_review=ref(review),native_diagnostic=ref(R/'native_diagnostic.py'),owner=ref(R/'native_diagnostic_container_owner.py'),runtime_sources=[ref(R/name)for name in ['native_diagnostic.py','native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py','native_diagnostic_container_owner.py']],sourcehashes=pins,unchanged_owner_body_rule='Only RUNNER/SELF/SOURCE_HASHES and exact bound diagnostic load path changed; all runtime/resource/retirement logic preserved.',accepted_v3_source=ref(v3),module_tuple=None,native_execution_authorized=False)
save(F/'COHERENT-NATIVE-SCHEMA2-COHORT.json',cohort)
(F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json').write_bytes((D/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json').read_bytes());profile=load(F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json');assert profile['id']=='begin-cleanup-real-ack-parent-clone-v2'and profile['modules']is None
# The exact old binder remains retained. Only its source load/pin and pending
# operation filename change; artifact joins and strict QMP/oracles are unchanged.
binder=(F/'bind_actual_v3_case_data.py').read_text();assert hashlib.sha256(binder.encode()).hexdigest()=='1bd397b832ae076e9617bed79bd4d8a70bc34bfbf37be1eee1896acdc8d0569c'
binder=binder.replace("consumer=N/'native-runtime-ready-1/native_diagnostic.py'",'consumer=Path('+repr(str(R/'native_diagnostic.py'))+')').replace('69d7bdb600309a4aea02f38746ba17438bf6e4758def35d6c2f90264c3ee75e3',NATIVE).replace("C/'NATIVE-OPERATION.PENDING.json'","C/'NATIVE-OPERATION.SCHEMA2-PENDING.json'").replace('UNCHANGED_STRICT69D_MANIFEST','ACCEPTED_SCHEMA2_MANIFEST');source(F/'bind_actual_case_schema2.py',binder)
for n in ['235','227']:
 C=F/('case-'+n);op=load(C/'NATIVE-OPERATION.PENDING.json');a=op['argv'];a[a.index(str(OLD/'native_diagnostic_container_owner.py'))]=str(R/'native_diagnostic_container_owner.py');a[a.index('--owner-sha256')+1]=cohort['owner']['sha256'];op.update(status='ACCEPTED_SCHEMA2_COHORT_PENDING_ACTUAL_SDK_AND_NATIVE_RELEASE',schema_cohort=ref(F/'COHERENT-NATIVE-SCHEMA2-COHORT.json'));save(C/'NATIVE-OPERATION.SCHEMA2-PENDING.json',op)
 a=load(C/'STRICT-CONSUMER-ARGV.PENDING.json');a[a.index(str(F/'bind_actual_v3_case_data.py'))]=str(F/'bind_actual_case_schema2.py');save(C/'STRICT-CONSUMER-ARGV.SCHEMA2-PENDING.json',a)
 data=load(C/'CASE-DATA.PENDING.json');data.update(diagnostic_schema=ref(F/'COHERENT-NATIVE-SCHEMA2-COHORT.json'),cleanup_profile_template=ref(F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json'));save(C/'CASE-DATA.SCHEMA2-PENDING.json',data)
# Future actual SDK binding supplies exactly the same ordered module references
# to the new optional profile. No old binary tuple is inserted in preparation.
s=(E/'bind_accepted_sdk.py').read_text();needle="save(C/'STRICT-NATIVE-MANIFEST.SDK-BOUND.json',m)";assert s.count(needle)==1
s=s.replace(needle,"profile=load(E/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json');assert profile['modules']is None;profile['modules']=copy.deepcopy(m['modules']);m['cleanup_profile']=profile;"+needle);source(E/'bind_accepted_sdk.schema2.py',s)
s=(E/'bind_stage_data.py').read_text().replace("c/'CASE-DATA.PENDING.json'","c/'CASE-DATA.SCHEMA2-PENDING.json'").replace("c/'STRICT-CONSUMER-ARGV.PENDING.json'","c/'STRICT-CONSUMER-ARGV.SCHEMA2-PENDING.json'");source(E/'bind_stage_data.schema2.py',s)
s=(E/'prepare_release_data.py').read_text();needle="guard[-1]=str(G/'EXACT-GUARD-DATA.json');save(G/'EXACT-PRODUCTION-GUARD-ARGV.json',guard)";assert needle in s
replacement="guard[ci]=guard[ci].replace('4d7ae097cae866389ed044a6247e01f1bc78ff8744fc8d72f39fb294b55bb298',"+repr(cohort['owner']['sha256'])+");guard[-2]="+repr(str(R))+";"+needle
s=s.replace(needle,replacement);s=s.replace("'reuse_unchanged139_tool_backend_authority':ref(PREVIOUS/'BOUND-CURRENT-IDENTITIES.ADDITIVE.json'),","'reuse_unchanged139_tool_backend_authority':ref(PREVIOUS/'BOUND-CURRENT-IDENTITIES.ADDITIVE.json'),'changed_schema2_source_cohort':ref(F/'COHERENT-NATIVE-SCHEMA2-COHORT.json'),")
source(E/'prepare_release_data.schema2.py',s)
packet=load(E/'REVIEW-READY-NEXT-STAGE-PACKET.PY39.json')
for row in packet['operations_in_order']:
 row['argv']=[v.replace('bind_accepted_sdk.py','bind_accepted_sdk.schema2.py').replace('bind_stage_data.py','bind_stage_data.schema2.py').replace('prepare_release_data.py','prepare_release_data.schema2.py')if isinstance(v,str)else v for v in row['argv']]
packet.update(status='ACCEPTED_SCHEMA2_COHORT_PY39_PENDING_REAL_SDK_TUPLE_AND_STAGE_GRANT',schema2_cohort=ref(F/'COHERENT-NATIVE-SCHEMA2-COHORT.json'),schema2_review=ref(review),cleanup_profile_template=ref(F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json'))
packet['schema2_changed_sources']=[ref(p)for p in [E/'bind_accepted_sdk.schema2.py',E/'bind_stage_data.schema2.py',E/'prepare_release_data.schema2.py',F/'bind_actual_case_schema2.py']]
save(E/'REVIEW-READY-NEXT-STAGE-PACKET.SCHEMA2.json',packet)
print(json.dumps(dict(status=packet['status'],packet=ref(E/'REVIEW-READY-NEXT-STAGE-PACKET.SCHEMA2.json'),cohort=ref(F/'COHERENT-NATIVE-SCHEMA2-COHORT.json'),owner=cohort['owner'],diagnostic=cohort['native_diagnostic'],effects=dict(snapshots=0,archives=0,stages=0,root=0,guests=0))))
