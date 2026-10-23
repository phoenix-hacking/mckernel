"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One selected SDK6 data/literal transformation from accepted848/d79/071. No root/workload/expiry authoring.
"""
import ast,hashlib,json,difflib
from pathlib import Path
D=Path(__file__).resolve().parent;OLD=D.parent/'expert-controller-binding-repair-1';S=D/'source';S.mkdir();R=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/runtime-sdk6-successor-1');(R/'source').mkdir()
H=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-next-native-preparation-1/capsule-next-1/ACTUAL-SDK6-CAPSULE-AND-STRICT-LOADER-HANDOFF.json')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='a445b1c9337829788997417931360eb55df7b3a7ff2253cdb85e4e98a3b5b001';h=json.loads(H.read_bytes());assert h['CPU6_released'] and h['actual_unchanged_members']==61
n=json.loads((D/'ROOT-RESERVED-NAMESPACE.json').read_bytes());manifest=h['actual_stage']['manifest'];assert hashlib.sha256(Path(n['scratch_manifest']).read_bytes()).hexdigest()==manifest['sha256']=='2f4c5c6dab2dcc5993df805da4d4c57c1e8d39c7ac2b4118b59ad578cd9c5c57'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def emit(name,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 for p in (D,R):(p/name).write_bytes(raw)
def lit(s,name):
 x=next(x for x in ast.parse(s).body if isinstance(x,ast.Assign) and any(isinstance(k,ast.Name) and k.id==name for k in x.targets))
 if isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='dict':return {k.arg:ast.literal_eval(k.value) for k in x.value.keywords}
 return ast.literal_eval(x.value)
def replace(s,name,value):
 x=next(x for x in ast.parse(s).body if isinstance(x,ast.Assign) and any(isinstance(k,ast.Name) and k.id==name for k in x.targets));return s.replace(ast.get_source_segment(s,x),name+' = '+repr(value),1)
def funcs(s):return {x.name:ast.dump(x,include_attributes=False) for x in ast.parse(s).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
# Derive every controller literal from ONE request model, never from path-prefix substitution.
request=json.loads((OLD/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());a=request['argv']
request.update(command_source=dict(path=str(S/'native_diagnostic_container_owner.py'),sha256=None,bytes=None),capture_directory=str(D/'actual-capture-1'),long_profile_release=dict(path=n['scratch_release'],sha256=None),wrapper_sha256=None)
a[13]=request['command_source']['path']
for flag,value in [('--attempt-parent',n['HOST_parent']),('--nonce',n['nonce']),('--manifest',n['scratch_manifest']),('--manifest-sha256',manifest['sha256']),('--long-profile-release',n['scratch_release'])]:a[a.index(flag)+1]=value
a[a.index('--owner-sha256')+1]=None;a[-1]=None
field=lambda key:a[a.index(key)+1]
bindings=dict(OWNER_PATH=request['command_source']['path'],RELEASE_PATH=request['long_profile_release']['path'],HOST_PARENT=field('--attempt-parent'),NONCE=field('--nonce'),MANIFEST_PATH=field('--manifest'),MANIFEST_SHA=field('--manifest-sha256'))
oldctl=(OLD/'capture_root_LONG.NOT-RELEASED.py').read_text();controller=oldctl
for key,value in bindings.items():controller=replace(controller,key,value)
assert funcs(oldctl)==funcs(controller)
for p in (D,R):(p/'capture_root_LONG.NOT-RELEASED.py').write_text(controller)
for p in (OLD/'source').iterdir():
 if p.is_file() and p.suffix in ('.py','.json') and p.name!='CURRENT68-SDK5-AUTHORITY-LINKS.json':(S/p.name).write_bytes(p.read_bytes())
for name,row in h['authority_source_pins'].items():
 p=Path(row['path']);assert ref(p)==row;(S/name).write_bytes(p.read_bytes())
told=(S/'long_transport.py').read_text();external=lit(told,'EXTERNAL_CAPTURE_BINDING');external.update(controller_path=str(D/'capture_root_LONG.NOT-RELEASED.py'),controller_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],request_path=str(D/'CAPTURE-REQUEST.json'),capture_directory=request['capture_directory'],command_source_path=request['command_source']['path']);host=lit(told,'HOST_OUTPUT');host.update(parent=n['HOST_parent'],retention_parent=str(Path(n['HOST_parent']).parent));transport=replace(replace(told,'HOST_OUTPUT',host),'EXTERNAL_CAPTURE_BINDING',external);(S/'long_transport.py').write_text(transport);assert funcs(told)==funcs(transport)
aold=(S/'native_diagnostic_container_owner.py').read_text();hashes=lit(aold,'SOURCE_HASHES');oldroots=lit(aold,'EXTRA_READONLY');historical={k:v for k,v in hashes.items() if not k.startswith(str(OLD/'source')+'/')};assert len(historical)==147
for key in list(hashes):
 if key.startswith(str(OLD/'source')+'/'):
  name=Path(key).name;del hashes[key]
  if name=='CURRENT68-SDK5-AUTHORITY-LINKS.json':name='CURRENT68-SDK6-AUTHORITY-LINKS.json'
  hashes[str(S/name)]=ref(S/name)['sha256']
links=json.loads((S/'CURRENT68-SDK6-AUTHORITY-LINKS.json').read_bytes());sdk=json.loads(Path(links['proofs']['SDK6_acceptance']['path']).read_bytes());actual=json.loads(Path(sdk['actual_reads']['path']).read_bytes());newpins=list(h['authority_source_pins'].values())+[links['proofs'][k] for k in ['SDK6_source_preparation','EVENTFD_source_and_nine_fixture_review','SDK6_acceptance']]+[sdk['actual_reads'],sdk['owner_receipt']]+list(actual['source_and_driver_bindings'].values())
for row in newpins:
 p=Path(row['path']);assert ref(p)==row
 if str(p) in hashes:assert hashes[str(p)]==row['sha256']
 else:hashes[str(p)]=row['sha256']
assert all(hashes[k]==v for k,v in historical.items())
# Preserve ALL historical RO roots; append exact new consumed SDK6 directories.
roots=[str(S) if p==str(OLD/'source') else p for p in oldroots]
newroots=[str(Path(manifest['path']).parent),h['source_map_handoff']['new_module_readonly_root'],str(Path(actual['source_and_driver_bindings']['actual_driver_receipt']['path']).parent),str(Path(sdk['owner_receipt']['path']).parent),str(Path(links['proofs']['SDK6_source_preparation']['path']).parent),str(Path(h['authority_source_pins']['composite_module_binding.py']['path']).parent)]
for p in newroots:
 if p not in roots:roots.append(p)
assert '/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1' in roots
owner=replace(replace(replace(replace(aold,'SELF',str(S/'native_diagnostic_container_owner.py')),'RUNNER',str(S/'native_diagnostic_runner.py')),'SOURCE_HASHES',hashes),'EXTRA_READONLY',roots);owner=owner.replace('    source = '+repr(str(OLD/'source/native_diagnostic.py')),'    source = '+repr(str(S/'native_diagnostic.py')),1);(S/'native_diagnostic_container_owner.py').write_text(owner)
af,bf=funcs(aold),funcs(owner);assert [k for k in af if af[k]!=bf[k]]==['bound_manifest'];assert af['bound_manifest'].replace(str(OLD/'source/native_diagnostic.py'),'PATH')==bf['bound_manifest'].replace(str(S/'native_diagnostic.py'),'PATH')
for p in S.iterdir():(R/'source'/p.name).write_bytes(p.read_bytes())
cohort={p.name:ref(p) for p in S.iterdir() if p.is_file()};emit('COHORT-BINDINGS.json',cohort)
request.update(command_source=cohort['native_diagnostic_container_owner.py'],wrapper_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],status='PROTOTYPE_NOT_EXECUTABLE_FRESH_RELEASE_DIGEST_NULL');a[a.index('--owner-sha256')+1]=request['command_source']['sha256'];emit('CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json',request)
test=json.loads(json.dumps(request));test['status']='TESTONLY_PRE_EFFECT_GUARDS_NOT_EXECUTABLE';test['long_profile_release']['sha256']='0'*64;test['argv'][-1]='0'*64;emit('TESTONLY-CORRECTED-REQUEST.json',test)
release=json.loads((OLD/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());release.update(manifest=dict(path=n['scratch_manifest'],sha256=manifest['sha256']),nonce=n['nonce'],attempt_parent=n['HOST_parent']);release['profile']['host_output']=host;release['source_sha256']={key:cohort[key]['sha256'] for key in release['source_sha256']};emit('LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json',release)
# Required SDK6 graph, with actual provider paths and all recorded historical identities retained.
required=[str(S/name) for name in cohort]+list(hashes)+[n['scratch_manifest']]+[row['path'] for row in h['actual_stage'].values() if isinstance(row,dict) and 'path'in row]+[row['path'] for row in newpins]
required+= [row['path'] for row in json.loads(Path(manifest['path']).read_bytes())['base']['modules']] if 'base' in json.loads(Path(manifest['path']).read_bytes()) else []
emit('PRECISE-SDK6-CONSUMED-PATHS.json',dict(scope=__doc__,required_paths=sorted(set(required)),new_source_pins=newpins,retained_historical_rows=len(historical),selected_source_rows=9,source_hash_rows=len(hashes),readonly_roots=len(roots),added_RO_roots=newroots,actual_stage_handoff=ref(H),current_live_SDK6_acceptance=h['current_live_authority'],all_historical_RO_roots_preserved_except_selected_source_dir=True))
proof=dict(scope=__doc__,status='SDK6_ACTUAL_DATA_COHORT_BOUND_NOT_FIXTURE_OR_RUNTIME_ACCEPTED',controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),controller_functions_AST_identical=True,controller_constant_matrix=[dict(constant=k,corrected_value=v,origin='ONE futureactualrequestmodel') for k,v in bindings.items()],source_hash_rows=len(hashes),historical147unchanged=True,readonly_roots=len(roots),actual_manifest=ref(Path(n['scratch_manifest'])),stage_handoff=ref(H),transport_functions_AST_identical=True,owner_only_function_AST_delta='bound_manifest local diagnostic sourcepath literal',actual_consumer=None,fresh_admission=None,runtime_release=None,native_acceptance=None);emit('SOURCE-TO-REQUEST-BINDING-MATRIX.json',proof)
for name,a,b in [('controller',oldctl,controller),('transport',told,transport),('owner',aold,owner)]:
 diff=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='acceptedSDK5/'+name,tofile='SDK6/'+name))
 for p in (D,R):(p/(name+'.literal.diff')).write_text(diff)
print(json.dumps(dict(controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'),owner=cohort['native_diagnostic_container_owner.py'],transport=cohort['long_transport.py'],source_hash_rows=len(hashes),ROroots=len(roots)),sort_keys=True))
