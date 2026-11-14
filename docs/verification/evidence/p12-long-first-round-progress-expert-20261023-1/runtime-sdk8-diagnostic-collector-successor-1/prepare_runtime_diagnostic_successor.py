"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Metadata-only SDK8 literal successor of accepted settlement runtime. No fixture/job/root/query/workload or expiry creation.
"""
import ast,hashlib,json,difflib,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent/'runtime-sdk8-successor-1';S=D/'source';R=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(name,raw):
 for root in [D,R]:
  with (root/name).open('xb') as f:f.write(raw)
def emit(name,value):write(name,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
def lit(s,key):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
 if isinstance(n.value,ast.Call):return {k.arg:ast.literal_eval(k.value) for k in n.value.keywords}
 return ast.literal_eval(n.value)
def replace(s,key,v):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets));return s.replace(ast.get_source_segment(s,n),key+' = '+repr(v),1)
def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
n=json.loads((D/'ROOT-SUCCESSOR-NAMESPACE.json').read_bytes());h=json.loads((D/'ACTUAL-DIAGNOSTIC-CASE-STAGE-BINDING.json').read_bytes());assert n['author']=='/root' and n['nonce'] and n['host_identity'] and h['actual_complete_wholejoin'] is True
assert ref(h['actual_handoff']['path'])==h['actual_handoff'];assert ref(h['manifest']['path'])['sha256']==h['manifest']['sha256']
newpins=h['additional_actual_source_pins']
for row in newpins:assert ref(row['path'])==row
for q in (B/'source').iterdir():
 if q.is_file() and q.name not in ['native_diagnostic_container_owner.py','CURRENT68-SDK8-AUTHORITY-LINKS.json','long_transport.py']:
  write('source/'+q.name,(Path(h['source_refs'][q.name]['path']) if q.name in h['source_refs'] and q.name!='long_transport.py' else q).read_bytes())
write('source/CURRENT68-SDK8-AUTHORITY-LINKS.json',Path(h['source_refs']['CURRENT68-SDK8-AUTHORITY-LINKS.json']['path']).read_bytes())
request=json.loads((B/'PROSPECTIVE-REQUEST-MODEL.NOT-EXECUTABLE.json').read_bytes());request=json.loads(json.dumps(request).replace(str(B),str(D)))
a=request['argv'];changes={'--attempt-parent':n['host_parent'],'--nonce':n['nonce'],'--manifest':n['manifest_path'],'--manifest-sha256':h['manifest']['sha256'],'--long-profile-release':n['release_path']}
for key,value in changes.items():a[a.index(key)+1]=value
request['long_profile_release']['path']=n['release_path'];field=lambda k:a[a.index(k)+1]
bindings=dict(OWNER_PATH=request['command_source']['path'],RELEASE_PATH=request['long_profile_release']['path'],HOST_PARENT=field('--attempt-parent'),NONCE=field('--nonce'),MANIFEST_PATH=field('--manifest'),MANIFEST_SHA=field('--manifest-sha256'))
old=(B/'capture_root_LONG.NOT-RELEASED.py').read_text();controller=old
for k,v in bindings.items():controller=replace(controller,k,v)
assert funcs(controller)==funcs(old);write('capture_root_LONG.NOT-RELEASED.py',controller.encode())
told=(B/'source/long_transport.py').read_text();host=lit(told,'HOST_OUTPUT');host.update(parent=n['host_parent'],retention_parent=str(Path(n['host_parent']).parent));external=lit(told,'EXTERNAL_CAPTURE_BINDING');external.update(controller_path=str(D/'capture_root_LONG.NOT-RELEASED.py'),controller_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],request_path=str(D/'CAPTURE-REQUEST.json'),capture_directory=request['capture_directory'],command_source_path=request['command_source']['path']);transport=replace(replace(told,'HOST_OUTPUT',host),'EXTERNAL_CAPTURE_BINDING',external);assert funcs(told)==funcs(transport)
write('source/long_transport.py',transport.encode())
aold=(B/'source/native_diagnostic_container_owner.py').read_text();oldhashes=lit(aold,'SOURCE_HASHES');hashes={k:v for k,v in oldhashes.items() if not k.startswith(str(B/'source')+'/')};preserved=dict(hashes)
assert len(oldhashes)==207 and len(hashes)==198
for q in sorted(S.iterdir()):
 if q.is_file():hashes[str(q)]=ref(q)['sha256']
for row in newpins:
 if row['path'] in hashes:assert hashes[row['path']]==row['sha256']
 else:hashes[row['path']]=row['sha256']
assert all(hashes[k]==v for k,v in preserved.items())
oldroots=lit(aold,'EXTRA_READONLY');roots=[str(S) if k==str(B/'source') else k for k in oldroots]
for k in h['additional_readonly_roots']:
 if k not in roots:roots.append(k)
assert '/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1' in roots
owner=replace(replace(replace(replace(aold,'SELF',str(S/'native_diagnostic_container_owner.py')),'RUNNER',str(S/'native_diagnostic_runner.py')),'SOURCE_HASHES',hashes),'EXTRA_READONLY',roots);owner=owner.replace('    source = '+repr(str(B/'source/native_diagnostic.py')),'    source = '+repr(str(S/'native_diagnostic.py')),1)
x,y=funcs(aold),funcs(owner);assert [k for k in x if x[k]!=y[k]]==['bound_manifest'];assert x['bound_manifest'].replace(str(B/'source/native_diagnostic.py'),'PATH')==y['bound_manifest'].replace(str(S/'native_diagnostic.py'),'PATH');write('source/native_diagnostic_container_owner.py',owner.encode())
cohort={q.name:ref(q) for q in S.iterdir() if q.is_file()};emit('COHORT-BINDINGS.json',cohort)
request.update(command_source=cohort['native_diagnostic_container_owner.py'],wrapper_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],status='PROTOTYPE_NOT_EXECUTABLE_FRESH_RELEASE_DIGEST_NULL');a[a.index('--owner-sha256')+1]=request['command_source']['sha256'];emit('PROSPECTIVE-REQUEST-MODEL.NOT-EXECUTABLE.json',request);emit('CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json',request)
test=json.loads(json.dumps(request));test['long_profile_release']['sha256']='0'*64;test['argv'][-1]='0'*64;test['status']='TESTONLY_PRE_EFFECT_GUARDS_NOT_EXECUTABLE';emit('TESTONLY-CORRECTED-REQUEST.json',test)
release=json.loads((B/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());release.update(manifest=dict(path=n['manifest_path'],sha256=h['manifest']['sha256']),nonce=n['nonce'],attempt_parent=n['host_parent']);release['profile']['host_output']=host;release['source_sha256']={k:cohort[k]['sha256'] for k in release['source_sha256']};emit('LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json',release)
required=set(json.loads((B/'PRECISE-SDK6-CONSUMED-PATHS.json').read_bytes())['required_paths']);required={str(S/('CURRENT68-SDK8-AUTHORITY-LINKS.json' if Path(k).name=='CURRENT68-SDK6-AUTHORITY-LINKS.json' else Path(k).name)) if k.startswith(str(B/'source')+'/') else k for k in required};required.update(hashes);required.update(row['path'] for row in newpins);required.update(row['path'] for row in h['stage_files']);required.add(n['manifest_path'])
emit('PRECISE-SDK6-CONSUMED-PATHS.json',dict(scope=__doc__,required_paths=sorted(required),new_source_pins=newpins,preserved_nonlocal198=True,source_hash_rows=len(hashes),readonly_roots=len(roots),actual_stage_handoff=h['actual_handoff']))
emit('SOURCE-TO-REQUEST-BINDING-MATRIX.json',dict(scope=__doc__,status='SDK8_ACTUAL_DATA_BOUND_NOT_FIXTURE_OR_RUNTIME_ACCEPTED',controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),controller_functions_AST_identical=True,controller_constant_matrix=[dict(constant=k,corrected_value=v,origin='ONEfutureactualrequestmodel') for k,v in bindings.items()],source_hash_rows=len(hashes),historical147unchanged=True,preserved_nonlocal198=True,readonly_roots=len(roots),actual_stage_manifest=h['manifest'],prospective_immutable_manifest=dict(path=n['manifest_path'],sha256=h['manifest']['sha256'],publication_observation=None),stage_handoff=h['actual_handoff'],transport_functions_AST_identical=True,owner_only_function_AST_delta='bound_manifest localdiagnostic sourcepath',actual_consumer=None,fresh_admission=None,runtime_release=None,native_acceptance=None))
consumer=(B/'controller_pre_effect_consumer.py').read_text().replace(ref(B/'capture_root_LONG.NOT-RELEASED.py')['sha256'],ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256']);write('controller_pre_effect_consumer.py',consumer.encode())
for name in ['fixture_actual_controller_guards.py','run_actual_guard_fixture_owned.py']:write(name,(B/name).read_bytes())
for name,left,right in [('controller',old,controller),('transport',told,transport),('owner',aold,owner)]:write(name+'.literal.diff',''.join(difflib.unified_diff(left.splitlines(True),right.splitlines(True),fromfile='frozen-settlement/'+name,tofile='SDK8-successor/'+name)).encode())
emit('NEXT-ACTUAL-FIXTURE-ARGV.NOT-RELEASED.json',dict(scope=__doc__,argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'run_actual_guard_fixture_owned.py')],profile=dict(cpu=[6],AS=2147483648,CPU=60,wall=120,grace=6,FSIZE=33554432,NOFILE=256,core=0),root_grant=None,immutable_manifest_publication=None,source=ref(D/'run_actual_guard_fixture_owned.py')))
print(json.dumps(dict(controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),owner=cohort['native_diagnostic_container_owner.py'],transport=cohort['long_transport.py'],source_hash_rows=len(hashes),readonly_roots=len(roots)),sort_keys=True))
