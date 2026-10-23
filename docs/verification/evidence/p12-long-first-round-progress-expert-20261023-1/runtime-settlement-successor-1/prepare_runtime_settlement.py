"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One metadata-only settlement successor derivation from frozen RT6, gated on genuine case-owned stage inputs.
No compiler/fixture/root/query/workload/expiry invocation.
"""
import ast,hashlib,json,difflib,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent/'runtime-sdk6-successor-1';S=D/'source';R=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/runtime-settlement-successor-1')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def emit(name,x):
 b=(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
 for root in [D,R]:
  with (root/name).open('xb') as f:f.write(b)
def lit(s,key):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
 if isinstance(n.value,ast.Call):return {k.arg:ast.literal_eval(k.value) for k in n.value.keywords}
 return ast.literal_eval(n.value)
def replace(s,key,v):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets));return s.replace(ast.get_source_segment(s,n),key+' = '+repr(v),1)
def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
n=json.loads((D/'ROOT-SUCCESSOR-NAMESPACE.json').read_bytes());h=json.loads((D/'ACTUAL-CASE-STAGE-BINDING.json').read_bytes());assert h['actual_complete_wholejoin'] is True and h['manifest']['sha256'] and h['stage_files'] and h['additional_actual_source_pins']
manifest=Path(n['manifest_path']);assert ref(h['manifest']['path'])['sha256']==h['manifest']['sha256'];assert ref(h['actual_handoff']['path'])==h['actual_handoff']
p=json.loads((D/'ACTUAL-SETTLEMENT-PROVIDER-INPUTS.json').read_bytes());newpins=list(p['production3'].values())+[ref(p['actual_fixture_receipt']['path']),h['actual_handoff']]+h['additional_actual_source_pins'];assert newpins[3]['sha256']==p['actual_fixture_receipt']['sha256']
for row in newpins:assert ref(row['path'])==row
request=json.loads((D/'PROSPECTIVE-REQUEST-MODEL.NOT-EXECUTABLE.json').read_bytes());a=request['argv'];a[a.index('--manifest-sha256')+1]=h['manifest']['sha256'];field=lambda k:a[a.index(k)+1]
bindings=dict(OWNER_PATH=request['command_source']['path'],RELEASE_PATH=request['long_profile_release']['path'],HOST_PARENT=field('--attempt-parent'),NONCE=field('--nonce'),MANIFEST_PATH=field('--manifest'),MANIFEST_SHA=field('--manifest-sha256'))
old=(B/'capture_root_LONG.NOT-RELEASED.py').read_text();controller=old
for k,v in bindings.items():controller=replace(controller,k,v)
assert funcs(controller)==funcs(old)
for root in [D,R]:(root/'capture_root_LONG.NOT-RELEASED.py').write_text(controller)
told=(B/'source/long_transport.py').read_text();host=lit(told,'HOST_OUTPUT');host.update(parent=n['host_parent'],retention_parent=str(Path(n['host_parent']).parent));external=lit(told,'EXTERNAL_CAPTURE_BINDING');external.update(controller_path=str(D/'capture_root_LONG.NOT-RELEASED.py'),controller_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],request_path=str(D/'CAPTURE-REQUEST.json'),capture_directory=request['capture_directory'],command_source_path=request['command_source']['path']);transport=replace(replace(told,'HOST_OUTPUT',host),'EXTERNAL_CAPTURE_BINDING',external);assert funcs(told)==funcs(transport);(S/'long_transport.py').write_text(transport)
aold=(B/'source/native_diagnostic_container_owner.py').read_text();hashes=lit(aold,'SOURCE_HASHES');preserved={k:v for k,v in hashes.items() if not k.startswith(str(B/'source')+'/')};assert len(hashes)==167 and len(preserved)==158
for k in list(hashes):
 if k.startswith(str(B/'source')+'/'):del hashes[k];hashes[str(S/Path(k).name)]=ref(S/Path(k).name)['sha256']
for row in newpins:
 if row['path'] in hashes:assert hashes[row['path']]==row['sha256']
 else:hashes[row['path']]=row['sha256']
assert all(hashes[k]==v for k,v in preserved.items())
oldroots=lit(aold,'EXTRA_READONLY');roots=[str(S) if k==str(B/'source') else k for k in oldroots];newroots=h['additional_readonly_roots']+[str(Path(row['path']).parent) for row in p['production3'].values()]
for k in newroots:
 if k not in roots:roots.append(k)
assert '/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1' in roots
owner=replace(replace(replace(replace(aold,'SELF',str(S/'native_diagnostic_container_owner.py')),'RUNNER',str(S/'native_diagnostic_runner.py')),'SOURCE_HASHES',hashes),'EXTRA_READONLY',roots);owner=owner.replace('    source = '+repr(str(B/'source/native_diagnostic.py')),'    source = '+repr(str(S/'native_diagnostic.py')),1)
x,y=funcs(aold),funcs(owner);assert [k for k in x if x[k]!=y[k]]==['bound_manifest'];assert x['bound_manifest'].replace(str(B/'source/native_diagnostic.py'),'PATH')==y['bound_manifest'].replace(str(S/'native_diagnostic.py'),'PATH');(S/'native_diagnostic_container_owner.py').write_text(owner)
for q in S.iterdir():shutil.copy2(q,R/'source'/q.name)
cohort={q.name:ref(q) for q in S.iterdir() if q.is_file()};emit('COHORT-BINDINGS.json',cohort)
request.update(command_source=cohort['native_diagnostic_container_owner.py'],wrapper_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],status='PROTOTYPE_NOT_EXECUTABLE_FRESH_RELEASE_DIGEST_NULL');a[a.index('--owner-sha256')+1]=request['command_source']['sha256'];emit('CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json',request)
test=json.loads(json.dumps(request));test['long_profile_release']['sha256']='0'*64;test['argv'][-1]='0'*64;test['status']='TESTONLY_PRE_EFFECT_GUARDS_NOT_EXECUTABLE';emit('TESTONLY-CORRECTED-REQUEST.json',test)
release=json.loads((B/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());release.update(manifest=dict(path=n['manifest_path'],sha256=h['manifest']['sha256']),nonce=n['nonce'],attempt_parent=n['host_parent']);release['profile']['host_output']=host;release['source_sha256']={k:cohort[k]['sha256'] for k in release['source_sha256']};emit('LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json',release)
required=set(json.loads((B/'PRECISE-SDK6-CONSUMED-PATHS.json').read_bytes())['required_paths']);required={str(S/Path(k).name) if k.startswith(str(B/'source')+'/') else k for k in required};required.update(hashes);required.update(row['path'] for row in newpins);required.update(row['path'] for row in h['stage_files']);required.add(n['manifest_path'])
emit('PRECISE-SDK6-CONSUMED-PATHS.json',dict(scope=__doc__,required_paths=sorted(required),new_source_pins=newpins,retained_historical147_and_SDK6_authority11=True,source_hash_rows=len(hashes),readonly_roots=len(roots),added_RO_roots=newroots,actual_stage_handoff=h['actual_handoff']))
emit('SOURCE-TO-REQUEST-BINDING-MATRIX.json',dict(scope=__doc__,status='SETTLEMENT_ACTUAL_DATA_BOUND_NOT_FIXTURE_OR_RUNTIME_ACCEPTED',controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),controller_functions_AST_identical=True,controller_constant_matrix=[dict(constant=k,corrected_value=v,origin='ONEfutureactualrequestmodel') for k,v in bindings.items()],source_hash_rows=len(hashes),historical147unchanged=True,priorSDK6authority11unchanged=True,readonly_roots=len(roots),actual_stage_manifest=ref(h['manifest']['path']),prospective_immutable_manifest=dict(path=str(manifest),sha256=h['manifest']['sha256'],publication_observation=None),stage_handoff=h['actual_handoff'],transport_functions_AST_identical=True,owner_only_function_AST_delta='bound_manifest localdiagnostic sourcepath',actual_consumer=None,fresh_admission=None,runtime_release=None,native_acceptance=None))
consumer=(B/'controller_pre_effect_consumer.py').read_text().replace('420a55c44bc32f90910b81f1855cdab521e41a2683f741ac3628cda24564f50d',ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'])
for root in [D,R]:(root/'controller_pre_effect_consumer.py').write_text(consumer)
for name,left,right in [('controller',old,controller),('transport',told,transport),('owner',aold,owner)]:
 diff=''.join(difflib.unified_diff(left.splitlines(True),right.splitlines(True),fromfile='frozenRT6/'+name,tofile='settlement-successor/'+name))
 for root in [D,R]:(root/(name+'.literal.diff')).write_text(diff)
print(json.dumps(dict(controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),owner=cohort['native_diagnostic_container_owner.py'],transport=cohort['long_transport.py'],source_hash_rows=len(hashes),readonly_roots=len(roots)),sort_keys=True))
